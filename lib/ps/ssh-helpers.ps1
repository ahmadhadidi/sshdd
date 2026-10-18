# lib/ps/ssh-helpers.ps1 — SSH utility helpers shared across ssh-ops and menu
# EXPORTS: Write-Out  Write-OutItem  Show-OpBanner
#          Write-SSHFence  Write-SSHFenceClose
#          Invoke-RemotePrompt  Write-IdentityFiles  Ensure-SSHDir  Write-KeyPair

# ─── Output helpers ───────────────────────────────────────────────────────────

function ConvertTo-NativeArgument {
    # PowerShell 7.3+ passes native-command arguments verbatim. Windows PowerShell 5.1 and
    # PS <= 7.2 ("Legacy") drop empty strings and don't escape embedded quotes, so a passphrase
    # or comment with " or an empty -N '' would reach ssh-keygen changed. Escape for them only.
    param([string]$Value)
    $mode = Get-Variable PSNativeCommandArgumentPassing -ValueOnly -ErrorAction SilentlyContinue
    if ($mode -and $mode -ne 'Legacy') { return $Value }
    if ($Value -eq '') { return '""' }
    $v = $Value -replace '(\\*)"', '$1$1\"'
    if ($v -match '\s') { $v = $v -replace '(\\+)$', '$1$1' }
    return $v
}


function Remove-RemotePublicKey {
    # Same as bash _remote_remove_pubkey: the key travels on stdin, never inside the command
    # (a comment with ' would run on the remote, plan Z1); authorized_keys is rewritten in place,
    # keeping its mode (Z3); CR is stripped because PS 5.1 pipes text with CRLF. Returns $true on success.
    param([string]$Target, [string]$PublicKey)
    $OutputEncoding = [System.Text.UTF8Encoding]::new($false)
    $cmd = 't=$(mktemp) && k=$(mktemp) && tr -d ''\r'' > "$k" && awk ''NR==FNR { keys[$0]; next } !($0 in keys)'' "$k" ~/.ssh/authorized_keys > "$t" && cat "$t" > ~/.ssh/authorized_keys; rc=$?; rm -f "$t" "$k"; exit $rc'
    $PublicKey.TrimEnd("`r", "`n") | ssh $Target (ConvertTo-NativeArgument $cmd)
    return ($LASTEXITCODE -eq 0)
}


function Write-TextFile {
    # UTF-8 without BOM, through the existing file (keeps a symlink and the file's ACL/mode).
    # Never Set-Content -Encoding UTF8 / WriteAllText(...UTF8): those write a BOM (Set-Content only
    # on Windows PowerShell 5.1), and OpenSSH then rejects the whole config ("Bad configuration
    # option: \357\273\277host") or the private key ("error in libcrypto").
    param([string]$Path, [string]$Text)
    # Resolve through PowerShell first: .NET doesn't turn "\" into "/" on macOS/Linux pwsh, so
    # "$env:USERPROFILE\.ssh\config" would become a new file literally named "…\.ssh\config".
    $full = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path)
    [System.IO.File]::WriteAllText($full, $Text, [System.Text.UTF8Encoding]::new($false))
}


function Test-SSHKeyName {
    # Plain file name inside ~/.ssh: letters, digits, . _ @ + -, no "/" "\" "..", not starting with
    # "." or "-" (plan Z1: "..\..\x" made ssh-keygen write outside ~/.ssh). Same rule as bash.
    param([string]$Name)
    return ($Name -cmatch '^[A-Za-z0-9_][A-Za-z0-9._@+-]*$' -and $Name -notmatch '\.\.')
}


function Write-Out {
    # Write-Out STYLE FORMAT [ARGS...]
    # Prints a 2-space indented, color-coded line.
    # Styles: ok (green)  warn (yellow)  error (red)  info (cyan)
    #         dim (gray)  heading (bright-cyan)  plain (bright-white)
    param(
        [string]$Style,
        [string]$Format,
        [Parameter(ValueFromRemainingArguments)][object[]]$FormatArgs = @()
    )
    $code = switch ($Style) {
        'ok'      { 32 }
        'warn'    { 33 }
        'error'   { 31 }
        'info'    { 36 }
        'dim'     { 90 }
        'heading' { 96 }
        'plain'   { 97 }
        default   { 37 }
    }
    $text = if ($FormatArgs.Count -gt 0) { $Format -f $FormatArgs } else { $Format }
    [Console]::WriteLine("  `e[${code}m${text}`e[0m")
}


function Write-OutItem {
    # Write-OutItem FORMAT [ARGS...]
    # Prints "  + text" with a green plus sign.
    param(
        [string]$Format,
        [Parameter(ValueFromRemainingArguments)][object[]]$FormatArgs = @()
    )
    $text = if ($FormatArgs.Count -gt 0) { $Format -f $FormatArgs } else { $Format }
    [Console]::WriteLine("  `e[32m+`e[0m  ${text}")
}


function Show-OpBanner {
    # Show-OpBanner -Pairs @("key","val",...) [-StartRow N]
    # Renders a styled context block with orange box-drawing borders.
    #
    # Stream mode (default, StartRow -lt 0): prints to stdout.
    # Buffer mode (StartRow >= 0): writes positioned ANSI into $script:_OpBannerBuf.
    #
    # Always sets $script:_OpBannerRows and $script:_OpBannerBuf.
    param(
        [string[]]$Pairs,
        [int]$StartRow = -1
    )

    $pairCount  = [Math]::Floor($Pairs.Count / 2)
    $script:_OpBannerRows = $pairCount + 4   # top-border + pad + content(s) + pad + bot-border
    $script:_OpBannerBuf  = ""

    $tw   = $Host.UI.RawUI.WindowSize.Width
    $mx   = 2                                # x-margin (spaces each side)
    $ow   = [Math]::Max(10, $tw - $mx * 2)  # outer box width (corners included)
    $iw   = $ow - 2                          # inner width (between │ chars)

    # Find longest key for alignment
    $maxKLen = 0
    for ($i = 0; $i -lt $Pairs.Count - 1; $i += 2) {
        if ($Pairs[$i].Length -gt $maxKLen) { $maxKLen = $Pairs[$i].Length }
    }

    # Box chars
    $TL  = [char]0x250C  # ┌
    $TR  = [char]0x2510  # ┐
    $BL  = [char]0x2514  # └
    $BR  = [char]0x2518  # ┘
    $VB  = [char]0x2502  # │
    $BUL = [char]0x2022  # •

    # Styles
    $OC  = "`e[38;2;217;119;87m"   # orange fg
    $FB  = "`e[48;2;48;26;19m"     # faint dark bg
    $FW  = "`e[97m"                 # bright white fg
    $BLD = "`e[1m"                  # bold on
    $NBD = "`e[22m"                 # bold off
    $RS  = "`e[0m"
    $MX  = " " * $mx

    # Horizontal rule: ow-2 connected ─ chars
    $hrule = ([char]0x2500).ToString() * ($ow - 2)

    # Inner blank padding row
    $ipad = " " * $iw

    # Pre-build content rows
    $crowList = [System.Collections.Generic.List[string]]::new()
    for ($i = 0; $i -lt $Pairs.Count - 1; $i += 2) {
        $keyRaw = $Pairs[$i]
        $val    = $Pairs[$i + 1]
        $keyUp  = ($keyRaw.ToUpper() + ":").PadRight($maxKLen + 2)
        # display width: "  • " (4) + key (maxKLen+2) + "  " (2) + val
        $cdw    = 4 + ($maxKLen + 2) + 2 + $val.Length
        $padN   = [Math]::Max(0, $iw - $cdw)
        $pad    = " " * $padN
        $crowList.Add("  ${BUL} ${BLD}${keyUp}${NBD}  ${val}${pad}")
    }

    $top  = "${MX}${OC}${TL}${hrule}${TR}${RS}"
    $bot  = "${MX}${OC}${BL}${hrule}${BR}${RS}"
    $prow = "${MX}${OC}${VB}${RS}${FB}${ipad}${RS}${OC}${VB}${RS}"

    if ($StartRow -ge 0) {
        $r = $StartRow
        $script:_OpBannerBuf += "`e[${r};1H${top}`e[K"; $r++
        $script:_OpBannerBuf += "`e[${r};1H${prow}`e[K"; $r++
        foreach ($crow in $crowList) {
            $line = "${MX}${OC}${VB}${RS}${FB}${FW}${crow}${RS}${OC}${VB}${RS}"
            $script:_OpBannerBuf += "`e[${r};1H${line}`e[K"; $r++
        }
        $script:_OpBannerBuf += "`e[${r};1H${prow}`e[K"; $r++
        $script:_OpBannerBuf += "`e[${r};1H${bot}`e[K"
    } else {
        [Console]::WriteLine($top)
        [Console]::WriteLine($prow)
        foreach ($crow in $crowList) {
            [Console]::WriteLine("${MX}${OC}${VB}${RS}${FB}${FW}${crow}${RS}${OC}${VB}${RS}")
        }
        [Console]::WriteLine($prow)
        [Console]::WriteLine($bot)
    }
}


# ─── Connection helpers ───────────────────────────────────────────────────────

function Write-SSHFence {
    # Opening fence rule: "── SSH Session user@host ──"
    param([string]$Target = "")
    $w      = $Host.UI.RawUI.WindowSize.Width
    $innerW = [Math]::Max(10, $w - 4)
    $dash   = [char]0x2500  # ─
    if ($Target) {
        $label  = " SSH Session $Target "
        $dTotal = [Math]::Max(4, $innerW - $label.Length)
        $lw     = [Math]::Floor($dTotal / 2)
        $rw     = $dTotal - $lw
        $left   = $dash.ToString() * $lw
        $right  = $dash.ToString() * $rw
        [Console]::WriteLine("  `e[2m${left}`e[0m`e[90m${label}`e[0m`e[2m${right}`e[0m")
    } else {
        [Console]::WriteLine("  `e[2m$($dash.ToString() * $innerW)`e[0m")
    }
}


function Write-SSHFenceClose {
    # Closing fence rule: "── SSH session closed ──"
    $w      = $Host.UI.RawUI.WindowSize.Width
    $innerW = [Math]::Max(10, $w - 4)
    $dash   = [char]0x2500
    $label  = " SSH session closed "
    $dTotal = [Math]::Max(4, $innerW - $label.Length)
    $lw     = [Math]::Floor($dTotal / 2)
    $rw     = $dTotal - $lw
    $left   = $dash.ToString() * $lw
    $right  = $dash.ToString() * $rw
    [Console]::WriteLine("  `e[2m${left}`e[0m`e[90m${label}`e[0m`e[2m${right}`e[0m")
}


# ─── Remote prompt helper ─────────────────────────────────────────────────────

function Invoke-RemotePrompt {
    # Prompts for a remote host and user in one call.
    # Sets $script:_RemoteHost, $script:_RemoteUser, $script:_RemoteAlias.
    # Lets OperationCanceledException propagate (callers handle it in _InvokeMenuAction).
    $script:_RemoteHost  = Read-RemoteHostAddress -SubnetPrefix $DefaultSubnetPrefix
    $script:_RemoteAlias = if ($script:_LastSelectedAlias) { $script:_LastSelectedAlias } else {
        Get-AliasForHostIP $script:_RemoteHost
    }
    $script:_RemoteUser  = Read-RemoteUser -DefaultUser $DefaultUserName
}


# ─── Output helpers ───────────────────────────────────────────────────────────

function Write-IdentityFiles {
    # Print the IdentityFile entries configured for a host (informational only).
    param([string]$IdLookup)
    foreach ($k in (Get-IdentityFilesForHost $IdLookup)) {
        Write-Out 'dim' "Using key: $k"
    }
}


# ─── Local filesystem helpers ─────────────────────────────────────────────────

function Ensure-SSHDir {
    $sshDir = "$env:USERPROFILE\.ssh"
    if (-not (Test-Path $sshDir)) {
        New-Item -ItemType Directory -Path $sshDir -Force | Out-Null
    }
}


function Write-KeyPair {
    # Write a key pair to ~/.ssh with overwrite confirmation.
    # CopyMode=$true  → Copy-Item from file paths PrivData/PubData.
    # CopyMode=$false → WriteAllText with literal string content.
    # Returns $true on success, $false if aborted.
    param(
        [string]$DestPriv,
        [string]$DestPub,
        [string]$PrivData,
        [string]$PubData,
        [bool]$CopyMode = $false
    )
    # Only plain names directly in ~/.ssh (import names come from user text or a remote path).
    $resolve = { param($p) $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($p).TrimEnd('/', '\') }
    $inSshDir = (& $resolve (Split-Path $DestPriv -Parent)) -eq (& $resolve (Join-Path $env:USERPROFILE ".ssh"))
    if (-not $inSshDir -or -not (Test-SSHKeyName (Split-Path $DestPriv -Leaf)) -or $DestPub -ne "$DestPriv.pub") {
        Write-Out 'error' "Invalid key name '$(Split-Path $DestPriv -Leaf)': use letters, digits and . _ @ + - only."
        return $false
    }
    if (Test-Path $DestPriv) {
        $resp = Read-ColoredInput -Prompt "  '$(Split-Path $DestPriv -Leaf)' already exists. Overwrite? [y/N]" -ForegroundColor Yellow
        if ($resp -notmatch '^[Yy]') {
            Write-Out 'warn' 'Aborted.'
            return $false
        }
    }
    if ($CopyMode) {
        Copy-Item $PrivData $DestPriv -Force
        Copy-Item $PubData  $DestPub  -Force
    } else {
        Write-TextFile $DestPriv $PrivData
        # Ensure public key ends with exactly one newline
        $pubContent = $PubData.TrimEnd("`n", "`r") + "`n"
        Write-TextFile $DestPub $pubContent
    }
    # macOS/Linux pwsh: ssh refuses a private key others can read (Windows uses the profile ACL).
    if ($PSVersionTable.Platform -eq 'Unix') { chmod 600 $DestPriv; chmod 644 $DestPub }
    Write-OutItem "$DestPriv  imported."
    Write-OutItem "$DestPub  imported."
    return $true
}
