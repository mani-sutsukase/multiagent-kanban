@echo off
echo ============================================
echo  Starting Frontend - MultiAgent Kanban System
echo ============================================
echo.

cd /d "%~dp0frontend"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to enter directory: %~dp0frontend
    pause
    exit /b 1
)

echo [1/3] Checking Node.js...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Please install Node.js and add it to PATH.
    pause
    exit /b 1
)
for /f "delims=" %%v in ('node --version') do echo   Node.js %%v
for /f "delims=" %%v in ('npm --version') do echo   npm v%%v

echo [2/3] Checking node_modules...
if not exist "node_modules" (
    echo   Installing npm dependencies...
    call npm install
    if %errorlevel% neq 0 (
        echo   [ERROR] npm install failed
        pause
        exit /b 1
    )
    echo   Dependencies installed
) else (
    echo   node_modules exists, skipping install
)

echo [3/3] Starting Vite dev server...
echo.
echo   Local:   http://localhost:5173
echo   Backend: proxied to http://localhost:8000
echo.
echo   Press Ctrl+C to stop
echo ============================================
echo.

npm run dev

pause
