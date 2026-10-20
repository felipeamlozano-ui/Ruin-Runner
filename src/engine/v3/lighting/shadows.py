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
    Constructs physically grounded hard and soft 2D shadow polygons from solid occluder geometries.
    """
    def __init__(self, shadow_length: float = 90.0):
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
        Grounded 2D constraint: shadows from obstacles on the ground are cast horizontally
        and downward onto the floor plane, never backwards/skywards into the ceiling.
        """
        length = length_override or self.shadow_length

        dx1 = p1[0] - lx
        dy1 = max(0.0, p1[1] - ly)
        len1 = math.hypot(dx1, dy1)
        if len1 > 1e-4:
            p1_proj = (p1[0] + (dx1 / len1) * length, p1[1] + (dy1 / len1) * length)
        else:
            p1_proj = (p1[0], p1[1] + length)

        dx2 = p2[0] - lx
        dy2 = max(0.0, p2[1] - ly)
        len2 = math.hypot(dx2, dy2)
        if len2 > 1e-4:
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
        shadow_alpha: int = 75,
        target_surface: Optional[pygame.Surface] = None
    ) -> pygame.Surface:
        """
        Bakes an ambient shadow mask with physically bounded soft penumbra.
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
                (-2.0, 0.0), (2.0, 0.0),
                (0.0, -1.5), (0.0, 1.5),
                (-1.5, -1.0), (1.5, 1.0)
            ][:soft_rays]
            pass_alpha = max(15, shadow_alpha // len(offsets))

        cam_x, cam_y = camera_offset.x, camera_offset.y

        for ox, oy in offsets:
            sample_lx = lx + ox
            sample_ly = ly + oy

            for x1, y1, x2, y2 in occluders:
                # 1. Occluder distance culling against light radius
                mid_x = (x1 + x2) * 0.5
                mid_y = (y1 + y2) * 0.5
                to_light_x = sample_lx - mid_x
                to_light_y = sample_ly - mid_y
                dist_to_light = math.hypot(to_light_x, to_light_y)
                if dist_to_light > radius or dist_to_light < 1e-3:
                    continue

                # 2. Orientation relative to light vector
                edge_dx = x2 - x1
                edge_dy = y2 - y1
                normal_x = -edge_dy
                normal_y = edge_dx

                dot = normal_x * to_light_x + normal_y * to_light_y
                if dot >= 0:
                    continue

                # 3. Dynamic shadow length bounded by remaining light radius
                remaining_reach = max(4.0, radius - dist_to_light)
                eff_length = min(self.shadow_length, remaining_reach * 1.15)

                quad = self.project_shadow_polygon(sample_lx, sample_ly, (x1, y1), (x2, y2), length_override=eff_length)
                screen_quad = [(int(qx - cam_x), int(qy - cam_y)) for qx, qy in quad]
                if any(-40 <= sx <= surface_w + 40 and -40 <= sy <= surface_h + 40 for sx, sy in screen_quad):
                    pygame.draw.polygon(mask_surf, (0, 0, 0, pass_alpha), screen_quad)
                    PROFILER.record_shadow()

        return mask_surf
