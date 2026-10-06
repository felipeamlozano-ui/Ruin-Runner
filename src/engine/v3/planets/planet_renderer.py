"""
Ruin Engine V3.0 — Deep-Fold PixelPlanets Spherical Generator & Renderer.
Simulates 3D pixel-art rotating planets (Terran, Lava, Ice, Gas Giant)
using spherical UV projection, dithering, rim-lighting, and pre-baked frame loops for 60 FPS.
"""

import math
import os
import pygame
from typing import Dict, List, Tuple

# Palettes for the four story worlds
PLANET_PALETTES = {
    "terrae": {
        "ocean": [(20, 35, 75), (35, 65, 130), (55, 105, 185)],
        "land": [(40, 95, 45), (65, 140, 60), (110, 185, 80)],
        "clouds": (230, 240, 255),
        "atmosphere": (90, 160, 255, 65)
    },
    "sanguis": {
        "ocean": [(60, 15, 20), (120, 25, 30), (190, 40, 35)],
        "land": [(35, 20, 30), (70, 35, 45), (115, 55, 65)],
        "clouds": (255, 110, 70),
        "atmosphere": (220, 50, 60, 80)
    },
    "glacies": {
        "ocean": [(30, 70, 110), (50, 115, 165), (85, 165, 215)],
        "land": [(140, 200, 240), (195, 230, 255), (255, 255, 255)],
        "clouds": (210, 245, 255),
        "atmosphere": (140, 220, 255, 60)
    },
    "aetheria": {
        "ocean": [(120, 75, 20), (180, 120, 35), (230, 175, 50)],
        "land": [(160, 105, 30), (220, 155, 45), (255, 215, 90)],
        "clouds": (255, 245, 180),
        "atmosphere": (255, 205, 70, 75)
    }
}

class PixelPlanetRenderer:
    """Renders rotating pixel planets based on Deep-Fold PixelPlanets logic."""
    
    _PLANET_FRAMES_CACHE: Dict[str, List[pygame.Surface]] = {}
    
    def __init__(self, world_id: str = "terrae", radius: int = 36, target_size: int = 144):
        self.world_id = world_id if world_id in PLANET_PALETTES else "terrae"
        self.radius = radius
        self.target_size = target_size
        self.current_frame = 0.0
        self.rotation_speed = 12.0 # Frames per second
        
        self.frames = self._get_or_bake_frames(self.world_id, self.radius, self.target_size)
        
    @classmethod
    def _get_or_bake_frames(cls, world_id: str, radius: int, target_size: int) -> List[pygame.Surface]:
        cache_key = f"{world_id}_{radius}_{target_size}"
        if cache_key in cls._PLANET_FRAMES_CACHE:
            return cls._PLANET_FRAMES_CACHE[cache_key]
            
        palette = PLANET_PALETTES.get(world_id, PLANET_PALETTES["terrae"])
        num_frames = 24
        baked_frames = []
        
        d = radius * 2
        for f in range(num_frames):
            frame_surf = pygame.Surface((d, d), pygame.SRCALPHA)
            rot_offset = (f / num_frames) * (2.0 * math.pi)
            
            # Render sphere pixels
            for y in range(d):
                dy = (y - radius) / float(radius)
                if abs(dy) >= 1.0:
                    continue
                row_width = math.sqrt(1.0 - dy * dy)
                x_start = int(radius - row_width * radius)
                x_end = int(radius + row_width * radius)
                
                for x in range(x_start, x_end):
                    dx = (x - radius) / float(radius)
                    r_sq = dx * dx + dy * dy
                    if r_sq >= 1.0:
                        continue
                        
                    # Spherical projection normal
                    dz = math.sqrt(1.0 - r_sq)
                    
                    # Lighting dot product (Light from top-left)
                    lx, ly, lz = -0.55, -0.45, 0.70
                    light_len = math.sqrt(lx*lx + ly*ly + lz*lz)
                    dot = (dx * lx + dy * ly + dz * lz) / light_len
                    light_factor = max(0.15, min(1.0, dot * 0.8 + 0.35))
                    
                    # Procedural terrain frequency (Simulating fbm longitude scrolling)
                    longitude = math.atan2(dx, dz) + rot_offset
                    latitude = dy * 2.5
                    
                    # Continent shape function
                    noise_val = math.sin(longitude * 3.0) * math.cos(latitude * 2.0) + \
                                math.sin(longitude * 7.0 + latitude * 4.0) * 0.45 + \
                                math.cos(longitude * 1.5 - latitude * 3.0) * 0.35
                                
                    is_land = (noise_val > 0.1)
                    colors = palette["land"] if is_land else palette["ocean"]
                    
                    # Palette shading tier
                    if light_factor > 0.7:
                        base_col = colors[2]
                    elif light_factor > 0.4:
                        base_col = colors[1]
                    else:
                        base_col = colors[0]
                        
                    # Cloud band overlay
                    cloud_noise = math.sin(longitude * 4.0 + rot_offset * 1.5) * math.cos(latitude * 3.0)
                    if cloud_noise > 0.55 and light_factor > 0.3:
                        px_col = palette["clouds"]
                    else:
                        px_col = base_col
                        
                    frame_surf.set_at((x, y), px_col)
                    
            # Atmosphere rim glow
            atm_surf = pygame.Surface((d + 4, d + 4), pygame.SRCALPHA)
            pygame.draw.circle(atm_surf, palette["atmosphere"], (radius + 2, radius + 2), radius + 1, 2)
            frame_surf.blit(atm_surf, (-2, -2))
            
            # Scale to display size with crisp nearest-neighbor integer interpolation
            scaled_frame = pygame.transform.scale(frame_surf, (target_size, target_size))
            baked_frames.append(scaled_frame)
            
        cls._PLANET_FRAMES_CACHE[cache_key] = baked_frames
        return baked_frames

    def update(self, dt: float):
        self.current_frame = (self.current_frame + self.rotation_speed * dt) % len(self.frames)

    def draw(self, surface: pygame.Surface, center: Tuple[int, int]):
        idx = int(self.current_frame) % len(self.frames)
        surf = self.frames[idx]
        rect = surf.get_rect(center=center)
        surface.blit(surf, rect)
