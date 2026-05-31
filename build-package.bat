@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "PY_VERSION=3.12.7"
set "PY_TAG=python%PY_VERSION:.=%"
set "PY_DIR=backend\portable-python"

echo ============================================
echo  Build Portable Package - MultiAgent Kanban
echo ============================================
echo.
echo  This script downloads and pre-installs everything
echo  into the project, creating a self-contained package
echo  that works WITHOUT network access on the target machine.
echo.
echo  Target Python: %PY_VERSION%
echo  Target dir:    %PY_DIR%
echo.

rem ==================== 1. Check prerequisites ====================
echo [1/6] Checking prerequisites...

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found on this machine.
    echo   Need Python to build the portable package.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo   Build Python: %%v

where curl >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] curl not found.
    echo   curl is required to download Python portable zip.
    pause
    exit /b 1
)
echo   curl found

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found.
    pause
    exit /b 1
)
for /f "delims=" %%v in ('node --version') do echo   Node.js %%v
echo.

rem ==================== 2. Download portable Python ====================
echo [2/6] Downloading portable Python %PY_VERSION%...

if exist "%PY_DIR%\python.exe" (
    echo   Portable Python already exists, skipping download.
    goto :install_pip
)

if not exist "%PY_DIR%" mkdir "%PY_DIR%"

set "PY_URL=https://www.python.org/ftp/python/%PY_VERSION%/%PY_TAG%-embed-amd64.zip"
set "PY_ZIP=%TEMP%\%PY_TAG%-embed-amd64.zip"

echo   Downloading from: %PY_URL%
curl -L -o "%PY_ZIP%" "%PY_URL%" --progress-bar
if %errorlevel% neq 0 (
    echo [ERROR] Failed to download Python embeddable zip.
    echo   Check network or try a different mirror.
    pause
    exit /b 1
)

echo   Extracting to %PY_DIR%...
tar -xf "%PY_ZIP%" -C "%PY_DIR%"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to extract Python zip.
    pause
    exit /b 1
)
echo   Portable Python extracted
echo.

rem ==================== 3. Install pip ====================
:install_pip
echo [3/6] Installing pip into portable Python...

set "PY_EXE=%PY_DIR%\python.exe"

if not exist "%PY_EXE%" (
    echo [ERROR] python.exe not found in %PY_DIR%
    pause
    exit /b 1
)

rem Enable site-packages in the embeddable Python
rem The _pth file controls module search paths for embeddable Python
rem We need to uncomment "import site" so pip-installed packages are found
for %%f in ("%PY_DIR%\*.%PY_TAG:~-3%._pth") do (
    echo   Found _pth file: %%f
    rem Read current content and write modified version
    set "PTH_FILE=%%f"
)

if not defined PTH_FILE (
    echo [WARN] No ._pth file found, creating one...
    echo %PY_TAG:~-3%.zip > "%PY_DIR%\%PY_TAG:~-3%._pth"
    echo . >> "%PY_DIR%\%PY_TAG:~-3%._pth"
    echo import site >> "%PY_DIR%\%PY_TAG:~-3%._pth"
    set "PTH_FILE=%PY_DIR%\%PY_TAG:~-3%._pth"
)

rem Edit the _pth file to uncomment import site
rem We do this by checking and rewriting line by line
set "TEMP_PTH=%TEMP%\_pth_edit.txt"
if exist "%TEMP_PTH%" del "%TEMP_PTH%"
set "SITE_FOUND=0"
for /f "usebackq delims=" %%a in ("%PTH_FILE%") do (
    set "line=%%a"
    setlocal enabledelayedexpansion
    if "!line!"=="#import site" (
        echo import site>>"%TEMP_PTH%"
        set SITE_FOUND=1
    ) else (
        echo !line!>>"%TEMP_PTH%"
    )
    endlocal
)
copy /y "%TEMP_PTH%" "%PTH_FILE%" >nul
del "%TEMP_PTH%"

rem Download and run get-pip.py
set "GET_PIP=%TEMP%\get-pip.py"
echo   Downloading get-pip.py...
curl -L -o "%GET_PIP%" "https://bootstrap.pypa.io/get-pip.py" --progress-bar
if %errorlevel% neq 0 (
    echo [ERROR] Failed to download get-pip.py.
    pause
    exit /b 1
)

echo   Installing pip...
"%PY_EXE%" "%GET_PIP%" --no-warn-script-location
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install pip.
    pause
    exit /b 1
)
echo   pip installed
echo.

rem ==================== 4. Install Python packages ====================
echo [4/6] Installing Python packages into portable Python...

cd backend
"%PY_DIR%\python.exe" -m pip install -r requirements.txt --no-warn-script-location
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Python packages.
    pause
    exit /b 1
)
echo   All Python packages installed
cd ..
echo.

rem ==================== 5. Install npm packages ====================
echo [5/6] Installing npm packages...
cd frontend
if exist "node_modules" (
    echo   node_modules already exists, skipping install.
) else (
    call npm install
    if %errorlevel% neq 0 (
        echo [ERROR] npm install failed.
        pause
        exit /b 1
    )
    echo   npm packages installed
)
cd ..
echo.

rem ==================== 6. Prepare config ====================
echo [6/6] Preparing configuration files...

if not exist "backend\data" (
    mkdir backend\data
    echo   Created backend\data\
)

if not exist "backend\.env" (
    if exist "backend\.env.example" (
        copy backend\.env.example backend\.env >nul
        echo   Created .env from .env.example
        rem Enable claude_git_bash_path by default for portable use
        echo.>> backend\.env
        echo MULTIAGENT_CLAUDE_GIT_BASH_PATH=>> backend\.env
    )
) else (
    echo   .env already exists
)

echo.
echo ============================================
echo  Package build complete!
echo.
echo  To distribute, zip the entire project folder
echo  (including portable-python and node_modules).
echo.
echo  On the target machine, users just need to:
echo    1. Unzip the package
echo    2. Run start-all.bat  (auto-detects portable Python)
echo.
echo  No internet, no Python, no Node.js required!
echo.
echo  Total size of portable-python:
dir /s "%PY_DIR%" | find "File(s)"
echo ============================================
echo.
pause
