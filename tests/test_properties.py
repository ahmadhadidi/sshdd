"""
Plan H1–H2: property tests against OpenSSH itself (`ssh -G` is the oracle).

H1  for random valid configs, every alias sshdd lists has the HostName and User that `ssh -G` resolves.
H2  replacing one Host block (sshdd's config edits) leaves every other block's lines unchanged and
    the file still parses with `ssh -G`.
Configs avoid wildcard blocks, which change effective values in ways sshdd doesn't claim to model.
"""
import os
import subprocess

from hypothesis import HealthCheck, given, settings, strategies as st

from .test_units import bash

SETTINGS = settings(max_examples=40, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])

name = st.from_regex(r"[a-z][a-z0-9-]{0,8}", fullmatch=True)
ip = st.tuples(*[st.integers(1, 254)] * 4).map(lambda t: ".".join(map(str, t)))
indent = st.sampled_from(["", "  ", "    ", "\t"])
sep = st.sampled_from([" ", "  ", "\t", "=", " = "])
case = st.sampled_from([str.lower, str.upper, lambda s: s])


@st.composite
def config(draw):
    aliases = draw(st.lists(name, min_size=1, max_size=5, unique=True))
    blocks, expect = [], {}
    for a in aliases:
        lines = [f"{draw(case)('Host')}{draw(sep).replace('=', ' ')}{a}"]
        hn, user = None, None
        for _ in range(draw(st.integers(0, 4))):
            kind = draw(st.sampled_from(["HostName", "User", "Port", "#", ""]))
            if kind == "HostName":
                v = draw(ip)
                hn = hn or v                     # OpenSSH: first value wins
                lines.append(f"{draw(indent)}{draw(case)('HostName')}{draw(sep)}{v}")
            elif kind == "User":
                v = draw(name)
                user = user or v
                lines.append(f"{draw(indent)}{draw(case)('User')}{draw(sep)}{v}")
            elif kind == "Port":
                lines.append(f"{draw(indent)}Port{draw(sep)}{draw(st.integers(1, 65535))}")
            elif kind == "#":
                lines.append(f"{draw(indent)}# note {draw(name)}")
            else:
                lines.append("")
        blocks.append("\n".join(lines) + "\n")
        expect[a] = (hn, user)
    return "".join(blocks), expect


def _ssh_g(cfg, alias):
    out = subprocess.run(["ssh", "-G", "-F", str(cfg), alias], capture_output=True, text=True, check=True).stdout
    vals = dict(l.split(" ", 1) for l in out.splitlines() if " " in l)
    return vals["hostname"], vals["user"]


@SETTINGS
@given(config())
def test_parser_agrees_with_openssh(tmp_path_factory, cfg_expect):
    text, expect = cfg_expect
    cfg = tmp_path_factory.mktemp("h1") / "config"
    cfg.write_text(text)
    listed = {}
    for line in bash("get_configured_ssh_hosts", env={"SSH_CONFIG": str(cfg)}).stdout.splitlines():
        a, hn, user = line.split("|")
        listed[a] = (hn, user)
    assert set(listed) == set(expect)
    for a, (hn, user) in listed.items():
        ssh_hn, ssh_user = _ssh_g(cfg, a)
        assert hn == (expect[a][0] or ""), (a, text)
        if hn:
            assert hn == ssh_hn, (a, text)
        if user:
            assert user == ssh_user, (a, text)


@SETTINGS
@given(config(), st.data())
def test_block_edit_leaves_others_alone(tmp_path_factory, cfg_expect, data):
    text, expect = cfg_expect
    cfg = tmp_path_factory.mktemp("h2") / "config"
    cfg.write_text(text)
    target = data.draw(st.sampled_from(sorted(expect)))
    new_ip = data.draw(ip)
    r = bash('_get_host_block "$A"; _replace_host_block "$_HOST_BLOCK" "Host $A\n    HostName $IP"; echo rc=$?',
             env={"SSH_CONFIG": str(cfg), "A": target, "IP": new_ip})
    assert "rc=0" in r.stdout, r.stderr
    for a in expect:
        if a == target:
            assert _ssh_g(cfg, a)[0] == new_ip
        elif expect[a][0]:
            assert _ssh_g(cfg, a)[0] == expect[a][0], (a, text, cfg.read_text())


@SETTINGS
@given(config())
def test_powershell_parser_agrees_with_openssh(tmp_path_factory, cfg_expect):
    """H1 parity: Get-ConfiguredSSHHosts lists the same aliases with OpenSSH's HostName/User."""
    import shutil
    if not shutil.which("pwsh"):
        return
    from .test_ssh_config_parse import ROOT as R, PS_LIBS
    text, expect = cfg_expect
    home = tmp_path_factory.mktemp("h1ps")
    (home / ".ssh").mkdir()
    (home / ".ssh" / "config").write_text(text)
    libs = "; ".join(f". '{R}/lib/ps/{m}.ps1'" for m in PS_LIBS)
    out = subprocess.run(["pwsh", "-NoProfile", "-Command",
                          f"$env:USERPROFILE = '{home}'; {libs}; Get-ConfiguredSSHHosts | "
                          "ForEach-Object { \"$($_.Alias)|$($_.HostName)|$($_.User)\" }"],
                         capture_output=True, text=True, check=True).stdout
    listed = {l.split("|")[0]: tuple(l.split("|")[1:]) for l in out.splitlines() if l}
    assert set(listed) == set(expect), (text, out)
    for a, (hn, user) in listed.items():
        assert hn == (expect[a][0] or ""), (a, text)
        assert user == (expect[a][1] or ""), (a, text)
