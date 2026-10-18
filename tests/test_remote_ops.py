"""
Plan R1–R8: every remote operation end to end against CT 213 (sshdd-test on ho4), from the TUI.

Each test starts the CT user's authorized_keys from a known state (over password SSH), runs one
operation through the screen harness, then checks the remote file and the local config.
Password prompts come from sshdd's askpass; the test types the CT password (sshpass isn't used).
"""
import subprocess

import pytest

from .screen import Term
from .test_lxc_connection import LXC_HOST, LXC_PASS, LXC_USER, _ssh_run

pytestmark = pytest.mark.lxc

ALIAS = "sshdd-e2e"
KEEP = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKeepKeepKeepKeepKeepKeepKeepKeepKeepKeep keep-me"


def _remote_keys():
    r = _ssh_run("cat ~/.ssh/authorized_keys 2>/dev/null; echo MODE=$(stat -c %a ~/.ssh/authorized_keys)")
    return r.stdout.decode()


def _set_remote_keys(*lines):
    data = "".join(l.rstrip("\n") + "\n" for l in lines).encode()
    r = _ssh_run("mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat > ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys",
                 stdin_data=data)
    assert r.returncode == 0, r.stderr


@pytest.fixture
def ct(isolated_home):
    """Temp HOME with keys k1, k2 and a config block for the CT; CT starts with only KEEP."""
    ssh = isolated_home / ".ssh"
    for k in ("k1", "k2"):
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", f"{k}-e2e", "-f", str(ssh / k)], check=True)
    (ssh / "config").write_text(f"Host {ALIAS}\n    HostName {LXC_HOST}\n    User {LXC_USER}\n")
    _set_remote_keys(KEEP)
    yield isolated_home
    _set_remote_keys(KEEP)


def _pub(home, k):
    return (home / ".ssh" / f"{k}.pub").read_text().split()[1]


def _answer_password(t, until="Press any key", timeout=20, yes_no="y"):
    """Type the CT password whenever ssh asks, answer [Y/n] questions, stop when `until` shows."""
    import time
    end = time.time() + timeout
    while time.time() < end:
        t.pump(0.5)
        txt = t.text()
        if until in txt:
            return txt
        last = txt.rstrip()
        if last.endswith("password:"):
            t.press(LXC_PASS + "\r")
        elif last.endswith("[Y/n]") or last.endswith("[y/N]"):
            t.press(yes_no + "\r")
    raise AssertionError(f"{until!r} didn't show:\n{t.text()}")


def _pick_host(t):
    t.wait_for("Select remote host", timeout=8)
    t.press(ALIAS + "\r")
    t.wait_for("Remote username")
    t.press("\r")


def test_install_existing_key(ct):
    """I: k1 lands in authorized_keys once; KEEP stays; mode 600."""
    with Term(home=ct, args=f"--user {LXC_USER}") as t:
        t.wait_for("Quit")
        t.press("I")
        t.wait_for("Esc cancel")
        t.press("k1\r")
        _pick_host(t)
        _answer_password(t)                     # "Add 'k1' as IdentityFile ...? [Y/n]" -> y
    keys = _remote_keys()
    assert keys.count(_pub(ct, "k1")) == 1 and KEEP in keys and "MODE=600" in keys
    # D1: the config gained exactly the IdentityFile line; nothing else changed
    cfg = (ct / ".ssh" / "config").read_text()
    assert cfg.replace(f"    IdentityFile {ct}/.ssh/k1\n", "").replace("    IdentityFile ~/.ssh/k1\n", "") == \
        f"Host {ALIAS}\n    HostName {LXC_HOST}\n    User {LXC_USER}\n", cfg


def test_install_twice_adds_once(ct):
    """R7: installing a key that's already there doesn't duplicate it."""
    _set_remote_keys(KEEP, (ct / ".ssh" / "k1.pub").read_text())
    with Term(home=ct, args=f"--user {LXC_USER}") as t:
        t.wait_for("Quit")
        t.press("I")
        t.wait_for("Esc cancel")
        t.press("k1\r")
        _pick_host(t)
        _answer_password(t)
    assert _remote_keys().count(_pub(ct, "k1")) == 1


def test_list_authorized_keys(ct):
    """Z: shows the CT's keys (comments)."""
    _set_remote_keys(KEEP, (ct / ".ssh" / "k2.pub").read_text())
    with Term(home=ct, args=f"--user {LXC_USER}") as t:
        t.wait_for("Quit")
        t.press("Z")
        _pick_host(t)
        txt = _answer_password(t)
    assert "keep-me" in txt and "k2-e2e" in txt


def test_delete_remote_key(ct):
    """D: removes only the chosen key; KEEP stays; mode stays 600."""
    _set_remote_keys(KEEP, (ct / ".ssh" / "k1.pub").read_text(), (ct / ".ssh" / "k2.pub").read_text())
    with Term(home=ct, args=f"--user {LXC_USER}") as t:
        t.wait_for("Quit")
        t.press("D")
        _pick_host(t)
        _answer_password(t, until="Select key to remove")
        t.press("k1\r")
        _answer_password(t, timeout=30, yes_no="n")   # keep the local key files
    keys = _remote_keys()
    assert _pub(ct, "k1") not in keys and _pub(ct, "k2") in keys and KEEP in keys and "MODE=600" in keys


def test_test_connection_with_installed_key(ct):
    """T: a key in authorized_keys tests as working; one that isn't, as not authorized."""
    _set_remote_keys(KEEP, (ct / ".ssh" / "k1.pub").read_text())
    for key, want in (("k1", "successful"), ("k2", "not authorized")):
        with Term(home=ct, args=f"--user {LXC_USER}") as t:
            t.wait_for("Quit")
            t.press("T")
            _pick_host(t)
            t.wait_for("Esc cancel", timeout=8)
            t.press(key + "\r")
            txt = _answer_password(t)
            assert want in txt.lower() or want in txt, txt


def test_install_when_last_line_has_no_newline(ct):
    """The new key must not be glued onto a last line that lacks its newline."""
    r = _ssh_run("printf '%s' \"$K\" > ~/.ssh/authorized_keys".replace("$K", KEEP))
    assert r.returncode == 0
    with Term(home=ct, args=f"--user {LXC_USER}") as t:
        t.wait_for("Quit")
        t.press("I")
        t.wait_for("Esc cancel")
        t.press("k1\r")
        _pick_host(t)
        _answer_password(t, yes_no="n")
    lines = _remote_keys().splitlines()
    assert KEEP in lines and any(l.split()[1:2] == [_pub(ct, "k1")] for l in lines), lines
