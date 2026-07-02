# ============================================================
# DirNav kickoff runner
# Invoked by the kickoff:// protocol, or from the command line.
#   Full kickoff:    kickoff.ps1 "kickoff://WSe2OEP"
#   Selected items:  kickoff.ps1 "kickoff://WSe2OEP?items=d0,u0,f1"
#   Open P00:        kickoff.ps1 "kickoff://WSe2OEP?items=p"
#   From CLI:        kickoff.ps1 WSe2OEP
#
# Item refs: d = folders, u = urls, f = files, p = p00 (VSCode), pd = p00 folder.
# Indices are resolved against projects.json here, so the URL never
# carries a raw path. A stray web page cannot inject a path.
# ============================================================

param(
    [Parameter(Position = 0)]
    [string]$Arg
)

$ErrorActionPreference = "Stop"

function Exit-WithError([string]$Message) {
    Write-Host ""
    Write-Host "DirNav kickoff failed:" -ForegroundColor Red
    Write-Host $Message
    Write-Host ""
    Read-Host "Press Enter to close"
    exit 1
}

trap {
    Exit-WithError $_.Exception.Message
}

Add-Type -AssemblyName System.Windows.Forms

$JsonPath = Join-Path $PSScriptRoot "..\projects.json"
if (-not (Test-Path $JsonPath)) {
    Exit-WithError "projects.json not found at $JsonPath"
}

# --- Parse the argument into slug and optional item refs ---
$raw = $Arg
if ($raw -like "kickoff://*") { $raw = $raw.Substring("kickoff://".Length) }
$raw = $raw.Trim()

$slug = $raw
$itemSpec = $null
if ($raw.Contains("?")) {
    $parts = $raw.Split("?", 2)
    $slug = $parts[0]
    foreach ($kv in $parts[1].Split("&")) {
        $pair = $kv.Split("=", 2)
        if ($pair[0] -eq "items" -and $pair.Count -eq 2) { $itemSpec = $pair[1] }
    }
}
$slug = $slug.TrimEnd('/')   # Chrome appends a slash to the authority, e.g. SARD/?items=p
try { $slug = [System.Uri]::UnescapeDataString($slug) } catch {}

# Synthetic slug: the manifest file itself.
# kickoff://__manifest?items=p  -> open projects.json in VSCode
# kickoff://__manifest?items=pd -> open its parent folder in Explorer
if ($slug -eq "__manifest") {
    if ($itemSpec -eq "pd") {
        Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "explorer", "`"$(Split-Path $JsonPath -Parent)`"" -WindowStyle Hidden
    } else {
        Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "code", "`"$JsonPath`"" -WindowStyle Hidden
    }
    exit 0
}

# Synthetic slug: latest weekly log (resolved at click time via weekly retriever).
# kickoff://__weekly?items=p  -> open latest weekly .md in VSCode
# kickoff://__weekly?items=pd -> open its parent folder in Explorer
if ($slug -eq "__weekly") {
    $weeklyPy = "D:\01_Floor\a_Ed\21_Claude\02_AI Career Advise\01_Weekly\P01_latest weekly retriever.py"
    if (-not (Test-Path -LiteralPath $weeklyPy)) {
        Exit-WithError "Weekly retriever not found at $weeklyPy"
    }
    $jsonText = & python $weeklyPy --json 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) {
        Exit-WithError "Weekly retriever failed:`n$jsonText"
    }
    $summary = $jsonText | ConvertFrom-Json
    $weeklyPath = $summary.path
    if ([string]::IsNullOrWhiteSpace($weeklyPath) -or -not (Test-Path -LiteralPath $weeklyPath)) {
        Exit-WithError "Latest weekly file not found at $weeklyPath"
    }
    if ($itemSpec -eq "pd") {
        Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "explorer", "`"$(Split-Path $weeklyPath -Parent)`"" -WindowStyle Hidden
    } else {
        Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "code", "`"$weeklyPath`"" -WindowStyle Hidden
    }
    exit 0
}

# Synthetic slug: run the Compile bat from the project root.
# kickoff://__compile -> [B]_P01-Compile Dashboard.bat
if ($slug -eq "__compile") {
    $batPath = Join-Path (Split-Path $JsonPath -Parent) "[B]_P01-Compile Dashboard.bat"
    if (Test-Path -LiteralPath $batPath) {
        Start-Process -FilePath $batPath
    } else {
        Exit-WithError "Compile bat not found at $batPath"
    }
    exit 0
}

$data = Get-Content -Raw -LiteralPath $JsonPath | ConvertFrom-Json
$project = $data.projects | Where-Object { $_.projectSlug -eq $slug } | Select-Object -First 1
if (-not $project) {
    Exit-WithError "No project with slug '$slug' in projects.json"
}

$folders = @($project.folders)
$urls    = @($project.urls)
$files   = @($project.files)
$p00     = $project.p00

# ============================================================
# Helpers
# ============================================================
function Open-Item([string]$p) {
    if ([string]::IsNullOrWhiteSpace($p)) { return }
    Start-Process -FilePath $p
    Start-Sleep -Milliseconds 300
}

function Open-InVSCode([string]$p) {
    if ([string]::IsNullOrWhiteSpace($p)) { return }
    # code resolves to code.cmd on PATH; go through cmd so it is found.
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "code", "`"$p`"" -WindowStyle Hidden
}

function Open-FoldersAsTabs([string[]]$dirs) {
    if ($dirs.Count -eq 0) { return }
    Start-Process explorer.exe $dirs[0]
    Start-Sleep -Milliseconds 1000
    $wshell = New-Object -ComObject WScript.Shell
    $explorer = Get-Process explorer | Sort-Object StartTime -Descending | Select-Object -First 1
    $wshell.AppActivate($explorer.Id) | Out-Null
    Start-Sleep -Milliseconds 1000
    for ($i = 1; $i -lt $dirs.Count; $i++) {
        [System.Windows.Forms.SendKeys]::SendWait("^t")
        Start-Sleep -Milliseconds 2500      # Important waiting time.
        [System.Windows.Forms.SendKeys]::SendWait("^l")
        Start-Sleep -Milliseconds 1500      # Important waiting time.
        Set-Clipboard -Value $dirs[$i]
        Start-Sleep -Milliseconds 500
        [System.Windows.Forms.SendKeys]::SendWait("^v")
        Start-Sleep -Milliseconds 500
        [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
        Start-Sleep -Milliseconds 500
    }
}

# ============================================================
# Mode 1: Selected items. Open each on its own, no tab orchestration.
# ============================================================
if ($itemSpec) {
    foreach ($ref in $itemSpec.Split(",")) {
        $ref = $ref.Trim()
        if ($ref -eq "") { continue }
        if ($ref -eq "p")  { Open-InVSCode $p00; continue }                              # P00 file in VSCode
        if ($ref -eq "pd") { if ($p00) { Open-Item (Split-Path $p00 -Parent) }; continue } # P00 folder in Explorer
        $kind = $ref.Substring(0, 1)
        $idx  = [int]$ref.Substring(1)
        switch ($kind) {
            "d" { if ($idx -lt $folders.Count) { Open-Item $folders[$idx] } }
            "u" { if ($idx -lt $urls.Count)    { Open-Item $urls[$idx] } }
            "f" { if ($idx -lt $files.Count)   { Open-Item $files[$idx] } }
        }
    }
    exit 0
}

# ============================================================
# Mode 2: Full kickoff. Folders as tabs in one window, then urls and files.
# ============================================================
Open-FoldersAsTabs $folders
foreach ($u in $urls)  { Open-Item $u }
foreach ($f in $files) { Open-Item $f }
exit 0
