---
number: 40
title: One SSH connection per operation (ControlMaster)
status: Inbox
category: ssh-ops
creator: Ahmad
created: 2026-10-26 18:34
kind: todo
latest: —
description: 'From herdr (ControlMaster/ControlPersist): sshdd opens a new connection per step (host-key check, fetch, change), so password hosts ask more than once and CT 213''s PerSourcePenalties count each one. Share one connection for an operation; bash only (Win32-OpenSSH has no ControlMaster). (Ahmad, 2026-10-26)'
---
## Updates
