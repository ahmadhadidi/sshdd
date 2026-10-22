---
number: 25
title: Pre-commit tests in parallel (pytest-xdist)
status: Review
category: tests
creator: Ahmad
created: 2026-10-22 19:26
kind: todo
latest: '10-22: pytest-xdist in the hook (-n auto when installed) + -v --durations=0; serial 20:08 vs parallel 2:16-2:21 (12 cores); per-test TMPDIR, app honours it;…'
description: The hook's full local suite takes ~20 min (384 tests, run one after another). Run it in parallel with pytest-xdist. (Ahmad, 2026-10-22)
---
## Updates
- **Started 2026-10-22.**

## Answers and results (2026-10-22)
- Ahmad: do it, compare the time saved, add the lesson to claude-init. Temp files: app honours $TMPDIR (chosen over a tests-only fix).
- Same tree, same host (12 cores), nothing else running: serial 1208 s (20:08); `-n auto` 141 s, 141 s, 137 s (2:16-2:21). ~8.6x faster, ~17.8 min saved per hook run.
- Fixed for parallel: per-test TMPDIR (conftest) + `_mktemp_reg` uses `${TMPDIR:-/tmp}`; termination probe check `pgrep -s <session>`.
- Hook (.git/hooks/pre-commit, untracked): `-n auto` when xdist is importable; `-v --durations=0` (Ahmad).
- Seen twice: `real_ssh_untouched` flags `agent.sock` when Ahmad logs in during a run (~/.bashrc relinks it). Not a test fault; check left as is.
- **Ready for review 2026-10-22.** pytest-xdist in the hook (-n auto when installed) + -v --durations=0; serial 20:08 vs parallel 2:16-2:21 (12 cores); per-test TMPDIR, app honours it; probe check per session. Skill parallel-test-suite in claude-init (df47289).
