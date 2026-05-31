@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================
echo  MultiAgent Kanban - 环境搭建
echo ============================================
echo.

rem ==================== 1. Python ====================
echo [1/5] Checking Python (>=3.10)...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found!
    echo   Please install Python 3.10+ from https://www.python.org/downloads/
    echo   Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set "PY_VER=%%v"
echo   Python %PY_VER%

rem 检查 Python 版本 >= 3.10
for /f "tokens=1,2 delims=." %%a in ("%PY_VER%") do (
    if %%a LSS 3 (
        echo [ERROR] Python 3.10+ required, found %PY_VER%
        pause
        exit /b 1
    )
    if %%a EQU 3 if %%b LSS 10 (
        echo [ERROR] Python 3.10+ required, found %PY_VER%
        pause
        exit /b 1
    )
)

rem ==================== 2. venv ====================
echo [2/5] Creating virtual environment...
cd backend
if exist "venv\Scripts\activate.bat" (
    echo   Virtual environment already exists
) else if exist ".venv\Scripts\activate.bat" (
    echo   Virtual environment already exists
) else (
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo   Virtual environment created (venv)
)
cd ..

rem ==================== 3. pip deps ====================
echo [3/5] Installing Python dependencies...
cd backend
call venv\Scripts\activate.bat
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] pip install failed
    pause
    exit /b 1
)
echo   Python dependencies installed
call deactivate
cd ..

rem ==================== 4. Node.js ====================
echo [4/5] Checking Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found!
    echo   Please install Node.js 18+ from https://nodejs.org/
    pause
    exit /b 1
)
for /f "delims=" %%v in ('node --version') do echo   Node.js %%v

echo   Installing npm dependencies...
cd frontend
if exist "node_modules" (
    echo   node_modules already exists, skipping install
) else (
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] npm install failed
        pause
        exit /b 1
    )
    echo   npm dependencies installed
)
cd ..

rem ==================== 5. data dir + .env ====================
echo [5/5] Preparing configuration...
if not exist "backend\data" (
    mkdir backend\data
    echo   Created backend\data\
) else (
    echo   backend\data\ exists
)

if not exist "backend\.env" (
    if exist "backend\.env.example" (
        copy backend\.env.example backend\.env >nul
        echo   Created backend\.env from .env.example
    ) else (
        echo   [INFO] No .env.example found, skipping .env creation
    )
) else (
    echo   backend\.env already exists
)

echo.
echo ============================================
echo  Setup complete!
echo.
echo  Quick start:
echo    start-all.bat     - Launch both services
echo    back-starter.bat  - Launch backend only
echo    front-starter.bat - Launch frontend only
echo.
echo  URLs:
echo    Frontend: http://localhost:5173
echo    Backend:  http://localhost:8000
echo    Docs:     http://localhost:8000/docs
echo ============================================
echo.
pause
