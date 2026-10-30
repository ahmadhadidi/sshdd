"""
TODO #48: a paste at the main menu (e.g. right-click in Windows Terminal) arrives as a burst of queued keys and
must not be read as hotkeys: "lq" pasted at once opens nothing and doesn't quit; a single typed key still works.
"""
import os
import shutil
import subprocess
import time

import pexpect
import pytest

from .screen import ROOT, Term
from .test_mouse_powershell import PsTerm


@pytest.fixture
def home(isolated_home):
    (isolated_home / ".ssh" / "config").write_text("Host box\n    HostName 192.0.2.5\n")   # not empty: #49
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(isolated_home / ".ssh" / "k1")], check=True)
    return isolated_home


def test_bash_paste_is_not_hotkeys(home):
    with Term(home=home) as t:
        t.wait_for("Quit")
        t.pump(0.5)
        t.child.send("lq\r")                                # one write, like a paste
        t.pump(1.5)
        assert t.alive(), "a pasted q quit sshdd"
        assert "Up/Dn Navigate" in t.text() and "List SSH Keys" not in t.text()
        t.child.send("l")                                   # typed on its own: still a hotkey
        t.wait_for("List SSH Keys")


@pytest.mark.skipif(not shutil.which("pwsh"), reason="pwsh not installed")
def test_powershell_paste_is_not_hotkeys(home):
    with PsTerm(home) as t:
        t.wait_for("Quit")
        t.pump(0.5)
        t.child.send("lq\r")
        t.pump(2)
        assert t.child.isalive(), "a pasted q quit sshdd"
        assert "Enter view key" not in t.text()
        t.child.send("l")
        t.wait_for("Enter view key")
