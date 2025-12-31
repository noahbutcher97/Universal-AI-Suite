@echo off
SETLOCAL EnableDelayedExpansion
TITLE AI Universal Suite Launcher

:: 1. Check for Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    ECHO [WARN] Python is not found in PATH.
    ECHO [INIT] Attempting to install Python 3.10 via Winget...
    
    winget install -e --id Python.Python.3.10
    
    IF %ERRORLEVEL% NEQ 0 (
        ECHO [ERROR] Automatic installation failed.
        ECHO Please install Python 3.10+ manually from: https://www.python.org/downloads/
        PAUSE
        EXIT /B 1
    )
    
    :: Refresh env vars (hacky way for batch to see new path, usually requires restart)
    ECHO [INFO] Python installed. You may need to restart this script or your PC.
    PAUSE
    EXIT /B 0
)

:: 2. Check for Git
git --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    ECHO [WARN] Git is not found.
    ECHO [INIT] Attempting to install Git via Winget...
    winget install -e --id Git.Git
    IF %ERRORLEVEL% NEQ 0 (
        ECHO [ERROR] Git install failed. Please install Git manually.
    )
)

:: 3. Launch Universal Script
python "%~dp0launch.py"

IF %ERRORLEVEL% NEQ 0 (
    ECHO [ERROR] Application crashed or failed to start.
    PAUSE
)