"""
Ruin Engine V3.0 — Clouds & Sky Atmosphere Parallax System.
Loads pixel-art clouds (craftpix-net-801184: Clouds_white and Clouds_gray),
pre-scales them into depth layers (distant layer: motion_scale 0.15-0.25, mid layer: motion_scale 0.40),
and renders with continuous independent horizontal autoscroll decoupled from camera motion.
"""

import os
import random
import pygame
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
        self.alpha = alpha


class CloudsManager:
    """
    Atmospheric multi-layered cloud parallax system.
    Decoupled from rigid camera motion with independent horizontal autoscroll.
    """
    
    def __init__(self, theme: str = "white", map_width: int = 4000, cloud_count: int = 16):
        self.theme = theme # "white", "gray", "black"
        self.map_width = max(1200, map_width)
        self.clouds: List[Cloud] = []
        
        # Lightning for stormy/dark themes
        self.lightning_surfs: List[pygame.Surface] = []
        self.lightning_active = False
        self.lightning_timer = 0.0
        self.lightning_pos = (0, 0)
        self.lightning_frame = 0
        
        self.distant_surfs: List[pygame.Surface] = []
        self.mid_surfs: List[pygame.Surface] = []
        
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
                    for f in sorted(os.listdir(sp))[:2]: # 2 variations per shape
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
            fallback = pygame.Surface((60, 24), pygame.SRCALPHA)
            pygame.draw.ellipse(fallback, (240, 245, 255, 180), (0, 0, 60, 24))
            raw_clouds.append(fallback)

        # 1. Distant layer: smaller scale (0.35x), softer appearance
        for img in raw_clouds:
            dw = max(20, int(img.get_width() * 0.35))
            dh = max(10, int(img.get_height() * 0.35))
            d_surf = pygame.transform.smoothscale(img, (dw, dh))
            self.distant_surfs.append(d_surf)

        # 2. Mid layer: medium scale (0.65x), pronounced pixel detail
        for img in raw_clouds:
            mw = max(32, int(img.get_width() * 0.65))
            mh = max(16, int(img.get_height() * 0.65))
            m_surf = pygame.transform.smoothscale(img, (mw, mh))
            self.mid_surfs.append(m_surf)

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
                            lw = max(32, int(lim.get_width() * 0.6))
                            lh = max(64, int(lim.get_height() * 0.6))
                            self.lightning_surfs.append(pygame.transform.smoothscale(lim, (lw, lh)))
                        except Exception:
                            pass

    def _spawn_clouds(self, count: int):
        if not self.distant_surfs or not self.mid_surfs:
            return
            
        spacing = self.map_width / max(1, count)
        
        # 1. Distant Clouds Layer (Smaller scale, motion_scale 0.18-0.24, gentle speed 10-16 px/s)
        dist_count = count // 2 + 1
        for i in range(dist_count):
            surf = random.choice(self.distant_surfs)
            x = i * (self.map_width / dist_count) + random.uniform(-40, 40)
            y = random.uniform(4, 38)
            speed = random.uniform(10.0, 16.0)
            motion_scale = random.uniform(0.18, 0.24)
            self.clouds.append(Cloud(x, y, speed, surf, motion_scale, layer="distant", alpha=195))

        # 2. Mid Clouds Layer (Medium scale, motion_scale 0.40, faster speed 22-30 px/s)
        mid_count = count - dist_count
        for i in range(mid_count):
            surf = random.choice(self.mid_surfs)
            x = i * (self.map_width / mid_count) + random.uniform(-50, 50)
            y = random.uniform(18, 56)
            speed = random.uniform(22.0, 30.0)
            motion_scale = 0.40
            self.clouds.append(Cloud(x, y, speed, surf, motion_scale, layer="mid", alpha=255))

    def update(self, dt: float, wind: float = 0.0):
        """Continuous independent horizontal autoscroll decoupled from player movement."""
        for c in self.clouds:
            c.x += (c.speed + wind) * dt
            
            # Continuous boundary wrap around virtual sky width
            if c.x > self.map_width + 120:
                c.x = -c.w - 80
                c.y = random.uniform(4, 38) if c.layer == "distant" else random.uniform(18, 56)
            elif c.x < -c.w - 120:
                c.x = self.map_width + 80

        # Lightning timer for dark themes
        if self.lightning_surfs:
            self.lightning_timer -= dt
            if self.lightning_timer <= 0:
                if random.random() < 0.25:
                    self.lightning_active = True
                    self.lightning_frame = random.randint(0, len(self.lightning_surfs) - 1)
                    self.lightning_pos = (random.uniform(100, self.map_width - 100), random.uniform(20, 80))
                    self.lightning_timer = random.uniform(4.0, 9.0)
                else:
                    self.lightning_timer = random.uniform(2.0, 5.0)
            elif self.lightning_timer < 4.0:
                self.lightning_active = False

    def draw(self, surface: pygame.Surface, cam_offset: tuple, screen_w: int = 640, screen_h: int = 480):
        """Draws layered clouds with smooth parallax depth and strict camera frustum culling."""
        cam_x, cam_y = cam_offset
        vl = cam_x - 180
        vr = cam_x + screen_w + 180

        for c in self.clouds:
            # Independent drift + camera parallax depth offset
            draw_x = c.x - cam_x * c.motion_scale
            if vl <= draw_x <= vr:
                draw_y = c.y - cam_y * (c.motion_scale * 0.20)
                surface.blit(c.surf, (draw_x, draw_y))

        # Draw lightning if active and in view
        if self.lightning_active and self.lightning_surfs:
            lx, ly = self.lightning_pos
            if vl <= lx <= vr:
                surface.blit(self.lightning_surfs[self.lightning_frame], (lx - cam_x, ly - cam_y))


# Dedicated ParallaxBackground alias as specified in requirements
ParallaxBackground = CloudsManager
