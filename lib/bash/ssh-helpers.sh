# lib/ssh-helpers.sh — SSH utility helpers shared across ssh-ops and menu
# Sourced by sshdd.sh — do not execute directly.
[[ -n "${_SSH_HELPERS_SH_LOADED:-}" ]] && return 0
_SSH_HELPERS_SH_LOADED=1
# EXPORTS: _out  _out_item  show_op_banner
#          _tcp_check  _spin_start  _spin_stop
#          _ssh_fence  _ssh_fence_close
#          _setup_askpass  _destroy_askpass  _ensure_ssh_dir
#          _write_key_pair  _print_identity_files  _prompt_remote

_SPIN_PID=''

# ─── Output helpers ───────────────────────────────────────────────────────────

# _out STYLE FORMAT [ARGS...]
# Prints a 2-space indented, color-coded line to stdout.
# Styles: ok (green)  warn (yellow)  error (red)  info (cyan)
#         dim (gray)  heading (bright-cyan)  plain (bright-white)
_out() {
    local style="$1" fmt="$2"; shift 2
    local code
    case "$style" in
        ok)      code=32 ;;
        warn)    code=33 ;;
        error)   code=31; _OP_ERROR=1 ;;   # _invoke_choice then always shows "Press any key"
        info)    code=36 ;;
        dim)     code=90 ;;
        heading) code=96 ;;
        plain)   code=97 ;;
        *)       code=37 ;;
    esac
    # shellcheck disable=SC2059
    printf "  \e[${code}m${fmt}\e[0m\n" "$@"
}

# _out_item FORMAT [ARGS...]
# Prints "  + FORMAT" with a green plus sign and plain unstyled text.
_out_item() {
    local fmt="$1"; shift
    # shellcheck disable=SC2059
    printf "  \e[32m+\e[0m  ${fmt}\n" "$@"
}

# show_op_banner KEY VAL [KEY VAL ...]
# Renders a styled context block between the op title rule and the first prompt.
# Style: #d97757 box (┌─┐/└─┘/│) with x-margins, faint-bg content+padding rows,
#        bold-uppercase keys, white values, "• KEY:  val" format.
#
# Stream mode (default): prints to stdout; used by menu item dispatches.
# Buffer mode: set _OP_BANNER_ROW to the starting row before calling.
#   Writes absolute-positioned ANSI into _OP_BANNER_BUF; caller appends to
#   its frame buffer. Used by self-contained TUI screens (inventory, config viewer).
#
# Always sets _OP_BANNER_ROWS (pair_count + 4) and _SFL_BANNER_ROWS.
show_op_banner() {
    local -a pairs=("$@")
    local max_klen=0 i
    for (( i=0; i<${#pairs[@]}; i+=2 )); do
        (( ${#pairs[$i]} > max_klen )) && max_klen=${#pairs[$i]}
    done

    _OP_BANNER_ROWS=5   # always: top + pad + content (all KVPs horizontal) + pad + bottom
    _SFL_BANNER_ROWS=8
    _OP_BANNER_BUF=''

    _term_size
    local _mx=2                              # x-margin (spaces each side)
    local _ow=$(( TERM_W - _mx * 2 ))        # outer box width (corners included)
    (( _ow < 10 )) && _ow=10
    local _iw=$(( _ow - 2 ))                 # inner width (between │ chars)

    # Box-drawing chars (light set — all connect with ─)
    local _TL=$'\xe2\x94\x8c'  # ┌
    local _TR=$'\xe2\x94\x90'  # ┐
    local _BL=$'\xe2\x94\x94'  # └
    local _BR=$'\xe2\x94\x98'  # ┘
    local _VB=$'\xe2\x94\x82'  # │
    local _BUL=$'\xe2\x80\xa2' # •

    # Styles
    local _OC=$'\e[38;2;217;119;87m'  # #d97757 orange fg (border)
    local _FB=$'\e[48;2;48;26;19m'    # faint dark bg (content + padding)
    local _FW=$'\e[37m'               # normal white fg (values — dimmer than bold keys)
    local _BLD=$'\e[1m'               # bold on (keys)
    local _NBD=$'\e[22m'              # bold off
    local _RS=$'\e[0m'
    local _MX; printf -v _MX '%*s' "$_mx" ''

    # Horizontal rule: _ow-2 connected ─ chars (fits between corners)
    local _hrule=''
    printf -v _hrule '%*s' $(( _ow - 2 )) ''
    _hrule="${_hrule// /─}"

    # Inner blank: _iw spaces (fills faint-bg padding rows between │ chars)
    local _ipad; printf -v _ipad '%*s' "$_iw" ''

    # Build horizontal content line — all KVPs side by side on one row.
    # Each KVP:  "• KEY:  val"  separated by 4 spaces between pairs.
    local _content_disp=2  # leading "  " indent (display width counter)
    local _content_raw="  "
    for (( i=0; i<${#pairs[@]}; i+=2 )); do
        local _val="${pairs[$i+1]}"
        local _key_up; printf -v _key_up '%-*s' $(( max_klen + 1 )) "$(tr 'a-z' 'A-Z' <<< "${pairs[$i]}"):"
        if (( i > 0 )); then
            _content_raw+="    "           # 4-char separator between KVPs
            (( _content_disp += 4 ))
        fi
        _content_raw+="${_BUL} ${_BLD}${_key_up}${_NBD}  ${_val}"
        # display width per KVP: "• "(2) + padded_key(max_klen+1) + "  "(2) + val
        (( _content_disp += 2 + (max_klen + 1) + 2 + ${#_val} ))
    done
    local _pad_n=$(( _iw - _content_disp ))
    (( _pad_n < 0 )) && _pad_n=0
    local _pad; printf -v _pad '%*s' "$_pad_n" ''
    _content_raw+="$_pad"

    # Compose reusable row strings
    local _top="${_MX}${_OC}${_TL}${_hrule}${_TR}${_RS}"
    local _bot="${_MX}${_OC}${_BL}${_hrule}${_BR}${_RS}"
    local _prow="${_MX}${_OC}${_VB}${_RS}${_FB}${_ipad}${_RS}${_OC}${_VB}${_RS}"
    local _crow="${_MX}${_OC}${_VB}${_RS}${_FB}${_FW}${_content_raw}${_RS}${_OC}${_VB}${_RS}"

    if [[ -n ${_OP_BANNER_ROW:-} ]]; then
        local _t _r="$_OP_BANNER_ROW"
        printf -v _t '\e[%d;1H%s\e[K' "$_r" "$_top";  _OP_BANNER_BUF+="$_t"; (( _r++ ))
        printf -v _t '\e[%d;1H%s\e[K' "$_r" "$_prow"; _OP_BANNER_BUF+="$_t"; (( _r++ ))
        printf -v _t '\e[%d;1H%s\e[K' "$_r" "$_crow"; _OP_BANNER_BUF+="$_t"; (( _r++ ))
        printf -v _t '\e[%d;1H%s\e[K' "$_r" "$_prow"; _OP_BANNER_BUF+="$_t"; (( _r++ ))
        printf -v _t '\e[%d;1H%s\e[K' "$_r" "$_bot";  _OP_BANNER_BUF+="$_t"
    else
        printf '%s\n' "$_top"
        printf '%s\n' "$_prow"
        printf '%s\n' "$_crow"
        printf '%s\n' "$_prow"
        printf '%s\n' "$_bot"
    fi
}

# Draw the teal operation title box at the top of the screen.
# Uses _visual_width for correct centering of emoji labels.
#
# Stream mode (default, _OP_HDR_ROW unset):
#   Clears the screen, prints the 5-row box (rows 2-6) + blank (row 7), leaves
#   cursor on row 8 ready for operation output. Also shows the cursor (\e[?25h).
# Buffer mode (_OP_HDR_ROW set to any value):
#   Writes absolute-positioned ANSI into _OP_HDR_BUF using rows 2-7.
#   Caller appends _OP_HDR_BUF to its frame buffer after \e[2J\e[H.
#
# Always sets _OP_HDR_HEIGHT=7 (rows 2-6 = box, row 7 = blank).
_draw_op_header() {
    local label="$1"
    _term_size
    local box_w=$(( TERM_W - 4 > 0 ? TERM_W - 4 : 10 ))
    local inner_w=$(( box_w - 2 ))
    local _TL=$'\xe2\x94\x8c' _TR=$'\xe2\x94\x90' _BL=$'\xe2\x94\x94' _BR=$'\xe2\x94\x98' _VB=$'\xe2\x94\x82'
    local h_rule inner_pad
    printf -v h_rule   '%*s' "$inner_w" ''; h_rule="${h_rule// /─}"
    printf -v inner_pad '%*s' "$inner_w" ''
    local lbl_len; lbl_len=$(_visual_width "$label")
    local lpad=$(( (inner_w - lbl_len) / 2 )); (( lpad < 0 )) && lpad=0
    local rpad=$(( inner_w - lbl_len - lpad )); (( rpad < 0 )) && rpad=0
    local lspc rspc
    printf -v lspc '%*s' "$lpad" ''
    printf -v rspc '%*s' "$rpad" ''
    _OP_HDR_HEIGHT=7
    _OP_HDR_BUF=''
    if [[ -z ${_OP_HDR_ROW+x} ]]; then
        # Stream mode: clear screen, show cursor, print box directly.
        printf '\e[2J\e[H\e[?25h\n'
        printf '  \e[96m%s%s%s\e[0m\n'                                     "$_TL" "$h_rule" "$_TR"
        printf '  \e[96m%s\e[0m\e[48;5;23m%s\e[0m\e[96m%s\e[0m\n'         "$_VB" "$inner_pad" "$_VB"
        printf '  \e[96m%s\e[0m\e[48;5;23m\e[1;97m%s%s%s\e[0m\e[96m%s\e[0m\n' "$_VB" "$lspc" "$label" "$rspc" "$_VB"
        printf '  \e[96m%s\e[0m\e[48;5;23m%s\e[0m\e[96m%s\e[0m\n'         "$_VB" "$inner_pad" "$_VB"
        printf '  \e[96m%s%s%s\e[0m\n\n'                                   "$_BL" "$h_rule" "$_BR"
    else
        # Buffer mode: write absolute-positioned ANSI into _OP_HDR_BUF (rows 2-7).
        local _t
        printf -v _t '\e[2;1H  \e[96m%s%s%s\e[0m\e[K'                                         "$_TL" "$h_rule" "$_TR";            _OP_HDR_BUF+="$_t"
        printf -v _t '\e[3;1H  \e[96m%s\e[0m\e[48;5;23m%s\e[0m\e[96m%s\e[0m\e[K'             "$_VB" "$inner_pad" "$_VB";          _OP_HDR_BUF+="$_t"
        printf -v _t '\e[4;1H  \e[96m%s\e[0m\e[48;5;23m\e[1;97m%s%s%s\e[0m\e[96m%s\e[0m\e[K' "$_VB" "$lspc" "$label" "$rspc" "$_VB"; _OP_HDR_BUF+="$_t"
        printf -v _t '\e[5;1H  \e[96m%s\e[0m\e[48;5;23m%s\e[0m\e[96m%s\e[0m\e[K'             "$_VB" "$inner_pad" "$_VB";          _OP_HDR_BUF+="$_t"
        printf -v _t '\e[6;1H  \e[96m%s%s%s\e[0m\e[K'                                         "$_BL" "$h_rule" "$_BR";             _OP_HDR_BUF+="$_t"
        printf -v _t '\e[7;1H\e[K';                                                                                                  _OP_HDR_BUF+="$_t"
    fi
}

# ─── Connection helpers ───────────────────────────────────────────────────────

# TCP port-22 pre-check. Returns 0 if reachable.
_tcp_check() {
    local host="$1" secs="${2:-3}"
    # Host as an argument, never inside the -c string (a crafted HostName ran as code).
    _with_timeout "$secs" bash -c 'echo >"/dev/tcp/$1/22"' _ "$host" 2>/dev/null
}

# Run CMD..., killed after SECS. Plain bash: macOS has no `timeout` (GNU coreutils), which made
# every host look unreachable and every Test Connection say "refused" on a stock Mac (plan E5).
_with_timeout() {
    local secs="$1" pid watcher rc
    shift
    "$@" &
    pid=$!
    ( sleep "$secs"; kill -9 "$pid" 2>/dev/null ) &
    watcher=$!
    wait "$pid"; rc=$?
    kill "$watcher" 2>/dev/null; wait "$watcher" 2>/dev/null
    return "$rc"
}

# Every ssh/scp sshdd runs gives up connecting after 10 s: without it an unreachable host hung each
# operation for the system TCP timeout (~2 min on Linux) with no message (plan E5).
ssh() { command ssh -o ConnectTimeout=10 "$@"; }
scp() { command scp -o ConnectTimeout=10 "$@"; }

# Animated spinner at the terminal's last row while a blocking operation runs.
# Usage: _spin_start "message"; <blocking command>; _spin_stop
_spin_start() {
    local _sm="$1"
    _SPIN_PID=''
    {
        local -a _sf=('|' '/' '-' "\\")
        local _si=0
        while true; do
            printf '\e7\e[999;1H\e[2K  \e[36m%s\e[0m  %s\e8' "${_sf[$_si]}" "$_sm" >/dev/tty
            _si=$(( (_si + 1) % 4 ))
            sleep 0.12
        done
    } &
    _SPIN_PID=$!
}

_spin_stop() {
    if [[ -n ${_SPIN_PID:-} ]]; then
        # CONT after TERM: Ctrl+Z stops the whole process group, and a stopped job never
        # acts on TERM, so the wait would hang (TODO #10).
        kill "$_SPIN_PID" 2>/dev/null || true
        kill -CONT "$_SPIN_PID" 2>/dev/null || true
        wait "$_SPIN_PID" 2>/dev/null || true
        _SPIN_PID=''
    fi
    printf '\e7\e[999;1H\e[2K\e8' >/dev/tty 2>/dev/null || true
}

# Opening fence rule: "── SSH Session user@host ──"
_ssh_fence() {
    local target="${1:-}"
    _term_size
    local inner_w=$(( TERM_W - 4 > 0 ? TERM_W - 4 : 10 ))
    local label=""
    [[ -n $target ]] && label=" ⏩ SSH Session ${target} "
    if [[ -n $label ]]; then
        local llen=${#label}
        local dtotal=$(( inner_w - llen ))
        (( dtotal < 4 )) && dtotal=4
        local lw=$(( dtotal / 2 )) rw=$(( dtotal - dtotal / 2 ))
        printf '  \e[2m%s\e[0m\e[90m%s\e[0m\e[2m%s\e[0m\n' \
            "$(_repeat '─' "$lw")" "$label" "$(_repeat '─' "$rw")"
    else
        printf '  \e[2m%s\e[0m\n' "$(_repeat '─' "$inner_w")"
    fi
}

# Closing fence rule: "── SSH session closed ──"
_ssh_fence_close() {
    _term_size
    local inner_w=$(( TERM_W - 4 > 0 ? TERM_W - 4 : 10 ))
    local label=" SSH session closed "
    local llen=${#label}
    local dtotal=$(( inner_w - llen ))
    (( dtotal < 4 )) && dtotal=4
    local lw=$(( dtotal / 2 )) rw=$(( dtotal - dtotal / 2 ))
    printf '  \e[2m%s\e[0m\e[90m%s\e[0m\e[2m%s\e[0m\n' \
        "$(_repeat '─' "$lw")" "$label" "$(_repeat '─' "$rw")"
}

# Temp files removed by _menu_cleanup however sshdd ends (Q, Ctrl+C/Z, kill, closed terminal). TODO #10.
_CLEANUP_PATHS=()
_cleanup_add() { _CLEANUP_PATHS+=("$@"); }

# _mktemp_reg VAR PREFIX — create an empty temp file /tmp/PREFIX-…, registered for cleanup BEFORE it
# exists. With VAR=$(mktemp) a signal during the subshell created the file but lost its name, so
# exit cleanup could never remove it (plan T1). Exclusive create via noclobber; 600 by umask.
_mktemp_reg() {
    local _p _i
    for (( _i = 0; _i < 20; _i++ )); do
        _p="/tmp/$2-$$-$RANDOM$RANDOM"
        _cleanup_add "$_p"
        if ( umask 077; set -C; : > "$_p" ) 2>/dev/null; then
            printf -v "$1" '%s' "$_p"
            return 0
        fi
    done
    return 1
}

# Create a temporary SSH_ASKPASS helper so password/passphrase prompts are
# displayed with 2-space padding. Requires OpenSSH 8.4+ (SSH_ASKPASS_REQUIRE=force).
# Call _destroy_askpass when the SSH operation completes.
_setup_askpass() {
    _mktemp_reg _ASKPASS_TMP .ssh-askpass || return 0
    chmod 700 "$_ASKPASS_TMP"
    cat > "$_ASKPASS_TMP" << 'ASKPASS_SCRIPT'
#!/bin/bash
printf '  \e[36m%s\e[0m' "$1" >/dev/tty
stty -echo </dev/tty 2>/dev/null
IFS= read -r _pw </dev/tty
stty echo </dev/tty 2>/dev/null
printf '\n' >/dev/tty
printf '%s\n' "$_pw"
ASKPASS_SCRIPT
    export SSH_ASKPASS="$_ASKPASS_TMP"
    export SSH_ASKPASS_REQUIRE=force
}

_destroy_askpass() {
    rm -f "${_ASKPASS_TMP:-}"
    unset SSH_ASKPASS SSH_ASKPASS_REQUIRE _ASKPASS_TMP
}

# Remove one public-key line from the remote user's authorized_keys.
# The key travels on stdin, never inside the command string: a comment containing ' would
# otherwise end the quoting and run on the remote (plan Z1). The file is rewritten in place
# (cat >, not mv from a temp file) so its mode and owner stay what sshd's StrictModes needs (Z3).
_remote_remove_pubkey() {
    local target="$1" pubkey="$2"
    printf '%s\n' "${pubkey%$'\n'}" | ssh "$target" \
        't=$(mktemp) && k=$(mktemp) && cat > "$k" && awk '\''NR==FNR { keys[$0]; next } !($0 in keys)'\'' "$k" ~/.ssh/authorized_keys > "$t" && cat "$t" > ~/.ssh/authorized_keys; rc=$?; rm -f "$t" "$k"; exit $rc'
}

# A key name must be a plain file name inside ~/.ssh: letters, digits, . _ @ + -, no "/", no "..",
# not starting with "." or "-" (plan Z1: "../../.bashrc" made ssh-keygen write outside ~/.ssh).
_valid_key_name() {
    [[ $1 =~ ^[A-Za-z0-9_][A-Za-z0-9._@+-]*$ && $1 != *..* ]]
}

# Remote side of "install a public key" (key on stdin). Appends only if that exact line isn't there
# (plan R7: installing twice duplicated it), adds a missing final newline first (else the key is glued
# onto the last one), and creates ~/.ssh 700 / authorized_keys 600 when they don't exist. Prints hostname.
_REMOTE_INSTALL_CMD='umask 077; mkdir -p .ssh && touch .ssh/authorized_keys && k=$(tr -d '\''\r'\'') && { [ ! -s .ssh/authorized_keys ] || [ -z "$(tail -c1 .ssh/authorized_keys)" ] || echo >> .ssh/authorized_keys; } && { grep -qxF "$k" .ssh/authorized_keys || printf '\''%s\n'\'' "$k" >> .ssh/authorized_keys; } && hostname'

# Print why an ssh call failed, from its captured output, so "Failed …" says what to fix
# (host key changed, wrong password, unreachable…). It used to be swallowed (plan E5).
_ssh_why() {
    local line
    line=$(printf '%s\n' "$1" | grep -m1 -iE 'host key verification failed|identification has changed|permission denied|could not resolve|connection refused|timed out|no route to host|network is unreachable|too many authentication failures')
    [[ -z $line ]] && line=$(printf '%s\n' "$1" | grep -v '^[[:space:]]*$' | tail -n 1)
    [[ -n $line ]] && _out dim 'ssh: %s' "${line%$'\r'}"
    return 0
}

# ─── Local filesystem helpers ─────────────────────────────────────────────────

# Ensure ~/.ssh exists with correct permissions.
_ensure_ssh_dir() {
    mkdir -p "$SSH_DIR"
    chmod 700 "$SSH_DIR"
}

# Write a key pair to ~/.ssh and set permissions.
# Prompts for overwrite confirmation if the private key already exists.
# Args: dest_priv dest_pub priv_data pub_data [copy_mode]
#   copy_mode=1 → cp priv_data/pub_data as file paths
#   copy_mode=0 → write priv_data/pub_data as literal strings (default)
# Returns 1 if aborted.
_write_key_pair() {
    local dest_priv="$1" dest_pub="$2" priv_data="$3" pub_data="$4" copy="${5:-0}"
    # Only plain names directly in ~/.ssh (import names come from user text or a remote path).
    if [[ ${dest_priv%/*} != "${SSH_DIR%/}" || $dest_pub != "$dest_priv.pub" ]] || ! _valid_key_name "${dest_priv##*/}"; then
        _out error "Invalid key name '%s': use letters, digits and . _ @ + - only (no / or ..)." "${dest_priv#"$SSH_DIR"/}"
        return 1
    fi
    if [[ -f $dest_priv ]]; then
        local overwrite
        overwrite=$(read_colored_input "  '$(basename "$dest_priv")' already exists. Overwrite? [y/N]" yellow)
        [[ ! "$overwrite" =~ ^[yY] ]] && _out warn 'Aborted.' && return 1
    fi
    if (( copy )); then
        cp "$priv_data" "$dest_priv" && chmod 600 "$dest_priv"
        cp "$pub_data"  "$dest_pub"  && chmod 644 "$dest_pub"
    else
        printf '%s' "$priv_data" > "$dest_priv" && chmod 600 "$dest_priv"
        # Strip every trailing newline (a pasted key often has several), then add exactly one.
        local _nl=$'\n'
        pub_data="${pub_data%"${pub_data##*[!$_nl]}"}"
        printf '%s\n' "$pub_data" > "$dest_pub" && chmod 644 "$dest_pub"
    fi
    _out_item '%s  imported.' "$dest_priv"
    _out_item '%s  imported.' "$dest_pub"
}

# ─── Prompt helpers ───────────────────────────────────────────────────────────

# Print the IdentityFile entries configured for a host (informational only).
_print_identity_files() {
    local id_lookup="$1"
    local k
    while IFS= read -r k; do
        _out dim 'Using key: %s' "$k"
    done < <(get_identity_files_for_host "$id_lookup")
}

# Prompt for a remote host and user in one call.
# Sets globals: _REMOTE_HOST  _REMOTE_USER  _REMOTE_ALIAS
# Returns 1 if the user cancels either prompt.
_prompt_remote() {
    # Redirect stdout to a temp file instead of using $() so that
    # _LAST_SELECTED_ALIAS (set inside read_remote_host_address when the user
    # picks an existing alias) is not lost in a subshell. Without this, two hosts
    # sharing the same IP cause get_alias_for_host_ip to return the wrong alias.
    local _rha_out
    _mktemp_reg _rha_out .sshdd-host || return 1
    read_remote_host_address "$DEFAULT_SUBNET_PREFIX" > "$_rha_out" || { rm -f "$_rha_out"; return 1; }
    _REMOTE_HOST=$(<"$_rha_out")
    rm -f "$_rha_out"
    _REMOTE_ALIAS="${_LAST_SELECTED_ALIAS:-$(get_alias_for_host_ip "$_REMOTE_HOST")}"
    _REMOTE_USER=$(read_remote_user "$DEFAULT_USER") || return 1
}
