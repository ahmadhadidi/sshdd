"""
TODO #11: arrow keys respond at once and none are lost when held down.

The old escape-sequence drain waited out a 100 ms read timeout after every arrow (~126 ms per press)
and, with keys arriving faster than that, merged several arrows into one unknown key and dropped them.
"""
import statistics
import time

import pytest

from .screen import Term

SEL_BG = "00cdcd"   # selected menu row (\e[48;5;6m)


@pytest.fixture
def menu(tmp_path):
    ssh = tmp_path / ".ssh"
    ssh.mkdir(mode=0o700)
    (ssh / "config").write_text("")
    with Term(home=tmp_path) as t:
        t.child.delaybeforesend = None              # pexpect's default 50 ms would be measured too
        t.wait_for("Quit")
        t.pump(0.5)
        yield t


def _selected(t):
    for y in range(t.screen.lines):
        if t.screen.buffer[y][6].bg == SEL_BG:
            return t.screen.display[y].strip()
    return None


def test_held_down_arrow_moves_every_step(menu):
    assert "Generate & Install" in _selected(menu)
    for _ in range(5):                               # key-repeat speed, ~30/s
        menu.child.send("\x1b[B")
        time.sleep(0.033)
    menu.pump(1)
    assert "List Authorized Keys" in _selected(menu)  # 5th item below the first


@pytest.mark.serial   # a timing measurement: under xdist load the median reached 88 ms (#34)
def test_arrow_latency(menu):
    lats = []
    for _ in range(10):
        before = _selected(menu)
        t0 = time.time()
        menu.child.send("\x1b[B")
        while time.time() - t0 < 1 and _selected(menu) == before:
            menu.pump(0.002)
        lats.append(time.time() - t0)
        menu.pump(0.05)
    assert statistics.median(lats) < 0.08, f"median arrow latency {statistics.median(lats) * 1000:.0f} ms"
