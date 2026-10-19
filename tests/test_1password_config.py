"""
TODO #18: 1Password's SSH-agent setup puts this block into ~/.ssh/config (at the top or the end):

    Host *
      IdentityAgent "~/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock"

Every function that reads or writes the config must ignore it and leave it byte for byte.
"""
import shutil
import subprocess

import pytest

from .screen import BASH32, ROOT, Term

OP = 'Host *\n  IdentityAgent "~/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock"\n'
BOX = "Host box\n    HostName 192.0.2.5\n    User root\n    IdentityFile ~/.ssh/k1\n"
LIBS = ["tui", "ssh-config", "ssh-helpers", "prompts", "ssh-ops"]


@pytest.fixture(params=["top", "end"])
def home(request, tmp_path):
    ssh = tmp_path / ".ssh"
    ssh.mkdir()
    for k in ("k1", "k2"):
        (ssh / k).write_text("x")
        (ssh / f"{k}.pub").write_text(f"ssh-ed25519 AAAA {k}\n")
    cfg = OP + "\n" + BOX if request.param == "top" else BOX + "\n" + OP
    (ssh / "config").write_text(cfg)
    return tmp_path


def _bash(home, snippet):
    src = " ".join(f"source {ROOT}/lib/bash/{m}.sh;" for m in LIBS)
    r = subprocess.run([BASH32, "-c", f'SSH_DIR="$HOME/.ssh"; SSH_CONFIG="$HOME/.ssh/config"; {src}\n{snippet}'],
                       env={"HOME": str(home), "PATH": "/usr/bin:/bin"}, capture_output=True, text=True, timeout=30)
    return r.stdout + r.stderr


def _cfg(home):
    return (home / ".ssh" / "config").read_text()


def test_host_star_is_not_a_host(home):
    assert _bash(home, "get_configured_ssh_hosts").splitlines() == ["box|192.0.2.5|root"]
    assert _bash(home, "get_identity_files_for_host box").splitlines() == ["~/.ssh/k1"]
    assert _bash(home, "get_alias_for_host_ip 192.0.2.5").strip() == "box"


@pytest.mark.parametrize("op", [
    "add_ssh_key_to_host_config k2 box 192.0.2.5 root",                 # existing block: IdentityFile added
    "add_ssh_key_to_host_config k2 newhost 192.0.2.9 root </dev/null",  # new block appended
    "remove_identity_file_from_config_block k1 box",
    '_get_host_block box; _replace_host_block "$_HOST_BLOCK" ""',       # Remove Host
])
def test_writes_leave_the_1password_block_alone(home, op):
    _bash(home, op)
    cfg = _cfg(home)
    assert cfg.count(OP) == 1, cfg
    assert cfg.count("Host *") == 1


def test_known_hosts_name_resolves_with_it(home):
    """ssh -G reads the whole config: the quoted path with spaces must not break it."""
    # OpenSSH reads the passwd home's config, not $HOME's: point it at the test config.
    out = _bash(home, 'ssh() { command ssh -F "$HOME/.ssh/config" "$@"; }; _hk_resolve box; '
                      'echo "$_HK_NAME $_HK_PORT ${#_HK_FILES[@]}"')
    assert out.strip().endswith("192.0.2.5 22 2"), out


def test_tui_menu_and_pickers_ignore_it(home):
    with Term(home=home) as t:
        t.wait_for("Quit")
        assert "unreadable" not in t.text().lower()
        t.press("H")
        t.wait_for("Select host to remove", timeout=5)
        t.pump(0.5)
        txt = t.text()
        assert "box" in txt and "*" not in txt.split("Select host to remove")[1], txt


@pytest.mark.skipif(not shutil.which("pwsh"), reason="pwsh not installed")
def test_powershell_parity(home):
    libs = "; ".join(f". '{ROOT}/lib/ps/{m}.ps1'" for m in LIBS)
    script = (f"$env:USERPROFILE = '{home}'; {libs}\n"
              "(Get-ConfiguredSSHHosts | ForEach-Object { $_.Alias }) -join ','\n"
              "Add-SSHKeyToHostConfig -KeyName k2 -RemoteHostName box -RemoteHostAddress 192.0.2.5 -RemoteUser root\n"
              "Remove-IdentityFileFromConfigBlock -KeyName k1 -HostAlias box\n")
    out = subprocess.run(["pwsh", "-NoProfile", "-Command", script], capture_output=True, text=True, timeout=60).stdout
    assert out.splitlines()[0] == "box", out
    cfg = _cfg(home)
    assert cfg.count(OP) == 1 and cfg.count("Host *") == 1, cfg
    assert "k2" in cfg and "/k1" not in cfg, cfg
