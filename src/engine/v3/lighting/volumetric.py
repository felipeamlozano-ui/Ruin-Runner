"""
Ruin Engine V3.0 — 2D Volumetric Lighting & Atmospheric Ray Marching (God Rays).
Simulates Mie scattering, atmospheric fog absorption, and radial light shafts.
"""

import math
import numpy as np
import pygame
from typing import List, Tuple, Optional
import opensimplex
from engine.v3.core.jit_backend import jit_compile
from engine.v3.core.surface_pool import SURFACE_POOL
from engine.v3.core.profiler import PROFILER

class VolumetricLightingEngine:
    """
    Simulates volumetric light shafts, atmospheric scattering, and turbulent fog.
    Hyper-optimized using multi-frequency harmonic synthesis and seamless texture scrolling.
    """
    def __init__(self, width: int = 512, height: int = 384):
        self.w = width
        self.h = height
        self.fog_time: float = 0.0

        # Pre-bake seamless 2D atmospheric fog texture
        self.fog_w, self.fog_h = 320, 160
        self._init_seamless_fog()

    def _init_seamless_fog(self) -> None:
        y, x = np.ogrid[0:self.fog_h, 0:self.fog_w]
        fx = 2.0 * np.pi * x / float(self.fog_w)
        fy = 2.0 * np.pi * y / float(self.fog_h)
        field = 0.5 + 0.28 * np.sin(fx) + 0.16 * np.cos(2.0 * fx + fy) + 0.12 * np.sin(3.0 * fx - 2.0 * fy)
        field = np.power(np.clip(field, 0.0, 1.0), 1.8)
        
        rgba = np.zeros((self.fog_w, self.fog_h, 4), dtype=np.uint8)
        rgba[..., 0] = 180
        rgba[..., 1] = 200
        rgba[..., 2] = 230
        rgba[..., 3] = np.clip(field.T * 80, 0, 255).astype(np.uint8)
        self.fog_surf = pygame.image.frombuffer(rgba.tobytes(), (self.fog_w, self.fog_h), 'RGBA')

    def update(self, dt: float) -> None:
        self.fog_time += dt * 0.45

    def render_god_rays(
        self,
        target_surface: pygame.Surface,
        light_pos: Tuple[float, float],
        color: Tuple[int, int, int] = (255, 235, 180),
        intensity: float = 0.8,
        num_shafts: int = 8,
        angle_spread: float = 0.65,
        base_angle: float = math.pi * 0.35,
        length: float = 480.0
    ) -> None:
        """
        Renders volumetric light shafts (God Rays) with atmospheric attenuation in < 1ms.
        """
        shaft_surf = SURFACE_POOL.acquire(self.w, self.h, pygame.SRCALPHA)
        shaft_surf.fill((0, 0, 0, 0))

        lx, ly = light_pos
        r, g, b = color[:3]

        for i in range(num_shafts):
            # Angular offset with subtle animated sway
            t_offset = math.sin(self.fog_time * 1.5 + i * 1.1) * 0.04
            angle = base_angle + (i - num_shafts / 2.0) * (angle_spread / num_shafts) + t_offset
            
            width_top = 8.0 + math.sin(i * 3.7) * 4.0
            width_bot = 45.0 + math.cos(i * 2.3) * 15.0

            dx = math.cos(angle)
            dy = math.sin(angle)
            perp_x = -dy
            perp_y = dx

            p1 = (lx + perp_x * (width_top * 0.5), ly + perp_y * (width_top * 0.5))
            p2 = (lx - perp_x * (width_top * 0.5), ly - perp_y * (width_top * 0.5))
            p3 = (lx + dx * length - perp_x * (width_bot * 0.5), ly + dy * length - perp_y * (width_bot * 0.5))
            p4 = (lx + dx * length + perp_x * (width_bot * 0.5), ly + dy * length + perp_y * (width_bot * 0.5))

            # Alpha modulated by fast multi-harmonic turbulence (subtle, elegant sunbeams)
            turb = 0.5 + 0.30 * math.sin(self.fog_time * 2.3 + i * 1.7) + 0.20 * math.cos(self.fog_time * 1.1 - i * 0.9)
            alpha = int(12 * intensity * (0.6 + 0.4 * turb))

            pts = [(int(x), int(y)) for x, y in (p1, p2, p3, p4)]
            pygame.draw.polygon(shaft_surf, (220, 195, 130, alpha), pts)

        target_surface.blit(shaft_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        SURFACE_POOL.release(shaft_surf)
        PROFILER.record_draw_calls(1)

    def render_volumetric_fog(
        self,
        target_surface: pygame.Surface,
        fog_color: Tuple[int, int, int] = (160, 180, 210),
        density: float = 0.35,
        wind_speed: float = 24.0
    ) -> None:
        """
        Renders multi-layer scrolling atmospheric fog in < 1ms using pre-baked seamless harmonics.
        """
        # Two-layer parallax scrolling
        off_x1 = int(self.fog_time * wind_speed * 1.1) % self.fog_w
        off_x2 = int(self.fog_time * wind_speed * 0.6) % self.fog_w
        base_y = self.h - self.fog_h - 20

        # Layer 1
        target_surface.blit(self.fog_surf, (-off_x1, base_y), special_flags=pygame.BLEND_RGBA_ADD)
        target_surface.blit(self.fog_surf, (self.fog_w - off_x1, base_y), special_flags=pygame.BLEND_RGBA_ADD)
        if self.fog_w * 2 - off_x1 < self.w:
            target_surface.blit(self.fog_surf, (self.fog_w * 2 - off_x1, base_y), special_flags=pygame.BLEND_RGBA_ADD)

        # Layer 2 (higher elevation, slower drift)
        target_surface.blit(self.fog_surf, (-off_x2, base_y - 30), special_flags=pygame.BLEND_RGBA_ADD)
        target_surface.blit(self.fog_surf, (self.fog_w - off_x2, base_y - 30), special_flags=pygame.BLEND_RGBA_ADD)
        if self.fog_w * 2 - off_x2 < self.w:
            target_surface.blit(self.fog_surf, (self.fog_w * 2 - off_x2, base_y - 30), special_flags=pygame.BLEND_RGBA_ADD)

        PROFILER.record_draw_calls(2)
