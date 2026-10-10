param([switch]$SkipAppBuild)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not $SkipAppBuild) { & .\build.ps1 }
$versionMatch = Select-String -LiteralPath 'app.py' -Pattern '^APP_VERSION = "([^"]+)"'
$releaseVersion = $versionMatch.Matches[0].Groups[1].Value
$compilerCandidates = @(
    (Join-Path $PSScriptRoot '.build-tools\InnoSetup\ISCC.exe'),
    'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
    'C:\Program Files\Inno Setup 6\ISCC.exe',
    'C:\Program Files\Inno Setup 7\ISCC.exe'
)
$compilerPath = $compilerCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $compilerPath) { throw 'Install Inno Setup, or provide .build-tools\InnoSetup\ISCC.exe.' }
& $compilerPath "/DAppVersion=$releaseVersion" '.\installer\Devices.iss'
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed.' }
Write-Host "Installer ready: Latest build\Devices-$releaseVersion-Setup.exe"
