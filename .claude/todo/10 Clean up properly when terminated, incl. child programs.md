---
number: 10
title: Clean up properly when terminated, incl. child programs
status: Review
category: tui
creator: Ahmad
created: 2026-10-17 20:36
kind: todo
latest: '10-17: Exit cleanup: temp files (/tmp/.hprobe-, askpass, _prompt_remote''s mktemp) registered with _cleanup_add and removed on every exit; background host…'
description: The tool does not clean up after itself correctly when it's terminated, especially when selecting menu items that open programs or use other bash instances within them, for example testing SSH keys (Ahmad, 2026-10-17).
---
## Updates
- **Started 2026-10-17.** Ahmad 2026-10-17: all ways of ending it must clean up: Ctrl+C, Ctrl+Z, closing the terminal/SSH drop (SIGHUP), kill (SIGTERM), herdr pane close, also mid-operation (e.g. Test SSH).
- **Ready for review 2026-10-17.** Exit cleanup: temp files (/tmp/.hprobe-*, askpass, _prompt_remote's mktemp) registered with _cleanup_add and removed on every exit; background host probes and the spinner killed (TERM + CONT, since Ctrl+Z stopped them and the old _spin_stop then hung forever); SIGHUP (closed terminal / SSH drop) now trapped. tests/test_termination.py: Ctrl+C, Ctrl+Z, SIGTERM, SIGHUP x (menu, during host probe) check exit, stty mode, alternate screen left, no temp files, no probe processes; old code fails all 4 mid-probe cases. Limit: SIGTERM to sshdd alone during a running ssh waits for that ssh. PS: no temp files/jobs; try/finally already restores the screen. This machine has 86+ leftover /tmp/.hprobe-* files from before (mostly my test runs); not deleted, ask.
