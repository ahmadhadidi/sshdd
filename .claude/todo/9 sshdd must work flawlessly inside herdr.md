---
number: 9
title: sshdd must work flawlessly inside herdr
status: Review
category: tui
creator: Ahmad
created: 2026-10-17 20:35
kind: todo
latest: '10-18: Not reproduced: in a throwaway herdr session (and tmux) every exit (Q, Exit item, Esc+Q, Ctrl+C, after ops, bash 3.2/5, cloud run) puts the prompt…'
description: The tool must work flawlessly when it's run in herdr (Ahmad, 2026-10-17).
---
## Updates
- **Started 2026-10-17.** Ahmad 2026-10-17: closing sshdd in herdr leaves the shell prompt in a weird location; it doesn't look like after a normal exit.
- **Ready for review 2026-10-18.** Not reproduced: in a throwaway herdr session (and tmux) every exit (Q, Exit item, Esc+Q, Ctrl+C, after ops, bash 3.2/5, cloud run) puts the prompt right below the output; tests/test_exit_cursor.py checks it in tmux and herdr with a cursor-position query and passes even without the change, so herdr's server-side emulator is fine. Guess per Ahmad: sshdd now asks the terminal for the cursor position before the alternate screen and moves it back explicitly after leaving it (bash _cursor_pos; PS RawUI.CursorPosition), for terminals/clients that don't restore it. UNCONFIRMED: please quit sshdd in your herdr and say if the prompt still lands oddly (a screenshot in ss/ helps).
- **Started 2026-10-18.** back from Review: suite failed
- **Ready for review 2026-10-18.** Not reproduced: in a throwaway herdr session (and tmux) every exit (Q, Exit item, Esc+Q, Ctrl+C, after ops, bash 3.2/5, cloud run) puts the prompt right below the output; tests/test_exit_cursor.py checks it in tmux and herdr with a cursor-position query and passes even without the change, so herdr's server-side emulator is fine. Guess per Ahmad: sshdd now asks the terminal for the cursor position before the alternate screen (bash _cursor_pos via dd, 100 ms cap; a first version with read -d hung terminals that don't answer, caught by the suite, test added) and moves it back after leaving it; PS uses RawUI.CursorPosition. UNCONFIRMED: please quit sshdd in your herdr and say whether the prompt still lands oddly (a screenshot in ss/ helps).
