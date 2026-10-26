---
number: 34
title: 'Timing tests fail under parallel load: run them serially'
status: Review
category: tests
creator: Claude
created: 2026-10-23 14:19
kind: todo
latest: '10-23: pytest marker serial; hook runs -m ''not lxc and not serial'' -n auto, then -m serial; TEST.md. Limit unchanged (80 ms).'
description: 'test_arrow_latency (median < 80 ms, guards #11''s 100 ms lag) measured 88 ms in the #33 hook run under xdist. Fix: pytest marker ''serial''; the hook runs those after the parallel run. Limit unchanged. (2026-10-23)'
---
## Updates
- **Ready for review 2026-10-23.** pytest marker serial; hook runs -m 'not lxc and not serial' -n auto, then -m serial; TEST.md. Limit unchanged (80 ms).
- **2026-10-23 (2).** test_paste_into_comment (800-char paste within 20 s; 7-11 s normally) took 22.9 s under load in the #32 hook run: marked serial too. Commits: #34 a4da14e, this one follows.
- **2026-10-26.** test_arrow_latency failed once in the #44 hook (93 ms) right after the parallel stage. Same median on the code before and after #41 (~30 ms, 5 runs each). Load average was 27 (5 min) on 12 cores with other work on the node; LXC shows the node load. The timing tests need a quiet node, not only a quiet CT.
