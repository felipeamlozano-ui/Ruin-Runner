"""
Ruin Engine V3.0 — Weather & Atmospheric Environmental Engine.
Drives dynamic weather phenomena (Rain, Storms, Snow, Wind, Mist, Ash)
and controls scenario presets for Catacombs, High Forest, Crypt, Forbidden Forest, and Blood Moon Boss.
"""

import math
import random
import pygame
from typing import Tuple, Optional
from engine.v3.particles.particle_engine import (
    ParticleEngine, PARTICLE_RAIN, PARTICLE_SNOW, PARTICLE_LEAVES,
    PARTICLE_ASH, PARTICLE_DUST, PARTICLE_MAGIC, PARTICLE_FIRE
)
from engine.v3.core.profiler import PROFILER
from engine.v3.core.surface_pool import SURFACE_POOL

WEATHER_CLEAR = "clear"
WEATHER_RAIN = "rain"
WEATHER_STORM = "storm"
WEATHER_SNOW = "snow"
WEATHER_WIND = "wind"
WEATHER_MIST = "mist"
WEATHER_ASH = "ash"
WEATHER_LEAVES = "leaves"
WEATHER_DUST = "dust"

class WeatherEngine:
    """
    Manages atmospheric environmental systems, weather particles, and lighting tints.
    """
    def __init__(self, particle_engine: ParticleEngine):
        self.particles = particle_engine
        self.current_weather = WEATHER_CLEAR
        self.wind_speed: float = 0.0
        self.intensity: float = 1.0

        # Lighting modulation
        self.ambient_tint: Tuple[int, int, int] = (255, 255, 255)
        self.lightning_timer: float = 0.0
        self.lightning_flash: float = 0.0

    def set_stage_preset(self, stage_name: str) -> None:
        """Configures atmospheric parameters for specific scenario identities."""
        s = stage_name.lower()
        if "catacumba" in s or "dungeon" in s:
            # Catacombs: Cold blue ambient, drifting dust, heavy AO, wispy smoke
            self.current_weather = WEATHER_DUST
            self.wind_speed = 10.0
            self.ambient_tint = (130, 160, 210)
        elif "floresta proibida" in s:
            # Forbidden Forest: Twilight crepuscular lighting, volumetric fog, falling dark ash
            self.current_weather = WEATHER_ASH
            self.wind_speed = -25.0
            self.ambient_tint = (160, 140, 180)
        elif "floresta" in s:
            # High Forest: God rays, windblown falling leaves, lush warm ambient
            self.current_weather = WEATHER_LEAVES
            self.wind_speed = 45.0
            self.ambient_tint = (210, 240, 190)
        elif "cripta" in s:
            # Crypt: Mystical violet mist, arcane magic sparks
            self.current_weather = WEATHER_MIST
            self.wind_speed = 5.0
            self.ambient_tint = (180, 130, 230)
        elif "chefe" in s or "boss" in s or "trono" in s:
            # Throne / Skeleton King Phase 2: Blood Moon, procedural magma, black embers
            self.current_weather = WEATHER_ASH
            self.wind_speed = 30.0
            self.ambient_tint = (255, 90, 70)

    def update(self, dt: float, camera_rect: pygame.Rect) -> None:
        """Ticks weather particle emissions and storm lightning."""
        self.particles.wind_x = self.wind_speed

        # Spawn weather particles inside/around camera view
        left = camera_rect.left - 50
        right = camera_rect.right + 50
        top = camera_rect.top - 40
        bottom = camera_rect.bottom + 40

        if self.current_weather == WEATHER_RAIN:
            for _ in range(int(8 * self.intensity)):
                rx = random.uniform(left, right)
                self.particles.spawn(rx, top, self.wind_speed * 1.5, random.uniform(500.0, 750.0), (160, 200, 255, 180), size=1.5, lifetime=0.7)

        elif self.current_weather == WEATHER_LEAVES:
            if random.random() < 0.45 * self.intensity:
                rx = random.uniform(left, right)
                color = random.choice([(140, 200, 50, 220), (180, 220, 60, 220), (210, 170, 40, 220)])
                self.particles.spawn(rx, top, self.wind_speed + random.uniform(-15.0, 15.0), random.uniform(25.0, 60.0), color, size=3.0, lifetime=4.0)

        elif self.current_weather == WEATHER_ASH:
            if random.random() < 0.65 * self.intensity:
                rx = random.uniform(left, right)
                color = random.choice([(60, 55, 50, 200), (255, 110, 30, 220), (180, 50, 30, 200)])
                self.particles.spawn(rx, top, self.wind_speed * 0.5 + random.uniform(-10.0, 10.0), random.uniform(15.0, 40.0), color, size=2.0, lifetime=5.0)

        elif self.current_weather == WEATHER_DUST:
            if random.random() < 0.35 * self.intensity:
                rx = random.uniform(left, right)
                ry = random.uniform(top, bottom)
                self.particles.spawn(rx, ry, random.uniform(-10.0, 10.0), random.uniform(-15.0, -35.0), (190, 180, 160, 120), size=1.5, lifetime=3.0)

        elif self.current_weather == WEATHER_STORM:
            # Rain + Thunder
            for _ in range(int(14 * self.intensity)):
                rx = random.uniform(left, right)
                self.particles.spawn(rx, top, self.wind_speed * 2.0, random.uniform(650.0, 900.0), (180, 220, 255, 200), size=1.8, lifetime=0.6)

            self.lightning_timer -= dt
            if self.lightning_timer <= 0:
                self.lightning_flash = 1.0
                self.lightning_timer = random.uniform(4.0, 12.0)

        if self.lightning_flash > 0:
            self.lightning_flash = max(0.0, self.lightning_flash - dt * 5.0)

    def render_overlay(self, surface: pygame.Surface) -> None:
        """Renders storm lightning flash or atmospheric ambient tint."""
        if self.lightning_flash > 0:
            alpha = int(180 * self.lightning_flash)
            flash = SURFACE_POOL.acquire(surface.get_width(), surface.get_height(), pygame.SRCALPHA)
            flash.fill((255, 255, 255, alpha))
            surface.blit(flash, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            SURFACE_POOL.release(flash)
            PROFILER.record_draw_calls(1)
