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

Paste this into your terminal (bash or zsh). Edit `user`, `subnet` and `suffix` first.

```bash
(
  set -e

  user=myuser
  subnet=192.168.0
  suffix='-[my-machine]'

  case "$SHELL" in
    */zsh) rc="${ZDOTDIR:-$HOME}/.zshrc" ;;
    *)     [ "$(uname)" = Darwin ] && rc="$HOME/.bash_profile" || rc="$HOME/.bashrc" ;;
  esac

  if [ -f "$HOME/sshdd/sshdd.sh" ]; then
    kind=local
    run='bash ~/sshdd/sshdd.sh'
  else
    kind=cloud
    run='bash <(curl -fsSL https://raw.githubusercontent.com/ahmadhadidi/sshdd/refs/heads/main/sshdd.sh)'
  fi

  touch "$rc"
  cp "$rc" "$rc.sshdd-bak"
  {
    awk '/^# >>> sshdd >>>/ {s=1} !s {print} /^# <<< sshdd <<</ {s=0}' "$rc.sshdd-bak"
    echo '# >>> sshdd >>>'
    echo "alias sshdd='$run --user $user --subnet $subnet --comment-suffix \"$suffix\"'"
    echo '# <<< sshdd <<<'
  } >| "$rc.sshdd-tmp"
  cat "$rc.sshdd-tmp" >| "$rc"
  rm -f "$rc.sshdd-tmp"

  echo "sshdd alias ($kind) written to $rc"
  echo "Backup: $rc.sshdd-bak. Open a new terminal."
)
```

- **rc file by login shell, not by OS:** zsh → `~/.zshrc` (or `$ZDOTDIR`); bash → `~/.bashrc`, but on macOS
  `~/.bash_profile`, because Terminal starts login shells and those don't read `~/.bashrc`.
- **Local if cloned, else cloud:** `~/sshdd/sshdd.sh` present → local alias (runs the code you cloned; update with
  `git -C ~/sshdd pull`). Otherwise cloud: every run fetches whatever is on `main` now.
- **Safe to run again:** the alias sits between `# >>> sshdd >>>` and `# <<< sshdd <<<`; a rerun replaces that block
  instead of adding a second one. The old file is kept as `<rc>.sshdd-bak`, and a symlinked rc (dotfile manager)
  stays a symlink.
- **No password in the alias:** an rc file is plain text. Leave `--password` out; sshdd asks when it needs one.
- The values go inside single quotes, so they can't contain `'`.
- Read pasted code before running it, this block included.

Then run `sshdd` (extra options still pass through, e.g. `sshdd --verbose`).

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

Paste this into PowerShell. Edit `user`, `subnet` and `suffix` first.

```powershell
& {
  $ErrorActionPreference = 'Stop'

  $user   = 'myuser'
  $subnet = '192.168.0'
  $suffix = '-[my-machine]'

  $local = Join-Path (Join-Path $HOME 'sshdd') 'sshdd.ps1'
  if (Test-Path $local) {
    $kind = 'local'
    $run  = "& '$local'"
  } else {
    $kind = 'cloud'
    $run  = '& ([scriptblock]::Create((irm "https://raw.githubusercontent.com/ahmadhadidi/sshdd/refs/heads/main/sshdd.ps1")))'
  }

  New-Item -ItemType Directory -Force -Path (Split-Path $PROFILE) | Out-Null
  $old = ''
  if (Test-Path $PROFILE) {
    $old = [string](Get-Content -Raw $PROFILE)
    Copy-Item $PROFILE "$PROFILE.sshdd-bak"
  }
  $old = [regex]::Replace($old, '(?s)# >>> sshdd >>>.*?# <<< sshdd <<<\r?\n?', '')
  $block = @(
    '# >>> sshdd >>>'
    "function sshdd { $run -DefaultUserName '$user' -DefaultSubnetPrefix '$subnet' -DefaultCommentSuffix '$suffix' @args }"
    '# <<< sshdd <<<'
  ) -join "`n"
  Set-Content -Path $PROFILE -Value ($old + $block + "`n") -NoNewline

  "sshdd function ($kind) written to $PROFILE"
  "Backup: $PROFILE.sshdd-bak. Open a new PowerShell window."
}
```

Same rules as bash: local if `$HOME\sshdd\sshdd.ps1` exists, else cloud; a rerun replaces the marked block (backup:
`$PROFILE.sshdd-bak`); no password in the profile; values can't contain `'`. Windows only runs a profile when the
execution policy allows it: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

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
