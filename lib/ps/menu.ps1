# lib/ps/menu.ps1 — Menu dispatcher and all menu case handlers
# Dot-sourced by sshdd.ps1 — do not execute directly.
# EXPORTS: Invoke-MenuChoice
#   handlers: _MenuGenerateAndInstall  _MenuInstallKey  _MenuTestConnection
#             _MenuDeleteRemoteKey  _MenuPromoteKey  _MenuGenerateKey
#             _MenuListKeys  _MenuAppendKeyToConfig  _MenuDeleteLocalKey
#             _MenuRemoveKeyFromConfig  _MenuShowBestPractices  _MenuConfDefaults
#             _MenuRemoveHost  _MenuViewConfig  _MenuEditConfig
#             _MenuListAuthorizedKeys  _MenuAddConfigBlock  _MenuImportKey

# ── Dispatcher ────────────────────────────────────────────────────────────────
# Returns $true to signal "skip Wait-UserAcknowledge"; $null otherwise.
function Invoke-MenuChoice {
    param([string]$Choice)
    switch ($Choice) {
        "1"  { return _MenuGenerateAndInstall }
        "2"  { return _MenuTestConnection }
        "3"  { return _MenuDeleteRemoteKey }
        "4"  { return _MenuPromoteKey }
        "5"  { return _MenuGenerateKey }
        "6"  { return _MenuListKeys }
        "7"  { return _MenuAppendKeyToConfig }
        "8"  { return _MenuDeleteLocalKey }
        "9"  { return _MenuRemoveKeyFromConfig }
        "10" { return _MenuShowBestPractices }
        "11" { return _MenuConfDefaults }
        "12" { return _MenuRemoveHost }
        "13" { return _MenuViewConfig }
        "14" { return _MenuEditConfig }
        "15" { return _MenuInstallKey }
        "16" { return _MenuListAuthorizedKeys }
        "17" { return _MenuAddConfigBlock }
        "18" { return _MenuImportKey }
        "19" { return _MenuListKnownHosts }
        "20" { return _MenuForgetHostKey }
        "21" { return _MenuListRemoteKnownHosts }
        "22" { return _MenuForgetRemoteHostKey }
    }
}

# ── Menu case handlers ────────────────────────────────────────────────────────

function _MenuGenerateAndInstall {   # choice 1 — generate if missing, deploy to remote
    Show-OpBanner @("host", $env:COMPUTERNAME)
    $KeyName = Read-SSHKeyName
    Deploy-SSHKeyToRemote -KeyName $KeyName
}

function _MenuInstallKey {           # choice 15 — key must already exist locally
    Show-OpBanner @("host", $env:COMPUTERNAME)
    $KeyName = Read-SSHKeyName
    if (-not (Find-PrivateKeyInHost -KeyName $KeyName -ReturnResult $true)) {
        Write-Out 'error' "Key '$KeyName' not found locally. Use 'Generate & Install' to create it first."
        return
    }
    Install-SSHKeyOnRemote -KeyName $KeyName
}

function _MenuTestConnection {       # choice 2 — pick key from host config or all local keys; supports Test ALL sweep
    Show-OpBanner @("host", $env:COMPUTERNAME, "user", $DefaultUserName)
    Invoke-RemotePrompt
    $RemoteHost = $script:_RemoteHost
    $RemoteUser = $script:_RemoteUser
    $selAlias   = $script:_RemoteAlias

    $cfgKeys = @(Get-IdentityFilesForHost ($(if ($selAlias) { $selAlias } else { $RemoteHost })))

    if ($cfgKeys.Count -gt 1) {
        $allLabel  = "-- Test ALL ($($cfgKeys.Count) keys)"
        $keyLabels = @($allLabel) + $cfgKeys
        $selected  = Select-FromList -Items $keyLabels -Prompt "Select key to test:"
        if ($selected -and $selected.StartsWith("--")) {
            $isFirst = $true
            $cfgKeys | ForEach-Object {
                if (-not $isFirst) { Write-Host "" }
                $isFirst = $false
                Write-Out 'dim' "Testing with key: $_"
                Test-SSHConnection -RemoteUser $RemoteUser -RemoteHost $RemoteHost -IdentityFile $_
            }
        } elseif ($selected) {
            Write-Out 'dim' "Testing with key: $selected"
            Test-SSHConnection -RemoteUser $RemoteUser -RemoteHost $RemoteHost -IdentityFile $selected
        }
    } else {
        if ($cfgKeys.Count -eq 1) { Write-Out 'dim' "Testing with key: $($cfgKeys[0])" }
        Test-SSHConnection -RemoteUser $RemoteUser -RemoteHost $RemoteHost
    }
}

function _MenuDeleteRemoteKey {      # choice 3 — fetch remote authorized_keys, cross-match local .pub, remove selected; offer to strip config + local files
    Show-OpBanner @("host", $env:COMPUTERNAME)
    Invoke-RemotePrompt
    $RemoteHostAddress = $script:_RemoteHost
    $RemoteUser        = $script:_RemoteUser
    $selectedAlias     = $script:_RemoteAlias
    $target            = Resolve-SSHTarget -RemoteHostAddress $RemoteHostAddress -RemoteUser $RemoteUser
    $idLookup          = if ($selectedAlias) { $selectedAlias } else { $RemoteHostAddress }
    Write-IdentityFiles $idLookup

    Write-Out 'dim' "Fetching authorized keys from $target..."
    Write-SSHFence $target
    try {
        $rawKeys = ssh $target "cat ~/.ssh/authorized_keys 2>/dev/null"
    } catch {
        Write-SSHFenceClose
        Write-Out 'error' "Could not connect to ${target}: $($_.Exception.Message)"
        return
    }
    Write-SSHFenceClose

    $remoteLines = @($rawKeys -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    if ($remoteLines.Count -eq 0) {
        Write-Out 'dim' "No authorized_keys found on $target."
        return
    }

    $sshDir      = "$env:USERPROFILE\.ssh"
    $matchedKeys = @()
    foreach ($pub in (Get-ChildItem -Path $sshDir -Filter "*.pub" -File -ErrorAction SilentlyContinue)) {
        $content = (Get-Content $pub.FullName -Raw -Encoding UTF8).Trim()
        if ($remoteLines -contains $content) {
            $matchedKeys += [pscustomobject]@{ KeyName = $pub.BaseName; PubPath = $pub.FullName; PubContent = $content }
        }
    }
    if ($matchedKeys.Count -eq 0) {
        Write-Out 'warn' "No local public keys found in $target authorized_keys."
        return
    }

    $labels   = @($matchedKeys | ForEach-Object { "$($_.KeyName)  ($($_.PubPath))" })
    $selected = Select-FromList -Items $labels -Prompt "Select key to remove from remote:" -StrictList
    if (-not $selected) { return }
    $pick     = $matchedKeys[$labels.IndexOf($selected)]

    $pubContent    = $pick.PubContent
    Write-Out 'warn' "Removing key '$($pick.KeyName)' from $target..."
    Write-SSHFence $target
    try {
        if (-not (Remove-RemotePublicKey -Target $target -PublicKey $pubContent)) { throw "ssh failed" }
        Write-SSHFenceClose
        Write-Out 'ok' "Key removed from remote authorized_keys."
    } catch {
        Write-SSHFenceClose
        Write-Out 'error' "Failed to remove key from remote."
        return
    }

    if ($selectedAlias) {
        Confirm-UserChoice -Message "  Remove IdentityFile '$($pick.KeyName)' from config block '$selectedAlias'?" -Action {
            Remove-IdentityFileFromConfigBlock -KeyName $pick.KeyName -HostAlias $selectedAlias
        } -DefaultAnswer "y"
    }

    $privPath = "$sshDir\$($pick.KeyName)"
    $pubPath  = "$privPath.pub"
    Confirm-UserChoice -Message "  Delete local key '$($pick.KeyName)' from this machine?" -Action {
        if (Test-Path $privPath) { Remove-Item $privPath -Force; Write-Out 'ok' "Deleted: $privPath" }
        if (Test-Path $pubPath)  { Remove-Item $pubPath  -Force; Write-Out 'ok' "Deleted: $pubPath"  }
    } -DefaultAnswer "n"
}

function _MenuPromoteKey {           # choice 4 — install new key, remove old in one operation
    Show-OpBanner @("host", $env:COMPUTERNAME)
    Deploy-PromotedKey
}

function _MenuGenerateKey {          # choice 5 — generate ED25519 pair locally without deploying
    Show-OpBanner @("host", $env:COMPUTERNAME)
    $KeyName = Read-NewSSHKeyName
    $Comment = Read-SSHKeyComment -DefaultComment "$KeyName$DefaultCommentSuffix"
    Add-SSHKeyInHost -KeyName $KeyName -Comment $Comment
}

function _MenuListKeys {             # choice 6 — show key inventory with fingerprints and host refs
    Show-SSHKeyInventory
    return $true
}

function _MenuAppendKeyToConfig {    # choice 7 — verify key works on remote, then add IdentityFile to host config block
    Show-OpBanner @("config", "$env:USERPROFILE\.ssh\config")
    $KeyName = Read-SSHKeyName
    Invoke-RemotePrompt
    $RemoteHostAddress = $script:_RemoteHost
    $RemoteUser        = $script:_RemoteUser
    $hostName          = if ($script:_RemoteAlias) { $script:_RemoteAlias } else { $script:_RemoteHost }
    $hostDisplay       = if ($hostName -ne $RemoteHostAddress) { "$hostName ($RemoteHostAddress)" } else { $hostName }

    $keyPath = "$env:USERPROFILE\.ssh\$KeyName"
    Write-SSHFence
    # Key auth only, but not BatchMode: that can't ask a passphrase, so protected keys never verified (R8).
    $testOut = & ssh -F NUL -i $keyPath -o IdentitiesOnly=yes -o PreferredAuthentications=publickey -o ConnectTimeout=6 `
                     -o StrictHostKeyChecking=accept-new "$RemoteUser@$RemoteHostAddress" "echo ok" 2>&1
    Write-SSHFenceClose

    if ($testOut -eq "ok") {
        Write-Out 'ok' "Key verified on $hostDisplay."
    } else {
        Write-Out 'warn' "Could not verify '$KeyName' on $hostDisplay — it may not be installed yet."
        # Same [y/N] question as everywhere else (was a pre-filled text prompt "(y/N): N").
        $script:_addAnyway = $false
        Confirm-UserChoice -Message "  Add it to the config anyway?" -Action { $script:_addAnyway = $true } -DefaultAnswer "n"
        if (-not $script:_addAnyway) { return }
    }
    Add-SSHKeyToHostConfig -KeyName $KeyName -RemoteHostName $hostName -RemoteHostAddress $RemoteHostAddress -RemoteUser $RemoteUser
}

function _MenuDeleteLocalKey {       # choice 8 — optionally remove from remote(s), then delete local key files
    Show-OpBanner @("ssh dir", "$env:USERPROFILE\.ssh")
    $KeyName = Read-SSHKeyName
    if (-not $KeyName) { return }

    $keyHosts = Get-HostsUsingKey -KeyName $KeyName

    if ($keyHosts.Count -gt 0) {
        # "None" first and highlighted (two Enters removed it from ALL hosts, then locally); Esc cancels.
        $noneLabel  = "-- None (keep it on remote hosts)"
        $allLabel   = "-- ALL  ($($keyHosts.Count) host$(if ($keyHosts.Count -ne 1){'s'}))"
        $hostLabels = @($noneLabel, $allLabel) + @($keyHosts | ForEach-Object {
            if ($_.HostName) { "$($_.Alias)  ($($_.HostName))" } else { $_.Alias }
        })
        $selectedHost = Select-FromList -Items $hostLabels -Prompt "Also remove it from remote host(s)?" -StrictList
        if ($selectedHost -eq $noneLabel) { $selectedHost = $null }

        $targetsToRemove = if ($selectedHost -and $selectedHost.StartsWith("-- ALL")) {
            $keyHosts
        } elseif ($selectedHost) {
            $alias = ($selectedHost -split '\s+\(')[0].Trim()
            @($keyHosts | Where-Object { $_.Alias -eq $alias })
        } else { @() }

        foreach ($h in $targetsToRemove) {
            $rUser = if ($h.User) { $h.User } else { $DefaultUserName }
            $rHost = if ($h.HostName) { $h.HostName } else { $h.Alias }
            Write-Out 'dim' "Removing key from $($h.Alias)..."
            Remove-SSHKeyFromRemote -RemoteUser $rUser -RemoteHost $rHost -KeyName $KeyName
        }
    } else {
        Write-Out 'dim' "No configured hosts reference this key."
    }

    $privPath = "$env:USERPROFILE\.ssh\$KeyName"
    $pubPath  = "$privPath.pub"
    # Error prevention (plan D3): deleting a private key can't be undone; default No.
    $script:_goDelete = $false
    Confirm-UserChoice -Message "  Delete $privPath and its .pub? This can't be undone." -Action { $script:_goDelete = $true } -DefaultAnswer "n"
    if (-not $script:_goDelete) { return }
    $deleted  = @()
    if (Test-Path $privPath) { Remove-Item $privPath -Force; $deleted += $privPath }
    if (Test-Path $pubPath)  { Remove-Item $pubPath  -Force; $deleted += $pubPath  }
    if ($deleted.Count -gt 0) {
        $deleted | ForEach-Object { Write-Out 'ok' "Deleted: $_" }
        Write-Out 'ok' "Key '$KeyName' removed locally."
    } else {
        Write-Out 'warn' "No local key files found for '$KeyName'."
    }
}

function _MenuRemoveKeyFromConfig {  # choice 9 — pick host then IdentityFile entry, remove that line from config block
    Show-OpBanner @("config", "$env:USERPROFILE\.ssh\config")
    $allHosts = Get-ConfiguredSSHHosts
    if ($allHosts.Count -eq 0) {
        Write-Out 'dim' "No configured hosts found in ~/.ssh/config."
        return
    }
    $hostName = Select-FromList -Items @($allHosts | ForEach-Object { $_.Alias }) -Prompt "Select host:" -StrictList
    if (-not $hostName) { return }

    $configRaw = Get-Content "$env:USERPROFILE\.ssh\config" -Raw -Encoding UTF8
    $block     = [regex]::Match($configRaw, (Get-HostBlockPattern $hostName)).Value
    $keyNames  = @([regex]::Matches($block, '(?m)^\s*IdentityFile\s+(.+?)\s*$') |
                   ForEach-Object { [System.IO.Path]::GetFileName($_.Groups[1].Value.Trim().Trim('"')) })

    if ($keyNames.Count -eq 0) {
        Write-Out 'dim' "No IdentityFile entries found under host '$hostName'."
        return
    }
    $KeyName = Select-FromList -Items $keyNames -Prompt "Select key to remove from '$hostName':"
    if (-not $KeyName) { return }

    Remove-IdentityFileFromConfigEntry -KeyName $KeyName -RemoteHostName $hostName
}

function _MenuShowBestPractices {    # choice 10 — 4-rule key-naming guide; no interactive input
    Write-Host ""
    Write-Out 'info' "Best Practices"
    Write-Out 'dim'  "--------------"
    Write-Out 'info' "1. CTs demo'd over LAN         -> shared key (e.g. demo-lan)"
    Write-Out 'info' "2. CTs in development over LAN -> shared key (e.g. dev-lan)"
    Write-Out 'info' "3. CTs promoted into the stack -> shared key (e.g. prod-lan)"
    Write-Out 'error' "4. CTs accessed over the WAN   -> individual key (e.g. sonarr-wan)"
}

function _MenuConfDefaults {         # choice 11 — inline TUI for editing DEFAULT_* globals; shows 4 copy-paste launch commands
    $fieldDefs = @(
        @{ Name = "DefaultUserName";      Label = "Default Username      " }
        @{ Name = "DefaultSubnetPrefix";  Label = "Default Subnet Prefix " }
        @{ Name = "DefaultCommentSuffix"; Label = "Default Comment Suffix" }
        @{ Name = "DefaultPassword";      Label = "Default Password      " }
    )
    $confSel = 0
    $confRun = $true
    [Console]::Write("`e[?25l")

    while ($confRun) {
        $tw = $Host.UI.RawUI.WindowSize.Width
        $th = $Host.UI.RawUI.WindowSize.Height
        $rule  = ([char]0x2500).ToString() * [Math]::Max(0, $tw - 4)
        $title = "Conf: Global Defaults"
        $tpad  = " " * [Math]::Max(0, [int](($tw - 4 - $title.Length) / 2))
        $tline = "  " + $tpad + $title
        $tfill = " " * [Math]::Max(0, $tw - $tline.Length)
        # Same teal title bar as every other PS operation screen (_InvokeMenuAction), TODO #5.
        $cf  = "`e[2J`e[H"
        $cf += "`e[2;1H  `e[96m$rule`e[0m`e[K"
        $cf += "`e[3;1H`e[48;5;23m`e[1;97m$tline$tfill`e[0m"
        $cf += "`e[4;1H  `e[96m$rule`e[0m`e[K"
        for ($i = 0; $i -lt $fieldDefs.Count; $i++) {
            $val  = (Get-Variable -Name $fieldDefs[$i].Name -Scope Script -ErrorAction SilentlyContinue).Value
            $disp = if ($fieldDefs[$i].Name -eq "DefaultPassword" -and $val) { "*" * $val.Length } else { $val }
            $row  = 6 + $i
            $cf  += "`e[$row;1H"
            if ($i -eq $confSel) {
                $cf += "  `e[7m  $($fieldDefs[$i].Label)  $disp`e[K`e[0m"
            } else {
                $cf += "  `e[0;37m    $($fieldDefs[$i].Label)  `e[90m$disp`e[0m`e[K"
            }
        }

        # ── Persist commands (4 methods) ────────────────────────────────────
        $rawUrl = "https://raw.githubusercontent.com/ahmadhadidi/sshdd/refs/heads/main"
        $bf = ""; $pf = ""
        $uVal = (Get-Variable -Name "DefaultUserName"      -Scope Script -EA SilentlyContinue).Value
        $sVal = (Get-Variable -Name "DefaultSubnetPrefix"  -Scope Script -EA SilentlyContinue).Value
        $cVal = (Get-Variable -Name "DefaultCommentSuffix" -Scope Script -EA SilentlyContinue).Value
        $pVal = (Get-Variable -Name "DefaultPassword"      -Scope Script -EA SilentlyContinue).Value
        if ($uVal) { $bf += " --user `"$uVal`"";           $pf += " -DefaultUserName `"$uVal`"" }
        if ($sVal) { $bf += " --subnet `"$sVal`"";         $pf += " -DefaultSubnetPrefix `"$sVal`"" }
        if ($cVal) { $bf += " --comment-suffix `"$cVal`""; $pf += " -DefaultCommentSuffix `"$cVal`"" }
        if ($pVal) { $bf += " --password `"$pVal`"";       $pf += " -DefaultPassword `"$pVal`"" }

        $maxCw = $tw - 6
        $c1 = "bash <(curl -fsSL $rawUrl/sshdd.sh)$bf"
        $c2 = "bash sshdd.sh$bf"
        $c3 = "`$sb=[scriptblock]::Create((irm `"$rawUrl/sshdd.ps1`")); & `$sb$pf"
        $c4 = "& ./sshdd.ps1$pf"
        if ($c1.Length -gt $maxCw) { $c1 = $c1.Substring(0, $maxCw - 3) + "..." }
        if ($c2.Length -gt $maxCw) { $c2 = $c2.Substring(0, $maxCw - 3) + "..." }
        if ($c3.Length -gt $maxCw) { $c3 = $c3.Substring(0, $maxCw - 3) + "..." }
        if ($c4.Length -gt $maxCw) { $c4 = $c4.Substring(0, $maxCw - 3) + "..." }

        $cf += "`e[11;1H`e[K"
        $cf += "`e[12;1H  `e[90mTo persist across sessions:`e[0m`e[K"
        $cf += "`e[13;1H`e[K"
        $cf += "`e[14;1H  `e[90m`u{2601}`u{FE0F}  Bash `u{00B7} cloud`e[0m`e[K"
        $cf += "`e[15;1H    `e[33m$c1`e[0m`e[K"
        $cf += "`e[16;1H  `e[90m`u{1F3E0}  Bash `u{00B7} local`e[0m`e[K"
        $cf += "`e[17;1H    `e[33m$c2`e[0m`e[K"
        $cf += "`e[18;1H`e[K"
        $cf += "`e[19;1H  `e[90m`u{2601}`u{FE0F}  PowerShell `u{00B7} cloud`e[0m`e[K"
        $cf += "`e[20;1H    `e[36m$c3`e[0m`e[K"
        $cf += "`e[21;1H  `e[90m`u{1F3E0}  PowerShell `u{00B7} local`e[0m`e[K"
        $cf += "`e[22;1H    `e[36m$c4`e[0m`e[K"

        $hint = "  Up/Dn  navigate     Enter  edit     Q  back  "
        $cf += "`e[$th;1H`e[7m$hint$(" " * [Math]::Max(0, $tw - $hint.Length))`e[0m"
        [Console]::Write($cf)

        try { $k = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") } catch { break }

        switch ($k.VirtualKeyCode) {
            38 { $confSel = ($confSel - 1 + $fieldDefs.Count) % $fieldDefs.Count }
            40 { $confSel = ($confSel + 1) % $fieldDefs.Count }
            13 {
                $row = 6 + $confSel
                [Console]::Write("`e[$row;1H`e[K  `e[1;33m> $($fieldDefs[$confSel].Label)  `e[0;33m")
                [Console]::Write("`e[?25h")
                $newVal = Read-Host
                [Console]::Write("`e[?25l")
                if (![string]::IsNullOrWhiteSpace($newVal)) {
                    Set-Variable -Name $fieldDefs[$confSel].Name -Value $newVal -Scope Script
                }
            }
        }
        if ($k.Character -eq 'q' -or $k.Character -eq 'Q') { $confRun = $false }
    }

    [Console]::Write("`e[?25h")
    Write-Host ""
    Write-Out 'ok'   "Defaults updated for this session."
    Write-Out 'warn' "To persist: pass as script parameters (-DefaultUserName, etc.)"
    return $true
}

function _MenuRemoveHost {           # choice 12 — remove entire Host block from ~/.ssh/config
    Remove-HostFromSSHConfig
}

function _MenuViewConfig {           # choice 13 — paginated SSH config viewer
    Show-SSHConfigFile
    return $true
}

function _MenuEditConfig {           # choice 14 — open config in editor
    Edit-SSHConfigFile
    return $true
}

function _MenuListAuthorizedKeys {   # choice 16 — SSH to target, fetch authorized_keys, display numbered list
    Show-OpBanner @("host", $env:COMPUTERNAME, "user", $DefaultUserName)
    Invoke-RemotePrompt
    $RemoteHostAddress = $script:_RemoteHost
    $RemoteUser        = $script:_RemoteUser
    $target = Resolve-SSHTarget -RemoteHostAddress $RemoteHostAddress -RemoteUser $RemoteUser
    $scope = Select-FromList -Items @("This user ($RemoteUser)", "All users (needs root or sudo)") `
                             -Prompt "List authorized keys of" -StrictList
    if (-not $scope) { return }
    if ($scope -like 'All*') { Write-AllAuthorizedKeys $target; return }
    Write-Out 'dim' "Fetching authorized_keys from $target..."
    Write-SSHFence $target
    try {
        $keys = ssh $target "cat ~/.ssh/authorized_keys 2>/dev/null"
        Write-SSHFenceClose
        if (-not $keys) {
            Write-Out 'dim' "No authorized_keys found on $target."
        } else {
            Write-Host "  `e[1;37mAuthorized keys on ${target}:`e[0m"
            $i = 1
            $keys -split "`n" | Where-Object { $_.Trim() } | ForEach-Object {
                Write-Host "  `e[90m$($i.ToString().PadLeft(3))`e[0m  `e[36m$_`e[0m"
                $i++
            }
        }
    } catch {
        Write-SSHFenceClose
        Write-Out 'error' "Failed to fetch authorized_keys: $($_.Exception.Message)"
    }
}

# Every user's ~/.ssh/authorized_keys (TODO #14), as root or through `sudo -n` (no tty for a password).
# Remote prints "U user path" per file, then "K line" per line; NOROOT (exit 4) when neither works.
# RemoteAkAll has no single quote: it goes into the command as s='...'.
$script:RemoteAkAll  = '{ getent passwd 2>/dev/null || cat /etc/passwd; } | while IFS=: read -r u _ _ _ _ h _; do f="$h/.ssh/authorized_keys"; [ -f "$f" ] || continue; echo "U $u $f"; sed "s/^/K /" "$f"; echo; done; true'
$script:RemoteAkRoot = 'if [ "$(id -u)" = 0 ]; then sh -c "$s"; elif sudo -n true 2>/dev/null; then sudo -n sh -c "$s"; else echo NOROOT; exit 4; fi'

function Write-AllAuthorizedKeys {
    param([string]$Target)
    Write-Out 'dim' "Fetching every user's authorized_keys from $Target..."
    Write-SSHFence $Target
    $out = @(ssh $Target (ConvertTo-NativeArgument "s='$($script:RemoteAkAll)'; $($script:RemoteAkRoot)") 2>&1 | ForEach-Object { "$_".TrimEnd("`r") })
    $rc = $LASTEXITCODE
    Write-SSHFenceClose
    if ($rc -ne 0) {
        if ($out -contains 'NOROOT') { Write-Out 'error' "All users needs root or passwordless sudo on $Target." }
        else { Write-Out 'error' "Failed to fetch authorized_keys."; Write-Out 'dim' "ssh: $($out | Select-Object -Last 1)" }
        return
    }
    Write-Host "  `e[1;37mAuthorized keys on ${Target}:`e[0m"
    $i = 1; $pend = $null; $any = $false
    foreach ($line in $out) {
        if ($line.StartsWith('U ')) {
            if ($pend) { Write-Host "$pend  `e[90m(none)`e[0m" }
            $u, $p = $line.Substring(2) -split ' ', 2
            $pend = "`n  `e[1;97m$u`e[0m  `e[90m$p`e[0m"; $any = $true
        } elseif ($line.StartsWith('K ') -and $line.Substring(2).Trim()) {
            if ($pend) { Write-Host $pend; $pend = $null }
            Write-Host "  `e[90m$($i.ToString().PadLeft(5))`e[0m  `e[36m$($line.Substring(2))`e[0m"
            $i++
        }
    }
    if ($pend) { Write-Host "$pend  `e[90m(none)`e[0m" }
    if (-not $any) { Write-Out 'dim' "No authorized_keys found on $Target." }
}

# ── known_hosts (TODO #15) ────────────────────────────────────────────────────
# Remote side: the SSH user's ~/.ssh/known_hosts. Host names come on stdin, never in the command;
# CR is stripped because PS 5.1 pipes text with CRLF.
$script:RemoteKhLookup = 'f=$HOME/.ssh/known_hosts; [ -s "$f" ] || exit 0; command -v ssh-keygen >/dev/null || { echo "ssh-keygen not found on the remote host" >&2; exit 3; }; tr -d ''\r'' | while read -r n; do ssh-keygen -l -F "$n" -f "$f"; done; true'
$script:RemoteKhList   = 'f=$HOME/.ssh/known_hosts; [ -s "$f" ] || exit 0; command -v ssh-keygen >/dev/null || { echo "ssh-keygen not found on the remote host" >&2; exit 3; }; ssh-keygen -lf "$f"; echo --; tr -d ''\r'' | while read -r n; do ssh-keygen -l -F "$n" -f "$f"; done; true'
# "done" only when no plain entry for any name is left (ssh-keygen -R keeps @cert-authority/@revoked lines).
$script:RemoteKhForget = 'f=$HOME/.ssh/known_hosts; tr -d ''\r'' | { rc=0; while read -r n; do ssh-keygen -R "$n" -f "$f" >/dev/null 2>&1; ssh-keygen -F "$n" -f "$f" 2>/dev/null | grep -q "found: line [0-9]* *$" && rc=1; done; [ $rc = 0 ] && echo done; }'

function _MenuListKnownHosts {       # choice 19 — local ~/.ssh/known_hosts with fingerprints
    $f = Join-Path $env:USERPROFILE ".ssh/known_hosts"
    Show-OpBanner @("file", $f)
    if (-not (Test-Path -LiteralPath $f) -or (Get-Item -LiteralPath $f).Length -eq 0) {
        Write-Out 'dim' "No known hosts in $f."
        return
    }
    $lookups = @(Get-ConfigHostKeyNames | ForEach-Object { ssh-keygen -l -F $_ -f $f 2>$null })
    Write-Host "  `e[1;37mKnown hosts in ${f}:`e[0m"
    if (-not (Write-KnownHostsList -Listing @(ssh-keygen -lf $f 2>$null) -Lookups $lookups)) { Write-Out 'dim' "No valid entries." }
}

function _MenuForgetHostKey {        # choice 20 — remove a host's keys from local known_hosts
    Show-OpBanner @("file", (Join-Path $env:USERPROFILE ".ssh/known_hosts"))
    $h = Read-RemoteHostAddress -SubnetPrefix $DefaultSubnetPrefix
    $target = if ($script:_LastSelectedAlias) { $script:_LastSelectedAlias } else { $h }
    $hk = Resolve-HostKeyName $target
    $known = @(Get-KnownHostKeys $hk)
    if (-not $known) { Write-Out 'dim' "No known host keys for $($hk.Name)."; return }
    Write-Out 'plain' "Known keys for $($hk.Name):"
    $known | ForEach-Object { Write-Out 'dim' (Format-KnownHostKey $_) }
    $null = Confirm-UserChoice -Message "Forget these keys?" -DefaultAnswer 'n' -Action { $null = Remove-KnownHostKeys $hk }
}

function _MenuListRemoteKnownHosts { # choice 21 — the remote user's ~/.ssh/known_hosts
    Show-OpBanner @("host", $env:COMPUTERNAME, "user", $DefaultUserName)
    Invoke-RemotePrompt
    $target = Resolve-SSHTarget -RemoteHostAddress $script:_RemoteHost -RemoteUser $script:_RemoteUser
    Write-Out 'dim' "Fetching known_hosts from $target..."
    $OutputEncoding = [System.Text.UTF8Encoding]::new($false)
    Write-SSHFence $target
    $out = @(Get-ConfigHostKeyNames | ssh $target (ConvertTo-NativeArgument $script:RemoteKhList) 2>&1)
    $rc = $LASTEXITCODE
    Write-SSHFenceClose
    if ($rc -ne 0) { Write-Out 'error' "Failed to fetch known_hosts."; Write-Out 'dim' "ssh: $($out | Select-Object -Last 1)"; return }
    if (-not $out) { Write-Out 'dim' "No known_hosts on $target."; return }
    $sep = [array]::IndexOf([string[]]$out, '--')
    $listing = if ($sep -ge 0) { $out[0..($sep - 1)] } else { $out }
    $lookups = if ($sep -ge 0 -and $sep -lt $out.Count - 1) { $out[($sep + 1)..($out.Count - 1)] } else { @() }
    Write-Host "  `e[1;37mKnown hosts on ${target}:`e[0m"
    if (-not (Write-KnownHostsList -Listing $listing -Lookups $lookups)) { Write-Out 'dim' "No valid entries." }
}

function _MenuForgetRemoteHostKey {  # choice 22 — remove a host's keys from the remote user's known_hosts
    Show-OpBanner @("host", $env:COMPUTERNAME, "user", $DefaultUserName)
    Invoke-RemotePrompt
    $target = Resolve-SSHTarget -RemoteHostAddress $script:_RemoteHost -RemoteUser $script:_RemoteUser
    Write-Out 'plain' "Host to forget on ${target}:"
    $h = Read-RemoteHostAddress -SubnetPrefix $DefaultSubnetPrefix
    $alias = $script:_LastSelectedAlias
    $hk = Resolve-HostKeyName $(if ($alias) { $alias } else { $h })
    $names = @($hk.Name)
    if ($alias -and $alias -ne $hk.Name) { $names += $alias }
    $OutputEncoding = [System.Text.UTF8Encoding]::new($false)
    Write-SSHFence $target
    $out = @($names | ssh $target (ConvertTo-NativeArgument $script:RemoteKhLookup) 2>&1)
    $rc = $LASTEXITCODE
    Write-SSHFenceClose
    if ($rc -ne 0) { Write-Out 'error' "Failed to read known_hosts on $target."; Write-Out 'dim' "ssh: $($out | Select-Object -Last 1)"; return }
    $plain = $false   # entry after "# Host x found: line N" (not "... line N CA" / "REVOKED")
    $found = @(foreach ($l in $out) {
        if ("$l" -like '# Host *') { $plain = "$l" -match 'found: line \d+\s*$'; continue }
        $q = "$l".Trim() -split '\s+'
        if ($plain -and $q.Count -ge 3) { $l }
    })
    $shown = $names -join ', '
    if (-not $found) { Write-Out 'dim' "No known host keys for $shown on $target."; return }
    Write-Out 'plain' "Known keys for $shown on ${target}:"
    foreach ($l in $found) { $q = "$l".Trim() -split '\s+'; Write-Out 'dim' "$($q[1].PadRight(8)) $($q[2])  ($($q[0]))" }
    $resp = Read-ColoredInput -Prompt "Forget these keys on $target? [y/N]" -ForegroundColor "Cyan"
    if ($resp -notmatch '^(y|yes)$') { Write-Host "  Action cancelled." -ForegroundColor Yellow; return }
    Write-SSHFence $target
    $out = @($names | ssh $target (ConvertTo-NativeArgument $script:RemoteKhForget) 2>&1)
    Write-SSHFenceClose
    if ($out -contains 'done') { Write-Out 'ok' "Removed $($found.Count) key(s) from ${target}:~/.ssh/known_hosts (backup: known_hosts.old)." }
    else { Write-Out 'error' "Failed to edit known_hosts on $target."; Write-Out 'dim' "ssh: $($out | Select-Object -Last 1)" }
}

function _MenuAddConfigBlock {       # choice 17 — read remote auth_keys, create host config entry
    Show-OpBanner @("host", $env:COMPUTERNAME, "config", "$env:USERPROFILE\.ssh\config")
    Register-RemoteHostConfig
}

function _MenuImportKey {            # choice 18 — import from local path, SCP, or paste
    Show-OpBanner @("host", $env:COMPUTERNAME, "ssh dir", "$env:USERPROFILE\.ssh")
    Import-ExternalSSHKey
}
