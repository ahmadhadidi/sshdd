# lib/ssh-config.sh — SSH config parsing
# Sourced by sshdd.sh — do not execute directly.
[[ -n "${_SSH_CONFIG_SH_LOADED:-}" ]] && return 0
_SSH_CONFIG_SH_LOADED=1
# EXPORTS: get_configured_ssh_hosts  get_available_ssh_keys
#          _get_host_block  _replace_host_block  _block_field
#          get_identity_files_for_host  get_hosts_using_key
#          get_alias_for_host_ip  get_ip_from_host_config
#          get_user_from_host_config  get_identity_file_from_host_config

# ─── SSH config parsing ───────────────────────────────────────────────────────

# Print "alias|hostname|user" for every non-wildcard Host block in ~/.ssh/config.
get_configured_ssh_hosts() {
    [[ -f "$SSH_CONFIG" ]] || return 0
    awk '
        { l=$0; sub(/^[ \t]+/, "", l); split(l, a, /[ \t=]+/); k=tolower(a[1]) }
        k == "host" {
            if (alias != "" && alias != "*") print alias "|" hn "|" user
            alias=a[2]; hn=""; user=""
        }
        k == "hostname" { hn=a[2] }
        k == "user"     { user=a[2] }
        END { if (alias != "" && alias != "*") print alias "|" hn "|" user }
    ' "$SSH_CONFIG"
}

# Print names of private key files in ~/.ssh (no .pub, excluding system files).
get_available_ssh_keys() {
    [[ -d "$SSH_DIR" ]] || return 0
    local exclude="config known_hosts known_hosts.old authorized_keys authorized_keys2 environment rc"
    local f
    for f in "$SSH_DIR"/*; do
        [[ -f "$f" ]] || continue
        local name; name=$(basename "$f")
        [[ $name == *.pub ]] && continue
        local skip=0
        local ex
        for ex in $exclude; do
            shopt -s nocasematch
            [[ "$name" == "$ex" ]] && skip=1
            shopt -u nocasematch
            (( skip )) && break
        done
        (( skip )) || printf '%s\n' "$name"
    done | sort
}

# Extract the full text of the Host block for a given alias. Sets _HOST_BLOCK global.
_get_host_block() {
    local alias="$1"
    _HOST_BLOCK=""
    [[ -f "$SSH_CONFIG" ]] || return 0
    local esc; esc=$(_regex_escape "$alias")
    _HOST_BLOCK=$(perl -0777 -ne \
        "/(^Host[ \t]+${esc}\\b.*?)(?=^Host[ \t]|\\z)/ms and print \$1" \
        "$SSH_CONFIG" 2>/dev/null || true)
}

# Print IdentityFile values for a given host alias or IP address.
get_identity_files_for_host() {
    local target="$1"
    [[ -z $target || ! -f "$SSH_CONFIG" ]] && return 0

    _get_host_block "$target"
    local block="$_HOST_BLOCK"

    # If no alias match, search by HostName value
    if [[ -z $block ]]; then
        block=$(awk -v tgt="$target" '
            { l=$0; sub(/^[ \t]+/, "", l); split(l, a, /[ \t=]+/); k=tolower(a[1]) }
            k == "host" { if (hit) exit; block="" }
            { block=block $0 "\n" }
            k == "hostname" && a[2]==tgt { hit=1 }
            END { if (hit) printf "%s", block }
        ' "$SSH_CONFIG" 2>/dev/null || true)
    fi

    [[ -z $block ]] && return 0
    printf '%s\n' "$block" | \
        grep -E '^\s*IdentityFile\s+' | \
        sed -E 's/^\s*IdentityFile\s+//; s/^"(.*)"$/\1/; s/^\s+//; s/\s+$//'
}

# Print "alias|hostname|user" for hosts whose config block references KeyName as IdentityFile.
get_hosts_using_key() {
    local keyname="$1"
    [[ -f "$SSH_CONFIG" ]] || return 0
    local esc; esc=$(_regex_escape "$keyname")
    while IFS='|' read -r alias hn user; do
        _get_host_block "$alias"
        if printf '%s\n' "$_HOST_BLOCK" | \
               grep -qE "IdentityFile\s+.*[/\\\\]?${esc}[[:space:]]*$"; then
            printf '%s|%s|%s\n' "$alias" "$hn" "$user"
        fi
    done < <(get_configured_ssh_hosts)
}

# Extract a single field value from a host block.
# Keyword match is case-insensitive and accepts "Key value" or "Key=value" (ssh_config syntax).
# Pure awk: BSD sed (macOS) has no portable case-insensitive s///i flag.
_block_field() {
    local field="$1" block="$2"
    printf '%s\n' "$block" | awk -v f="$field" '
        {
            line = $0; sub(/^[ \t]+/, "", line)
            if (!match(line, /[ \t]*[ \t=][ \t]*/)) next
            if (tolower(substr(line, 1, RSTART - 1)) != tolower(f)) next
            v = substr(line, RSTART + RLENGTH); sub(/[ \t\r]+$/, "", v)
            print v; exit
        }'
}

# Return the Host alias whose HostName matches a given IP/hostname.
get_alias_for_host_ip() {
    local ip="$1"
    [[ -z $ip || ! -f "$SSH_CONFIG" ]] && return 0
    awk -v tgt="$ip" '
        { l=$0; sub(/^[ \t]+/, "", l); split(l, a, /[ \t=]+/); k=tolower(a[1]) }
        k == "host" { alias=a[2] }
        k == "hostname" && a[2]==tgt { print alias; exit }
    ' "$SSH_CONFIG" 2>/dev/null
}

get_ip_from_host_config() {
    local alias="$1"
    _get_host_block "$alias"
    _block_field "HostName" "$_HOST_BLOCK"
}

get_user_from_host_config() {
    local alias="$1"
    _get_host_block "$alias"
    _block_field "User" "$_HOST_BLOCK"
}

get_identity_file_from_host_config() {
    local alias="$1"
    _get_host_block "$alias"
    local raw
    raw=$(_block_field "IdentityFile" "$_HOST_BLOCK")
    raw="${raw/#\~/$HOME}"
    raw="${raw/#\$HOME/$HOME}"
    printf '%s' "$raw"
}

# Replace old_block with new_block in SSH_CONFIG.
# Pass new_block="" to delete the block entirely.
# Uses perl (preferred) with python3 fallback.
_replace_host_block() {
    local old_block="$1" new_block="${2:-}"
    if command -v perl &>/dev/null; then
        perl -0777 -i -pe "s/\Q${old_block}\E/${new_block}/" "$SSH_CONFIG" 2>/dev/null && return 0
    fi
    if command -v python3 &>/dev/null; then
        python3 -c "
f='$SSH_CONFIG'
content=open(f).read()
open(f,'w').write(content.replace('''${old_block}''', '''${new_block}''', 1))
" 2>/dev/null && return 0
    fi
    return 1
}
