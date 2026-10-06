"""
Ruin Engine V3.0 — High-Performance Surface & Buffer Pool.
Eliminates runtime Garbage Collection overhead by pooling and recycling Pygame Surfaces.
"""

import pygame
from typing import Dict, List, Tuple

class SurfacePool:
    """
    Object pool for Pygame surfaces to prevent memory allocations and GC spikes during render passes.
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
        self._pools: Dict[Tuple[int, int, int], List[pygame.Surface]] = {}
        self._active_leases: int = 0
        self._total_created: int = 0
        self._cache_hits: int = 0
        self._initialized = True

    def acquire(self, width: int, height: int, flags: int = pygame.SRCALPHA) -> pygame.Surface:
        """
        Acquires a recycled surface matching the requested dimensions and flags.
        Clears the surface to transparent black before returning.
        """
        key = (width, height, flags)
        pool = self._pools.setdefault(key, [])
        if pool:
            surf = pool.pop()
            self._cache_hits += 1
            surf.fill((0, 0, 0, 0))
            self._active_leases += 1
            return surf

        # Create new surface if pool empty
        surf = pygame.Surface((width, height), flags)
        self._total_created += 1
        self._active_leases += 1
        return surf

    def release(self, surface: pygame.Surface) -> None:
        """
        Returns a surface back to the pool for future reuse.
        """
        if surface is None:
            return
        key = (surface.get_width(), surface.get_height(), surface.get_flags())
        pool = self._pools.setdefault(key, [])
        # Cap pool size per resolution key to avoid excessive VRAM/RAM retention
        if len(pool) < 32:
            pool.append(surface)
        self._active_leases = max(0, self._active_leases - 1)

    def clear(self) -> None:
        """Flushes all pooled surfaces from memory."""
        self._pools.clear()
        self._active_leases = 0

    def get_stats(self) -> dict:
        """Returns diagnostic telemetry for the profiler."""
        pooled_count = sum(len(p) for p in self._pools.values())
        return {
            "pooled_surfaces": pooled_count,
            "active_leases": self._active_leases,
            "total_created": self._total_created,
            "cache_hits": self._cache_hits
        }


# Global surface pool instance
SURFACE_POOL = SurfacePool()
