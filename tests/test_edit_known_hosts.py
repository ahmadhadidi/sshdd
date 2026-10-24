"""
TODO #37: S (Edit Known Hosts) opens the local ~/.ssh/known_hosts in $EDITOR, like E does for the config;
a missing file is reported, not created. EDITOR is a script that records the file it was given.
"""
import shutil
import time

import pytest

from .screen import Term, Tmux


def _edited(tmp_path, timeout=10):
    """The file the editor was given (sshdd returns to the menu at once, so "Done." only flashes)."""
    end = time.time() + timeout
    while time.time() < end and not (tmp_path / "edited").exists():
        time.sleep(0.1)
    return (tmp_path / "edited").read_text()


def _recorder(tmp_path):
    rec = tmp_path / "editor.sh"
    rec.write_text(f'#!/bin/sh\nprintf "%s" "$1" > "{tmp_path}/edited"\n')
    rec.chmod(0o755)
    return rec


@pytest.fixture
def home(isolated_home):
    (isolated_home / ".ssh" / "known_hosts").write_text("box ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDoesntMatterForThisTest\n")
    return isolated_home


def test_bash_opens_known_hosts_in_editor(home, tmp_path):
    with Term(home=home, env={"EDITOR": str(_recorder(tmp_path))}) as t:
        t.wait_for("Quit")
        t.press("S")
        assert _edited(tmp_path) == f"{home}/.ssh/known_hosts"
        t.wait_for("Up/Dn Navigate")                       # back on the menu


def test_bash_missing_known_hosts_is_reported(home, tmp_path):
    (home / ".ssh" / "known_hosts").unlink()
    with Term(home=home, env={"EDITOR": str(_recorder(tmp_path))}) as t:
        t.wait_for("Quit")
        t.press("S")
        t.wait_for("known_hosts not found")
        t.wait_for("Press any key")                        # the error stays until a key
    assert not (tmp_path / "edited").exists() and not (home / ".ssh" / "known_hosts").exists()


@pytest.mark.skipif(not (shutil.which("pwsh") and shutil.which("tmux")), reason="needs pwsh and tmux")
def test_powershell_opens_known_hosts_in_editor(home, tmp_path):
    env = {"HOME": str(home), "USERPROFILE": str(home), "EDITOR": str(_recorder(tmp_path))}
    with Tmux("pwsh -NoProfile -File ./sshdd.ps1", env=env) as t:
        t.wait_for("Quit", timeout=15)
        t.press("S")
        assert _edited(tmp_path).replace("\\", "/") == f"{home}/.ssh/known_hosts"
