$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Med-Assist - Medical Device AI Assistant" -ForegroundColor White
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$viewer = Join-Path (Split-Path -Parent $root) "iobs-unified-app"

Write-Host "[1/3] Starting backend + Agent (port 8000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backend'; python -m uvicorn main:app --port 8000 --reload"

Write-Host "[2/3] Starting 3D Viewer (port 3001)..." -ForegroundColor Yellow
if (-not (Test-Path "$viewer\node_modules")) {
    Write-Host "      npm install ..." -ForegroundColor Gray
    Set-Location $viewer; npm install
}
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$viewer'; npm run dev"

Write-Host "[3/3] Starting Chat UI (port 5173)..." -ForegroundColor Yellow
if (-not (Test-Path "$frontend\node_modules")) {
    Write-Host "      npm install ..." -ForegroundColor Gray
    Set-Location $frontend; npm install
}

Write-Host ""
Write-Host "-----------------------------------------------" -ForegroundColor Green
Write-Host "  3D Viewer : http://localhost:3001" -ForegroundColor White
Write-Host "  Chat UI   : http://localhost:5173" -ForegroundColor White
Write-Host "  Backend   : http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs  : http://localhost:8000/docs" -ForegroundColor White
Write-Host "-----------------------------------------------" -ForegroundColor Green
Write-Host ""

Set-Location $frontend; npm run dev
