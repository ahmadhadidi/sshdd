"""
Regression tests for lib/bash/ssh-config.sh parsers (TODO #3).

ssh_config keywords are case-insensitive and accept "Key value" or "Key=value",
indented with spaces or tabs. Every getter must return the bare value.
"""
import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG = (
    "Host spaces\n"
    "    HostName 192.168.0.204\n"
    "    User kraid\n"
    "    IdentityFile ~/.ssh/dev-lan\n"
    "\n"
    "Host tabs\n"
    "\tHostname\t10.0.0.5\n"
    "\tuser\troot\n"
    "\n"
    "Host equals\n"
    "  HOSTNAME=10.0.0.6\n"
    "  User = admin\n"
)


def _bash(tmp_path, snippet):
    cfg = tmp_path / "config"
    cfg.write_text(CONFIG)
    script = (
        f"SSH_CONFIG='{cfg}'; SSH_DIR='{tmp_path}'\n"
        f"source '{ROOT}/lib/bash/tui.sh'; source '{ROOT}/lib/bash/ssh-config.sh'\n"
        + snippet
    )
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True).stdout


@pytest.mark.parametrize("alias,ip,user", [
    ("spaces", "192.168.0.204", "kraid"),
    ("tabs", "10.0.0.5", "root"),
    ("equals", "10.0.0.6", "admin"),
])
def test_getters_return_bare_values(tmp_path, alias, ip, user):
    out = _bash(tmp_path, f"get_ip_from_host_config {alias}; echo '|'; get_user_from_host_config {alias}")
    assert out.split("\n|\n") == [ip, user + "\n"]


def test_configured_hosts_list(tmp_path):
    out = _bash(tmp_path, "get_configured_ssh_hosts")
    assert out.splitlines() == [
        "spaces|192.168.0.204|kraid",
        "tabs|10.0.0.5|root",
        "equals|10.0.0.6|admin",
    ]


def test_alias_and_identity_lookup_by_ip(tmp_path):
    out = _bash(tmp_path, "get_alias_for_host_ip 10.0.0.5; get_identity_files_for_host 192.168.0.204")
    assert out.splitlines() == ["tabs", "~/.ssh/dev-lan"]


PS_LIBS = ["tui", "ssh-helpers", "ssh-config", "prompts", "ssh-ops"]


@pytest.mark.skipif(not shutil.which("pwsh"), reason="pwsh not installed")
def test_powershell_parity(tmp_path):
    (tmp_path / ".ssh").mkdir()
    (tmp_path / ".ssh" / "config").write_text(CONFIG + "\nHost spaces-twin\n    HostName 192.168.0.204\n")
    libs = "; ".join(f". '{ROOT}/lib/ps/{m}.ps1'" for m in PS_LIBS)
    script = (
        f"$env:USERPROFILE = '{tmp_path}'; {libs}\n"
        "(Get-ConfiguredSSHHosts | ForEach-Object { \"$($_.Alias)|$($_.HostName)|$($_.User)\" }) -join ','\n"
        "Get-IPAddressFromHostConfigEntry equals; Get-RemoteUserFromConfigEntry tabs\n"
        "$script:_RemoteHost = '192.168.0.204'; $script:_RemoteAlias = 'spaces-twin'\n"
        "Resolve-SSHTarget -RemoteHostAddress 192.168.0.204 -RemoteUser kraid 6>$null\n"
    )
    out = subprocess.run(["pwsh", "-NoProfile", "-Command", script],
                         capture_output=True, text=True, check=True).stdout
    lines = [l for l in out.splitlines() if l.strip() and "SSH config entry" not in l]
    assert lines == [
        "spaces|192.168.0.204|kraid,tabs|10.0.0.5|root,equals|10.0.0.6|admin,spaces-twin|192.168.0.204|",
        "10.0.0.6", "root", "kraid@spaces-twin",
    ]


@pytest.mark.skipif(not shutil.which("pwsh"), reason="pwsh not installed")
def test_powershell_host_prompt_esc_and_typed_text(tmp_path):
    """TODO #1 parity: Esc on the host list cancels; typed digits are the address; a new name asks (#20)."""
    (tmp_path / ".ssh").mkdir()
    (tmp_path / ".ssh" / "config").write_text(CONFIG)
    libs = "; ".join(f". '{ROOT}/lib/ps/{m}.ps1'" for m in PS_LIBS)
    script = (
        f"$env:USERPROFILE = '{tmp_path}'; {libs}; $DefaultSubnetPrefix = '192.168.0'\n"
        "function Select-FromList { param($Items, $Prompt) $script:next }\n"
        "$script:next = '10';      Read-RemoteHostAddress 6>$null\n"
        "$script:next = 'tab';     Read-RemoteHostAddress 6>$null; $script:_LastSelectedAlias\n"
        "function Read-HostWithDefault { param($Prompt, $Default) if ($Default) { 'PREFILLED' } else { '45' } }\n"
        "$script:next = 'newhost'; Read-RemoteHostAddress 6>$null; $script:_NewHostAlias\n"
        "function Select-FromList { throw [System.OperationCanceledException]::new() }\n"
        "try { Read-RemoteHostAddress; 'NOT-CANCELLED' } catch [System.OperationCanceledException] { 'CANCELLED' }\n"
    )
    out = subprocess.run(["pwsh", "-NoProfile", "-Command", script],
                         capture_output=True, text=True, check=True).stdout.split()
    assert out == ["192.168.0.10", "10.0.0.5", "tabs", "192.168.0.45", "newhost", "CANCELLED"]


@pytest.mark.skipif(not shutil.which("pwsh"), reason="pwsh not installed")
def test_powershell_new_key_name(tmp_path):
    """TODO #4 parity: Read-NewSSHKeyName re-asks on empty, unsafe and existing names."""
    (tmp_path / ".ssh").mkdir()
    (tmp_path / ".ssh" / "k1").write_text("x")
    libs = "; ".join(f". '{ROOT}/lib/ps/{m}.ps1'" for m in PS_LIBS)
    script = (
        f"$env:USERPROFILE = '{tmp_path}'; {libs}\n"
        "$script:answers = [System.Collections.Queue]::new(@('', 'bad name', 'k1', 'fresh'))\n"
        "function Read-ColoredInput { param($Prompt, $ForegroundColor) $script:answers.Dequeue() }\n"
        "$n = Read-NewSSHKeyName 6>$null; \"$n left=$($script:answers.Count)\"\n"
    )
    out = subprocess.run(["pwsh", "-NoProfile", "-Command", script],
                         capture_output=True, text=True, check=True).stdout.strip()
    assert out == "fresh left=0"
