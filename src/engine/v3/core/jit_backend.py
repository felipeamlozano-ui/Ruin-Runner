"""
Ruin Engine V3.0 — JIT Compilation & Hardware Acceleration Backend.
Provides transparent Numba JIT acceleration with zero-cost fallback to NumPy SIMD.
"""

from typing import Callable, Any
import functools
import logging

logger = logging.getLogger("RuinEngineV3.JIT")

_NUMBA_AVAILABLE = False
_NUMBA_VERSION = "N/A"

try:
    import numba
    from numba import njit, prange, float32, int32, boolean
    _NUMBA_AVAILABLE = True
    _NUMBA_VERSION = numba.__version__
except ImportError:
    njit = None
    prange = range
    float32 = float
    int32 = int
    boolean = bool


def jit_compile(fastmath: bool = True, parallel: bool = False, nogil: bool = True) -> Callable:
    """
    Decorator for compiling numerical kernels with Numba when available.
    Falls back gracefully to regular Python execution if Numba is unavailable.
    """
    def decorator(func: Callable) -> Callable:
        if _NUMBA_AVAILABLE and njit is not None:
            try:
                compiled = njit(fastmath=fastmath, parallel=parallel, nogil=nogil)(func)
                return compiled
            except Exception as e:
                logger.warning(f"JIT compilation failed for {func.__name__}, using native Python: {e}")
                return func
        return func
    return decorator


def is_jit_enabled() -> bool:
    """Returns True if Numba JIT compiler is active and operational."""
    return _NUMBA_AVAILABLE


def get_jit_info() -> dict[str, Any]:
    """Returns hardware acceleration diagnostic information."""
    return {
        "numba_available": _NUMBA_AVAILABLE,
        "numba_version": _NUMBA_VERSION,
        "backend": "Numba LLVM JIT (FastMath)" if _NUMBA_AVAILABLE else "NumPy SIMD Fallback"
    }
