"""
Plan U2–U8: bash helpers, one function at a time, under bash 3.2.
"""
import os
import shutil
import stat
import subprocess

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from .screen import BASH32, ROOT

LIBS = ["tui", "ssh-config", "ssh-helpers", "prompts", "ssh-ops", "config-display", "menu", "menu-support", "menu-renderer"]
SOURCE = " ".join(f"source {ROOT}/lib/bash/{m}.sh;" for m in LIBS)
FAST = settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])


def bash(snippet, env=None, path=None):
    e = dict(os.environ, **(env or {}))
    if path is not None:
        e["PATH"] = path
    r = subprocess.run([BASH32, "-c", f"{SOURCE}\n{snippet}"], env=e, capture_output=True, timeout=30)
    # bytes, decoded without newline translation (text=True would turn \r into \n)
    r.stdout, r.stderr = r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")
    return r


# ── U2: _replace_host_block ───────────────────────────────────────────────────

OTHER = "# keep: comment\nInclude ~/.ssh/conf.d/*\n\nHost other\n    HostName 9.9.9.9   \n    User  me\n\n"
TARGET = "Host t\n    HostName 1.1.1.1\n    IdentityFile ~/.ssh/k1\n"
NASTY = "    IdentityFile C:\\Users\\me\\.ssh\\k2 @team $HOME %d/x\\n '\"`$(touch /tmp/no)` /path/with/slashes\n"


def _no_perl_path(tmp_path):
    """A PATH with everything except perl, to force the python3 fallback."""
    d = tmp_path / "noperl"
    d.mkdir()
    for tool in ("python3", "cat", "sed", "awk", "grep", "tr", "dirname", "basename", "stty", "mktemp", "rm"):
        p = shutil.which(tool)
        if p:
            os.symlink(p, d / tool)
    return str(d)


@pytest.mark.parametrize("engine", ["perl", "python3"])
def test_replace_host_block_takes_text_literally(tmp_path, engine):
    cfg = tmp_path / "config"
    cfg.write_text(OTHER + TARGET)
    # Old block passed in directly: _get_host_block itself needs perl.
    r = bash('_replace_host_block "$OLD" "$NEW"; echo rc=$?',
             env={"SSH_CONFIG": str(cfg), "OLD": TARGET.rstrip("\n"), "NEW": (TARGET + NASTY).rstrip("\n")},
             path=None if engine == "perl" else _no_perl_path(tmp_path))
    assert "rc=0" in r.stdout, r.stdout + r.stderr
    assert cfg.read_text() == OTHER + TARGET + NASTY
    assert not os.path.exists("/tmp/no")


@pytest.mark.parametrize("engine", ["perl", "python3"])
def test_replace_host_block_delete_keeps_others(tmp_path, engine):
    cfg = tmp_path / "config"
    cfg.write_text(OTHER + TARGET + "Host z\n    HostName 3.3.3.3\n")
    bash('_replace_host_block "$OLD" ""', env={"SSH_CONFIG": str(cfg), "OLD": TARGET.rstrip("\n")},
         path=None if engine == "perl" else _no_perl_path(tmp_path))
    assert cfg.read_text() == OTHER + "Host z\n    HostName 3.3.3.3\n"


# ── U3: _sq quotes anything for a shell ───────────────────────────────────────

@FAST
@given(st.text(alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"), max_size=40))
def test_sq_round_trips(value):
    r = bash('eval "printf %s $(_sq "$V")"', env={"V": value})
    assert r.stdout == value


# ── U4: _visual_width ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("text,cols", [
    ("abc", 3), ("🔑  Key", 7), ("🗑️  Del", 7), ("🗑   Del", 7), ("👁  View", 7), ("🗝", 1), ("🏚x", 2),
    ("✨ x", 4), ("❌", 2), ("── x", 4), ("", 0),
])
def test_visual_width(text, cols):
    assert bash('_visual_width "$T"', env={"T": text}).stdout.strip() == str(cols)


# ── U5: _hint_bar always fits ─────────────────────────────────────────────────

@FAST
@given(st.integers(min_value=1, max_value=300))
def test_hint_bar_fits_any_width(width):
    r = bash('_hint_bar "$W" Up/Dn Navigate Enter Select G Generate T Test D Delete L List Q Quit; '
             'printf "%s" "$_HINT_BAR"', env={"W": str(width)})
    import re
    plain = re.sub(r"\x1b\[[0-9;]*m", "", r.stdout)
    assert len(plain) == width
    if width >= len("  Q Quit"):
        assert "Q Quit" in plain


# ── U7: key ↔ host lookups ────────────────────────────────────────────────────

def test_hosts_using_key_and_identity_files(tmp_path):
    cfg = tmp_path / "config"
    cfg.write_text('Host a\n    HostName 1.1.1.1\n    IdentityFile "~/.ssh/my key"\n'
                   'Host b\n    HostName 2.2.2.2\n    IdentityFile $HOME/.ssh/k2\n'
                   'Host c\n    HostName 3.3.3.3\n    IdentityFile ~/.ssh/k2-old\n'
                   'Host d\n    HostName 4.4.4.4\n    IdentityFile ~/.ssh/xk2\n'
                   'Host e\n    hostname 5.5.5.5\n    identityfile="/keys/k2"\n')
    r = bash('get_hosts_using_key k2; echo --; get_identity_files_for_host a', env={"SSH_CONFIG": str(cfg)})
    using, files = r.stdout.split("--\n")
    assert using.splitlines() == ["b|2.2.2.2|", "e|5.5.5.5|"]
    assert files.splitlines() == ["~/.ssh/my key"]


# ── U8: _write_key_pair ───────────────────────────────────────────────────────

def test_write_key_pair_modes_and_newline(tmp_path):
    priv, pub = tmp_path / "k", tmp_path / "k.pub"
    bash('_write_key_pair "$P" "$Q" "$PRIV" "$PUB"',
         env={"P": str(priv), "Q": str(pub), "PRIV": "-----BEGIN-----\nx\n-----END-----\n",
              "PUB": "ssh-ed25519 AAAA c\n\n\n", "SSH_DIR": str(tmp_path)})
    assert stat.S_IMODE(priv.stat().st_mode) == 0o600
    assert pub.read_text() == "ssh-ed25519 AAAA c\n"


def test_visual_width_matches_wcwidth_for_every_app_label():
    """U4: every quoted label with an emoji in lib/bash has the width wcwidth (terminals' table) gives."""
    import re
    import wcwidth
    labels = set()
    for f in sorted(os.listdir(f"{ROOT}/lib/bash")):
        if f.endswith(".sh"):
            for m in re.finditer(r'"([^"\n$`\\]*[\U0001F000-\U0001FFFF☀-➿][^"\n$`\\]*)"',
                                 open(f"{ROOT}/lib/bash/{f}", encoding="utf-8").read()):
                labels.add(m.group(1))
    assert len(labels) > 15
    script = 'while IFS= read -r l; do _visual_width "$l"; echo; done'
    r = subprocess.run([BASH32, "-c", f"{SOURCE}\n{script}"], input="\n".join(sorted(labels)) + "\n",
                       capture_output=True, text=True, timeout=60)
    got = dict(zip(sorted(labels), map(int, r.stdout.split())))
    wrong = {l: (got[l], wcwidth.wcswidth(l)) for l in labels if got[l] != wcwidth.wcswidth(l)}
    assert not wrong, wrong


@pytest.mark.parametrize("engine", ["perl", "python3"])
def test_replace_host_block_writes_through_symlink(tmp_path, engine):
    """E2: a symlinked config (dotfile managers) stays a symlink and its target gets the edit;
    the file keeps its mode."""
    real = tmp_path / "dotfiles" / "config"
    real.parent.mkdir()
    real.write_text(OTHER + TARGET)
    real.chmod(0o600)
    link = tmp_path / "config"
    link.symlink_to(real)
    bash('_replace_host_block "$OLD" ""', env={"SSH_CONFIG": str(link), "OLD": TARGET.rstrip("\n")},
         path=None if engine == "perl" else _no_perl_path(tmp_path))
    assert link.is_symlink()
    assert real.read_text() == OTHER
    assert stat.S_IMODE(real.stat().st_mode) == 0o600
