# ============================================================
# Registers the kickoff:// URI protocol under HKCU. No admin needed.
# After running, a page link like kickoff://MySlug?items=d0,u0 invokes
# 01_scripts\kickoff.ps1 with that full URI as %1.
# Run once. Re-run safely if you move the folder.
# ============================================================

$scriptPath = (Resolve-Path (Join-Path $PSScriptRoot "kickoff.ps1")).Path

$base = "HKCU:\Software\Classes\kickoff"
New-Item -Path $base -Force | Out-Null
Set-ItemProperty -Path $base -Name "(Default)" -Value "URL:DirNav Kickoff Protocol"
Set-ItemProperty -Path $base -Name "URL Protocol" -Value ""

$cmdKey = "HKCU:\Software\Classes\kickoff\shell\open\command"
New-Item -Path $cmdKey -Force | Out-Null
$command = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" `"%1`""
Set-ItemProperty -Path $cmdKey -Name "(Default)" -Value $command

Write-Host "Registered kickoff:// protocol."
Write-Host "  Handler: $scriptPath"
Write-Host "  Command: $command"
Write-Host ""
Write-Host "Test it: open the dashboard with [B]_localhost homepage.bat and click any Kickoff button."
