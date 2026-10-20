@echo off
setlocal

echo ========================================================
echo             RUIN RUNNER — ENGINE V3
echo   High-Performance 2D Action RPG / Co-op Soulslike
echo ========================================================

set "PYTHONPATH=%~dp0;%~dp0src;%PYTHONPATH%"

set "PYTHON_EXE=python"
if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe"
)

"%PYTHON_EXE%" "%~dp0main.py" %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Game terminated unexpectedly with code %ERRORLEVEL%.
    pause
)

endlocal
