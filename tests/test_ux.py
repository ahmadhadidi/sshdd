"""
Plan S6, S8, S9, K5: what the screens promise works.

S6  --user / --subnet / --comment-suffix appear pre-filled where they apply.
S8  "?" help pages with Enter and closes with Q.
K5  View Config pager: PgDn / PgUp / End / Home move the view.
S9  a picker with 60 hosts filters, scrolls, and keeps the highlight on screen.
"""
import pytest

from .screen import Term

SEL_BG = "00cdcd"


def _home(tmp_path, config=""):
    ssh = tmp_path / ".ssh"
    ssh.mkdir(mode=0o700, exist_ok=True)
    (ssh / "config").write_text(config)
    (ssh / "config").chmod(0o600)
    return tmp_path


def test_defaults_prefilled(tmp_path):
    home = _home(tmp_path)
    with Term(home=home, args="--user bob --subnet 10.1.2 --comment-suffix -[lab]") as t:
        t.wait_for("Quit")
        t.press("T")
        t.wait_for("10.1.2.xx")                       # subnet named in the manual-entry prompt
        t.press("7\r")
        t.wait_for("10.1.2.7")                         # shorthand resolved with --subnet
        t.wait_for("Remote username")
        assert t.screen.display[t.screen.cursor.y].rstrip().endswith("bob")
        t.press("ESC")
        t.pump(1)
        if "Press any key" in t.text():
            t.press("ENTER")
        t.wait_for("Up/Dn Navigate")
        t.press("W")
        t.wait_for("Enter SSH key name")
        t.press("lab1\r")
        t.wait_for("Key comment")
        assert t.screen.display[t.screen.cursor.y].rstrip().endswith("lab1-[lab]")


def test_help_pages_and_closes(tmp_path):
    with Term(home=_home(tmp_path), rows=24, cols=100) as t:
        t.wait_for("Quit")
        t.press("?")
        t.wait_for("lines shown")
        first = t.text()
        t.press("ENTER")
        t.pump(0.5)
        assert t.text() != first, "Enter didn't page"
        t.press("Q")
        t.wait_for("Up/Dn Navigate")


def test_view_config_pager_keys(tmp_path):
    cfg = "".join(f"Host h{i:03d}\n    HostName 10.0.{i // 250}.{i % 250 + 1}\n\n" for i in range(150))
    with Term(home=_home(tmp_path, cfg), rows=24, cols=100) as t:
        t.wait_for("Quit")
        t.press("V")
        t.wait_for("h000")

        def shown():
            return [r for r in t.screen.display if "Host h" in r]
        top = shown()[0]
        t.press("\x1b[6~")                             # PgDn
        t.pump(0.4)
        assert shown()[0] != top, "PgDn didn't scroll"
        t.press("\x1b[F")                              # End
        t.pump(0.4)
        assert any("h149" in r for r in shown()), "End didn't reach the bottom"
        t.press("\x1b[H")                              # Home
        t.pump(0.4)
        assert shown()[0] == top, "Home didn't return to the top"
        t.press("ESC")
        t.wait_for("Up/Dn Navigate")


def test_picker_with_many_hosts(tmp_path):
    cfg = "".join(f"Host box{i:02d}\n    HostName 192.0.2.{i + 1}\n\n" for i in range(60))
    with Term(home=_home(tmp_path, cfg), rows=24, cols=100) as t:
        t.child.delaybeforesend = None
        t.wait_for("Quit")
        t.press("T")
        t.wait_for("Esc cancel", timeout=8)
        for _ in range(30):                            # scroll well past one screen
            t.press("DOWN", gap=0.03)
        t.pump(0.6)
        sel = [y for y in range(24) if t.screen.buffer[y][4].bg == SEL_BG]
        assert len(sel) == 1 and "box30" in t.screen.display[sel[0]], t.text()
        t.press("box4", gap=0.05)                       # filter: box04, box40..box49
        t.pump(0.5)
        listed = [r for r in t.screen.display if "box" in r and "(" in r]
        assert listed and all("box4" in r or "box04" in r for r in listed), listed
        t.press("ESC")
