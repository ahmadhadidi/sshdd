---
number: 2
title: F-key bar background must match the bar below it
status: Review
category: tui
creator: Ahmad
created: 2026-10-17 20:15
kind: todo
latest: '10-17: F-key bar was dim with no background; now reverse video with bold keys, same as the hint bar (bash; PS already matched). Also fixed: at 80 columns the…'
description: The top hint bar (F1 Best Practices, F2 SSH Config, F5 Conf Defaults, ? Help) needs the same background as the bar below it (Up/Dn Navigate, Enter Select, G Generate, T Test, D Delete, L List, Q Quit). Imported from todo2.md on 2026-10-17; not re-checked whether still open.
---
## Updates
- **Started 2026-10-17.**
- **Ready for review 2026-10-17.** F-key bar was dim with no background; now reverse video with bold keys, same as the hint bar (bash; PS already matched). Also fixed: at 80 columns the hint bar (82 chars) wrapped and scrolled the screen up a row; new _hint_bar drops shortcuts from the middle to fit, keeping Q Quit / ? Help. tests/test_main_menu_look.py checks every column of both bars at 80/100/140. Screenshot: handoff/main-menu-80x40.png.
