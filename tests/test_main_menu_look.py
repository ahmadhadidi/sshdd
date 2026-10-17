"""
Main menu look, asserted on the rendered screen (pyte):
  TODO #13: title box reads '🌊 SSHDD -- axc.sh', centred.
  TODO #2:  the F-key bar has the same background (reverse video) as the hint bar below it.
"""
import pytest

from .screen import Term


@pytest.mark.parametrize("cols", [80, 100, 140])
def test_title_and_bars(tmp_path, cols):
    ssh = tmp_path / ".ssh"
    ssh.mkdir(mode=0o700)
    (ssh / "config").write_text("")
    with Term(home=tmp_path, rows=40, cols=cols) as t:
        t.wait_for("Quit")
        t.pump(0.5)
        rows = t.screen.display
        title = next(r for r in rows if "SSHDD -- axc.sh" in r)
        inner = title.strip()[1:-1]                      # between the box's │ borders
        left, right = len(inner) - len(inner.lstrip()), len(inner) - len(inner.rstrip())
        assert abs(left - right) <= 2, f"title not centred: {left} vs {right}"
        assert "HDD SSH Keys Manager" not in t.text()

        fbar, hint = t.screen.buffer[38], t.screen.buffer[39]
        assert "F1 Best Practices" in rows[38] and "Up/Dn Navigate" in rows[39]
        for name, row in (("F-key bar", fbar), ("hint bar", hint)):
            plain = [x for x in range(cols) if not row[x].reverse]
            assert not plain, f"{name}: columns without the bar background: {plain[:10]}"
