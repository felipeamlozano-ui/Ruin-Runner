@echo off
setlocal

echo ========================================================
echo             RUIN RUNNER — ENGINE V3
echo   High-Performance 2D Action RPG / Co-op Soulslike
echo ========================================================

set "PYTHONPATH=%~dp0;%~dp0src;%PYTHONPATH%"

python "%~dp0main.py" %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Game terminated unexpectedly with code %ERRORLEVEL%.
    pause
)

endlocal
