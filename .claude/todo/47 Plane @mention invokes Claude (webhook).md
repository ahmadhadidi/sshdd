---
number: 47
title: Plane @mention invokes Claude (webhook)
status: Review
category: tooling
creator: Ahmad
created: 2026-10-30 22:18
kind: todo
latest: '10-30: Ahmad: testing'
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
- **2026-10-30.** Mention format (read via the plane MCP, SSHDD-41 comment): the comment_html carries @[<user uuid>] inline (that comment mentions 4c43b56a-7796-442a-b3fc-2192fcde053d). The MCP can also write mentions the same way, so a run can reply and @-mention the asker.
- **Comment 2026-10-30 (Ahmad, Plane).** testing
- **2026-10-30.** Live: Plane 1.4.3 refused a LAN webhook URL ("Invalid or disallowed webhook URL"); Ahmad set WEBHOOK_ALLOWED_IPS=192.168.0.190/32 in /opt/plane/plane.env on CT 107 (api + worker recreated). Receiver: claude-init 7a8858b, @reboot cron, port 8790, secret in ~/.config/plane/webhook.secret. First real run: @sshdd testing on SSHDD-47 at 23:06:31 -> On it 23:06:32 -> reply @mentioning Ahmad 23:06:47; own comments skipped.
- **Ready for review 2026-10-30.** Plane @mention -> Claude run works live (SSHDD-47, 16 s). Receiver in claude-init todo-tables (plane_webhook.py).
- **Comment 2026-10-30 (Ahmad, Plane).** testing
