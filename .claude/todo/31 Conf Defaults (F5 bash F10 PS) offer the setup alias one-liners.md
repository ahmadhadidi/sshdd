---
number: 31
title: 'Conf Defaults (F5 bash / F10 PS): offer the setup/alias one-liners'
status: Review
category: tui
creator: Ahmad
created: 2026-10-23 09:52
kind: todo
latest: '10-23: bash F5 / PS F10: ''To persist'' = setup/alias one-liners (🐚 macOS/Linux, 🪟 Windows) with current values incl. password, run-once below; all values…'
description: The Conf Defaults screen's 'To persist across sessions' shows only run-once launch commands; it should offer the setup/alias.sh / alias.ps1 one-liners with the current values. (Ahmad, 2026-10-23)
---
## Updates

## Answers (Ahmad, 2026-10-23)
- Layout: "To persist across sessions" = the 2 setup one-liners (🐚 macOS / Linux, 🪟 Windows) with the current values; the 4 launch commands stay below under "Run once".
- A set default password is included in the setup line (--password / -Password).
- **Started 2026-10-23.**
- **Ready for review 2026-10-23.** bash F5 / PS F10: 'To persist' = setup/alias one-liners (🐚 macOS/Linux, 🪟 Windows) with current values incl. password, run-once below; all values single-quoted (PS screen used double quotes before); PS wraps instead of cutting with '...'. tests/test_conf_defaults_setup.py runs the lines copied off both screens.
