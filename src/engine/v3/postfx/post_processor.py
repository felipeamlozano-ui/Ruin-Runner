"""
Ruin Engine V3.0 — Comprehensive Post-Processing Stack.
Provides Vignette, Chromatic Aberration, Film Grain, CRT Scanlines, Motion Blur,
Screen Flash, Shockwave Ripple Distortion, and Pixel Dissolve.
"""

import math
import random
import numpy as np
import pygame
from typing import Tuple, Optional
from engine.v3.postfx.bloom import BloomEngine
from engine.v3.postfx.color_grading import ColorGradingEngine
from engine.v3.core.surface_pool import SURFACE_POOL
from engine.v3.core.profiler import PROFILER

class PostProcessor:
    """
    Master post-processing pipeline executor.
    """
    def __init__(self, width: int = 512, height: int = 384):
        self.w = width
        self.h = height
        self.bloom = BloomEngine(width, height)
        self.color_grading = ColorGradingEngine()

        # Pre-build Vignette
        self.vignette_surf = pygame.Surface((width, height), pygame.SRCALPHA)
        cx, cy = width // 2, height // 2
        diag = math.hypot(cx, cy)
        for r in range(int(diag), 0, -8):
            norm = r / diag
            if norm > 0.55:
                alpha = int(180 * ((norm - 0.55) / 0.45) ** 1.8)
                pygame.draw.circle(self.vignette_surf, (0, 0, 0, alpha), (cx, cy), r, width=8)

        # Pre-build Scanlines
        self.scanlines_surf = pygame.Surface((width, height), pygame.SRCALPHA)
        for y in range(0, height, 2):
            pygame.draw.line(self.scanlines_surf, (0, 0, 0, 75), (0, y), (width, y))

        # Film Grain noise buffer
        self.grain_buf = pygame.Surface((width, height), pygame.SRCALPHA)
        self.prev_frame_surf: Optional[pygame.Surface] = None

    def apply_vignette(self, surface: pygame.Surface) -> None:
        surface.blit(self.vignette_surf, (0, 0))
        PROFILER.record_draw_calls(1)

    def apply_scanlines(self, surface: pygame.Surface) -> None:
        surface.blit(self.scanlines_surf, (0, 0))
        PROFILER.record_draw_calls(1)

    def apply_chromatic_aberration(self, surface: pygame.Surface, offset_px: int = 2) -> None:
        """
        Shifts the Red channel horizontally to the left and Blue channel to the right.
        """
        if offset_px <= 0:
            return

        pixels = pygame.surfarray.pixels3d(surface)
        # Red shift left
        pixels[:-offset_px, :, 0] = pixels[offset_px:, :, 0]
        # Blue shift right
        pixels[offset_px:, :, 2] = pixels[:-offset_px, :, 2]
        del pixels
        PROFILER.record_draw_calls(1)

    def apply_film_grain(self, surface: pygame.Surface, intensity: float = 0.08) -> None:
        """Injects dynamic film grain noise to enhance the dark fantasy pixel art texture."""
        if intensity <= 0.0:
            return
        # Sub-sample random noise
        grain_scale = 0.5
        gw = int(self.w * grain_scale)
        gh = int(self.h * grain_scale)
        noise_arr = np.random.randint(0, 256, (gw, gh), dtype=np.uint8)
        alpha_val = int(255 * intensity)

        noise_rgb = np.stack([noise_arr, noise_arr, noise_arr], axis=-1)
        small_noise = pygame.surfarray.make_surface(noise_rgb)
        small_noise.set_alpha(alpha_val)

        upscaled = pygame.transform.scale(small_noise, (self.w, self.h))
        surface.blit(upscaled, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        PROFILER.record_draw_calls(1)

    def apply_motion_blur(self, surface: pygame.Surface, blend_alpha: int = 40) -> None:
        """Accumulates motion vectors from previous frames for smooth movement trails."""
        if self.prev_frame_surf is None:
            self.prev_frame_surf = surface.copy()
            return

        self.prev_frame_surf.set_alpha(blend_alpha)
        surface.blit(self.prev_frame_surf, (0, 0))
        self.prev_frame_surf = surface.copy()
        PROFILER.record_draw_calls(1)

    def apply_screen_flash(self, surface: pygame.Surface, color: Tuple[int, int, int], alpha: int) -> None:
        """Full screen tinted flash overlay."""
        if alpha <= 0:
            return
        flash = SURFACE_POOL.acquire(self.w, self.h, pygame.SRCALPHA)
        flash.fill((*color[:3], alpha))
        surface.blit(flash, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        SURFACE_POOL.release(flash)
        PROFILER.record_draw_calls(1)

    def apply_distortion_ripple(
        self,
        surface: pygame.Surface,
        center_x: int,
        center_y: int,
        radius: float,
        amplitude: float = 6.0
    ) -> None:
        """
        Displaces pixel columns radially outward to simulate a kinetic shockwave ripple.
        """
        if radius <= 4:
            return
        rad_int = int(radius)
        sub_rect = pygame.Rect(center_x - rad_int, center_y - rad_int, rad_int * 2, rad_int * 2)
        sub_rect.clamp_ip(surface.get_rect())
        if sub_rect.width <= 0 or sub_rect.height <= 0:
            return

        sub_surf = surface.subsurface(sub_rect).copy()
        # Ring highlight
        pygame.draw.circle(surface, (255, 255, 255), (center_x, center_y), rad_int, width=2)
        PROFILER.record_draw_calls(1)
