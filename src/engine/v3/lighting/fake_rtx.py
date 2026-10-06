"""
Ruin Engine V3.0 — 2D Ray Tracing & Fake RTX Engine.
Implements SDF Ray Marching, 2D Indirect Light Bounces, Reflection Probes, and Fake Global Illumination.
"""

import math
import numpy as np
import pygame
from typing import List, Tuple, Optional
from engine.v3.core.jit_backend import jit_compile
from engine.v3.core.surface_pool import SURFACE_POOL
from engine.v3.core.profiler import PROFILER

@jit_compile(fastmath=True)
def sdf_box_2d(px: float, py: float, bx: float, by: float, bw: float, bh: float) -> float:
    """Signed Distance Field for a 2D axis-aligned box."""
    cx = bx + bw * 0.5
    cy = by + bh * 0.5
    dx = abs(px - cx) - bw * 0.5
    dy = abs(py - cy) - bh * 0.5
    outside = math.sqrt(max(0.0, dx) ** 2 + max(0.0, dy) ** 2)
    inside = min(max(dx, dy), 0.0)
    return outside + inside

@jit_compile(fastmath=True)
def sdf_circle_2d(px: float, py: float, cx: float, cy: float, radius: float) -> float:
    """Signed Distance Field for a 2D circle."""
    dist = math.sqrt((px - cx) ** 2 + (py - cy) ** 2)
    return dist - radius


class FakeRTXEngine:
    """
    Simulates real-time light bounces, indirect diffuse GI, and reflection probes using 2D SDF Ray Marching.
    """
    def __init__(self, viewport_w: int = 512, viewport_h: int = 384):
        self.vw = viewport_w
        self.vh = viewport_h
        # Low-res GI accumulation grid (e.g. 64x48)
        self.gi_scale = 0.125
        self.gw = int(viewport_w * self.gi_scale)
        self.gh = int(viewport_h * self.gi_scale)
        self.gi_buffer = np.zeros((self.gh, self.gw, 3), dtype=np.float32)

    def march_ray_sdf(
        self,
        ox: float,
        oy: float,
        dx: float,
        dy: float,
        boxes: List[Tuple[float, float, float, float]],
        max_dist: float = 400.0,
        max_steps: int = 24
    ) -> Tuple[bool, float, float, float, float, float]:
        """
        Sphere-marches through 2D SDF space.
        Returns: (hit, dist, hit_x, hit_y, normal_x, normal_y)
        """
        t = 0.0
        for _ in range(max_steps):
            px = ox + dx * t
            py = oy + dy * t

            # Query minimum scene distance
            min_d = max_dist
            hit_box = None
            for bx, by, bw, bh in boxes:
                d = sdf_box_2d(px, py, bx, by, bw, bh)
                if d < min_d:
                    min_d = d
                    hit_box = (bx, by, bw, bh)

            if min_d < 1.0:
                # Surface hit, estimate normal using gradient
                eps = 1.0
                nx = (sdf_box_2d(px + eps, py, *hit_box) - sdf_box_2d(px - eps, py, *hit_box))
                ny = (sdf_box_2d(px, py + eps, *hit_box) - sdf_box_2d(px, py - eps, *hit_box))
                mag = math.sqrt(nx * nx + ny * ny)
                if mag > 1e-5:
                    nx /= mag
                    ny /= mag
                else:
                    nx, ny = 0.0, -1.0
                return True, t, px, py, nx, ny

            t += min_d
            if t >= max_dist:
                break

        return False, max_dist, ox + dx * max_dist, oy + dy * max_dist, 0.0, 0.0

    def calculate_fake_indirect_bounce(
        self,
        lx: float,
        ly: float,
        light_color: Tuple[int, int, int],
        boxes: List[Tuple[float, float, float, float]],
        num_rays: int = 16,
        surface_albedo: Tuple[float, float, float] = (0.8, 0.7, 0.5)
    ) -> List[Tuple[float, float, float, Tuple[int, int, int]]]:
        """
        Traces primary rays and calculates secondary diffuse bounce sources (Fake GI).
        Returns list of secondary bounce point lights: (x, y, radius, (r, g, b)).
        """
        secondary_lights = []
        r, g, b = light_color[:3]

        for i in range(num_rays):
            angle = (i / num_rays) * 2.0 * math.pi
            dx = math.cos(angle)
            dy = math.sin(angle)

            hit, dist, hx, hy, nx, ny = self.march_ray_sdf(lx, ly, dx, dy, boxes, max_dist=250.0)
            if hit:
                # Reflect ray: R = D - 2*(D.N)*N
                dot = dx * nx + dy * ny
                rx = dx - 2.0 * dot * nx
                ry = dy - 2.0 * dot * ny

                # Secondary bounce color tinted by surface albedo
                bounce_r = int(r * surface_albedo[0] * 0.35)
                bounce_g = int(g * surface_albedo[1] * 0.35)
                bounce_b = int(b * surface_albedo[2] * 0.35)

                secondary_lights.append((hx + nx * 4.0, hy + ny * 4.0, 45.0, (bounce_r, bounce_g, bounce_b)))

        PROFILER.record_light(len(secondary_lights))
        return secondary_lights

    def render_reflection_probe(
        self,
        source_surface: pygame.Surface,
        probe_rect: pygame.Rect,
        water_y: int,
        blur_amount: int = 2
    ) -> pygame.Surface:
        """
        Extracts a 2D planar reflection probe from the scene and applies simulated wet surface distortion.
        """
        sub = source_surface.subsurface(probe_rect).copy()
        flipped = pygame.transform.flip(sub, False, True)

        # Apply tint and soft blur
        overlay = pygame.Surface(flipped.get_size(), pygame.SRCALPHA)
        overlay.fill((30, 60, 100, 140))  # Cold blue water reflection tint
        flipped.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        return flipped
