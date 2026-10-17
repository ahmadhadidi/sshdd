---
number: 7
title: 4 LXC tests stop at 'Enter remote IP / hostname'
status: Inbox
category: tests
creator: Claude
created: 2026-10-17 20:31
kind: todo
latest: —
description: 'Against CT 213 (2026-10-17), `bash scripts/run-tests.sh -m lxc`: 6 pass, 4 fail (01 gen_install passphraseless/passphrased, test_lxc_connection no_key/with_key). After the lxc-test alias is chosen the TUI prompts ''Enter remote IP / hostname (or last 1-3 digits...)'' where the tests expect ''Remote username''. Password auth to the CT works (the with_key fixture gets past it). Possibly the same alias/HostName lookup as #3; unconfirmed.'
---
## Updates
