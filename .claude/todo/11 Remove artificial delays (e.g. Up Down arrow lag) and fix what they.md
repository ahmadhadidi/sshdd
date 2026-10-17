---
number: 11
title: Remove artificial delays (e.g. Up/Down arrow lag) and fix what they masked
status: Review
category: tui
creator: Ahmad
created: 2026-10-17 20:39
kind: todo
latest: '10-17: Arrow lag cause: _esc_drain read the rest of every escape sequence with read -r (no -n) under a 100 ms VTIME, so each arrow waited out the timeout (126…'
description: Older models added artificial delays to get expected behaviour; Up/Down arrows visibly lag. After the test work, remove the delays, see what breaks, and fix the real bugs (Ahmad, 2026-10-17).
---
## Updates
- **Started 2026-10-17.** Ahmad 2026-10-17: done = no artificial sleeps in the tool; real waits (spinner, I/O timeouts) stay; arrows instant; full suite + herdr pass.
- **Ready for review 2026-10-17.** Arrow lag cause: _esc_drain read the rest of every escape sequence with read -r (no -n) under a 100 ms VTIME, so each arrow waited out the timeout (126 ms per press measured) and held-down arrows merged into one unknown key and were dropped (highlight didn't move at all). Now dd reads the byte after ESC (only a bare Esc waits 100 ms) and read -n1 reads the rest up to the final byte: 21 ms per press, held-down arrows land on every step. Also: verbose-mode 'sleep 1' -> 'press any key to start'; PS key poll 50 -> 10 ms. Left on purpose: spinner frame interval (animation), PS poll (no blocking read with timeout in PS). tests/test_keys.py: held-down burst + latency < 80 ms; old code fails both.
