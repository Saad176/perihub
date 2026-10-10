$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

python -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --windowed `
    --name Devices `
    --distpath 'Latest build' `
    --workpath 'Old builds/build-cache' `
    --specpath 'Old builds/build-spec' `
    --icon "$PSScriptRoot\assets\devices.ico" `
    --add-data "$PSScriptRoot\assets;assets" `
    "$PSScriptRoot\app.py"

if ($LASTEXITCODE -ne 0) {
    throw 'PyInstaller build failed.'
}

Write-Host 'Build ready at Latest build\Devices\Devices.exe'
