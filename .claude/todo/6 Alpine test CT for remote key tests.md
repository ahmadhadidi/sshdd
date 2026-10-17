---
number: 6
title: Alpine test CT for remote key tests
status: Review
category: tests
creator: Ahmad
created: 2026-10-17 20:20
kind: todo
latest: '10-17: CT 213 sshdd-test on ho4: full clone of golden 324 (Alpine 3.24.1), 192.168.0.213, DE:AD:DE:AD:02:13, 1 core/256 MB/1 GB, onboot 1, Asia/Amman…'
description: 'Create an always-on Alpine CT (sshd, testuser/testpass with password auth, kraid with dev-lan.pub) on ho4 as the target for `pytest -m lxc`. Agreed 2026-10-17: reach root@ho4.lan via the forwarded agent; CTID picked by Ahmad after pct list; unprivileged, 1 core, 256 MB, 1 GB; onboot 1; tests'' LXC_HOST follows the chosen IP.'
---
## Updates
- **Started 2026-10-17.**
- **Ready for review 2026-10-17.** CT 213 sshdd-test on ho4: full clone of golden 324 (Alpine 3.24.1), 192.168.0.213, DE:AD:DE:AD:02:13, 1 core/256 MB/1 GB, onboot 1, Asia/Amman (tzdata), bash; testuser/testpass (password auth on), kraid with dev-lan.pub. Survived pct reboot; sshd up at boot. Logins checked: kraid key, hddssh-test alias, testuser via the tests' askpass fixture. pytest -m lxc: 6 pass, 4 fail in the TUI flow (#7). ho4 access: ~/.ssh/ho4-root on dev-poc, authorized for root@192.168.0.9.
