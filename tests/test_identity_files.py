"""
TODO #17: IdentityFile lines are compared by whole path / file name, never as substrings.
Seen on a Mac: installing key "dev" to a host whose block had ~/.ssh/dev-lan said "IdentityFile
already exists" (grep -F substring) and didn't add it; "Using key:" showed the raw
"IdentityFile /path" line (sed's \\s is GNU-only, macOS sed left the line as it was).
"""
import shutil
import subprocess

import pytest

from .screen import BASH32, ROOT

LIBS = ["tui", "ssh-config", "ssh-helpers", "prompts", "ssh-ops"]
PS_LIBS = ["tui", "ssh-helpers", "ssh-config", "prompts", "ssh-ops"]


def _home(tmp_path, block_lines):
    ssh = tmp_path / ".ssh"
    ssh.mkdir()
    for k in ("dev", "dev-lan", "lan-dev"):
        (ssh / k).write_text("x")
        (ssh / f"{k}.pub").write_text(f"ssh-ed25519 AAAA {k}\n")
    (ssh / "config").write_text("Host dev-poc\n    HostName 192.168.0.204\n    User kraid\n"
                                + "".join(f"    {l}\n" for l in block_lines) + "\nHost other\n    HostName 10.0.0.9\n")
    return tmp_path


def _bash(home, snippet):
    src = " ".join(f"source {ROOT}/lib/bash/{m}.sh;" for m in LIBS)
    r = subprocess.run([BASH32, "-c", f'SSH_DIR="$HOME/.ssh"; SSH_CONFIG="$HOME/.ssh/config"; {src}\n{snippet}'],
                       env={"HOME": str(home), "PATH": "/usr/bin:/bin"}, capture_output=True, text=True, timeout=30)
    return r.stdout + r.stderr


def _block(home):
    return (home / ".ssh" / "config").read_text().split("Host other")[0]


def test_add_key_whose_name_prefixes_an_existing_one(tmp_path):
    home = _home(tmp_path, [f"IdentityFile {tmp_path}/.ssh/dev-lan"])
    out = _bash(home, "add_ssh_key_to_host_config dev dev-poc 192.168.0.204 kraid")
    assert "already exists" not in out, out
    assert f"IdentityFile {tmp_path}/.ssh/dev\n" in _block(home)
    assert f"IdentityFile {tmp_path}/.ssh/dev-lan\n" in _block(home)
    assert "Host other" in (home / ".ssh" / "config").read_text()


@pytest.mark.parametrize("line", ["IdentityFile {h}/.ssh/dev", "IdentityFile ~/.ssh/dev", "identityfile=\"~/.ssh/dev\"",
                                  "IdentityFile $HOME/.ssh/dev"])
def test_add_key_already_there_in_any_spelling(tmp_path, line):
    home = _home(tmp_path, [line.format(h=tmp_path)])
    before = _block(home)
    out = _bash(home, "add_ssh_key_to_host_config dev dev-poc 192.168.0.204 kraid")
    assert "already exists" in out, out
    assert _block(home) == before


def test_identity_files_are_values_only(tmp_path):
    home = _home(tmp_path, ["IdentityFile ~/.ssh/dev-lan", "identityfile=\"~/.ssh/lan-dev\"", "IDENTITYFILE\t/x/dev"])
    out = _bash(home, "get_identity_files_for_host dev-poc")
    assert out.splitlines() == ["~/.ssh/dev-lan", "~/.ssh/lan-dev", "/x/dev"]


def test_remove_only_the_exact_key_name(tmp_path):
    home = _home(tmp_path, ["IdentityFile ~/.ssh/dev-lan", "IdentityFile ~/.ssh/lan-dev", "IdentityFile ~/.ssh/dev"])
    _bash(home, "remove_identity_file_from_config_block dev dev-poc")
    block = _block(home)
    assert "/dev\n" not in block
    assert "~/.ssh/dev-lan" in block and "~/.ssh/lan-dev" in block, block


@pytest.mark.skipif(not shutil.which("pwsh"), reason="pwsh not installed")
def test_powershell_add_and_remove_exact(tmp_path):
    home = _home(tmp_path, [f"IdentityFile {tmp_path}/.ssh/dev-lan", "IdentityFile ~/.ssh/lan-dev"])
    libs = "; ".join(f". '{ROOT}/lib/ps/{m}.ps1'" for m in PS_LIBS)

    def ps(cmd):
        return subprocess.run(["pwsh", "-NoProfile", "-Command", f"$env:USERPROFILE = '{home}'; {libs}\n{cmd}"],
                              capture_output=True, text=True, timeout=60).stdout

    out = ps("Add-SSHKeyToHostConfig -KeyName dev -RemoteHostName dev-poc -RemoteHostAddress 192.168.0.204 -RemoteUser kraid")
    assert "already exists" not in out, out
    assert "/.ssh/dev\n" in _block(home).replace("\\", "/"), _block(home)
    out = ps("Add-SSHKeyToHostConfig -KeyName dev -RemoteHostName dev-poc -RemoteHostAddress 192.168.0.204 -RemoteUser kraid")
    assert "already exists" in out, out
    ps("Remove-IdentityFileFromConfigBlock -KeyName dev -HostAlias dev-poc")
    block = _block(home).replace("\\", "/")
    assert "/.ssh/dev\n" not in block and "/.ssh/dev-lan" in block and "~/.ssh/lan-dev" in block, block
