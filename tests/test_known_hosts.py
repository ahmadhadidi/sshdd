"""
TODO #15: known_hosts. A destroyed and recreated CT has new host keys; ssh then refuses it with
"REMOTE HOST IDENTIFICATION HAS CHANGED". sshdd checks the key before connecting and offers to
forget the old one; K/F list and forget local entries, O/B the remote user's, H offers it too.
A fake ssh-keyscan on PATH stands in for the recreated host (192.0.2.7 never answers).
"""
import subprocess
import time

import pexpect
import pytest

from .screen import Term

IP = "192.0.2.7"


def _key(tmp, name):
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(tmp / name)], check=True)
    t, k = (tmp / f"{name}.pub").read_text().split()[:2]
    return f"{t} {k}"


def _fp(line):
    return subprocess.run(["ssh-keygen", "-lf", "-"], input=line, capture_output=True,
                          text=True).stdout.split()[1]


@pytest.fixture
def kh(isolated_home, tmp_path):
    """Config host ct -> 192.0.2.7, known_hosts with its OLD key (hashed) and another host's key;
    the fake ssh-keyscan answers with whatever scan.out holds (the NEW key by default)."""
    ssh = isolated_home / ".ssh"
    # HashKnownHosts like Ubuntu's /etc/ssh/ssh_config (the test ssh wrapper's -F skips that file).
    (ssh / "config").write_text(f"Host ct\n    HostName {IP}\n    User root\nHost *\n    HashKnownHosts yes\n")
    old, new, other = _key(tmp_path, "old"), _key(tmp_path, "new"), _key(tmp_path, "other")
    (ssh / "known_hosts").write_text(f"{IP} {old}\n10.9.9.9 {other}\n")
    subprocess.run(["ssh-keygen", "-H", "-f", str(ssh / "known_hosts")], check=True, capture_output=True)
    (ssh / "known_hosts.old").unlink()
    (isolated_home / "scan.out").write_text(f"{IP} {new}\n")
    scan = isolated_home / "bin" / "ssh-keyscan"
    scan.write_text('#!/bin/sh\necho "$*" >> "$HOME/scanned"\ncat "$HOME/scan.out"\n')
    scan.chmod(0o755)
    return {"home": isolated_home, "old": old, "new": new, "other": other}


def _known(home, name):
    return subprocess.run(["ssh-keygen", "-F", name, "-f", str(home / ".ssh" / "known_hosts")],
                          capture_output=True, text=True).stdout


def _test_connection_to_ct(t):
    t.wait_for("Quit")
    t.press("T")
    t.wait_for("Select remote host", timeout=8)
    t.press("ct\r")


def test_changed_key_shows_both_fingerprints_and_forgets(kh):
    with Term(home=kh["home"]) as t:
        _test_connection_to_ct(t)
        t.wait_for("changed", timeout=8)
        txt = t.text()
        assert f"Host key for {IP} (ct) changed" in txt
        assert _fp(kh["old"]) in txt and _fp(kh["new"]) in txt, txt
        assert "Forget the old key and retry? [y/N]" in txt
        t.press("y\r")
        t.wait_for("Remote username", timeout=5)
        assert f"Removed 1 key(s) for {IP}" in t.text()
        assert f"Trusted the new key for {IP}" in t.text()
    entry = _known(kh["home"], IP)
    assert entry.count("found") == 1 and entry.split("\n")[1].startswith("|1|"), entry   # HashKnownHosts
    assert _fp(kh["new"]) in subprocess.run(["ssh-keygen", "-l", "-F", IP, "-f", str(kh["home"] / ".ssh" / "known_hosts")],
                                            capture_output=True, text=True).stdout
    assert _known(kh["home"], "10.9.9.9"), "another host's key was removed"
    assert (kh["home"] / ".ssh" / "known_hosts.old").exists()


def test_changed_key_kept_cancels_operation(kh):
    before = (kh["home"] / ".ssh" / "known_hosts").read_text()
    with Term(home=kh["home"]) as t:
        _test_connection_to_ct(t)
        t.wait_for("retry? [y/N]", timeout=8)
        t.press("\r")                                   # default: No -> back to the menu, like Esc
        t.wait_for("Up/Dn Navigate", timeout=5)
        assert "Remote username" not in t.text()
    assert (kh["home"] / ".ssh" / "known_hosts").read_text() == before


def test_same_key_no_prompt(kh):
    (kh["home"] / "scan.out").write_text(f"{IP} {kh['old']}\n")
    with Term(home=kh["home"]) as t:
        _test_connection_to_ct(t)
        t.wait_for("Remote username", timeout=8)
        assert "changed" not in t.text()
    assert (kh["home"] / "scanned").read_text().split("\n")[:-1] == [f"-T 4 -t ed25519 -p 22 {IP}"]   # one connection


def test_unknown_host_is_not_scanned(kh):
    """A host never seen has nothing to compare: no extra connection (ssh's accept-new records it)."""
    (kh["home"] / ".ssh" / "known_hosts").write_text("")
    with Term(home=kh["home"]) as t:
        _test_connection_to_ct(t)
        t.wait_for("Remote username", timeout=8)
    assert not (kh["home"] / "scanned").exists()


def test_list_known_hosts_names_hashed_entries(kh):
    with Term(home=kh["home"]) as t:
        t.wait_for("Quit")
        t.press("K")
        t.wait_for("Esc/Q to close", timeout=8)
        txt = t.text()
        assert f"{IP} (hashed)" in txt, txt            # matched against config host ct
        assert "(hashed)" in txt.replace(f"{IP} (hashed)", ""), txt   # 10.9.9.9: not in config
        assert _fp(kh["other"]) in txt
        t.press("q")
        t.wait_for("Quit")


def test_forget_host_key_local(kh):
    with Term(home=kh["home"]) as t:
        t.wait_for("Quit")
        t.press("F")
        t.wait_for("Select remote host", timeout=8)
        t.press("ct\r")
        t.wait_for("Forget these keys? [y/N]", timeout=5)
        assert _fp(kh["old"]) in t.text()
        t.press("y\r")
        t.wait_for("Removed 1 key(s)", timeout=5)
    assert not _known(kh["home"], IP)
    assert _known(kh["home"], "10.9.9.9")


def test_remove_host_offers_to_forget_key(kh):
    with Term(home=kh["home"]) as t:
        t.wait_for("Quit")
        t.press("H")
        t.wait_for("Select host to remove", timeout=5)
        t.press("ct\r")
        t.wait_for("Remove this block? [y/N]")
        t.press("y\r")
        t.wait_for("Also forget its host key? [y/N]", timeout=5)
        t.press("y\r")
        t.wait_for("Removed 1 key(s)", timeout=5)
    assert "Host ct" not in (kh["home"] / ".ssh" / "config").read_text()
    assert not _known(kh["home"], IP)


def test_remove_host_names_other_users_of_the_key(kh):
    ssh = kh["home"] / ".ssh"
    ssh.joinpath("config").write_text(f"Host ct\n    HostName {IP}\nHost ct2\n    HostName {IP}\n")
    with Term(home=kh["home"]) as t:
        t.wait_for("Quit")
        t.press("H")
        t.wait_for("Select host to remove", timeout=5)
        t.press("ct\r")                                 # filter "ct" leaves ct and ct2: first wins
        t.wait_for("Remove this block? [y/N]")
        t.press("y\r")
        t.wait_for("Also forget its host key?", timeout=5)
        assert "Still used by: ct2" in t.text(), t.text()
        t.press("\r")
        t.wait_for("Action cancelled")
    assert _known(kh["home"], IP)


# ── O / B on CT 213 (the SSH user's ~/.ssh/known_hosts there) ─────────────────

LXC = "192.168.0.213"


def _ct_shell(cmd):
    """Run cmd on CT 213 as testuser (password auth), from outside sshdd."""
    c = pexpect.spawn("ssh", ["-F", "/dev/null", "-o", "StrictHostKeyChecking=accept-new",
                              "-o", "PreferredAuthentications=password,keyboard-interactive",
                              f"testuser@{LXC}", cmd], encoding="utf-8", timeout=20)
    c.expect("assword:")
    c.sendline("testpass")
    c.expect(pexpect.EOF)
    return c.before


def _answer_until(t, want, timeout=40):
    end = time.time() + timeout
    while time.time() < end:
        t.pump(0.5)
        if want in t.text():
            return t.text()
        if t.screen.display[t.screen.cursor.y].rstrip().endswith("password:"):
            t.press("testpass\r")
    raise AssertionError(t.text())


@pytest.fixture
def ct(isolated_home, tmp_path):
    (isolated_home / ".ssh" / "config").write_text(
        f"Host ct\n    HostName {LXC}\n    User testuser\nHost gone\n    HostName 10.8.8.8\n")
    gone, other = _key(tmp_path, "gone"), _key(tmp_path, "other")
    _ct_shell(f"mkdir -p ~/.ssh && printf '%s\\n' '10.8.8.8 {gone}' '10.7.7.7 {other}' > ~/.ssh/known_hosts"
              " && ssh-keygen -H -f ~/.ssh/known_hosts >/dev/null 2>&1; rm -f ~/.ssh/known_hosts.old")
    yield {"home": isolated_home, "gone": gone, "other": other}
    _ct_shell("rm -f ~/.ssh/known_hosts ~/.ssh/known_hosts.old")


@pytest.mark.lxc
def test_remote_list_known_hosts(ct):
    with Term(home=ct["home"], args="--user testuser") as t:
        t.wait_for("Quit")
        t.press("O")
        t.wait_for("Select remote host", timeout=8)
        t.press("ct\r")
        t.wait_for("Remote username")
        t.press("\r")
        txt = _answer_until(t, "Esc/Q to close")
        assert "10.8.8.8 (hashed)" in txt, txt
        assert _fp(ct["other"]) in txt
        t.press("q")
        t.wait_for("Quit")


@pytest.mark.lxc
def test_remote_forget_host_key(ct):
    with Term(home=ct["home"], args="--user testuser") as t:
        t.wait_for("Quit")
        t.press("B")
        t.wait_for("Select remote host", timeout=8)
        t.press("ct\r")
        t.wait_for("Remote username")
        t.press("\r")
        t.wait_for("Host to forget on", timeout=10)
        t.wait_for("Select remote host", timeout=8)
        t.press("gone\r")
        txt = _answer_until(t, "Forget these keys on")
        assert _fp(ct["gone"]) in txt, txt
        t.press("y\r")
        _answer_until(t, "Removed 1 key(s)")
    left = _ct_shell("ssh-keygen -F 10.8.8.8 -f ~/.ssh/known_hosts; echo; ssh-keygen -F 10.7.7.7 -f ~/.ssh/known_hosts")
    assert "10.8.8.8" not in left and "found" in left, left


# ── PowerShell parity (pwsh in tmux) ──────────────────────────────────────────

def _pwsh(home, args=""):
    import shutil
    from .screen import Tmux
    if not (shutil.which("pwsh") and shutil.which("tmux")):
        pytest.skip("needs pwsh and tmux")
    return Tmux(f"pwsh -NoProfile -File ./sshdd.ps1 {args}", env={"HOME": str(home), "USERPROFILE": str(home)})


def test_powershell_changed_key_forgets_and_trusts_new(kh):
    with _pwsh(kh["home"]) as t:
        t.wait_for("Q Quit", timeout=15)
        t.press("T")
        t.wait_for("Select remote host", timeout=8)
        t.press("ct", "ENTER")
        t.wait_for("retry? [y/N]", timeout=10)
        txt = t.text()
        assert f"Host key for {IP} (ct) changed" in txt and _fp(kh["old"]) in txt and _fp(kh["new"]) in txt, txt
        t.press("y", "ENTER")
        t.wait_for("Remote username", timeout=8)
        assert f"Trusted the new key for {IP}" in t.text()
    entry = _known(kh["home"], IP)
    assert entry.count("found") == 1 and entry.split("\n")[1].startswith("|1|"), entry
    assert _known(kh["home"], "10.9.9.9")


def test_powershell_kept_key_cancels(kh):
    before = (kh["home"] / ".ssh" / "known_hosts").read_text()
    with _pwsh(kh["home"]) as t:
        t.wait_for("Q Quit", timeout=15)
        t.press("T")
        t.wait_for("Select remote host", timeout=8)
        t.press("ct", "ENTER")
        t.wait_for("retry? [y/N]", timeout=10)
        t.press("ENTER")
        t.wait_for("Up/Dn Navigate", timeout=8)
        assert "Remote username" not in t.text()
    assert (kh["home"] / ".ssh" / "known_hosts").read_text() == before


def test_powershell_list_and_forget(kh):
    with _pwsh(kh["home"]) as t:
        t.wait_for("Q Quit", timeout=15)
        t.press("K")
        t.wait_for("Known hosts in", timeout=8)
        t.wait_for("Press any key", timeout=8)
        txt = t.text()
        assert f"{IP} (hashed)" in txt and _fp(kh["other"]) in txt, txt
        t.press("ENTER")
        t.wait_for("Q Quit", timeout=8)
        t.press("F")
        t.wait_for("Select remote host", timeout=8)
        t.press("ct", "ENTER")
        t.wait_for("Forget these keys? [y/N]", timeout=8)
        t.press("y", "ENTER")
        t.wait_for("Removed 1 key(s)", timeout=8)
    assert not _known(kh["home"], IP) and _known(kh["home"], "10.9.9.9")


def test_powershell_remove_host_offers_forget(kh):
    with _pwsh(kh["home"]) as t:
        t.wait_for("Q Quit", timeout=15)
        t.press("H")
        t.wait_for("Select host to remove", timeout=8)
        t.press("ct", "ENTER")
        t.wait_for("Remove this block? [y/N]", timeout=8)
        t.press("y", "ENTER")
        t.wait_for("Also forget its host key? [y/N]", timeout=8)
        t.press("y", "ENTER")
        t.wait_for("Removed 1 key(s)", timeout=8)
    assert not _known(kh["home"], IP)


def _pwsh_answer_until(t, want, timeout=40):
    end = time.time() + timeout
    while time.time() < end:
        txt = t.text()
        if want in txt:
            return txt
        if txt.rstrip().endswith("password:"):
            t.press("testpass", "ENTER")
        time.sleep(0.5)
    raise AssertionError(t.text())


@pytest.mark.lxc
def test_powershell_remote_list_and_forget(ct):
    with _pwsh(ct["home"], "-DefaultUserName testuser") as t:
        t.wait_for("Q Quit", timeout=15)
        t.press("O")
        t.wait_for("Select remote host", timeout=8)
        t.press("ct", "ENTER")
        t.wait_for("Remote username", timeout=8)
        t.press("ENTER")
        txt = _pwsh_answer_until(t, "Press any key")
        assert "10.8.8.8 (hashed)" in txt and _fp(ct["other"]) in txt, txt
        t.press("ENTER")
        t.wait_for("Q Quit", timeout=8)
        t.press("B")
        t.wait_for("Select remote host", timeout=8)
        t.press("ct", "ENTER")
        t.wait_for("Remote username", timeout=8)
        t.press("ENTER")
        t.wait_for("Host to forget on", timeout=10)
        time.sleep(1)
        t.press("gone", "ENTER")
        txt = _pwsh_answer_until(t, "Forget these keys on")
        assert _fp(ct["gone"]) in txt, txt
        t.press("y", "ENTER")
        _pwsh_answer_until(t, "Removed 1 key(s)")
    left = _ct_shell("ssh-keygen -F 10.8.8.8 -f ~/.ssh/known_hosts; echo; ssh-keygen -F 10.7.7.7 -f ~/.ssh/known_hosts")
    assert "10.8.8.8" not in left and "found" in left, left


# ── Security review fixes (one regression test each) ──────────────────────────

def _to_username_or_menu(t, want):
    _test_connection_to_ct(t)
    t.wait_for(want, timeout=8)
    assert "changed" not in t.text(), t.text()


def test_m3_cert_authority_line_is_not_a_host_key(kh):
    """@cert-authority / @revoked lines aren't host keys: no false "changed", and Forget leaves them."""
    ssh = kh["home"] / ".ssh"
    ssh.joinpath("known_hosts").write_text(f"@cert-authority {IP} {kh['other']}\n")
    with Term(home=kh["home"]) as t:
        _to_username_or_menu(t, "Remote username")
    assert not (kh["home"] / "scanned").exists()
    ssh.joinpath("known_hosts").write_text(f"@cert-authority {IP} {kh['other']}\n{IP} {kh['old']}\n")
    with Term(home=kh["home"]) as t:
        _test_connection_to_ct(t)
        t.wait_for("retry? [y/N]", timeout=8)
        txt = t.text()
        assert _fp(kh["old"]) in txt and _fp(kh["other"]) not in txt, txt
        t.press("y\r")
        t.wait_for("Remote username", timeout=5)
        assert "Removed 1 key(s)" in t.text()
    assert f"@cert-authority {IP}" in ssh.joinpath("known_hosts").read_text()


def test_m2_proxied_host_is_not_scanned(kh):
    """Through ProxyJump the scan would reach another machine: leave it to ssh."""
    (kh["home"] / ".ssh" / "config").write_text(f"Host ct\n    HostName {IP}\n    ProxyJump bastion\n")
    with Term(home=kh["home"]) as t:
        _to_username_or_menu(t, "Remote username")
    assert not (kh["home"] / "scanned").exists()


@pytest.mark.parametrize("scan", ["two", "garbage"])
def test_m1_only_one_shown_key_is_ever_recorded(kh, scan):
    """More than one scanned line, or one without a fingerprint: no prompt, nothing recorded."""
    out = {"two": f"{IP} {kh['new']}\n{IP} {kh['other']}\n", "garbage": f"{IP} ssh-ed25519 AAAAnotakey\n"}[scan]
    (kh["home"] / "scan.out").write_text(out)
    before = (kh["home"] / ".ssh" / "known_hosts").read_text()
    with Term(home=kh["home"]) as t:
        _to_username_or_menu(t, "Remote username")
    assert (kh["home"] / ".ssh" / "known_hosts").read_text() == before


def test_l1_hash_failure_records_nothing_and_cancels(kh):
    """HashKnownHosts yes but ssh-keygen -H fails: never write the name in clear; the op stops."""
    import shutil
    fake = kh["home"] / "bin" / "ssh-keygen"
    fake.write_text('#!/bin/sh\nfor a; do [ "$a" = -H ] && exit 1; done\nexec ' + shutil.which("ssh-keygen") + ' "$@"\n')
    fake.chmod(0o755)
    with Term(home=kh["home"]) as t:
        _test_connection_to_ct(t)
        t.wait_for("retry? [y/N]", timeout=8)
        t.press("y\r")
        t.wait_for("not recorded", timeout=5)
        t.wait_for("Press any key", timeout=5)          # an error waits to be read
        assert "Remote username" not in t.text()
        t.press("\r")
        t.wait_for("Up/Dn Navigate", timeout=8)
    assert IP not in (kh["home"] / ".ssh" / "known_hosts").read_text()
    assert not list((kh["home"] / ".ssh").glob(".sshdd-kh-*")), "hash temp file left behind"


def test_l2_append_keeps_last_line_of_file_without_newline(kh):
    """Old key in a second UserKnownHostsFile; the first lacks a final newline: lines stay apart."""
    ssh = kh["home"] / ".ssh"
    (ssh / "kh1").write_text(f"10.9.9.9 {kh['other']}")              # no final newline
    (ssh / "kh2").write_text(f"{IP} {kh['old']}\n")
    w = kh["home"] / "bin" / "ssh"
    w.write_text(w.read_text().replace('UserKnownHostsFile="$HOME/.ssh/known_hosts"',
                                       'UserKnownHostsFile="$HOME/.ssh/kh1 $HOME/.ssh/kh2"'))
    (ssh / "config").write_text(f"Host ct\n    HostName {IP}\n")      # no hashing: lines readable
    with Term(home=kh["home"]) as t:
        _test_connection_to_ct(t)
        t.wait_for("retry? [y/N]", timeout=8)
        t.press("y\r")
        t.wait_for("Trusted the new key", timeout=5)
    assert (ssh / "kh1").read_text() == f"10.9.9.9 {kh['other']}\n{IP} {kh['new']}\n"


def test_powershell_review_fixes(kh):
    """PS mirror: @cert-authority ignored (M3), proxied host not scanned (M2), two scan lines ignored (M1)."""
    ssh = kh["home"] / ".ssh"
    cases = [
        (f"Host ct\n    HostName {IP}\n", f"@cert-authority {IP} {kh['other']}\n", f"{IP} {kh['new']}\n"),
        (f"Host ct\n    HostName {IP}\n    ProxyJump bastion\n", f"{IP} {kh['old']}\n", f"{IP} {kh['new']}\n"),
        (f"Host ct\n    HostName {IP}\n", f"{IP} {kh['old']}\n", f"{IP} {kh['new']}\n{IP} {kh['other']}\n"),
    ]
    for cfg, known, scan in cases:
        ssh.joinpath("config").write_text(cfg)
        ssh.joinpath("known_hosts").write_text(known)
        (kh["home"] / "scan.out").write_text(scan)
        with _pwsh(kh["home"]) as t:
            t.wait_for("Q Quit", timeout=15)
            t.press("T")
            t.wait_for("Select remote host", timeout=8)
            t.press("ct", "ENTER")
            t.wait_for("Remote username", timeout=10)
            assert "changed" not in t.text(), (cfg, t.text())
        assert ssh.joinpath("known_hosts").read_text() == known


@pytest.mark.lxc
def test_remote_forget_reports_failure(ct):
    """The remote edit fails (~/.ssh not writable): say so instead of "Removed"."""
    _ct_shell("chmod 500 ~/.ssh")
    try:
        with Term(home=ct["home"], args="--user testuser") as t:
            t.wait_for("Quit")
            t.press("B")
            t.wait_for("Select remote host", timeout=8)
            t.press("ct\r")
            t.wait_for("Remote username")
            t.press("\r")
            t.wait_for("Host to forget on", timeout=10)
            t.wait_for("Select remote host", timeout=8)
            t.press("gone\r")
            _answer_until(t, "Forget these keys on")
            t.press("y\r")
            txt = _answer_until(t, "Press any key")
            assert "Failed to edit known_hosts" in txt and "Removed" not in txt, txt
    finally:
        _ct_shell("chmod 700 ~/.ssh")
