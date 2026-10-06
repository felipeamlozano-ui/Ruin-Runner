#!/usr/bin/env bash
set -e

echo "======================================================="
echo "Ruin Runner - Native C Engine Extension Builder (AVX2)"
echo "======================================================="

CC=${CC:-gcc}
SRC="src/engine/v3/native/ruin_native.c"

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    OUT="src/engine/v3/native/ruin_native.dylib"
    FLAGS="-O3 -shared -fPIC -mavx2 -mfma -Xpreprocessor -fopenmp -lomp"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    OUT="src/engine/v3/native/ruin_native.dll"
    FLAGS="-O3 -shared -fPIC -mavx2 -mfma -fopenmp -static-libgcc"
else
    OUT="src/engine/v3/native/ruin_native.so"
    FLAGS="-O3 -shared -fPIC -mavx2 -mfma -fopenmp"
fi

echo "Compiling $SRC -> $OUT using $CC with AVX2 and OpenMP..."
$CC $FLAGS "$SRC" -o "$OUT"

if [ $? -eq 0 ]; then
    echo "[SUCCESS] Compiled $OUT successfully!"
    ls -lh "$OUT"
else
    echo "[ERROR] Native compilation failed."
    exit 1
fi
