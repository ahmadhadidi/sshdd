---
number: 15
title: Manage known_hosts locally and on the target
status: Review
category: ssh-ops
creator: Ahmad
created: 2026-10-18 21:23
kind: todo
latest: '10-18: f84ea1c. Bash+PS; 23 tests (CT 213 incl.). Security review fixes in the same commit. Open for Ahmad: hint wording (''Expected after a CT is destroyed…'
description: Manage the known_hosts file on the host machine and the target machine, to avoid the man-in-the-middle warnings that appear after a CT is destroyed and recreated. (Ahmad, 2026-10-18)
---
## Updates
- 2026-10-18 Ahmad's answers: on a changed host key, show host + old/new fingerprints and ask "[y/N] Forget the old key and retry?" (never automatic). Menu items: forget host key (local), list known hosts (local), Remove Host also offers to forget its key, and the same forget/list on the target's ~/.ssh/known_hosts over SSH ("the target's file too": the target also SSHes to recreated CTs).
- **Started 2026-10-18.** Layout: split, remote items under Remote (O list, B forget), local under Local (K list, F forget). Check before connecting: ssh-keyscan vs known_hosts right after the host is picked. Remote file: the SSH user's ~/.ssh/known_hosts only.
- **Ready for review 2026-10-18.** f84ea1c. Bash+PS; 23 tests (CT 213 incl.). Security review fixes in the same commit. Open for Ahmad: hint wording ('Expected after a CT is destroyed and recreated.' vs 'If you didn't recreate this host, answer N.'); L3: after Forget, the next accept-new op trusts the new key without showing it (ssh's normal TOFU). Windows ssh -G path format unverified.
