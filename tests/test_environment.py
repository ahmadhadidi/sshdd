"""
Plan E2–E4, X4, C2: sshdd in unusual environments, and terminal resizes.
"""
import os
import subprocess

import pytest

from .screen import Term
from .test_screens import _box_intact, home  # noqa: F401  (fixture: 3 hosts, 2 keys)
from .test_units import _no_perl_path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _empty_home(tmp_path, with_ssh=True):
    if with_ssh:
        (tmp_path / ".ssh").mkdir(mode=0o700)
    return tmp_path


# ── E2 ────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("answer,created", [("n", False), ("ESC", False), ("ENTER", True), ("y", True)])
@pytest.mark.parametrize("with_ssh", [True, False], ids=["no-config", "no-ssh-dir"])
def test_missing_config_prompt_waits_for_the_user(tmp_path, answer, created, with_ssh):
    home = _empty_home(tmp_path, with_ssh)
    cfg = home / ".ssh" / "config"
    with Term(home=home) as t:
        t.wait_for("[Y/n]")
        t.pump(1.5)                                  # used to answer itself within 100 ms
        assert not cfg.exists()
        t.press(answer)
        t.pump(1)
        assert cfg.exists() == created
        if created:
            assert oct(cfg.stat().st_mode & 0o777) == "0o600"
            assert oct(cfg.parent.stat().st_mode & 0o777) == "0o700"
            t.press("ENTER")
        t.wait_for("Quit")
        if not created:
            assert "press F2 to create it" in t.text()


def test_unreadable_config_warns_and_stays_quiet(tmp_path):
    home = _empty_home(tmp_path)
    cfg = home / ".ssh" / "config"
    cfg.write_text("Host a\n    HostName 1.1.1.1\n")
    cfg.chmod(0)
    with Term(home=home) as t:
        t.wait_for("Quit")
        assert "Can't read" in t.text() and "chmod 600" in t.text()
        t.press("T")
        t.pump(1.5)
        assert "awk" not in t.text() and "Permission denied" not in t.text()


# ── E3 ────────────────────────────────────────────────────────────────────────

def test_runs_without_perl(tmp_path, home):  # noqa: F811
    """No perl on PATH: menu works and host lists still come from the config (python3/awk)."""
    path = _no_perl_path(tmp_path)
    for tool in ("ssh-keygen", "ssh", "tput", "date", "od", "wc", "dd", "sleep", "timeout", "ls", "find", "sort",
                 "head", "tail", "cut", "uname", "hostname", "chmod", "mkdir", "touch", "id", "env"):
        src = subprocess.run(["sh", "-c", f"command -v {tool}"], capture_output=True, text=True).stdout.strip()
        if src and not os.path.exists(os.path.join(path, tool)):
            os.symlink(src, os.path.join(path, tool))
    with Term(home=home, env={"PATH": path}) as t:
        t.wait_for("Quit")
        t.press("T")
        t.wait_for("box1")


# ── E4 ────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("env,rows,cols", [({}, 10, 40), ({"TERM": "dumb"}, 40, 100), ({"TERM": "vt100"}, 24, 80),
                                           ({"LANG": "C", "LC_ALL": "C"}, 40, 100)])
def test_odd_terminals_start_and_quit(tmp_path, home, env, rows, cols):  # noqa: F811
    with Term(home=home, env=env, rows=rows, cols=cols) as t:
        t.wait_for("Quit")
        _box_intact(t)
        t.press("Q")
        t.pump(1)
        assert not t.alive()


# ── X4: resize ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("hotkey", ["", "L", "V", "\x1b[15~", "T"], ids=["menu", "keys", "view", "conf", "picker"])
@pytest.mark.parametrize("to", [(24, 80), (60, 200)])
def test_resize_redraws(home, hotkey, to):  # noqa: F811
    with Term(home=home, rows=40, cols=120) as t:
        t.wait_for("Quit")
        if hotkey:
            t.press(hotkey)
            t.pump(3)
        rows, cols = to
        t.screen.resize(rows, cols)
        t.child.setwinsize(rows, cols)             # sends SIGWINCH
        t.pump(1.5)
        if hotkey == "T":
            # A picker on an op screen redraws its own rows; the op's title box above is part of the
            # op transcript and is not redrawn. Its hint bar must fit the new width.
            assert any("Esc cancel" in r for r in t.screen.display)
        else:
            _box_intact(t)


# ── C2: cloud download failure ────────────────────────────────────────────────

def test_cloud_download_failure_is_one_clear_message(tmp_path):
    src = open(os.path.join(ROOT, "sshdd.sh")).read().replace(
        '_BASE_URL="https://raw.githubusercontent.com/ahmadhadidi/sshdd/refs/heads/main"',
        '_BASE_URL="http://127.0.0.1:9"')                 # discard port: connection refused
    script = tmp_path / "sshdd.sh"
    script.write_text(src)
    r = subprocess.run(["bash", str(script)], capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
    assert r.returncode == 1
    lines = [l for l in r.stderr.splitlines() if l.strip()]
    assert any("could not download" in l for l in lines) and len(lines) <= 3, r.stderr
