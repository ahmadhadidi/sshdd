"""
TODO #41: mouse in the bash TUI, like herdr. The terminal reports clicks (SGR: ESC[<b;col;rowM press, m release)
only while an sshdd screen reads keys: a click opens a menu item / chooses a list entry, the wheel scrolls,
releases and right/middle clicks do nothing. Capture is off before ssh, editors and text prompts, and on exit.
--no-mouse (and F5 Conf Defaults) switches it off.
"""
import re
import subprocess

import pytest

from .screen import BASH32, ROOT, Term

ON, OFF = "\x1b[?1000h", "\x1b[?1000l"


def _click(t, row, col=12, button=0):
    t.child.send(f"\x1b[<{button};{col};{row}M\x1b[<{button};{col};{row}m")


def _row_of(t, text):
    return next(i for i, l in enumerate(t.text().splitlines()) if text in l) + 1


class Raw:
    """Records everything the app wrote, escape codes included."""
    def __init__(self, t):
        self.parts, feed = [], t.stream.feed
        t.stream.feed = lambda s: (self.parts.append(s), feed(s))

    def text(self):
        return "".join(self.parts)


@pytest.fixture
def home(isolated_home):
    ssh = isolated_home / ".ssh"
    (ssh / "config").write_text("".join(f"Host box{i}\n    HostName 192.0.2.{i}\n" for i in range(1, 40)))
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(ssh / "k1")], check=True)
    return isolated_home


def test_menu_click_opens_and_wheel_moves(home):
    with Term(home=home) as t:
        raw = Raw(t)
        t.wait_for("Quit")
        t.pump(0.5)
        assert ON in raw.text() and "\x1b[?1006h" in raw.text(), "the menu should capture the mouse"
        t.child.send("\x1b[<65;10;10M")                    # wheel down: the selection moves to item 2
        t.pump(0.5)
        assert "\x1b[48;5;6m\x1b[1;97m    📤  Install SSH Key" in raw.text()
        _click(t, _row_of(t, "List Keys Locally"))
        t.wait_for("List SSH Keys")
        _click(t, _row_of(t, " k1 "), col=20)               # a click on a key row opens its viewer
        t.wait_for("View — k1")


def test_release_and_right_click_do_nothing(home):
    with Term(home=home) as t:
        t.wait_for("Quit")
        t.pump(0.5)
        row = _row_of(t, "List Keys Locally")
        t.child.send(f"\x1b[<0;12;{row}m")                  # a release alone
        _click(t, row, button=2)                            # right click
        t.pump(1.5)
        assert "List SSH Keys" not in t.text() and "Up/Dn Navigate" in t.text()


def test_no_mouse_flag(home):
    with Term(home=home, args="--no-mouse") as t:
        raw = Raw(t)
        t.wait_for("Quit")
        _click(t, _row_of(t, "List Keys Locally"))
        t.pump(1.5)
        assert ON not in raw.text(), "--no-mouse must not capture the mouse"
        assert "List SSH Keys" not in t.text()


def test_capture_off_before_editor_and_on_exit(home, tmp_path):
    ed = tmp_path / "ed.sh"
    ed.write_text("#!/bin/sh\nexit 0\n")
    ed.chmod(0o755)
    with Term(home=home, env={"EDITOR": str(ed)}) as t:
        raw = Raw(t)
        t.wait_for("Quit")
        t.pump(0.5)
        t.press("E")
        t.wait_for("Up/Dn Navigate")
        out = raw.text()
        opening = out.index("Opening in")
        assert out.rindex(OFF, 0, opening) > out.rfind(ON, 0, opening), "mouse still captured when the editor ran"
        raw.parts.clear()
        t.press("Q")
        t.pump(1)
        assert OFF in raw.text() and raw.text().rfind(ON) < raw.text().rindex(OFF), "capture left on after exit"


def test_picker_click_chooses_and_pager_wheel_scrolls(home):
    with Term(home=home) as t:
        t.wait_for("Quit")
        t.press("T")
        t.wait_for("Select remote host")
        t.pump(3)                                           # host probes time out after 2 s
        _click(t, _row_of(t, "box3  (192.0.2.3)"))
        t.wait_for("Remote username")
        assert "192.0.2.3" in t.text()
    with Term(home=home) as t:
        t.wait_for("Quit")
        t.press("V")
        t.wait_for("box1")
        first = t.text()
        t.child.send("\x1b[<65;10;12M" * 3)                 # wheel down three steps
        t.pump(1)
        assert t.text() != first and "Host box1\n" not in t.text().replace("  ", "")


def test_conf_defaults_click_switches_mouse_off(home):
    with Term(home=home) as t:
        raw = Raw(t)
        t.wait_for("Quit")
        t.press("\x1b[15~")                                 # F5
        t.wait_for("Run once")
        _click(t, _row_of(t, "Mouse"))
        t.wait_for("off  (Enter: on)")
        assert "--no-mouse" in t.text()
        raw.parts.clear()
        t.press("DOWN")
        t.pump(0.5)
        assert ON not in raw.text(), "switched off, the screen must not capture again"


@pytest.mark.parametrize("report,expect", [
    ("\x1b[<0;12;9M", "<click>:12:9"), ("\x1b[<64;1;1M", "\x1b[A::"), ("\x1b[<65;1;1M", "\x1b[B::"),
    ("\x1b[<4;3;4M", "<click>:3:4"),                        # Shift+click is still a click
    ("\x1b[<0;12;9m", "::"), ("\x1b[<2;12;9M", "::"), ("\x1b[<1;12;9M", "::"), ("\x1b[<x;1;1M", "::"),
    ("\x1b[A", "\x1b[A::"),                                 # not a mouse report: unchanged
])
def test_mouse_key_parsing(report, expect):
    snippet = f'source {ROOT}/lib/bash/tui.sh; SSHDD_MOUSE=1 KEY=$1; MOUSE_COL=; MOUSE_ROW=; _mouse_key\n' \
              'if [[ $KEY == "$KEY_CLICK" ]]; then printf "%s:%s:%s" "$KEY" "$MOUSE_COL" "$MOUSE_ROW"\n' \
              'else printf "%s::" "$KEY"; fi'
    out = subprocess.run([BASH32, "-c", snippet, "_", report], capture_output=True, text=True).stdout
    assert out == expect, repr(out)
