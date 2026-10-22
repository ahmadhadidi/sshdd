"""
TODO #20: a name typed in the host picker that isn't in ~/.ssh/config asks for the address, and
Install SSH Key names the new config block after that name (not the remote's hostname).
The UI pieces and ssh are stubbed; _prompt_remote / Invoke-RemotePrompt and the install run for real.
"""
import shutil
import subprocess

import pytest

from .screen import BASH32, ROOT

LIBS = ["tui", "ssh-config", "ssh-helpers", "prompts", "ssh-ops", "config-display", "menu"]
PS_LIBS = ["tui", "ssh-helpers", "ssh-config", "prompts", "ssh-ops", "config-display", "menu"]


@pytest.fixture
def home(tmp_path):
    ssh = tmp_path / ".ssh"
    ssh.mkdir(mode=0o700)
    (ssh / "config").write_text("Host box\n    HostName 10.0.0.5\n    User root\n")
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(ssh / "k1")], check=True)
    return tmp_path


def _block(home):
    text = (home / ".ssh" / "config").read_text()
    return text[text.index("Host claude-ho4"):] if "Host claude-ho4" in text else text


def test_bash_new_name_becomes_the_alias(home):
    src = " ".join(f"source {ROOT}/lib/bash/{m}.sh;" for m in LIBS)
    snippet = (f'SSH_DIR="$HOME/.ssh"; SSH_CONFIG="$HOME/.ssh/config"; DEFAULT_SUBNET_PREFIX=192.168.0; {src}\n'
               'select_from_list() { _SELECT_CANCELLED=0; _SELECT_RESULT=claude-ho4; }\n'
               'read_host_with_default() { case $1 in Enter*) printf 45;; *) printf %s "$2";; esac; }\n'
               '_hostkey_check() { :; }; _spin_start() { :; }; _spin_stop() { :; }\n'
               'ssh() { cat >/dev/null; echo remote-hn; }\n'
               'confirm_user_choice() { "$3"; }\n'
               'install_ssh_key_on_remote k1')
    r = subprocess.run([BASH32, "-c", snippet], env={"HOME": str(home), "PATH": "/usr/bin:/bin", "TERM": "dumb"},
                       capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
    assert "isn't in ~/.ssh/config" in r.stderr, r.stderr
    block = _block(home)
    assert block.startswith("Host claude-ho4"), block + r.stdout + r.stderr
    assert "HostName 192.168.0.45" in block and "k1" in block


@pytest.mark.skipif(not shutil.which("pwsh"), reason="pwsh not installed")
def test_powershell_new_name_becomes_the_alias(home):
    libs = "; ".join(f". '{ROOT}/lib/ps/{m}.ps1'" for m in PS_LIBS)
    script = (f"$env:USERPROFILE = '{home}'; {libs}; $DefaultSubnetPrefix = '192.168.0'; $DefaultUserName = 'kraid'\n"
              "function Select-FromList { 'claude-ho4' }\n"
              "function Read-HostWithDefault { param($Prompt, $Default) if ($Prompt -like 'Enter*') { '45' } else { $Default } }\n"
              "function Test-HostKey { $true }; function Read-RemoteUser { 'kraid' }\n"
              "function ssh { $input | Out-Null; 'remote-hn' }\n"
              "function Confirm-UserChoice { param($Message, $Action, $DefaultAnswer) & $Action }\n"
              "Install-SSHKeyOnRemote -KeyName k1 6>$null\n")
    r = subprocess.run(["pwsh", "-NoProfile", "-Command", script], capture_output=True, text=True, timeout=60)
    block = _block(home)
    assert block.startswith("Host claude-ho4"), block + r.stdout + r.stderr
    assert "HostName 192.168.0.45" in block and "k1" in block
