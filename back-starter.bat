@echo off
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

echo [3/3] Starting Uvicorn server...
echo.
echo   API:     http://localhost:8000
echo   Swagger: http://localhost:8000/docs
echo   Health:  http://localhost:8000/api/health
echo.
echo   Press Ctrl+C to stop
echo ============================================
echo.

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause
