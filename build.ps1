$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    # PyInstaller logs progress to stderr; Windows PowerShell must not treat it as failure.
    $ErrorActionPreference = 'Continue'
    python -m PyInstaller --noconfirm --clean --onefile --windowed `
        --name EscapeAcademy2-Russian-Setup --paths installer `
        --icon installer/academy.ico --add-data 'installer/academy.ico;.' `
        --add-data 'installer/assets/ticket-art.png;assets' `
        --add-data 'payload;payload' installer/app.py
    $buildExitCode = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($buildExitCode -ne 0) { throw 'Сборка не выполнена' }
    $target = Join-Path $PSScriptRoot 'dist/EscapeAcademy2-Russian-Setup.exe'
    $hash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
    Set-Content -LiteralPath 'dist/SHA256.txt' -Value "$hash  EscapeAcademy2-Russian-Setup.exe" -Encoding UTF8
} finally { Pop-Location }
