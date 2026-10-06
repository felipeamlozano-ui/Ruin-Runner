"""
Ruin Engine V3.0 — 2D Shadow Polygon & Soft Penumbra Engine.
Projects shadow quads away from light emitters with multi-ray soft penumbra interpolation.
"""

import math
import pygame
from typing import List, Tuple, Optional
from engine.v3.core.profiler import PROFILER
from engine.v3.core.surface_pool import SURFACE_POOL

class ShadowRenderer:
    """
    Constructs hard and soft shadow polygons from solid occluder geometries.
    """
    def __init__(self, shadow_length: float = 1200.0):
        self.shadow_length = shadow_length

    def project_shadow_polygon(
        self,
        lx: float,
        ly: float,
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        length_override: Optional[float] = None
    ) -> List[Tuple[float, float]]:
        """
        Extrudes a 2D line segment away from light (lx, ly) into a 4-point shadow fin quad.
        """
        length = length_override or self.shadow_length

        dx1 = p1[0] - lx
        dy1 = p1[1] - ly
        len1 = math.hypot(dx1, dy1)
        if len1 > 0:
            p1_proj = (p1[0] + (dx1 / len1) * length, p1[1] + (dy1 / len1) * length)
        else:
            p1_proj = (p1[0], p1[1] + length)

        dx2 = p2[0] - lx
        dy2 = p2[1] - ly
        len2 = math.hypot(dx2, dy2)
        if len2 > 0:
            p2_proj = (p2[0] + (dx2 / len2) * length, p2[1] + (dy2 / len2) * length)
        else:
            p2_proj = (p2[0], p2[1] + length)

        return [p1, p2, p2_proj, p1_proj]

    def render_shadow_mask(
        self,
        surface_w: int,
        surface_h: int,
        lx: float,
        ly: float,
        radius: float,
        occluders: List[Tuple[float, float, float, float]],
        camera_offset: pygame.math.Vector2,
        soft_rays: int = 1,
        shadow_alpha: int = 180,
        target_surface: Optional[pygame.Surface] = None
    ) -> pygame.Surface:
        """
        Bakes an ambient shadow mask with optional soft penumbra.
        If target_surface is provided, draws directly into it (for buffer accumulation).
        """
        if target_surface is not None:
            mask_surf = target_surface
        else:
            mask_surf = SURFACE_POOL.acquire(surface_w, surface_h, pygame.SRCALPHA)
            mask_surf.fill((0, 0, 0, 0))

        if soft_rays <= 1:
            offsets = [(0.0, 0.0)]
            pass_alpha = shadow_alpha
        else:
            # Multi-sample penumbra jittering
            offsets = [
                (-3.0, 0.0), (3.0, 0.0),
                (0.0, -3.0), (0.0, 3.0),
                (-2.0, -2.0), (2.0, 2.0)
            ][:soft_rays]
            pass_alpha = max(15, shadow_alpha // len(offsets))

        cam_x, cam_y = camera_offset.x, camera_offset.y

        for ox, oy in offsets:
            sample_lx = lx + ox
            sample_ly = ly + oy

            for x1, y1, x2, y2 in occluders:
                # Occluder culling
                if (max(x1, x2) < sample_lx - radius or min(x1, x2) > sample_lx + radius or
                    max(y1, y2) < sample_ly - radius or min(y1, y2) > sample_ly + radius):
                    continue

                # Back-face culling for edges: check normal relative to light vector
                edge_dx = x2 - x1
                edge_dy = y2 - y1
                normal_x = -edge_dy
                normal_y = edge_dx
                to_light_x = sample_lx - (x1 + x2) * 0.5
                to_light_y = sample_ly - (y1 + y2) * 0.5

                if normal_x * to_light_x + normal_y * to_light_y < 0:
                    # Edge faces away from light, cast shadow
                    quad = self.project_shadow_polygon(sample_lx, sample_ly, (x1, y1), (x2, y2))
                    screen_quad = [(int(qx - cam_x), int(qy - cam_y)) for qx, qy in quad]
                    pygame.draw.polygon(mask_surf, (0, 0, 0, pass_alpha), screen_quad)
                    PROFILER.record_shadow()

        return mask_surf
