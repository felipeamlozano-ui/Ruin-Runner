"""
Ruin Engine V3.0 — Clouds & Sky Atmosphere Parallax System.
Loads pixel-art clouds (craftpix-net-801184: Clouds_white and Clouds_gray),
pre-scales them into depth layers (distant layer: motion_scale 0.18-0.24, mid layer: motion_scale 0.40),
and renders with continuous independent horizontal autoscroll decoupled from camera motion.
Supports configurable sky_horizon_y, warm/cool cloud_tint, and cloud_opacity_scale per stage.
Guarantees uniform spatial distribution across the entire camera horizontal extent,
strictly bounded above the horizon, with zero runtime gradient or state allocation overhead.
"""

import os
import random
import pygame
import numpy as np
from typing import List, Optional, Tuple


class Cloud:
    __slots__ = ('x', 'y', 'speed', 'surf', 'w', 'h', 'motion_scale', 'layer', 'alpha')

    def __init__(self, x: float, y: float, speed: float, surf: pygame.Surface, motion_scale: float, layer: str = "mid", alpha: int = 255):
        self.x = float(x)
        self.y = float(y)
        self.speed = float(speed)
        self.surf = surf
        self.w = surf.get_width()
        self.h = surf.get_height()
        self.motion_scale = float(motion_scale)
        self.layer = layer
        self.alpha = int(alpha)


class CloudsManager:
    """
    Atmospheric multi-layered cloud parallax system.
    Decoupled from rigid camera motion with independent horizontal autoscroll.
    Uniform screen-relative spatial distribution with strict camera frustum culling.
    """

    def __init__(
        self,
        theme: str = "white",
        map_width: int = 4000,
        cloud_count: int = 14,
        screen_w: int = 640,
        sky_horizon_y: int = 70,
        cloud_tint: Optional[Tuple[int, int, int]] = None,
        cloud_opacity_scale: float = 1.0,
    ):
        self.theme = theme  # "white", "gray", "black"
        self.map_width = max(1200, map_width)
        self.screen_w = screen_w
        self.sky_horizon_y = sky_horizon_y
        self.cloud_tint = cloud_tint
        self.cloud_opacity_scale = max(0.1, float(cloud_opacity_scale))
        self.buffer = 160
        self.virtual_w = screen_w + self.buffer * 2  # 960px virtual sky period
        self.clouds: List[Cloud] = []

        # Lightning for stormy/dark themes
        self.lightning_surfs: List[pygame.Surface] = []
        self.lightning_active = False
        self.lightning_timer = 0.0
        self.lightning_pos = (0, 0)
        self.lightning_frame = 0

        self.distant_surfs: List[Tuple[pygame.Surface, int]] = []
        self.mid_surfs: List[Tuple[pygame.Surface, int]] = []

        self._load_assets()
        self._spawn_clouds(cloud_count)

    def _load_assets(self):
        base_dir = os.path.join("assets", "sprites", "clouds", "PNG")

        # Load from both Clouds_white and Clouds_gray for rich sky atmosphere
        target_folders = ["Clouds_white", "Clouds_gray"]
        if self.theme == "black":
            target_folders = ["Clouds_black", "Clouds_gray"]
        elif self.theme == "gray":
            target_folders = ["Clouds_gray", "Clouds_white"]

        raw_clouds = []
        for folder_name in target_folders:
            theme_path = os.path.join(base_dir, folder_name)
            if not os.path.exists(theme_path):
                continue
            for shape in ["Shape1", "Shape2", "Shape3", "Shape4", "Shape5", "Shape6", "Shape7", "Shape8"]:
                sp = os.path.join(theme_path, shape)
                if os.path.exists(sp):
                    for f in sorted(os.listdir(sp))[:3]:
                        if f.endswith(".png"):
                            fp = os.path.join(sp, f)
                            try:
                                img = pygame.image.load(fp)
                                disp = pygame.display.get_surface()
                                if disp:
                                    img = img.convert_alpha()
                                raw_clouds.append(img)
                            except Exception:
                                pass

        if not raw_clouds:
            # Fallback procedural cloud
            fallback = pygame.Surface((100, 36), pygame.SRCALPHA)
            pygame.draw.ellipse(fallback, (240, 245, 255, 180), (0, 0, 100, 36))
            raw_clouds.append(fallback)

        is_low_sky = (self.sky_horizon_y <= 60)

        # ─────────────────────────────────────────────────────────────────
        # 1. Distant layer
        # ─────────────────────────────────────────────────────────────────
        for img in raw_clouds:
            if is_low_sky:
                scale_fac = min(0.30, 14.0 / max(1, img.get_height()))
                dw = max(48, int(img.get_width() * scale_fac))
                dh = max(10, int(img.get_height() * scale_fac))
                d_alpha = max(40, min(80, int(random.randint(55, 80) * self.cloud_opacity_scale)))
            else:
                scale_fac = min(0.65, 45.0 / max(1, img.get_height()))
                dw = max(80, int(img.get_width() * scale_fac))
                dh = max(28, int(img.get_height() * scale_fac))
                d_alpha = int(random.randint(110, 155) * self.cloud_opacity_scale)

            d_surf = pygame.transform.smoothscale(img, (dw, dh))

            # Apply stage color tint (e.g. warm sunset for beach, cool slate for fortress)
            if self.cloud_tint:
                t_surf = pygame.Surface((dw, dh))
                t_surf.fill(self.cloud_tint)
                d_surf.blit(t_surf, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

            # Soft vertical bottom fade and per-pixel alpha modulation for low-horizon skies
            if is_low_sky and dh >= 6:
                fade_h = min(5, dh // 2)
                alpha_arr = pygame.surfarray.pixels_alpha(d_surf)
                # Modulate per-pixel alpha directly into the texture
                alpha_arr[:] = np.clip(alpha_arr.astype(np.float32) * (d_alpha / 255.0), 0, 255).astype(np.uint8)
                for dy in range(fade_h):
                    weight = dy / float(fade_h)
                    alpha_arr[:, dh - 1 - dy] = (alpha_arr[:, dh - 1 - dy] * weight).astype(np.uint8)
                del alpha_arr
            else:
                d_surf.set_alpha(max(20, min(255, d_alpha)))

            disp = pygame.display.get_surface()
            if disp:
                d_surf = d_surf.convert_alpha()
            self.distant_surfs.append((d_surf, d_alpha))

        # ─────────────────────────────────────────────────────────────────
        # 2. Mid layer
        # ─────────────────────────────────────────────────────────────────
        for img in raw_clouds:
            if is_low_sky:
                scale_fac = min(0.42, 18.0 / max(1, img.get_height()))
                mw = max(70, int(img.get_width() * scale_fac))
                mh = max(14, int(img.get_height() * scale_fac))
                m_alpha = max(45, min(85, int(random.randint(70, 95) * self.cloud_opacity_scale)))
            else:
                scale_fac = min(1.05, 75.0 / max(1, img.get_height()))
                mw = max(140, int(img.get_width() * scale_fac))
                mh = max(48, int(img.get_height() * scale_fac))
                m_alpha = int(random.randint(165, 215) * self.cloud_opacity_scale)

            m_surf = pygame.transform.smoothscale(img, (mw, mh))

            # Apply stage color tint
            if self.cloud_tint:
                t_surf = pygame.Surface((mw, mh))
                t_surf.fill(self.cloud_tint)
                m_surf.blit(t_surf, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

            # Soft vertical bottom fade and per-pixel alpha modulation for low-horizon skies
            if is_low_sky and mh >= 6:
                fade_h = min(6, mh // 2)
                alpha_arr = pygame.surfarray.pixels_alpha(m_surf)
                alpha_arr[:] = np.clip(alpha_arr.astype(np.float32) * (m_alpha / 255.0), 0, 255).astype(np.uint8)
                for dy in range(fade_h):
                    weight = dy / float(fade_h)
                    alpha_arr[:, mh - 1 - dy] = (alpha_arr[:, mh - 1 - dy] * weight).astype(np.uint8)
                del alpha_arr
            else:
                m_surf.set_alpha(max(30, min(255, m_alpha)))

            disp = pygame.display.get_surface()
            if disp:
                m_surf = m_surf.convert_alpha()
            self.mid_surfs.append((m_surf, m_alpha))

        # Load lightning if stormy
        if self.theme in ("black", "gray"):
            light_path = os.path.join(base_dir, "Lightning")
            if os.path.exists(light_path):
                for f in sorted(os.listdir(light_path)):
                    if f.endswith(".png"):
                        try:
                            lim = pygame.image.load(os.path.join(light_path, f))
                            disp = pygame.display.get_surface()
                            if disp:
                                lim = lim.convert_alpha()
                            lw = max(48, int(lim.get_width() * 0.8))
                            lh = max(96, int(lim.get_height() * 0.8))
                            self.lightning_surfs.append(pygame.transform.smoothscale(lim, (lw, lh)))
                        except Exception:
                            pass

    def _spawn_clouds(self, count: int):
        if not self.distant_surfs or not self.mid_surfs:
            return

        total_count = max(4, count)
        dist_count = total_count // 2 + 1
        mid_count = total_count - dist_count
        is_low_sky = (self.sky_horizon_y <= 60)

        # 1. Distant Clouds Layer: uniformly spaced across virtual sky period
        dist_spacing = self.virtual_w / float(dist_count)
        for i in range(dist_count):
            surf, alpha = random.choice(self.distant_surfs)
            x = (i * dist_spacing + random.uniform(-15, 15)) % self.virtual_w
            if is_low_sky:
                # Strictly bounded in upper band so c.y + c.h <= sky_horizon_y
                max_spawn_y = max(3.0, float(self.sky_horizon_y) - float(surf.get_height()) - 2.0)
                y = random.uniform(2.0, max_spawn_y)
            else:
                y = random.uniform(6.0, 32.0)

            speed = random.uniform(7.0, 14.0)
            motion_scale = random.uniform(0.18, 0.24)
            self.clouds.append(Cloud(x, y, speed, surf, motion_scale, layer="distant", alpha=alpha))

        # 2. Mid Clouds Layer: uniformly spaced across virtual sky period
        mid_spacing = self.virtual_w / float(mid_count)
        for i in range(mid_count):
            surf, alpha = random.choice(self.mid_surfs)
            x = (i * mid_spacing + random.uniform(-20, 20)) % self.virtual_w
            if is_low_sky:
                max_spawn_y = max(4.0, float(self.sky_horizon_y) - float(surf.get_height()) - 1.5)
                y = random.uniform(3.0, max_spawn_y)
            else:
                y = random.uniform(16.0, 54.0)

            speed = random.uniform(16.0, 26.0)
            motion_scale = 0.40
            self.clouds.append(Cloud(x, y, speed, surf, motion_scale, layer="mid", alpha=alpha))

    def update(self, dt: float, wind: float = 0.0):
        """Continuous independent horizontal autoscroll decoupled from player movement."""
        vw = float(self.virtual_w)
        for c in self.clouds:
            c.x = (c.x + (c.speed + wind) * dt) % vw

        # Lightning timer for dark themes
        if self.lightning_surfs:
            self.lightning_timer -= dt
            if self.lightning_timer <= 0:
                if random.random() < 0.25:
                    self.lightning_active = True
                    self.lightning_frame = random.randint(0, len(self.lightning_surfs) - 1)
                    self.lightning_pos = (random.uniform(50, self.screen_w - 50), random.uniform(15, 70))
                    self.lightning_timer = random.uniform(4.0, 9.0)
                else:
                    self.lightning_timer = random.uniform(2.0, 5.0)
            elif self.lightning_timer < 4.0:
                self.lightning_active = False

    def draw(self, surface: pygame.Surface, cam_offset: tuple, screen_w: int = 640, screen_h: int = 360):
        """
        Draws layered clouds with smooth parallax depth and strict screen-space frustum culling.
        Guarantees uniform sky coverage across 0..screen_w and zero bleeding below sky_horizon_y.
        Uses native SDL2 batch blitting (surface.blits) for peak CPU performance.
        """
        cam_x, cam_y = cam_offset
        vw = self.virtual_w
        buf = self.buffer
        sw = screen_w

        # Restrict drawing to the sky horizon line
        prev_clip = surface.get_clip()
        surface.set_clip(pygame.Rect(0, 0, sw, self.sky_horizon_y))

        try:
            cloud_batch = []
            for c in self.clouds:
                # Screen-space X position wrapping smoothly across virtual sky window
                screen_x = ((c.x - cam_x * c.motion_scale) % vw) - buf

                # Strict frustum culling against viewport
                if screen_x + c.w >= 0 and screen_x <= sw:
                    draw_y = c.y - cam_y * (c.motion_scale * 0.12)
                    cloud_batch.append((c.surf, (int(screen_x), int(draw_y))))

            if cloud_batch:
                surface.blits(cloud_batch)

            # Draw lightning if active and in view
            if self.lightning_active and self.lightning_surfs:
                lx, ly = self.lightning_pos
                if 0 <= lx <= sw:
                    surface.blit(self.lightning_surfs[self.lightning_frame], (lx, ly))
        finally:
            surface.set_clip(prev_clip)


# Dedicated ParallaxBackground alias as specified in requirements
ParallaxBackground = CloudsManager
