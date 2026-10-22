---
number: 20
title: 'Host picker: a new name should ask for the address'
status: Review
category: ssh-ops
creator: Ahmad
created: 2026-10-22 11:22
kind: todo
latest: '10-22: e94b82d: typed new name asks for the address (pre-filled), alias = that name; bash+PS; 4 new/changed tests fail on old code. Not run live on CT 213.'
description: 'Install SSH Key: typing claude-ho4 (no config entry, no DNS) in ''Select remote host (type to filter or create new)'' connected to ''claude-ho4'' instead of asking for the IP or last 1-3 digits (subnet shorthand).'
---
## Updates

## Answers (Ahmad, 2026-10-22)
- Mechanic name: subnet shorthand (last 1-3 digits → `<subnet>.N`).
- When: always, for any typed name not in ~/.ssh/config (not only unresolvable ones). The address prompt is pre-filled with the typed name, editable.
- Alias: the config block gets the typed name (not the remote hostname).
- Prompt: same as the manual prompt: `Enter remote IP / hostname (or last 1-3 digits for <subnet>.xx):`, after a line `<name> isn't in ~/.ssh/config.`
- **Started 2026-10-22.**
- **Ready for review 2026-10-22.** e94b82d: typed new name asks for the address (pre-filled), alias = that name; bash+PS; 4 new/changed tests fail on old code. Not run live on CT 213.
