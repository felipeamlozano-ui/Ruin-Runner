"""
Ruin Engine V3.0 — Memory Manager & GC Governor.
Monitors memory consumption, tracks simulated VRAM buffers, and orchestrates GC cycles during idle intervals.
"""

import gc
import os
import sys
import time
from typing import Dict, Any

class MemoryManager:
    """
    Orchestrates memory utilization, prevents mid-combat GC pauses,
    and tracks resource footprints across surfaces, textures, and geometry caches.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self.tracked_surfaces_bytes: int = 0
        self.tracked_textures_bytes: int = 0
        self.last_gc_time: float = time.perf_counter()
        self.gc_interval_seconds: float = 30.0
        self.gc_disabled_in_gameplay: bool = False
        
        # Configure Garbage Collector for high throughput
        gc.enable()
        gc.set_threshold(1000, 15, 15)
            
        self._initialized = True

    def register_surface(self, width: int, height: int, bytes_per_pixel: int = 4) -> None:
        """Tracks allocation of raw surface buffers."""
        self.tracked_surfaces_bytes += width * height * bytes_per_pixel

    def unregister_surface(self, width: int, height: int, bytes_per_pixel: int = 4) -> None:
        """Removes untracked surface buffers."""
        self.tracked_surfaces_bytes = max(0, self.tracked_surfaces_bytes - (width * height * bytes_per_pixel))

    def collect_safely(self, force: bool = False) -> int:
        """
        Executes a controlled garbage collection cycle during non-time-critical frames
        (e.g., scene transition, loading, pause screen).
        """
        now = time.perf_counter()
        if force or (now - self.last_gc_time > self.gc_interval_seconds):
            gc.enable()
            collected = gc.collect()
            if self.gc_disabled_in_gameplay:
                gc.disable()
            self.last_gc_time = now
            return collected
        return 0

    def get_memory_stats(self) -> Dict[str, Any]:
        """Returns comprehensive memory telemetry in Megabytes."""
        ram_mb = 0.0
        try:
            import psutil
            process = psutil.Process(os.getpid())
            ram_mb = process.memory_info().rss / (1024 * 1024)
        except Exception:
            # Fallback estimation for Windows without psutil
            try:
                import ctypes
                class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                    _fields_ = [
                        ('cb', ctypes.c_ulong),
                        ('PageFaultCount', ctypes.c_ulong),
                        ('PeakWorkingSetSize', ctypes.c_size_t),
                        ('WorkingSetSize', ctypes.c_size_t),
                        ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                        ('PagefileUsage', ctypes.c_size_t),
                        ('PeakPagefileUsage', ctypes.c_size_t),
                    ]
                counters = PROCESS_MEMORY_COUNTERS()
                counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
                ctypes.windll.psapi.GetProcessMemoryInfo(
                    ctypes.windll.kernel32.GetCurrentProcess(),
                    ctypes.byref(counters),
                    counters.cb
                )
                ram_mb = counters.WorkingSetSize / (1024 * 1024)
            except Exception:
                ram_mb = 128.0

        vram_mb = (self.tracked_surfaces_bytes + self.tracked_textures_bytes) / (1024 * 1024)
        return {
            "ram_mb": round(ram_mb, 1),
            "vram_mb": round(vram_mb, 1),
            "gc_count": gc.get_count(),
            "gc_disabled": not gc.isenabled()
        }


MEMORY_MANAGER = MemoryManager()
