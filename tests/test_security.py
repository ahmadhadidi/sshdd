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
