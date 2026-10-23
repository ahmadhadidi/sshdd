"""
TODO #31: the Conf Defaults screen (bash F5, PowerShell F10) shows the setup/alias one-liners with the current
values. Each line is copied off the screen as displayed (wrapped, with continuation characters), run, and the
alias it writes must pass the values through unchanged. curl / irm are stubbed to serve the repo's own scripts.
"""
import os
import shutil
import subprocess
import time

import pytest

from .screen import ROOT, Term, Tmux

RAW = "https://raw.githubusercontent.com/ahmadhadidi/sshdd/refs/heads/main/"
VALUES = {"user": "kr aid", "subnet": "10.0.0", "suffix": "-[HO'5]", "password": "p w"}


def _block(screen, start, stop):
    lines = screen.splitlines()
    i = next(n for n, l in enumerate(lines) if start in l)
    out = []
    for l in lines[i + 1:]:
        if stop in l:
            break
        out.append(l.strip())
    return "\n".join(out)


def _home(tmp_path):
    (tmp_path / ".ssh").mkdir(exist_ok=True)
    (tmp_path / ".ssh" / "config").write_text("")
    (tmp_path / "sshdd").mkdir()
    (tmp_path / "sshdd" / "sshdd.sh").write_text('printf "<%s>" "$@"\n')
    (tmp_path / "sshdd" / "sshdd.ps1").write_text('($args | ForEach-Object { "<$_>" }) -join ""\n')
    return tmp_path


def _check_bash_line(line, home):
    assert RAW + "setup/alias.sh" in line.replace("\\\n", "").replace("\n", "")
    fake = home / "fakebin"
    fake.mkdir(exist_ok=True)
    (fake / "curl").write_text(f'#!/bin/sh\nfor a; do u=$a; done\ncat "{ROOT}/${{u#{RAW}}}"\n')
    (fake / "curl").chmod(0o755)
    r = subprocess.run(["bash", "-c", line], env={"HOME": str(home), "SHELL": "/bin/bash",
                       "PATH": f"{fake}:/usr/bin:/bin"}, capture_output=True, text=True, timeout=30,
                       start_new_session=True, stdin=subprocess.DEVNULL)
    assert r.returncode == 0, r.stderr
    out = subprocess.run(["bash", "-O", "expand_aliases", "-c", f"source {home}/.bashrc\nsshdd"],
                         env={"HOME": str(home), "PATH": "/usr/bin:/bin"}, capture_output=True, text=True).stdout
    v = VALUES
    assert out == (f"<--user><{v['user']}><--subnet><{v['subnet']}><--comment-suffix><{v['suffix']}>"
                   f"<--password><{v['password']}>"), out


def _check_ps_line(line, home):
    assert RAW + "setup/alias.ps1" in line.replace("`\n", "").replace("\n", "")
    stub = f"function irm($u) {{ Get-Content -Raw (Join-Path '{ROOT}' $u.Substring({len(RAW)})) }}\n"
    env = {"HOME": str(home), "PATH": os.environ["PATH"]}
    r = subprocess.run(["pwsh", "-NoProfile", "-NonInteractive", "-Command", stub + line], env=env,
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    profile = subprocess.run(["pwsh", "-NoProfile", "-Command", "$PROFILE"], env=env, capture_output=True,
                             text=True).stdout.strip()
    out = subprocess.run(["pwsh", "-NoProfile", "-Command", f". '{profile}'; sshdd"], env=env, capture_output=True,
                         text=True).stdout.strip()
    v = VALUES
    assert out == (f"<-DefaultUserName><{v['user']}><-DefaultSubnetPrefix><{v['subnet']}>"
                   f"<-DefaultCommentSuffix><{v['suffix']}><-DefaultPassword><{v['password']}>"), out


@pytest.mark.skipif(not shutil.which("pwsh"), reason="pwsh not installed")
def test_bash_screen_setup_lines_run_as_shown(tmp_path):
    home = _home(tmp_path)
    v = VALUES
    args = f"--user '{v['user']}' --subnet {v['subnet']} --comment-suffix \"{v['suffix']}\" --password '{v['password']}'"
    with Term(home=home, args=args, cols=100) as t:
        t.wait_for("Quit")
        t.press("\x1b[15~")                                   # F5
        t.wait_for("Run once")
        screen = t.text()
    _check_bash_line(_block(screen, "macOS / Linux", "Windows (PowerShell)"), home)
    _check_ps_line(_block(screen, "Windows (PowerShell)", "Run once"), home)


@pytest.mark.skipif(not (shutil.which("pwsh") and shutil.which("tmux")), reason="needs pwsh and tmux")
def test_powershell_screen_setup_lines_run_as_shown(tmp_path):
    home = _home(tmp_path)
    v = VALUES
    cmd = (f"pwsh -NoProfile -File ./sshdd.ps1 -DefaultUserName '{v['user']}' -DefaultSubnetPrefix {v['subnet']} "
           f"-DefaultCommentSuffix \"{v['suffix']}\" -DefaultPassword '{v['password']}'")
    with Tmux(cmd, env={"HOME": str(home), "USERPROFILE": str(home)}) as t:
        t.wait_for("Quit", timeout=15)
        t.press("F10")
        t.wait_for("Run once", timeout=10)
        time.sleep(0.5)
        screen = t.text()
    _check_bash_line(_block(screen, "macOS / Linux", "Windows (PowerShell)"), home)
    _check_ps_line(_block(screen, "Windows (PowerShell)", "Run once"), home)
