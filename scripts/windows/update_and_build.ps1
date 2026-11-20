# Pull the latest work, import it and build the game as real Windows .exe files
# in this folder, with shortcuts to double-click. Run it from "Update Game.cmd"
# at the top of the repository, or:
#
#   powershell -ExecutionPolicy Bypass -File scripts\windows\update_and_build.ps1 [-NoPull] [-Godot <path>]
#
# What you get (not committed, rebuilt each time):
#   game\build_town\HaldenRidge.exe      the town at night (03:00 Foggy, High)
#   game\build\day\HaldenRidgeDay.exe    the town by day (10:00 Clear, Low)
#   "Halden Ridge (Night).lnk" and "Halden Ridge (Day).lnk" next to this
#   repository's README, and on the Desktop.
# Third person and first person are the same game: V switches between them.

param(
    [switch]$NoPull,
    [string]$Godot = "",
    [string]$Branch = "claude/sweet-fermat-oxmviq"
)

$ErrorActionPreference = "Stop"
$Version = "4.7.2"
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Repo

function Step($text) { Write-Host "`n=== $text" -ForegroundColor Cyan }

# --- Godot -------------------------------------------------------------------
Step "Finding Godot $Version"
if (-not $Godot) { $Godot = $env:GODOT }
if (-not $Godot -or -not (Test-Path $Godot)) {
    $Godot = (Get-ChildItem -Path C:\, D:\ -Recurse -Filter "Godot_v$Version-stable_win64_console.exe" `
        -ErrorAction SilentlyContinue | Select-Object -First 1).FullName
}
if (-not $Godot) {
    Write-Host "Not found: downloading Godot $Version to C:\Godot"
    $zip = Join-Path $env:TEMP "godot_$Version.zip"
    Invoke-WebRequest "https://github.com/godotengine/godot/releases/download/$Version-stable/Godot_v$Version-stable_win64.exe.zip" -OutFile $zip
    Expand-Archive $zip -DestinationPath C:\Godot -Force
    $Godot = "C:\Godot\Godot_v$Version-stable_win64_console.exe"
}
[Environment]::SetEnvironmentVariable("GODOT", $Godot, "User")
Write-Host "Godot: $Godot"

# --- Export templates (needed once to make .exe files) ------------------------
$templates = Join-Path $env:APPDATA "Godot\export_templates\$Version.stable"
if (-not (Test-Path (Join-Path $templates "windows_release_x86_64.exe"))) {
    Step "Downloading Godot's export templates (once, about 1 GB)"
    $tpz = Join-Path $env:TEMP "godot_templates_$Version.zip"
    Invoke-WebRequest "https://github.com/godotengine/godot/releases/download/$Version-stable/Godot_v$Version-stable_export_templates.tpz" -OutFile $tpz
    $unpack = Join-Path $env:TEMP "godot_templates_$Version"
    Expand-Archive $tpz -DestinationPath $unpack -Force
    New-Item -ItemType Directory -Force $templates | Out-Null
    Copy-Item (Join-Path $unpack "templates\*") $templates -Recurse -Force
    Remove-Item $tpz, $unpack -Recurse -Force
}

# --- Pull ----------------------------------------------------------------------
if (-not $NoPull) {
    Step "Getting the latest work ($Branch)"
    # Godot rewrites line endings in some files; those changes would block the pull.
    git diff --name-only | ForEach-Object {
        git diff --ignore-cr-at-eol --quiet -- $_
        if ($LASTEXITCODE -eq 0) { git checkout -- $_ }
    }
    git pull origin $Branch
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Pull failed. If it says local changes would be overwritten, run:" -ForegroundColor Yellow
        Write-Host '  git stash push -u -m "before-pull"' -ForegroundColor Yellow
        Write-Host "and start this again." -ForegroundColor Yellow
        exit 1
    }
    git lfs pull
}
git log --oneline -1

# --- Import --------------------------------------------------------------------
Step "Importing (this takes a few minutes the first time)"
& $Godot --headless --path game --import
python projects/03-town/godot_imports.py
& $Godot --headless --path game --import

# --- Build ---------------------------------------------------------------------
$builds = @(
    @{ Preset = "Halden Ridge Town"; Exe = "game\build_town\HaldenRidge.exe"; Name = "Halden Ridge (Night)" },
    @{ Preset = "Halden Ridge Day";  Exe = "game\build\day\HaldenRidgeDay.exe"; Name = "Halden Ridge (Day)" }
)
$shell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath("Desktop")
foreach ($b in $builds) {
    Step "Building $($b.Name)"
    $exe = Join-Path $Repo $b.Exe
    New-Item -ItemType Directory -Force (Split-Path $exe) | Out-Null
    & $Godot --headless --path game --export-release $b.Preset (Join-Path $Repo $b.Exe)
    if (-not (Test-Path $exe)) { Write-Host "Build failed: $($b.Exe) was not made" -ForegroundColor Red; exit 1 }
    foreach ($dir in @($Repo, $desktop)) {
        $lnk = $shell.CreateShortcut((Join-Path $dir "$($b.Name).lnk"))
        $lnk.TargetPath = $exe
        $lnk.WorkingDirectory = Split-Path $exe
        $lnk.Save()
    }
}

Step "Done"
Write-Host "Double-click 'Halden Ridge (Night)' or 'Halden Ridge (Day)' in $Repo or on the Desktop."
Write-Host "In the game: V = first person / third person, F4 = time and weather."
