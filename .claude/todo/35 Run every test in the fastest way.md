---
number: 35
title: Run every test in the fastest way
status: Review
category: tests
creator: Ahmad
created: 2026-10-24 09:24
kind: todo
latest: '10-24: make test-all (scripts/test-all.sh): local in parallel + LXC alongside, then timing; all 438 passed in 3:01. worksteal in hook (150-153 s vs 172 s).…'
description: Run all tests again, make sure they all pass, and run them in the most optimized way. (Ahmad, 2026-10-24)
---
## Updates
- **Started 2026-10-24.**
- **Ready for review 2026-10-24.** make test-all (scripts/test-all.sh): local in parallel + LXC alongside, then timing; all 438 passed in 3:01. worksteal in hook (150-153 s vs 172 s). Fixed on the way: #36; test-all.sh's background job ignored Ctrl+C (set -m).
