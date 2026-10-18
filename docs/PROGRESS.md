# Progress

## Remaining work

- #15 known_hosts (in Review): Windows is unverified. `Resolve-HostKeyName` assumes that `ssh -G` on Windows prints
  `userknownhostsfile` as a path (a leading `~` is expanded). Tested only with pwsh 7.6 on Linux.
- The remote list (O) can name hashed entries only for hosts in the local `~/.ssh/config`; others show `(hashed)`.
