---
number: 28
title: Ctrl+\ (SIGQUIT) kills the prompt and jumps back a step
status: Review
category: tui
creator: Claude
created: 2026-10-22 20:59
kind: todo
latest: '10-22: menu-renderer.sh: trap '''' QUIT (inherited by prompts and dd); fuzz example ''\x1c'' fails on the old code. PowerShell not checked.'
description: 'Found by the H3 fuzzer (test_fuzz_key_comment, text=''\x1c''), blocks the #20 commit: sshdd has no QUIT trap, so Ctrl+\ kills the $(...) subshell of the Key comment prompt and W goes back to ''Enter SSH key name''. Pre-existing (same on 9932968). (2026-10-22)'
---
## Updates
- **Started 2026-10-22.** Ahmad: Ctrl+\ does nothing (ignore SIGQUIT). The real-~/.ssh check stays as is (agent.sock relinked by a login fails it; rerun).
- **Ready for review 2026-10-22.** menu-renderer.sh: trap '' QUIT (inherited by prompts and dd); fuzz example '\x1c' fails on the old code. PowerShell not checked.
