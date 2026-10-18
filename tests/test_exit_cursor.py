"""
TODO #9 / plan X3: after sshdd exits, the shell prompt is on the line right after the command's
output, in the real terminals Ahmad uses (tmux, herdr).

Each test runs, in a fresh shell:  clear; echo line-a; echo line-b; sshdd   → quit →
then asks the terminal where the cursor is (DSR 6). `clear` wipes the command line too, so rows: 1 line-a, 2 line-b,
3 the new prompt + our query command, so the query must report row 4.
herdr runs in a throwaway session (`herdr --session sshdd-test-x3`), never Ahmad's default one.
"""
import json
import os
import re
import shutil
import subprocess
import time

import pytest

from .screen import BASH32, ROOT

QUERY = r"""printf '\e[6n'; IFS= read -rs -d R p; echo "CUR=${p#*[}" """
RUN = f"clear; echo line-a; echo line-b; {BASH32} ./sshdd.sh"


def _home(tmp_path):
    ssh = tmp_path / ".ssh"
    ssh.mkdir(mode=0o700)
    (ssh / "config").write_text("")
    return str(tmp_path)


def _cursor_row(text):
    m = re.search(r"CUR=(\d+);(\d+)", text)
    assert m, f"no cursor report in:\n{text}"
    return int(m.group(1))


@pytest.mark.skipif(not shutil.which("tmux"), reason="tmux not installed")
@pytest.mark.parametrize("quit_key", ["Q", "C-c"])
def test_prompt_below_output_tmux(tmp_path, quit_key):
    tmux = ["tmux", "-L", f"sshdd-x3-{os.getpid()}"]
    env = dict(os.environ, HOME=_home(tmp_path))
    subprocess.run(tmux + ["new-session", "-d", "-x", "100", "-y", "30", "-c", ROOT,
                           f"{BASH32} --norc --noprofile -i"], env=env, check=True)
    try:
        time.sleep(0.5)
        subprocess.run(tmux + ["send-keys", RUN, "Enter"], check=True)
        time.sleep(2)
        subprocess.run(tmux + ["send-keys", quit_key], check=True)
        time.sleep(1.5)
        subprocess.run(tmux + ["send-keys", QUERY, "Enter"], check=True)
        time.sleep(1)
        out = subprocess.run(tmux + ["capture-pane", "-p"], capture_output=True, text=True).stdout
        assert _cursor_row(out) == 4, out
    finally:
        subprocess.run(tmux + ["kill-server"])


@pytest.mark.skipif(not shutil.which("herdr"), reason="herdr not installed")
def test_prompt_below_output_herdr(tmp_path):
    h = ["herdr", "--session", "sshdd-test-x3"]
    server = subprocess.Popen(h + ["server"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(1.5)
        ws = json.loads(subprocess.run(h + ["workspace", "create", "--label", "x3", "--no-focus", "--cwd", ROOT],
                                       capture_output=True, text=True, check=True).stdout)
        pane = ws["result"]["root_pane"]["pane_id"]

        def send(text):
            subprocess.run(h + ["pane", "send-text", pane, text], check=True)
            subprocess.run(h + ["pane", "send-keys", pane, "Enter"], check=True)

        time.sleep(1)
        send(f"export HOME={_home(tmp_path)}; {RUN}")
        time.sleep(2.5)
        subprocess.run(h + ["pane", "send-text", pane, "Q"], check=True)
        time.sleep(1.5)
        send(QUERY)
        time.sleep(1)
        out = subprocess.run(h + ["pane", "read", pane, "--source", "visible"], capture_output=True, text=True).stdout
        assert _cursor_row(out) == 4, out
    finally:
        subprocess.run(h + ["server", "stop"], capture_output=True)
        server.wait(timeout=10)
        subprocess.run(h[:1] + ["session", "delete", "sshdd-test-x3"], capture_output=True)


def test_starts_when_terminal_ignores_cursor_query(tmp_path):
    """The cursor-position query must never hang a terminal that doesn't answer it (plain pexpect doesn't)."""
    import pexpect
    env = dict(os.environ, HOME=_home(tmp_path), TERM="xterm-256color", LANG="en_US.UTF-8")
    t0 = time.time()
    c = pexpect.spawn(f"{BASH32} ./sshdd.sh", cwd=ROOT, env=env, encoding="utf-8", dimensions=(30, 100))
    try:
        c.expect("Quit", timeout=5)
        assert time.time() - t0 < 1.5
    finally:
        c.terminate(force=True)
