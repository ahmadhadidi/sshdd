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
- **2026-10-30.** Diagnostic (Ahmad, Windows Terminal, pwsh 7.6.9, console mode 0x1B7): both work. Mouse records: left press buttons=0x1 flags=0, release 0x0 flags=0, right 0x2, middle 0x4, wheel flags=4 with 0x800000 up / 0xFF800000 down, double-click flags 3, and a constant stream of moves (flags 1). VT mode: SGR ESC[<b;col;rowM/m as key chars. sshdd reads those fields the same way, so the failed clicks were likely an old local clone ($HOME\sshdd, the alias prefers it): asked Ahmad to check. Fix from the data: Available() discards moves/releases/key-ups (PeekConsoleInput) so the main menu does not block on them.
