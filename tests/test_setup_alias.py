"""
TODO #29: setup/alias.sh and setup/alias.ps1 (the README's alias one-liners). Flags are optional; what's missing
is asked on the terminal (Enter keeps the default), or defaulted without one. Values of any characters reach
sshdd unchanged. rc file by login shell; local if ~/sshdd is cloned, else cloud; a rerun replaces the block.
"""
import os
import shutil
import subprocess

import pexpect
import pytest

from .screen import BASH32, ROOT

SH = f"{ROOT}/setup/alias.sh"
PS = f"{ROOT}/setup/alias.ps1"
ODD = "it's $HOME \"q\" `x` \\ ✏️"


def _home(tmp_path, local=True):
    if local:
        (tmp_path / "sshdd").mkdir()
        (tmp_path / "sshdd" / "sshdd.sh").write_text('printf "<%s>" "$@"\n')
        (tmp_path / "sshdd" / "sshdd.ps1").write_text('($args | ForEach-Object { "<$_>" }) -join ""\n')
    return tmp_path


def _bash(home, args=(), shell="/bin/bash", bash="bash", path="/usr/bin:/bin"):
    """No controlling terminal (new session): no questions, defaults for what isn't passed."""
    r = subprocess.run([bash, SH, *args], env={"HOME": str(home), "SHELL": shell, "PATH": path},
                       capture_output=True, text=True, timeout=30, start_new_session=True, stdin=subprocess.DEVNULL)
    assert r.returncode == 0, r.stderr
    return r.stdout


def _run_alias(home, rc, extra=""):
    r = subprocess.run(["bash", "-O", "expand_aliases", "-c", f"source {rc}\nsshdd {extra}"],
                       env={"HOME": str(home), "PATH": "/usr/bin:/bin"}, capture_output=True, text=True, timeout=30)
    return r.stdout


@pytest.mark.parametrize("bash", ["bash", BASH32])
def test_bash_flags_any_characters(tmp_path, bash):
    home = _home(tmp_path)
    out = _bash(home, ["--user", "kr aid", "--subnet", "10.0.0", "--comment-suffix", "-[HO'5]", "--password", ODD],
                bash=bash)
    assert "(local)" in out and "plain text" in out
    assert _run_alias(home, home / ".bashrc", "--verbose") == \
        f"<--user><kr aid><--subnet><10.0.0><--comment-suffix><-[HO'5]><--password><{ODD}><--verbose>"


def test_bash_no_terminal_uses_defaults_and_rerun_keeps_one_block(tmp_path):
    home = _home(tmp_path, local=False)
    (home / ".bashrc").write_text("export KEEP=1\n")
    assert "(cloud)" in _bash(home)
    _home(home)
    assert "(local)" in _bash(home)
    text = (home / ".bashrc").read_text()
    assert text.startswith("export KEEP=1\n") and text.count("# >>> sshdd >>>") == 1 and "curl" not in text
    assert (home / ".bashrc.sshdd-bak").exists()
    assert _run_alias(home, home / ".bashrc") == \
        "<--user><myuser><--subnet><192.168.0><--comment-suffix><-[my-machine]>"


def test_bash_rc_file_by_shell(tmp_path):
    home = _home(tmp_path)
    _bash(home, shell="/bin/zsh")
    assert (home / ".zshrc").read_text().count("alias sshdd=") == 1
    fake = home / "bin"
    fake.mkdir()
    (fake / "uname").write_text("#!/bin/sh\necho Darwin\n")
    (fake / "uname").chmod(0o755)
    _bash(home, path=f"{fake}:/usr/bin:/bin")
    assert "alias sshdd=" in (home / ".bash_profile").read_text()      # macOS bash: login shells
    assert not (home / ".bashrc").exists()


def test_bash_symlinked_rc_stays_a_symlink(tmp_path):
    home = _home(tmp_path)
    real = home / "dotfiles-bashrc"
    real.write_text("# mine\n")
    os.symlink(real, home / ".bashrc")
    _bash(home)
    assert (home / ".bashrc").is_symlink() and "alias sshdd=" in real.read_text()


def test_bash_asks_on_a_terminal_password_hidden(tmp_path):
    home = _home(tmp_path)
    c = pexpect.spawn("bash", [SH, "--subnet", "10.1.1"], env={"HOME": str(home), "SHELL": "/bin/bash",
                      "PATH": "/usr/bin:/bin"}, encoding="utf-8", timeout=10)
    c.expect_exact("Default remote username [myuser]: ")
    c.sendline("kraid")
    c.expect_exact("Key comment suffix [-[my-machine]]: ")      # --subnet given: not asked
    c.sendline("")
    c.expect_exact("SSH password (hidden, Enter = ask each time): ")
    c.sendline("s3cr3t")
    c.expect("Open a new terminal")
    assert "s3cr3t" not in c.before, "password was echoed"
    c.expect(pexpect.EOF)
    assert _run_alias(home, home / ".bashrc") == \
        "<--user><kraid><--subnet><10.1.1><--comment-suffix><-[my-machine]><--password><s3cr3t>"


def test_bash_rejects_unknown_and_missing_values(tmp_path):
    for args in (["--nope"], ["--user"]):
        r = subprocess.run(["bash", SH, *args], env={"HOME": str(tmp_path), "PATH": "/usr/bin:/bin"},
                           capture_output=True, text=True, start_new_session=True)
        assert r.returncode == 2 and not (tmp_path / ".bashrc").exists(), r.stderr


def _pwsh(home, cmd):
    r = subprocess.run(["pwsh", "-NoProfile", "-Command", cmd], env={"HOME": str(home), "PATH": os.environ["PATH"]},
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


@pytest.mark.skipif(not shutil.which("pwsh"), reason="pwsh not installed")
def test_powershell_params_any_characters_and_one_block(tmp_path):
    home = _home(tmp_path)
    odd = ODD.replace("'", "''")
    call = f"& '{PS}' -User 'kr aid' -Subnet 10.0.0 -CommentSuffix '-[HO''5]' -Password '{odd}'"
    assert "(local)" in _pwsh(home, call)
    _pwsh(home, call)
    profile = _pwsh(home, "$PROFILE")
    assert open(profile, encoding="utf-8-sig").read().count("# >>> sshdd >>>") == 1
    assert _pwsh(home, f". '{profile}'; sshdd") == \
        f"<-DefaultUserName><kr aid><-DefaultSubnetPrefix><10.0.0><-DefaultCommentSuffix><-[HO'5]><-DefaultPassword><{ODD}>"


def _expect_answering_dsr(c, text):
    """pwsh's line editor asks the terminal for the cursor position (ESC[6n); answer like a terminal does."""
    while c.expect_exact([text, "\x1b[6n"]) == 1:
        c.send("\x1b[1;1R")


@pytest.mark.skipif(not shutil.which("pwsh"), reason="pwsh not installed")
def test_powershell_asks_for_missing_values(tmp_path):
    home = _home(tmp_path)
    c = pexpect.spawn("pwsh", ["-NoProfile", "-File", PS, "-Subnet", "10.1.1"],
                      env={"HOME": str(home), "PATH": os.environ["PATH"], "TERM": "xterm-256color"},
                      encoding="utf-8", timeout=20)
    _expect_answering_dsr(c, "Default remote username [myuser]: ")
    c.sendline("kraid")
    _expect_answering_dsr(c, "Key comment suffix [-[my-machine]]: ")
    c.sendline("")
    _expect_answering_dsr(c, "SSH password (hidden, Enter = ask each time): ")
    c.sendline("")
    _expect_answering_dsr(c, "Open a new PowerShell window")
    profile = _pwsh(home, "$PROFILE")
    assert _pwsh(home, f". '{profile}'; sshdd") == \
        "<-DefaultUserName><kraid><-DefaultSubnetPrefix><10.1.1><-DefaultCommentSuffix><-[my-machine]>"


def test_readme_points_at_the_setup_scripts():
    text = open(f"{ROOT}/README.md").read()
    base = "https://raw.githubusercontent.com/ahmadhadidi/sshdd/refs/heads/main/"
    for f in ("setup/alias.sh", "setup/alias.ps1"):
        assert base + f in text and os.path.exists(f"{ROOT}/{f}")
