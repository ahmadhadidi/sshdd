# sshdd #48 (manual, Windows only): which mouse events does this Windows console give a program? Run in PowerShell (Windows Terminal
# and/or the classic console), then click a few times, scroll and right-click during each 10-second pass.
#   Pass 1: Windows console mouse records (what sshdd uses now).   Pass 2: VT mouse mode (escape sequences).
# Copy everything it prints back to Claude.
# Run: irm https://raw.githubusercontent.com/ahmadhadidi/sshdd/refs/heads/main/tests/manual/windows-mouse-diag.ps1 | iex
Add-Type -TypeDefinition @'
using System; using System.Runtime.InteropServices;
public static class Diag {
    [StructLayout(LayoutKind.Explicit, CharSet = CharSet.Unicode)] public struct R {
        [FieldOffset(0)] public ushort T; [FieldOffset(4)] public int Down; [FieldOffset(10)] public ushort Vk;
        [FieldOffset(14)] public char Ch; [FieldOffset(4)] public short X; [FieldOffset(6)] public short Y;
        [FieldOffset(8)] public uint Btn; [FieldOffset(16)] public uint Flags; }
    [DllImport("kernel32.dll")] public static extern IntPtr GetStdHandle(int h);
    [DllImport("kernel32.dll")] public static extern bool GetConsoleMode(IntPtr h, out uint m);
    [DllImport("kernel32.dll")] public static extern bool SetConsoleMode(IntPtr h, uint m);
    [DllImport("kernel32.dll")] public static extern bool GetNumberOfConsoleInputEvents(IntPtr h, out uint n);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)] public static extern bool ReadConsoleInputW(IntPtr h, [Out] R[] b, uint l, out uint r);
}
'@
$in = [Diag]::GetStdHandle(-10); $mode = 0; [void][Diag]::GetConsoleMode($in, [ref]$mode)
"PowerShell $($PSVersionTable.PSVersion) | Windows Terminal: $([bool]$env:WT_SESSION) | console mode 0x{0:X}" -f $mode
function Pass([string]$Name, [uint32]$NewMode, [string]$Vt) {
    "`n=== ${Name}: click, scroll, right-click now (10 s) ==="
    [void][Diag]::SetConsoleMode($in, $NewMode); if ($Vt) { [Console]::Write($Vt) }
    $end = (Get-Date).AddSeconds(10); $b = New-Object Diag+R[] 1
    while ((Get-Date) -lt $end) {
        $n = 0; [void][Diag]::GetNumberOfConsoleInputEvents($in, [ref]$n)
        if ($n -eq 0) { Start-Sleep -Milliseconds 20; continue }
        $r = 0; [void][Diag]::ReadConsoleInputW($in, $b, 1, [ref]$r); $e = $b[0]
        switch ($e.T) {
            1 { if ($e.Down) { "KEY   vk={0} char={1}" -f $e.Vk, [int]$e.Ch } }
            2 { "MOUSE x={0} y={1} buttons=0x{2:X} flags={3}" -f $e.X, $e.Y, $e.Btn, $e.Flags }
            default { "EVENT type={0}" -f $e.T }
        }
    }
    if ($Vt) { [Console]::Write("`e[?1006l`e[?1000l") }
    [void][Diag]::SetConsoleMode($in, $mode)
}
Pass "Pass 1 (mouse records)" (($mode -bor 0x10 -bor 0x80) -band (-bnot 0x40)) ""
Pass "Pass 2 (VT mouse mode)" (($mode -bor 0x200 -bor 0x80) -band (-bnot 0x40)) "`e[?1000h`e[?1006h"
"`nDone; console mode restored to 0x{0:X}." -f $mode
