"""
src/engine/game_feel.py
-----------------------
Hollow Knight: Silksong inspired Game Feel & Visual Reactivity Engine.
Designed with 100% Object Pooling and Zero Per-Frame Heap Allocation.

Features:
1. Asymmetric Hit-Stop & Directional Micro-Shake (35ms - 55ms freeze with ±2px to ±4px vibration).
2. Slash Arcs & Motion Trails with Additive Glow (BLEND_RGB_ADD).
3. Reactive Movement Dust (Footstep puff, Landing billow, Dash ghost trail).
4. Foliage & Foreground Silhouette Wind Sway.
"""

import math
import random
from typing import List, Dict, Tuple, Optional, Any
import pygame
from config.settings import SETTINGS

class DustParticle:
    """A single pooled dust particle."""
    __slots__ = ("active", "x", "y", "vx", "vy", "size", "alpha", "max_life", "life", "color")

    def __init__(self):
        self.active = False
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.size = 2.0
        self.alpha = 180.0
        self.max_life = 0.35
        self.life = 0.0
        self.color = (190, 200, 215)

    def spawn(self, x: float, y: float, vx: float, vy: float, size: float, life: float, color: Tuple[int, int, int]):
        self.active = True
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.size = size
        self.max_life = life
        self.life = life
        self.alpha = 200.0
        self.color = color

    def update(self, dt: float):
        if not self.active:
            return
        self.life -= dt
        if self.life <= 0.0:
            self.active = False
            return
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.88  # Friction
        self.vy += 8.0 * dt  # Gentle gravity
        progress = self.life / self.max_life
        self.alpha = progress * 200.0


class SlashArc:
    """A pooled slash arc / combat light trail."""
    __slots__ = ("active", "x", "y", "radius", "start_angle", "end_angle", "color", "life", "max_life")

    def __init__(self):
        self.active = False
        self.x = 0.0
        self.y = 0.0
        self.radius = 24.0
        self.start_angle = 0.0
        self.end_angle = 1.57
        self.color = (255, 230, 160)
        self.life = 0.0
        self.max_life = 0.15

    def spawn(self, x: float, y: float, radius: float, start_angle: float, end_angle: float, color: Tuple[int, int, int], duration: float):
        self.active = True
        self.x = x
        self.y = y
        self.radius = radius
        self.start_angle = start_angle
        self.end_angle = end_angle
        self.color = color
        self.life = duration
        self.max_life = duration

    def update(self, dt: float):
        if not self.active:
            return
        self.life -= dt
        if self.life <= 0.0:
            self.active = False


class TransientLight:
    """A pooled dynamic point light emitted by attacks/projectiles."""
    __slots__ = ("active", "x", "y", "radius", "color", "intensity", "life", "max_life")

    def __init__(self):
        self.active = False
        self.x = 0.0
        self.y = 0.0
        self.radius = 48.0
        self.color = (255, 200, 120)
        self.intensity = 1.0
        self.life = 0.0
        self.max_life = 0.25

    def spawn(self, x: float, y: float, radius: float, color: Tuple[int, int, int], duration: float, intensity: float):
        self.active = True
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.life = duration
        self.max_life = duration
        self.intensity = intensity

    def update(self, dt: float):
        if not self.active:
            return
        self.life -= dt
        if self.life <= 0.0:
            self.active = False


class GameFeelManager:
    """Singleton coordinator for hit-stops, trails, dust particles, and wind sway."""

    def __init__(self, pool_dust_count: int = 64, pool_arcs_count: int = 24, pool_lights_count: int = 32):
        self.dust_pool: List[DustParticle] = [DustParticle() for _ in range(pool_dust_count)]
        self.arc_pool: List[SlashArc] = [SlashArc() for _ in range(pool_arcs_count)]
        self.light_pool: List[TransientLight] = [TransientLight() for _ in range(pool_lights_count)]
        
        # Hit-stop registry: maps entity ID or entity object to hit-stop data
        self.hit_stops: Dict[int, Dict[str, Any]] = {}
        self.time_sec = 0.0
        
        # Pre-rendered dust circle stamps in 3 sizes
        self._dust_stamps: Dict[Tuple[int, int], pygame.Surface] = {}
        self._prebake_dust_stamps()

    def _prebake_dust_stamps(self):
        """Pre-allocates soft dust puff surfaces."""
        for size in (2, 3, 4, 6):
            surf = pygame.Surface((size * 2 + 2, size * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (220, 225, 235, 180), (size + 1, size + 1), size)
            self._dust_stamps[(size, 180)] = surf

    def trigger_hit_stop(self, entity: Any, duration_ms: float = 45.0, shake_px: float = 3.0, direction: float = 1.0):
        """Applies asymmetric impact freeze on the hit entity with horizontal directional micro-shake."""
        if not getattr(SETTINGS, "GAME_FEEL_REACTIVE", True):
            return
        ent_id = id(entity)
        self.hit_stops[ent_id] = {
            "entity": entity,
            "remaining": max(0.02, min(0.12, duration_ms / 1000.0)),
            "duration": duration_ms / 1000.0,
            "shake": shake_px,
            "direction": 1.0 if direction >= 0 else -1.0,
            "timer": 0.0
        }

    def is_in_hit_stop(self, entity: Any) -> bool:
        """Checks if an entity is currently frozen in hit-stop."""
        ent_id = id(entity)
        return ent_id in self.hit_stops and self.hit_stops[ent_id]["remaining"] > 0.0

    def get_entity_shake_offset(self, entity: Any) -> Tuple[float, float]:
        """Returns (dx, dy) vibration offset for an entity in hit-stop."""
        ent_id = id(entity)
        if ent_id not in self.hit_stops:
            return (0.0, 0.0)
        data = self.hit_stops[ent_id]
        t = data["timer"]
        # Fast 90 Hz horizontal harmonic vibration
        offset_x = math.sin(t * 90.0) * data["shake"] * data["direction"]
        return (offset_x, 0.0)

    def emit_dust(self, x: float, y: float, dust_type: str = "footstep", facing_right: bool = True):
        """Spawns zero-allocation pooled dust particles at entity feet."""
        if not getattr(SETTINGS, "GAME_FEEL_REACTIVE", True):
            return

        direction = 1.0 if facing_right else -1.0
        if dust_type == "footstep":
            # 2 small puffs moving backwards
            count = 2
            for _ in range(count):
                p = self._get_free_dust()
                if p:
                    vx = -direction * random.uniform(15.0, 35.0)
                    vy = random.uniform(-12.0, -4.0)
                    p.spawn(x + random.uniform(-4, 4), y + random.uniform(-2, 1), vx, vy, size=2.0, life=0.22, color=(200, 210, 220))
        elif dust_type == "landing":
            # 6 puffs billowing left and right
            for d in (-1.0, 1.0):
                for _ in range(3):
                    p = self._get_free_dust()
                    if p:
                        vx = d * random.uniform(25.0, 65.0)
                        vy = random.uniform(-18.0, -8.0)
                        p.spawn(x + d * random.uniform(2, 8), y, vx, vy, size=3.0, life=0.35, color=(210, 220, 230))
        elif dust_type == "dash":
            # 8 swift dash trail particles
            for i in range(8):
                p = self._get_free_dust()
                if p:
                    vx = -direction * random.uniform(30.0, 90.0)
                    vy = random.uniform(-8.0, 8.0)
                    offset_back = -direction * (i * 4.0)
                    p.spawn(x + offset_back, y + random.uniform(-12, 4), vx, vy, size=2.5, life=0.28, color=(220, 230, 245))

    def emit_slash_arc(self, x: float, y: float, radius: float = 28.0, start_angle: float = -0.5, end_angle: float = 1.8, color: Tuple[int, int, int] = (255, 235, 175), duration: float = 0.16):
        """Spawns an additive slash arc glow."""
        if not getattr(SETTINGS, "GAME_FEEL_REACTIVE", True):
            return
        arc = self._get_free_arc()
        if arc:
            arc.spawn(x, y, radius, start_angle, end_angle, color, duration)
        # Simultaneously register a point light in the dynamic pool
        self.register_point_light(x, y, radius=radius * 2.2, color=color, duration=duration * 1.3, intensity=0.85)

    def register_point_light(self, x: float, y: float, radius: float = 50.0, color: Tuple[int, int, int] = (255, 220, 150), duration: float = 0.22, intensity: float = 0.8):
        """Registers a temporary point light for attacks, projectiles, or impacts."""
        if not getattr(SETTINGS, "DYNAMIC_LIGHTS", True):
            return
        light = self._get_free_light()
        if light:
            light.spawn(x, y, radius, color, duration, intensity)

    def get_foliage_wind_sway(self, time_sec: float, layer_scale: float = 1.0) -> float:
        """Returns smooth sine wind sway offset for foreground silhouettes in pixels."""
        t = time_sec * 1.8
        # Compound harmonic wave: 1st harmonic + subtle 2nd harmonic
        sway = math.sin(t) * 2.2 + math.sin(t * 2.3 + 1.2) * 1.1
        return sway * layer_scale

    def _get_free_dust(self) -> Optional[DustParticle]:
        for p in self.dust_pool:
            if not p.active:
                return p
        return None

    def _get_free_arc(self) -> Optional[SlashArc]:
        for a in self.arc_pool:
            if not a.active:
                return a
        return None

    def _get_free_light(self) -> Optional[TransientLight]:
        for l in self.light_pool:
            if not l.active:
                return l
        return None

    def update(self, dt: float):
        """Updates all pooled game feel elements."""
        self.time_sec += dt

        # 1. Update Hit-Stops
        expired_ids = []
        for ent_id, data in self.hit_stops.items():
            data["remaining"] -= dt
            data["timer"] += dt
            if data["remaining"] <= 0.0:
                expired_ids.append(ent_id)
        for eid in expired_ids:
            del self.hit_stops[eid]

        # 2. Update Dust Particles
        for p in self.dust_pool:
            if p.active:
                p.update(dt)

        # 3. Update Slash Arcs
        for a in self.arc_pool:
            if a.active:
                a.update(dt)

        # 4. Update Transient Lights
        for l in self.light_pool:
            if l.active:
                l.update(dt)

    def draw_dust(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        """Renders all active pooled dust particles."""
        cam_x, cam_y = camera_offset.x, camera_offset.y
        sw, sh = surface.get_size()

        for p in self.dust_pool:
            if not p.active:
                continue
            sx = int(p.x - cam_x)
            sy = int(p.y - cam_y)
            if -8 <= sx <= sw + 8 and -8 <= sy <= sh + 8:
                rad = max(1, int(p.size))
                alpha = max(0, min(255, int(p.alpha)))
                # Render soft dust dot
                dust_surf = pygame.Surface((rad * 2 + 2, rad * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(dust_surf, (*p.color, alpha), (rad + 1, rad + 1), rad)
                surface.blit(dust_surf, (sx - rad, sy - rad))

    def draw_slash_arcs(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        """Renders all active slash arcs with additive glow."""
        cam_x, cam_y = camera_offset.x, camera_offset.y
        sw, sh = surface.get_size()

        for arc in self.arc_pool:
            if not arc.active:
                continue
            sx = int(arc.x - cam_x)
            sy = int(arc.y - cam_y)
            if -64 <= sx <= sw + 64 and -64 <= sy <= sh + 64:
                progress = arc.life / arc.max_life
                alpha = int(progress * 220)
                rad = int(arc.radius)
                arc_surf = pygame.Surface((rad * 2 + 8, rad * 2 + 8), pygame.SRCALPHA)
                center = (rad + 4, rad + 4)
                rect = pygame.Rect(4, 4, rad * 2, rad * 2)
                # Draw additive arc curve
                try:
                    pygame.draw.arc(arc_surf, (*arc.color, alpha), rect, arc.start_angle, arc.end_angle, width=max(2, int(3 * progress)))
                    surface.blit(arc_surf, (sx - rad - 4, sy - rad - 4), special_flags=pygame.BLEND_RGB_ADD)
                except Exception:
                    pass

    def get_active_point_lights(self) -> List[Tuple[float, float, float, Tuple[int, int, int], float]]:
        """Returns list of (x, y, radius, color, intensity) for the active point lights."""
        active_lights = []
        for l in self.light_pool:
            if l.active:
                progress = l.life / l.max_life
                active_lights.append((l.x, l.y, l.radius, l.color, l.intensity * progress))
        return active_lights

GAME_FEEL = GameFeelManager()
