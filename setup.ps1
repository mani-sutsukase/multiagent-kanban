Write-Host "============================================" -ForegroundColor Cyan
Write-Host " MultiAgent Kanban - 环境搭建" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# ==================== 1. Python ====================
Write-Host "[1/5] 检查 Python (>=3.10)..." -ForegroundColor Yellow
try {
    $pyVersion = python --version
    Write-Host "  $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python 未找到！" -ForegroundColor Red
    Write-Host "  请从 https://www.python.org/downloads/ 安装 Python 3.10+" -ForegroundColor Yellow
    Read-Host "按 Enter 退出..."
    exit 1
}

# 检查版本 >= 3.10
$verParts = $pyVersion -replace 'Python ', '' -split '\.'
if (([int]$verParts[0] -lt 3) -or ([int]$verParts[0] -eq 3 -and [int]$verParts[1] -lt 10)) {
    Write-Host "[ERROR] 需要 Python 3.10+，当前: $pyVersion" -ForegroundColor Red
    Read-Host "按 Enter 退出..."
    exit 1
}

# ==================== 2. venv ====================
Write-Host "[2/5] 创建虚拟环境..." -ForegroundColor Yellow
Set-Location "$rootDir\backend"
$venvPath = Join-Path $rootDir "backend\venv"
$venvActivate = Join-Path $venvPath "Scripts\Activate.ps1"

if (Test-Path $venvActivate) {
    Write-Host "  虚拟环境已存在" -ForegroundColor Green
} else {
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] 创建虚拟环境失败" -ForegroundColor Red
        Read-Host "按 Enter 退出..."
        exit 1
    }
    Write-Host "  虚拟环境已创建 (venv)" -ForegroundColor Green
}

# ==================== 3. pip deps ====================
Write-Host "[3/5] 安装 Python 依赖..." -ForegroundColor Yellow
& $venvActivate
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] pip install 失败" -ForegroundColor Red
    Read-Host "按 Enter 退出..."
    exit 1
}
Write-Host "  Python 依赖安装完成" -ForegroundColor Green
deactivate

# ==================== 4. Node.js ====================
Write-Host "[4/5] 检查 Node.js..." -ForegroundColor Yellow
try {
    $nodeVer = node --version
    Write-Host "  Node.js $nodeVer" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Node.js 未找到！" -ForegroundColor Red
    Write-Host "  请从 https://nodejs.org/ 安装 Node.js 18+" -ForegroundColor Yellow
    Read-Host "按 Enter 退出..."
    exit 1
}

Write-Host "  安装 npm 依赖..." -ForegroundColor Yellow
Set-Location "$rootDir\frontend"
if (Test-Path "node_modules") {
    Write-Host "  node_modules 已存在，跳过安装" -ForegroundColor Green
} else {
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] npm install 失败" -ForegroundColor Red
        Read-Host "按 Enter 退出..."
        exit 1
    }
    Write-Host "  npm 依赖安装完成" -ForegroundColor Green
}

# ==================== 5. data dir + .env ====================
Write-Host "[5/5] 配置项目..." -ForegroundColor Yellow
Set-Location "$rootDir"

$dataDir = Join-Path $rootDir "backend\data"
if (-not (Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir | Out-Null
    Write-Host "  已创建 backend\data\" -ForegroundColor Green
} else {
    Write-Host "  backend\data\ 已存在" -ForegroundColor Green
}

$envFile = Join-Path $rootDir "backend\.env"
$envExample = Join-Path $rootDir "backend\.env.example"
if (-not (Test-Path $envFile)) {
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        Write-Host "  已从 .env.example 创建 .env" -ForegroundColor Green
    } else {
        Write-Host "  [INFO] 未找到 .env.example，跳过 .env 创建" -ForegroundColor DarkYellow
    }
} else {
    Write-Host "  .env 已存在" -ForegroundColor Green
}

Set-Location $rootDir
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  环境搭建完成！" -ForegroundColor Green
Write-Host ""
Write-Host "  启动方式:" -ForegroundColor White
Write-Host "    .\start-all.bat     - 同时启动前后端" -ForegroundColor Yellow
Write-Host "    .\back-starter.bat  - 仅启动后端" -ForegroundColor Yellow
Write-Host "    .\front-starter.bat - 仅启动前端" -ForegroundColor Yellow
Write-Host ""
Write-Host "  地址:" -ForegroundColor White
Write-Host "    前端: http://localhost:5173" -ForegroundColor Green
Write-Host "    后端: http://localhost:8000" -ForegroundColor Green
Write-Host "    API 文档: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Read-Host "按 Enter 退出..."
