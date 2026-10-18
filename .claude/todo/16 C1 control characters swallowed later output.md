---
number: 16
title: C1 control characters swallowed later output
status: In progress
category: tui
creator: Claude
created: 2026-10-18 22:36
kind: todo
latest: '10-18: Fix and regression tests written (bash + PS); committing.'
description: 'Found by the H3 fuzz test (hypothesis): typing U+009D into a prompt. Bash echoed its two bytes one by one (each passed [[:cntrl:]]), PS took every char >= 32; terminals read U+009D as the start of an OSC string and swallow everything printed after it. Fix: bash _utf8_tail reads whole UTF-8 characters per key; PS uses [char]::IsControl. Limit: under LANG=C a non-ASCII character is now dropped (it was bytes before).'
---
## Updates
- **Started 2026-10-18.** Fix and regression tests written (bash + PS); committing.
