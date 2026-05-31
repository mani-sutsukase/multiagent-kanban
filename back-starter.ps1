Write-Host "============================================" -ForegroundColor Cyan
Write-Host " 启动 Backend - MultiAgent Kanban System" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$rootDir\backend"

# ====== 检测 Python 运行时 ======
$portablePy = Join-Path $rootDir "backend\portable-python\python.exe"
if (Test-Path $portablePy) {
    $script:PY_EXE = $portablePy
    Write-Host "[MODE] 检测到便携 Python - 使用离线运行时" -ForegroundColor Green
    Write-Host "  $portablePy" -ForegroundColor Gray
    goto :check_config
}

$script:PY_EXE = "python"
Write-Host "[MODE] 使用系统 Python" -ForegroundColor Yellow
goto :check_python

# ==================== 系统 Python 检查 ====================
:check_python
Write-Host "[1/3] 检查 Python..." -ForegroundColor Yellow
try {
    $pyVersion = python --version
    Write-Host "  $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python 未找到，请安装 Python 并添加到 PATH" -ForegroundColor Red
    Read-Host "按 Enter 退出..."
    exit 1
}

# 尝试激活虚拟环境
$venvActivate = Join-Path $rootDir "backend\venv\Scripts\Activate.ps1"
$venv2Activate = Join-Path $rootDir "backend\.venv\Scripts\Activate.ps1"

Write-Host "[2/3] 检查虚拟环境..." -ForegroundColor Yellow
if (Test-Path $venvActivate) {
    & $venvActivate
    Write-Host "  虚拟环境已激活 (venv)" -ForegroundColor Green
}
elseif (Test-Path $venv2Activate) {
    & $venv2Activate
    Write-Host "  虚拟环境已激活 (.venv)" -ForegroundColor Green
}
else {
    Write-Host "  [INFO] 未找到虚拟环境，使用系统 Python" -ForegroundColor DarkYellow
}

Write-Host "  检查依赖..." -ForegroundColor Yellow
try {
    python -c "import fastapi, uvicorn, sqlalchemy, aiosqlite, apscheduler, pydantic" 2>&1 | Out-Null
    Write-Host "  所有依赖已满足" -ForegroundColor Green
} catch {
    Write-Host "  安装依赖中..." -ForegroundColor Yellow
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] pip install 失败" -ForegroundColor Red
        Read-Host "按 Enter 退出..."
        exit 1
    }
    Write-Host "  依赖安装完成" -ForegroundColor Green
}

# ==================== 共享配置检查 ====================
:check_config
Write-Host "  检查数据目录..." -ForegroundColor Yellow
$dataDir = Join-Path $rootDir "backend\data"
if (-not (Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir | Out-Null
    Write-Host "  数据目录已创建" -ForegroundColor Green
} else {
    Write-Host "  数据目录已存在" -ForegroundColor Green
}

$envFile = Join-Path $rootDir "backend\.env"
if (Test-Path $envFile) {
    Write-Host "  [INFO] .env 配置文件已找到" -ForegroundColor DarkYellow
} else {
    Write-Host "  [INFO] 未找到 .env 文件，使用默认配置" -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  启动 Uvicorn 服务器..." -ForegroundColor Yellow
Write-Host "  API:       http://localhost:8000" -ForegroundColor Green
Write-Host "  Swagger:   http://localhost:8000/docs" -ForegroundColor Green
Write-Host "  Health:    http://localhost:8000/api/health" -ForegroundColor Green
Write-Host ""
Write-Host "  按 Ctrl+C 停止服务" -ForegroundColor Red
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

& $PY_EXE -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Read-Host "按 Enter 键退出..."
