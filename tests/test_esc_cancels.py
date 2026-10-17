"""
TODO #1: Esc at any prompt cancels the operation and returns to the main menu, where a single Q quits.

Prompts read inside $(...) lose globals like _SELECT_CANCELLED, so callers must act on the return code;
these tests walk to prompts past the first one, where that was missed.
"""
import subprocess

import pytest

from .screen import Term

MAIN = "Up/Dn Navigate"


@pytest.fixture
def home(tmp_path):
    ssh = tmp_path / ".ssh"
    ssh.mkdir(mode=0o700)
    (ssh / "config").write_text("Host box\n    HostName 127.0.0.1\n    User root\n")
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(ssh / "k1")], check=True)
    return tmp_path


def _back_to_main_then_quit(t):
    t.pump(1)
    if "Press any key" in t.text():
        t.press("ENTER")
    t.wait_for(MAIN)
    t.press("Q")
    t.pump(1)
    assert not t.alive(), "one Q on the main menu must quit"


@pytest.mark.parametrize("hotkey", ["G", "W"])
def test_esc_at_key_comment_cancels(home, hotkey):
    """G (generate & install) and W (generate local): Esc at 'Key comment' must not go on to the passphrase."""
    with Term(home=home) as t:
        t.wait_for("Quit")
        t.press(hotkey)
        t.wait_for("Up/Dn navigate" if hotkey == "G" else "Enter SSH key name")   # G: key picker, W: name prompt
        t.press("brandnew", "ENTER")
        t.wait_for("Key comment")
        t.press("ESC")
        t.pump(1)
        assert "Passphrase" not in t.text()
        assert not (home / ".ssh" / "brandnew").exists()
        _back_to_main_then_quit(t)


def test_esc_on_host_list_cancels(home):
    """T: Esc on the host list cancels the operation (it used to claim 'Esc = enter manually')."""
    with Term(home=home) as t:
        t.wait_for("Quit")
        t.press("T")
        t.wait_for("Select remote host")
        t.press("ESC")
        _back_to_main_then_quit(t)


@pytest.mark.parametrize("typed,shown", [("10", "192.168.0.10"), ("203.0.113.9", "203.0.113.9"), ("newhost", "newhost")])
def test_typed_unknown_host_is_used_directly(home, typed, shown):
    """Typing an address that isn't configured goes straight on with it, no second prompt."""
    with Term(home=home, args="--subnet 192.168.0") as t:
        t.wait_for("Quit")
        t.press("T")
        t.wait_for("Select remote host")
        t.press(typed, "ENTER")
        t.wait_for("Remote username")
        assert "Enter remote IP" not in t.text()
        assert shown in t.text()
        t.press("ESC")
        _back_to_main_then_quit(t)


def test_generate_local_asks_for_a_new_name(home):
    """TODO #4: W asks for a new name (no picker of existing keys) and rejects bad or taken names."""
    with Term(home=home) as t:
        t.wait_for("Quit")
        t.press("W")
        t.wait_for("Enter SSH key name")
        assert "Select SSH key" not in t.text()
        t.press("k1", "ENTER")
        t.wait_for("already exists")
        t.press("bad name", "ENTER")
        t.wait_for("no spaces")
        t.press("fresh", "ENTER")
        t.wait_for("Key comment")
        t.press("ENTER")
        t.wait_for("Passphrase")
        t.press("ENTER")
        t.wait_for("generated")
        assert (home / ".ssh" / "fresh").exists() and (home / ".ssh" / "fresh.pub").exists()
