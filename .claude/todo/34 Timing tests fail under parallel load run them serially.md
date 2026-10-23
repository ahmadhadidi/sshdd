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
