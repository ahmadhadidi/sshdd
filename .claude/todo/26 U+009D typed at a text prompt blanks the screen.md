---
number: 26
title: U+009D typed at a text prompt blanks the screen
status: Review
category: tui
creator: Claude
created: 2026-10-22 19:28
kind: todo
latest: '10-22: read_colored_input reads whole characters via _wait_key; _wait_key returns Enter at end of input when stdin isn''t a terminal; U+009D pinned as a fuzz…'
description: 'Found by the H3 fuzzer during the #24 commit (test_fuzz_host_entry, text=''\x9d''): read_colored_input reads with read -r -n1 (byte by byte in bash 3.2), so both bytes of U+009D pass the [[:cntrl:]] filter and are echoed; the terminal starts an OSC string and swallows everything after. Fix: read keys via _wait_key (whole UTF-8 characters), as the other prompts do. (2026-10-22)'
---
## Updates
- **Started 2026-10-22.**
- **Ready for review 2026-10-22.** read_colored_input reads whole characters via _wait_key; _wait_key returns Enter at end of input when stdin isn't a terminal; U+009D pinned as a fuzz example (fails on the old code).
- **2026-10-22 (2).** Also: Ctrl+\ (SIGQUIT) killed dd mid-character, so a lone 0x80 of U+0080 was echoed (fuzzer, '\x1c\x80'). dd now ignores QUIT too (tui.sh, 3 places); pinned as a second example, fails 4/4 on the old code.
