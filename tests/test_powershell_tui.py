"""
Plan P1: the PowerShell TUI (sshdd.ps1) driven under pwsh in a real terminal (tmux): every hotkey
opens its screen, Esc / Enter bring it back to the menu, one Q quits. Hosts are unreachable
(TEST-NET), so no real SSH happens.
"""
import shutil
import subprocess

import pytest

from .screen import Tmux

pytestmark = pytest.mark.skipif(not (shutil.which("pwsh") and shutil.which("tmux")), reason="needs pwsh and tmux")
MAIN = "Up/Dn Navigate"
SCREENS = {   # hotkey -> words from the screen's title
    "G": "Generate & Install", "I": "Install SSH Key", "T": "Test SSH Connection", "D": "Delete SSH Key From",
    "P": "Promote Key", "Z": "List Authorized Keys", "N": "Add Config Block", "W": "Generate SSH Key",
    "L": "List SSH Keys", "A": "Append SSH Key", "X": "Delete an SSH Key Locally", "R": "Remove an SSH Key",
    "M": "Import SSH Key", "H": "Remove Host", "V": "View SSH Config",
}


@pytest.fixture
def home(isolated_home):
    ssh = isolated_home / ".ssh"
    (ssh / "config").write_text("".join(
        f"Host box{i}\n    HostName 192.0.2.{i}\n    User root\n    IdentityFile ~/.ssh/k1\n\n" for i in (1, 2)))
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(ssh / "k1")], check=True)
    return isolated_home


def _start(home):
    return Tmux("pwsh -NoProfile -File ./sshdd.ps1", env={"HOME": str(home), "USERPROFILE": str(home)})


def _back_to_menu(t):
    import time
    for _ in range(8):
        time.sleep(0.8)
        txt = t.text()
        if MAIN in txt and "Q Quit" in txt and "SSHDD" in txt:
            return
        t.press("ENTER" if "Press any key" in txt else "ESC")
    t.wait_for(MAIN, timeout=4)


@pytest.mark.parametrize("hotkey", list(SCREENS))
def test_powershell_every_screen(home, hotkey):
    with _start(home) as t:
        t.wait_for("Q Quit", timeout=15)
        t.press(hotkey)
        t.wait_for(SCREENS[hotkey], timeout=8)
        _back_to_menu(t)
        t.press("Q")
        import time
        time.sleep(1.5)
        assert not t.alive(), "one Q on the main menu must quit"
