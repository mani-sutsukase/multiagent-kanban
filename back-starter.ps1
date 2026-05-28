Write-Host "============================================" -ForegroundColor Cyan
Write-Host " 启动 Backend - MultiAgent Kanban System" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$rootDir\backend"

# 尝试激活虚拟环境
$venvActivate = Join-Path $rootDir "backend\venv\Scripts\Activate.ps1"
$venv2Activate = Join-Path $rootDir "backend\.venv\Scripts\Activate.ps1"

if (Test-Path $venvActivate) {
    Write-Host "[1/2] 激活虚拟环境 (venv)..." -ForegroundColor Yellow
    & $venvActivate
}
elseif (Test-Path $venv2Activate) {
    Write-Host "[1/2] 激活虚拟环境 (.venv)..." -ForegroundColor Yellow
    & $venv2Activate
}
else {
    Write-Host "[1/2] 未找到虚拟环境，使用系统 Python" -ForegroundColor DarkYellow
}

Write-Host "[2/2] 启动 Uvicorn 服务器..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  API:       http://localhost:8000" -ForegroundColor Green
Write-Host "  Swagger:   http://localhost:8000/docs" -ForegroundColor Green
Write-Host "  Health:    http://localhost:8000/api/health" -ForegroundColor Green
Write-Host ""
Write-Host "  按 Ctrl+C 停止服务" -ForegroundColor Red
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Read-Host "按 Enter 键退出..."
