---
number: 7
title: 4 LXC tests stop at 'Enter remote IP / hostname'
status: Review
category: tests
creator: Claude
created: 2026-10-17 20:31
kind: todo
latest: '10-17: Cause: ff4d475 (reachability dots) only matched the exact display line, so typed filter text fell through to the manual IP prompt.…'
description: 'Against CT 213 (2026-10-17), `bash scripts/run-tests.sh -m lxc`: 6 pass, 4 fail (01 gen_install passphraseless/passphrased, test_lxc_connection no_key/with_key). After the lxc-test alias is chosen the TUI prompts ''Enter remote IP / hostname (or last 1-3 digits...)'' where the tests expect ''Remote username''. Password auth to the CT works (the with_key fixture gets past it). Possibly the same alias/HostName lookup as #3; unconfirmed.'
---
## Updates
- **Started 2026-10-17.**
- **Ready for review 2026-10-17.** Cause: ff4d475 (reachability dots) only matched the exact display line, so typed filter text fell through to the manual IP prompt. read_remote_host_address now accepts an alias or a filter that leaves one host (PS parity). Test 01 now adds its own Host block instead of needing one in ~/.ssh/config. pytest -m lxc: 10/10; full suite 41 passed.
