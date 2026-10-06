@echo off
setlocal

echo ========================================================
echo Ruin Runner — Production Benchmark & Stress Test Runner
echo Target: AMD Ryzen 5 5500U / Vega 7 iGPU / 8GB RAM
echo ========================================================

set "PYTHONPATH=%~dp0;%~dp0src;%PYTHONPATH%"

python "%~dp0tests\benchmark_suite.py" %*

if %ERRORLEVEL% equ 0 (
    echo.
    echo [SUCCESS] Benchmark suite completed!
    echo Baseline recorded at performance_baseline.json
) else (
    echo.
    echo [ERROR] Benchmark encountered errors (code: %ERRORLEVEL%).
)

endlocal
