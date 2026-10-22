# Progress

## Remaining work

- #20 (in Review): a typed new host name asks for its address. Not run live on CT 213; tested with stubs and the bash TUI.
- #15 known_hosts (in Review): Windows is unverified. `Resolve-HostKeyName` assumes that `ssh -G` on Windows prints
  `userknownhostsfile` as a path (a leading `~` is expanded). Tested only with pwsh 7.6 on Linux.
- The remote list (O) can name hashed entries only for hosts in the local `~/.ssh/config`; others show `(hashed)`.
- #14 All users (in Review): only `~/.ssh/authorized_keys` of each `getent passwd` user (no `authorized_keys2`, no
  `AuthorizedKeysFile` from sshd_config); root path tested with fakes, not on a real root login.
- #19 (Inbox): keys kept only in 1Password (no private files in ~/.ssh) aren't supported. Test Connection
  uses -F /dev/null, and list/install/delete expect private key files. The design needs Ahmad's agreement first.
