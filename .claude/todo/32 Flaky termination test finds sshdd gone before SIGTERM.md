---
number: 32
title: 'Flaky: termination test finds sshdd gone before SIGTERM'
status: Review
category: tests
creator: Claude
created: 2026-10-23 13:10
kind: todo
latest: '10-26: Likely PID wraparound (see note); _pid uses pgrep -o. Unproven: forcing a wrap needs root.'
description: 'test_cleanup_on_termination[menu-sigterm] failed once in the #31 hook run (xdist, 2026-10-23): os.kill(_pid(marker)) raised ProcessLookupError. Passes 3/3 alone. pgrep lists by PID (no wraparound: ~990k of 4.19M), so the main sshdd process must already have been gone; sshdd doesn''t re-exec. Blocks #31''s commit. (2026-10-23)'
---
## Updates
- **Started 2026-10-23.**
- **2026-10-23.** Not reproduced in 8 more parallel runs (3,200 test runs). Ruled out: a subshell answering pgrep (pgrep lists by PID; the main process is lowest), PID reuse (~990k of 4.19M), another test's signal (Term.close hits only its own group). Ahmad: keep a failure report in the test (process list + last output when sshdd is missing) and leave #32 open.
- **2026-10-26.** Likely cause: PID wraparound. The counter went ~3.4M (10-23) -> ~0.99M (10-24) -> ~1.7M (10-26), pid_max 4.19M; after a wrap an sshdd $(...) subshell (same command line) can get a lower PID than sshdd, pgrep lists it first, and it is gone by the signal. Seen again in test_cleanup_inside_subscreens[help-close-terminal] (os.getpgid: No such process). Fix: pgrep -o (oldest). Not provable without root (forcing a wrap).
- **Ready for review 2026-10-26.** Likely PID wraparound (see note); _pid uses pgrep -o. Unproven: forcing a wrap needs root.
