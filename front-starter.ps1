Write-Host "============================================" -ForegroundColor Cyan
Write-Host " 启动 Frontend - MultiAgent Kanban System" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$rootDir\frontend"

# 检查 node_modules
if (-not (Test-Path "node_modules")) {
    Write-Host "[1/2] 正在安装 npm 依赖..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] npm install 失败" -ForegroundColor Red
        Read-Host "按 Enter 键退出..."
        exit 1
    }
    Write-Host "  依赖安装完成" -ForegroundColor Green
}
else {
    Write-Host "[1/2] node_modules 已存在，跳过安装" -ForegroundColor Yellow
}

Write-Host "[2/2] 启动 Vite 开发服务器..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  Local:    http://localhost:5173" -ForegroundColor Green
Write-Host "  Backend:  代理到 http://localhost:8000" -ForegroundColor Green
Write-Host ""
Write-Host "  按 Ctrl+C 停止服务" -ForegroundColor Red
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

npm run dev

Read-Host "按 Enter 键退出..."
