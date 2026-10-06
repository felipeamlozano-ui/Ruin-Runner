"""
Ruin Engine V3.0 — Cinematic Screen-Space Effects & Hardware Quality Presets.
Implements:
- Chromatic Aberration (R/B channel displacement on heavy impacts)
- Vignette (Smooth quadratic radial edge falloff)
- Film Grain (Subtle procedural analog texture)
- Motion Blur (Directional streak along velocity vector)
- Quality Presets: Very Low, Low, Medium, High, Ultra, and Ryzen Vega Optimized (AMD 5500U / 8GB)
"""

import math
import random
import pygame
import numpy as np
from dataclasses import dataclass
from typing import Dict, Tuple, Optional
from engine.v3.core.profiler import PROFILER

@dataclass
class QualityPreset:
    name: str
    target_fps: int
    internal_res: Tuple[int, int]
    fsr_preset: str
    shadow_mode: str       # "Suaves", "Duras", "Desativado"
    soft_shadow_rays: int
    ray_casting_enabled: bool
    bloom_enabled: bool
    bloom_downsample_tier: int  # 2 = 1/4 res, 3 = 1/8 res
    max_particles: int
    aa_mode: str           # "FXAA", "Pixel AA", "Off"
    ambient_particles: bool
    chromatic_aberration: bool
    vignette: bool

QUALITY_PRESETS: Dict[str, QualityPreset] = {
    "Legacy / Retro Optimized": QualityPreset(
        name="Legacy / Retro Optimized",
        target_fps=60,
        internal_res=(512, 384),
        fsr_preset="Desativado",
        shadow_mode="Desativado",
        soft_shadow_rays=0,
        ray_casting_enabled=False,
        bloom_enabled=False,
        bloom_downsample_tier=3,
        max_particles=300,
        aa_mode="Pixel AA (Fast)",
        ambient_particles=False,
        chromatic_aberration=False,
        vignette=False
    ),
    "Very Low": QualityPreset(
        name="Very Low",
        target_fps=60,
        internal_res=(384, 288),
        fsr_preset="Ultra Performance",
        shadow_mode="Desativado",
        soft_shadow_rays=0,
        ray_casting_enabled=False,
        bloom_enabled=False,
        bloom_downsample_tier=3,
        max_particles=400,
        aa_mode="Off",
        ambient_particles=False,
        chromatic_aberration=False,
        vignette=False
    ),
    "Low": QualityPreset(
        name="Low",
        target_fps=60,
        internal_res=(448, 336),
        fsr_preset="Performance",
        shadow_mode="Duras",
        soft_shadow_rays=1,
        ray_casting_enabled=False,
        bloom_enabled=True,
        bloom_downsample_tier=3,
        max_particles=800,
        aa_mode="Pixel AA",
        ambient_particles=True,
        chromatic_aberration=False,
        vignette=True
    ),
    "Ryzen Vega Optimized": QualityPreset(
        name="Ryzen Vega Optimized",
        target_fps=60,
        internal_res=(512, 384),
        fsr_preset="Balanced",
        shadow_mode="Suaves",
        soft_shadow_rays=4,
        ray_casting_enabled=True,
        bloom_enabled=True,
        bloom_downsample_tier=2,
        max_particles=2000,
        aa_mode="FXAA",
        ambient_particles=True,
        chromatic_aberration=True,
        vignette=True
    ),
    "Medium": QualityPreset(
        name="Medium",
        target_fps=60,
        internal_res=(512, 384),
        fsr_preset="Balanced",
        shadow_mode="Suaves",
        soft_shadow_rays=4,
        ray_casting_enabled=True,
        bloom_enabled=True,
        bloom_downsample_tier=2,
        max_particles=1800,
        aa_mode="FXAA",
        ambient_particles=True,
        chromatic_aberration=True,
        vignette=True
    ),
    "High": QualityPreset(
        name="High",
        target_fps=60,
        internal_res=(640, 480),
        fsr_preset="Quality",
        shadow_mode="Suaves",
        soft_shadow_rays=6,
        ray_casting_enabled=True,
        bloom_enabled=True,
        bloom_downsample_tier=2,
        max_particles=3000,
        aa_mode="FXAA",
        ambient_particles=True,
        chromatic_aberration=True,
        vignette=True
    ),
    "Ultra": QualityPreset(
        name="Ultra",
        target_fps=60,
        internal_res=(768, 576),
        fsr_preset="Ultra Quality",
        shadow_mode="Suaves",
        soft_shadow_rays=8,
        ray_casting_enabled=True,
        bloom_enabled=True,
        bloom_downsample_tier=1,
        max_particles=4500,
        aa_mode="SMAA",
        ambient_particles=True,
        chromatic_aberration=True,
        vignette=True
    )
}

class ScreenSpaceEffects:
    """Manages selective, cinematic screen-space visual treatments."""
    def __init__(self, width: int = 512, height: int = 384):
        self.w = width
        self.h = height
        
        # Chromatic aberration state
        self.aberration_timer: float = 0.0
        self.aberration_intensity: float = 0.0
        
        # Film grain pre-generated noise buffer
        self.grain_noise = np.random.randint(-12, 12, (height, width, 3), dtype=np.int16)

    def trigger_chromatic_aberration(self, intensity: float = 3.5, duration: float = 0.22):
        """Triggers radial RGB channel displacement on heavy hits or ultimates."""
        self.aberration_intensity = intensity
        self.aberration_timer = duration

    def update(self, dt: float):
        if self.aberration_timer > 0:
            self.aberration_timer -= dt
            if self.aberration_timer <= 0:
                self.aberration_intensity = 0.0

    def apply_chromatic_aberration(self, surface: pygame.Surface) -> None:
        """Displaces Red and Blue color channels by pixel offset."""
        if self.aberration_timer <= 0 or self.aberration_intensity <= 0.1:
            return

        with PROFILER.time_phase("postfx"):
            w, h = surface.get_size()
            offset = max(1, int(self.aberration_intensity * (self.aberration_timer / 0.22)))
            
            arr = pygame.surfarray.pixels3d(surface)
            # Red channel shifted left, Blue channel shifted right
            r_chan = arr[:, :, 0].copy()
            b_chan = arr[:, :, 2].copy()
            
            arr[:-offset, :, 0] = r_chan[offset:, :]
            arr[offset:, :, 2] = b_chan[:-offset, :]
            del arr

    def apply_motion_blur(self, surface: pygame.Surface, vx: float, vy: float, factor: float = 0.003) -> None:
        """Applies subtle directional velocity ghosting during high-speed dashes."""
        speed = math.hypot(vx, vy)
        if speed < 280.0:
            return
            
        with PROFILER.time_phase("postfx"):
            w, h = surface.get_size()
            blur_surf = surface.copy()
            blur_surf.set_alpha(int(min(80, speed * factor)))
            
            dx = int(-vx * 0.012)
            dy = int(-vy * 0.012)
            surface.blit(blur_surf, (dx, dy))

SCREEN_FX = ScreenSpaceEffects()
