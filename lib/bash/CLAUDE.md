# Bash Implementation

See root `CLAUDE.md` for project overview and running instructions.

## Architecture (Bash)

`sshdd.sh` parses CLI args, sets globals, then sources the lib modules in order and calls `show_main_menu()`. The lib modules are loaded locally from `lib/bash/` when the directory exists, or fetched via `curl` from the GitHub raw URL when run remotely.

### Library load order

```
tui → ssh-config → ssh-helpers → prompts → ssh-ops → config-display → menu → menu-support → menu-renderer
```

Each module has a guard variable (`_<MODULE>_SH_LOADED`) to prevent double-sourcing.

### Cross-file dependencies

When modifying a module, these are the other files that call its functions:

| Modified module | Must also check | Key cross-module calls |
|---|---|---|
| `tui.sh` | all 5 others | `_repeat`, `_term_size`, `_regex_escape`, `_dbg` used everywhere; `select_from_list` called from prompts/ssh-ops/config-display/menu; `_read_key`/`_read_key_nb` used by prompts/config-display/menu |
| `ssh-config.sh` | ssh-helpers, prompts, ssh-ops, config-display, menu | `get_configured_ssh_hosts` (prompts×2, ssh-ops×2, config-display, menu×2); `_get_host_block`/`_replace_host_block` (ssh-ops×3, config-display, menu); `get_alias_for_host_ip` (ssh-helpers); `get_identity_files_for_host` (ssh-helpers, menu) |
| `ssh-helpers.sh` | ssh-ops, config-display, menu | `_out`/`_out_item` called throughout ssh-ops and menu; `show_op_banner` (config-display×3, menu×9); `_prompt_remote` (ssh-ops×2, menu×3); `_ssh_fence`/`_ssh_fence_close` (ssh-ops×4, menu×4); `_setup_askpass`/`_destroy_askpass` (menu only) |
| `prompts.sh` | ssh-ops, config-display, menu | `read_ssh_key_name` (ssh-ops×2, menu×3); `find_private_key` (ssh-ops, menu×2); `resolve_ssh_target` (ssh-ops×2, menu×2); `confirm_user_choice` (ssh-ops×2, config-display, menu×2); `read_colored_input` (ssh-ops×3, config-display×2, menu×2) |
| `ssh-ops.sh` | menu only | All 11 public functions called exclusively from `_menu_*` handlers in menu.sh |
| `config-display.sh` | menu only | `show_ssh_config_file`, `edit_ssh_config_file`, `show_ssh_key_inventory`, `remove_host_from_ssh_config` called from `_menu_*` handlers in menu.sh |
| `menu.sh` | menu-renderer only | `invoke_menu_choice` called from `_invoke_choice` in menu-renderer.sh; `_check_config_at_start`, `_do_create_config` called from `show_main_menu` in menu-renderer.sh |
| `menu-support.sh` | menu-renderer only | `_run_conf_editor` called from `_menu_conf_defaults` in menu.sh; `_show_menu_help` called from `show_main_menu` in menu-renderer.sh |

### Module breakdown

| File | Lines | Responsibility | Key functions |
|------|-------|----------------|---------------|
| `tui.sh` | ~532 | Terminal primitives, TUI widgets | `_read_key`:96, `_read_key_raw`:139, `select_from_list`:360, `select_multi_from_list`:245, `show_paged`:188 |
| `ssh-config.sh` | ~156 | `~/.ssh/config` parsing | `get_configured_ssh_hosts`:14, `_get_host_block`:49, `_replace_host_block`:143, `get_alias_for_host_ip`:109 |
| `ssh-helpers.sh` | ~335 | Shared SSH utility helpers and output helpers | `_out`:19, `show_op_banner`:55, `_prompt_remote`:323, `_setup_askpass`:256 |
| `prompts.sh` | ~520 | Input prompts and host/key finders | `read_colored_input`:25, `read_remote_host_address`:267, `confirm_user_choice`:438 |
| `ssh-ops.sh` | ~592 | SSH key operations | `deploy_ssh_key_to_remote`:15, `test_ssh_connection`:92, `add_ssh_key_in_host`:268, `import_external_ssh_key`:425 |
| `config-display.sh` | ~479 | SSH config viewer, key inventory display, host removal | `show_ssh_config_file`:12, `show_ssh_key_inventory`:189, `remove_host_from_ssh_config`:140 |
| `menu.sh` | ~437 | Menu dispatcher and all 18 `_menu_*` handlers | `invoke_menu_choice`:17, `_menu_generate_and_install`:44, `_do_create_config`:402 |
| `menu-support.sh` | ~258 | Conf defaults editor TUI and menu help screen | `_run_conf_editor`:63, `_show_menu_help`:174 |
| `menu-renderer.sh` | ~358 | TUI event loop, operation runner | `_invoke_choice`:13, `show_main_menu`:38 |

### Control flow

1. Parse CLI args → set defaults
2. `show_main_menu()` enters the event loop (raw terminal, non-blocking key reads with ~50ms timeout for resize detection)
3. User selects one of 17 menu options → `invoke_menu_choice()` dispatches to the appropriate function
4. Operation completes → `wait_user_acknowledge()` → return to menu

### tui.sh

- `_dbg`:12, `_term_size`:19, `_visual_width`:37, `_regex_escape`:55, `_repeat`:60, `_max`:66, `_min`:67
- `_esc_drain` — reads the rest of an ESC sequence into `_ESC_TAIL`. Only a bare Esc waits (100 ms): the byte after ESC is read by `dd` under `stty min 0 time 1`; the rest of a CSI/SS3 sequence is read with `read -r -n1` up to its final byte (letters or `~`). One `dd` fork per ESC-prefixed key. Accepts an optional stty restore spec.
- `_read_key`:96 / `_read_key_nb`:118 / `_read_key_raw`:139 — Raw terminal key capture, handles multi-byte escape sequences (arrow keys). Uses `stty` raw mode; avoid adding subprocess forks inside the render loop.
- `wait_user_acknowledge`:178 — "Press any key" gate (also in menu.sh dispatcher)
- `show_paged`:188 — Paginator for long output.
- `format_menu_label`:222 — Hotkey character highlighting.
- `select_multi_from_list`:245 — Checkbox list with Space toggle, Enter confirm, ESC cancel.
- `select_from_list`:360 — Core combo-box widget with incremental filtering — used for picking hosts, keys, and users throughout. Render loop uses `printf -v` (zero-fork) instead of `$(printf ...)`.
- ANSI escape sequences used directly (cursor positioning, colors, bold, hide/show cursor).
- Terminal resize detected by comparing `tput cols/lines` between key-read cycles.

### ssh-config.sh

Reads `~/.ssh/config` using `perl`, `awk`, `grep`:
- `get_configured_ssh_hosts`:14 — emits `alias|hostname|user` tuples
- `get_available_ssh_keys`:28 — lists private keys in `~/.ssh`
- `_get_host_block`:49 / `_replace_host_block`:143 — multiline Host block read/write. Values go to perl/python through the environment, never pasted into their code. Matching rules (keyword case, `=`, alias boundary, first value wins) are checked against `ssh -G` by `tests/test_properties.py`
- `_block_field`:101 — extract a single field from a Host block
- `get_identity_files_for_host`:60 / `get_hosts_using_key`:87 — cross-reference keys and hosts
- `get_alias_for_host_ip`:109 — reverse-lookup Host alias from a HostName IP
- `get_ip_from_host_config`:118, `get_user_from_host_config`:124, `get_identity_file_from_host_config`:130

### ssh-helpers.sh

Shared helpers sourced by both `ssh-ops.sh` and `menu.sh`. Must be loaded after `tui` and `ssh-config` (depends on `_repeat` and `get_alias_for_host_ip`).

**Output helpers:**
- `_out`:19 `STYLE FORMAT [ARGS...]` — 2-space indented, color-coded line to stdout.
  Styles: `ok` (green), `warn` (yellow), `error` (red), `info` (cyan), `dim` (gray), `heading` (bright-cyan), `plain` (bright-white).
- `_out_item`:38 `FORMAT [ARGS...]` — green `+` prefix, plain text.
- `show_op_banner`:55
- `_draw_op_header`:150 `label` — teal box header (stream mode: clears screen, prints rows 2-6 box + row 7 blank; buffer mode: set `_OP_HDR_ROW` before calling, reads result from `_OP_HDR_BUF`). Uses `_visual_width` for correct centering. Always sets `_OP_HDR_HEIGHT=7`.

**SSH/filesystem helpers:**
- `_tcp_check`:190 `HOST` — TCP port-22 reachability check
- `_ssh_fence`:222 `TARGET` / `_ssh_fence_close`:241 — decorative rule printed around SSH sessions
- `_remote_remove_pubkey TARGET PUBKEY` — removes one key line from the remote authorized_keys: key on stdin (never in the command: a `'` in a comment ran on the remote), file rewritten in place (keeps mode 600)
- `_setup_askpass`:256 / `_destroy_askpass`:272 — temporary `SSH_ASKPASS` script for padded prompts
- `_valid_key_name NAME` — the one rule for key names (plain file name in `~/.ssh`); checked where keys are written (`add_ssh_key_in_host`, `_write_key_pair`), not just in prompts
- `_ensure_ssh_dir`:280 — `mkdir -p ~/.ssh && chmod 700`
- `_write_key_pair`:291 `DEST_PRIV DEST_PUB DATA DATA [copy_mode]` — write or copy a key pair with permission enforcement
- `_print_identity_files`:312 `ID_LOOKUP` — prints IdentityFile entries for a host (dim style)
- `_prompt_host` — host picker only, sets `_REMOTE_HOST`, `_REMOTE_ALIAS`
- `_prompt_remote`:323 — prompts for host + user, sets `_REMOTE_HOST`, `_REMOTE_USER`, `_REMOTE_ALIAS`; runs `_hostkey_check` between the two (every remote op goes through here)

**known_hosts (TODO #15):**
- `_hk_resolve TARGET` — `ssh -G` → `_HK_NAME` (HostKeyAlias or HostName, `[name]:port` off 22), `_HK_HOST`, `_HK_PORT`, `_HK_FILES`, `_HK_HASH`. Never build the known_hosts name by hand.
- `_hk_known` / `_hk_show` / `_hk_forget` (`ssh-keygen -F/-R`, hashed entries too; `-R` keeps `FILE.old`)
- `_hostkey_check TARGET` — no known entry, or ProxyJump/ProxyCommand set (the scan would reach another machine): nothing (no extra connection). `@cert-authority`/`@revoked` lines don't count as entries. Only a scan of exactly one key with a fingerprint is compared and recorded (what the user is shown is what gets written). Known: `ssh-keyscan` of ONE key type (the preferred known one: ed25519 > ecdsa > rsa), since OpenSSH 9.8+ PerSourcePenalties charges every connection that doesn't log in. No match: old/new fingerprints + `[y/N]`; yes = `_hk_replace` (forget, then record the scanned key so the op's ssh doesn't ask again); no = the op is cancelled.
- `_hk_print_list LISTING LOOKUPS` — numbered list; hashed entries named via the config hosts' lookups

### prompts.sh

- `read_colored_input`:25 `PROMPT COLOR` — single-line text input with ESC cancel, Ctrl+W word-delete
- `read_host_with_default`:160 `PROMPT DEFAULT` — pre-filled editable input
- `read_remote_host_address`:267 — host selector; Esc cancels; typed text that isn't a configured host is the address (subnet shorthand `"10"` → `"192.168.0.10"`); the manual prompt appears only when no hosts are configured
- `read_remote_user`:262 / `read_remote_host_name`:362 / `read_ssh_key_name`:398 (picker of existing keys) / `read_new_ssh_key_name` (new name, validated, no picker; used by W) / `read_ssh_key_comment`:432
- `confirm_user_choice`:438 `MESSAGE DEFAULT ACTION_FN` — y/N confirmation that calls a callback
- `find_config_file`:469 / `find_private_key`:478 / `find_public_key`:483 / `get_public_key`:488
- `resolve_ssh_target`:503

### ssh-ops.sh

All status/feedback output uses `_out`/`_out_item` — no raw `\e[` escape codes.

- `deploy_ssh_key_to_remote`:15 `KEYNAME` — generates if missing, then installs
- `install_ssh_key_on_remote`:33 `KEYNAME` — copies public key to remote `authorized_keys`, then registers config
- `test_ssh_connection`:92 `USER HOST [IDENTITY]` — uses `-F /dev/null -o IdentitiesOnly=yes -o PreferredAuthentications=publickey` when an identity is given, bypassing the config block entirely to avoid false-positive fallbacks
- `remove_ssh_key_from_remote`:144 `USER HOST KEYNAME`
- `deploy_promoted_key`:179 — key rotation (deploy new, remove old)
- `register_remote_host_config`:204 — connects and matches remote `authorized_keys` against local keys
- `add_ssh_key_in_host`:268 `KEYNAME COMMENT` — generates an ED25519 key pair
- `add_ssh_key_to_host_config`:299 `KEYNAME HOST_NAME HOST_ADDR USER` — creates or updates a Host block
- `remove_identity_file_from_config_block`:361 `KEYNAME HOST_ALIAS`
- `_add_key_to_hosts`:386 `KEYNAME` — multi-select host checklist, appends `IdentityFile` to chosen blocks
- `import_external_ssh_key`:425 — import from local path, SCP, or paste

### config-display.sh

- `show_ssh_config_file`:12 — paginated SSH config viewer with inline editor launch
- `edit_ssh_config_file`:116
- `remove_host_from_ssh_config`:140 — removes a Host block after confirmation
- `show_ssh_key_inventory`:189 — lists local keys, their fingerprints, and which hosts reference them
- `_view_ssh_key`:375 / `_display_key_file`:415

### menu.sh

- `invoke_menu_choice`:17 — 22-line pure dispatcher; each case calls a `_menu_*` handler
- `_menu_generate_and_install`:44 — prompts key name, generates if missing, deploys to remote (`deploy_ssh_key_to_remote`)
- `_menu_install_key`:50 — same but requires key to already exist locally; aborts with message if not found
- `_menu_test_connection`:60 — picks key from host config or all local keys; supports "Test ALL" multi-key sweep
- `_menu_delete_remote_key`:118 — fetches remote `authorized_keys`, cross-matches local `.pub` files, removes selected; offers to strip IdentityFile from config and delete local key pair
- `_menu_promote_key`:201 — delegates to `deploy_promoted_key` (installs new key, removes old in one operation)
- `_menu_generate_key`:206 — prompts key name + comment, generates ED25519 pair locally without deploying
- `_menu_append_key_to_config`:213 — verifies key is accepted by remote via SSH test, then adds IdentityFile to host config block
- `_menu_delete_local_key`:242 — cross-references key against configured hosts, optionally removes from remote(s), then deletes local key files
- `_menu_remove_key_from_config`:296 — picks host then IdentityFile entry, removes that line from the config block
- `_menu_show_best_practices`:328 — prints the 4-rule key-naming guide (LAN shared vs WAN individual); no interactive input
- `_menu_list_keys`:338 — calls `show_ssh_key_inventory`; returns 1 to skip `wait_user_acknowledge`
- `_menu_conf_defaults`:343 — launches `_run_conf_editor` TUI; returns 1 to skip `wait_user_acknowledge`
- `_menu_remove_host`:348 — delegates to `remove_host_from_ssh_config`
- `_menu_view_config`:352 — calls `show_ssh_config_file`; returns 1 to skip `wait_user_acknowledge`
- `_menu_edit_config`:357 — calls `edit_ssh_config_file`; returns 1 to skip `wait_user_acknowledge`
- `_menu_list_authorized_keys`:362 — SSHes to target, fetches `authorized_keys`, displays numbered list
- `_menu_add_config_block`:389 — delegates to `register_remote_host_config` (reads remote auth_keys, creates host config entry)
- `_menu_import_key`:394 — delegates to `import_external_ssh_key` (local path / SCP / paste)
- `_menu_list_known_hosts` (19, K) / `_menu_forget_host_key` (20, F) — local `~/.ssh/known_hosts`
- `_menu_list_remote_known_hosts` (21, O) / `_menu_forget_remote_host_key` (22, B) — the SSH user's `~/.ssh/known_hosts` on the target; names go on stdin (`_REMOTE_KH_*`), never into the command
- `_hk_page` — pages a listing; `show_paged` reads keys from `/dev/tty` because stdin is the pipe
- `_do_create_config`:402 — creates `~/.ssh/config` with 600 permissions; sets `_CONFIG_MISSING=0`
- `_check_config_at_start`:412 — full-screen prompt on startup when config absent; offers to create it

### menu-support.sh

- `_sq`:13 — single-quote a value for shell command strings (bash 3.2-safe); escapes embedded `'` as `'\''`
- `_run_conf_editor`:63 — inline TUI for editing DEFAULT_USER/SUBNET/COMMENT_SUFFIX/PASSWORD; shows 4 copy-paste launch commands with current flag values
- `_show_menu_help`:174 — paginated help text describing every menu item

### menu-renderer.sh

- `_invoke_choice`:13 — clears screen, renders centered op title box, calls `invoke_menu_choice`, waits for ack. Sets `need_full=1` via bash dynamic scoping into `show_main_menu`'s local frame.
- `_hint_bar` `WIDTH KEY LABEL...` — builds a full-width reverse-video bar into `_HINT_BAR` (no fork); drops pairs from the middle until it fits, the last pair always stays, so it never wraps (a wrap scrolls the screen). Used for both bottom bars.
- `show_main_menu`:38 — scrolling viewport, differential rendering, hotkey support, resize detection. Alternate screen buffer (`\e[?1049h/l`).
- `_menu_cleanup` — defined inside `show_main_menu`; restores terminal state; guarded by `_MENU_CLEANED_UP` flag to prevent double-execution on Ctrl+C (INT trap → `exit` → EXIT trap)

## Key implementation notes

- **Remote lib loading uses temp files, not nested process substitution.** `source <(curl ...)` nested inside `bash <(curl ...)` fails on macOS — the outer process substitution holds a `/dev/fd` FD, and opening more FDs for inner substitutions causes curl to get a closed pipe (`Failure writing output to destination`). Fix: `_source_lib` downloads each lib to a `mktemp` file, sources it, then deletes it.
- **`format_menu_label` uses pure bash regex, not `sed`.** BSD sed (macOS) does not support `\x1b` in replacements, and embedding a raw ESC byte in the sed replacement string is unreliable across platforms. The function uses `[[ =~ ]]` with `BASH_REMATCH` — `^([^lo_up]*)(char)(.*)$` finds the first hotkey occurrence — then `printf '\e[1;4m...\e[0;97m'` wraps it. No subprocess, no platform differences.
- **No subprocess forks in render loops.** `$(printf ...)` costs ~1ms per call. Use `printf -v varname` instead.

## bash 3.2 rules (macOS system shell — only supported version)

The bash implementation targets bash 3.2 exclusively (macOS system shell, GPL v2). Do not use any bash 4+ construct — they silently break on 3.2, usually with no error, just wrong behavior.

**Banned — never use these:**

| Banned | Replace with |
|---|---|
| `${var,,}` / `${var^^}` | `tr 'A-Z' 'a-z' <<< "$var"` / `tr`; or `[yY]` glob / `[[ =~ [yY] ]]` for y/n checks |
| `local -A` / `declare -A` (associative arrays) | Parallel indexed arrays (`local -a keys=() vals=()`); or direct file checks; or `sort -u` pipeline for set-union |
| `${var@Q}` (quoting operator) | Avoid; use `_sq` (single-quote wrapper in `menu-support.sh`) or manual escaping |
| `printf '%q'` (bash builtin `%q`) | Use `_sq "$value"` — wraps in single quotes, escapes embedded `'` as `'\''` |

**Specific patterns established in this codebase:**

- **Case-insensitive comparisons** — use `shopt -s nocasematch; [[ "$a" == "$b" ]]; shopt -u nocasematch` (available bash 3.1+), or expand both cases explicitly (`[yY]`, `y|Y|yes|Yes|YES`).
- **Hotkey uppercasing for menu dispatch** — `k_up=$(tr 'a-z' 'A-Z' <<< "$k")` once before the loop; compare against the stored uppercase hotkey directly.
- **Associative maps with string keys** — use two parallel `local -a` arrays (`_umap_keys` / `_umap_vals`) with O(n) linear search. Key counts in this app are always < 20 so this is fast enough.
- **Key inventory set-union** — replace `"${!assoc[@]}"` iteration with a `{ list_source_a; list_source_b; } | sort -u` pipeline fed into a `while read` loop.

**Terminal reads — the contract (TODO #11, plan X4):**

- **Never read a key with bash's `read -n1` / `read -d`.** On a tty they force VMIN=1 and block until a byte arrives, ignoring `stty … time N`: a bare-Esc check or a poll loop can then hang, and loops can't redraw on resize.
- **`_poll_byte`** reads one byte with `dd` under `stty -echo -icanon min 0 time 1` (100 ms): returns 1 on timeout. `dd` runs with TSTP/INT ignored (a stopped `dd` would hang sshdd on Ctrl+Z; bash still gets the signal and its trap runs when the read returns). The `x` suffix keeps a newline byte through `$(…)`.
- **`_wait_key`** polls until a key arrives; when `stty size` no longer matches `TERM_H TERM_W` it updates them and returns `KEY=$KEY_RESIZE`. Every interactive loop handles `KEY_RESIZE` by redrawing (loops that redraw each iteration need nothing).
- **`_read_key`** (own stty), **`_read_key_raw`** (caller holds `min 0 time 1`) and **`_read_key_nb`** (one 100 ms window, main menu poll) are built on these. All call `_esc_drain` after ESC.
- Interactive loops hold `stty -echo -icanon min 0 time 1` (not `min 1 time 0`).
- **Limit:** a picker on an operation screen redraws its own rows on resize; the operation's title box above it is transcript and isn't redrawn.
- **SSH test isolation.** `-F /dev/null` bypasses `~/.ssh/config` entirely; `-o IdentitiesOnly=yes` alone is insufficient because it still allows keys from the matching config block.
- **Passphrase-protected keys.** Never use `-o BatchMode=yes` when testing keys — it blocks passphrase prompts. Use `-o PreferredAuthentications=publickey` to restrict to key auth without silencing prompts.
- **Shared HostName.** Several Host blocks may point at one IP. `resolve_ssh_target` prefers `_REMOTE_ALIAS` when the address is `_REMOTE_HOST`; anything that maps an IP back to an alias must do the same, never take the first match.
- **Esc inside `$(...)`.** `read_colored_input` / `read_host_with_default` return 1 on Esc, but `_SELECT_CANCELLED` set inside `$(...)` never reaches the caller. Always `x=$(read_... ) || return 1`; never test `_SELECT_CANCELLED` after a `$(...)` prompt, and never let Esc fall through to a default (`confirm_user_choice`).
- **`_LAST_SELECTED_ALIAS` subshell loss.** Any global set inside `$()` is discarded. Use `get_alias_for_host_ip` as a reverse-lookup after the subshell returns, or use `_prompt_remote` which handles this correctly.
- **Ctrl+C guard.** The INT/TERM/TSTP/HUP traps only set the exit code; cleanup lives exclusively in the EXIT trap. The `_MENU_CLEANED_UP=1` flag prevents a second cleanup run.
- **`${f/#$HOME/~}` differs by version**: bash 5 expands the `~` (giving `$HOME` back), 3.2 doesn't. Use `$_TILDE`.
- **`_with_timeout` inside a pipe or `$(…)`**: its watcher `sleep` must not hold stdout, or the reader waits the full timeout (fixed: watcher output goes to /dev/null).
- **Temp files: `_mktemp_reg VAR PREFIX`**, never `VAR=$(mktemp)` (a signal during the subshell loses the name). **Timeouts: `_with_timeout`**, never GNU `timeout` (not on macOS). `ssh`/`scp` are functions adding `ConnectTimeout=10`; call `command ssh` only when you mean the bare binary.
- **Cleanup on any exit (TODO #10).** Register every temp file with `_cleanup_add` (ssh-helpers.sh); `_menu_cleanup` removes them, kills background jobs and `_destroy_askpass`es. Kill background jobs with TERM then CONT: Ctrl+Z stops the whole process group and a stopped job ignores TERM (a `wait` on it hangs). Limit: a SIGTERM sent to sshdd alone while a foreground `ssh` runs is handled only after that `ssh` exits (bash defers traps until the foreground child returns); Ctrl+C and a closed terminal reach `ssh` too. Tests: `tests/test_termination.py`.
- **Terminal resize.** `trap 'need_full=1' WINCH` in `show_main_menu` triggers a full redraw on the next loop iteration. The poll-based resize detection alone is insufficient — if a key arrives during a resize, the poll branch is skipped and only a differential update runs, leaving static elements (rules, title, hint bar) unredrawn.
- **`authorized_keys` newline.** `printf '%s'` (not `printf '%s\n'`) when writing the public key — the `.pub` file already ends with `\n`.
- **`_read_key_raw` vs `_read_key` vs `_read_key_nb`.** `_read_key_raw` and `_read_key_nb` both skip `stty` save/restore (2 subprocess forks each). `_read_key_nb` is used exclusively by the `show_main_menu` poll loop which already holds raw mode. `_read_key_raw` is used inside `select_from_list`/`select_multi_from_list` render loops which also hold raw mode. `_read_key` manages its own stty mode and is safe to call from anywhere else. All three call `_esc_drain` to handle ESC continuation bytes.
- **Pexpect test ESC timing.** If a test sends a bare ESC and then the next key within 100 ms, the two read as one Alt+key sequence (as in any terminal). Mitigation: `time.sleep(0.15)` after each "back at main menu" expect in the test loop.
- **`select_from_list` writes to `/dev/tty`, result in `_SELECT_RESULT`.** All TUI rendering goes to `/dev/tty` (fallback: `/proc/self/fd/2`) so the widget works correctly inside `$(...)` subshells. Never capture the return value with `$(select_from_list ...)` — it will be empty. Read `_SELECT_RESULT` and check `_SELECT_CANCELLED` after the call returns.
- **`_HOST_BLOCK` global is overwritten on every `_get_host_block` call.** Consume `_HOST_BLOCK` immediately after calling `_get_host_block`; any subsequent call (including those inside helpers like `_block_field` callers) will clobber it.
- **`show_op_banner` dual mode.** Default (stream) prints directly to stdout. Buffer mode: set `_OP_BANNER_ROW` to the starting row before calling — output goes into `_OP_BANNER_BUF` for the caller to append to its frame. Always sets `_SFL_BANNER_ROWS=5` so `select_from_list`/`select_multi_from_list` offset their start row below the banner.
- **`_draw_op_header` dual mode.** Same pattern as `show_op_banner`. Stream mode (default): clears screen and prints the teal box directly — used by `_invoke_choice`. Buffer mode: set `_OP_HDR_ROW=1` before calling — writes absolute-positioned ANSI to `_OP_HDR_BUF` at rows 2-7 — used by `show_ssh_config_file` and `show_ssh_key_inventory` inside their render loops. Always sets `_OP_HDR_HEIGHT=7`. `_OP_BANNER_ROW` for those screens must be 8 (box occupies rows 2-7).
- **`_visual_width` emoji correction.** `${#str}` counts Unicode code points, not terminal columns. Non-BMP emoji (4-byte UTF-8, e.g. 🔌🔑📤) = 1 bash char but 2 display cols → add 1. Variation selectors U+FE0F/FE0E = 1 bash char but 0 display cols → subtract 1. These cancel for emoji+VS pairs (🗑️👁️✏️) — no correction needed. Wide BMP symbols ✨➕❌ also need +1. Text-presentation emoji (🗑 🗝 🏚 👁, no VS16) are 1 column: −1. `tests/test_units.py` checks every app label against `wcwidth`. Detection: 4-byte lead bytes via `LC_ALL=C tr`; BMP wide chars by string substitution loop.
- **`_replace_host_block` silent failure.** Uses `perl` with `python3` fallback. If neither is present it returns 1 and the config block is not updated — callers must handle this or changes are silently lost.
- **`select_from_list` strict mode (`-s`).** Enter is a no-op unless exactly one filtered item remains. Without `-s`, Enter with a non-empty filter string creates a new item from the typed text — intentional for key-name and host-name inputs.
- **`_write_key_pair` public key normalization.** In non-copy mode it strips every trailing newline from the passed string and adds exactly one back, so `.pub` files always end with exactly one newline regardless of source (U8).
- **`get_identity_file_from_host_config` expands `~` and `$HOME`.** Other `ssh-config.sh` getters return raw strings. Only this function substitutes `~` → `$HOME` in the returned path; callers of other getters must expand paths themselves if needed.
