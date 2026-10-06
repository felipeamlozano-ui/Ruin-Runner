"""
Ruin Engine V3.0 — Rock Obstacles, Platforms & Biome Environmental Props.
Integrates pixel-art rocks from craftpix-net-675652 with pre-cached surfaces,
solid platform support, hazardous stalagmites, and zero-allocation frustum culling.
"""

import os
import pygame
from typing import Dict, Tuple, Optional

_ROCK_CACHE: Dict[Tuple[str, int, float], pygame.Surface] = {}

BIOME_FOLDER_MAP = {
    "canyon": "canyon_rocks",
    "cave": "cave_rocks",
    "desert": "desert_rocks",
    "ice": "ice_rock",
    "road": "middle_lane_rocks1",
    "middle_lane": "middle_lane_rocks2",
    "snowy": "snowy_rocks1",
    "stalagmite": "stalagmites"
}

class RockProp:
    """A static environmental rock prop, platform or hazard with pre-baked scaling."""
    
    def __init__(self, x: float, y: float, biome: str = "road", variant: int = 1, scale: float = 1.0, is_solid: bool = False, is_hazard: bool = False, is_foreground: bool = False):
        self.x = x
        self.y = y
        self.biome = biome
        self.variant = max(1, min(5, variant))
        self.scale = scale
        self.is_solid = is_solid
        self.is_hazard = is_hazard or (biome == "stalagmite")
        self.is_foreground = is_foreground
        
        self.image = self._get_cached_surface(self.biome, self.variant, self.scale)
        self.rect = self.image.get_rect(midbottom=(int(x), int(y)))
        
        # Solid collision box (slightly tighter than visual bounding box)
        self.collision_rect = pygame.Rect(
            self.rect.left + 4,
            self.rect.top + 6,
            max(4, self.rect.width - 8),
            max(4, self.rect.height - 6)
        )
        
    @staticmethod
    def _get_cached_surface(biome: str, variant: int, scale: float) -> pygame.Surface:
        cache_key = (biome, variant, round(scale, 2))
        if cache_key in _ROCK_CACHE:
            return _ROCK_CACHE[cache_key]
            
        folder_name = BIOME_FOLDER_MAP.get(biome, "middle_lane_rocks1")
        base_dir = os.path.join("assets", "sprites", "rocks", "PNG", folder_name)
        
        # Determine filename pattern
        prefix_map = {
            "canyon_rocks": f"canyon_rock{variant}.png",
            "cave_rocks": f"cave_rock{variant}.png",
            "desert_rocks": f"desert_rock{variant}.png",
            "ice_rock": f"ice_rock{variant}.png",
            "middle_lane_rocks1": f"middle_lane_rock1_{variant}.png",
            "middle_lane_rocks2": f"middle_lane_rock2_{variant}.png",
            "snowy_rocks1": f"snowy_rock{variant}.png",
            "stalagmites": f"stalagmite{variant}.png",
        }
        filename = prefix_map.get(folder_name, f"middle_lane_rock1_{variant}.png")
        full_path = os.path.join(base_dir, filename)
        
        surf = None
        if os.path.exists(full_path):
            try:
                raw = pygame.image.load(full_path).convert_alpha()
                if scale != 1.0:
                    nw = max(8, int(raw.get_width() * scale))
                    nh = max(8, int(raw.get_height() * scale))
                    surf = pygame.transform.smoothscale(raw, (nw, nh))
                else:
                    surf = raw
            except Exception:
                pass
                
        if surf is None:
            # Fallback procedural rock
            rw, rh = int(32 * scale), int(24 * scale)
            surf = pygame.Surface((rw, rh), pygame.SRCALPHA)
            pygame.draw.ellipse(surf, (110, 105, 120), (0, 0, rw, rh))
            pygame.draw.ellipse(surf, (80, 75, 90), (2, 2, rw - 4, rh - 4))
            
        _ROCK_CACHE[cache_key] = surf
        return surf

    def update(self, dt: float, player=None):
        """Check hazard damage if player steps on sharp stalagmite."""
        if self.is_hazard and player and not getattr(player, "is_dead", False):
            if self.collision_rect.colliderect(player.rect):
                if hasattr(player, "take_damage"):
                    player.take_damage(12, knockback=(2.0 if player.rect.centerx > self.rect.centerx else -2.0, -3.0))

    def draw(self, surface: pygame.Surface, cam_offset: tuple):
        """Draws rock with camera offset and strict frustum culling."""
        cam_x, cam_y = cam_offset
        sw, sh = surface.get_size()
        
        # Frustum culling check
        if self.rect.right - cam_x >= 0 and self.rect.left - cam_x <= sw:
            if self.rect.bottom - cam_y >= 0 and self.rect.top - cam_y <= sh:
                surface.blit(self.image, (self.rect.x - cam_x, self.rect.y - cam_y))
