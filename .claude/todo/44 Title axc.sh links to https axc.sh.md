---
number: 44
title: 'Title: axc.sh links to https://axc.sh'
status: Review
category: tui
creator: Ahmad
created: 2026-10-26 22:28
kind: todo
latest: '10-30: Ahmad: On Powershell, CTRL+Click works.'
description: Make 'axc.sh' in the main title box a link to https://axc.sh. (Ahmad, 2026-10-26)
---
## Updates

## Answers (Ahmad, 2026-10-26)
- OSC 8 terminal link on axc.sh (Cmd/Ctrl+click where supported) + a plain click on the title opens https://axc.sh with open/xdg-open when sshdd runs locally (not over SSH).
- PowerShell title too (link only; PS has no mouse yet, #42).
- **Started 2026-10-26.**
- **Ready for review 2026-10-26.** OSC 8 link on axc.sh in the title (bash + PowerShell); bash: a click on the title opens https://axc.sh via open/xdg-open unless SSH_CONNECTION is set. Terminal.app likely shows plain text (not on the OSC 8 support list). tests/test_title_link.py; tests wait for 'SSHDD -- ' (raw title now split by the link codes).
- **Comment 2026-10-30 (Ahmad, Plane).** On Powershell, CTRL+Click works.
