"""
Ruin Engine V3.0 — AAA Cinematic Camera & Dynamic Co-op Bounding System.
Implements:
1. Single Player Look Ahead, Dead Zone, Trauma Shake, and Perlin Noise Rumble.
2. 2-Player Co-op Bounding Box centering.
3. Smooth dynamic FOV zoom: zoom = f(distance) with MIN_ZOOM and MAX_ZOOM.
4. Soft Leash (visual cue and gentle edge velocity dampening).
5. Hard Leash (guarantees neither player can ever leave the camera viewport).
"""

import math
import random
import pygame
import opensimplex
from typing import Tuple, Optional
from utils.math_utils import lerp, clamp

class CameraV3:
    """
    Cinematic camera providing responsive lookahead, trauma screen shake,
    and dynamic multi-player cooperative framing.
    """
    MIN_ZOOM: float = 0.72
    MAX_ZOOM: float = 1.15
    MAX_PLAYER_DISTANCE: float = 460.0

    def __init__(self, map_width: int, map_height: int, viewport_w: int = 512, viewport_h: int = 384):
        self.map_w = map_width
        self.map_h = map_height
        self.vw = viewport_w
        self.vh = viewport_h

        # Position state
        self.x: float = 0.0
        self.y: float = 0.0
        self.target_x: float = 0.0
        self.target_y: float = 0.0

        # Look Ahead & Dead Zone
        self.look_ahead_x: float = 0.0
        self.look_ahead_distance: float = 48.0
        self.look_ahead_speed: float = 3.5
        self.dead_zone = pygame.FRect(0, 0, 60.0, 40.0)

        # Smooth Lag
        self.lag_speed: float = 6.0

        # Trauma Shake System (Trauma^2 / Trauma^3 polynomial curve)
        self.trauma: float = 0.0
        self.max_shake_offset: float = 18.0
        self.max_shake_angle: float = 3.5  # degrees
        self.trauma_decay: float = 1.4
        self.noise = opensimplex.OpenSimplex(seed=42)
        self.noise_time: float = 0.0

        # Dynamic FOV Zoom
        self.zoom_factor: float = 1.0
        self.target_zoom: float = 1.0
        self.zoom_speed: float = 2.5

        # Freeze & Lock
        self.freeze_timer: float = 0.0
        self.locked: bool = False

        # Co-op Leash State
        self.p1_leash_alert: bool = False
        self.p2_leash_alert: bool = False
        self.current_player_distance: float = 0.0
        self.min_zoom: float = self.MIN_ZOOM
        self.max_zoom: float = self.MAX_ZOOM
        self.max_player_distance: float = self.MAX_PLAYER_DISTANCE

    @property
    def zoom(self) -> float:
        return self.zoom_factor

    def add_trauma(self, amount: float) -> None:
        """Injects kinetic trauma into camera shake system (clamped to 1.0)."""
        self.trauma = min(1.0, self.trauma + amount)

    def trigger_ultimate_freeze(self, duration: float = 0.15) -> None:
        """Momentarily halts camera displacement to heighten ultimate attack execution."""
        self.freeze_timer = duration

    def set_zoom(self, zoom: float) -> None:
        """Sets target FOV zoom (1.0 = normal, 0.8 = zoom out, 1.25 = zoom in)."""
        self.target_zoom = clamp(zoom, self.MIN_ZOOM, self.MAX_ZOOM)

    def update(self, target_rect: pygame.FRect, target_facing: int, target_vx: float, dt: float) -> None:
        """Updates single-player camera trajectory, lookahead, trauma decay, and shake offsets."""
        self.noise_time += dt * 35.0

        if self.freeze_timer > 0:
            self.freeze_timer -= dt
            return

        # 1. Decay trauma
        if self.trauma > 0:
            self.trauma = max(0.0, self.trauma - self.trauma_decay * dt)

        # 2. Smooth Zoom interpolation
        self.zoom_factor = lerp(self.zoom_factor, self.target_zoom, self.zoom_speed * dt)

        if self.locked:
            return

        # 3. Look Ahead calculation
        target_lead = target_facing * self.look_ahead_distance if abs(target_vx) > 10.0 else 0.0
        self.look_ahead_x = lerp(self.look_ahead_x, target_lead, self.look_ahead_speed * dt)

        # 4. Target position with viewport centering
        desired_x = target_rect.centerx + self.look_ahead_x - (self.vw * 0.5)
        desired_y = target_rect.centery - (self.vh * 0.5)

        # 5. Critically damped lag
        self.x = lerp(self.x, desired_x, self.lag_speed * dt)
        self.y = lerp(self.y, desired_y, self.lag_speed * dt)

        # 6. Map boundary clamp
        self.x = clamp(self.x, 0, max(0, self.map_w - self.vw))
        self.y = clamp(self.y, 0, max(0, self.map_h - self.vh))

    def update_coop(self, p1, p2, dt: float) -> None:
        """
        Dynamic Co-op camera tracking:
        1. Calculates player bounding box
        2. Smoothly zooms camera based on inter-player distance
        3. Enforces Soft Leash (velocity dampening + visual alert)
        4. Enforces Hard Leash (prevents any player from ever moving offscreen)
        """
        self.noise_time += dt * 35.0

        if self.freeze_timer > 0:
            self.freeze_timer -= dt
            return

        # Decay trauma
        if self.trauma > 0:
            self.trauma = max(0.0, self.trauma - self.trauma_decay * dt)

        # 1. Player Bounding Box & Distance
        p1_r = p1.rect
        p2_r = p2.rect
        
        dx = p2_r.centerx - p1_r.centerx
        dy = p2_r.centery - p1_r.centery
        dist = math.hypot(dx, dy)
        self.current_player_distance = dist

        center_x = (p1_r.centerx + p2_r.centerx) * 0.5
        center_y = (p1_r.centery + p2_r.centery) * 0.5

        # 2. Dynamic Zoom Calculation: zoom = f(distance) with easing
        t = clamp((dist - 140.0) / (self.MAX_PLAYER_DISTANCE - 140.0), 0.0, 1.0)
        # Smooth quadratic easing
        ease_t = t * t * (3.0 - 2.0 * t)
        self.target_zoom = lerp(self.MAX_ZOOM, self.MIN_ZOOM, ease_t)
        self.zoom_factor = lerp(self.zoom_factor, self.target_zoom, self.zoom_speed * dt)

        # 3. Camera Position Centering
        desired_x = center_x - (self.vw * 0.5)
        desired_y = center_y - (self.vh * 0.5)
        
        self.x = lerp(self.x, desired_x, self.lag_speed * dt)
        self.y = lerp(self.y, desired_y, self.lag_speed * dt)
        self.x = clamp(self.x, 0, max(0, self.map_w - self.vw))
        self.y = clamp(self.y, 0, max(0, self.map_h - self.vh))

        # 4. Soft Leash (Margin = 48px from viewport edge)
        margin = 48.0
        self.p1_leash_alert = (
            p1_r.left < self.x + margin or
            p1_r.right > self.x + self.vw - margin
        )
        self.p2_leash_alert = (
            p2_r.left < self.x + margin or
            p2_r.right > self.x + self.vw - margin
        )

        # Gentle outward velocity dampening without abrupt snapping
        if p1_r.left < self.x + margin and p1.velocity.x < 0:
            p1.velocity.x *= 0.85
        if p1_r.right > self.x + self.vw - margin and p1.velocity.x > 0:
            p1.velocity.x *= 0.85

        if p2_r.left < self.x + margin and p2.velocity.x < 0:
            p2.velocity.x *= 0.85
        if p2_r.right > self.x + self.vw - margin and p2.velocity.x > 0:
            p2.velocity.x *= 0.85

        # 5. Hard Leash: Absolute boundary clamping (Players NEVER leave screen)
        hard_margin = 12.0
        p1.rect.left = max(self.x + hard_margin, p1.rect.left)
        p1.rect.right = min(self.x + self.vw - hard_margin, p1.rect.right)
        p1.pos.x = p1.rect.x

        p2.rect.left = max(self.x + hard_margin, p2.rect.left)
        p2.rect.right = min(self.x + self.vw - hard_margin, p2.rect.right)
        p2.pos.x = p2.rect.x

    def draw_coop_overlay(self, surface: pygame.Surface, p1, p2) -> None:
        """Renders subtle, non-intrusive co-op tether and edge indicator cues."""
        off = self.offset
        p1_x = p1.rect.centerx - off.x
        p1_y = p1.rect.centery - off.y
        p2_x = p2.rect.centerx - off.x
        p2_y = p2.rect.centery - off.y

        # 1. Subtle glowing tether line when players are separated (> 220px)
        if self.current_player_distance > 220.0:
            dist_factor = clamp((self.current_player_distance - 220.0) / (self.MAX_PLAYER_DISTANCE - 220.0), 0.0, 1.0)
            alpha = int(90 * dist_factor)
            if alpha > 0:
                line_surf = pygame.Surface((self.vw, self.vh), pygame.SRCALPHA)
                tether_color = (80, 200, 255, alpha) if not (self.p1_leash_alert or self.p2_leash_alert) else (255, 140, 50, alpha)
                pygame.draw.line(line_surf, tether_color, (int(p1_x), int(p1_y)), (int(p2_x), int(p2_y)), 1)
                surface.blit(line_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        # 2. Edge Leash Chevron Alerts
        if self.p1_leash_alert:
            self._draw_edge_chevron(surface, p1_x, p1_y, (0, 220, 255))
        if self.p2_leash_alert:
            self._draw_edge_chevron(surface, p2_x, p2_y, (255, 180, 50))

    def _draw_edge_chevron(self, surface: pygame.Surface, px: float, py: float, color: Tuple[int, int, int]):
        """Draws small directional chevron near screen border."""
        cx = max(16, min(self.vw - 16, px))
        cy = max(16, min(self.vh - 16, py))
        alpha = int(160 + 80 * math.sin(pygame.time.get_ticks() * 0.01))
        chev_surf = pygame.Surface((16, 16), pygame.SRCALPHA)
        pygame.draw.circle(chev_surf, (*color, alpha), (8, 8), 6, width=1)
        surface.blit(chev_surf, (cx - 8, cy - 8), special_flags=pygame.BLEND_RGBA_ADD)

    @property
    def offset(self) -> pygame.math.Vector2:
        """Calculates final rendered offset including Perlin noise trauma shake."""
        shake_x = 0.0
        shake_y = 0.0

        if self.trauma > 0:
            shake_mag = (self.trauma ** 2.0) * self.max_shake_offset
            noise_x = self.noise.noise2(self.noise_time, 0.0)
            noise_y = self.noise.noise2(0.0, self.noise_time)
            shake_x = noise_x * shake_mag
            shake_y = noise_y * shake_mag

        return pygame.math.Vector2(self.x + shake_x, self.y + shake_y)

    @property
    def viewport(self) -> pygame.FRect:
        """Returns the world-space bounding box currently visible through the camera."""
        return pygame.FRect(self.x, self.y, self.vw, self.vh)

    @property
    def visible_rect(self) -> pygame.FRect:
        return self.viewport

    def apply(self, rect: pygame.FRect) -> pygame.FRect:
        """Translates a world rect into camera screen coordinates."""
        off = self.offset
        return pygame.FRect(rect.x - off.x, rect.y - off.y, rect.width, rect.height)
