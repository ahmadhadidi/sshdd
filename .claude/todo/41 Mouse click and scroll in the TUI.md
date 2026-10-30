---
number: 41
title: 'Mouse: click and scroll in the TUI'
status: Review
category: tui
creator: Ahmad
created: 2026-10-26 19:03
kind: todo
latest: '10-30: Ahmad: clicking did not work, disable pasting (RMB on the mouse) in the main menu because whatever is in the clipboard is being interpreted from the…'
description: 'Like herdr (crossterm mouse capture): enable SGR mouse reporting (ESC[?1000h ESC[?1006h), map clicks to menu rows, wheel scrolls; capture switched off in every exit path; a way to turn it off (capture blocks normal text selection). (Ahmad, 2026-10-26)'
---
## Updates

## Answers (Ahmad, 2026-10-26)
- Click: like herdr (clicking a tab/pane/workspace activates it): one click opens a menu item / chooses a list entry.
- Scope: everywhere (menu, pick lists, checklists, pagers, key list, Conf Defaults, help).
- On by default; --no-mouse switches it off (drag-selecting text needs Shift/Option while on).
- bash first; PowerShell as a follow-up.
- Design (Claude): mouse reporting only while an sshdd screen reads keys; off before ssh, editors and text prompts, and in every exit path.
- **Started 2026-10-26.**
- **Ready for review 2026-10-26.** bash: click opens menu items / list entries / key rows / F5 fields, toggles checklist entries, wheel scrolls everywhere; capture only while an sshdd screen waits for a key (off for ops, editors, prompts, exit); --no-mouse + F5 Mouse on/off + setup/alias.sh --no-mouse. tests/test_mouse.py (15; 14 fail on the old code). PowerShell: #42.
- **Comment 2026-10-30 (Ahmad, Plane).** clicking did not work, disable pasting (RMB on the mouse) in the main menu because whatever is in the clipboard is being interpreted from the hotkey of the menu., the scroll wheel works but clicking on a menu item does not.
