---
number: 4
title: Generate SSH Key (without installation) must not ask to select a key
status: Review
category: tui
creator: Ahmad
created: 2026-10-17 20:15
kind: todo
latest: '10-17: W (Generate Local SSH Key) now asks ''Enter SSH key name'' directly instead of listing existing keys; re-asks on empty names, unsafe characters (letters,…'
description: When generating a key, create it straight away; asking to select an existing SSH key is senseless and confusing. Imported from todo2.md on 2026-10-17; not re-checked whether still open.
---
## Updates
- **Started 2026-10-17.**
- **Ready for review 2026-10-17.** W (Generate Local SSH Key) now asks 'New key name:' instead of listing existing keys; re-asks on empty names, unsafe characters (letters, digits, . _ @ + - only) and names already in ~/.ssh, so ssh-keygen's Overwrite prompt can't appear. G keeps its picker (installing an existing key is valid there). PS parity (Read-NewSSHKeyName). Tests: test_esc_cancels.py::test_generate_local_asks_for_a_new_name, PS test in test_ssh_config_parse.py.
- **Started 2026-10-17.** back from Review: full suite failed, investigating
- **Ready for review 2026-10-17.** W (Generate Local SSH Key) now asks 'Enter SSH key name' directly instead of listing existing keys; re-asks on empty names, unsafe characters (letters, digits, . _ @ + - only) and names already in ~/.ssh, so ssh-keygen's Overwrite prompt can't appear. G keeps its picker. PS parity (Read-NewSSHKeyName). Tests: test_esc_cancels.py::test_generate_local_asks_for_a_new_name + PS test; full suite passes.
