"""
TODO #24: the README's alias installers. Each block is taken from README.md as written and run in a temp HOME:
rc file by login shell, local if ~/sshdd is cloned else cloud, a rerun replaces the marked block, symlinks stay.
"""
import os
import re
import shutil
import subprocess

import pytest

from .screen import BASH32, ROOT


def _block(lang):
    text = open(f"{ROOT}/README.md").read()
    alias = text.split("### Alias")
    sec = alias[1] if lang == "bash" else alias[2]
    return re.search(rf"```{lang}\n(.*?)```", sec, re.S).group(1)


def _run_bash(home, shell="/bin/bash", bash="bash"):
    env = {"HOME": str(home), "SHELL": shell, "PATH": "/usr/bin:/bin"}
    r = subprocess.run([bash, "-c", "set -o noclobber\n" + _block("bash")], env=env, capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    return r.stdout


def _alias_output(home, rc):
    """Source the rc and run the alias with an extra option; the fake sshdd.sh echoes its arguments."""
    env = {"HOME": str(home), "PATH": "/usr/bin:/bin"}
    r = subprocess.run(["bash", "-O", "expand_aliases", "-c", f"source {rc}\nsshdd --verbose"],
                       env=env, capture_output=True, text=True, timeout=30)
    return r.stdout.strip()


@pytest.mark.parametrize("bash", ["bash", BASH32])
def test_bash_cloud_then_local_one_block(tmp_path, bash):
    rc = tmp_path / ".bashrc"
    rc.write_text("export KEEP=1\n")
    assert "(cloud)" in _run_bash(tmp_path, bash=bash)
    assert "raw.githubusercontent.com" in rc.read_text()
    (tmp_path / "sshdd").mkdir()
    (tmp_path / "sshdd" / "sshdd.sh").write_text('echo "ARGS $*"\n')
    assert "(local)" in _run_bash(tmp_path, bash=bash)
    assert "(local)" in _run_bash(tmp_path, bash=bash)
    text = rc.read_text()
    assert text.startswith("export KEEP=1\n")
    assert text.count("# >>> sshdd >>>") == 1 and "curl" not in text
    assert (tmp_path / ".bashrc.sshdd-bak").exists()
    assert _alias_output(tmp_path, rc) == "ARGS --user myuser --subnet 192.168.0 --comment-suffix -[my-machine] --verbose"


def test_zsh_login_shell_writes_zshrc(tmp_path):
    assert "/.zshrc" in _run_bash(tmp_path, shell="/bin/zsh")
    assert (tmp_path / ".zshrc").read_text().count("alias sshdd=") == 1
    assert not (tmp_path / ".bashrc").exists()


def test_symlinked_rc_stays_a_symlink(tmp_path):
    real = tmp_path / "dotfiles" / "bashrc"
    real.parent.mkdir()
    real.write_text("# mine\n")
    os.symlink(real, tmp_path / ".bashrc")
    _run_bash(tmp_path)
    assert (tmp_path / ".bashrc").is_symlink()
    assert "alias sshdd=" in real.read_text()


@pytest.mark.skipif(not shutil.which("pwsh"), reason="pwsh not installed")
def test_powershell_cloud_then_local_one_block(tmp_path):
    env = {"HOME": str(tmp_path), "PATH": os.environ["PATH"]}

    def run(cmd):
        r = subprocess.run(["pwsh", "-NoProfile", "-Command", cmd], env=env, capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr
        return r.stdout

    assert "(cloud)" in run(_block("powershell"))
    (tmp_path / "sshdd").mkdir()
    (tmp_path / "sshdd" / "sshdd.ps1").write_text('"ARGS $args"\n')
    run(_block("powershell"))
    assert "(local)" in run(_block("powershell"))
    profile = run("$PROFILE").strip()
    text = open(profile).read()
    assert text.count("# >>> sshdd >>>") == 1 and "irm" not in text
    assert run(f". '{profile}'; sshdd -Verbose").strip() == \
        "ARGS -DefaultUserName myuser -DefaultSubnetPrefix 192.168.0 -DefaultCommentSuffix -[my-machine] -Verbose"
