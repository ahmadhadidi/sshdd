---
number: 19
title: Support keys that live only in 1Password
status: Inbox
category: ssh-ops
creator: Ahmad
created: 2026-10-19 06:41
kind: todo
latest: —
description: 'Ahmad''s MBP: private keys live in 1Password (no private files); config has Host * IdentityAgent <1Password socket> and IdentityFile ~/.ssh/<key>.pub. Known gaps (from #18, not yet tested with 1Password): Test Connection runs ssh -F /dev/null -i <file>, so the 1Password agent isn''t used; key listing, install and delete assume private files in ~/.ssh; with more than ~5 keys in the agent, installs may hit ''Too many authentication failures''. Needs a design agreed with Ahmad first. (2026-10-19)'
---
## Updates
