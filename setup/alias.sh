#!/usr/bin/env bash
# sshdd alias setup for macOS and Linux (TODO #29). Writes `alias sshdd=…` into your shell's rc file.
#
#   bash <(curl -fsSL https://raw.githubusercontent.com/ahmadhadidi/sshdd/refs/heads/main/setup/alias.sh) \
#     [--user NAME] [--subnet PREFIX] [--comment-suffix STR] [--password PASS]
#
# Values not passed are asked for (Enter keeps the [default]); without a terminal the defaults are used.
# rc file by login shell: zsh → ~/.zshrc ($ZDOTDIR), bash → ~/.bashrc, on macOS ~/.bash_profile.
# Local alias if ~/sshdd/sshdd.sh exists, else the cloud one. A rerun replaces the marked block;
# the old file is kept as <rc>.sshdd-bak.
set -e

user='' subnet='' suffix='' password='' got_user=0 got_subnet=0 got_suffix=0 got_password=0

usage() {
  cat <<'EOF'
Usage: bash <(curl -fsSL https://raw.githubusercontent.com/ahmadhadidi/sshdd/refs/heads/main/setup/alias.sh) [options]
  --user NAME            default remote username       (asked if missing; default myuser)
  --subnet PREFIX        subnet prefix, 10 → PREFIX.10 (default 192.168.0)
  --comment-suffix STR   appended to key comments      (default -[my-machine])
  --password PASS        optional; stored in plain text in the rc file (better: the hidden prompt)
EOF
}

while [ $# -gt 0 ]; do
  case $1 in
    --user|--subnet|--comment-suffix|--password)
      [ $# -ge 2 ] || { echo "$1 needs a value" >&2; exit 2; } ;;
  esac
  case $1 in
    --user)           user=$2;     got_user=1;     shift 2 ;;
    --subnet)         subnet=$2;   got_subnet=1;   shift 2 ;;
    --comment-suffix) suffix=$2;   got_suffix=1;   shift 2 ;;
    --password)       password=$2; got_password=1; shift 2 ;;
    -h|--help)        usage; exit 0 ;;
    *)                echo "Unknown option: $1 (see --help)" >&2; exit 2 ;;
  esac
done

# Questions go to the terminal, so they work however the script is started.
tty=0
{ : </dev/tty; } 2>/dev/null && tty=1

ask() {   # ask VAR PROMPT DEFAULT
  local ans=''
  if (( tty )); then
    printf '%s [%s]: ' "$2" "$3" >/dev/tty
    IFS= read -r ans </dev/tty || ans=''
  fi
  printf -v "$1" '%s' "${ans:-$3}"
}

if (( tty )) && (( !got_user || !got_subnet || !got_suffix || !got_password )); then
  echo 'sshdd alias setup (Enter keeps the [default])' >/dev/tty
fi
(( got_user ))   || ask user   'Default remote username' myuser
(( got_subnet )) || ask subnet 'Subnet prefix'           192.168.0
(( got_suffix )) || ask suffix 'Key comment suffix'      '-[my-machine]'
if (( !got_password && tty )); then
  printf 'SSH password (hidden, Enter = ask each time): ' >/dev/tty
  IFS= read -rs password </dev/tty || password=''
  echo >/dev/tty
fi

# Single-quote a value for the shell: any character is safe, ' becomes '\''.
q() { printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"; }

case "${SHELL:-}" in
  */zsh) rc="${ZDOTDIR:-$HOME}/.zshrc" ;;
  *)     if [ "$(uname)" = Darwin ]; then rc="$HOME/.bash_profile"; else rc="$HOME/.bashrc"; fi ;;
esac

if [ -f "$HOME/sshdd/sshdd.sh" ]; then
  kind=local
  run='bash ~/sshdd/sshdd.sh'
else
  kind=cloud
  run='bash <(curl -fsSL https://raw.githubusercontent.com/ahmadhadidi/sshdd/refs/heads/main/sshdd.sh)'
fi

cmd="$run --user $(q "$user") --subnet $(q "$subnet") --comment-suffix $(q "$suffix")"
[ -n "$password" ] && cmd="$cmd --password $(q "$password")"

touch "$rc"
cp "$rc" "$rc.sshdd-bak"
{
  awk '/^# >>> sshdd >>>/ {s=1} !s {print} /^# <<< sshdd <<</ {s=0}' "$rc.sshdd-bak"
  echo '# >>> sshdd >>>'
  echo "alias sshdd=$(q "$cmd")"
  echo '# <<< sshdd <<<'
} >| "$rc.sshdd-tmp"
cat "$rc.sshdd-tmp" >| "$rc"      # through the file: a symlinked rc (dotfile manager) stays a symlink
rm -f "$rc.sshdd-tmp"

echo "sshdd alias ($kind) written to $rc (backup: $rc.sshdd-bak)"
[ -n "$password" ] && echo "Note: the password is stored in plain text in $rc."
cat <<'EOF'
Open a new terminal, then:
  sshdd               open the menu
  sshdd --user root   another user, this run only
  sshdd --verbose     debug log to /tmp/sshdd-debug.log
EOF
