---
number: 42
title: Mouse in the PowerShell TUI
status: Review
category: powershell
creator: Claude
created: 2026-10-26 19:24
kind: todo
latest: '10-27: Branch ps-mouse (not main): macOS/Linux pwsh tested (8 tests, 7 fail on the old code; all 472 pass); Windows reader (ReadConsoleInput) compiles,…'
description: 'Follow-up of #41 (bash first, Ahmad 2026-10-26): click and wheel in sshdd.ps1. Windows console delivers mouse as separate input events that ReadKey doesn''t return; needs research (VT input mode / ReadConsoleInput). Also -NoMouse and F10 Conf Defaults. (2026-10-26)'
---
## Updates
- **Started 2026-10-26.** Ahmad 2026-10-26: build it. Same behaviour as bash #41 (click opens like herdr, everywhere, on by default, -NoMouse + F10 field).

## Answers (Ahmad, 2026-10-26)
- Same behaviour as bash #41.
- Windows too (ReadConsoleInput via C#, QuickEdit off while capturing); Ahmad tests it on a Windows machine before it ships: not pushed to main until checked.
- macOS/Linux pwsh: click reports arrive through ReadKey one character at a time (ESC [ < b ; col ; row M), KeyAvailable true in between (tested 2026-10-26).
- Test build: branch ps-mouse (Ahmad, 2026-10-27); merged into main after Ahmad checks it on Windows.
- **Ready for review 2026-10-27.** Branch ps-mouse (not main): macOS/Linux pwsh tested (8 tests, 7 fail on the old code; all 472 pass); Windows reader (ReadConsoleInput) compiles, untested on Windows: waiting for Ahmad's check.
- **2026-10-30.** Ahmad: ship it on main without the Windows test (no branch swapping); fast-forwarded main to ps-mouse and pushed. Windows still unchecked.
