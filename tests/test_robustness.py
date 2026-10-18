"""
Plan H3, K6, S3, E5 (rest): sshdd under odd input and remote failures.

H3  random text (control chars, unicode, shell syntax, a $(touch canary) payload) into free-text
    prompts: no crash, nothing executed, back to the menu.
K6  a 2 KB paste into a prompt.
S3  the spinner shows while hosts are probed and is gone afterwards.
E5  wrong password / changed host key on CT 213: a clear message, then the menu.
"""
import subprocess

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from .screen import Term

MAIN = "Up/Dn Navigate"
FUZZ = settings(max_examples=12, deadline=None, suppress_health_check=list(HealthCheck))
nasty = st.one_of(
    st.text(alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00\r\n\x1b\x03\x1a\x15\x17"),
            max_size=60),
    st.sampled_from(["'", '"', "$(touch {c})", "`touch {c}`", "; touch {c}", "\\", "%s%n", "../../x", " " * 40]),
)


def _home(tmp_path):
    ssh = tmp_path / ".ssh"
    ssh.mkdir(mode=0o700, exist_ok=True)
    (ssh / "config").write_text("")
    return tmp_path


def _to_menu(t):
    import time
    for _ in range(6):
        t.pump(0.7)
        if MAIN in t.text() and "Q Quit" in t.text():
            return
        t.press("ENTER" if "Press any key" in t.text() else "ESC")
    t.wait_for(MAIN)


@FUZZ
@given(text=nasty)
def test_fuzz_key_comment(tmp_path_factory, text):
    home = _home(tmp_path_factory.mktemp("h3"))
    canary = home / "canary"
    text = text.replace("{c}", str(canary))
    with Term(home=home) as t:
        t.wait_for("Quit")
        t.press("W")
        t.wait_for("Enter SSH key name")
        t.press("fz1\r")
        t.wait_for("Key comment")
        t.press("\x15", text, "\r", gap=0.05)
        t.wait_for("Passphrase")
        t.press("\r")
        t.wait_for("Press any key", timeout=10)
        _to_menu(t)
        assert t.alive()
    assert not canary.exists(), "comment text was executed"
    pub = (home / ".ssh" / "fz1.pub")
    assert pub.exists()


@FUZZ
@given(text=nasty)
def test_fuzz_host_entry(tmp_path_factory, text):
    home = _home(tmp_path_factory.mktemp("h3h"))
    canary = home / "canary"
    text = text.replace("{c}", str(canary))
    with Term(home=home) as t:
        t.wait_for("Quit")
        t.press("T")
        t.wait_for("Enter remote IP")
        t.press(text, "\r", gap=0.05)
        t.pump(1)
        _to_menu(t)
        assert t.alive()
    assert not canary.exists(), "host text was executed"


def test_paste_into_comment(tmp_path):
    """K6: an 800-char paste (an RSA-4096 public key is ~750) arrives whole. Input costs ~6 ms per
    character (bash read -n1 per key), so a 2 KB paste takes ~13 s: a known limit."""
    home = _home(tmp_path)
    big = ("abcdefghij" * 80)[:800]
    with Term(home=home) as t:
        t.wait_for("Quit")
        t.press("W")
        t.wait_for("Enter SSH key name")
        t.press("pst\r")
        t.wait_for("Key comment")
        t.press("\x15")
        t.child.send(big)                              # one write, like a paste
        t.pump(1)
        t.press("\r")
        t.wait_for("Passphrase", timeout=20)
        t.press("\r")
        t.wait_for("generated", timeout=10)
    assert (home / ".ssh" / "pst.pub").read_text().rstrip("\n").split(" ", 2)[2] == big


def test_spinner_shows_then_clears(tmp_path):
    home = _home(tmp_path)
    (home / ".ssh" / "config").write_text("Host a\n    HostName 192.0.2.1\nHost b\n    HostName 192.0.2.2\n")
    with Term(home=home) as t:
        t.wait_for("Quit")
        t.press("T")
        t.wait_for("Checking host availability", timeout=3)
        t.wait_for("Select remote host", timeout=6)
        t.pump(0.5)
        assert "Checking host availability" not in t.text()


# ── E5 on CT 213 ──────────────────────────────────────────────────────────────

@pytest.fixture
def ct_home(isolated_home):
    ssh = isolated_home / ".ssh"
    (ssh / "config").write_text("Host ct\n    HostName 192.168.0.213\n    User testuser\n")
    return isolated_home


def _list_keys_on_ct(t, password_answers):
    import time
    t.wait_for("Quit")
    t.press("Z")
    t.wait_for("Select remote host", timeout=8)
    t.press("ct\r")
    t.wait_for("Remote username")
    t.press("\r")
    end = time.time() + 40
    while time.time() < end:
        t.pump(0.5)
        if "Press any key" in t.text():
            return t.text()
        if t.screen.display[t.screen.cursor.y].rstrip().endswith("password:"):
            t.press(password_answers + "\r")
    raise AssertionError(t.text())


@pytest.mark.lxc
def test_wrong_password_message(ct_home):
    with Term(home=ct_home, args="--user testuser") as t:
        txt = _list_keys_on_ct(t, "not-the-password")
        assert "Failed" in txt or "denied" in txt.lower(), txt
        _to_menu(t)


def _ct_with_fake_known_key(ct_home):
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(ct_home / "fakehost")], check=True)
    pub = (ct_home / "fakehost.pub").read_text().split()
    (ct_home / ".ssh" / "known_hosts").write_text(f"192.168.0.213 {pub[0]} {pub[1]}\n")


@pytest.mark.lxc
def test_changed_host_key_message(ct_home):
    """A known_hosts entry with a different key: sshdd says so before connecting (TODO #15);
    keeping the old key cancels the operation."""
    _ct_with_fake_known_key(ct_home)
    with Term(home=ct_home, args="--user testuser") as t:
        t.wait_for("Quit")
        t.press("Z")
        t.wait_for("Select remote host", timeout=8)
        t.press("ct\r")
        t.wait_for("retry? [y/N]", timeout=15)
        assert "Host key for 192.168.0.213 (ct) changed" in t.text(), t.text()
        t.press("n\r")
        t.wait_for(MAIN)


@pytest.mark.lxc
def test_changed_host_key_forget_then_connects(ct_home):
    """The recreated-CT case end to end: forget the old key, ssh records the new one, the op runs."""
    _ct_with_fake_known_key(ct_home)
    with Term(home=ct_home, args="--user testuser") as t:
        t.wait_for("Quit")
        t.press("Z")
        t.wait_for("Select remote host", timeout=8)
        t.press("ct\r")
        t.wait_for("retry? [y/N]", timeout=15)
        t.press("y\r")
        t.wait_for("Remote username")
        t.press("\r")
        end = __import__("time").time() + 40
        while "Press any key" not in t.text():
            assert __import__("time").time() < end, t.text()
            t.pump(0.5)
            if t.screen.display[t.screen.cursor.y].rstrip().endswith("password:"):
                t.press("testpass\r")
        assert "Authorized keys on" in t.text() or "No authorized_keys" in t.text(), t.text()
    kh = (ct_home / ".ssh" / "known_hosts").read_text()
    assert (ct_home / "fakehost.pub").read_text().split()[1] not in kh


def test_ctrl_s_does_not_freeze(tmp_path):
    """Ctrl+S (XOFF) used to stop all output until Ctrl+Q: the app looked hung (found by H3)."""
    with Term(home=_home(tmp_path)) as t:
        t.wait_for("Quit")
        t.press("\x13")
        t.press("T")
        t.wait_for("Enter remote IP", timeout=4)
        t.press("\x13", "10")
        t.wait_for("10", timeout=3)


def test_c1_control_dropped_unicode_kept(tmp_path):
    """U+009D (bytes C2 9D) passed the control check byte by byte and was echoed; terminals then
    swallowed all later output as an OSC string (found by H3). Whole UTF-8 characters still work."""
    home = _home(tmp_path)
    with Term(home=home) as t:
        t.wait_for("Quit")
        t.press("W")
        t.wait_for("Enter SSH key name")
        t.press("c1\r")
        t.wait_for("Key comment")
        t.press("\x15", "a\x9dé", "\r", gap=0.05)
        t.wait_for("Passphrase")
        t.press("\r")
        t.wait_for("Press any key", timeout=10)
    assert (home / ".ssh" / "c1.pub").read_text().rstrip("\n").split(" ", 2)[2] == "aé"
