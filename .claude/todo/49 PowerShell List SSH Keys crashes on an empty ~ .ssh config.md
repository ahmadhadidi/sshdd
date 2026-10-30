---
number: 49
title: PowerShell List SSH Keys crashes on an empty ~/.ssh/config
status: Inbox
category: powershell
creator: Claude
created: 2026-10-30 22:23
kind: todo
latest: —
description: 'Found by #48''s test (2026-10-30): with an empty config, Show-SSHKeyInventory throws at config-display.ps1:214 ([regex]::Matches on $null: ''Value cannot be null''), Get-Content -Raw of an empty file returns $null. Bash is fine.'
---
## Updates
