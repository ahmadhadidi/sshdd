---
number: 5
title: 'Conf: Global Defaults banner needs the boxed title'
status: Review
category: tui
creator: Ahmad
created: 2026-10-17 20:15
kind: todo
latest: '10-17: Bash: F5 ''Conf: Global Defaults'' now draws its title with _draw_op_header, the same teal box as other screens; fields and persist commands moved down…'
description: 'The banner at the top of Conf: Global Defaults should use the same box as other screens (e.g. the ''Delete SSH Key From A Remote Machine'' title box). Imported from todo2.md on 2026-10-17; not re-checked whether still open.'
---
## Updates
- **Started 2026-10-17.**
- **Ready for review 2026-10-17.** Bash: F5 'Conf: Global Defaults' now draws its title with _draw_op_header, the same teal box as other screens; fields and persist commands moved down to fit. Also fixed: editing a field showed a stray 'Input' label (read_colored_input turned an explicit empty prompt into 'Input'). PS: PS screens have no boxes; F5 now uses the same teal title bar as every other PS screen. Test: test_main_menu_look.py::test_conf_defaults_has_title_box. Screenshot: handoff/conf-defaults-100x30.png.
