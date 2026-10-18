# sshdd test plan (TODO #8)

Goal: every behaviour a user can reach is covered by an automated test that fails when it breaks.
Status per test: ✅ built · 🔨 to build · 🚫 needs a tool or platform not available yet.

## How the tests see the app

| Layer | Tool | What it proves |
|---|---|---|
| Static | `bash -n`, `shellcheck`, PS parser, bash-3.2 ban list | code parses, no known shell traps |
| Unit (bash) | pytest + `bash -c 'source lib…'` | one function's output for one input |
| Unit (PowerShell) | pytest + `pwsh -Command '. lib…'` | same, for `lib/ps` |
| Property | hypothesis, OpenSSH `ssh -G` as the oracle | parsers agree with OpenSSH on generated configs |
| Screen | pexpect + pyte (`tests/screen.py`) under `/proj/bash32` | what a terminal shows: text, colours, cursor |
| Real terminal | tmux, herdr (`--session sshdd-test`) | behaviour inside the terminals Ahmad uses |
| Remote | CT 213 `sshdd-test` on ho4 | real SSH: keys, passwords, authorized_keys |
| Platforms | GitHub Actions macOS + Windows runners | macOS bash 3.2 + BSD tools, Windows PowerShell 5.1 |

Rule for every test: isolated `HOME` (temp dir); never the real `~/.ssh` (T0).

## Usability heuristics → what we test

| Heuristic | sshdd requirement | Tests |
|---|---|---|
| 1 Visibility of system status | spinner during every wait over ~200 ms; reachability dots; op title on every screen; every op ends with an explicit ✓/✗ line | S3, S5, R* |
| 2 Match the real world | ssh vocabulary (Host, HostName, IdentityFile); prompts say what's expected and the default | S6 |
| 3 User control & freedom | Esc cancels at every prompt; Q quits from the main menu only; Ctrl+C/Z, kill, closed terminal leave a clean terminal | K1–K3, X1–X4 |
| 4 Consistency | same title box, bars and keys on every screen; bash = PowerShell | S1, S2, P1 |
| 5 Error prevention | names validated; destructive actions confirm with default No; no silent overwrite | E1–E4, D1 |
| 6 Recognition over recall | hint bar on every screen lists its keys; lists of hosts/keys instead of typing | S4 |
| 7 Flexibility & efficiency | hotkeys, type-to-filter, subnet shorthand, keys respond < 80 ms, key repeat never drops keys | K4–K6 |
| 8 Minimal, fits the screen | nothing wraps or overlaps at 80×24 … 200×60; emoji widths right | S1, S7 |
| 9 Recover from errors | every failure says what failed and what to do; app stays usable after it | R5–R8, E5 |
| 10 Help | `?` help and F1 reachable from the main menu and accurate | S8 |
| Shneiderman: closure | each op ends with "Press any key" then returns to the menu | S5 |
| Shneiderman: reduce memory load | defaults pre-filled (user, subnet, comment suffix) | S6 |

## Test catalogue

### T — test hygiene
- **T0** ✅ every test runs with a temp `HOME` (`conftest.isolated_home`, autouse): empty config, only CT 213's `known_hosts` entry. OpenSSH ignores `$HOME` (it uses the passwd home dir), so `ssh`/`scp` wrappers first on PATH add `-F $HOME/.ssh/config` and `UserKnownHostsFile` unless the caller passed `-F`.
- **T1** ✅ the run errors if the real `~/.ssh` changed (`conftest.real_ssh_untouched`) · 🔨 same for `/tmp/.hprobe-*`, `/tmp/.ssh-askpass-*`.

### A — static
- **A1** ✅ `bash -n` all scripts (pre-commit, `make check`).
- **A2** ✅ `shellcheck -S warning` on all bash, SC2034 off (globals shared across files) — `test_static.py`.
- **A3** ✅ bash-3.2 ban list per file — `test_static.py`.
- **A4** ✅ PS parser 0 errors; PSScriptAnalyzer risky rules (automatic-variable assignment, Invoke-Expression outside the loader, aliases) — `test_static.py`.

### U — unit (bash and PowerShell)
- **U1** ✅ config getters: case, tabs, `Key=value` (bash + PS).
- **U2** ✅ `_replace_host_block` with `$ @ \ / ' " `…`` in the block, perl and python3 paths; delete keeps other blocks byte-for-byte — `test_units.py`.
- **U3** ✅ `_sq` round-trips random text through `eval` (hypothesis).
- **U4** ✅ `_visual_width` for ASCII, wide emoji, emoji + VS16, wide symbols; every app label matches `wcwidth`.
- **U5** ✅ `_hint_bar` exactly fills widths 1–300, keeps `Q Quit` (hypothesis).
- **U6** ✅ host selection: typed alias, unique filter, digits shorthand, unknown text (bash + PS).
- **U7** ✅ `get_hosts_using_key`, `get_identity_files_for_host` with `~`, `$HOME`, quotes, spaces, `=`, look-alike names.
- **U8** ✅ `_write_key_pair`: mode 600, exactly one trailing newline.

### H — property tests
- **H1** ✅ random valid configs: bash and PS host lists match `ssh -G` — `test_properties.py`.
- **H2** ✅ random Host-block replacement: other blocks resolve unchanged with `ssh -G`.
- **H3** 🔨 random text into every free-text prompt: no crash, no shell evaluation, screen stays inside its box.

### S — screens (pyte)
- **S1** ✅ every screen at 80×24, 100×40, 200×60: title box intact, all borders in one column — `test_screens.py`.
- **S2** ✅ main menu bars share the reverse-video background · ✅ F5 title box · 🔨 all op screens use the same box.
- **S3** 🔨 spinner visible during host probes and remote ops; gone afterwards.
- **S4** ✅ every screen shows key hints · 🔨 hints match the keys each screen really handles.
- **S5** ✅ errors stay on screen behind "Press any key" (`_OP_ERROR`) · 🔨 every op's result line.
- **S6** 🔨 defaults shown pre-filled (`--user`, `--subnet`, `--comment-suffix`).
- **S7** 🔨 emoji rows align (icon column) at every width.
- **S8** ✅ F1 opens and closes · 🔨 `?` help paging.
- **S9** ✅ menu scrolls at 24 rows with the selection always visible · 🔨 pickers with 50/200 hosts.

### K — keyboard
- **K1** ✅ Esc at every prompt of every operation (13 ops, 34 prompts): back to the menu, `~/.ssh` unchanged, one Q quits — `test_flows.py`. Esc at the passphrase cancels.
- **K2** ✅ one Q quits from the main menu; every screen returns to the menu instead of quitting.
- **K3** ✅ every hotkey and its lowercase; unknown keys (letters, F12, Ctrl+Up) ignored; E runs `$EDITOR` on the config.
- **K4** ✅ arrow latency < 80 ms; held-down arrows never dropped · 🔨 same in pickers and pagers.
- **K5** 🔨 Home/End/PgUp/PgDn wherever a list or pager is shown.
- **K6** 🔨 type-to-filter, Backspace, Ctrl+W in pickers and text prompts; paste of 2 KB text.

### X — termination and terminal state
- **X1** ✅ Ctrl+C, Ctrl+Z, SIGTERM, SIGHUP at the menu and during host probes.
- **X2** 🔨 same during ssh, ssh-keygen, pager, conf editor, `$EDITOR`.
- **X3** ✅ shell prompt position after exit in tmux and herdr (`test_exit_cursor.py`), and startup when the terminal ignores the cursor query — TODO #9.
- **X4** ✅ resize redraws the menu, key list, View Config, Conf Defaults and pickers (shrink and grow) · limit: an op's title box above a picker isn't redrawn.

### E — environment and errors
- **E1** ✅ new key name validation (#4).
- **E2** ✅ symlinked config (bash + PS) · ✅ no `~/.ssh` / no config: prompt waits; Y/Enter creates 700/600, N/Esc declines · ✅ unreadable config: warning bar, no raw errors — `test_environment.py`.
- **E3** ✅ no perl (python3 fallback for block lookup and edits) · ✅ no curl/unreachable download: one clear message (C2) · 🔨 no `sshpass`.
- **E4** ✅ `LANG=C`, `TERM=vt100`, `TERM=dumb`, 40×10: start, title box intact, Q quits.
- **E5** 🔨 unreachable host, wrong password, host key changed, remote without `~/.ssh`: clear message, back to menu.

### D — data safety
- **D1** 🔨 every config edit keeps comments, `Include`, `Match`, `Host *` and other blocks byte-for-byte.
- **D2** ✅ PS imported private key 600 · 🔨 every op.
- **D3** ✅ Delete Local Key: "None" is the default remote choice; local files only after an explicit yes · 🔨 other deletes.

### Z — security
- **Z1** ✅ PS key generation (comment/passphrase literal, both argument modes) · ✅ remote key removal bash + PS on CT 213 (canary) · ✅ key names can't leave `~/.ssh` (G, W, import; bash + PS) · 🔨 host/user/password through every op.
- **Z2** 🔨 password never in the debug log, never in `ps` output for longer than the call, temp files 600/700.
- **Z3** ✅ remote key removal keeps other keys and mode 600 (bash + PS) · 🔨 install/promote paths.

### R — remote (CT 213)
- **R1–R4** ✅ end to end on CT 213 (`test_remote_ops.py`, 01, `test_lxc_connection.py`): generate & install, install, test (authorized / not), delete (others and mode kept), list · 🔨 promote (P), add config block (N), append hostname (A). Note: the older tests 02–07 only open each screen.
- **R5** 🔨 password auth and key auth for every remote op.
- **R6** 🔨 unreachable host / closed port.
- **R7** ✅ installing a key that's already there doesn't duplicate it; a last line without newline isn't corrupted.
- **R8** 🔨 passphrase-protected key.

### C — cloud
- **C1** ✅ cloud loader runs clean from an HTTP copy of the repo.
- **C2** ✅ download failure: one clear message, exit 1.

### P — parity and platforms
- **P1** 🔨 PowerShell TUI driven by pexpect + pyte under `pwsh` on Linux: same screens and keys as bash (S, K tests parametrised by implementation).
- **P2** 🚫 macOS: whole suite on a GitHub Actions `macos-latest` runner (system bash 3.2, BSD sed/awk/dd). Not approved (2026-10-18); run by hand on the Mac meanwhile.
- **P3** 🚫 Windows PowerShell 5.1: PS tests on a `windows-latest` runner. Not approved (2026-10-18).

## Tools

| Tool | Status | Why |
|---|---|---|
| pytest, pexpect | installed | runner, pty driving |
| pyte | installed 2026-10-17 | rendered-screen assertions |
| bash 3.2 (`/proj/bash32`) | installed | the macOS shell |
| shellcheck 0.9 | installed 2026-10-17 | A2 |
| tmux 3.4, herdr 0.8.2 | installed | X3, real-terminal checks |
| pwsh | installed | U*, P1 |
| CT 213 on ho4 | running | R* |
| hypothesis 6.170 | installed 2026-10-18 | H1–H3 |
| PSScriptAnalyzer 1.25 | installed 2026-10-18 (CurrentUser) | A4 |
| GitHub Actions macOS + Windows runners | not approved | P2/P3 |

## Findings while building the tests

- OpenSSH reads `~/.ssh` from the passwd home dir, not `$HOME`, while sshdd edits `$HOME/.ssh/config`. Same dir in normal use; differs under `sudo -E` or a changed `HOME` (then sshdd's edits don't reach `ssh`). Not fixed; would need `-F "$SSH_CONFIG"` on every ssh call.
- PS `Add-SSHKeyInHost` ran ssh-keygen through `Invoke-Expression`: a comment with `$(…)` executed, passphrases with `$`/`"` were altered. Fixed (args + `ConvertTo-NativeArgument`).
- PS turned the passphrase back into text with `PtrToStringAuto`, which on macOS/Linux pwsh returns only its first character. Fixed (NetworkCredential).
- Remote key removal (bash + PS) pasted the key inside '…' in the remote command: a comment with `'` ran on the remote (proven on CT 213), and `mv` from a temp file reset authorized_keys to the temp file's mode (600→644 on CT 213; 664 under umask 002 locks every key out). Fixed: key on stdin, file rewritten in place. PS also reported success when ssh failed.
- `_replace_host_block`: perl got the blocks pasted into its code, so every block with `/` (any IdentityFile path) failed and the python fallback did the work; python then failed on backslashes (Windows paths) and the edit was silently lost; two callers ignored the failure, one appended a duplicate Host block. Fixed (blocks via environment, callers report failure).
- Deleting a host left its trailing newline, and the removal screen then rewrote the whole config with `sed` (trailing spaces stripped, blank lines squeezed in every block). Fixed: the block goes with its newline; no whole-file rewrite.
- Parsers vs OpenSSH (H1): a repeated HostName/User showed the last value (OpenSSH uses the first); lowercase `host` lines weren't found by `_get_host_block`; alias `a` matched `Host a-b`; `get_hosts_using_key k2` matched `xk2`. PS: the alias was pasted into the regex unescaped. Fixed in bash and PS (`Get-HostBlockPattern`).
- `_write_key_pair` stripped only one trailing newline from a pasted key.
- `_visual_width` counted text-presentation emoji (🗑 🗝 🏚 👁, Unicode width 1) as 2 columns: the title box's right border was one column off on Delete Remote/Local, List Keys, Remove Host and View Config (screenshot `handoff/view-config-before-after.png`). Likely the old todo1 note "View SSH Config box looks broken".
- Bash config edits used `perl -i`, which replaces a symlinked config (dotfile managers) with a plain file; the real config stopped getting edits. Fixed: write through the file.
- PS wrote files with a UTF-8 BOM (`WriteAllText(…UTF8)` always; `Set-Content -Encoding UTF8` on Windows PowerShell 5.1). OpenSSH rejects a BOM config entirely (`Bad configuration option: \357\273\277host`, every connection fails) and a BOM private key (`error in libcrypto`), checked with OpenSSH here; Win32-OpenSSH not verified. Imported keys were also mode 664 on macOS/Linux pwsh (ssh refuses them), and `-replace` treated `$…` in a config block as substitutions. Fixed: `Write-TextFile` (no BOM, path resolved by PowerShell), chmod 600, literal `.Replace`.
- The missing-config prompt (`Create ~/.ssh/config now? [Y/n]`) used `read` in the menu's raw mode (100 ms timeout): it returned empty at once and the default Y created the file before anyone could answer. Fixed: waits for one key.
- An unreadable config printed raw `awk: cannot open … Permission denied` and every list was silently empty. Fixed: parsers skip it; the menu shows a warning with the chmod fix.
- Without perl, `_get_host_block` returned nothing, so every config edit did nothing. Fixed: python3 fallback.
- Every key loop blocked in `read -n1` (forces VMIN=1), so nothing redrew on terminal resize until a key was pressed. Fixed: dd-based polling (`_wait_key`, `KEY_RESIZE`); dd ignores Ctrl+Z/C so a stopped dd can't hang sshdd.
- **Delete Local Key removed the key everywhere after two Enters**: the remote list highlighted "-- ALL" first, and the local private key was deleted with no confirmation. Fixed: "None" first, then "Delete …? [y/N]" (bash + PS).
- **`set -u` on bash 3.2 crashed sshdd on any empty array** (`"${arr[@]}"` = unbound variable; bash ≥ 4.4 doesn't). Hit by "skip remote" in Delete Local Key; 31 such expansions. Fixed: no `set -u` (shellcheck covers typos); `test_static.py` keeps it out.
- Errors in operations returned 1, which also means "skip Press any key", so the message flashed away (e.g. empty import path). Fixed: `_out error` sets `_OP_ERROR` and the ack is shown.
- The passphrase prompt (`read -s`) took Esc as a character: the key got a passphrase containing `\x1b`. Fixed: `read_secret` (Esc cancels, Backspace edits). Generate & Install also carried on after a cancelled key generation.
- **Key names could leave `~/.ssh`**: G and Import took `../../x` and ssh-keygen / the import wrote there. Fixed: `_valid_key_name` / `Test-SSHKeyName` where keys are written (generation and import), not only in W's prompt.
- **Install appended the key every time** (duplicates in `authorized_keys`) and glued it onto a last line without a newline, breaking both keys. Fixed: one shared remote install command (bash `_REMOTE_INSTALL_CMD`, PS `RemoteInstallCommand`) that appends only if absent, fixes the newline, and creates `~/.ssh` 700 / `authorized_keys` 600.
