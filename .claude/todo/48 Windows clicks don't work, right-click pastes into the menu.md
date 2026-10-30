---
number: 48
title: 'Windows: clicks don''t work, right-click pastes into the menu'
status: In progress
category: powershell
creator: Ahmad
created: 2026-10-30 22:18
kind: todo
latest: '10-30: Started'
description: 'Ahmad''s Plane comment on #41 (2026-10-30), PowerShell sshdd on Windows, no SSH: scroll wheel works, a click on a menu item does nothing; right-click pastes the clipboard and the menu reads it as hotkeys. Wants pasting disabled in the main menu.'
---
## Updates
- **Started 2026-10-30.**
- **2026-10-30.** Paste guard: the main menu (bash + PowerShell) drops a burst of already-queued keys (a paste) instead of reading it as hotkeys; tests/test_paste_guard.py. Clicks on Windows: waiting for handoff/mouse-diag.ps1 output from Ahmad (Windows Terminal vs classic console).
