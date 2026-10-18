"""
Plan K1, D3, S5: walk every operation prompt by prompt.

K1  Esc at any prompt of any operation returns to the menu and changes nothing in ~/.ssh.
D3  deleting a local key needs an explicit yes; Enter alone keeps it (and keeps it on remote hosts).
S5  an error (e.g. empty import path) stays on screen behind "Press any key".
Hosts are TEST-NET (unreachable): no real SSH happens.
"""
import hashlib
import subprocess

import pytest

from .screen import Term

MAIN = "Up/Dn Navigate"
PICK = "Esc cancel"   # every picker's hint bar

# hotkey -> [(text that shows the prompt is up, keys that answer it)]; the last prompt needs no answer
FLOWS = {
    "G": [(PICK, "newk\r"), ("Key comment", "\r"), ("Passphrase", None)],
    "W": [("Enter SSH key name", "newk\r"), ("Key comment", "\r"), ("Passphrase", None)],
    "I": [(PICK, "\r"), ("Select remote host", "\r"), ("Remote username", None)],
    "T": [("Select remote host", "\r"), ("Remote username", None)],
    "D": [("Select remote host", "\r"), ("Remote username", None)],
    "Z": [("Select remote host", "\r"), ("Remote username", None)],
    "N": [("Select remote host", "\r"), ("Remote username", None)],
    "A": [(PICK, "\r"), ("Select remote host", "\r"), ("Remote username", None)],
    "P": [(PICK, "\r"), (PICK, "\r"), (PICK, None)],
    "X": [(PICK, "\r"), ("Also remove it", "\r"), ("Delete", None)],
    "R": [(PICK, "\r"), (PICK, None)],
    "M": [(PICK, "\r"), ("Path to private key file", None)],
    "H": [(PICK, "\r"), ("Remove this block", None)],
}
CASES = [(hk, depth) for hk, steps in FLOWS.items() for depth in range(len(steps))]


@pytest.fixture
def home(tmp_path):
    ssh = tmp_path / ".ssh"
    ssh.mkdir(mode=0o700)
    (ssh / "config").write_text("".join(
        f"Host box{i}\n    HostName 192.0.2.{i}\n    User root\n    IdentityFile ~/.ssh/k{i % 2 + 1}\n\n" for i in (1, 2)))
    (ssh / "config").chmod(0o600)
    for k in ("k1", "k2"):
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(ssh / k)], check=True)
    return tmp_path


def _snapshot(home):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (home / ".ssh").iterdir() if p.is_file() and p.name != "known_hosts"}


def _walk(t, hotkey, depth):
    t.wait_for("Quit")
    t.press(hotkey)
    for text, answer in FLOWS[hotkey][:depth]:
        t.wait_for(text, timeout=6)
        t.press(answer)
    t.wait_for(FLOWS[hotkey][depth][0], timeout=6)


def _back_at_menu(t):
    t.pump(1.5)
    if "Press any key" in t.text():
        t.press("ENTER")
    t.wait_for(MAIN, timeout=5)


@pytest.mark.parametrize("hotkey,depth", CASES, ids=[f"{h}-{d}" for h, d in CASES])
def test_esc_at_every_prompt(home, hotkey, depth):
    before = _snapshot(home)
    with Term(home=home) as t:
        _walk(t, hotkey, depth)
        t.press("ESC")
        _back_at_menu(t)
        assert _snapshot(home) == before, "Esc changed ~/.ssh"
        t.press("Q")
        t.pump(1)
        assert not t.alive()


def test_delete_local_key_needs_explicit_yes(home):
    """D3: pick k1, Enter on the remote list (None is highlighted), Enter at the confirmation: kept."""
    with Term(home=home) as t:
        _walk(t, "X", 2)
        t.press("\r")
        _back_at_menu(t)
    assert (home / ".ssh" / "k1").exists() and (home / ".ssh" / "k1.pub").exists()


def test_delete_local_key_with_yes(home):
    with Term(home=home) as t:
        _walk(t, "X", 2)
        t.press("y\r")
        t.wait_for("removed locally")
    assert not (home / ".ssh" / "k1").exists()
    assert (home / ".ssh" / "k2").exists()


def test_error_stays_on_screen(home):
    """S5: an empty import path is an error; it must stay readable behind "Press any key"."""
    with Term(home=home) as t:
        _walk(t, "M", 1)
        t.press("\r")
        t.wait_for("Path is required")
        t.wait_for("Press any key")


def test_esc_at_passphrase_makes_no_key(home):
    """read_secret: Esc at the passphrase cancels; a plain `read -s` used to take Esc as a character."""
    with Term(home=home) as t:
        _walk(t, "W", 2)
        t.press("abc", "ESC")
        _back_at_menu(t)
    assert not (home / ".ssh" / "newk").exists()


def test_passphrase_with_backspace(home):
    with Term(home=home) as t:
        _walk(t, "W", 2)
        t.press("pass", "BS", "s", "word\r")
        t.wait_for("generated")
    r = subprocess.run(["ssh-keygen", "-y", "-P", "password", "-f", str(home / ".ssh" / "newk")], capture_output=True)
    assert r.returncode == 0, r.stderr
