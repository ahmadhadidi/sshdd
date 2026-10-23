# 🌊 SSHDD

Interactive TUI for SSH keys: generate, deploy, test, rotate, and keep `~/.ssh/config` in sync.

---

## Linux (Bash)

### Run from the cloud

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/ahmadhadidi/sshdd/refs/heads/main/sshdd.sh) \
  --user myuser \
  --subnet 192.168.0 \
  --comment-suffix "-[my-machine]"
```

### Run locally

```bash
git clone https://github.com/ahmadhadidi/sshdd.git ~/sshdd
bash ~/sshdd/sshdd.sh \
  --user myuser \
  --subnet 192.168.0 \
  --comment-suffix "-[my-machine]"
```

### Alias

One line adds an `sshdd` alias to your shell's rc file:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/ahmadhadidi/sshdd/refs/heads/main/setup/alias.sh)
```

It asks for the values you don't pass (Enter keeps the default). Pass the ones you already know:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/ahmadhadidi/sshdd/refs/heads/main/setup/alias.sh) \
  --user myuser --subnet 192.168.0 --comment-suffix "-[my-machine]"
```

✏️ The values:
- `--user`: default remote username
- `--subnet`: subnet prefix (`10` → `192.168.0.10`)
- `--comment-suffix`: appended to key comments
- `--password`: optional. Better left to the hidden question: a flag stays in your shell history. Either way it's
  stored in plain text in the rc file; left empty, sshdd asks when it needs one.

What it does ([`setup/alias.sh`](setup/alias.sh), read it before running):
- **rc file by login shell:** zsh → `~/.zshrc`; bash → `~/.bashrc`, on macOS `~/.bash_profile` (Terminal starts
  login shells, which don't read `~/.bashrc`).
- **Local if cloned, else cloud:** with `~/sshdd/sshdd.sh` the alias runs your clone (update with
  `git -C ~/sshdd pull`); otherwise each run fetches `main`.
- **Safe to run again:** it replaces its own `# >>> sshdd >>>` block; the old file is kept as `<rc>.sshdd-bak`.

Then run `sshdd`. Options passed to it win for that run, e.g. `sshdd --user root` or `sshdd --verbose`.

### Options

| Option | Default | Description |
|---|---|---|
| `--user NAME` | `default_non_root_username` | Default remote username |
| `--subnet PREFIX` | `192.168.0` | Subnet prefix (`10` → `192.168.0.10`) |
| `--comment-suffix STR` | `-[my-machine]` | Appended to key comments |
| `--password PASS` | *(empty)* | Default SSH password (needs `sshpass`) |
| `--verbose` | off | Debug log to `/tmp/sshdd-debug.log` |

---

## Windows (PowerShell)

### Run from the cloud

```powershell
& ([scriptblock]::Create((irm "https://raw.githubusercontent.com/ahmadhadidi/sshdd/refs/heads/main/sshdd.ps1"))) `
  -DefaultUserName myuser `
  -DefaultSubnetPrefix 192.168.0 `
  -DefaultCommentSuffix "-[my-machine]"
```

### Run locally

```powershell
git clone https://github.com/ahmadhadidi/sshdd.git $HOME\sshdd
& $HOME\sshdd\sshdd.ps1 `
  -DefaultUserName myuser `
  -DefaultSubnetPrefix 192.168.0 `
  -DefaultCommentSuffix "-[my-machine]"
```

### Alias

One line adds a `sshdd` function to your PowerShell profile:

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/ahmadhadidi/sshdd/refs/heads/main/setup/alias.ps1)))
```

It asks for the values you don't pass (Enter keeps the default; the password is hidden). Pass the ones you already know:

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/ahmadhadidi/sshdd/refs/heads/main/setup/alias.ps1))) `
  -User myuser -Subnet 192.168.0 -CommentSuffix "-[my-machine]"
```

✏️ `-User`, `-Subnet`, `-CommentSuffix`, `-Password`: same values as bash. Same rules: local if
`$HOME\sshdd\sshdd.ps1` exists, else cloud; a rerun replaces its block (backup: `$PROFILE.sshdd-bak`); a password is
stored in plain text. Script: [`setup/alias.ps1`](setup/alias.ps1). Windows only runs a profile when the execution
policy allows it: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

Then run `sshdd`.

### Options

| Option | Default | Description |
|---|---|---|
| `-DefaultUserName` | `default_non_root_username` | Default remote username |
| `-DefaultSubnetPrefix` | `192.168.0` | Subnet prefix |
| `-DefaultCommentSuffix` | `-[my-machine]` | Appended to key comments |
| `-DefaultPassword` | *(empty)* | Default SSH password |

## Backups

- `backup/2026-10-17-1959-boilerplate-adoption` — before adopting claude-init (2026-10-17 19:59).
