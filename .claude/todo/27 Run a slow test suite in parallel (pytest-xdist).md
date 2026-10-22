---
number: 27
title: Run a slow test suite in parallel (pytest-xdist)
status: Review
category: tests
creator: Claude
created: 2026-10-22 20:10
kind: lesson
latest: '10-22: claude-init df47289: global skill parallel-test-suite.'
description: 'The pre-commit suite took 20 min 08 s serially (390 tests); with pytest-xdist -n auto on 12 cores it takes 2 min 16-21 s (3 runs): ~8.6x faster, ~17.8 min saved per commit. Parallel needed shared state isolated first: temp-file leak check on global /tmp (per-test TMPDIR, app honours it), system-wide pgrep (scoped to the test''s session). Place: claude-init global skill parallel-test-suite.'
---
## Updates
- **Ready for review 2026-10-22.** claude-init df47289: global skill parallel-test-suite.
