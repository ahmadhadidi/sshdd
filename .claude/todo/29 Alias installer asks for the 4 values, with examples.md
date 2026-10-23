---
number: 29
title: Alias installer asks for the 4 values, with examples
status: Review
category: docs
creator: Ahmad
created: 2026-10-23 08:28
kind: todo
latest: '10-23: setup/alias.sh + setup/alias.ps1, README one-liners; 10 tests (flags with any characters, prompts on a terminal with the password hidden, rc by shell…'
description: The README alias installer should prompt for user, subnet, suffix and password (with examples of how sshdd is used) instead of the user editing the block. (Ahmad, 2026-10-23)
---
## Updates

## Answers (Ahmad, 2026-10-23)
- Replace the README's paste-in blocks with cloud one-liners that run setup scripts kept in the repo, for every OS (bash for macOS/Linux, PowerShell for Windows).
- Folder: setup/ (scripts/ holds dev tools).
- The 4 values (user, subnet, comment suffix, password) are optional flags; whatever isn't passed is asked (Enter keeps the default); password prompt hidden. Usage examples printed at the end.
- Defaults: the README placeholders (myuser, 192.168.0, -[my-machine]).
- **Started 2026-10-23.**
- **Ready for review 2026-10-23.** setup/alias.sh + setup/alias.ps1, README one-liners; 10 tests (flags with any characters, prompts on a terminal with the password hidden, rc by shell incl. macOS bash, symlink, rerun, PowerShell params and prompts); shellcheck clean; checked from zsh 5.9. The cloud URLs work once pushed.
