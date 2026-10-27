"""
TODO #42: mouse in the PowerShell TUI, like bash #41. On macOS/Linux pwsh the terminal's SGR reports reach
Read-TuiKey one character at a time; a click opens a menu item / list entry, the wheel scrolls, releases and
right/middle clicks do nothing; capture is off for operations and on exit; -NoMouse and F10 switch it off.
Windows reads mouse records through a C# ReadConsoleInput reader: only its compiling is checked here.
"""
import os
import shutil
import subprocess
import tempfile
import time

import pexpect
import pyte
import pytest

from .screen import ROOT

pytestmark = pytest.mark.skipif(not shutil.which("pwsh"), reason="pwsh not installed")
ON, OFF = "\x1b[?1000h", "\x1b[?1000l"


class PsTerm:
    """sshdd.ps1 in a pty with a pyte screen (answers cursor-position queries like a terminal)."""
    def __init__(self, home, args=(), env=None):
        e = dict(os.environ, HOME=str(home), USERPROFILE=str(home), TERM="xterm-256color", SSH_CONNECTION="")
        e.update(env or {})
        self.screen, self.raw = pyte.Screen(100, 40), []
        self.stream = pyte.Stream(self.screen)
        self.child = pexpect.spawn("pwsh", ["-NoProfile", "-File", "./sshdd.ps1", *args], cwd=ROOT, env=e,
                                   encoding="utf-8", dimensions=(40, 100), timeout=20)
        self.screen.write_process_input = self.child.send

    def pump(self, secs):
        end = time.time() + secs
        while time.time() < end:
            try:
                d = self.child.read_nonblocking(65536, timeout=0.1)
                self.raw.append(d)
                self.stream.feed(d)
            except pexpect.TIMEOUT:
                pass
            except pexpect.EOF:
                return

    def text(self):
        return "\n".join(l.rstrip() for l in self.screen.display)

    def wait_for(self, needle, timeout=15):
        end = time.time() + timeout
        while time.time() < end:
            self.pump(0.2)
            if needle in self.text():
                return
        raise AssertionError(f"{needle!r} not on screen:\n{self.text()}")

    def row_of(self, text):
        return next(i for i, l in enumerate(self.screen.display) if text in l) + 1

    def click(self, row, col=12, button=0):
        self.child.send(f"\x1b[<{button};{col};{row}M\x1b[<{button};{col};{row}m")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.child.terminate(force=True)


@pytest.fixture
def home(tmp_path):
    (tmp_path / ".ssh").mkdir()
    (tmp_path / ".ssh" / "config").write_text("".join(f"Host box{i}\n    HostName 192.0.2.{i}\n" for i in (1, 2, 3)))
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(tmp_path / ".ssh" / "k1")], check=True)
    return tmp_path


def test_read_tui_key_turns_reports_into_keys(tmp_path):
    script = tmp_path / "rtk.ps1"
    script.write_text(f". '{ROOT}/lib/ps/tui.ps1'\n$script:SshddMouse = $true\n'READY'\n"
                      "for ($i = 0; $i -lt 4; $i++) { while (-not (Test-TuiInput)) { Start-Sleep -Milliseconds 10 }\n"
                      "  $k = Read-TuiKey; \"GOT $($k.VirtualKeyCode)/$($k.Click)/$($k.Col)/$($k.Row)\" }\n")
    c = pexpect.spawn("pwsh", ["-NoProfile", "-File", str(script)], encoding="utf-8", timeout=15)
    c.expect("READY")
    for seq in ("\x1b[<0;12;9M\x1b[<0;12;9m",   # click (+ release, skipped)
                "\x1b[<2;5;5M\x1b[<2;5;5m",     # right click: skipped entirely
                "\x1b[<65;1;1M", "\x1b[<64;1;1M", "x"):
        c.send(seq)
        time.sleep(0.4)
    c.expect(pexpect.EOF)
    got = [l.split("GOT ")[1].strip() for l in c.before.splitlines() if "GOT " in l]
    assert got == ["0/True/12/9", "40/False/0/0", "38/False/0/0", "88//0/0"] or \
        got == ["0/True/12/9", "40/False/0/0", "38/False/0/0", "88///"], got


def test_menu_click_opens_and_capture_off_for_the_operation(home):
    with PsTerm(home) as t:
        t.wait_for("Quit")
        t.pump(0.5)
        assert ON in "".join(t.raw), "the menu should capture the mouse"
        t.raw.clear()
        t.click(t.row_of("List SSH Keys"))
        t.wait_for("Enter view key")
        assert OFF in "".join(t.raw)


def test_no_mouse_switch(home):
    with PsTerm(home, args=["-NoMouse"]) as t:
        t.wait_for("Quit")
        t.click(t.row_of("List SSH Keys"))
        t.pump(2)
        assert ON not in "".join(t.raw) and "Enter view key" not in t.text()


def test_picker_click_chooses(home):
    with PsTerm(home) as t:
        t.wait_for("Quit")
        t.child.send("T")
        t.wait_for("box2")
        t.pump(3)                                           # host probes time out
        t.click(t.row_of("box2  (192.0.2.2)"))
        t.wait_for("Remote username")
        assert "192.0.2.2" in t.text()


def test_f10_click_switches_mouse_off(home):
    with PsTerm(home) as t:
        t.wait_for("Quit")
        t.child.send("\x1b[21~")                            # F10
        t.wait_for("Run once")
        t.click(t.row_of("Mouse"))
        t.wait_for("off  (Enter: on)")
        assert "-NoMouse" in t.text().replace("\n", " ")


def test_title_click_opens_axc_sh_locally(home, tmp_path):
    b = tmp_path / "bin"
    b.mkdir()
    (b / "xdg-open").write_text(f'#!/bin/sh\nprintf "%s" "$1" > "{tmp_path}/opened"\n')
    (b / "xdg-open").chmod(0o755)
    with PsTerm(home, env={"PATH": f"{b}:{os.environ['PATH']}"}) as t:
        t.wait_for("Quit")
        t.click(3, col=50)
        end = time.time() + 5
        while time.time() < end and not (tmp_path / "opened").exists():
            t.pump(0.2)
    assert (tmp_path / "opened").read_text() == "https://axc.sh"


def test_windows_reader_compiles():
    out = subprocess.run(["pwsh", "-NoProfile", "-Command", f". '{ROOT}/lib/ps/tui.ps1'; Test-WinConsole"],
                         capture_output=True, text=True, timeout=60).stdout.strip()
    assert out == "True"


def test_alias_ps1_no_mouse_is_passed_on(tmp_path):
    (tmp_path / "sshdd").mkdir()
    (tmp_path / "sshdd" / "sshdd.ps1").write_text('($args | ForEach-Object { "<$_>" }) -join ""\n')
    env = {"HOME": str(tmp_path), "PATH": os.environ["PATH"]}
    run = lambda cmd: subprocess.run(["pwsh", "-NoProfile", "-Command", cmd], env=env, capture_output=True,
                                     text=True, timeout=60).stdout.strip()
    run(f"& '{ROOT}/setup/alias.ps1' -User u -Subnet 10.0.0 -CommentSuffix x -Password '' -NoMouse")
    profile = run("$PROFILE")
    assert run(f". '{profile}'; sshdd").endswith("<-NoMouse>")
