"""
TODO #14: List Authorized Keys, "All users": every user's ~/.ssh/authorized_keys, grouped by user,
keys numbered on through the list; needs root or passwordless sudo on the remote.
The remote command runs locally here (ssh replaced by sh -c), with fake id/getent/sudo.
"""
import re
import shutil
import subprocess

import pytest

from .screen import BASH32, ROOT

LIBS = ["tui", "ssh-config", "ssh-helpers", "prompts", "ssh-ops", "config-display", "menu"]
PS_LIBS = ["tui", "ssh-helpers", "ssh-config", "prompts", "ssh-ops", "config-display", "menu"]


@pytest.fixture
def remote(tmp_path):
    homes = {"root": "ssh-ed25519 AAAA r1\n", "kraid": "ssh-ed25519 AAAA k1\r\n\nssh-ed25519 AAAA k2",
             "testuser": "", "nobody": None}
    pw = []
    for u, keys in homes.items():
        h = tmp_path / u
        (h / ".ssh").mkdir(parents=True)
        if keys is not None:
            (h / ".ssh" / "authorized_keys").write_text(keys)
        pw.append(f"{u}:x:0:0::{h}:/bin/sh\n")
    (tmp_path / "passwd").write_text("".join(pw))
    b = tmp_path / "bin"
    b.mkdir()
    for name, body in {"id": 'echo "$FAKE_UID"', "getent": f'cat {tmp_path}/passwd',
                       "sudo": '[ "$FAKE_SUDO" = 1 ] || exit 1; shift; exec "$@"'}.items():
        (b / name).write_text("#!/bin/sh\n" + body + "\n")
        (b / name).chmod(0o755)
    return tmp_path


def _env(remote, uid, sudo):
    return {"HOME": str(remote), "PATH": f"{remote}/bin:/usr/bin:/bin", "FAKE_UID": uid, "FAKE_SUDO": sudo,
            "TERM": "dumb"}


def _plain(s):
    return [l.rstrip() for l in re.sub(r"\x1b\[[0-9;]*m", "", s).splitlines()]


def _bash(remote, uid="0", sudo="0"):
    src = " ".join(f"source {ROOT}/lib/bash/{m}.sh;" for m in LIBS)
    snippet = f'SSH_DIR="$HOME/.ssh"; {src}\nssh() {{ sh -c "$2"; }}; _list_all_authorized_keys box'
    r = subprocess.run([BASH32, "-c", snippet], env=_env(remote, uid, sudo), capture_output=True, text=True, timeout=30)
    return _plain(r.stdout + r.stderr)


def _ps(remote, uid="0", sudo="0"):
    libs = "; ".join(f". '{ROOT}/lib/ps/{m}.ps1'" for m in PS_LIBS)
    script = f"$env:USERPROFILE = '{remote}'; {libs}\nfunction ssh {{ sh -c $args[1] }}\nWrite-AllAuthorizedKeys box"
    r = subprocess.run(["pwsh", "-NoProfile", "-Command", script], env=_env(remote, uid, sudo),
                       capture_output=True, text=True, timeout=60)
    return _plain(r.stdout + r.stderr)


def _expected(remote):
    return ["Authorized keys on box:", "",
            f"root  {remote}/root/.ssh/authorized_keys", "1  ssh-ed25519 AAAA r1", "",
            f"kraid  {remote}/kraid/.ssh/authorized_keys", "2  ssh-ed25519 AAAA k1", "3  ssh-ed25519 AAAA k2", "",
            f"testuser  {remote}/testuser/.ssh/authorized_keys  (none)"]


def _listing(lines):
    i = next(n for n, l in enumerate(lines) if "Authorized keys on" in l)
    return [l.strip() for l in lines[i:]]


@pytest.mark.parametrize("uid,sudo", [("0", "0"), ("1000", "1")], ids=["root", "sudo"])
def test_bash_all_users_grouped(remote, uid, sudo):
    assert _listing(_bash(remote, uid, sudo)) == _expected(remote)


def test_bash_all_users_needs_root(remote):
    out = _bash(remote, "1000", "0")
    assert any("All users needs root or passwordless sudo on box." in l for l in out), out
    assert not any("Authorized keys on" in l for l in out)


@pytest.mark.skipif(not shutil.which("pwsh"), reason="pwsh not installed")
@pytest.mark.parametrize("uid,sudo", [("0", "0"), ("1000", "1")], ids=["root", "sudo"])
def test_powershell_all_users_grouped(remote, uid, sudo):
    assert _listing(_ps(remote, uid, sudo)) == _expected(remote)


@pytest.mark.skipif(not shutil.which("pwsh"), reason="pwsh not installed")
def test_powershell_all_users_needs_root(remote):
    out = _ps(remote, "1000", "0")
    assert any("All users needs root or passwordless sudo on box." in l for l in out), out
