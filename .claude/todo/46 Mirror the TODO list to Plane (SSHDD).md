---
number: 46
title: Mirror the TODO list to Plane (SSHDD)
status: Review
category: docs
creator: Ahmad
created: 2026-10-30 22:10
kind: todo
latest: '10-30: Plane mirror running; backtick loss reported.'
description: 'Use Plane for this project''s TODO list (todo-tables Plane section): setup SSHDD with the claude-sshdd token file, first sync, check SSHDD-N = #N. (Ahmad, 2026-10-30)'
---
## Updates
- **2026-10-30.** Done: project SSHDD (an older SSHDD project Ahmad deleted first), .claude/plane.json, cron every 5 min, plane MCP (local scope). First sync: 45/45 notes, SSHDD-N = #N (checked via the API). Found: the round trip drops `code` backticks from descriptions (#3, #6, #7, #12 changed, not committed): a plane_sync.py bug in claude-init.
- **Ready for review 2026-10-30.** Plane mirror running; backtick loss reported.
