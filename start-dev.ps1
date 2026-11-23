# SupportGenie - start everything for local development with ONE command.
#
#   From the project root:   .\start-dev.ps1
#
# Opens two new PowerShell windows (backend + frontend) and then the app in the browser.
# The backend runs with --reload (auto-restarts when code changes) and --no-proxy-headers
# (so nobody can fake their IP to dodge the rate limiter - see backend/app/core/rate_limit.py).
# To stop: close the two windows (or press Ctrl+C in each).

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "Virtual environment not found at $python" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path (Join-Path $root "frontend\node_modules"))) {
    Write-Host "Installing frontend packages first (one time)..." -ForegroundColor Yellow
    Push-Location (Join-Path $root "frontend"); npm install; Pop-Location
}

$backendCmd  = "`$host.UI.RawUI.WindowTitle = 'SupportGenie BACKEND'; Set-Location '$root\backend'; & '$python' -m uvicorn app.main:app --port 8000 --reload --no-proxy-headers"
$frontendCmd = "`$host.UI.RawUI.WindowTitle = 'SupportGenie FRONTEND'; Set-Location '$root\frontend'; npm run dev"

Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Write-Host ""
Write-Host "Starting SupportGenie..." -ForegroundColor Cyan
Write-Host "  Backend : http://localhost:8000/docs"
Write-Host "  Frontend: http://localhost:5173"
Start-Sleep -Seconds 8
Start-Process "http://localhost:5173"
