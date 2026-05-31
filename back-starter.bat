@echo off
setlocal enabledelayedexpansion
echo ============================================
echo  Starting Backend - MultiAgent Kanban System
echo ============================================
echo.

cd /d "%~dp0backend"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to enter directory: %~dp0backend
    pause
    exit /b 1
)

rem ====== Detect Python runtime ======
if exist "portable-python\python.exe" (
    set "PY_EXE=portable-python\python.exe"
    echo [MODE] Portable Python detected - using offline runtime
    echo   %PY_EXE%
    goto :check_config
)

set "PY_EXE=python"
echo [MODE] Using system Python
goto :check_python

rem ==================== System Python checks ====================
:check_python
echo [1/3] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python and add it to PATH.
    pause
    exit /b 1
)
for /f "delims=" %%v in ('python --version 2^>^&1') do echo   %%v

echo [2/3] Checking virtual environment...
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo   Virtual env activated
) else if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo   Virtual env activated
) else (
    echo   [INFO] No virtual env found, using system Python
)

echo   Checking dependencies...
%PY_EXE% -c "import fastapi, uvicorn, sqlalchemy, aiosqlite, apscheduler, pydantic" >nul 2>&1
if %errorlevel% neq 0 (
    echo   Installing dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] pip install failed
        pause
        exit /b 1
    )
    echo   Dependencies installed
) else (
    echo   All dependencies satisfied
)
goto :check_config

rem ==================== Shared config checks ====================
:check_config
echo   Checking data directory...
if not exist "data" (
    echo   Creating data directory...
    mkdir data
) else (
    echo   data directory exists
)

if exist ".env" (
    echo   [INFO] .env file found
) else (
    echo   [INFO] No .env file, using default settings
)

echo.
echo ============================================
echo   Starting Uvicorn server...
echo   API:     http://localhost:8000
echo   Swagger: http://localhost:8000/docs
echo   Health:  http://localhost:8000/api/health
echo.
echo   Press Ctrl+C to stop
echo ============================================
echo.

%PY_EXE% -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause
