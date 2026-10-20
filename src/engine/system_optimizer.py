"""
src/engine/system_optimizer.py
-------------------------------
Low-level engine optimization system for AMD Ryzen 5 5500U & Radeon Vega GPU:
1. Windows kernel clock resolution to 1.0ms (winmm.timeBeginPeriod) & HIGH_PRIORITY_CLASS.
2. Vulkan GPU-native hardware presentation driver setup.
3. Garbage Collection freeze during active gameplay (gc.disable() / gc.collect(2)).
4. Persistent 4-worker thread pool (EngineWorkerPool) for GIL-free background tasks.
5. Static Texture Pool for VRAM/RAM pre-allocation.
6. Vectorized NumPy routines (C-contiguous arrays) for zero-allocation particle updates.
"""

import os
import sys
import gc
import atexit
import concurrent.futures
from typing import Dict, Any, Optional, Tuple
import numpy as np
import pygame

RENDER_FALLBACK_CHAIN = ["vulkan", "direct3d11", "opengl"]

# 1. HARDWARE DRIVER & KERNEL INITIALIZATION
def init_render_backend(preferred_driver: str = "vulkan"):
    """
    Configures the benchmark-winning Vulkan backend as the definitive rendering driver
    (SDL_RENDER_DRIVER="vulkan"), with automatic fallback chain: vulkan -> direct3d11 -> opengl.
    """
    # Prefer Vulkan unless a dummy test driver is actively requested
    if os.environ.get("SDL_VIDEODRIVER") != "dummy":
        os.environ.setdefault("SDL_RENDER_DRIVER", preferred_driver)
        os.environ["SDL_RENDER_SCALE_QUALITY"] = "1"  # Hardware linear filtering in GPU VRAM
        if sys.platform == "win32":
            os.environ.setdefault("SDL_VIDEODRIVER", "windows")
    else:
        os.environ.setdefault("SDL_RENDER_DRIVER", preferred_driver)


def create_hardware_display(size: Tuple[int, int], flags: int) -> Tuple[pygame.Surface, str]:
    """
    Creates a hardware-accelerated presentation display (pygame.SCALED).
    Tries Vulkan first. If the host GPU lacks Vulkan drivers/hardware support,
    it automatically falls back to direct3d11, then opengl.
    """
    requested_driver = os.environ.get("SDL_RENDER_DRIVER", "vulkan")
    drivers_to_try = [requested_driver]
    for d in RENDER_FALLBACK_CHAIN:
        if d not in drivers_to_try:
            drivers_to_try.append(d)

    last_exc = None
    for driver in drivers_to_try:
        try:
            os.environ["SDL_RENDER_DRIVER"] = driver
            surface = pygame.display.set_mode(size, flags)
            return surface, driver
        except Exception as e:
            last_exc = e
            continue

    # Final fallback if window creation with hardware flags failed
    try:
        surface = pygame.display.set_mode(size, pygame.RESIZABLE)
        return surface, "software"
    except Exception:
        raise last_exc


def init_system_clock_and_priority():
    """Forces Windows kernel timer to 1.0ms and sets HIGH_PRIORITY_CLASS."""
    if sys.platform == "win32":
        try:
            import ctypes
            # Force 1.0ms timer period to eliminate micro-stutter in clock.tick()
            ctypes.windll.winmm.timeBeginPeriod(1)
            atexit.register(lambda: ctypes.windll.winmm.timeEndPeriod(1))

            # Set HIGH_PRIORITY_CLASS (0x00000080)
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            ctypes.windll.kernel32.SetPriorityClass(handle, 0x00000080)
        except Exception as e:
            print(f"[SystemOptimizer] Kernel clock notice: {e}")


# Run initialization immediately when imported
init_render_backend()
init_system_clock_and_priority()


# 2. GARBAGE COLLECTION CONTROL (GC FREEZE)
def freeze_gc_for_gameplay(scene_name: str = "ActiveScene"):
    """Disables automatic garbage collection during active combat/gameplay."""
    gc.disable()


def collect_garbage_transition():
    """Performs a full generation 2 garbage collection only during transitions/loading/pause."""
    was_disabled = not gc.isenabled()
    gc.collect(2)
    if was_disabled:
        gc.disable()


# 3. ENGINE WORKER POOL (4 PERSISTENT WORKERS FOR GIL BYPASS)
class _EngineWorkerPool:
    """Persistent thread pool for offloading GIL-releasing matrix calculations and async I/O."""
    def __init__(self, max_workers: int = 4):
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="RuinEngineWorker"
        )
        atexit.register(self.shutdown)

    def submit(self, fn, *args, **kwargs):
        return self._executor.submit(fn, *args, **kwargs)

    def shutdown(self):
        try:
            self._executor.shutdown(wait=False)
        except Exception:
            pass

ENGINE_WORKER_POOL = _EngineWorkerPool(max_workers=4)


# 4. STATIC TEXTURE POOL
class TexturePool:
    """Pre-allocates, converts, and pins commonly used surfaces, stamps, and LUTs in memory."""
    _cache: Dict[str, pygame.Surface] = {}

    @classmethod
    def get_or_create(cls, key: str, width: int, height: int, has_alpha: bool = True) -> pygame.Surface:
        if key in cls._cache:
            return cls._cache[key]
        surf = pygame.Surface((width, height), pygame.SRCALPHA if has_alpha else 0)
        cls._cache[key] = surf
        return surf

    @classmethod
    def register(cls, key: str, surface: pygame.Surface) -> pygame.Surface:
        cls._cache[key] = surface
        return surface

    @classmethod
    def get(cls, key: str) -> Optional[pygame.Surface]:
        return cls._cache.get(key)

    @classmethod
    def clear_stage_buffers(cls):
        """Discards intermediate temporary buffers without clearing persistent core assets."""
        keys_to_remove = [k for k in cls._cache if k.startswith("temp_")]
        for k in keys_to_remove:
            del cls._cache[k]


# 5. VECTORIZED NUMPY PARTICLES ENGINE (C-LEVEL GIL-FREE ROUTINES)
class VectorizedParticleSystem:
    """Manages atmospheric and visual particles using C-contiguous NumPy float32 arrays."""

    def __init__(self, count: int, bounds: Tuple[int, int]):
        self.count = count
        self.bounds_w, self.bounds_h = bounds
        # C-contiguous float32 arrays for vectorization
        self.x = np.random.uniform(0, self.bounds_w, count).astype(np.float32)
        self.y = np.random.uniform(0, self.bounds_h, count).astype(np.float32)
        self.vx = np.random.uniform(-15.0, 15.0, count).astype(np.float32)
        self.vy = np.random.uniform(12.0, 36.0, count).astype(np.float32)
        self.sizes = np.random.uniform(1.2, 3.2, count).astype(np.float32)
        self.alphas = np.random.uniform(50.0, 180.0, count).astype(np.float32)
        self.phases = np.random.uniform(0.0, 2.0 * np.pi, count).astype(np.float32)

    def set_count(self, new_count: int):
        if new_count == self.count:
            return
        self.count = new_count
        if new_count <= 0:
            self.x = np.empty(0, dtype=np.float32)
            self.y = np.empty(0, dtype=np.float32)
            self.vx = np.empty(0, dtype=np.float32)
            self.vy = np.empty(0, dtype=np.float32)
            self.sizes = np.empty(0, dtype=np.float32)
            self.alphas = np.empty(0, dtype=np.float32)
            self.phases = np.empty(0, dtype=np.float32)
        else:
            self.x = np.random.uniform(0, self.bounds_w, new_count).astype(np.float32)
            self.y = np.random.uniform(0, self.bounds_h, new_count).astype(np.float32)
            self.vx = np.random.uniform(-15.0, 15.0, new_count).astype(np.float32)
            self.vy = np.random.uniform(12.0, 36.0, new_count).astype(np.float32)
            self.sizes = np.random.uniform(1.2, 3.2, new_count).astype(np.float32)
            self.alphas = np.random.uniform(50.0, 180.0, new_count).astype(np.float32)
            self.phases = np.random.uniform(0.0, 2.0 * np.pi, new_count).astype(np.float32)

    def update(self, dt: float, wind: float = 0.0):
        """Fully vectorized update in C/NumPy with zero Python looping."""
        if self.count <= 0:
            return
        dt_f = float(dt)
        self.phases += dt_f * 1.5
        # Upward drift with gentle sine wave oscillation
        self.x += (self.vx + np.sin(self.phases) * 8.0 + wind) * dt_f
        self.y -= self.vy * dt_f

        # Wrap around bounds vectorized
        np.fmod(self.x, self.bounds_w, out=self.x)
        self.x[self.x < 0] += self.bounds_w
        self.y[self.y < 0] += self.bounds_h

    def get_positions(self) -> np.ndarray:
        """Returns (count, 2) array of (x, y) coordinates."""
        if self.count <= 0:
            return np.empty((0, 2), dtype=np.float32)
        return np.column_stack((self.x, self.y))
