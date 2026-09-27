<#
.SYNOPSIS
    Builds the Windows release of CrossPatch: portable zip and installer.

.DESCRIPTION
    Run from anywhere; paths are resolved from the repository root.

      1. Runs the test suite (skip with -SkipTests).
      2. Publishes the pak parser to build\parser\win-x64 if it is missing, or
         when -RebuildParser is given.
      3. Runs PyInstaller with packaging\windows\CrossPatch.spec.
      4. Stages build\stage-win\CrossPatch and zips it as dist\CrossPatch.<version>.zip,
         the archive older CrossPatch versions update from.
      5. Compiles dist\CrossPatch-<version>-win-x64-setup.exe with Inno Setup
         (skip with -SkipInstaller).

.EXAMPLE
    ./packaging/windows/build.ps1
    ./packaging/windows/build.ps1 -Version 1.4.0-test -SkipTests
#>
[CmdletBinding()]
param(
    [string]$Version,
    [switch]$RebuildParser,
    [switch]$SkipTests,
    [switch]$SkipInstaller
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $root

if (-not $Version) { $Version = (Get-Content version.txt -Raw).Trim() }
Write-Host "Building CrossPatch $Version" -ForegroundColor Cyan

function Invoke-Checked([string]$what, [scriptblock]$block) {
    & $block
    if ($LASTEXITCODE -ne 0) { throw "$what failed (exit $LASTEXITCODE)" }
}

# 1. Tests
if (-not $SkipTests) {
    Invoke-Checked 'Tests' { python -m pytest -q }
}

# 2. Pak parser. Published to build\, never into tools\...\bin\: those files are
#    tracked in git and dotnet publish would rewrite hundreds of them.
$parser = Join-Path $root 'build\parser\win-x64\CrossPatchParser.exe'
if ($RebuildParser -or -not (Test-Path $parser)) {
    Invoke-Checked 'Parser publish' {
        dotnet publish tools\CrossPatchParser\CrossPatchParser.csproj -c Release -f net8.0 `
            -r win-x64 --self-contained true -p:PublishSingleFile=true -p:InvariantGlobalization=true `
            -o build\parser\win-x64
    }
    # dotnet publish also rewrites the tracked build output under tools\.
    $touched = git status --porcelain -- tools/
    if ($touched) {
        Write-Warning "dotnet publish modified tracked files under tools\. Review them, then restore with: git checkout -- tools/"
    }
}

# 3. PyInstaller
$pyiDist = Join-Path $root 'build\pyinstaller'
Invoke-Checked 'PyInstaller' {
    python -m PyInstaller packaging\windows\CrossPatch.spec --noconfirm --distpath $pyiDist --workpath build\pyi
}

# 4. Stage and zip. Everything sits under a single CrossPatch\ folder: the
#    in-app updater of older versions relies on that layout.
$stageRoot = Join-Path $root 'build\stage-win'
$stage = Join-Path $stageRoot 'CrossPatch'
if (Test-Path $stageRoot) { Remove-Item $stageRoot -Recurse -Force }
New-Item -ItemType Directory -Force $stage | Out-Null
Copy-Item (Join-Path $pyiDist 'CrossPatch\*') $stage -Recurse
Copy-Item assets (Join-Path $stage 'assets') -Recurse
New-Item -ItemType Directory -Force (Join-Path $stage 'tools') | Out-Null
Copy-Item $parser (Join-Path $stage 'tools\CrossPatchParser.exe')
Copy-Item LICENSE, PRIVACY.md, README.md $stage

New-Item -ItemType Directory -Force dist | Out-Null
$zip = Join-Path $root "dist\CrossPatch.$Version.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
# Python's zipfile, the same library the updater unpacks with.
Invoke-Checked 'Zip' {
    python -c "import shutil,sys; shutil.make_archive(sys.argv[1][:-4], 'zip', root_dir=sys.argv[2], base_dir='CrossPatch')" $zip $stageRoot
}

# 5. Installer
$outputs = @($zip)
if (-not $SkipInstaller) {
    $iscc = @(
        (Get-Command iscc.exe -ErrorAction SilentlyContinue).Source,
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    ) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
    if (-not $iscc) { throw 'Inno Setup 6 not found. Install it (winget install JRSoftware.InnoSetup) or pass -SkipInstaller.' }

    # Inno Setup wants a numeric version; "1.4.0-test" becomes 1.4.0 there.
    $numeric = ($Version -replace '[^0-9.].*$', '')
    Invoke-Checked 'Inno Setup' {
        & $iscc /Q "/DAppVersion=$numeric" "/DSourceDir=$stage" "/DOutputDir=$(Join-Path $root 'dist')" `
            packaging\windows\CrossPatch.iss
    }
    $setup = Join-Path $root "dist\CrossPatch-$numeric-win-x64-setup.exe"
    if ($numeric -ne $Version) {
        $renamed = Join-Path $root "dist\CrossPatch-$Version-win-x64-setup.exe"
        Move-Item $setup $renamed -Force
        $setup = $renamed
    }
    $outputs += $setup
}

Write-Host "`nDone:" -ForegroundColor Green
foreach ($file in $outputs) {
    $hash = (Get-FileHash $file -Algorithm SHA256).Hash.ToLower()
    '{0}  {1:N1} MB  sha256:{2}' -f (Split-Path $file -Leaf), ((Get-Item $file).Length / 1MB), $hash
}
