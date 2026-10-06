"""
Ruin Engine V3.0 — Chunk-Based Tilemap Renderer with Frustum Culling.
Breaks world tilemaps into discrete cached chunks (16x16, 32x32, 64x64)
to achieve zero draw-call overhead on static environments.
"""

import pygame
from typing import Dict, Tuple, List, Optional
from engine.v3.core.surface_pool import SURFACE_POOL
from engine.v3.core.profiler import PROFILER

class Chunk:
    """Represents a cached spatial partition of map tiles."""
    def __init__(self, chunk_x: int, chunk_y: int, chunk_size: int, tile_size: int):
        self.chunk_x = chunk_x
        self.chunk_y = chunk_y
        self.chunk_size = chunk_size
        self.tile_size = tile_size
        self.pixel_w = chunk_size * tile_size
        self.pixel_h = chunk_size * tile_size
        self.world_x = chunk_x * self.pixel_w
        self.world_y = chunk_y * self.pixel_h
        
        self.dirty: bool = True
        self.surface: Optional[pygame.Surface] = None
        self.tiles: Dict[Tuple[int, int], pygame.Surface] = {}

    def set_tile(self, local_x: int, local_y: int, tile_surface: pygame.Surface) -> None:
        self.tiles[(local_x, local_y)] = tile_surface
        self.dirty = True

    def bake(self) -> None:
        """Bakes all tiles into the chunk surface cache."""
        if not self.dirty and self.surface is not None:
            return

        if self.surface is None:
            self.surface = pygame.Surface((self.pixel_w, self.pixel_h), pygame.SRCALPHA)
        else:
            self.surface.fill((0, 0, 0, 0))

        for (lx, ly), tile_surf in self.tiles.items():
            px = lx * self.tile_size
            py = ly * self.tile_size
            self.surface.blit(tile_surf, (px, py))

        self.dirty = False

    def free(self) -> None:
        self.surface = None
        self.dirty = True


class ChunkRenderer:
    """
    Manages chunk allocation, frustum culling, and batch blitting.
    """
    def __init__(self, chunk_size: int = 32, tile_size: int = 16):
        self.chunk_size = chunk_size  # 16x16, 32x32, or 64x64 tiles
        self.tile_size = tile_size
        self.chunks: Dict[Tuple[int, int], Chunk] = {}

    def set_chunk_size(self, size: int) -> None:
        if size in (16, 32, 64):
            self.chunk_size = size
            self.chunks.clear()

    def get_chunk(self, world_x: float, world_y: float) -> Chunk:
        pixel_chunk = self.chunk_size * self.tile_size
        cx = int(world_x // pixel_chunk)
        cy = int(world_y // pixel_chunk)
        key = (cx, cy)
        if key not in self.chunks:
            self.chunks[key] = Chunk(cx, cy, self.chunk_size, self.tile_size)
        return self.chunks[key]

    def add_tile(self, tile_x: int, tile_y: int, tile_surf: pygame.Surface) -> None:
        """Adds a tile using global tile coordinates."""
        cx = tile_x // self.chunk_size
        cy = tile_y // self.chunk_size
        lx = tile_x % self.chunk_size
        ly = tile_y % self.chunk_size

        key = (cx, cy)
        if key not in self.chunks:
            self.chunks[key] = Chunk(cx, cy, self.chunk_size, self.tile_size)
        self.chunks[key].set_tile(lx, ly, tile_surf)

    def render(self, target_surface: pygame.Surface, camera_offset: pygame.math.Vector2, viewport_w: int, viewport_h: int) -> int:
        """
        Frustum-culls and blits only visible chunks.
        Returns the number of visible chunks drawn.
        """
        view_rect = (camera_offset.x, camera_offset.y, viewport_w, viewport_h)
        drawn_count = 0

        for chunk in self.chunks.values():
            # Frustum culling AABB check
            if (chunk.world_x + chunk.pixel_w < view_rect[0] or
                chunk.world_x > view_rect[0] + view_rect[2] or
                chunk.world_y + chunk.pixel_h < view_rect[1] or
                chunk.world_y > view_rect[1] + view_rect[3]):
                continue

            chunk.bake()
            if chunk.surface:
                screen_x = int(chunk.world_x - camera_offset.x)
                screen_y = int(chunk.world_y - camera_offset.y)
                target_surface.blit(chunk.surface, (screen_x, screen_y))
                drawn_count += 1
                PROFILER.record_draw_calls(1)

        PROFILER.record_chunks(drawn_count)
        return drawn_count
