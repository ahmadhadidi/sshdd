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
- **A2** 🔨 `shellcheck` all bash at error+warning level, with a reviewed allowlist.
- **A3** 🔨 bash-3.2 ban list as a test (`${x,,}`, `declare -A`, `${x@Q}`, `printf %q`, `read -t 0.x`, `mapfile`).
- **A4** 🔨 PowerShell: parser has 0 errors on every `.ps1`; PSScriptAnalyzer if installed.

### U — unit (bash and PowerShell)
- **U1** ✅ config getters: case, tabs, `Key=value` (bash + PS).
- **U2** 🔨 `_replace_host_block` with `$`, `@`, `\`, `/`, quotes and regex characters in the block: other blocks untouched byte-for-byte.
- **U3** 🔨 `_sq`: round-trips any string through `bash -c`.
- **U4** 🔨 `_visual_width` for ASCII, wide emoji, emoji + VS16, CJK.
- **U5** 🔨 `_hint_bar` never exceeds width (1…300) and keeps the last pair.
- **U6** ✅ host selection: typed alias, unique filter, digits shorthand, unknown text (bash + PS).
- **U7** 🔨 `get_hosts_using_key`, `get_identity_files_for_host` with `~`, `$HOME`, quotes, spaces.
- **U8** 🔨 `_write_key_pair`: modes 600/644, exactly one trailing newline.

### H — property tests
- **H1** 🔨 random valid ssh_config files: `get_configured_ssh_hosts` matches `ssh -G <alias> -F file` (hostname, user) for every alias.
- **H2** 🔨 random add/remove of IdentityFile and Host blocks: unrelated lines unchanged, file still parses with `ssh -G`.
- **H3** 🔨 random text into every free-text prompt: no crash, no shell evaluation, screen stays inside its box.

### S — screens (pyte)
- **S1** 🔨 every screen at 80×24, 100×40, 200×60: no line wider than the terminal, no wrap, title box intact.
- **S2** ✅ main menu bars share the reverse-video background · ✅ F5 title box · 🔨 all op screens use the same box.
- **S3** 🔨 spinner visible during host probes and remote ops; gone afterwards.
- **S4** 🔨 every screen shows a hint bar listing exactly the keys it handles.
- **S5** 🔨 every op ends with a result line and "Press any key", then the menu.
- **S6** 🔨 defaults shown pre-filled (`--user`, `--subnet`, `--comment-suffix`).
- **S7** 🔨 emoji rows align (icon column) at every width.
- **S8** 🔨 `?` help and F1 open, page, and close with Q/Esc.
- **S9** 🔨 main menu with 0, 1, 50, 200 configured hosts: scrolling, selection visible.

### K — keyboard
- **K1** ✅ Esc cancels at the first and later prompts (G, W, T) · 🔨 every prompt of every op.
- **K2** ✅ one Q quits from the main menu · 🔨 Q never quits from inside an op.
- **K3** 🔨 every hotkey and its lowercase; unknown keys ignored.
- **K4** ✅ arrow latency < 80 ms; held-down arrows never dropped · 🔨 same in pickers and pagers.
- **K5** 🔨 Home/End/PgUp/PgDn wherever a list or pager is shown.
- **K6** 🔨 type-to-filter, Backspace, Ctrl+W in pickers and text prompts; paste of 2 KB text.

### X — termination and terminal state
- **X1** ✅ Ctrl+C, Ctrl+Z, SIGTERM, SIGHUP at the menu and during host probes.
- **X2** 🔨 same during ssh, ssh-keygen, pager, conf editor, `$EDITOR`.
- **X3** ✅ shell prompt position after exit in tmux and herdr (`test_exit_cursor.py`), and startup when the terminal ignores the cursor query — TODO #9.
- **X4** 🔨 SIGWINCH (resize) on every screen: full redraw, nothing left over.

### E — environment and errors
- **E1** ✅ new key name validation (#4).
- **E2** 🔨 no `~/.ssh`, no config (F2 creates it, mode 600), unreadable config, config is a symlink.
- **E3** 🔨 no `perl`, no `sshpass`, no `curl` (cloud run message).
- **E4** 🔨 `LANG=C`, `TERM=vt100`, `TERM=dumb`, 40×10 terminal: degrade without garbage.
- **E5** 🔨 unreachable host, wrong password, host key changed, remote without `~/.ssh`: clear message, back to menu.

### D — data safety
- **D1** 🔨 every config edit keeps comments, `Include`, `Match`, `Host *` and other blocks byte-for-byte.
- **D2** 🔨 permissions: `~/.ssh` 700, private keys 600, config 600 after every op.
- **D3** 🔨 delete operations remove only what was confirmed.

### Z — security
- **Z1** 🔨 key name, comment, host, user, password containing `'`, `"`, `$(…)`, `` ` ``, `;`, newline: no command runs locally or on the remote (canary file).
- **Z2** 🔨 password never in the debug log, never in `ps` output for longer than the call, temp files 600/700.
- **Z3** 🔨 remote `authorized_keys` edits leave other users' keys and the file mode intact.

### R — remote (CT 213)
- **R1–R4** ✅ install, test, delete, promote, list, add config block (existing 01–07).
- **R5** 🔨 password auth and key auth for every remote op.
- **R6** 🔨 unreachable host / closed port.
- **R7** 🔨 duplicate key already in `authorized_keys`: not added twice.
- **R8** 🔨 passphrase-protected key.

### C — cloud
- **C1** ✅ cloud loader runs clean from an HTTP copy of the repo.
- **C2** 🔨 download failure: one clear message, exit 1.

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
