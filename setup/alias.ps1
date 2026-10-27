# sshdd alias setup for Windows PowerShell and pwsh (TODO #29). Writes a `function sshdd` into $PROFILE.
#
#   & ([scriptblock]::Create((irm https://raw.githubusercontent.com/ahmadhadidi/sshdd/refs/heads/main/setup/alias.ps1))) `
#     [-User NAME] [-Subnet PREFIX] [-CommentSuffix STR] [-Password PASS]
#
# Values not passed are asked for (Enter keeps the [default]); the password prompt is hidden.
# Defaults come from this machine: your user name, the subnet of the IP on the default route, the short hostname.
# Local if $HOME\sshdd\sshdd.ps1 exists, else the cloud script. A rerun replaces the marked block;
# the old profile is kept as $PROFILE.sshdd-bak.
param(
    [string]$User,
    [string]$Subnet,
    [string]$CommentSuffix,
    [string]$Password,
    [switch]$NoMouse        # the function starts sshdd without mouse capture (#42)
)
$ErrorActionPreference = 'Stop'

# The default in cyan, like the app; Enter keeps it.
function Ask([string]$Prompt, [string]$Default) {
    Write-Host -NoNewline "$Prompt ["
    Write-Host -NoNewline $Default -ForegroundColor Cyan
    Write-Host -NoNewline ']: '
    $a = [Console]::ReadLine()
    if ($a) { $a } else { $Default }
}

# First three parts of this machine's IP on the default route (192.168.0.190 -> 192.168.0), else 192.168.0.
# Connecting a UDP socket only picks the route; nothing is sent.
function Get-DefaultSubnet {
    try {
        $s = [System.Net.Sockets.Socket]::new('InterNetwork', 'Dgram', 'Udp')
        $s.Connect('1.1.1.1', 53)
        $ip = $s.LocalEndPoint.Address.ToString()
        $s.Dispose()
        if ($ip -match '^(\d+\.\d+\.\d+)\.\d+$' -and $ip -ne '0.0.0.0') { return $Matches[1] }
    } catch { }
    '192.168.0'
}

$asking = -not ($PSBoundParameters.ContainsKey('User') -and $PSBoundParameters.ContainsKey('Subnet') -and
                $PSBoundParameters.ContainsKey('CommentSuffix') -and $PSBoundParameters.ContainsKey('Password'))
if ($asking) { 'sshdd alias setup (Enter keeps the [default])' }
$hostShort = [Environment]::MachineName.Split('.')[0]
if (-not $PSBoundParameters.ContainsKey('User'))          { $User          = Ask 'Default remote username' ([Environment]::UserName) }
if (-not $PSBoundParameters.ContainsKey('Subnet'))        { $Subnet        = Ask 'Subnet prefix' (Get-DefaultSubnet) }
if (-not $PSBoundParameters.ContainsKey('CommentSuffix')) { $CommentSuffix = Ask 'Key comment suffix' "-[$hostShort]" }
if (-not $PSBoundParameters.ContainsKey('Password')) {
    $secure   = Read-Host 'SSH password (hidden, Enter = ask each time)' -AsSecureString
    $Password = [System.Net.NetworkCredential]::new('', $secure).Password
}

# Single-quote a value for PowerShell: any character is safe, ' becomes ''.
function Q([string]$v) { "'" + $v.Replace("'", "''") + "'" }

$local = Join-Path (Join-Path $HOME 'sshdd') 'sshdd.ps1'
if (Test-Path $local) {
    $kind = 'local'
    $run  = "& $(Q $local)"
} else {
    $kind = 'cloud'
    $run  = '& ([scriptblock]::Create((irm "https://raw.githubusercontent.com/ahmadhadidi/sshdd/refs/heads/main/sshdd.ps1")))'
}

$params = "-DefaultUserName $(Q $User) -DefaultSubnetPrefix $(Q $Subnet) -DefaultCommentSuffix $(Q $CommentSuffix)"
if ($Password) { $params += " -DefaultPassword $(Q $Password)" }
if ($NoMouse)  { $params += " -NoMouse" }

New-Item -ItemType Directory -Force -Path (Split-Path $PROFILE) | Out-Null
$old = ''
if (Test-Path $PROFILE) {
    $old = [string](Get-Content -Raw $PROFILE)
    Copy-Item $PROFILE "$PROFILE.sshdd-bak"
}
$old = [regex]::Replace($old, '(?s)# >>> sshdd >>>.*?# <<< sshdd <<<\r?\n?', '')
$block = @(
    '# >>> sshdd >>>'
    "function sshdd { $run $params @args }"
    '# <<< sshdd <<<'
) -join "`n"
# UTF-8 with BOM: Windows PowerShell 5.1 reads a profile without one as ANSI (a non-ASCII suffix would break).
[System.IO.File]::WriteAllText($PROFILE, $old + $block + "`n", [System.Text.UTF8Encoding]::new($true))

"sshdd function ($kind) written to $PROFILE (backup: $PROFILE.sshdd-bak)"
if ($Password) { "Note: the password is stored in plain text in $PROFILE." }
@'
Open a new PowerShell window, then run:  sshdd
'@
