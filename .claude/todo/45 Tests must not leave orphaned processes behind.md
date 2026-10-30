---
number: 45
title: Tests must not leave orphaned processes behind
status: Inbox
category: tests
creator: Claude
created: 2026-10-26 23:07
kind: todo
latest: —
description: 'Found investigating #44''s hook failures (2026-10-26): 5 ''bash -c ... add_ssh_key_to_host_config'' processes from 2026-10-22 19:30-19:40 (my #26 _wait_key EOF loop) ran on with parent 1 for 4 days, ~14 h CPU each, and the load made test_arrow_latency fail (93/111 ms vs ~30 ms). subprocess.run(timeout) killed only the top bash; its $(...) subshell kept looping. Killed by PID with Ahmad''s OK. Fix: run such bash in its own process group and kill the group on timeout; check at the end of a run that no test process is left. (2026-10-26)'
---
## Updates
