import pexpect
import os
import shutil
import subprocess
import pytest
import sys
import time

BASH32 = "/proj/bash32/bin/bash"

# ── T0/T1 (docs/TEST-PLAN.md): never touch the real ~/.ssh ─────────────────────
REAL_SSH = os.path.join(os.path.expanduser("~"), ".ssh")   # captured before any test changes HOME
LXC_HOST = "192.168.0.213"


def _snapshot(d):
    """Names, sizes, modes and mtimes of everything in d (non-recursive)."""
    if not os.path.isdir(d):
        return {}
    return {n: (st.st_size, st.st_mode, st.st_mtime_ns)
            for n in sorted(os.listdir(d)) for st in [os.lstat(os.path.join(d, n))]}


@pytest.fixture(scope="session", autouse=True)
def real_ssh_untouched():
    """T1: the whole run must leave the real ~/.ssh exactly as it was."""
    before = _snapshot(REAL_SSH)
    yield
    after = _snapshot(REAL_SSH)
    assert after == before, f"tests changed the real {REAL_SSH}: " + str(
        {k for k in before.keys() | after.keys() if before.get(k) != after.get(k)})


TMP_GLOBS = (".hprobe-*", ".ssh-askpass-*", ".sshdd-*")


@pytest.fixture(autouse=True)
def no_temp_files_left(tmp_path_factory, monkeypatch):
    """T1: sshdd removes its temp files however a test ends it (Term.close sends SIGHUP first).
    Checked per test so a leak names its test; waits up to 3 s for a probe still timing out.
    Each test gets its own TMPDIR (sshdd honours it), so parallel workers (xdist) don't see each other's files."""
    import glob
    import time
    tmp = tmp_path_factory.mktemp("tmpdir")
    monkeypatch.setenv("TMPDIR", str(tmp))
    def now():
        return {f for g in TMP_GLOBS for f in glob.glob(f"{tmp}/{g}")}
    before = now()
    yield
    end = time.time() + 3
    while (left := now() - before) and time.time() < end:
        time.sleep(0.2)
    assert not left, f"temp files left behind: {sorted(left)[:5]} ({len(left)})"


@pytest.fixture(autouse=True)
def isolated_home(tmp_path_factory, monkeypatch):
    """T0: every test gets a temp HOME with an empty ~/.ssh/config (600) and only CT 213's
    known_hosts entry, so remote tests don't stop at a host-key prompt."""
    home = tmp_path_factory.mktemp("home")
    ssh = home / ".ssh"
    ssh.mkdir(mode=0o700)
    (ssh / "config").write_text("")
    (ssh / "config").chmod(0o600)
    kh = os.path.join(REAL_SSH, "known_hosts")
    if os.path.exists(kh):
        entry = subprocess.run(["ssh-keygen", "-F", LXC_HOST, "-f", kh],
                               capture_output=True, text=True).stdout
        (ssh / "known_hosts").write_text("".join(l + "\n" for l in entry.splitlines() if not l.startswith("#")))
    monkeypatch.setenv("HOME", str(home))
    # OpenSSH ignores $HOME (it uses the passwd home dir), so without this the app's own
    # ssh/scp calls would read the real ~/.ssh/config and known_hosts. Wrappers first on PATH
    # point them at the temp HOME unless the caller already chose a config with -F.
    bin_dir = home / "bin"
    bin_dir.mkdir()
    for tool in ("ssh", "scp"):
        real = shutil.which(tool)
        w = bin_dir / tool
        w.write_text(
            "#!/bin/sh\n"
            # -F as its own argument: a remote command may contain the text "-F" (ssh-keygen -F).
            'for a; do [ "$a" = -F ] && exec ' + real + ' "$@"; done\n'
            "exec " + real + ' -F "$HOME/.ssh/config" -o UserKnownHostsFile="$HOME/.ssh/known_hosts" "$@"\n')
        w.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    return home

def end_like_terminal(child):
    """End an app the way a closing terminal does: SIGHUP to its whole process group, then wait.
    pexpect's own close() signals only the bash pid and SIGKILLs it ~0.2 s later, before sshdd's
    trap has run, so temp files were left (T1). SIGHUP is repeated: one that lands just before
    sshdd forks a $(...) prompt subshell misses that subshell, which then waits for input forever
    (a real hang-up also makes its tty read fail; an open pty doesn't)."""
    import signal
    for _ in range(6):
        if not child.isalive():
            return
        try:
            os.killpg(os.getpgid(child.pid), signal.SIGHUP)
            child.expect(pexpect.EOF, timeout=0.5)
        except Exception:
            pass
    if child.isalive():
        child.terminate(force=True)


@pytest.fixture
def run_tui():
    children = []
    def _run(args=""):
        script_path = "./sshdd.sh"
        env = os.environ.copy()
        env.update({"TERM": "xterm-256color", "LANG": "en_US.UTF-8", "EDITOR": "/bin/true", "VISUAL": ""})

        child = pexpect.spawn(f"{BASH32} {script_path} {args}", env=env, encoding='utf-8', timeout=10)
        child.setwinsize(40, 100)
        child.logfile = sys.stdout

        child.expect(["SSHDD -- axc.sh", "Quit"], timeout=10)

        time.sleep(0.5)
        children.append(child)
        return child
    yield _run
    for c in children:
        end_like_terminal(c)

@pytest.fixture
def run_tui_no_keys(tmp_path):
    children = []
    """Like run_tui but with an isolated temp HOME: no SSH keys, empty config.

    Guarantees the app always goes to the manual text prompt (not the
    select_from_list) when asking for a key name, making odd-input tests
    environment-independent.
    """
    def _run(args=""):
        ssh_dir = tmp_path / ".ssh"
        ssh_dir.mkdir(mode=0o700)
        config = ssh_dir / "config"
        config.write_text("")
        config.chmod(0o600)

        env = os.environ.copy()
        env.update({
            "TERM":   "xterm-256color",
            "LANG":   "en_US.UTF-8",
            "EDITOR": "/bin/true",
            "VISUAL": "",
            "HOME":   str(tmp_path),
        })
        child = pexpect.spawn(
            f"{BASH32} ./sshdd.sh {args}", env=env, encoding='utf-8', timeout=10
        )
        child.setwinsize(40, 100)
        child.logfile = sys.stdout
        child.expect(["SSHDD -- axc.sh", "Quit"], timeout=10)
        time.sleep(0.5)
        children.append(child)
        return child
    yield _run
    for c in children:
        end_like_terminal(c)

@pytest.fixture
def check_navigation():
    def _check(child, enter_key, expected_header):
        child.send(enter_key)
        child.expect(expected_header)
        time.sleep(0.2)
        child.send("\x1b")  # ESC
        child.expect("SSHDD -- axc.sh")
    return _check
