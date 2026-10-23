---
number: 24
title: 'README: script that installs the sshdd alias'
status: Review
category: docs
creator: Ahmad
created: 2026-10-22 19:11
kind: todo
latest: '10-23: ✏️ value list above the bash block (no comments inside: zsh paste breaks), inline ✏️ comments in PowerShell, optional password (kept out of the alias…'
description: A README script that adds the sshdd alias (cloud or local, by what's on the laptop) to the right rc file (~/.zshrc on a Mac, ~/.bashrc otherwise), following best practice. (2026-10-22)
---
## Updates

## Answers (Ahmad, 2026-10-22)
- "Claude or local" = cloud or local: local if ~/sshdd is cloned, else cloud; no question.
- rc file by login shell ($SHELL zsh → ~/.zshrc, else bash; bash on macOS → ~/.bash_profile).
- Inline in the README (no install script in the repo); replaces the hand-written alias blocks.
- PowerShell version too, same rules ($PROFILE).
- **Started 2026-10-22.**
- **Ready for review 2026-10-22.** README Alias sections: paste-in installers (bash/zsh + PowerShell) replace the hand-written aliases; tests/test_readme_alias.py runs them from the README. zsh itself not installed here: the zsh path is tested only for the file it picks.
- **Started 2026-10-22.** Ahmad 2026-10-22: format the installer blocks to read nicer; bash version approved (subshell kept: set -e can't close the terminal).
- **Ready for review 2026-10-23.** Installer blocks reformatted (one step per line; bash subshell + set -e, PS & {} + ErrorActionPreference Stop); approved by Ahmad 2026-10-23.
- **Started 2026-10-23.** Ahmad 2026-10-23: ✏️ descriptions for the values and an optional password. Bash: ✏️ list above the block (inline # comments break a default zsh paste: values silently empty, tested with zsh 5.9); PowerShell: inline ✏️ comments.
- **Ready for review 2026-10-23.** ✏️ value list above the bash block (no comments inside: zsh paste breaks), inline ✏️ comments in PowerShell, optional password (kept out of the alias when empty); 7 README tests; checked in zsh 5.9.
