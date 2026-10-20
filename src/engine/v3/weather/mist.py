"""
Ruin Engine V3.0 — Atmospheric Distant Fog & Ground Mist System.
Implements pre-rendered offscreen surfaces for distant mountain haze,
bridge-level ground mist, and foreground battlement mist.
Zero per-frame allocations or runtime gradient creations (100% pre-baked).
"""

import math
import pygame
from typing import Tuple, Optional


class MistManager:
    """
    Manages atmospheric depth fog and dynamic ground mist.
    All textures are pre-rendered into Offscreen surfaces once at initialization.
    Runtime execution uses dual-slice blitting with zero runtime memory allocations.
    """

    def __init__(self, screen_w: int = 640, screen_h: int = 360, floor_y: int = 280, theme: str = "road"):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.floor_y = floor_y
        self.theme = theme

        # Continuous autoscroll offsets (in pixels)
        self.distant_scroll = 0.0
        self.ground_scroll = 0.0
        self.battlement_scroll = 0.0

        # Scroll speeds (pixels per second)
        self.distant_speed = 5.0
        self.ground_speed = 13.0
        self.battlement_speed = -8.0

        # Parallax depth factors relative to camera motion
        self.distant_parallax = 0.18
        self.ground_parallax = 0.35
        self.battlement_parallax = 0.40

        # Vertical screen anchors
        self.distant_y = 65
        self.ground_y = max(180, floor_y - 28)
        self.battlement_y = screen_h - 52

        # Pre-baked tileable surfaces
        self.distant_fog_surf: Optional[pygame.Surface] = None
        self.ground_mist_surf: Optional[pygame.Surface] = None
        self.battlement_mist_surf: Optional[pygame.Surface] = None

        self._prebake_surfaces()

    def _prebake_surfaces(self) -> None:
        """Pre-renders tileable atmospheric textures once into memory."""
        try:
            import numpy as np

            # ─────────────────────────────────────────────────────────────────
            # 1. Distant Fog (Atmospheric separation between mountains & towers)
            # ─────────────────────────────────────────────────────────────────
            fog_w, fog_h = self.screen_w, 110
            self.distant_fog_surf = pygame.Surface((fog_w, fog_h), pygame.SRCALPHA, 32)

            x = np.arange(fog_w)[:, None]
            y = np.arange(fog_h)[None, :]

            # Smooth cosine vertical distribution (peaks in center-low, fades at edges)
            vert_curve = 0.5 - 0.5 * np.cos(2.0 * np.pi * y / float(fog_h))
            
            # Subtle tileable horizontal harmonics
            horiz_curve = (
                0.72
                + 0.18 * np.sin(2.0 * np.pi * x / float(fog_w))
                + 0.10 * np.cos(4.0 * np.pi * x / float(fog_w))
            )
            
            # Atmospheric cool slate/emerald tint (Emerald Fortress theme)
            fog_alpha = np.clip(vert_curve * horiz_curve * 68.0, 0.0, 72.0).astype(np.uint8)

            p3d = pygame.surfarray.pixels3d(self.distant_fog_surf)
            p3d[..., 0] = 135
            p3d[..., 1] = 168
            p3d[..., 2] = 162
            del p3d

            pa = pygame.surfarray.pixels_alpha(self.distant_fog_surf)
            pa[:] = fog_alpha
            del pa

            # ─────────────────────────────────────────────────────────────────
            # 2. Ground Mist (Gliding over bridge floor at foot height)
            # ─────────────────────────────────────────────────────────────────
            mist_w, mist_h = self.screen_w, 62
            self.ground_mist_surf = pygame.Surface((mist_w, mist_h), pygame.SRCALPHA, 32)

            x = np.arange(mist_w)[:, None]
            y = np.arange(mist_h)[None, :]

            # Ground mist curve: soft falloff top and bottom, alpha strictly 0.12 - 0.22 (30..55 / 255)
            # Preserves contact shadows and characters' feet without hiding them
            gm_vert = np.sin(np.pi * y / float(mist_h)) ** 1.3
            gm_horiz = (
                0.65
                + 0.22 * np.sin(2.0 * np.pi * x / float(mist_w))
                + 0.13 * np.sin(6.0 * np.pi * x / float(mist_w) + 1.2)
            )
            ground_alpha = np.clip(gm_vert * gm_horiz * 52.0, 0.0, 55.0).astype(np.uint8)

            p3d = pygame.surfarray.pixels3d(self.ground_mist_surf)
            p3d[..., 0] = 195
            p3d[..., 1] = 215
            p3d[..., 2] = 210
            del p3d

            pa = pygame.surfarray.pixels_alpha(self.ground_mist_surf)
            pa[:] = ground_alpha
            del pa

            # ─────────────────────────────────────────────────────────────────
            # 3. Battlement Mist (Subtle foreground band at the bottom of screen)
            # ─────────────────────────────────────────────────────────────────
            bat_w, bat_h = self.screen_w, 52
            self.battlement_mist_surf = pygame.Surface((bat_w, bat_h), pygame.SRCALPHA, 32)

            x = np.arange(bat_w)[:, None]
            y = np.arange(bat_h)[None, :]

            bm_vert = np.sin(np.pi * y / float(bat_h)) ** 1.5
            bm_horiz = (
                0.70
                + 0.20 * np.cos(2.0 * np.pi * x / float(bat_w))
                + 0.10 * np.sin(4.0 * np.pi * x / float(bat_w) + 0.8)
            )
            bat_alpha = np.clip(bm_vert * bm_horiz * 40.0, 0.0, 42.0).astype(np.uint8)

            p3d = pygame.surfarray.pixels3d(self.battlement_mist_surf)
            p3d[..., 0] = 175
            p3d[..., 1] = 195
            p3d[..., 2] = 190
            del p3d

            pa = pygame.surfarray.pixels_alpha(self.battlement_mist_surf)
            pa[:] = bat_alpha
            del pa

        except Exception as err:
            # Safe procedural fallback if numpy is unavailable
            print(f"Warning: NumPy accelerated mist pre-bake fallback: {err}")
            self._prebake_procedural_fallback()

        # Optimize surfaces for display
        disp = pygame.display.get_surface()
        if disp:
            if self.distant_fog_surf:
                self.distant_fog_surf = self.distant_fog_surf.convert_alpha()
            if self.ground_mist_surf:
                self.ground_mist_surf = self.ground_mist_surf.convert_alpha()
            if self.battlement_mist_surf:
                self.battlement_mist_surf = self.battlement_mist_surf.convert_alpha()

    def _prebake_procedural_fallback(self) -> None:
        """Lightweight pygame procedural drawing fallback."""
        fog_w, fog_h = self.screen_w, 110
        self.distant_fog_surf = pygame.Surface((fog_w, fog_h), pygame.SRCALPHA, 32)
        for dy in range(fog_h):
            t = math.sin(math.pi * dy / fog_h)
            a = int(60 * t)
            pygame.draw.line(self.distant_fog_surf, (135, 168, 162, a), (0, dy), (fog_w, dy))

        mist_w, mist_h = self.screen_w, 62
        self.ground_mist_surf = pygame.Surface((mist_w, mist_h), pygame.SRCALPHA, 32)
        for dy in range(mist_h):
            t = math.sin(math.pi * dy / mist_h)
            a = int(45 * t)
            pygame.draw.line(self.ground_mist_surf, (195, 215, 210, a), (0, dy), (mist_w, dy))

        bat_w, bat_h = self.screen_w, 52
        self.battlement_mist_surf = pygame.Surface((bat_w, bat_h), pygame.SRCALPHA, 32)
        for dy in range(bat_h):
            t = math.sin(math.pi * dy / bat_h)
            a = int(35 * t)
            pygame.draw.line(self.battlement_mist_surf, (175, 195, 190, a), (0, dy), (bat_w, dy))

    def update(self, dt: float) -> None:
        """Updates continuous horizontal drift offsets."""
        sw = float(self.screen_w)
        self.distant_scroll = (self.distant_scroll + self.distant_speed * dt) % sw
        self.ground_scroll = (self.ground_scroll + self.ground_speed * dt) % sw
        self.battlement_scroll = (self.battlement_scroll + self.battlement_speed * dt) % sw

    def _draw_tileable_slice(self, surface: pygame.Surface, surf: Optional[pygame.Surface], offset_x: float, y: int) -> None:
        """Dual-slice blit algorithm with 100% seamless continuity and 0 allocations."""
        if surf is None:
            return
        sw = self.screen_w
        tw = surf.get_width()
        ox = int(offset_x) % tw
        x1 = -ox
        x2 = x1 + tw
        surface.blit(surf, (x1, y))
        if x2 < sw:
            surface.blit(surf, (x2, y))
        if x2 + tw < sw:
            surface.blit(surf, (x2 + tw, y))

    def draw_distant_fog(self, surface: pygame.Surface, cam_x: float, cam_y: float = 0.0) -> None:
        """Draws the soft atmospheric haze between distant mountains and castle towers."""
        offset = cam_x * self.distant_parallax + self.distant_scroll
        draw_y = int(self.distant_y - cam_y * (self.distant_parallax * 0.15))
        self._draw_tileable_slice(surface, self.distant_fog_surf, offset, draw_y)

    def draw_ground_mist(self, surface: pygame.Surface, cam_x: float, cam_y: float = 0.0) -> None:
        """Draws the dynamic ground mist gliding over the bridge floor at feet level."""
        offset = cam_x * self.ground_parallax + self.ground_scroll
        draw_y = int(self.ground_y - cam_y)
        self._draw_tileable_slice(surface, self.ground_mist_surf, offset, draw_y)

    def draw_foreground_mist(self, surface: pygame.Surface, cam_x: float, cam_y: float = 0.0) -> None:
        """Draws the subtle mist band across the bottom foreground battlements."""
        offset = cam_x * self.battlement_parallax + self.battlement_scroll
        draw_y = int(self.battlement_y - cam_y * 0.1)
        self._draw_tileable_slice(surface, self.battlement_mist_surf, offset, draw_y)
