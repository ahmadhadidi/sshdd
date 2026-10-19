---
number: 14
title: 'List Authorized Keys: one user''s file or all users''?'
status: In progress
category: ssh-ops
creator: Ahmad
created: 2026-10-17 21:40
kind: todo
latest: '10-19: Ahmad''s answers (2026-10-19): ask each time (''this user'' / ''all users''; all users needs root or passwordless sudo on the remote); only…'
description: Does 'List Authorized Keys on Remote Host' list only the specified user's keys, or all users' authorized_keys on the remote host? (Ahmad, 2026-10-17)
---
## Updates
- **2026-10-17 answer (Claude):** only the entered user: both bash and PS run `ssh user@host "cat ~/.ssh/authorized_keys"`; `~` is that user's home. Not other users' files, not `authorized_keys2`, not a custom `AuthorizedKeysFile` from the server's sshd_config. All users would need root/sudo on the remote. Open: does Ahmad want an all-users option?
- **Started 2026-10-19.** Ahmad's answers (2026-10-19): ask each time ('this user' / 'all users'; all users needs root or passwordless sudo on the remote); only ~/.ssh/authorized_keys (no authorized_keys2, no sshd -T); all-users list grouped by user, one heading per user (name + path), keys numbered on through the whole list.
