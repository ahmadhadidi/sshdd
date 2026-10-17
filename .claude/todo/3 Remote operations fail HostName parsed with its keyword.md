---
number: 3
title: 'Remote operations fail: HostName parsed with its keyword'
status: Review
category: ssh-ops
creator: Ahmad
created: 2026-10-17 20:15
kind: todo
latest: '10-17: Bash: _block_field rewritten in awk (no sed s///i, which BSD sed may reject; unconfirmed on macOS), all ssh-config parsers accept any keyword case,…'
description: '`ssh dev-poc` works from the terminal, but Test SSH Connection reports ''Connection refused: HostName 192.168.0.204 is not accepting SSH on port 22''. Delete SSH Key From A Remote Machine shows ''Fetching authorized keys from kraid@ HostName 192.168.0.204'' and ''Could not connect''. The host value keeps the ''HostName'' keyword and indentation. Likely the same function is used by Install SSH Key, Delete SSH Key and List Authorized Keys. Imported from todo2.md on 2026-10-17; not re-checked whether still open.'
---
## Updates
- **Started 2026-10-17.**
- **Ready for review 2026-10-17.** Bash: _block_field rewritten in awk (no sed s///i, which BSD sed may reject; unconfirmed on macOS), all ssh-config parsers accept any keyword case, tabs and Key=value; get_identity_files_for_host by IP now captures the whole block (IdentityFile lines after HostName were dropped). resolve_ssh_target prefers the picked alias when several blocks share an IP. PS parity: same regexes, Resolve-SSHTarget prefers $script:_RemoteAlias. New tests/test_ssh_config_parse.py (bash + pwsh), fails on old code. Please confirm on the Mac.
