@echo off
setlocal enabledelayedexpansion

echo =======================================================
echo Ruin Runner - Native C Engine Extension Builder (AVX2)
echo =======================================================

set GCC_CMD=gcc
where gcc >nul 2>&1
if %ERRORLEVEL% neq 0 (
    if exist "C:\msys64\ucrt64\bin\gcc.exe" (
        set "GCC_CMD=C:\msys64\ucrt64\bin\gcc.exe"
    ) else if exist "C:\msys64\mingw64\bin\gcc.exe" (
        set "GCC_CMD=C:\msys64\mingw64\bin\gcc.exe"
    ) else (
        echo [ERROR] GCC compiler not found in PATH or MSYS2 locations.
        echo Please ensure GCC is installed with AVX2 and OpenMP support.
        exit /b 1
    )
)

echo Using compiler: %GCC_CMD%
set SRC=src\engine\v3\native\ruin_native.c
set OUT=src\engine\v3\native\ruin_native.dll

echo Compiling %SRC% with -O3 -mavx2 -mfma -fopenmp -static -static-libgcc...
"%GCC_CMD%" -O3 -shared -fPIC -mavx2 -mfma -fopenmp -static -static-libgcc "%SRC%" -o "%OUT%"

if %ERRORLEVEL% equ 0 (
    echo [SUCCESS] Compiled %OUT% successfully!
    dir "%OUT%"
) else (
    echo [ERROR] Native compilation failed with exit code %ERRORLEVEL%.
    exit /b %ERRORLEVEL%
)

endlocal
