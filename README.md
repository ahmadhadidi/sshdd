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

Add one to `~/.bashrc` (or `~/.zshrc`):

```bash
# cloud
alias sshdd='bash <(curl -fsSL https://raw.githubusercontent.com/ahmadhadidi/sshdd/refs/heads/main/sshdd.sh) \
  --user myuser \
  --subnet 192.168.0 \
  --comment-suffix "-[my-machine]"'

# local
alias sshdd='bash ~/sshdd/sshdd.sh \
  --user myuser \
  --subnet 192.168.0 \
  --comment-suffix "-[my-machine]"'
```

Then just run `sshdd` (extra options still pass through, e.g. `sshdd --verbose`).

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

Add one to your profile (`notepad $PROFILE`):

```powershell
# cloud
function sshdd {
  & ([scriptblock]::Create((irm "https://raw.githubusercontent.com/ahmadhadidi/sshdd/refs/heads/main/sshdd.ps1"))) `
    -DefaultUserName myuser `
    -DefaultSubnetPrefix 192.168.0 `
    -DefaultCommentSuffix "-[my-machine]" `
    @args
}

# local
function sshdd {
  & "$HOME\sshdd\sshdd.ps1" `
    -DefaultUserName myuser `
    -DefaultSubnetPrefix 192.168.0 `
    -DefaultCommentSuffix "-[my-machine]" `
    @args
}
```

Then just run `sshdd`.

### Options

| Option | Default | Description |
|---|---|---|
| `-DefaultUserName` | `default_non_root_username` | Default remote username |
| `-DefaultSubnetPrefix` | `192.168.0` | Subnet prefix |
| `-DefaultCommentSuffix` | `-[my-machine]` | Appended to key comments |
| `-DefaultPassword` | *(empty)* | Default SSH password |
