@echo off
cd /d "%~dp0"

echo ============================================
echo  Start All - MultiAgent Kanban System
echo ============================================
echo.

rem ====== 检测 EXE 模式（单文件可执行） ======
if exist "dist-exe\MultiAgentKanban.exe" (
    echo [MODE] EXE package detected - starting single executable...
    echo.
    echo   The EXE serves both frontend and backend on one port.
    echo   Press Ctrl+C in the EXE window to stop.
    echo.
    start "MultiAgentKanban" /D "%~dp0" cmd /k "dist-exe\MultiAgentKanban.exe"
    timeout /t 3 /nobreak >nul
    echo Opening browser...
    powershell -Command "Start-Process 'http://localhost:8000'"
    echo   [如果浏览器未打开，请手动访问 http://localhost:8000]
    echo.
    echo ============================================
    echo  MultiAgent Kanban started!
    echo.
    echo   Open: http://localhost:8000
    echo   Docs: http://localhost:8000/docs
    echo.
    echo  Close the EXE window to stop
    echo ============================================
    echo.
    pause
    exit /b 0
)

rem ====== 检测便携包模式 ======
if exist "backend\portable-python\python.exe" (
    echo [MODE] Portable package detected - skipping setup check
    goto :start_services
)

if not exist "backend\venv\Scripts\activate.bat" (
    if not exist "backend\.venv\Scripts\activate.bat" (
        echo [INFO] Virtual environment not found.
        echo.
        echo   Choose an option:
        echo   1. Run setup.bat first (recommended for first-time users)
        echo   2. Continue anyway (if you already have dependencies)
        echo.
        choice /c:12 /n /m "Press 1 for setup, 2 to continue: "
        if errorlevel 2 goto :check_frontend
        echo.
        echo   Starting setup...
        echo.
        call setup.bat
        if %errorlevel% neq 0 (
            echo [ERROR] Setup failed. Please fix the issues and try again.
            pause
            exit /b 1
        )
        echo   Setup complete, starting services...
        echo.
        goto :start_services
    )
)

:check_frontend
if not exist "frontend\node_modules" (
    echo [INFO] frontend\node_modules not found.
    echo.
    echo   Choose an option:
    echo   1. Run setup.bat first (recommended for first-time users)
    echo   2. Continue anyway (may fail if dependencies are missing)
    echo.
    choice /c:12 /n /m "Press 1 for setup, 2 to continue: "
    if errorlevel 2 goto :start_services
    echo.
    echo   Starting setup...
    echo.
    call setup.bat
    if %errorlevel% neq 0 (
        echo [ERROR] Setup failed. Please fix the issues and try again.
        pause
        exit /b 1
    )
    echo   Setup complete, starting services...
)

:start_services
echo [1/2] Starting Backend (new window)...
setlocal enabledelayedexpansion
set "ROOT=%~dp0"
endlocal & set "ROOT=%ROOT%"
start "Backend" /D "%ROOT%" cmd /k "back-starter.bat"
echo   Backend starting...

timeout /t 3 /nobreak >nul

echo [2/2] Starting Frontend (new window)...
start "Frontend" /D "%ROOT%" cmd /k "front-starter.bat"
echo   Frontend starting...

timeout /t 3 /nobreak >nul

echo Opening browser...
powershell -Command "Start-Process 'http://localhost:5173'"
echo   [如果浏览器未打开，请手动访问 http://localhost:5173]

echo.
echo ============================================
echo  Both services started!
echo.
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo   Docs:     http://localhost:8000/docs
echo.
echo  Close all windows to stop
echo ============================================
echo.
pause
