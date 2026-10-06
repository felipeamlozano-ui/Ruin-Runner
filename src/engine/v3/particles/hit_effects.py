"""
Ruin Engine V3.0 — AAA Hit Impact & Kinetic Feedback System.
Orchestrates Hitstop, Impact Frames, Chromatic Flash, Sparks, Ground Shockwaves, and Dust Rings.
"""

import math
import random
import pygame
from typing import List, Tuple
from engine.v3.core.profiler import PROFILER
from engine.v3.core.surface_pool import SURFACE_POOL

class Spark:
    def __init__(self, x: float, y: float, vx: float, vy: float, color: Tuple[int, int, int] = (255, 220, 100)):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.lifetime = random.uniform(0.15, 0.45)
        self.time = 0.0

class Shockwave:
    def __init__(self, x: float, y: float, max_radius: float = 80.0, speed: float = 320.0, color: Tuple[int, int, int] = (255, 255, 255)):
        self.x = x
        self.y = y
        self.radius = 4.0
        self.max_radius = max_radius
        self.speed = speed
        self.color = color
        self.active = True

class HitEffectsManager:
    """
    Manages visceral kinetic combat feedback to deliver Hollow Knight / Dead Cells level impact satisfaction.
    """
    def __init__(self):
        self.hitstop_timer: float = 0.0
        self.impact_frames_left: int = 0
        self.chromatic_flash_intensity: float = 0.0

        self.sparks: List[Spark] = []
        self.shockwaves: List[Shockwave] = []

    def trigger_hitstop(self, duration: float = 0.08) -> None:
        """Freezes character animations and physics momentarily on critical impact."""
        self.hitstop_timer = max(self.hitstop_timer, duration)

    def trigger_impact_frame(self, frames: int = 2) -> None:
        """Flashes a stark monochrome contrast frame."""
        self.impact_frames_left = frames

    def trigger_chromatic_flash(self, intensity: float = 1.0) -> None:
        self.chromatic_flash_intensity = intensity

    def spawn_sparks(self, x: float, y: float, count: int = 12, direction_angle: float = None) -> None:
        """Spawns incandescent metal sparks with kinetic trajectory."""
        for _ in range(count):
            if direction_angle is not None:
                angle = direction_angle + random.uniform(-0.6, 0.6)
            else:
                angle = random.uniform(0, 2.0 * math.pi)
            speed = random.uniform(150.0, 450.0)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            self.sparks.append(Spark(x, y, vx, vy))

    def spawn_shockwave(self, x: float, y: float, max_radius: float = 90.0, color: Tuple[int, int, int] = (255, 230, 160)) -> None:
        """Spawns an expanding ground distortion shockwave."""
        self.shockwaves.append(Shockwave(x, y, max_radius, color=color))

    def update(self, dt: float) -> bool:
        """
        Updates kinetic hit effects.
        Returns True if hitstop is active (caller should skip physics integration).
        """
        is_hitstopped = False
        if self.hitstop_timer > 0:
            self.hitstop_timer -= dt
            is_hitstopped = True

        if self.chromatic_flash_intensity > 0:
            self.chromatic_flash_intensity = max(0.0, self.chromatic_flash_intensity - dt * 4.0)

        # Update sparks
        alive_sparks = []
        for s in self.sparks:
            s.time += dt
            if s.time < s.lifetime:
                s.x += s.vx * dt
                s.y += s.vy * dt
                s.vy += 800.0 * dt  # Gravity
                alive_sparks.append(s)
        self.sparks = alive_sparks

        # Update shockwaves
        alive_sw = []
        for sw in self.shockwaves:
            sw.radius += sw.speed * dt
            if sw.radius < sw.max_radius:
                alive_sw.append(sw)
        self.shockwaves = alive_sw

        return is_hitstopped

    def render(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2) -> None:
        cam_x, cam_y = camera_offset.x, camera_offset.y

        # Render shockwaves
        for sw in self.shockwaves:
            sx = int(sw.x - cam_x)
            sy = int(sw.y - cam_y)
            fraction = 1.0 - (sw.radius / sw.max_radius)
            alpha = int(220 * fraction)
            width = max(1, int(4 * fraction))
            r, g, b = sw.color

            sw_surf = SURFACE_POOL.acquire(int(sw.radius * 2 + 8), int(sw.radius * 2 + 8), pygame.SRCALPHA)
            sw_surf.fill((0, 0, 0, 0))
            center = int(sw.radius + 4)
            pygame.draw.circle(sw_surf, (r, g, b, alpha), (center, center), int(sw.radius), width=width)
            surface.blit(sw_surf, (sx - center, sy - center), special_flags=pygame.BLEND_RGBA_ADD)
            SURFACE_POOL.release(sw_surf)
            PROFILER.record_draw_calls(1)

        # Render sparks
        for s in self.sparks:
            sx = int(s.x - cam_x)
            sy = int(s.y - cam_y)
            # Trailing spark line
            tail_x = int(sx - s.vx * 0.02)
            tail_y = int(sy - s.vy * 0.02)
            pygame.draw.line(surface, s.color, (tail_x, tail_y), (sx, sy), 2)
            PROFILER.record_draw_calls(1)

        # Render Impact Frame flash
        if self.impact_frames_left > 0:
            flash_surf = SURFACE_POOL.acquire(surface.get_width(), surface.get_height(), pygame.SRCALPHA)
            flash_surf.fill((255, 255, 255, 180))
            surface.blit(flash_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            SURFACE_POOL.release(flash_surf)
            self.impact_frames_left -= 1
