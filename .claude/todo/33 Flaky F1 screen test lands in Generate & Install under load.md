---
number: 33
title: 'Flaky: F1 screen test lands in Generate & Install under load'
status: Review
category: tests
creator: Claude
created: 2026-10-23 14:01
kind: todo
latest: '10-23: tests/test_screens.py _back_to_main waits for each key''s redraw; 0/21 vs 1/11 under load.'
description: 'test_every_screen[''\x1bOP''-40-100] failed once in the #32 hook run (xdist, 2026-10-23): expected the main menu after the F1 page, saw ''Generate & Install'' (menu item 1). Passes 3/3 alone. (2026-10-23)'
---
## Updates
- **Started 2026-10-23.**
- **2026-10-23.** Cause: _back_to_main sent ESC, ESC, Q, ENTER with fixed 0.6 s gaps; under load the menu redrew late and a spare ENTER opened item 1. Reproduced 1/11 (F1 test looped during a full parallel run). Fix: each key waits for the screen to react and settle. 0/21 under the same load. Seen only under double load (not in hook runs): test_arrow_latency, test_ctrl_u_clears_prefilled_default.
- **Ready for review 2026-10-23.** tests/test_screens.py _back_to_main waits for each key's redraw; 0/21 vs 1/11 under load.
