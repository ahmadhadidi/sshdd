# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A terminal-based SSH key manager with an interactive TUI (Text User Interface). It automates ED25519 key generation, deployment to remote machines, SSH config management, connection testing, and key rotation/cleanup.

Two parallel implementations exist:
- `sshdd.sh` — macOS (bash 3.2), entry point (~47 lines); logic lives in `lib/bash/`
- `sshdd.ps1` — Windows (PowerShell 5+), entry point (~47 lines); logic lives in `lib/ps/`
- `setup/alias.sh`, `setup/alias.ps1` — the README's one-line alias installers (asks for values not passed; tests: `tests/test_setup_alias.py`)

Full spec: `docs/PRD.md`.

Implementation details are in the sub-directory CLAUDE.md files (loaded automatically when editing files in those directories):
- Bash: `lib/bash/CLAUDE.md` — architecture, module breakdown, bash 3.2 rules, implementation notes
- PowerShell: `lib/ps/CLAUDE.md` — architecture, module breakdown, PS-specific notes

## Running

**Bash:**
```bash
bash sshdd.sh
bash sshdd.sh --user myuser --subnet 192.168.0 --comment-suffix "-[prod]" --password "mypass"
```

**PowerShell:**
```powershell
. .\sshdd.ps1
& ./sshdd.ps1 -DefaultUserName "root" -DefaultSubnetPrefix "192.168.0"
```

No build step. Both scripts run directly with no dependencies beyond Bash/PowerShell and OpenSSH (`ssh`, `ssh-keygen`). `sshpass` is optional for password-based remote auth.

Checks: `make check` (syntax-checks `lib/bash/*.sh`, `lib/ps/*.ps1`); tests: `bash scripts/run-tests.sh -m "not lxc"` (pytest + pexpect, see `TEST.md`; `-m lxc` needs the test LXC). The pre-commit hook refreshes line numbers in this file (`make update-docs`), syntax-checks staged lib files, and runs the non-LXC tests when lib or test files are staged.

## Bash vs PowerShell parity

When modifying behavior, changes typically need to be mirrored in the counterpart lib files. Bash uses `stty`/`read` for terminal I/O; PowerShell uses `Host.UI.RawUI.ReadKey()` and `[Console]::Write()`. Config parsing in Bash uses `perl`/`awk`/`sed`; PowerShell uses `[regex]` class methods.

## Where project-specific detail lives

Per "one owner per fact" below, this file states the operating rules; it does not restate content another file owns:

- Spec, goals, non-goals → `docs/PRD.md`. Build status → `docs/PROGRESS.md`.
- Bash and PowerShell architecture, module map, bash 3.2 rules → `lib/bash/CLAUDE.md`, `lib/ps/CLAUDE.md`.
- TUI look and key bindings (emojis, teal highlight, hint bar, F-keys) → project memory `user_preferences.md`.
- How to run the tests → `TEST.md`; codebase-specific QA quirks → qa-agent's own file.
- Security-sensitive files → security-review-agent's own file; trust boundaries → "Security posture" below.
- Credential-handling rule → "Do not" below (the canonical statement).

## Operating rules

- **Consult `.claude/` and project memory first, every task — binding, not optional reference.** Before starting any task, check `.claude/` (agents, skills, commands) and the auto-memory system (indexed by `~/.claude/projects/-proj-sshdd/memory/MEMORY.md`) for relevant prior guidance, decisions, or procedures. Treat what's there as binding project context, not background reading to skip under time pressure. Memory is currently one shared pool — split a specific agent's accumulated domain knowledge into its own file/section once it's substantial enough that mixing it with general project memory gets unwieldy, rather than defaulting to one flat pool forever. When a topic file itself grows past comfortable full-read size (rough guideline: ~35-40KB), split it into a compact present-tense core plus a `<name>.memory.archive.md` sibling holding verbatim history/narrative detail — grep the archive for a specific question, never read it in full, and keep the core from regrowing past that point.
- **Never assume when it matters — ask, and ask once.** On an ambiguous requirement or a hard-to-undo decision, do not guess and proceed. Group every open question into a single batch (one `AskUserQuestion` call, not several trickled out over a conversation) rather than resolving them one at a time by assumption. Obvious defaults (a convention already established elsewhere in the repo, a formatting choice with only one sane answer) don't need a question — pick it, state the choice, move on. A wrong assumption on a hard-to-undo change (a schema rewrite, a bulk delete, a live write to remote hosts (`authorized_keys`) and the local `~/.ssh/`) is expensive to unwind — ask before acting, not after.
- **Manage context deliberately — narrow the read, not the work.** Search before reading, read the narrowest slice that answers the question, batch independent tool calls in one turn, delegate to a subagent for context isolation on sizable work, skip verification you can't actually observe (never fabricate "confirmed working" for anything unverifiable), and keep summaries tight. This targets waste, never real work — it is not license to do less, only to do it with less wasted context.
- **Act as team leader.** Delegate sizable or parallelizable domain work to this project's configured agents (docs-agent, qa-agent, security-review-agent) rather than doing it all in the main session — run independent agents in parallel. Create a new agent only for a durable, recurring domain that doesn't already have an owner among the configured set — standing authorization from the project owner to do this when that criterion is met, no need to ask permission each time. **Match the model to the task when spawning:** override an agent's default model via the `Agent` tool's `model` parameter whenever the task's effort clearly calls for something else — `haiku` for trivial/mechanical work, `opus` for genuinely hard or high-stakes reasoning, `sonnet` as the general-work default, `fable` where it specifically fits (no strong differentiated guidance on fable's niche yet — flag that uncertainty rather than guessing confidently when it's unclear). This is a per-invocation judgment, not a change to the agent files' own `model:` frontmatter, and it does not apply to the main session itself — there is no tool to change the currently-running model mid-conversation. If a spawned task turns out harder or easier than expected mid-flight, re-spawn on the right tier rather than grinding through on the wrong one.
- **Run a broader code review when the change warrants it.** Trigger `/code-review` (if this project has that command) for large, multi-file, or risk-bearing changes — not for small, localized edits. security-review-agent remains the narrower, security-specific gate for this project (see its own file for scope); this is the general-purpose counterpart for everything else risky enough to warrant a second look.
- **Grow the skill and agent library deliberately.** After any task that taught something new, capture it — a new or extended skill under `.claude/skills/` for a repeatable procedure, or a new agent under `.claude/agents/` for a durable domain with no current owner. As part of end-of-task housekeeping (below), consciously decide whether anything new was learned — "nothing new this time" is a real, stated conclusion, never a silent omission. Keep this file's own references to the current agent/skill roster in sync whenever the roster changes.
- **Commits: on `main`, as Ahmad Hadidi.** One commit per task, with its TODO number in the message. Identity per commit via `GIT_AUTHOR_NAME`/`GIT_AUTHOR_EMAIL` and `GIT_COMMITTER_NAME`/`GIT_COMMITTER_EMAIL` = "Ahmad Hadidi" `ahmadhadidi@gmail.com` (no global git config), always with the `Co-Authored-By: Claude …` trailer. Stage by explicit file name, not `git add -A`. Push only when asked, through the owner's forwarded agent (`SSH_AUTH_SOCK=<live socket> git push origin main`; the inherited `SSH_AUTH_SOCK` and `~/.ssh/agent.sock` both go stale, so find the live one with `for s in /tmp/ssh-*/agent.*; do SSH_AUTH_SOCK=$s ssh-add -l >/dev/null 2>&1 && echo $s; done`); `main` is what the cloud install URLs serve, so a push ships to users. Never force-push or amend a published commit. The owner's own edits are theirs to commit.
- **Session continuity via `docs/SESSION-HANDOFF.md`.** "Continue where the previous session stopped" is a recovery command, not small talk — follow that file's own "How to resume" protocol rather than improvising. Log per-task, not just per-session: before starting any non-trivial task, append an entry there with `Status: in progress`; when that task is completely implemented (verified, not just committed), update that same entry's `Status` to `done` — don't wait for session end to record either half. Still also true: close out or append a final entry before ending your own session, even if it's just marking the last open one done — an unwritten/unclosed entry means the next session starts blind.
- **One owner per fact.** Record each lesson, number, or decision in exactly one authoritative file and link to it from anywhere else that needs it — copying a fact into multiple places guarantees it drifts out of sync the next time it changes.
- **Files for the owner** (zips, reports, screenshots) go under `handoff/`, never a scratchpad or `/tmp`.

## TODO list

The `todo-tables` skill keeps the list: `.claude/TODO.md` (a symlink is fine) with one note per item in `todo/` beside it, shown as a Kanban board in Obsidian. Read statuses with `todo.py`, never from memory. **Review** means the owner checks it; only their approval moves an item to Done. The lessons review before each compaction files Claude's mistakes under `.claude/lessons/`; ask the owner which become rules.

## Before making changes

1. Read `docs/PRD.md` if you haven't already this session.
2. Run `/goals` (or `/goals <area>`) to confirm the current task maps to a stated goal and doesn't silently expand scope.
3. Follow this project's stated build-phase order, if one exists — later phases typically assume schema and interaction decisions from earlier ones are already in place.

## After finishing a task

Housekeeping is part of the task, not a follow-up — do this before considering anything closed, not only when asked:
- Undo your own verification side effects first — delete any screenshots, temp files, scratch DB rows, or other artifacts created while confirming the work.
- Update `docs/PROGRESS.md` in the same commit (or the very next one). It is the single source of truth for current build status — not the session task list, not out-of-repo memory. Completed-round historical detail lives in the sibling `docs/PROGRESS.archive.md` — grep it for a specific round/ticket rather than reading it in full, and if an archived round leaves anything unresolved, that must also land in `docs/PROGRESS.md`'s "Remaining work" section in the same edit; the archive is append-only history, never the only place an open item is recorded.
- Append a fresh dated entry to `docs/SESSION-HANDOFF.md` before ending the session — see that file's own format.
- If the change altered a convention, gotcha, or constraint that a subagent's system prompt in `.claude/agents/*.md` describes, update that agent file too. A stale agent prompt is worse than none — it actively misleads whoever it's invoked for.
- If the change is a reusable procedure or a hard-won debugging technique specific to this codebase (not just "what the code does," but "how we figured out what was wrong" or "how to verify this class of thing"), add or update a skill under `.claude/skills/` — see the "skills" section below.
- If the change altered project-wide architecture, stack conventions, or a "Do not" rule, update this file.
- Keep `.claude/` in sync with reality: commands, agents, and skills should describe how the project actually works today, not how it worked when they were written.
- If the change altered code structure (new/removed files, moved functions, changed relationships) — not a pure doc/config edit — run `graphify update .` to refresh the knowledge graph (AST-only, no API cost). See the "graphify" section below.

## Before an architecture-affecting change

If a change is likely to touch the stack, the schema shape, or a cross-cutting convention broadly enough that a bad outcome would be hard to unwind, take a backup branch first and log it in `README.md`'s `## Backups` section — judge by rollback cost, not change size. Keep at most 2 backup branches; ask before deleting the oldest. Full procedure: `~/.claude/skills/backup-before-major-change/SKILL.md` (a global skill).

## Do not

- Default to `sudo` in any shell command or instruction.
- Embed a live API token, secret key, or other credential in any generated or exported artifact the user downloads. If you find yourself about to write a credential into a file the user will download or export, stop and flag it instead.

## Security posture

- Single-user CLI on the owner's machine; no server and no auth of its own.
- Local `~/.ssh/` (private keys, `config`) never leaves the machine. Only public keys go to remote hosts.
- Remote hosts are reached with `ssh` using a key, or a password via `sshpass` / a temporary askpass script (`_setup_askpass` / `_destroy_askpass`).
- Passwords come from `--password` / `-DefaultPassword` or a prompt. The F5 "Conf Defaults" screen prints a persist command that includes the password when one is set.
- Cloud runs fetch code over HTTPS from this repo's `main`: anyone who can push to `main` runs code on every cloud user's machine.

## Open questions — project-wide (do not silently resolve)

<!-- Document unresolved project-wide decisions here (deployment, environment assumptions, behaviour still being confirmed). Delete this comment once populated. -->

## Style, when writing docs or comments in this repo

Direct, factual phrasing. No marketing language. Metric units. Separate facts from assumptions from recommendations explicitly when a decision needs a reason attached — this convention should carry into code comments and commit messages, not just this project's spec document.

## skills

`.claude/skills/` (now: `ct-connection-closed`) holds project-specific procedures learned the hard way — each one a symptom, the root cause, and the fix, not a restatement of what the code does. Check there before re-deriving a debugging path from scratch. When a new one is learned — a workaround, a non-obvious verification technique, a gotcha that cost real time to diagnose — add a skill for it per the "After finishing a task" section above, rather than letting the knowledge live only in a commit message or a chat transcript.

## graphify

This project's knowledge graph lives in `graphify-out/` (god nodes, community structure, cross-file relationships); build it with `/graphify` once there is code.

Rules:
- For codebase questions, first run `graphify query "<question>"` when `graphify-out/graph.json` exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than `GRAPH_REPORT.md` or raw grep output.
- If `graphify-out/wiki/index.md` exists, use it for broad navigation instead of raw source browsing.
- Read `graphify-out/GRAPH_REPORT.md` only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- `graphify affected "<symbol>"` — reverse impact analysis; run this BEFORE editing a widely-shared helper so every call site is known upfront instead of discovered one broken thing at a time.
- After a refactor that *deleted* code, pass `--force` (or `GRAPHIFY_FORCE=1`) to `graphify update` — it otherwise refuses to shrink the node count, assuming it's an accident.
- `.graphifyignore` excludes `.claude/` — agent/skill/command markdown can otherwise pollute code-structure queries; if you have a question about `.claude/` content, read it directly, don't query the graph for it.

## Pack rules: proxmox-lxc

- **CT changes, `pct create`/`destroy`, reboots and router changes: ask first**, every time.
- **CTIDs: the owner picks.** Offer the free ones in a modal with what you know about each. Before calling one free, run `pct list` on every node (ask the owner for nodes Claude can't reach) and ping it **from a Proxmox host** with a control IP that answers. A stale "taken" note or a failed ping proves nothing. To find a CT, use `pct list` plus each CT's `ip=`; a failed `pct config <id>` only proves that ID isn't on that node.
- **Address mismatch on a CT: read the CT first** (`pct config`, `ip addr`, what last set the address), then the router.
- **Hand tests on a scratch CT** cloned from a golden template, with a CTID no job uses; never on a CT a CI job owns or the owner kept. Reach golden clones with `pct exec` on the host.
- **Before sealing a template**, write down the consumer's first three actions and confirm each works with what the template carries (`pct clone` can't inject SSH keys).
- **Mounts: the narrowest folder.** An app's mount point is its own subfolder, never the whole share; raise the risk unasked.
- **"Always on" means a boot service** (`rc-update add … default` on Alpine, `systemctl enable` elsewhere) and `--onboot 1`, in the same change.
- **Alpine:** `apk add` every command-line tool you call, never rely on a dependency (`acme.sh` pulled `aws-lc-tools` as `openssl` and broke). busybox `ash` has no bracketed paste: a pasted `read` takes the next pasted line as its answer, so wrap such blocks in `{ … }`.
- CT provisioning procedure: the `lxc-bootstrap` skill (on the owner's claude.ai account, synced as `anthropic-skills:lxc-bootstrap`) if it's available.
- Proxmox nodes: ho4 (`root@192.168.0.9`, standalone, key `~/.ssh/ho4-root` on dev-poc); dev-poc (204) runs on another node Claude can't reach (ask the owner). `ho4.lan` resolves to 192.168.0.101, not the node. Router and `.lan` proxy CT: not recorded yet.
- LAN: `192.168.0.0/24`, gateway `192.168.0.1`, bridge `vmbr0`.
- The CTID gives the IP's last octet and the MAC (`DE:AD:DE:AD:XX:YY`); CTIDs stay at or below 254.
- CT 204 (`dev-poc`, 192.168.0.204) is Claude's own. CT 213 (`sshdd-test` on ho4, 192.168.0.213, full clone of golden 324, onboot) is the sshdd test LXC (`-m lxc` tests write its `authorized_keys`; users `testuser` with password auth, `kraid` with `dev-lan.pub`). Never touch any other CT.
