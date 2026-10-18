"""
Plan Z1: user-typed text (key name, comment, passphrase, host, user) is data, never code,
locally or on the remote host.
"""
import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PS_LIBS = ["tui", "ssh-helpers", "ssh-config", "prompts", "ssh-ops"]
needs_pwsh = pytest.mark.skipif(not shutil.which("pwsh"), reason="pwsh not installed")
TRICKY = ["", "plain", "two words", 'pa$$ "w" \\x', 'end\\', 'a\\"b', '"', "$(whoami)", "tab\there", "x\\\\ y\\"]


def _pwsh(script, env=None):
    libs = "; ".join(f". '{ROOT}/lib/ps/{m}.ps1'" for m in PS_LIBS)
    return subprocess.run(["pwsh", "-NoProfile", "-Command", libs + "\n" + script], env=env,
                          capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)


@needs_pwsh
@pytest.mark.parametrize("passphrase", ["", 'pa$$ "w" \\x'])
def test_powershell_keygen_takes_text_literally(tmp_path, passphrase):
    """Real run (pwsh 7.6, native args passed verbatim): comment not executed, both stored exactly."""
    canary = tmp_path / "pwned"
    comment = f'evil $(New-Item {canary}) "q" end\\'
    (tmp_path / ".ssh").mkdir()
    r = _pwsh(
        f"$env:USERPROFILE = '{tmp_path}'\n"
        "function Read-Host { param([switch]$AsSecureString) $s = [securestring]::new(); "
        "foreach ($c in $env:PASS.ToCharArray()) { $s.AppendChar($c) }; $s }\n"
        "Add-SSHKeyInHost -KeyName k1 -Comment $env:COMMENT *> $null\n",
        env=dict(os.environ, PASS=passphrase, COMMENT=comment))
    assert r.returncode == 0, r.stderr
    assert not canary.exists(), "comment was executed"
    assert (tmp_path / ".ssh" / "k1.pub").read_text().split(" ", 2)[2].rstrip("\n") == comment
    r = subprocess.run(["ssh-keygen", "-y", "-P", passphrase, "-f", str(tmp_path / ".ssh" / "k1")],
                       capture_output=True, text=True)
    assert r.returncode == 0, f"passphrase didn't unlock the key: {r.stderr}"


def _ps51_command_line(args):
    """How Windows PowerShell 5.1 (legacy native args) joins arguments: empty ones dropped,
    ones with whitespace wrapped in quotes, nothing escaped."""
    out = []
    for a in args:
        if a == "":
            continue
        out.append(f'"{a}"' if any(c.isspace() for c in a) else a)
    return " ".join(out)


def _command_line_to_argv(line):
    """Windows CommandLineToArgvW / MSVC rules: 2n backslashes + quote -> n backslashes, toggle;
    2n+1 backslashes + quote -> n backslashes + literal quote; other backslashes literal."""
    args, cur, inq, have, i = [], "", False, False, 0
    while i < len(line):
        c = line[i]
        if c == "\\":
            n = 0
            while i < len(line) and line[i] == "\\":
                n += 1
                i += 1
            if i < len(line) and line[i] == '"':
                cur += "\\" * (n // 2)
                if n % 2:
                    cur += '"'
                    i += 1
                have = True
                continue
            cur += "\\" * n
            have = True
            continue
        if c == '"':
            inq = not inq
            have = True
        elif c.isspace() and not inq:
            if have:
                args.append(cur)
            cur, have = "", False
        else:
            cur += c
            have = True
        i += 1
    if have:
        args.append(cur)
    return args


@needs_pwsh
def test_native_argument_escaping_for_windows_powershell_51():
    """ConvertTo-NativeArgument in Legacy mode + 5.1's joining + Windows' splitting == the original text.
    A model: proving it on real Windows PowerShell 5.1 needs plan P3."""
    r = _pwsh("$PSNativeCommandArgumentPassing = 'Legacy'\n"
              "$env:TRICKY.Split([char]0x1F) | ForEach-Object { ConvertTo-NativeArgument $_ } | "
              "ForEach-Object { [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes('x' + $_)) }",
              env=dict(os.environ, TRICKY="\x1f".join(TRICKY)))
    import base64
    escaped = [base64.b64decode(x).decode()[1:] for x in r.stdout.split()]
    assert len(escaped) == len(TRICKY), r.stderr
    for original, arg in zip(TRICKY, escaped):
        assert _command_line_to_argv(_ps51_command_line([arg])) == [original], (original, arg)


@needs_pwsh
def test_native_argument_untouched_on_modern_powershell():
    r = _pwsh("$env:TRICKY.Split([char]0x1F) | ForEach-Object { ConvertTo-NativeArgument $_ } | "
              "ForEach-Object { [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes('x' + $_)) }",
              env=dict(os.environ, TRICKY="\x1f".join(TRICKY)))
    import base64
    assert [base64.b64decode(x).decode()[1:] for x in r.stdout.split()] == TRICKY


@pytest.mark.lxc
def test_remote_key_removal_is_injection_safe_and_keeps_mode(tmp_path):
    """Z1 + Z3 on CT 213: a key comment with ' can't run commands on the remote; only that key
    line goes; other keys stay; authorized_keys keeps mode 600 (sshd StrictModes)."""
    from .test_lxc_connection import _ssh_run, _askpass_env, LXC_USER, LXC_HOST, LXC_PASS
    canary = f"/tmp/pwned-sshdd-{os.getpid()}"
    key = tmp_path / "evil"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key),
                    "-C", f"x'; touch {canary}; echo '"], check=True)
    keep = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKeepKeepKeepKeepKeepKeepKeepKeepKeepKeep keep-me"
    pub = key.with_suffix(".pub").read_text()
    r = _ssh_run("mkdir -p ~/.ssh && cat > ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys",
                 stdin_data=(keep + "\n" + pub).encode())
    assert r.returncode == 0, r.stderr
    env = _askpass_env(LXC_PASS)
    libs = " ".join(f"source {ROOT}/lib/bash/{m}.sh;" for m in ["tui", "ssh-config", "ssh-helpers"])
    r = subprocess.run(["bash", "-c", f'{libs} _remote_remove_pubkey "$T" "$K"'],
                       env=dict(env, T=f"{LXC_USER}@{LXC_HOST}", K=pub), capture_output=True, text=True,
                       timeout=30, stdin=subprocess.DEVNULL)
    assert r.returncode == 0, r.stderr
    after = _ssh_run(f"cat ~/.ssh/authorized_keys; echo MODE=$(stat -c %a ~/.ssh/authorized_keys); "
                     f"ls {canary} 2>/dev/null && echo CANARY").stdout.decode()
    assert "CANARY" not in after, "comment ran on the remote"
    assert keep in after and pub.split()[1] not in after
    assert "MODE=600" in after


@pytest.mark.lxc
@needs_pwsh
def test_powershell_remote_key_removal_is_injection_safe_and_keeps_mode(tmp_path):
    """Same as the bash test, through Remove-RemotePublicKey (PS parity)."""
    from .test_lxc_connection import _ssh_run, _askpass_env, LXC_USER, LXC_HOST, LXC_PASS
    canary = f"/tmp/pwned-sshdd-ps-{os.getpid()}"
    key = tmp_path / "evil"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key),
                    "-C", f"x'; touch {canary}; echo '"], check=True)
    keep = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKeepKeepKeepKeepKeepKeepKeepKeepKeepKeep keep-me"
    pub = key.with_suffix(".pub").read_text()
    assert _ssh_run("mkdir -p ~/.ssh && cat > ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys",
                    stdin_data=(keep + "\n" + pub).encode()).returncode == 0
    r = _pwsh('if (Remove-RemotePublicKey -Target $env:T -PublicKey $env:K) { "OK" } else { "FAIL" }',
              env=dict(_askpass_env(LXC_PASS), T=f"{LXC_USER}@{LXC_HOST}", K=pub))
    assert r.stdout.strip().endswith("OK"), r.stdout + r.stderr
    after = _ssh_run(f"cat ~/.ssh/authorized_keys; echo MODE=$(stat -c %a ~/.ssh/authorized_keys); "
                     f"ls {canary} 2>/dev/null && echo CANARY").stdout.decode()
    assert "CANARY" not in after and keep in after and pub.split()[1] not in after and "MODE=600" in after


@needs_pwsh
def test_powershell_imported_key_usable(tmp_path):
    """Write-KeyPair: no BOM (OpenSSH: 'error in libcrypto'), mode 600 off Windows, ssh loads it."""
    src = tmp_path / "src"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(src)], check=True)
    (tmp_path / ".ssh").mkdir()
    r = _pwsh(f"$env:USERPROFILE = '{tmp_path}'\n"
              "Write-KeyPair -DestPriv $env:D -DestPub ($env:D + '.pub') "
              "-PrivData ([IO.File]::ReadAllText($env:S)) -PubData ([IO.File]::ReadAllText($env:S + '.pub')) *> $null",
              env=dict(os.environ, S=str(src), D=str(tmp_path / ".ssh" / "k")))
    assert r.returncode == 0, r.stderr
    key = tmp_path / ".ssh" / "k"
    assert not key.read_bytes().startswith(b"\xef\xbb\xbf")
    assert oct(key.stat().st_mode & 0o777) == "0o600"
    assert subprocess.run(["ssh-keygen", "-y", "-f", str(key)], capture_output=True).returncode == 0


@needs_pwsh
def test_powershell_config_edit_no_bom_and_symlink_kept(tmp_path):
    """Add-SSHKeyToHostConfig: config stays BOM-free (OpenSSH rejects the whole file otherwise),
    readable by ssh -G, and a symlinked config keeps its link."""
    real = tmp_path / "dot" / "config"
    real.parent.mkdir()
    real.write_text("Host a\n    HostName 1.1.1.1\n    IdentityFile $HOME/.ssh/old\n")
    (tmp_path / ".ssh").mkdir()
    for k in ("k1", "k2"):
        (tmp_path / ".ssh" / k).write_text("x")
    (tmp_path / ".ssh" / "config").symlink_to(real)
    r = _pwsh(f"$env:USERPROFILE = '{tmp_path}'\n"
              "function Read-HostWithDefault { param($Prompt, $Default) 'n' }\n"
              "function Confirm-UserChoice { param($Message, $Action, $DefaultAnswer) }\n"
              "Add-SSHKeyToHostConfig -KeyName k1 -RemoteHostName a -RemoteHostAddress 1.1.1.1 -RemoteUser root *> $null\n"
              "Add-SSHKeyToHostConfig -KeyName k2 -RemoteHostName b -RemoteHostAddress 2.2.2.2 -RemoteUser root *> $null\n")
    assert r.returncode == 0, r.stderr
    assert (tmp_path / ".ssh" / "config").is_symlink()
    data = real.read_bytes()
    assert not data.startswith(b"\xef\xbb\xbf") and b"k1" in data and b"Host b" in data
    assert b"IdentityFile $HOME/.ssh/old" in data
    g = subprocess.run(["ssh", "-G", "-F", str(real), "b"], capture_output=True, text=True)
    assert g.returncode == 0 and "hostname 2.2.2.2" in g.stdout, g.stderr


BAD_NAMES = ["../evil", "../../evil", "sub/evil", ".hidden", "-x", "a..b", "has space", "a\\b"]


def _bash(snippet, env):
    from .screen import BASH32
    libs = " ".join(f"source {ROOT}/lib/bash/{m}.sh;" for m in
                    ["tui", "ssh-config", "ssh-helpers", "prompts", "ssh-ops"])
    return subprocess.run([BASH32, "-c", f"{libs}\n{snippet}"], env=dict(os.environ, **env),
                          capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)


@pytest.mark.parametrize("name", BAD_NAMES)
def test_bash_refuses_key_names_outside_ssh_dir(tmp_path, name):
    """Z1: key generation and import never write outside ~/.ssh."""
    ssh = tmp_path / "home" / ".ssh"
    ssh.mkdir(parents=True)
    env = {"SSH_DIR": str(ssh), "N": name}
    r = _bash('add_ssh_key_in_host "$N" c < /dev/null; echo gen=$?; '
              '_write_key_pair "$SSH_DIR/$N" "$SSH_DIR/$N.pub" "priv" "ssh-ed25519 AAAA c"; echo imp=$?', env)
    assert "gen=1" in r.stdout and "imp=1" in r.stdout, r.stdout + r.stderr
    written = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert written == [], written


def test_generate_and_install_refuses_traversal_name(tmp_path):
    from .screen import Term
    (tmp_path / ".ssh").mkdir(mode=0o700)
    (tmp_path / ".ssh" / "config").write_text("Host box1\n    HostName 192.0.2.1\n")
    with Term(home=tmp_path) as t:
        t.wait_for("Quit")
        t.press("G")
        t.wait_for("Enter SSH key name")
        t.press("../evil\r")
        t.wait_for("Key comment")
        t.press("\r")
        t.wait_for("Invalid key name")
    assert not (tmp_path / "evil").exists() and not (tmp_path / "evil.pub").exists()


@needs_pwsh
@pytest.mark.parametrize("name", BAD_NAMES + ["..\\..\\evil"])
def test_powershell_refuses_key_names_outside_ssh_dir(tmp_path, name):
    home = tmp_path / "home"
    (home / ".ssh").mkdir(parents=True)
    r = _pwsh(f"$env:USERPROFILE = '{home}'\n"
              "function Read-Host { param([switch]$AsSecureString) [securestring]::new() }\n"
              "Add-SSHKeyInHost -KeyName $env:N -Comment c *> $null\n"
              "$d = Join-Path (Join-Path $env:USERPROFILE '.ssh') $env:N\n"
              "$ok = Write-KeyPair -DestPriv $d -DestPub \"$d.pub\" -PrivData p -PubData 'ssh-ed25519 AAAA c' 6> $null\n"
              "\"ok=$ok\"", env=dict(os.environ, N=name))
    assert "ok=False" in r.stdout, r.stdout + r.stderr
    written = [p for p in tmp_path.rglob("*") if p.is_file()]
    assert written == [], written


def test_password_never_on_command_line_or_in_log(tmp_path, isolated_home):
    """Z2: --password reaches sshpass through $SSHPASS (sshpass -e), not argv (-p, visible in ps);
    the --verbose debug log never contains it."""
    from .screen import Term
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()
    rec = tmp_path / "sshpass.rec"
    fake = bin_dir / "sshpass"
    fake.write_text(f'#!/bin/sh\nprintf "argv=%s\\nenv=%s\\n" "$*" "$SSHPASS" > {rec}\nexit 1\n')
    fake.chmod(0o755)
    ssh = isolated_home / ".ssh"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(ssh / "k1")], check=True)
    (ssh / "config").write_text("Host box\n    HostName 192.0.2.1\n    User root\n")
    log = "/tmp/sshdd-debug.log"
    with Term(home=isolated_home, args="--password S3cret-pw --verbose",
              env={"PATH": f"{bin_dir}:{os.environ['PATH']}"}) as t:
        t.wait_for("Press any key to start")
        t.press("ENTER")
        t.wait_for("Quit")
        t.press("I")
        t.wait_for("Esc cancel")
        t.press("k1\r")
        t.wait_for("Select remote host", timeout=8)
        t.press("box\r")
        t.wait_for("Remote username")
        t.press("\r")
        t.wait_for("Press any key", timeout=15)
    out = rec.read_text()
    assert "argv=" in out and "S3cret-pw" not in out.split("env=")[0], out
    assert out.strip().endswith("env=S3cret-pw"), out
    assert "S3cret-pw" not in open(log, errors="replace").read()
