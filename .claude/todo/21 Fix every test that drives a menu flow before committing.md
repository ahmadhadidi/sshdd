---
number: 21
title: Fix every test that drives a menu flow before committing
status: Review
category: tests
creator: Claude
created: 2026-10-22 11:29
kind: lesson
latest: '10-22: lib/bash/CLAUDE.md Key implementation notes (commit follows).'
description: '#14 added a question to Z; only CT tests were updated and the pre-commit hook failed twice (test_errors, robustness helper). Rule: grep every test and helper that drives the item, fix all in one pass, run them before committing. Place: lib/bash/CLAUDE.md (project).'
---
## Updates
- **Ready for review 2026-10-22.** lib/bash/CLAUDE.md Key implementation notes (commit follows).
