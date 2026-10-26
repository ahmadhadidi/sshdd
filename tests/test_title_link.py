"""
TODO #44: "axc.sh" in the main title links to https://axc.sh: an OSC 8 terminal link (bash and PowerShell), and in
bash a click on the title (mouse, #41) opens it with open/xdg-open, but only when sshdd runs locally (over SSH the
browser would open on the remote machine). The title still renders as before (test_main_menu_look checks centring).
"""
import os
import shutil
import time

import pexpect
import pytest

from .screen import ROOT, Term

LINK = "\x1b]8;;https://axc.sh\x1b\\axc.sh\x1b]8;;\x1b\\"


def _opener(tmp_path):
    d = tmp_path / "bin"
    d.mkdir()
    (d / "xdg-open").write_text(f'#!/bin/sh\nprintf "%s" "$1" > "{tmp_path}/opened"\n')
    (d / "xdg-open").chmod(0o755)
    return f"{d}:{os.environ['PATH']}"


def _title_click(isolated_home, tmp_path, ssh_connection):
    with Term(home=isolated_home, env={"PATH": _opener(tmp_path), "SSH_CONNECTION": ssh_connection}) as t:
        raw = []
        feed = t.stream.feed
        t.stream.feed = lambda s: (raw.append(s), feed(s))
        t.wait_for("Quit")
        t.pump(0.5)
        t.child.send("\x1b[<0;50;4M\x1b[<0;50;4m")      # the title row
        end = time.time() + 3
        while time.time() < end and not (tmp_path / "opened").exists():
            t.pump(0.1)
        assert "Up/Dn Navigate" in t.text(), "a title click must not open a menu item"
    return "".join(raw)


def test_bash_title_is_a_link_and_a_click_opens_it(isolated_home, tmp_path):
    raw = _title_click(isolated_home, tmp_path, "")
    assert LINK in raw
    assert (tmp_path / "opened").read_text() == "https://axc.sh"


def test_bash_title_click_over_ssh_opens_nothing(isolated_home, tmp_path):
    _title_click(isolated_home, tmp_path, "192.0.2.9 50000 192.0.2.1 22")
    time.sleep(0.5)
    assert not (tmp_path / "opened").exists()


@pytest.mark.skipif(not shutil.which("pwsh"), reason="pwsh not installed")
def test_powershell_title_is_a_link(isolated_home):
    env = dict(os.environ, HOME=str(isolated_home), USERPROFILE=str(isolated_home), TERM="xterm-256color")
    c = pexpect.spawn("pwsh", ["-NoProfile", "-File", "./sshdd.ps1"], cwd=ROOT, env=env, encoding="utf-8",
                      dimensions=(40, 100), timeout=20)
    try:
        while c.expect_exact(["Quit", "\x1b[6n"]) == 1:     # answer cursor-position queries like a terminal
            c.send("\x1b[1;1R")
        assert LINK in c.before
    finally:
        c.terminate(force=True)
