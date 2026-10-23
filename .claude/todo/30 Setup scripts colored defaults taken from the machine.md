---
number: 30
title: 'Setup scripts: colored defaults taken from the machine'
status: Review
category: tui
creator: Ahmad
created: 2026-10-23 08:51
kind: todo
latest: '10-23: Defaults from the machine (whoami / default-route subnet, fallback 192.168.0 / -[short hostname]), shown in teal (bash bold; PowerShell cyan,…'
description: 'In setup/alias.sh and alias.ps1, color the default value in each question so it''s clear what''s asked; defaults from the user''s machine: username (whoami), a calculated subnet, the hostname for the suffix. (Ahmad, 2026-10-23)'
---
## Updates

## Answers (Ahmad, 2026-10-23)
- Default value in each question in teal bold (the app's color), shown in [ ]; Enter keeps it (not pre-typed: macOS bash 3.2 has no read -i).
- Defaults from the machine: username = whoami, subnet = first 3 parts of the IP on the default route (fallback 192.168.0), suffix = -[short hostname]. Replaces #29's placeholder defaults.
- **Started 2026-10-23.**
- **Ready for review 2026-10-23.** Defaults from the machine (whoami / default-route subnet, fallback 192.168.0 / -[short hostname]), shown in teal (bash bold; PowerShell cyan, Write-Host can't bold); 13 tests incl. macOS route stubs and fallback.
