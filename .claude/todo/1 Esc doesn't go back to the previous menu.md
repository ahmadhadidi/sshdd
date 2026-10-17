---
number: 1
title: Esc doesn't go back to the previous menu
status: Review
category: tui
creator: Ahmad
created: 2026-10-17 20:15
kind: todo
latest: '10-17: Cause: prompts read inside $(...) returned 1 on Esc but callers ignored it, so Esc fell through: Key comment went on to the passphrase (G, W),…'
description: In any menu, Esc does nothing. After pressing Esc 3 times, Q has to be pressed 3 times to get back to the main menu. Esc should go back one menu. Imported from todo2.md on 2026-10-17; not re-checked whether still open.
---
## Updates
- **Started 2026-10-17.**
- **Ready for review 2026-10-17.** Cause: prompts read inside $(...) returned 1 on Esc but callers ignored it, so Esc fell through: Key comment went on to the passphrase (G, W), confirm_user_choice took the default (Esc = yes when default Y), import paths continued; two callers tested _SELECT_CANCELLED after $(...) where it is always stale. The host list said 'Esc = enter manually' but cancelled; now Esc cancels everywhere, the hint reads '(or type an IP / hostname)', and typed text that isn't a host is used directly (no second prompt; '10' still = subnet shorthand). PS parity. Tests: tests/test_esc_cancels.py (new pyte screen harness tests/screen.py), PS test in test_ssh_config_parse.py. Couldn't reproduce 'Q three times': one Q quits after every Esc path tested.
