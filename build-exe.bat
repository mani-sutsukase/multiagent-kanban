@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "EXE_NAME=MultiAgentKanban"
set "OUTPUT_DIR=dist-exe"

echo ============================================
echo  Build EXE - MultiAgent Kanban
echo  (PyInstaller single-file executable)
echo ============================================
echo.

rem ==================== 1. Check prerequisites ====================
echo [1/5] Checking prerequisites...

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo   Python: %%v

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found.
    pause
    exit /b 1
)
for /f "delims=" %%v in ('node --version') do echo   Node.js: %%v

where pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo   PyInstaller not found, installing...
    pip install pyinstaller
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install PyInstaller.
        pause
        exit /b 1
    )
    echo   PyInstaller installed.
) else (
    echo   PyInstaller found.
)
echo.

rem ==================== 2. Build frontend ====================
echo [2/5] Building frontend...
cd frontend
if not exist "node_modules" (
    echo   Installing npm dependencies...
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] npm install failed.
        cd ..
        pause
        exit /b 1
    )
)
echo   Running npm run build...
call npm run build
if %errorlevel% neq 0 (
    echo [ERROR] Frontend build failed.
    cd ..
    pause
    exit /b 1
)
echo   Frontend built successfully: frontend\dist\
cd ..
echo.

rem ==================== 3. Install backend dependencies ====================
echo [3/5] Installing Python dependencies (for PyInstaller)...
pip install -r backend\requirements.txt
if %errorlevel% neq 0 (
    echo [WARN] pip install had warnings, continuing anyway...
)
echo.

rem ==================== 4. Build EXE with PyInstaller ====================
echo [4/5] Building EXE with PyInstaller (this may take a few minutes)...

if exist "%OUTPUT_DIR%" (
    echo   Cleaning previous output...
    rmdir /s /q "%OUTPUT_DIR%"
)
mkdir "%OUTPUT_DIR%" >nul 2>&1

rem Run PyInstaller from the backend directory so "app" package is importable
cd backend

echo   Running PyInstaller --onefile...
pyinstaller --onefile ^
    --name "%EXE_NAME%" ^
    --distpath "..\%OUTPUT_DIR%" ^
    --workpath "..\build-temp" ^
    --specpath "." ^
    --add-data "..\frontend\dist;frontend\dist" ^
    --collect-all uvicorn ^
    --collect-all sqlalchemy ^
    --collect-all apscheduler ^
    --hidden-import aiosqlite ^
    --hidden-import pydantic_settings ^
    --hidden-import multipart ^
    --hidden-import app.config ^
    --hidden-import app.database ^
    --hidden-import app.websocket_manager ^
    --hidden-import app.models.card ^
    --hidden-import app.models.kanban ^
    --hidden-import app.models.log ^
    --hidden-import app.models.approval ^
    --hidden-import app.models.schedule ^
    --hidden-import app.models.setting ^
    --hidden-import app.routers.kanbans ^
    --hidden-import app.routers.cards ^
    --hidden-import app.routers.approvals ^
    --hidden-import app.routers.logs ^
    --hidden-import app.routers.schedules ^
    --hidden-import app.routers.settings ^
    --hidden-import app.routers.browse ^
    --hidden-import app.routers.ws ^
    --hidden-import app.services.kanban_service ^
    --hidden-import app.services.card_service ^
    --hidden-import app.services.card_engine ^
    --hidden-import app.services.agent_engine ^
    --hidden-import app.services.approval_service ^
    --hidden-import app.services.schedule_engine ^
    --hidden-import app.services.log_service ^
    --hidden-import app.services.file_writer ^
    app\main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] PyInstaller build failed.
    cd ..
    pause
    exit /b 1
)

cd ..
echo.

rem ==================== 5. Clean up & verify ====================
echo [5/5] Cleaning up...

if exist "build-temp" (
    rmdir /s /q "build-temp"
)

rem Remove .spec file from backend directory (keep only in output)
if exist "backend\%EXE_NAME%.spec" (
    copy "backend\%EXE_NAME%.spec" "%OUTPUT_DIR%\%EXE_NAME%.spec" >nul
    del "backend\%EXE_NAME%.spec"
)

echo.
echo ============================================
echo  EXE build complete!
echo.
echo  Output: %OUTPUT_DIR%\%EXE_NAME%.exe
echo.
echo  Usage:
echo    1. %OUTPUT_DIR%\%EXE_NAME%.exe
echo       (starts server on http://localhost:8000)
echo.
echo    2. %OUTPUT_DIR%\%EXE_NAME%.exe --port 8080
echo       (starts server on custom port)
echo.
echo  To stop: press Ctrl+C in the console window
echo.
echo  NOTE: The EXE needs claude.exe accessible from PATH
echo        (or set MULTIAGENT_CLAUDE_PATH env var)
echo.
echo  Total size:
dir "%OUTPUT_DIR%\%EXE_NAME%.exe" | find "File(s)"
echo ============================================
echo.
pause
