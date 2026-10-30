---
number: 47
title: Plane @mention invokes Claude (webhook)
status: In progress
category: tooling
creator: Ahmad
created: 2026-10-30 22:18
kind: todo
latest: '10-30: Started'
description: 'Ahmad 2026-10-30: when a Plane comment @mentions Claude, Claude starts working on it without being told. Webhook approach (Ahmad tested Plane webhooks on a self-hosted instance). Design to agree before building: receiver host/port, signature secret, who may trigger, what the run may do, how it replies.'
---
## Updates

## Answers (Ahmad, 2026-10-30)
- Webhook (Ahmad tested Plane webhooks on a self-hosted instance).
- Who: any workspace member's @mention of the Claude user starts a run.
- Allowed without asking: read, edit, run tests, commit locally on main; never push, never touch hosts/CTs or outside services; reply in a Plane comment, ask there when a choice is needed.
- Receiver: this machine, http://192.168.0.190:8790/plane, started at boot by an @reboot cron line (no user systemd here); verifies X-Plane-Signature with a secret Ahmad sets.
- Projects: every project with Plane (.claude/plane.json maps a Plane project to its repo): one receiver in claude-init's todo-tables skill.
- **Started 2026-10-30.**
