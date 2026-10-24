# Session handoff

## How to resume

Read the newest entry below, then `docs/PROGRESS.md`, then continue its open task.

## 2026-10-17 — claude-init adoption

Status: done
- Adopted claude-init via `setup/RETROFIT.md`. Rollback point: `backup/2026-10-17-1959-boilerplate-adoption`.
- TODO list set up (`todo.py init`, categories bash, powershell, tui, ssh-ops, tests, docs).

## 2026-10-17 — TODO #1–#7, #12, #13

Status: done (all in Review, waiting for Ahmad)
- Fixed #1 Esc, #2 hint bars, #3 config parsing, #4 new-key name, #5 F5 title box, #7 host filter, #12 cloud CRITICAL, #13 title. #6: test CT 213 on ho4.
- New test tooling: pyte screen harness `tests/screen.py`; pwsh unit tests in `tests/test_ssh_config_parse.py`; shellcheck installed. tmux not installed (dpkg says not installed).
- Not pushed: `git rev-list --count origin/main..main` commits waiting; cloud users get the fixes only after a push.
- Open: #8 test plan, #9 herdr, #10 cleanup on termination, #11 artificial delays.

## 2026-10-18 — TODO #8–#11

Status: done (in Review, waiting for Ahmad); pushed 2026-10-18 (`c197806`).
- #8 `docs/TEST-PLAN.md` (53 built, 16 partly open, 30 bugs fixed); #9 herdr not reproduced, explicit cursor restore added (unconfirmed); #10 cleanup on every exit; #11 arrow lag 126 → ~20 ms.

## 2026-10-18 — TODO #15 known_hosts

Status: done (in Review, waiting for Ahmad); not pushed
- Answers in the #15 note: pre-connect host key check with `[y/N]` forget-and-retry; Local K/F and Remote O/B items; Remove Host offers to forget the key.
- Security review (security-review-agent) found M1–M3, L1, L2 and a false "done"; all fixed with a regression test each in `tests/test_known_hosts.py`. Open: the hint wording and L3 (see the #15 note).

## 2026-10-19 — TODO #17, #18 (and #19 filed)

Status: done (in Review, waiting for Ahmad); all pushed (`6c5ff3b`).
- #15 hint wording changed to "If you didn't recreate this host, answer N." (Ahmad's choice).
- #17: IdentityFile compared whole (no substring); awk replaces GNU-only `sed \s` (broke key paths on macOS).
- #18: 1Password's `Host * IdentityAgent` block: no conflict, tests only.
- Open: #19 keys that live only in 1Password (Ahmad's MBP); needs a design agreed first. #14 in Inbox.
- Don't run tests while the pre-commit hook runs (TEST.md).

## 2026-10-19 — TODO #14 List Authorized Keys: all users

Status: done (in Review, waiting for Ahmad); not pushed
- Ahmad's answers in the #14 note: ask each time (This user / All users), `authorized_keys` only, grouped by user.
- CT 213: "needs root" path tested live (testuser); root and sudo paths tested locally with fake `id`/`getent`/`sudo`.

## 2026-10-22 — TODO #20 new host name asks for the address

Status: done (in Review, waiting for Ahmad); not pushed
- Doska board `sshdd` holds a one-time copy of the TODO list (19 cards, scripted diff clean). Notes stay the source.
- #20: a name typed in the host picker that isn't in ~/.ssh/config asks for the address (pre-filled with the name);
  Install SSH Key / Add config block default the alias to that name. Answers in the #20 note.
- #24: README alias installers (bash/zsh, PowerShell); answers in the #24 note. zsh not installed here: untested in zsh itself.
- #26: U+009D at a text prompt blanked the screen (read -n1 read bytes); fixed via _wait_key.
- #25: tests run in parallel (pytest-xdist): hook ~20 min → ~2.5 min. Hook is .git/hooks/pre-commit (untracked).
  Lesson #27 → claude-init skill parallel-test-suite.

## 2026-10-23 — TODO #29 alias setup scripts

Status: done (in Review, waiting for Ahmad)
- README "Alias" is now one cloud line per OS running `setup/alias.sh` / `setup/alias.ps1`; flags optional, missing
  values asked (Enter = default), password hidden. Answers in the #29 note. Replaces #24's paste-in blocks.
- #28 Ctrl+\ ignored; #20 address prompt empty (Ahmad's change). All pushed except #29.

## 2026-10-24 — TODO #35 every test, fastest; #36 host-block edit

Status: done (in Review, waiting for Ahmad)
- `make test-all`: all 438 tests pass (402 local, 34 LXC on CT 213, 2 timing) in ~3 min; hook uses --dist worksteal.
- #36: bash _replace_host_block matched block text anywhere ("host a" inside "host a0"); now whole lines only.
- #32 still open (cause unknown; the test now reports the process list).
