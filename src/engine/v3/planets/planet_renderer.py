"""
Ruin Engine V3.0 — Deep-Fold PixelPlanets Spherical Generator & Renderer.
Simulates 3D pixel-art rotating planets (Terran, Lava, Ice, Gas Giant)
using spherical UV projection, dithering, rim-lighting, and pre-baked frame loops for 60 FPS.
"""

import math
import os
import pygame
from typing import Dict, List, Tuple

# Atmospheric glow colors for each realm
ATMOSPHERE_COLORS = {
    "terrae": (85, 165, 255),
    "sanguis": (255, 65, 45),
    "glacies": (95, 225, 255),
    "aetheria": (255, 215, 85)
}


class PixelPlanetRenderer:
    """Renders rotating 3D pixel planets with 48 smooth frames and crisp integer scaling."""
    
    _PLANET_FRAMES_CACHE: Dict[str, List[pygame.Surface]] = {}
    
    def __init__(self, world_id: str = "terrae", radius: int = 30, target_size: int = 120):
        self.world_id = world_id if world_id in ATMOSPHERE_COLORS else "terrae"
        self.radius = radius
        self.target_size = target_size
        self.current_frame = 0.0
        self.rotation_speed = 12.0 # Smooth 4-second revolution at 48 frames
        
        self.frames = self._get_or_bake_frames(self.world_id, self.radius, self.target_size)
        
    @classmethod
    def _get_or_bake_frames(cls, world_id: str, radius: int, target_size: int) -> List[pygame.Surface]:
        cache_key = f"{world_id}_{radius}_{target_size}"
        if cache_key in cls._PLANET_FRAMES_CACHE:
            return cls._PLANET_FRAMES_CACHE[cache_key]
            
        d = radius * 2
        sphere_pixels = []
        for y in range(d):
            dy = (y + 0.5 - radius) / float(radius)
            if abs(dy) >= 1.0:
                continue
            for x in range(d):
                dx = (x + 0.5 - radius) / float(radius)
                r_sq = dx * dx + dy * dy
                if r_sq >= 1.0:
                    continue
                dz = math.sqrt(max(0.0, 1.0 - r_sq))
                
                # Top-left celestial light source
                lx, ly, lz = -0.58, -0.45, 0.68
                dot = (dx * lx + dy * ly + dz * lz) / math.sqrt(lx*lx + ly*ly + lz*lz)
                light = max(0.12, min(1.0, dot * 0.88 + 0.36))
                
                base_lon = math.atan2(dx, dz)
                lat = dy * 2.5
                abs_dy = abs(dy)
                sphere_pixels.append((x, y, dx, dy, dz, base_lon, lat, light, abs_dy))

        num_frames = 48
        baked_frames = []
        atm_col = ATMOSPHERE_COLORS.get(world_id, (100, 160, 255))
        
        for f in range(num_frames):
            rot = (f / num_frames) * (2.0 * math.pi)
            surf = pygame.Surface((d, d), pygame.SRCALPHA)
            
            for x, y, dx, dy, dz, base_lon, lat, light, abs_dy in sphere_pixels:
                lon = base_lon + rot
                
                if world_id == "terrae":
                    # Polar ice caps
                    if abs_dy > 0.74 + math.sin(lon * 4.0) * 0.04:
                        px = (245, 250, 255) if light > 0.45 else (195, 215, 240)
                    else:
                        # Continents vs Oceans
                        val = math.sin(lon * 2.6) * math.cos(lat * 1.8) + \
                              math.sin(lon * 5.4 + lat * 3.2) * 0.42 + \
                              math.cos(lon * 1.3 - lat * 2.2) * 0.32
                        if val > 0.10:
                            # Land
                            if val > 0.46 and light > 0.5:
                                px = (120, 115, 95) # Mountain peak
                            elif val > 0.28:
                                px = (52, 130, 48) if light > 0.45 else (35, 95, 36)
                            else:
                                px = (42, 105, 42) if light > 0.45 else (28, 75, 32)
                        else:
                            # Ocean
                            if val > -0.06:
                                px = (48, 125, 180) # Shallow coastal shelf
                            elif light > 0.88:
                                px = (165, 215, 255) # Ocean specular sun glint
                            elif light > 0.50:
                                px = (32, 68, 142) # Deep blue sea
                            else:
                                px = (18, 32, 75) # Abyssal sea
                                
                        # Dual-speed clouds layer (rotates 1.25x faster than terrain)
                        c_lon = base_lon + rot * 1.25
                        c_val = math.sin(c_lon * 3.6) * math.cos(lat * 2.4) + math.cos(c_lon * 6.5 - lat * 1.6) * 0.35
                        if c_val > 0.36:
                            px = (245, 252, 255) if (c_val > 0.50 and light > 0.4) else (195, 215, 240)

                elif world_id == "sanguis":
                    # Dark obsidian basalt crust & glowing magma oceans
                    val = math.sin(lon * 2.8) * math.cos(lat * 2.0) + math.cos(lon * 6.5 + lat * 3.8) * 0.45
                    if val < -0.08:
                        # Molten magma seas
                        heat = math.sin(lon * 8.0 + rot * 4.0) * 0.5 + 0.5
                        if heat > 0.70 or val < -0.32:
                            px = (255, 210, 70) # Glowing magma core
                        elif heat > 0.35:
                            px = (255, 95, 30) # Liquid lava
                        else:
                            px = (180, 35, 25) # Cooling lava
                    else:
                        # Basalt crags & glowing fissures
                        if abs(val - 0.20) < 0.05:
                            px = (255, 130, 40) # Glowing lava fissure
                        elif val > 0.35 and light > 0.4:
                            px = (75, 30, 38) # Highland basalt
                        else:
                            px = (45, 18, 25) if light > 0.4 else (22, 10, 15)

                elif world_id == "glacies":
                    # Crystalline ice world & shimmering aurora
                    val = math.sin(lon * 3.0) * math.cos(lat * 2.2) + math.sin(lon * 7.2 - lat * 3.5) * 0.40
                    if abs_dy > 0.58 and (math.sin(lon * 4.0 + rot * 2.5) > 0.3):
                        px = (70, 248, 235) # Polar cyan aurora ribbons
                    elif val > 0.25:
                        px = (250, 255, 255) if light > 0.5 else (205, 235, 255) # Glacial snow ridges
                    elif val > -0.10:
                        px = (105, 185, 225) if light > 0.4 else (65, 135, 185) # Ice pack
                    else:
                        px = (38, 85, 138) # Deep frozen chasm

                else: # aetheria
                    # Gas giant sweeping jet streams & Great Eye storm
                    bands = math.sin(lat * 7.0 + math.sin(lon * 2.5) * 0.4) + math.cos(lat * 14.0) * 0.22
                    # Great storm vortex
                    s_lon = ((lon - 1.1 + math.pi) % (2*math.pi)) - math.pi
                    s_lat = lat - (-0.4)
                    if (s_lon * 2.2)**2 + (s_lat * 3.8)**2 < 0.22:
                        px = (255, 225, 120) if light > 0.4 else (210, 95, 35) # Great Solar Eye
                    elif bands > 0.45:
                        px = (255, 240, 180) # Pale cream band
                    elif bands > 0.05:
                        px = (245, 188, 65) if light > 0.45 else (195, 135, 42) # Radiant gold band
                    elif bands > -0.35:
                        px = (190, 118, 38) if light > 0.45 else (145, 82, 28) # Amber band
                    else:
                        px = (135, 68, 24) # Deep bronze band
                
                # Apply spherical day/night shadow shading
                cr, cg, cb = px
                shading = light ** 0.8
                final_c = (int(cr * shading), int(cg * shading), int(cb * shading))
                surf.set_at((x, y), final_c)
                
            # Draw soft atmosphere crescent halo on lit rim
            halo_surf = pygame.Surface((d + 6, d + 6), pygame.SRCALPHA)
            pygame.draw.circle(halo_surf, (*atm_col, 55), (radius + 3, radius + 3), radius + 2, 2)
            pygame.draw.circle(halo_surf, (*atm_col, 95), (radius + 3, radius + 3), radius + 1, 1)
            surf.blit(halo_surf, (-3, -3), special_flags=pygame.BLEND_RGBA_ADD)

            # Scale with crisp nearest-neighbor integer scaling to target_size
            scaled = pygame.transform.scale(surf, (target_size, target_size))
            baked_frames.append(scaled)
            
        cls._PLANET_FRAMES_CACHE[cache_key] = baked_frames
        return baked_frames

    def update(self, dt: float):
        self.current_frame = (self.current_frame + self.rotation_speed * dt) % len(self.frames)

    def draw(self, surface: pygame.Surface, center: Tuple[int, int], scale: float = 1.0, alpha: int = 255):
        idx = int(self.current_frame) % len(self.frames)
        surf = self.frames[idx]
        
        if scale != 1.0 or alpha < 255:
            w = max(4, int(surf.get_width() * scale))
            h = max(4, int(surf.get_height() * scale))
            scaled = pygame.transform.scale(surf, (w, h))
            if alpha < 255:
                scaled.set_alpha(max(0, min(255, alpha)))
            rect = scaled.get_rect(center=center)
            surface.blit(scaled, rect)
        else:
            rect = surf.get_rect(center=center)
            surface.blit(surf, rect)
