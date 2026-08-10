# Script de ayuda para Windows: añadir MSYS2 mingw64/bin al PATH temporalmente
# y reinstalar weasyprint en el virtualenv del proyecto.
# Uso: desde PowerShell en la carpeta del proyecto ejecutar:
#   .\scripts\install_weasyprint.ps1

Write-Host "Script helper: reinstalling weasyprint for the project's venv"

$msysPath = 'C:\msys64\mingw64\bin'
if (-Not (Test-Path $msysPath)) {
    Write-Host "WARNING: MSYS2 mingw64 path not found: $msysPath" -ForegroundColor Yellow
    Write-Host "Please install MSYS2 and run the pacman commands in the MSYS2 MinGW 64-bit shell first." -ForegroundColor Yellow
    exit 1
}

Write-Host "Adding $msysPath to PATH for this PowerShell session..."
$env:PATH = "$msysPath;" + $env:PATH

Write-Host "Activating virtualenv (if .venv exists)..."
if (-Not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
    Write-Host "No .venv found in project root. Make sure your venv is at .\.venv or edit this script." -ForegroundColor Red
    exit 1
}

& .\.venv\Scripts\Activate.ps1

Write-Host "Upgrading pip/setuptools/wheel..."
python -m pip install --upgrade pip setuptools wheel

Write-Host "Reinstalling WeasyPrint (this will now link against the system DLLs)..."
pip install --force-reinstall weasyprint==66.0

Write-Host "Done. Verify with: python -c \"import weasyprint; print('weasyprint', weasyprint.__version__)\""
Write-Host "If that prints the version, restart your Django server: python manage.py runserver"
