---
number: 37
title: Edit ~/.ssh/known_hosts from sshdd
status: Review
category: tui
creator: Ahmad
created: 2026-10-24 09:47
kind: todo
latest: '10-24: S / 📒 Edit Known Hosts (Local section): opens ~/.ssh/known_hosts in $EDITOR like E, bash + PowerShell; hidden bash S (View Config) dropped; a missing…'
description: Allow editing my local ~/.ssh/known_hosts from sshdd. (Ahmad, 2026-10-24)
---
## Updates

## Answers (Ahmad, 2026-10-24)
- Open ~/.ssh/known_hosts in $EDITOR, like Edit Config (E); bash and PowerShell. K (list) and F (forget) stay.
- Menu: Local section, next to List Known Hosts (K) and Forget Host Key (F).
- Start now.
- **Started 2026-10-24.**
- Label/hotkey: 📒 Edit Known Hosts, S (Ahmad). S was a hidden bash-only second key for View Config (V stays, F2 too): dropped (Ahmad).
- **Ready for review 2026-10-24.** S / 📒 Edit Known Hosts (Local section): opens ~/.ssh/known_hosts in $EDITOR like E, bash + PowerShell; hidden bash S (View Config) dropped; a missing file's error now stays on screen (E too). tests/test_edit_known_hosts.py (3, fail on the old code).
