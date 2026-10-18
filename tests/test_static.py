"""
Plan A2–A4: static checks over all shipped code.
"""
import glob
import os
import pwd
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASH_FILES = sorted(glob.glob(f"{ROOT}/lib/bash/*.sh")) + [f"{ROOT}/sshdd.sh"]
PS_FILES = sorted(glob.glob(f"{ROOT}/lib/ps/*.ps1")) + [f"{ROOT}/sshdd.ps1"]


@pytest.mark.skipif(not shutil.which("shellcheck"), reason="shellcheck not installed")
def test_shellcheck_clean():
    """A2: warnings and errors. SC2034 (unused) is off: the libs share globals across files."""
    files = BASH_FILES + sorted(glob.glob(f"{ROOT}/scripts/*.sh"))
    r = subprocess.run(["shellcheck", "-s", "bash", "-S", "warning", "-e", "SC2034", "-f", "gcc", *files],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


BANNED = {  # A3: bash 4+ constructs that break silently on macOS bash 3.2
    r"\$\{[A-Za-z_][A-Za-z0-9_]*(,,|\^\^)": "${var,,} / ${var^^}",
    r"\b(declare|local|typeset)\s+-[a-zA-Z]*A": "associative arrays",
    r"@Q\}": "${var@Q}",
    r"printf\s+['\"]%q": "printf %q",
    r"\bread\b[^\n#]*\s-t\s*[0-9]*\.[0-9]": "fractional read -t",
    r"\b(mapfile|readarray)\b": "mapfile/readarray",
    r"\[\s*-1\s*\]\}": "negative array index",
    r";;&|;&\s*$": "case fall-through",
    r"\bcoproc\b": "coproc",
}


@pytest.mark.parametrize("path", BASH_FILES, ids=os.path.basename)
def test_no_bash4_constructs(path):
    hits = []
    for n, line in enumerate(open(path, encoding="utf-8"), 1):
        code = line.split(" #", 1)[0] if not line.lstrip().startswith("#") else ""
        hits += [f"{n}: {why}: {line.strip()}" for rx, why in BANNED.items() if re.search(rx, code)]
    assert not hits, "\n".join(hits)


needs_pwsh = pytest.mark.skipif(not shutil.which("pwsh"), reason="pwsh not installed")


@needs_pwsh
def test_powershell_parses():
    """A4: no parse errors in any .ps1."""
    script = "; ".join(
        f"$e=$null; [void][System.Management.Automation.Language.Parser]::ParseFile('{f}',[ref]$null,[ref]$e); "
        f"$e | ForEach-Object {{ '{os.path.basename(f)}: ' + $_.Message }}" for f in PS_FILES)
    r = subprocess.run(["pwsh", "-NoProfile", "-Command", script], capture_output=True, text=True)
    assert r.stdout.strip() == "", r.stdout


@needs_pwsh
def test_psscriptanalyzer_risky_rules():
    """A4: the analyzer rules that point at real bugs. Invoke-Expression is allowed only for the
    cloud loader in sshdd.ps1 (it runs the downloaded libs by design)."""
    rules = "PSAvoidAssignmentToAutomaticVariable,PSAvoidUsingInvokeExpression,PSAvoidUsingCmdletAliases"
    script = (f"if (-not (Get-Module -ListAvailable PSScriptAnalyzer)) {{ 'SKIP'; exit }}\n"
              + "\n".join(f"Invoke-ScriptAnalyzer -Path '{f}' -IncludeRule {rules} | ForEach-Object "
                          f"{{ '{os.path.basename(f)}:' + $_.Line + ' ' + $_.RuleName }}" for f in PS_FILES))
    # The temp HOME (T0) hides CurrentUser modules: add the real user's module folder, read-only.
    real_mods = os.path.join(pwd.getpwuid(os.getuid()).pw_dir, ".local/share/powershell/Modules")
    env = dict(os.environ, PSModulePath=real_mods + os.pathsep + os.environ.get("PSModulePath", ""))
    r = subprocess.run(["pwsh", "-NoProfile", "-Command", script], capture_output=True, text=True, timeout=300, env=env)
    if r.stdout.strip() == "SKIP":
        pytest.skip("PSScriptAnalyzer not installed")
    findings = [l for l in r.stdout.splitlines()
                if l.strip() and not (l.startswith("sshdd.ps1:") and "InvokeExpression" in l)]
    assert not findings, "\n".join(findings)


def test_no_set_u():
    """bash 3.2 + set -u: "${arr[@]}" on an empty array is an "unbound variable" crash."""
    import re as _re
    for path in BASH_FILES:
        for n, line in enumerate(open(path, encoding="utf-8"), 1):
            code = line.split("#", 1)[0]
            assert not _re.search(r"\bset\s+-[a-z]*u|set\s+-o\s+nounset", code), f"{path}:{n}: {line.strip()}"
