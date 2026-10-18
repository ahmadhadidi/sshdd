"""
Plan E5 / R6 / S5: remote failures end with one clear message, "Press any key", and the menu.

unreachable  TEST-NET address (no route): every remote op.
wrong pass   CT 213 with a wrong password (lxc).
hostkey      CT 213 under a known_hosts entry with a different key (lxc).
"""
import pytest

from .screen import Term

MAIN = "Up/Dn Navigate"


@pytest.fixture
def home(isolated_home):
    import subprocess
    ssh = isolated_home / ".ssh"
    for k in ("k1",):
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(ssh / k)], check=True)
    (ssh / "config").write_text("Host dead\n    HostName 192.0.2.77\n    User root\n    IdentityFile ~/.ssh/k1\n")
    return isolated_home


def _finish(t, timeout=25):
    import time
    end = time.time() + timeout
    while time.time() < end:
        t.pump(0.5)
        txt = t.text()
        if "Press any key" in txt:
            return txt
        cur = t.screen.display[t.screen.cursor.y].rstrip()
        if cur.endswith("password:"):
            t.press("wrong-pass\r")
        elif cur.endswith("[Y/n]") or cur.endswith("[y/N]"):
            t.press("n\r")
    raise AssertionError(f"no end of operation:\n{t.text()}")


# hotkey -> keys before the host picker
OPS = {"I": "k1\r", "T": "", "D": "", "Z": "", "N": "", "A": "k1\r"}


@pytest.mark.parametrize("hotkey", list(OPS))
def test_unreachable_host(home, hotkey):
    with Term(home=home, args="--user root") as t:
        t.wait_for("Quit")
        t.press(hotkey)
        if OPS[hotkey]:
            t.wait_for("Esc cancel")
            t.press(OPS[hotkey])
        t.wait_for("Select remote host", timeout=8)
        t.press("dead\r")
        t.wait_for("Remote username")
        t.press("\r")
        txt = _finish(t, timeout=40)
        low = txt.lower()
        assert any(w in low for w in ("unreachable", "not reachable", "could not", "failed", "refused",
                                      "timed out", "not accepting")), txt
        t.press("ENTER")
        t.wait_for(MAIN)


@pytest.mark.lxc
def test_reachability_without_gnu_timeout(home, tmp_path):
    """macOS has no `timeout`: the host list must still show CT 213 as reachable (green dot)."""
    import os
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "timeout").write_text("#!/bin/sh\nexit 127\n")          # like 'command not found'
    (fake / "timeout").chmod(0o755)
    (home / ".ssh" / "config").write_text("Host ct\n    HostName 192.168.0.213\n")
    with Term(home=home, env={"PATH": f"{fake}:{os.environ['PATH']}"}) as t:
        t.wait_for("Quit")
        t.press("T")
        t.wait_for("Select remote host", timeout=8)
        row = next(y for y, r in enumerate(t.screen.display) if "ct  (192.168.0.213)" in r)
        dot = next(c for c in t.screen.buffer[row].values() if c.data == "●")
        assert dot.fg == "green", f"CT shown unreachable (dot {dot.fg})"


def test_unreachable_gives_up_fast(home):
    """ConnectTimeout: an unreachable host ends the operation within ~15 s, not the TCP timeout."""
    import time
    with Term(home=home, args="--user root") as t:
        t.wait_for("Quit")
        t.press("Z")
        t.wait_for("Select remote host", timeout=8)
        t.press("dead\r")
        t.wait_for("Remote username")
        t0 = time.time()
        t.press("\r")
        _finish(t, timeout=40)
        assert time.time() - t0 < 16
