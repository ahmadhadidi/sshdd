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
