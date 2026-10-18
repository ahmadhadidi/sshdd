# sshdd — PRD

Stub written at claude-init adoption (2026-10-17) from `README.md` and `CLAUDE.md`. Grow it as decisions are made.

## What it is

Terminal TUI SSH key manager. Two parallel implementations: `sshdd.sh` (bash 3.2, macOS/Linux) and `sshdd.ps1` (PowerShell 5+, Windows), with logic in `lib/bash/` and `lib/ps/`.

## Goals

- Generate ED25519 keys and deploy them to remote hosts.
- Keep `~/.ssh/config` in sync (add, edit, remove host blocks; attach keys).
- Test connections; list, promote, rotate and delete keys locally and remotely.
- Recreated hosts (e.g. a destroyed CT) don't block work: the host key is checked before connecting, and
  `known_hosts` entries can be listed and forgotten here and on a remote host (TODO #15).
- Run with no install: straight from GitHub (`curl` / `irm`) or from a clone, with only Bash/PowerShell and OpenSSH (`sshpass` optional).
- Bash and PowerShell behave the same (parity).

## Non-goals

<!-- Not stated yet. Ask the owner before assuming one. -->

## Build phases

<!-- None stated. Existing plans: `plans/bash32-only.md`. -->
