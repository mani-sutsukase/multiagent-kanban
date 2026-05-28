@echo off
cd /d "%~dp0"

echo ============================================
echo  Start All - MultiAgent Kanban System
echo ============================================
echo.

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
