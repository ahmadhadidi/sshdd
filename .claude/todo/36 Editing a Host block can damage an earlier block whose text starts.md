---
number: 36
title: Editing a Host block can damage an earlier block whose text starts the same
status: Review
category: ssh-ops
creator: Claude
created: 2026-10-24 09:32
kind: todo
latest: '10-24: _replace_host_block matches whole lines (perl + python fallback); tests/test_units.py whole_lines_only (3/4 variants fail on the old code). PowerShell…'
description: 'Found by test_properties (hypothesis) in make test-all, 2026-10-24: config ''host a0'' then ''host a''; _get_host_block a + _replace_host_block wrote the new block over the ''host a'' inside ''host a0'', leaving its ''0'' (ssh -G a -> 1.1.1.10 instead of 1.1.1.1). Pre-existing. (2026-10-24)'
---
## Updates
- **Started 2026-10-24.**
- **Ready for review 2026-10-24.** _replace_host_block matches whole lines (perl + python fallback); tests/test_units.py whole_lines_only (3/4 variants fail on the old code). PowerShell unaffected (its block includes the newline; checked with the same config).
