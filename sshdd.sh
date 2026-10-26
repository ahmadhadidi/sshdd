#!/usr/bin/env bash
# sshdd.sh — SSH Key Manager TUI
#
# Usage:
#   bash sshdd.sh [OPTIONS]
#   bash <(curl -fsSL https://raw.githubusercontent.com/ahmadhadidi/sshdd/refs/heads/main/sshdd.sh) [OPTIONS]
#
# Options:
#   --user NAME           Default remote username        (default: default_non_root_username)
#   --subnet PREFIX       Default subnet prefix          (default: 192.168.0)
#   --comment-suffix STR  Default key comment suffix     (default: -[my-machine])
#   --password PASS       Default SSH password for sshpass
#   --verbose             Log debug info to /tmp/sshdd-debug.log

# No `set -u`: bash 3.2 (macOS) treats an empty array as unset, so every "${arr[@]}" on an empty
# list (e.g. "keep it on remote hosts" in Delete Local Key) killed sshdd mid-operation.
set -o pipefail
export LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8


# ─── Defaults (overridable via CLI) ──────────────────────────────────────────
DEFAULT_USER="default_non_root_username"
DEFAULT_SUBNET_PREFIX="192.168.0"
DEFAULT_COMMENT_SUFFIX="-[my-machine]"
DEFAULT_PASSWORD=""
VERBOSE=0
SSHDD_MOUSE=1   # click and wheel in sshdd's screens (#41); --no-mouse switches it off

while [[ $# -gt 0 ]]; do
    case "$1" in
        --user)            DEFAULT_USER="$2";            shift 2 ;;
        --subnet)          DEFAULT_SUBNET_PREFIX="$2";   shift 2 ;;
        --comment-suffix)  DEFAULT_COMMENT_SUFFIX="$2";  shift 2 ;;
        --password)        DEFAULT_PASSWORD="$2";         shift 2 ;;
        --verbose)         VERBOSE=1;                     shift   ;;
        --no-mouse)        SSHDD_MOUSE=0;                 shift   ;;   # #41: no click/wheel capture
        *) shift ;;
    esac
done

# ─── Constants ────────────────────────────────────────────────────────────────
SSH_DIR="$HOME/.ssh"
SSH_CONFIG="$HOME/.ssh/config"
P="  "

# ─── Script-scope globals ────────────────────────────────────────────────────
_LAST_SELECTED_ALIAS=""
KEY=""
_SELECT_RESULT=""
_SELECT_CANCELLED=0
_LOG_FILE="/tmp/sshdd-debug.log"
_STTY_SAVED=""   # global so _menu_cleanup can always access it
_HOST_BLOCK=""   # set by _get_host_block
_CONFIG_MISSING=0  # set to 1 when ~/.ssh/config does not exist

# ─── Library loader ──────────────────────────────────────────────────────────
_BASE_URL="https://raw.githubusercontent.com/ahmadhadidi/sshdd/refs/heads/main"

# Determine script directory (empty when run via bash <(curl ...))
_SCRIPT_DIR=""
if [[ -n "${BASH_SOURCE[0]:-}" ]]; then
    _candidate="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || true)"
    # Only use local path if the lib/bash directory actually exists there
    [[ -d "${_candidate}/lib/bash" ]] && _SCRIPT_DIR="$_candidate"
fi

_source_lib() {
    local name="$1"
    local local_path="${_SCRIPT_DIR}/lib/bash/${name}.sh"
    if [[ -n "$_SCRIPT_DIR" && -f "$local_path" ]]; then
        # shellcheck source=/dev/null
        source "$local_path"
    else
        # Use a temp file to avoid nested process substitution FD conflicts
        # (nested source <(curl ...) inside bash <(curl ...) fails on macOS)
        local tmp
        tmp="$(mktemp /tmp/sshdd-XXXXXX.sh 2>/dev/null \
               || mktemp 2>/dev/null \
               || printf '/tmp/sshdd-%s-%s.sh' "$$" "$name")"
        if curl -fsSL "${_BASE_URL}/lib/bash/${name}.sh" -o "$tmp" 2>/dev/null \
           && [[ -s "$tmp" ]]; then
            # shellcheck source=/dev/null
            source "$tmp"
            rm -f "$tmp"
        else
            rm -f "$tmp"
            printf '\e[31mError: could not download lib/bash/%s.sh from:\e[0m\n  %s\n' \
                "$name" "$_BASE_URL" >&2
            printf 'Check network connectivity or run from a local clone.\n' >&2
            exit 1
        fi
    fi
}

for _lib in tui ssh-config ssh-helpers prompts ssh-ops config-display menu menu-support menu-renderer; do
    _source_lib "$_lib"
done
unset _lib _source_lib _candidate _SCRIPT_DIR _BASE_URL

# ─── Entry point ─────────────────────────────────────────────────────────────
if (( VERBOSE )); then
    : > "$_LOG_FILE"
    printf '\e[33mVerbose mode: logging to %s\e[0m\n' "$_LOG_FILE"
    printf '\e[90mIn another terminal run:  tail -f %s\e[0m\n' "$_LOG_FILE"
    printf '\e[90mPress any key to start.\e[0m'
    IFS= read -r -s -n1 _ 2>/dev/null || true
fi

show_main_menu
