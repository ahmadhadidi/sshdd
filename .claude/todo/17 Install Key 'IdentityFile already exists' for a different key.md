---
number: 17
title: 'Install Key: ''IdentityFile already exists'' for a different key'
status: Review
category: ssh-ops
creator: Ahmad
created: 2026-10-19 06:18
kind: todo
latest: '10-19: 77b58d2 (pushed). Install ''dev'' next to dev-lan now adds it; ''Using key:'' shows the path only (awk instead of GNU-only sed \s). Also fixed: Remove…'
description: 'MBP cloud run, Install SSH Key (I) of key ''dev'' to dev-poc, whose block has IdentityFile /Users/hdd/.ssh/dev-lan: ''Add dev as IdentityFile? [Y/n]'' -> ''⚠️ IdentityFile already exists under Host dev-poc.'' (dev was not added). Also ''Using key: IdentityFile /Users/hdd/.ssh/dev-lan'' shows the keyword. (Ahmad, 2026-10-19)'
---
## Updates
- **Started 2026-10-19.** Cause 1: duplicate check was a substring grep (dev ⊂ dev-lan); PS same. Cause 2: sed \s is GNU-only, so macOS printed 'IdentityFile /path' (and Test Connection got that as the key path). Also found: removing 'dev' removed lan-dev (bash, optional slash) and dev-lan (PS). Fixed with exact compares; tests/test_identity_files.py.
- **Ready for review 2026-10-19.** 77b58d2 (pushed). Install 'dev' next to dev-lan now adds it; 'Using key:' shows the path only (awk instead of GNU-only sed \s). Also fixed: Remove IdentityFile 'dev' removed lan-dev (bash) / dev-lan (PS). tests/test_identity_files.py. Not run on a Mac.
