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

TMP_GLOBS = [".hprobe-*", ".ssh-askpass-*", ".sshdd-*"]
PROMPT = "READY> "


def _tmp_files():
    return {f for g in TMP_GLOBS for f in glob.glob(f"{os.environ['TMPDIR']}/{g}")}   # per test (conftest)


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
    # This test's session only: under xdist other workers run probes to 192.0.2.x at the same time (#25).
    probes = subprocess.run(["pgrep", "-s", str(sh.pid), "-f", "/dev/tcp/192.0.2."],
                            capture_output=True, text=True).stdout
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


# ── X2: ending sshdd while it's inside a sub-screen or a child program ─────────

def _group_pid(marker):
    pid = _pid(marker)
    return os.getpgid(pid) if pid else None


@pytest.mark.parametrize("how", ["ctrl-c", "close-terminal"])
@pytest.mark.parametrize("where", ["pager", "conf", "help", "editor"])
def test_cleanup_inside_subscreens(shell, tmp_path, how, where):
    marker = f"-x2-{how}-{where}"
    before = _tmp_files()
    if where == "editor":
        ed = tmp_path / "fake-editor"                     # an editor that stays open (ignores the file)
        ed.write_text("#!/bin/sh\nexec sleep 37\n")
        ed.chmod(0o755)
        shell.sendline(f"export EDITOR={ed}")
        shell.expect_exact(PROMPT)
    _start(shell, marker)
    keys = {"pager": "V", "conf": "\x1b[15~", "help": "?", "editor": "E"}[where]
    shell.send(keys)
    time.sleep(1.5)
    if how == "ctrl-c":
        shell.sendcontrol("c")
    else:
        os.killpg(_group_pid(marker), signal.SIGHUP)      # what a closing terminal does
    if how == "close-terminal":
        # the shell itself got SIGHUP too; check the leftovers from outside
        time.sleep(2.5)
        assert _pid(marker) is None, "sshdd still running"
        assert not (_tmp_files() - before)
    else:
        _assert_clean(shell, before)
    left = subprocess.run(["pgrep", "-s", str(shell.pid), "-f", "^sleep 37$"], capture_output=True, text=True).stdout
    assert not left.strip(), f"editor left running: {left}"


@pytest.mark.lxc
@pytest.mark.parametrize("how", ["ctrl-c", "sigterm"])
def test_cleanup_at_ssh_password_prompt(shell, isolated_home, how):
    """X2 / TODO #10: ending sshdd while ssh waits for a password (Install on CT 213)."""
    import subprocess as sp
    ssh = isolated_home / ".ssh"
    sp.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(ssh / "k1")], check=True)
    (ssh / "config").write_text("Host ct\n    HostName 192.168.0.213\n    User testuser\n")
    marker = f"-x2-ssh-{how}"
    before = _tmp_files()
    shell.sendline(f"export HOME={isolated_home}")
    shell.expect_exact(PROMPT)
    _start(shell, marker)
    shell.send("I")
    shell.expect("Esc cancel")
    shell.send("k1\r")
    shell.expect("Select remote host", timeout=8)
    shell.send("ct\r")
    shell.expect("Remote username")
    shell.send("\r")
    shell.expect("password:", timeout=15)
    if how == "ctrl-c":
        shell.sendcontrol("c")
    else:
        os.kill(_pid(marker), signal.SIGTERM)
        time.sleep(1)
        shell.sendcontrol("c")                             # the waiting ssh, as a user would
    _assert_clean(shell, before)
    left = subprocess.run(["pgrep", "-s", str(shell.pid), "-f", "testuser@ct"], capture_output=True, text=True).stdout
    assert not left.strip(), f"ssh left running: {left}"


def test_temp_files_go_to_tmpdir(tmp_path):
    """#25: temp files go to $TMPDIR (per user on macOS); the per-test leak check relies on it."""
    src = " ".join(f"source {ROOT}/lib/bash/{m}.sh;" for m in ["tui", "ssh-config", "ssh-helpers"])
    r = subprocess.run([BASH32, "-c", f'{src} _mktemp_reg f .sshdd-x && echo "$f" && rm -f "$f"'],
                       env={"TMPDIR": f"{tmp_path}/", "PATH": "/usr/bin:/bin", "HOME": str(tmp_path)},
                       capture_output=True, text=True, timeout=30)
    assert r.stdout.startswith(f"{tmp_path}/.sshdd-x-"), r.stdout + r.stderr
