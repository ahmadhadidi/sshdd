---
number: 12
title: 'Cloud run fails: CRITICAL: Could not find /tmp/tui.sh'
status: Review
category: bash
creator: Ahmad
created: 2026-10-17 20:42
kind: todo
latest: '10-17: Cause: prompts.sh sourced tui.sh from its own dir; in a cloud run each lib is a temp file in /tmp, so it printed ''CRITICAL: Could not find /tmp/tui.sh''…'
description: '`bash <(curl -fsSL https://raw.githubusercontent.com/ahmadhadidi/sshdd/refs/heads/main/sshdd.sh) --user kraid --subnet 192.168.0 --comment-suffix "-[dev-poc]"` on dev-poc prints ''CRITICAL: Could not find /tmp/tui.sh'' (Ahmad, 2026-10-17).'
---
## Updates
- **Started 2026-10-17.**
- **Ready for review 2026-10-17.** Cause: prompts.sh sourced tui.sh from its own dir; in a cloud run each lib is a temp file in /tmp, so it printed 'CRITICAL: Could not find /tmp/tui.sh' (harmless: sshdd.sh had already loaded tui.sh). Removed the block. tests/test_cloud_loader.py serves this checkout over HTTP and runs the loader like bash <(curl ...); it reproduces the message on the old code. PS loader unaffected. Reaches cloud users only after a push to main.
