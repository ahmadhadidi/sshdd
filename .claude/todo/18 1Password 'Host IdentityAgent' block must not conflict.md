---
number: 18
title: 1Password 'Host * IdentityAgent' block must not conflict
status: In progress
category: ssh-ops
creator: Ahmad
created: 2026-10-19 06:37
kind: todo
latest: '10-19: Started'
description: '1Password (Terminal forwarding) injects into ~/.ssh/config: ''Host *'' / '' IdentityAgent "~/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock"''. Make sure every sshdd function works with it on the machine running sshdd. (Ahmad, 2026-10-19)'
---
## Updates
- 2026-10-19 Tested: every config reader/writer ignores 'Host *' and leaves the block byte-for-byte (top or end of file), bash+PS; ssh with a missing IdentityAgent socket logs in with the key file (CT 213). Ahmad's keys live in 1Password → follow-up #19.
- **Started 2026-10-19.**
