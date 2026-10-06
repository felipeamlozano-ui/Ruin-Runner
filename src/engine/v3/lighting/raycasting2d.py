"""
Ruin Engine V3.0 — 2D Ray Casting & Visibility Polygon Engine.
Implements O(V log V) angular sweep ray casting with Numba/NumPy accelerated segment intersections.
"""

import math
import numpy as np
import pygame
from typing import List, Tuple, Optional
from engine.v3.core.jit_backend import jit_compile
from engine.v3.core.profiler import PROFILER

@jit_compile(fastmath=True)
def ray_segment_intersect_jit(
    ox: float, oy: float, dx: float, dy: float,
    x1: float, y1: float, x2: float, y2: float
) -> Tuple[bool, float]:
    """Computes ray-segment intersection distance t along (ox + t*dx, oy + t*dy)."""
    dx_seg = x2 - x1
    dy_seg = y2 - y1

    denom = dx * dy_seg - dy * dx_seg
    if abs(denom) < 1e-7:
        return False, 0.0

    t1 = ((x1 - ox) * dy_seg - (y1 - oy) * dx_seg) / denom
    t2 = ((x1 - ox) * dy - (y1 - oy) * dx) / denom

    if t1 > 0.0 and 0.0 <= t2 <= 1.0:
        return True, t1
    return False, 0.0


class LightRayCaster:
    """
    Computes precise 2D visibility polygons through radial sweep sorting.
    """
    def __init__(self):
        self._boundary_cache: List[Tuple[float, float, float, float]] = []

    def compute_visibility_polygon(
        self,
        lx: float,
        ly: float,
        radius: float,
        segments: List[Tuple[float, float, float, float]]
    ) -> List[Tuple[float, float]]:
        """
        Calculates the 2D visibility polygon from light position (lx, ly) against segment occluders.
        Complexity: O(V log V).
        """
        # Collect relevant segments within light radius
        rad_sq = radius * radius
        active_segments = []
        for x1, y1, x2, y2 in segments:
            # Check bounding box distance
            min_x = min(x1, x2)
            max_x = max(x1, x2)
            min_y = min(y1, y2)
            max_y = max(y1, y2)
            if (max_x < lx - radius or min_x > lx + radius or
                max_y < ly - radius or min_y > ly + radius):
                continue
            active_segments.append((x1, y1, x2, y2))

        # Add circular bounding segments for radial containment
        num_circ = 16
        for i in range(num_circ):
            a1 = (i / num_circ) * 2.0 * math.pi
            a2 = ((i + 1) / num_circ) * 2.0 * math.pi
            bx1 = lx + math.cos(a1) * radius
            by1 = ly + math.sin(a1) * radius
            bx2 = lx + math.cos(a2) * radius
            by2 = ly + math.sin(a2) * radius
            active_segments.append((bx1, by1, bx2, by2))

        # Collect unique angles
        angles = set()
        for x1, y1, x2, y2 in active_segments:
            for px, py in ((x1, y1), (x2, y2)):
                base_angle = math.atan2(py - ly, px - lx)
                angles.add(base_angle)
                angles.add(base_angle - 0.0001)
                angles.add(base_angle + 0.0001)

        sorted_angles = sorted(angles)
        PROFILER.record_light(len(sorted_angles))

        # Check for Native C AVX2 acceleration
        from engine.v3.native.native_bridge import has_native, native_compute_visibility_rays
        if has_native() and active_segments:
            angles_arr = np.array(sorted_angles, dtype=np.float32)
            occluders_arr = np.array(active_segments, dtype=np.float32)
            out_x, out_y = native_compute_visibility_rays(lx, ly, angles_arr, occluders_arr, radius)
            return list(zip(out_x.tolist(), out_y.tolist()))

        # Python / Numba FastMath fallback
        polygon = []
        for angle in sorted_angles:
            dx = math.cos(angle)
            dy = math.sin(angle)
            closest_dist = radius
            hit_point = (lx + dx * radius, ly + dy * radius)

            for x1, y1, x2, y2 in active_segments:
                hit, dist = ray_segment_intersect_jit(lx, ly, dx, dy, x1, y1, x2, y2)
                if hit and dist < closest_dist:
                    closest_dist = dist
                    hit_point = (lx + dx * dist, ly + dy * dist)

            polygon.append(hit_point)

        return polygon

    def render_light_cone(
        self,
        surface: pygame.Surface,
        lx: float,
        ly: float,
        radius: float,
        color: Tuple[int, int, int],
        intensity: float,
        polygon: List[Tuple[float, float]],
        camera_offset: pygame.math.Vector2
    ) -> None:
        """
        Renders the visibility polygon with radial falloff gradient.
        """
        if len(polygon) < 3:
            return

        rad_int = int(radius)
        light_surf = pygame.Surface((rad_int * 2, rad_int * 2), pygame.SRCALPHA)

        # Local polygon coordinates
        local_poly = [
            (int(px - lx + radius), int(py - ly + radius))
            for px, py in polygon
        ]

        # Draw filled visibility mask
        alpha = int(255 * min(1.0, intensity))
        mask_surf = pygame.Surface((rad_int * 2, rad_int * 2), pygame.SRCALPHA)
        pygame.draw.polygon(mask_surf, (255, 255, 255, 255), local_poly)

        # Draw radial falloff gradient
        r, g, b = color[:3]
        grad_surf = pygame.Surface((rad_int * 2, rad_int * 2), pygame.SRCALPHA)
        for step in range(rad_int, 0, -3):
            ratio = 1.0 - (step / radius)
            step_alpha = int(alpha * (ratio ** 1.8))
            pygame.draw.circle(grad_surf, (r, g, b, step_alpha), (rad_int, rad_int), step)

        # Composite gradient clipped to visibility polygon
        grad_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        # Blit to target surface
        dest_x = int(lx - camera_offset.x - radius)
        dest_y = int(ly - camera_offset.y - radius)
        surface.blit(grad_surf, (dest_x, dest_y), special_flags=pygame.BLEND_RGBA_ADD)
        PROFILER.record_draw_calls(1)
