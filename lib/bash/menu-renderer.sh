# lib/menu-renderer.sh — TUI event loop and operation runner
# Sourced by sshdd.sh — do not execute directly.
# Depends on menu.sh (invoke_menu_choice, _check_config_at_start,
#                      _show_menu_help, _do_create_config).
[[ -n "${_MENU_RENDERER_SH_LOADED:-}" ]] && return 0
_MENU_RENDERER_SH_LOADED=1
# EXPORTS: show_main_menu  _invoke_choice

# ─── Operation runner ─────────────────────────────────────────────────────────

# Clear screen, render the op title box, run invoke_menu_choice, wait for ack.
# Sets need_full=1 on return (local in show_main_menu — bash dynamic scoping).
_invoke_choice() {
    local choice="$1" label="$2"
    _mouse_off   # operations run ssh, editors and prompts: no click codes there (#41)
    _dbg "_invoke_choice: choice='$choice' label='$label'"
    _draw_op_header "$label"

    # Restore cooked terminal mode for operations that use normal read
    local _stty_saved_inner
    _stty_saved_inner=$(stty -g 2>/dev/null) || true
    stty sane -ixon 2>/dev/null || true

    _setup_askpass
    local skip_wait=0
    _OP_ERROR=0
    invoke_menu_choice "$choice" || skip_wait=$?
    _dbg "_invoke_choice: '$choice' completed, skip_wait=$skip_wait error=$_OP_ERROR"
    _destroy_askpass

    stty "$_stty_saved_inner" 2>/dev/null || true

    # Non-zero = own full-screen TUI or cancelled: back to the menu at once. But an error must
    # stay readable: error paths also return 1 and their message used to flash away (plan S5).
    (( skip_wait && ! _OP_ERROR )) || wait_user_acknowledge
    printf '\e[?25l'
    need_full=1
}

# ─── Main menu ────────────────────────────────────────────────────────────────

# Build a full-width reverse-video bar from KEY LABEL pairs into _HINT_BAR (no fork).
# If it doesn't fit WIDTH, pairs are dropped from the middle; the last pair (Quit/Help) always stays,
# so the bar never wraps onto a second row (a wrap scrolls the whole screen up).
_hint_bar() {
    local w="$1"; shift
    local -a _hk=() _hl=()
    while (( $# >= 2 )); do _hk+=("$1"); _hl+=("$2"); shift 2; done
    local n=${#_hk[@]} keep=$(( ${#_hk[@]} - 1 )) i plain out
    while :; do
        plain="" out=""
        for (( i=0; i<n; i++ )); do
            (( i >= keep && i < n - 1 )) && continue
            plain+="   ${_hk[$i]} ${_hl[$i]}"
            out+=$'   \e[1m'"${_hk[$i]}"$'\e[0;7m '"${_hl[$i]}"
        done
        plain="  ${plain:3}"; out="  ${out:3}"
        (( ${#plain} <= w || keep == 0 )) && break
        (( keep-- ))
    done
    (( ${#plain} > w )) && { plain="${plain:0:w}"; out="$plain"; }
    printf -v _HINT_BAR '\e[7m%s%*s\e[0m' "$out" "$(( w - ${#plain} ))" ""
}

# Open https://axc.sh in the browser (#44): on this machine only; over SSH it would open on the remote.
_open_axc() {
    [[ -n ${SSH_CONNECTION:-} ]] && return 0
    local o=''
    if [[ $(uname) == Darwin ]]; then o=open
    elif command -v xdg-open >/dev/null 2>&1; then o=xdg-open
    else return 0; fi
    ( "$o" https://axc.sh >/dev/null 2>&1 & )      # detached: not a job sshdd's cleanup would kill
}

show_main_menu() {
    local -a m_type=(
        header  item    item    item    item    item    item    item    item    item
        header  item    item    item    item    item    item    item    item    item
        header  item    item    item    item
    )
    local -a m_label=(
        "Remote"
        "🔑  Generate & Install SSH Key on A Remote Machine"
        "📤  Install SSH Key on A Remote Machine"
        "🔌  Test SSH Connection"
        "🗑   Delete Remote SSH Key"
        "🔄  Promote Key on A Remote Machine"
        "📋  List Authorized Keys on Remote Host"
        "🔗  Add Config Block for Existing Remote Key"
        "📡  List Known Hosts on Remote Host"
        "🧽  Forget Host Key on Remote Host"
        "Local"
        "✨  Generate Local SSH Key"
        "🗝   List Keys Locally"
        "➕  Append Hostname: Add SSH Key to Host Config"
        "🗑   Delete Local SSH Key"
        "❌  Remove Config: Unlink SSH Key from Host"
        "📥  Import Key from Another Machine"
        "📜  List Known Hosts"
        "🧹  Forget Host Key"
        "📒  Edit Known Hosts"
        "Config File"
        "🏚   Remove Host from SSH Config"
        "👁   View Config"
        "📝  Edit Config"
        "🚪  Exit"
    )
    local -a m_choice=(
        ""   "1"  "15" "2"  "3"  "4"  "16" "17" "21" "22"
        ""   "5"  "6"  "7"  "8"  "9"  "18" "19" "20" "23"
        ""   "12" "13" "14" "q"
    )
    local -a m_hotkey=(
        ""   "G"  "I"  "T"  "D"  "P"  "Z"  "N"  "O"  "B"
        ""   "W"  "L"  "A"  "X"  "R"  "M"  "K"  "F"  "S"
        ""   "H"  "V"  "E"  "Q"
    )

    # Build flat rows
    local -a fr_type=() fr_label=() fr_nidx=() fr_choice=() fr_hotkey=()
    local ni=0 i
    for (( i=0; i<${#m_type[@]}; i++ )); do
        if [[ ${m_type[$i]} == "header" ]]; then
            fr_type+=("blank");  fr_label+=("");               fr_nidx+=(-1); fr_choice+=(""); fr_hotkey+=("")
            fr_type+=("header"); fr_label+=("${m_label[$i]}"); fr_nidx+=(-1); fr_choice+=(""); fr_hotkey+=("")
        else
            fr_type+=("item");   fr_label+=("${m_label[$i]}"); fr_nidx+=("$ni"); fr_choice+=("${m_choice[$i]}"); fr_hotkey+=("${m_hotkey[$i]}")
            (( ni++ ))
        fi
    done
    local flat_count=${#fr_type[@]}

    local -a nav_label=() nav_choice=() nav_hotkey=()
    for (( i=0; i<flat_count; i++ )); do
        if [[ ${fr_type[$i]} == "item" ]]; then
            nav_label+=("${fr_label[$i]}")
            nav_choice+=("${fr_choice[$i]}")
            nav_hotkey+=("${fr_hotkey[$i]}")
        fi
    done
    local nav_count=${#nav_label[@]}

    local sel=0 prev_sel=-1 need_full=1 running=1
    local term_w=0 term_h=0 view_off=0
    local -a item_rows  # integer-keyed; indexed array works on bash 3.2

    # Enter alternate screen, save terminal state globally for reliable cleanup.
    # Then enter raw/noecho immediately so the event loop never echoes escape sequences.
    _STTY_SAVED=$(stty -g 2>/dev/null) || true
    # Where the shell's cursor is, so exit can put it back even on terminals that don't
    # restore it when leaving the alternate screen (TODO #9: prompt in an odd place in herdr).
    _cursor_pos; _ENTRY_ROW=$_CUR_ROW _ENTRY_COL=$_CUR_COL
    printf '\e[?1049h\e[?25l'
    # -ixon: Ctrl+S (XOFF) froze all output, so the app looked hung until Ctrl+Q (plan H3).
    stty -echo -icanon -ixon min 0 time 1 2>/dev/null || true

    _MENU_CLEANED_UP=0
    _menu_cleanup() {
        (( _MENU_CLEANED_UP )) && return 0
        _MENU_CLEANED_UP=1
        # A second signal mid-cleanup ran its "exit" trap and cut cleanup short (temp files left).
        trap '' HUP INT TERM TSTP
        # Files first: removing them needs no terminal, which may already be gone (closed window).
        _destroy_askpass 2>/dev/null || true
        (( ${#_CLEANUP_PATHS[@]} )) && rm -f "${_CLEANUP_PATHS[@]}" 2>/dev/null
        # Background helpers (host probes, spinner) must not outlive sshdd.
        # CONT after TERM: after Ctrl+Z they are stopped and would ignore TERM.
        local _job
        for _job in $(jobs -p); do kill "$_job" 2>/dev/null; kill -CONT "$_job" 2>/dev/null; done
        _spin_stop 2>/dev/null || true
        _mouse_off   # never leave the terminal reporting clicks (#41)
        # Clear the alternate screen before leaving so no content bleeds through,
        # then restore cursor visibility and switch back to the normal screen.
        local _back=''
        [[ -n ${_ENTRY_ROW:-} ]] && printf -v _back '\e[%d;%dH' "$_ENTRY_ROW" "$_ENTRY_COL"
        printf '\e[?25h\e[2J\e[H\e[?1049l%s' "$_back" >/dev/tty 2>/dev/null || \
        printf '\e[?25h\e[2J\e[H\e[?1049l%s' "$_back"
        stty "$_STTY_SAVED" 2>/dev/null || stty sane 2>/dev/null || true
    }

    # EXIT covers all paths. INT/TERM/TSTP set the right exit code then let EXIT
    # handle cleanup — the guard flag ensures _menu_cleanup runs exactly once.
    trap '_menu_cleanup' EXIT
    trap 'exit 130' INT
    trap 'exit 0'   TERM TSTP
    trap 'exit 129' HUP      # terminal closed / SSH dropped
    trap 'need_full=1' WINCH
    trap '' QUIT             # Ctrl+\ does nothing; it killed the open prompt's subshell (#28). Inherited.

    # ── Startup config file check ────────────────────────────────────────────
    if [[ ! -f "$SSH_CONFIG" ]]; then
        _check_config_at_start
    fi

    while (( running )); do

        # ── Full render ──────────────────────────────────────────────────────
        if (( need_full )); then
            _mouse_on   # #41: the menu takes clicks; on again after every screen that switched it off
            _term_size
            term_w=$TERM_W; term_h=$TERM_H

            local box_w=$(( term_w - 4 > 0 ? term_w - 4 : 10 ))
            local inner_w=$(( box_w - 2 ))
            local _TL=$'\xe2\x94\x8c' _TR=$'\xe2\x94\x90' _BL=$'\xe2\x94\x94' _BR=$'\xe2\x94\x98' _VB=$'\xe2\x94\x82'
            local h_rule inner_pad
            printf -v h_rule   '%*s' "$inner_w" ''; h_rule="${h_rule// /─}"
            printf -v inner_pad '%*s' "$inner_w" ''
            local menu_title="🌊 SSHDD -- axc.sh"
            local lbl_len; lbl_len=$(_visual_width "$menu_title")
            local lpad=$(( (inner_w - lbl_len) / 2 )); (( lpad < 0 )) && lpad=0
            local rpad=$(( inner_w - lbl_len - lpad )); (( rpad < 0 )) && rpad=0
            local lspc rspc
            printf -v lspc '%*s' "$lpad" ''
            printf -v rspc '%*s' "$rpad" ''
            # axc.sh as a terminal link (OSC 8, #44); widths above use the plain title
            local title_out="${menu_title%axc.sh}"$'\e]8;;https://axc.sh\e\\axc.sh\e]8;;\e\\'

            local content_start=8
            # Reserve 2 rows: hint bar (bottom) + second bar (F-keys or config warning)
            local content_end=$(( term_h - 2 ))
            local content_rows=$(( content_end - content_start + 1 ))
            (( content_rows < 1 )) && content_rows=1

            local sel_flat=-1
            for (( i=0; i<flat_count; i++ )); do
                if [[ ${fr_type[$i]} == "item" ]] && (( fr_nidx[$i] == sel )); then
                    sel_flat=$i; break
                fi
            done
            if (( sel_flat >= 0 )); then
                if (( sel_flat < view_off )); then
                    view_off=$sel_flat
                elif (( sel_flat >= view_off + content_rows )); then
                    view_off=$(( sel_flat - content_rows + 1 ))
                fi
            fi
            (( view_off < 0 )) && view_off=0

            local f
            f="$(printf '\e[2J\e[H')"
            f+="$(printf '\e[2;1H  \e[96m%s%s%s\e[0m\e[K'                                          "$_TL" "$h_rule" "$_TR")"
            f+="$(printf '\e[3;1H  \e[96m%s\e[0m\e[48;5;23m%s\e[0m\e[96m%s\e[0m\e[K'              "$_VB" "$inner_pad" "$_VB")"
            f+="$(printf '\e[4;1H  \e[96m%s\e[0m\e[48;5;23m\e[1;97m%s%s%s\e[0m\e[96m%s\e[0m\e[K'  "$_VB" "$lspc" "$title_out" "$rspc" "$_VB")"
            f+="$(printf '\e[5;1H  \e[96m%s\e[0m\e[48;5;23m%s\e[0m\e[96m%s\e[0m\e[K'              "$_VB" "$inner_pad" "$_VB")"
            f+="$(printf '\e[6;1H  \e[96m%s%s%s\e[0m\e[K'                                          "$_BL" "$h_rule" "$_BR")"
            f+="$(printf '\e[7;1H\e[K')"

            item_rows=()
            local row=$content_start
            local end_fi=$(( view_off + content_rows < flat_count ? view_off + content_rows : flat_count ))
            for (( i=view_off; i<end_fi; i++ )); do
                case "${fr_type[$i]}" in
                    blank)
                        f+="$(printf '\e[%d;1H\e[K' "$row")" ;;
                    header)
                        f+="$(printf '\e[%d;1H  \e[90m  > \e[1m%s\e[0m\e[K' "$row" "${fr_label[$i]}")" ;;
                    item)
                        item_rows[${fr_nidx[$i]}]=$row
                        if (( fr_nidx[$i] == sel )); then
                            f+="$(printf '\e[%d;1H\e[48;5;6m\e[1;97m    %s\e[K\e[0m' "$row" "${fr_label[$i]}")"
                        else
                            local lbl; lbl=$(format_menu_label "${fr_label[$i]}" "${fr_hotkey[$i]}")
                            f+="$(printf '\e[%d;1H\e[0m\e[97m    %s\e[0m\e[K' "$row" "$lbl")"
                        fi
                        ;;
                esac
                (( row++ ))
            done
            while (( row <= content_end )); do
                f+="$(printf '\e[%d;1H\e[K' "$row")"
                (( row++ ))
            done

            # Scroll indicators (ASCII ^/v instead of Unicode arrows)
            (( view_off > 0 )) && \
                f+="$(printf '\e[%d;%dH\e[90m^\e[0m' "$content_start" "$(( term_w - 1 ))")"
            (( view_off + content_rows < flat_count )) && \
                f+="$(printf '\e[%d;%dH\e[90mv\e[0m' "$content_end" "$(( term_w - 1 ))")"

            # Second bar: red config warning when absent, else dim F-key shortcuts
            if [[ -f $SSH_CONFIG && ! -r $SSH_CONFIG ]]; then
                # Unreadable config: every list would silently be empty (plan E2).
                local _cp="${SSH_CONFIG/#$HOME/~}"
                local wmsg="  ⚠  Can't read $_cp — fix: chmod 600 $_cp"
                local wpad; wpad=$(_repeat ' ' "$(( term_w - ${#wmsg} > 0 ? term_w - ${#wmsg} : 0 ))")
                f+="$(printf '\e[%d;1H\e[41m\e[1;97m%s%s\e[0m' "$(( term_h - 1 ))" "${wmsg:0:term_w}" "$wpad")"
            elif (( _CONFIG_MISSING )); then
                local wmsg="  ⚠  SSH config missing — press F2 to create it"
                local wpad; wpad=$(_repeat ' ' "$(( term_w - ${#wmsg} > 0 ? term_w - ${#wmsg} : 0 ))")
                f+="$(printf '\e[%d;1H\e[41m\e[1;97m%s%s\e[0m' "$(( term_h - 1 ))" "$wmsg" "$wpad")"
            else
                # Same reverse-video style as the hint bar below it (TODO #2).
                _hint_bar "$term_w" F1 "Best Practices" F5 "Conf Defaults" "?" Help
                f+="$(printf '\e[%d;1H' "$(( term_h - 1 ))")$_HINT_BAR"
            fi

            # Single-row hint bar
            _hint_bar "$term_w" Up/Dn Navigate Enter Select G Generate T Test D Delete L List Q Quit
            f+="$(printf '\e[%d;1H' "$term_h")$_HINT_BAR"

            printf '%s' "$f"
            prev_sel=$sel
            need_full=0

        # ── Differential update ──────────────────────────────────────────────
        elif (( prev_sel != sel )); then
            if [[ -n ${item_rows[$sel]+x} && -n ${item_rows[$prev_sel]+x} ]]; then
                local r=${item_rows[$prev_sel]}
                local lbl; lbl=$(format_menu_label "${nav_label[$prev_sel]}" "${nav_hotkey[$prev_sel]}")
                printf '\e[%d;1H\e[0m\e[97m    %s\e[0m\e[K' "$r" "$lbl"
                r=${item_rows[$sel]}
                printf '\e[%d;1H\e[48;5;6m\e[1;97m    %s\e[K\e[0m' "$r" "${nav_label[$sel]}"
                prev_sel=$sel
            else
                need_full=1
            fi
        fi

        # ── Poll for input (with resize detection) ───────────────────────────
        local got_key=0
        while (( ! got_key )); do
            if _read_key_nb; then
                got_key=1
            else
                local nw nh _sz
                _sz=$(stty size 2>/dev/null)
                if [[ -n $_sz ]]; then
                    nh=${_sz%% *}; nw=${_sz##* }
                else
                    nw=$(tput cols  2>/dev/null || echo 80)
                    nh=$(tput lines 2>/dev/null || echo 24)
                fi
                if (( nw != term_w || nh != term_h )); then
                    term_w=$nw; term_h=$nh
                    need_full=1
                    break
                fi
            fi
        done
        (( ! got_key )) && continue

        local k="$KEY"
        _dbg "key pressed: $(printf '%s' "$k" | od -An -tx1 2>/dev/null | tr -d ' \n')"
        if [[ ${#k} -eq 1 ]] && _drain_burst; then   # a paste: drop the burst, not hotkeys (#48)
            continue
        fi
        if [[ $k == "$KEY_CLICK" ]] && (( MOUSE_ROW >= 3 && MOUSE_ROW <= 5 )); then
            _open_axc                                # a click on the title opens https://axc.sh (#44)
            continue
        fi
        if [[ $k == "$KEY_CLICK" ]]; then          # a click on an item opens it, like a tab in herdr (#41)
            local _n _hit=-1
            for (( _n=0; _n<nav_count; _n++ )); do
                [[ ${item_rows[$_n]:-} == "$MOUSE_ROW" ]] && { _hit=$_n; break; }
            done
            (( _hit < 0 )) && continue
            sel=$_hit k=$KEY_ENTER
        fi

        # ── Navigation keys ──────────────────────────────────────────────────
        case "$k" in
            "$KEY_UP")
                (( sel = (sel - 1 + nav_count) % nav_count )) ;;
            "$KEY_DOWN")
                (( sel = (sel + 1) % nav_count )) ;;
            "$KEY_HOME"|"$KEY_HOME2")
                sel=0 ;;
            "$KEY_END"|"$KEY_END2")
                sel=$(( nav_count - 1 )) ;;
            "$KEY_ENTER"|"$KEY_ENTER2")
                local choice="${nav_choice[$sel]}"
                _dbg "Enter pressed: sel=$sel choice='$choice' label='${nav_label[$sel]}'"
                if [[ $choice == "q" ]]; then
                    running=0
                else
                    _invoke_choice "$choice" "${nav_label[$sel]}"
                fi
                ;;
            "$KEY_F1_A"|"$KEY_F1_B")
                _invoke_choice "10" "Help: Best Practices"
                ;;
            '?')
                stty sane -ixon 2>/dev/null || true
                printf '\e[?25h'
                _show_menu_help
                stty -echo -icanon min 0 time 1 2>/dev/null || true
                need_full=1
                ;;
            "$KEY_F2_A"|"$KEY_F2_B")
                if (( _CONFIG_MISSING )); then
                    _term_size
                    stty sane -ixon 2>/dev/null || true
                    printf '\e[?25h'
                    _do_create_config
                    printf '\n  \e[90mPress any key to continue...\e[0m'
                    _read_key
                    printf '\e[?25l'
                    stty -echo -icanon min 0 time 1 2>/dev/null || true
                    need_full=1
                else
                    _invoke_choice "13" "👁  View SSH Config"
                fi
                ;;
            "$KEY_F5")
                _invoke_choice "11" "Conf: Global Defaults"
                ;;
            q|Q)
                running=0 ;;
            *)
                if [[ ${#k} -eq 1 ]]; then
                    # Convert pressed key to uppercase once for case-insensitive match.
                    # All hotkeys are defined as uppercase letters, so comparing k_up
                    # against nav_hotkey avoids bash 4+ ${var^^} operator.
                    local k_up hki
                    k_up=$(tr 'a-z' 'A-Z' <<< "$k")
                    for (( hki=0; hki<nav_count; hki++ )); do
                        if [[ -n ${nav_hotkey[$hki]} && \
                              "${nav_hotkey[$hki]}" == "$k_up" ]]; then
                            local hk_choice="${nav_choice[$hki]}"
                            _dbg "Hotkey '$k' -> choice='$hk_choice'"
                            if [[ $hk_choice == "q" ]]; then
                                running=0
                            else
                                _invoke_choice "$hk_choice" "${nav_label[$hki]}"
                            fi
                            break
                        fi
                    done
                fi
                ;;
        esac
    done

    _menu_cleanup
    trap - EXIT INT TERM TSTP HUP WINCH
}
