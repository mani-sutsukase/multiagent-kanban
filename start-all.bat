@echo off
cd /d "%~dp0"

echo ============================================
echo  Start All - MultiAgent Kanban System
echo ============================================
echo.

rem ====== 检查环境是否已搭建 ======
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
start http://localhost:5173

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
