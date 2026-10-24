"""
Plan S1, S4, S5, S8, S9, K2, K3: open every screen from the main menu at three terminal sizes,
check what is drawn, and leave it again.

Fixture: 3 hosts (TEST-NET, unreachable, so no real SSH) and 2 keys in a temp HOME.
"""
import subprocess

import pytest

from .screen import Term

SIZES = [(24, 80), (40, 100), (60, 200)]
MAIN = "Up/Dn Navigate"
# hotkey -> text the screen's title box shows
SCREENS = {
    "G": "Generate & Install", "I": "Install SSH Key", "T": "Test SSH Connection", "D": "Delete Remote SSH Key",
    "P": "Promote Key", "Z": "List Authorized Keys", "N": "Add Config Block", "W": "Generate Local SSH Key",
    "L": "List", "A": "Append Hostname", "X": "Delete Local SSH Key", "R": "Remove Config",
    "M": "Import Key", "H": "Remove Host", "V": "View",
    "O": "List Known Hosts on Remote", "B": "Forget Host Key on Remote", "K": "List Known Hosts", "F": "Forget Host Key", "S": "Edit Known Hosts",
    "\x1bOP": "Best Practices", "\x1b[15~": "Conf: Global Defaults",
}


@pytest.fixture
def home(tmp_path):
    ssh = tmp_path / ".ssh"
    ssh.mkdir(mode=0o700)
    (ssh / "config").write_text("".join(
        f"Host box{i}\n    HostName 192.0.2.{i}\n    User root\n    IdentityFile ~/.ssh/k{i % 2 + 1}\n\n" for i in range(1, 4)))
    (ssh / "config").chmod(0o600)
    for k in ("k1", "k2"):
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(ssh / k)], check=True)
    return tmp_path


def _last_col(t, y):
    """Screen column of the rightmost drawn cell (wide emoji take two cells, so use the buffer)."""
    line = t.screen.buffer[y]
    return max((x for x in range(t.screen.columns) if line[x].data.strip()), default=-1)


def _box_intact(t):
    """Title box: corners and side bars all end in the same column, inside the width."""
    rows = t.screen.display
    top = next((i for i, r in enumerate(rows) if r.lstrip().startswith("┌")), None)
    assert top is not None, "no title box"
    right = _last_col(t, top)
    assert t.screen.buffer[top][right].data == "┐"
    bot = next(i for i in range(top + 1, len(rows)) if rows[i].lstrip().startswith("└"))
    assert t.screen.buffer[bot][right].data == "┘", f"bottom corner off:\n{t.text()}"
    for y in range(top + 1, bot):
        assert t.screen.buffer[y][right].data == "│" and _last_col(t, y) == right, \
            f"box side broken on row {y}: {rows[y]!r}"
    return " ".join(rows[top:bot + 1])


def _settle_after_key(t, before, change=2.0, quiet=0.3):
    """Wait for the screen to react to a key (up to `change` s), then to stop changing for `quiet` s."""
    import time
    end = time.time() + change
    while t.text() == before and time.time() < end:
        t.pump(0.1)
    last, still = t.text(), time.time()
    while time.time() - still < quiet and time.time() < end + 3:
        t.pump(0.1)
        if t.text() != last:
            last, still = t.text(), time.time()


def _back_to_main(t):
    """One key at a time, the next only after the screen settled: with a fixed 0.6 s gap, a redraw slowed
    by load let a spare ENTER reach the main menu and open Generate & Install (#33)."""
    t.pump(0.6)
    for key in ("ESC", "ESC", "Q", "ENTER"):
        if MAIN in t.text() and "┌" in t.text() and "SSHDD" in t.text():
            return
        before = t.text()
        t.press("ENTER" if "Press any key" in before else key)
        _settle_after_key(t, before)
    t.wait_for(MAIN, timeout=4)


@pytest.mark.parametrize("rows,cols", SIZES, ids=lambda v: str(v))
@pytest.mark.parametrize("hotkey", list(SCREENS), ids=lambda k: repr(k))
def test_every_screen(home, hotkey, rows, cols):
    with Term(home=home, rows=rows, cols=cols) as t:
        t.wait_for("Quit")
        t.press(hotkey)
        t.pump(3)                                   # host probes time out after 2 s
        screen = t.screen.display
        title = _box_intact(t)
        assert SCREENS[hotkey] in title, f"title box doesn't say {SCREENS[hotkey]!r}:\n{t.text()}"
        bottom = " ".join(r for r in screen[-3:] if r.strip())
        assert any(w in bottom for w in ("Esc", "Q", "Enter", "Press any key", "Up/Dn", "Passphrase", "y/N")) \
            or any(w in t.text() for w in ("Esc", "Up/Dn", "Enter")), f"no key hints on screen:\n{t.text()}"
        _back_to_main(t)
        assert t.alive(), "app exited instead of returning to the menu"
        t.press("Q")
        t.pump(1)
        assert not t.alive(), "one Q on the main menu must quit"


@pytest.mark.parametrize("hotkey", [k for k in SCREENS if len(k) == 1])
def test_lowercase_hotkeys(home, hotkey):
    """K3: hotkeys work in lowercase too."""
    with Term(home=home) as t:
        t.wait_for("Quit")
        t.press(hotkey.lower())
        t.pump(2.5)
        assert SCREENS[hotkey] in t.text()


def test_unknown_keys_ignored(home):
    with Term(home=home) as t:
        t.wait_for("Quit")
        before = t.text()
        t.press("j", "K", "9", "%", "\x1b[24~", "\x1b[1;5A")   # unbound letters, F12, Ctrl+Up
        t.pump(0.5)
        assert t.alive() and t.text() == before


@pytest.mark.parametrize("rows,cols", SIZES, ids=lambda v: str(v))
def test_main_menu_scrolls_with_selection_visible(home, rows, cols):
    """S9: at 24 rows the menu scrolls; the highlighted item is always on screen."""
    with Term(home=home, rows=rows, cols=cols) as t:
        t.child.delaybeforesend = None
        t.wait_for("Quit")
        for i in range(25):
            t.press("DOWN", gap=0.05)
            t.pump(0.05)
            sel = [y for y in range(rows) if t.screen.buffer[y][6].bg == "00cdcd"]
            assert len(sel) == 1, f"step {i}: selection not visible:\n{t.text()}"


def test_edit_config_runs_editor_on_the_config(home, tmp_path):
    """E: runs $EDITOR on ~/.ssh/config, then back to the menu."""
    marker = tmp_path / "edited"
    editor = tmp_path / "ed.sh"
    editor.write_text(f'#!/bin/sh\nprintf "%s" "$1" > {marker}\n')
    editor.chmod(0o755)
    with Term(home=home, env={"EDITOR": str(editor)}) as t:
        t.wait_for("Quit")
        t.press("E")
        t.pump(2)
        assert marker.read_text() == str(home / ".ssh" / "config")
        _back_to_main(t)


def test_edit_config_with_editor_arguments(home, tmp_path):
    """E: EDITOR="cmd --wait" (VS Code style) gets the flag and the config path; checking the whole
    string used to fail and fall back to nano."""
    marker = tmp_path / "args"
    editor = tmp_path / "ed2.sh"
    editor.write_text(f'#!/bin/sh\nprintf "%s|" "$@" > {marker}\n')
    editor.chmod(0o755)
    with Term(home=home, env={"EDITOR": f"{editor} --wait"}) as t:
        t.wait_for("Quit")
        t.press("E")
        t.pump(2)
    assert marker.read_text() == f"--wait|{home / '.ssh' / 'config'}|"
