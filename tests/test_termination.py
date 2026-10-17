"""
TODO #10: however sshdd ends, it cleans up: terminal mode restored, alternate screen left,
no temp files (/tmp/.hprobe-*, /tmp/.ssh-askpass-*) and no host-probe processes left behind.

Runs sshdd from an interactive bash in a pty (job control on, like a real terminal), so Ctrl+C/Ctrl+Z
reach sshdd only, and the shell's `stty -a` afterwards shows the state the user would be left with.
Hosts use TEST-NET addresses (192.0.2.x) so the reachability probes are still running when we strike.
"""
import glob
import os
import signal
import subprocess
import time

import pexpect
import pytest

from .screen import BASH32, ROOT

TMP_GLOBS = ["/tmp/.hprobe-*", "/tmp/.ssh-askpass-*"]
PROMPT = "READY> "


def _tmp_files():
    return {f for g in TMP_GLOBS for f in glob.glob(g)}


@pytest.fixture
def shell(tmp_path):
    ssh = tmp_path / ".ssh"
    ssh.mkdir(mode=0o700)
    (ssh / "config").write_text("".join(
        f"Host t{i}\n    HostName 192.0.2.{i}\n    User root\n" for i in range(1, 4)))
    env = dict(os.environ, HOME=str(tmp_path), TERM="xterm-256color", LANG="en_US.UTF-8",
               PS1=PROMPT, EDITOR="/bin/true")
    sh = pexpect.spawn(BASH32, ["--norc", "--noprofile", "-i"], cwd=ROOT, env=env,
                       encoding="utf-8", dimensions=(40, 100), timeout=10)
    sh.expect_exact(PROMPT)
    yield sh
    sh.terminate(force=True)


def _start(sh, marker):
    sh.sendline(f"{BASH32} ./sshdd.sh --comment-suffix {marker}")
    sh.expect("Quit")
    time.sleep(0.5)


def _pid(marker):
    out = subprocess.run(["pgrep", "-f", f"sshdd.sh --comment-suffix {marker}"],
                         capture_output=True, text=True).stdout.split()
    return int(out[0]) if out else None


def _assert_clean(sh, before):
    sh.expect_exact(PROMPT, timeout=10)
    out = sh.before
    assert "\x1b[?1049l" in out, "did not leave the alternate screen"
    sh.sendline("stty -a")
    sh.expect_exact(PROMPT)
    modes = sh.before.split()
    assert "echo" in modes and "icanon" in modes, "terminal left in raw/no-echo mode"
    time.sleep(2.5)                                   # a leaked probe would still run its 2 s timeout
    assert not (_tmp_files() - before), f"temp files left: {_tmp_files() - before}"
    probes = subprocess.run(["pgrep", "-f", "/dev/tcp/192.0.2."], capture_output=True, text=True).stdout
    assert not probes.strip(), f"probe processes left: {probes}"


@pytest.mark.parametrize("how", ["ctrl-c", "ctrl-z", "sigterm", "sighup"])
@pytest.mark.parametrize("where", ["menu", "host-probe"])
def test_cleanup_on_termination(shell, how, where):
    marker = f"-term-{how}-{where}"
    before = _tmp_files()
    _start(shell, marker)
    if where == "host-probe":
        shell.send("T")                               # starts the parallel reachability probes
        shell.expect("Checking host availability")
    if how == "ctrl-c":
        shell.sendcontrol("c")
    elif how == "ctrl-z":
        shell.sendcontrol("z")
    else:
        os.kill(_pid(marker), signal.SIGTERM if how == "sigterm" else signal.SIGHUP)
    _assert_clean(shell, before)
    assert _pid(marker) is None, "sshdd still running"
