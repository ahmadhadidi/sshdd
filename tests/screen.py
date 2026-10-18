"""
Screen-level harness: drives sshdd.sh under bash 3.2 with pexpect and renders its output
through pyte, so tests assert on what a terminal shows (text, cursor, colours), not raw bytes.

    with Term(home=tmp_path) as t:
        t.wait_for("Quit")
        t.press("G"); t.wait_for("Key name")
        print(t.text())
"""
import os
import time

import pexpect
import pyte

BASH32 = "/proj/bash32/bin/bash"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

KEYS = {"ESC": "\x1b", "ENTER": "\r", "UP": "\x1b[A", "DOWN": "\x1b[B", "BS": "\x7f"}


class Term:
    def __init__(self, args="", rows=40, cols=100, home=None, env=None):
        e = os.environ.copy()
        e.update({"TERM": "xterm-256color", "LANG": "en_US.UTF-8", "EDITOR": "/bin/true", "VISUAL": ""})
        if home:
            e["HOME"] = str(home)
        e.update(env or {})
        self.screen = pyte.Screen(cols, rows)
        self.stream = pyte.Stream(self.screen)
        self.child = pexpect.spawn(f"{BASH32} ./sshdd.sh {args}", cwd=ROOT, env=e,
                                   encoding="utf-8", dimensions=(rows, cols), timeout=10)
        # Answer terminal queries (cursor position, DSR) like a real terminal does.
        self.screen.write_process_input = self.child.send

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def pump(self, secs=0.2):
        """Feed everything the app printed within `secs` into the emulator."""
        end = time.time() + secs
        while True:
            try:
                self.stream.feed(self.child.read_nonblocking(65536, timeout=max(0.01, end - time.time())))
            except (pexpect.TIMEOUT, pexpect.EOF):
                if time.time() >= end or not self.child.isalive():
                    return

    def text(self):
        return "\n".join(line.rstrip() for line in self.screen.display)

    def wait_for(self, needle, timeout=5):
        end = time.time() + timeout
        while time.time() < end:
            self.pump(0.1)
            if needle in self.text():
                return
        raise AssertionError(f"{needle!r} not on screen after {timeout}s:\n{self.text()}")

    def press(self, *keys, gap=0.15):
        """Send keys (names from KEYS or literal text); `gap` covers the 100 ms ESC drain."""
        for k in keys:
            self.child.send(KEYS.get(k, k))
            self.pump(gap)

    def alive(self):
        return self.child.isalive()

    def close(self):
        """End the app like a closed terminal: SIGHUP to its whole process group. pexpect's
        terminate() hits only the bash pid, whose trap waits for the foreground child, so pexpect
        then SIGKILLs it and sshdd's cleanup never runs (T1 found the leftovers)."""
        import os
        import signal
        if self.child.isalive():
            try:
                os.killpg(os.getpgid(self.child.pid), signal.SIGHUP)
                self.child.expect(pexpect.EOF, timeout=3)
            except Exception:
                pass
        if self.child.isalive():
            self.child.terminate(force=True)
