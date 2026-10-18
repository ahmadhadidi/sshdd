---
number: 8
title: Rigorous test plan (HCI/UX) and the tools it needs
status: Review
category: tests
creator: Ahmad
created: 2026-10-17 20:33
kind: todo
latest: '10-18: docs/TEST-PLAN.md: usability heuristics -> ~90 test items; 53 built, 16 partly open (marked 🔨), P2/P3 (macOS/Windows CI) not approved. 22 new test…'
description: Come up with every sort of rigorous test for the tool to make it as bullet-proof as possible; use HCI and UX principles so the tool behaves as expected; report which testing tools are needed to make testing and e2e tests straightforward and efficient. (Ahmad, 2026-10-17)
---
## Updates
- **Started 2026-10-17.** Ahmad 2026-10-17: plan + build everything (docs/TEST-PLAN.md, then implement every test in it).
- **Ready for review 2026-10-18.** docs/TEST-PLAN.md: usability heuristics -> ~90 test items; 53 built, 16 partly open (marked 🔨), P2/P3 (macOS/Windows CI) not approved. 22 new test files; suite 310 local + 28 on CT 213, all passing; every test in a temp HOME. Building it found and fixed 30 bugs (Findings section), incl. remote command injection, key deleted everywhere after two Enters, bash 3.2 empty-array crash, macOS without GNU timeout, PS BOM files OpenSSH rejects, path traversal in key names, duplicate keys on install, Ctrl+S freeze. Tools: pyte, hypothesis, shellcheck, tmux, PSScriptAnalyzer.
