# lib/ps/tui.ps1 — TUI helpers: Wait-UserAcknowledge, Show-Paged, Select-FromList, Format-MenuLabel
# EXPORTS: Wait-UserAcknowledge  Show-Paged  Select-FromList
#          Select-MultiFromList  Format-MenuLabel  Read-TuiKey  Enable-TuiMouse  Disable-TuiMouse

# ─── Mouse (TODO #42, like bash #41 / herdr) ──────────────────────────────────
# Read-TuiKey returns the key like ReadKey, or for the mouse an object with Click = $true and Col / Row
# (1-based screen cell); the wheel comes back as Up / Down (VirtualKeyCode 38 / 40); releases and
# right/middle clicks are skipped. Capture is on only while a screen calls Read-TuiKey -Mouse (or the
# main menu holds it), so ssh, editors and text prompts never get click codes.
# macOS/Linux: the terminal sends SGR reports (ESC [ < b ; col ; row M) that ReadKey returns one
# character at a time. Windows: mouse input arrives as separate console records ReadKey never returns,
# so a small C# reader (ReadConsoleInput) is used while capturing; QuickEdit is off only then.
$script:SshddMouse = $false   # sshdd.ps1 sets it (on unless -NoMouse)
$script:IsWin      = ($PSVersionTable.PSEdition -eq 'Desktop') -or $IsWindows
$script:WinConsole = $null     # $true once the C# reader compiled, $false if it can't

function Test-WinConsole {
    if ($null -ne $script:WinConsole) { return $script:WinConsole }
    try {
        Add-Type -ErrorAction Stop -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class SshddConsole {
    [StructLayout(LayoutKind.Explicit, CharSet = CharSet.Unicode)]
    struct INPUT_RECORD {
        [FieldOffset(0)] public ushort EventType;
        [FieldOffset(4)] public int KeyDown;          // KEY_EVENT_RECORD
        [FieldOffset(10)] public ushort VirtualKeyCode;
        [FieldOffset(14)] public char UnicodeChar;
        [FieldOffset(16)] public uint KeyControlState;
        [FieldOffset(4)] public short X;              // MOUSE_EVENT_RECORD
        [FieldOffset(6)] public short Y;
        [FieldOffset(8)] public uint ButtonState;
        [FieldOffset(16)] public uint EventFlags;
    }
    [DllImport("kernel32.dll")] static extern IntPtr GetStdHandle(int h);
    [DllImport("kernel32.dll")] static extern bool GetConsoleMode(IntPtr h, out uint m);
    [DllImport("kernel32.dll")] static extern bool SetConsoleMode(IntPtr h, uint m);
    [DllImport("kernel32.dll")] static extern bool GetNumberOfConsoleInputEvents(IntPtr h, out uint n);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
    static extern bool ReadConsoleInputW(IntPtr h, [Out] INPUT_RECORD[] b, uint len, out uint read);
    static uint saved; static bool on;
    static IntPtr In { get { return GetStdHandle(-10); } }
    public static void MouseOn() {
        uint m; if (on || !GetConsoleMode(In, out m)) return;
        saved = m; on = true;
        SetConsoleMode(In, (m | 0x0010 | 0x0080) & ~0x0040u);   // + MOUSE_INPUT + EXTENDED_FLAGS, - QUICK_EDIT
    }
    public static void MouseOff() { if (on) { SetConsoleMode(In, saved); on = false; } }
    public static bool Available() { uint n; return GetNumberOfConsoleInputEvents(In, out n) && n > 0; }
    // Kind: 1 key (Vk, Ch, Ctrl), 2 left press (X, Y), 3 wheel up, 4 wheel down, 0 nothing to report.
    public static int[] Read() {
        var b = new INPUT_RECORD[1]; uint r;
        if (!ReadConsoleInputW(In, b, 1, out r) || r == 0) return new int[] { 0, 0, 0, 0, 0, 0 };
        var e = b[0];
        if (e.EventType == 1 && e.KeyDown != 0)
            return new int[] { 1, e.VirtualKeyCode, e.UnicodeChar, (int)e.KeyControlState, 0, 0 };
        if (e.EventType == 2) {
            if (e.EventFlags == 4) return new int[] { ((int)e.ButtonState) > 0 ? 3 : 4, 0, 0, 0, e.X, e.Y };   // MOUSE_WHEELED
            if (e.EventFlags == 0 && (e.ButtonState & 1) != 0) return new int[] { 2, 0, 0, 0, e.X, e.Y };   // left press
        }
        return new int[] { 0, 0, 0, 0, 0, 0 };
    }
}
'@
        $script:WinConsole = $true
    } catch { $script:WinConsole = $false }
    return $script:WinConsole
}

function Enable-TuiMouse {
    if (-not $script:SshddMouse) { return }
    if ($script:IsWin) { if (Test-WinConsole) { [SshddConsole]::MouseOn() } }
    else { [Console]::Write("`e[?1000h`e[?1006h") }
}

function Disable-TuiMouse {   # always: -NoMouse may have come later (F10)
    if ($script:IsWin) { if ($script:WinConsole) { [SshddConsole]::MouseOff() } }
    else { [Console]::Write("`e[?1006l`e[?1000l") }
}

function Test-TuiInput {   # a key (or, on Windows while capturing, a mouse record) is waiting
    if ($script:IsWin -and $script:SshddMouse -and $script:WinConsole) { return [SshddConsole]::Available() }
    try { return $Host.UI.RawUI.KeyAvailable } catch { return $false }
}

function New-TuiMouseKey([int]$Vk, [bool]$Click, [int]$Col, [int]$Row) {
    [pscustomobject]@{ VirtualKeyCode = $Vk; Character = [char]0; ControlKeyState = 0; Click = $Click; Col = $Col; Row = $Row }
}

function Read-TuiKey {
    param([switch]$Mouse)   # -Mouse: capture while waiting (screens); the main menu holds capture itself
    if ($Mouse) { Enable-TuiMouse }
    try {
        while ($true) {
            if ($script:IsWin -and $script:SshddMouse -and $script:WinConsole) {
                $r = [SshddConsole]::Read()
                switch ($r[0]) {
                    1 { return [pscustomobject]@{ VirtualKeyCode = $r[1]; Character = [char]$r[2]; ControlKeyState = $r[3]; Click = $false } }
                    2 { return New-TuiMouseKey 0 $true ($r[4] + 1) ($r[5] - $Host.UI.RawUI.WindowPosition.Y + 1) }
                    3 { return New-TuiMouseKey 38 $false 0 0 }
                    4 { return New-TuiMouseKey 40 $false 0 0 }
                }
                continue
            }
            $k = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
            if ($k.VirtualKeyCode -ne 27 -or -not (Test-TuiInput)) { return $k }   # not ESC + more: a key (bare Esc too)
            $c = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown").Character
            if ($c -ne '[') { return $k }                         # Esc pressed with another key close behind
            $s = ''
            while ((Test-TuiInput) -and $s.Length -lt 24) {        # rest of the sequence, up to its final byte
                $ch = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown").Character
                $s += $ch
                if ($ch -match '[A-Za-z~]') { break }
            }
            if ($s -notmatch '^<(\d+);(\d+);(\d+)([Mm])$' -or -not $script:SshddMouse) { continue }   # other / unwanted
            if ($Matches[4] -ceq 'm') { continue }                 # release (-ceq: -eq ignores case, M is a press)
            $btn = [int]$Matches[1] -band (-bnot 28)               # without Shift/Alt/Ctrl
            switch ($btn) {
                0  { return New-TuiMouseKey 0 $true ([int]$Matches[2]) ([int]$Matches[3]) }
                64 { return New-TuiMouseKey 38 $false 0 0 }
                65 { return New-TuiMouseKey 40 $false 0 0 }
            }
        }
    } finally { if ($Mouse) { Disable-TuiMouse } }
}

function Wait-UserAcknowledge {
    $h = $Host.UI.RawUI.WindowSize.Height
    $w = $Host.UI.RawUI.WindowSize.Width
    $msg = "  Press any key to return to menu  "
    [Console]::Write("`e[$h;1H`e[7m$msg$(" " * [Math]::Max(0, $w - $msg.Length))`e[0m")
    $modifierVKs = @(16, 17, 18, 20, 91, 92, 93, 144, 145)
    try {
        do {
            $k = Read-TuiKey -Mouse   # a click counts as a key (#42)
        } while ($modifierVKs -contains $k.VirtualKeyCode)
    } catch {
        $null = Read-Host
    }
}


function Show-Paged {
    param([string[]]$Lines)

    try { $pageSize = [Math]::Max(5, $Host.UI.RawUI.WindowSize.Height - 4) }
    catch { $pageSize = 20 }

    $total = $Lines.Count
    $i = 0

    while ($i -lt $total) {
        $end = [Math]::Min($i + $pageSize - 1, $total - 1)
        $Lines[$i..$end] | ForEach-Object { Write-Host $_ }
        $i += $pageSize

        if ($i -lt $total) {
            Write-Host "-- $i/$total lines shown | Enter=more, Q=quit --" -ForegroundColor DarkGray -NoNewline
            try {
                do { $key = Read-TuiKey -Mouse } while ($key.Click -or $key.VirtualKeyCode -eq 38)   # wheel down = more (#42)
                Write-Host ""
                if ($key.Character -eq 'q' -or $key.Character -eq 'Q') { break }
            } catch {
                $null = Read-Host
            }
        }
    }
}


function Select-FromList {
    # Combo-box: Up/Dn navigates list, typing filters/creates new entry, Enter selects, Esc cancels.
    # -StrictList: Enter only accepts a highlighted list item (or sole match); disallows free text.
    param(
        [string[]]$Items,
        [string]$Prompt = "Select",
        [switch]$StrictList
    )
    if (-not $Items -or $Items.Count -eq 0) { return $null }

    $tw  = $Host.UI.RawUI.WindowSize.Width
    $th  = $Host.UI.RawUI.WindowSize.Height
    try { $startRow = [Console]::CursorTop + 3 } catch { $startRow = 8 }
    $maxVis  = [Math]::Max(1, $th - $startRow - 2)
    $sel     = -1    # -1 = cursor in text input, >=0 = list item highlighted
    $viewOff = 0
    $filter  = ""
    $filtered = $Items

    [Console]::Write("`e[?25l")

    while ($true) {
        # Re-filter list
        $filtered = if ($filter) { @($Items | Where-Object { $_ -like "*$filter*" }) } else { $Items }
        if ($sel -ge $filtered.Count) { $sel = $filtered.Count - 1 }
        if ($sel -lt $viewOff -and $sel -ge 0) { $viewOff = $sel }
        elseif ($sel -ge 0 -and $sel -ge $viewOff + $maxVis) { $viewOff = $sel - $maxVis + 1 }
        # Never scrolled past the end (filter typed after scrolling left nothing drawn, plan S9).
        if ($viewOff -gt $filtered.Count - $maxVis) { $viewOff = $filtered.Count - $maxVis }
        if ($viewOff -lt 0) { $viewOff = 0 }

        $promptRow = $startRow - 2
        $inputRow  = $startRow - 1
        $inputDisp = if ($filter) { "`e[37m$filter`e[90m|`e[0m" } else { "`e[90m(type to filter or create new)`e[0m" }
        $f  = "`e[$promptRow;1H`e[K  `e[90m$Prompt`e[0m"
        $f += "`e[$inputRow;1H`e[K  `e[36m>`e[0m $inputDisp"
        for ($i = 0; $i -lt $maxVis; $i++) {
            $idx = $viewOff + $i
            $r   = $startRow + $i
            $f  += "`e[$r;1H`e[K"
            if ($idx -lt $filtered.Count) {
                if ($idx -eq $sel) { $f += "`e[7m  > $($filtered[$idx])`e[K`e[0m" }
                else               { $f += "  `e[37m  $($filtered[$idx])`e[0m" }
            }
        }
        $up   = if ($viewOff -gt 0)                           { "^ " } else { "  " }
        $dn   = if ($viewOff + $maxVis -lt $filtered.Count)   { "v " } else { "  " }
        $hint = "  Up/Dn  navigate     Enter  select     type  filter / new name     Esc  cancel    $up$dn"
        $f   += "`e[$th;1H`e[7m$hint$(" " * [Math]::Max(0, $tw - $hint.Length))`e[0m"
        [Console]::Write($f)

        try { $k = Read-TuiKey -Mouse } catch { break }
        if ($k.Click) {   # a click on an entry chooses it, like Enter (#42)
            $mi = $k.Row - $startRow
            if ($mi -lt 0 -or $mi -ge $maxVis -or $viewOff + $mi -ge $filtered.Count) { continue }
            $sel = $viewOff + $mi
            $k = [pscustomobject]@{ VirtualKeyCode = 13; Character = [char]13; Click = $false }
        }

        $clr = ""; for ($ci = $promptRow; $ci -lt [Math]::Min($startRow + $maxVis + 1, $th); $ci++) { $clr += "`e[$ci;1H`e[K" }

        switch ($k.VirtualKeyCode) {
            38 {  # Up
                if ($sel -gt 0) { $sel-- }
                elseif ($sel -eq 0) { $sel = -1 }
            }
            40 {  # Down
                if ($sel -eq -1 -and $filtered.Count -gt 0) { $sel = 0 }
                elseif ($sel -lt $filtered.Count - 1) { $sel++ }
            }
            8 {  # Backspace
                if ($filter.Length -gt 0) { $filter = $filter.Substring(0, $filter.Length - 1); $sel = -1 }
            }
            13 {  # Enter
                $chosen = if ($sel -ge 0 -and $sel -lt $filtered.Count) {
                              $filtered[$sel]
                          } elseif ($StrictList) {
                              if ($filtered.Count -eq 1) { $filtered[0] } else { $null }
                          } elseif ($filter) {
                              $filter
                          } else { $null }
                if ($null -eq $chosen -and $StrictList) { break }
                [Console]::Write($clr + "`e[$th;1H`e[K")
                if ($chosen) { [Console]::Write("`e[$promptRow;1H  `e[90m$Prompt`e[0m  `e[36m$chosen`e[0m`n`e[?25h") }
                else         { [Console]::Write("`e[$promptRow;1H`e[?25h") }
                return $chosen
            }
            27 {  # Esc — cancel entire operation, unwind to menu
                [Console]::Write($clr + "`e[$th;1H`e[K`e[$promptRow;1H`e[?25h")
                throw [System.OperationCanceledException]::new("ESC")
            }
        }

        # Printable character → append to filter
        if ([int]$k.Character -ge 32) { $filter += $k.Character; $sel = -1 }
    }

    [Console]::Write("`e[?25h")
    return $null
}


function Select-MultiFromList {
    # Checkbox list: Space toggles, Enter confirms (returns [string[]], may be empty), Esc cancels.
    param(
        [string[]]$Items,
        [string]$Prompt = "Select"
    )
    if (-not $Items -or $Items.Count -eq 0) { return @() }

    $tw      = $Host.UI.RawUI.WindowSize.Width
    $th      = $Host.UI.RawUI.WindowSize.Height
    try { $startRow = [Console]::CursorTop + 3 } catch { $startRow = 8 }
    $maxVis  = [Math]::Max(1, $th - $startRow - 2)
    $sel     = 0
    $viewOff = 0
    $checked = [bool[]]::new($Items.Count)

    [Console]::Write("`e[?25l")

    while ($true) {
        # Clamp viewport
        if ($sel -lt $viewOff) { $viewOff = $sel }
        elseif ($sel -ge $viewOff + $maxVis) { $viewOff = $sel - $maxVis + 1 }
        # Never scrolled past the end (filter typed after scrolling left nothing drawn, plan S9).
        if ($viewOff -gt $Items.Count - $maxVis) { $viewOff = $Items.Count - $maxVis }
        if ($viewOff -lt 0) { $viewOff = 0 }

        $promptRow = $startRow - 2
        $f  = "`e[$promptRow;1H`e[K  `e[90m$Prompt`e[0m"
        $f += "`e[$($startRow - 1);1H`e[K  `e[36m>`e[0m `e[90m(Space toggle, Enter confirm, Esc cancel)`e[0m"
        for ($i = 0; $i -lt $maxVis; $i++) {
            $idx = $viewOff + $i
            $r   = $startRow + $i
            $f  += "`e[$r;1H`e[K"
            if ($idx -lt $Items.Count) {
                $box = if ($checked[$idx]) { "`e[32m[`u{2713}]`e[0m" } else { "`e[90m[ ]`e[0m" }
                if ($idx -eq $sel) {
                    $f += "`e[48;5;6m`e[1;97m  $box  $($Items[$idx])`e[K`e[0m"
                } else {
                    $f += "  $box  `e[37m$($Items[$idx])`e[0m"
                }
            }
        }
        $up   = if ($viewOff -gt 0)                          { "^ " } else { "  " }
        $dn   = if ($viewOff + $maxVis -lt $Items.Count)     { "v " } else { "  " }
        $hint = "  Up/Dn  navigate     Space  toggle     Enter  confirm     Esc  cancel    $up$dn"
        $f   += "`e[$th;1H`e[7m$hint$(" " * [Math]::Max(0, $tw - $hint.Length))`e[0m"
        [Console]::Write($f)

        try { $k = Read-TuiKey -Mouse } catch { break }
        if ($k.Click) {   # a click on an entry toggles it, like Space (#42)
            $mi = $k.Row - $startRow
            if ($mi -lt 0 -or $mi -ge $maxVis -or $viewOff + $mi -ge $Items.Count) { continue }
            $sel = $viewOff + $mi
            $k = [pscustomobject]@{ VirtualKeyCode = 32; Character = ' '; Click = $false }
        }

        $clr = ""
        for ($ci = $promptRow; $ci -lt [Math]::Min($startRow + $maxVis + 1, $th); $ci++) {
            $clr += "`e[$ci;1H`e[K"
        }

        switch ($k.VirtualKeyCode) {
            38 {  # Up
                if ($sel -gt 0) { $sel-- }
                else { $sel = $Items.Count - 1 }
            }
            40 {  # Down
                if ($sel -lt $Items.Count - 1) { $sel++ }
                else { $sel = 0 }
            }
            32 {  # Space — toggle
                $checked[$sel] = -not $checked[$sel]
            }
            13 {  # Enter — confirm
                [Console]::Write($clr + "`e[$th;1H`e[K`e[$promptRow;1H`e[?25h")
                $result = @()
                for ($i = 0; $i -lt $Items.Count; $i++) {
                    if ($checked[$i]) { $result += $Items[$i] }
                }
                return $result
            }
            27 {  # Esc — cancel
                [Console]::Write($clr + "`e[$th;1H`e[K`e[$promptRow;1H`e[?25h")
                throw [System.OperationCanceledException]::new("ESC")
            }
        }
    }

    [Console]::Write("`e[?25h")
    return @()
}


function Format-MenuLabel {
    param([string]$Label, [string]$Hotkey)
    if (-not $Hotkey) { return $Label }
    [regex]::Replace($Label, "(?i)($([regex]::Escape($Hotkey)))", "`e[1;4m`$1`e[0;37m", 1)
}
