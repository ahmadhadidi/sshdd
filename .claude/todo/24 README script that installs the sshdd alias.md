---
number: 24
title: 'README: script that installs the sshdd alias'
status: Review
category: docs
creator: Ahmad
created: 2026-10-22 19:11
kind: todo
latest: '10-22: README Alias sections: paste-in installers (bash/zsh + PowerShell) replace the hand-written aliases; tests/test_readme_alias.py runs them from the…'
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
