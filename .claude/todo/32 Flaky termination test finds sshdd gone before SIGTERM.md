---
number: 32
title: 'Flaky: termination test finds sshdd gone before SIGTERM'
status: In progress
category: tests
creator: Claude
created: 2026-10-23 13:10
kind: todo
latest: '10-23: Started'
description: 'test_cleanup_on_termination[menu-sigterm] failed once in the #31 hook run (xdist, 2026-10-23): os.kill(_pid(marker)) raised ProcessLookupError. Passes 3/3 alone. pgrep lists by PID (no wraparound: ~990k of 4.19M), so the main sshdd process must already have been gone; sshdd doesn''t re-exec. Blocks #31''s commit. (2026-10-23)'
---
## Updates
- **Started 2026-10-23.**
- **2026-10-23.** Not reproduced in 8 more parallel runs (3,200 test runs). Ruled out: a subshell answering pgrep (pgrep lists by PID; the main process is lowest), PID reuse (~990k of 4.19M), another test's signal (Term.close hits only its own group). Ahmad: keep a failure report in the test (process list + last output when sshdd is missing) and leave #32 open.
