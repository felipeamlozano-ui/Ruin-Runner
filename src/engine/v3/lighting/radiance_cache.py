"""
Ruin Engine V3.0 — Radiance Cache for Static & Dynamic Light Separation.
Bakes static environmental light sources to a cached buffer, completely eliminating redundant re-computation.
"""

import pygame
from typing import List, Tuple, Optional
from engine.v3.core.profiler import PROFILER

class StaticLight:
    def __init__(self, x: float, y: float, radius: float, color: Tuple[int, int, int], intensity: float = 1.0):
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.intensity = intensity

class RadianceCache:
    """
    Decouples persistent static illumination from per-frame dynamic light sources.
    """
    def __init__(self, map_width: int, map_height: int):
        self.map_w = map_width
        self.map_h = map_height
        self.static_lights: List[StaticLight] = []
        self.cached_radiance: Optional[pygame.Surface] = None
        self.dirty: bool = True

    def add_static_light(self, x: float, y: float, radius: float, color: Tuple[int, int, int], intensity: float = 1.0) -> None:
        self.static_lights.append(StaticLight(x, y, radius, color, intensity))
        self.dirty = True

    def clear(self) -> None:
        self.static_lights.clear()
        self.cached_radiance = None
        self.dirty = True

    def bake_static_radiance(self) -> None:
        """Bakes all static point lights into the world radiance map."""
        if not self.dirty and self.cached_radiance is not None:
            return

        self.cached_radiance = pygame.Surface((self.map_w, self.map_h), pygame.SRCALPHA)
        self.cached_radiance.fill((0, 0, 0, 0))

        for sl in self.static_lights:
            rad = int(sl.radius)
            light_surf = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
            r, g, b = sl.color[:3]
            alpha_max = int(255 * sl.intensity)

            for step in range(rad, 0, -3):
                ratio = 1.0 - (step / rad)
                alpha = int(alpha_max * (ratio ** 2.0))
                pygame.draw.circle(light_surf, (r, g, b, alpha), (rad, rad), step)

            dest_x = int(sl.x - rad)
            dest_y = int(sl.y - rad)
            self.cached_radiance.blit(light_surf, (dest_x, dest_y), special_flags=pygame.BLEND_RGBA_ADD)

        self.dirty = False

    def render_to_camera(self, target_surface: pygame.Surface, camera_offset: pygame.math.Vector2, viewport_w: int, viewport_h: int) -> None:
        """Blits the visible viewport slice of the static radiance map in O(1)."""
        self.bake_static_radiance()
        if self.cached_radiance:
            sub_rect = pygame.Rect(int(camera_offset.x), int(camera_offset.y), viewport_w, viewport_h)
            sub_rect.clamp_ip(self.cached_radiance.get_rect())
            target_surface.blit(self.cached_radiance, (0, 0), area=sub_rect, special_flags=pygame.BLEND_RGBA_ADD)
            PROFILER.record_draw_calls(1)
