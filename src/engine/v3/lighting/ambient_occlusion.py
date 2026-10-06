"""
Ruin Engine V3.0 — 2D Screen Space Ambient Occlusion (SSAO 2D).
Darkens solid corners, crevices, walls, and ground contact points.
Includes a static geometry cache and a dynamic proximity AO pass.
"""

import pygame
from typing import List, Tuple, Dict
from engine.v3.core.surface_pool import SURFACE_POOL
from engine.v3.core.profiler import PROFILER

class AmbientOcclusion2D:
    """
    Computes 2D contact shadow ambient occlusion for corners, crevices, and entities.
    """
    def __init__(self, tile_size: int = 16):
        self.tile_size = tile_size
        self._static_cache: Dict[Tuple[int, int], pygame.Surface] = {}

    def bake_corner_occlusion(
        self,
        grid_width: int,
        grid_height: int,
        solid_mask: List[List[bool]],
        ao_radius: int = 12
    ) -> pygame.Surface:
        """
        Bakes static ambient occlusion crevices into a reusable texture map.
        Darkens internal corners and platform underbellies.
        """
        pixel_w = grid_width * self.tile_size
        pixel_h = grid_height * self.tile_size
        ao_surf = pygame.Surface((pixel_w, pixel_h), pygame.SRCALPHA)
        ao_surf.fill((255, 255, 255, 255))  # Multiplicative identity

        # Darken along solid perimeter
        for gy in range(grid_height):
            for gx in range(grid_width):
                if not solid_mask[gy][gx]:
                    continue

                px = gx * self.tile_size
                py = gy * self.tile_size

                # Check top edge
                if gy > 0 and not solid_mask[gy - 1][gx]:
                    for step in range(ao_radius):
                        val = int(255 - 45 * (1.0 - step / ao_radius))
                        pygame.draw.line(ao_surf, (val, val, val, 255), (px, py - step), (px + self.tile_size, py - step))

                # Check bottom edge (under platform)
                if gy < grid_height - 1 and not solid_mask[gy + 1][gx]:
                    for step in range(ao_radius):
                        val = int(255 - 70 * (1.0 - step / ao_radius))
                        pygame.draw.line(ao_surf, (val, val, val, 255), (px, py + self.tile_size + step), (px + self.tile_size, py + self.tile_size + step))

                # Check left edge
                if gx > 0 and not solid_mask[gy][gx - 1]:
                    for step in range(ao_radius):
                        val = int(255 - 50 * (1.0 - step / ao_radius))
                        pygame.draw.line(ao_surf, (val, val, val, 255), (px - step, py), (px - step, py + self.tile_size))

                # Check right edge
                if gx < grid_width - 1 and not solid_mask[gy][gx + 1]:
                    for step in range(ao_radius):
                        val = int(255 - 50 * (1.0 - step / ao_radius))
                        pygame.draw.line(ao_surf, (val, val, val, 255), (px + self.tile_size + step, py), (px + self.tile_size + step, py + self.tile_size))

        return ao_surf

    def render_dynamic_entity_ao(
        self,
        surface: pygame.Surface,
        entities_pos: List[Tuple[float, float, float]],  # (x, y, radius)
        camera_offset: pygame.math.Vector2
    ) -> None:
        """
        Renders dynamic contact shadow auras beneath characters and dynamic props.
        """
        for x, y, radius in entities_pos:
            screen_x = int(x - camera_offset.x)
            screen_y = int(y - camera_offset.y)

            rx = int(radius)
            ry = int(radius * 0.45)
            if rx <= 0 or ry <= 0:
                continue

            shadow_surf = SURFACE_POOL.acquire(rx * 2, ry * 2, pygame.SRCALPHA)
            shadow_surf.fill((0, 0, 0, 0))

            # Concentric soft ellipse
            for step in range(ry, 0, -2):
                norm = 1.0 - (step / ry)
                alpha = int(120 * (norm ** 1.5))
                step_w = int(rx * (step / ry))
                pygame.draw.ellipse(shadow_surf, (0, 0, 0, alpha), (rx - step_w, ry - step, step_w * 2, step * 2))

            surface.blit(shadow_surf, (screen_x - rx, screen_y - ry), special_flags=pygame.BLEND_RGBA_SUB)
            SURFACE_POOL.release(shadow_surf)
            PROFILER.record_draw_calls(1)
