"""
========================================================================================
ULTIMATE AoE VFX SYSTEM - HIGH-DPI HD-2D PROCEDURAL VISUAL EFFECTS ENGINE
========================================================================================
Polymorphic, modular, and high-performance visual effects system for Hero Ultimate
AoE abilities (triggered by key [E]) in Ruin Runner.

Features:
- Pure Python and Pygame (pygame-ce compatible)
- Sub-Pixel rendering with Additive Blending (pygame.BLEND_RGBA_ADD)
- Procedural particle systems with realistic physics (drag, gravity, turbulence)
- Full suite of mathematical easing curves (ease_out_expo, ease_out_back, etc.)
- Stylized Anime Impact Frames (high-contrast monochrome flashes, time pauses)
- Safe numerical clamping via clamp_color() on all color tuples and channels
- Distinct visual designs and custom geometry for all 7 character archetypes:
    1. Ignis   (Fire)           : Massive Volcanic Eruption & Ballistic Cinders
    2. Lunaria (Water/Arcane)   : Gravitational Singularity & Cosmic Shockwave
    3. Astra   (Ice)            : Sharp Jagged Shard Blizzard & Permafrost
    4. Ryuu    (Ki/Fighter)     : Golden Martial Ki Domain & Ascending Shock Rings
    5. Samurai (Wind)           : Dimensional Judgement Cut & Reality Shatter
    6. Shinobi (Shadow)         : Shadow Shroud & High-Speed Phantom Clone Blitz
    7. Shaia   (Light/Sacred)   : Divine Orbital Laser Rain & Holy Ground Seal
========================================================================================
"""

import pygame
import math
import random
from collections import deque
from typing import List, Tuple, Dict, Optional, Any


# ========================================================================================
# 1. CORE MATH, EASING & COLOR UTILITIES
# ========================================================================================

def clamp(val: float, min_val: float, max_val: float) -> float:
    """Clamps a floating point value between min_val and max_val."""
    return max(min_val, min(val, max_val))


def clamp_color(color: Tuple[float, ...]) -> Tuple[int, ...]:
    """
    Mandatory safety helper ensuring all color channels (RGB or RGBA) stay strictly
    within the valid [0, 255] integer range to prevent Pygame ValueError crashes.
    """
    return tuple(max(0, min(255, int(round(c)))) for c in color)


def lerp(a: float, b: float, t: float) -> float:
    """Standard linear interpolation between scalar values a and b."""
    return a + (b - a) * clamp(t, 0.0, 1.0)


def lerp_color(c1: Tuple[float, ...], c2: Tuple[float, ...], t: float) -> Tuple[int, ...]:
    """Linearly interpolates between two RGB or RGBA color tuples with strict clamping."""
    t_clamped = clamp(t, 0.0, 1.0)
    min_len = min(len(c1), len(c2))
    res = [c1[i] + (c2[i] - c1[i]) * t_clamped for i in range(min_len)]
    return clamp_color(tuple(res))


def ease_out_expo(t: float) -> float:
    """Exponential deceleration: explosive snap with long, smooth tail."""
    t = clamp(t, 0.0, 1.0)
    return 1.0 if t >= 1.0 else 1.0 - (2.0 ** (-10.0 * t))


def ease_in_expo(t: float) -> float:
    """Exponential acceleration: slow windup accelerating to near-infinite speed."""
    t = clamp(t, 0.0, 1.0)
    return 0.0 if t <= 0.0 else 2.0 ** (10.0 * (t - 1.0))


def ease_out_back(t: float, s: float = 1.70158) -> float:
    """Overshooting expansion that snaps beyond 1.0 before settling back."""
    t = clamp(t, 0.0, 1.0) - 1.0
    return 1.0 + (s + 1.0) * (t ** 3) + s * (t ** 2)


def ease_in_back(t: float, s: float = 1.70158) -> float:
    """Anticipation recoil pulling backward before lunging forward."""
    t = clamp(t, 0.0, 1.0)
    return (s + 1.0) * (t ** 3) - s * (t ** 2)


def ease_out_quad(t: float) -> float:
    """Quadratic deceleration."""
    t = clamp(t, 0.0, 1.0)
    return 1.0 - (1.0 - t) * (1.0 - t)


def ease_in_quad(t: float) -> float:
    """Quadratic acceleration."""
    t = clamp(t, 0.0, 1.0)
    return t * t


def ease_in_out_quad(t: float) -> float:
    """Smooth S-curve acceleration and deceleration."""
    t = clamp(t, 0.0, 1.0)
    return 2.0 * t * t if t < 0.5 else 1.0 - ((-2.0 * t + 2.0) ** 2) / 2.0


def ease_out_elastic(t: float) -> float:
    """Damped harmonic oscillation / elastic ring-out."""
    t = clamp(t, 0.0, 1.0)
    if t == 0.0: return 0.0
    if t == 1.0: return 1.0
    c4 = (2.0 * math.pi) / 3.0
    return (2.0 ** (-10.0 * t)) * math.sin((t * 10.0 - 0.75) * c4) + 1.0


# ========================================================================================
# 2. LIGHTWEIGHT HIGH-PERFORMANCE PROCEDURAL PARTICLES
# ========================================================================================

class BaseVFXParticle:
    """Abstract base for procedural particles with custom physics and lifespans."""
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "active")
    
    def __init__(self, x: float, y: float, vx: float, vy: float, life: float):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.life = float(life)
        self.max_life = float(life)
        self.active = True

    def update(self, dt: float) -> bool:
        self.life -= dt
        if self.life <= 0:
            self.active = False
        return self.active

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        pass


class VolcanicCinder(BaseVFXParticle):
    """Ballistic heavy spark ejected by Ignis eruption with gravity, drag and trail."""
    __slots__ = ("trail", "size", "color_core", "color_glow", "gravity")

    def __init__(self, x: float, y: float, vx: float, vy: float, life: float):
        super().__init__(x, y, vx, vy, life)
        self.trail = deque(maxlen=4)
        self.size = random.uniform(2.0, 4.5)
        self.color_core = (255, 255, 220)
        self.color_glow = (255, random.randint(80, 160), 20)
        self.gravity = random.uniform(480.0, 620.0)

    def update(self, dt: float) -> bool:
        if not super().update(dt):
            return False
        self.trail.appendleft((self.x, self.y))
        self.vx *= (1.0 - 0.25 * dt)
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        return True

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        if not self.active or self.life <= 0: return
        t = self.life / self.max_life
        alpha = int(255 * ease_out_quad(t))
        if alpha <= 0: return
        
        px, py = int(self.x - cam_x), int(self.y - cam_y)
        
        # Draw trailing embers
        if len(self.trail) > 1:
            for i, (tx, ty) in enumerate(self.trail):
                trail_alpha = int(alpha * (1.0 - (i / len(self.trail))) * 0.6)
                if trail_alpha > 5:
                    tcx, tcy = int(tx - cam_x), int(ty - cam_y)
                    pygame.draw.line(surface, clamp_color((*self.color_glow[:3], trail_alpha)), 
                                     (px, py), (tcx, tcy), max(1, int(self.size * 0.7)))
                    
        # Glowing head
        pygame.draw.circle(surface, clamp_color((*self.color_glow[:3], int(alpha * 0.8))), (px, py), int(self.size + 1))
        pygame.draw.circle(surface, clamp_color((*self.color_core[:3], alpha)), (px, py), max(1, int(self.size * 0.5)))


class VolcanicSmokePuff(BaseVFXParticle):
    """Dense billowing smoke puff that ascends, decelerates, expands and fades."""
    __slots__ = ("radius", "max_radius", "rot_angle", "rot_speed", "shade")

    def __init__(self, x: float, y: float, vx: float, vy: float, life: float):
        super().__init__(x, y, vx, vy, life)
        self.radius = random.uniform(8.0, 16.0)
        self.max_radius = random.uniform(32.0, 56.0)
        self.rot_angle = random.uniform(0.0, math.tau)
        self.rot_speed = random.uniform(-1.5, 1.5)
        self.shade = random.randint(25, 55)

    def update(self, dt: float) -> bool:
        if not super().update(dt):
            return False
        self.vx *= (1.0 - 0.8 * dt)
        self.vy *= (1.0 - 0.4 * dt)
        self.vy -= 45.0 * dt  # Buoyant lift
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.rot_angle += self.rot_speed * dt
        progress = 1.0 - (self.life / self.max_life)
        self.radius = lerp(self.radius, self.max_radius, ease_out_quad(progress))
        return True

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        if not self.active or self.life <= 0: return
        t = self.life / self.max_life
        alpha = int(140 * math.sin(t * math.pi))
        if alpha <= 0: return
        
        px, py = int(self.x - cam_x), int(self.y - cam_y)
        r = int(self.radius)
        if r <= 0: return
        
        color = (self.shade + 15, self.shade + 5, self.shade, alpha)
        pygame.draw.circle(surface, clamp_color(color), (px, py), r)


class SingularityMote(BaseVFXParticle):
    """Stardust mote pulled towards Lunaria's singularity with inverse square acceleration."""
    __slots__ = ("origin_x", "origin_y", "angle", "distance", "inward_speed", "color", "size")

    def __init__(self, cx: float, cy: float, distance: float, angle: float, life: float):
        super().__init__(cx + math.cos(angle) * distance, cy + math.sin(angle) * distance, 0, 0, life)
        self.origin_x = cx
        self.origin_y = cy
        self.distance = distance
        self.angle = angle
        self.inward_speed = random.uniform(220.0, 420.0)
        self.size = random.uniform(1.8, 3.8)
        self.color = random.choice([
            (140, 220, 255),
            (200, 160, 255),
            (255, 255, 255),
            (90, 180, 255)
        ])

    def update_vortex(self, dt: float, center_x: float, center_y: float) -> bool:
        if not super().update(dt):
            return False
        self.origin_x = center_x
        self.origin_y = center_y
        
        # Accelerate inward with logarithmic spiral
        pull_factor = 1.0 + (1.0 - clamp(self.distance / 180.0, 0.0, 1.0)) * 2.5
        self.distance -= self.inward_speed * pull_factor * dt
        self.angle += (3.5 + pull_factor * 4.0) * dt
        
        self.x = self.origin_x + math.cos(self.angle) * max(0.0, self.distance)
        self.y = self.origin_y + math.sin(self.angle) * max(0.0, self.distance)
        
        if self.distance <= 4.0:
            self.active = False
        return self.active

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        if not self.active: return
        px, py = int(self.x - cam_x), int(self.y - cam_y)
        t = clamp(self.life / self.max_life, 0.0, 1.0)
        alpha = int(255 * ease_out_expo(t))
        sz = max(1, int(self.size))
        
        # Cross spark rendering
        pygame.draw.line(surface, clamp_color((*self.color[:3], alpha)), (px - sz * 2, py), (px + sz * 2, py), 1)
        pygame.draw.line(surface, clamp_color((*self.color[:3], alpha)), (px, py - sz * 2), (px, py + sz * 2), 1)
        pygame.draw.circle(surface, clamp_color((255, 255, 255, alpha)), (px, py), max(1, sz - 1))


class DiamondDustParticle(BaseVFXParticle):
    """Floating glacial diamond dust mote for Astra's blizzard."""
    __slots__ = ("size", "color", "rot", "rot_spd", "sway_freq", "sway_amp")

    def __init__(self, x: float, y: float, vx: float, vy: float, life: float):
        super().__init__(x, y, vx, vy, life)
        self.size = random.uniform(2.5, 6.0)
        self.color = random.choice([
            (210, 245, 255),
            (140, 220, 255),
            (255, 255, 255),
            (100, 190, 240)
        ])
        self.rot = random.uniform(0.0, math.tau)
        self.rot_spd = random.uniform(-6.0, 6.0)
        self.sway_freq = random.uniform(6.0, 12.0)
        self.sway_amp = random.uniform(20.0, 45.0)

    def update(self, dt: float) -> bool:
        if not super().update(dt):
            return False
        self.x += (self.vx + math.sin(self.life * self.sway_freq) * self.sway_amp) * dt
        self.y += self.vy * dt
        self.rot += self.rot_spd * dt
        return True

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        if not self.active or self.life <= 0: return
        px, py = self.x - cam_x, self.y - cam_y
        t = self.life / self.max_life
        alpha = int(255 * math.sin(t * math.pi))
        if alpha <= 0: return
        
        pts = []
        for i in range(4):
            ang = self.rot + i * (math.pi / 2)
            dist = self.size if (i % 2 == 0) else self.size * 0.45
            pts.append((px + math.cos(ang) * dist, py + math.sin(ang) * dist))
            
        pygame.draw.polygon(surface, clamp_color((*self.color[:3], alpha)), pts)
        pygame.draw.polygon(surface, clamp_color((255, 255, 255, alpha)), pts, 1)


# ========================================================================================
# 3. BASE ULTIMATE AoE VFX CLASS & POLYMORPHIC DISPATCHER
# ========================================================================================

_AOE_VFX_REGISTRY: Dict[str, type] = {}


class UltimateAoE_VFX:
    """
    Polymorphic base and factory for Hero Ultimate AoE Visual Effects.
    Instantiating UltimateAoE_VFX(x, y, radius, character_id) automatically returns
    the dedicated high-performance VFX subclass instance for that hero.
    
    Standard Interface:
        vfx = UltimateAoE_VFX(x, y, radius, character_id)
        vfx.update(dt)
        vfx.draw(surface, camera_offset)
    """
    def __new__(cls, x: float, y: float, radius: float, character_id: str = "shaia"):
        if cls is not UltimateAoE_VFX:
            return super().__new__(cls)
            
        cid = str(character_id).lower()
        subclass = _AOE_VFX_REGISTRY.get(cid, ShaiaDivineJudgementVFX)
        return super().__new__(subclass)

    def __init__(self, x: float, y: float, radius: float, character_id: str):
        self.x = float(x)
        self.y = float(y)
        self.radius = float(radius)
        self.character_id = str(character_id).lower()
        self.time = 0.0
        self.duration = 0.8
        self.active = True
        self.impact_flash = 0.0
        
    def update(self, dt: float):
        """Advances elapsed time and checks active status."""
        self.time += dt
        if self.impact_flash > 0:
            self.impact_flash = max(0.0, self.impact_flash - dt)
        if self.time >= self.duration:
            self.active = False

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        """Must be overridden by concrete character archetype implementations."""
        raise NotImplementedError("Subclasses must implement bespoke draw logic.")

    def _get_local_bounds(self, padding: int = 40) -> Tuple[int, int, int, int]:
        """Calculates square/rectangular bounding box dimensions for scratch surfaces."""
        dim = int((self.radius + padding) * 2)
        half = dim // 2
        return dim, dim, half, half


# Alias for explicit base type inheritance
BaseUltimateAoE_VFX = UltimateAoE_VFX


# ========================================================================================
# 4. ARCHETYPE 1: IGNIS (FIRE) - VOLCANIC ERUPTION
# ========================================================================================

class IgnisVolcanicEruptionVFX(BaseUltimateAoE_VFX):
    """
    Ignis: Erupção Vulcânica.
    Replaces generic circular blast with a towering vertical pillar of white-hot magma
    erupting from tectonic fissures on the ground, ejecting ballistic sparks and dense smoke.
    """
    def __init__(self, x: float, y: float, radius: float, character_id: str):
        super().__init__(x, y, radius, character_id)
        self.duration = 0.90
        self.cinders: List[VolcanicCinder] = []
        self.smoke_puffs: List[VolcanicSmokePuff] = []
        self.fissure_points: List[Tuple[float, float]] = []
        
        # Pre-generate ground fissure fracture lines
        num_cracks = 16
        span = self.radius * 0.95
        for i in range(num_cracks):
            fx = self.x + random.uniform(-span, span)
            fy = self.y + random.uniform(-8.0, 10.0)
            self.fissure_points.append((fx, fy))
            
        # Spawn initial wave of dense smoke and ballistic cinders
        for _ in range(40):
            vx = random.uniform(-280.0, 280.0)
            vy = random.uniform(-520.0, -180.0)
            life = random.uniform(0.45, 0.85)
            self.cinders.append(VolcanicCinder(self.x + random.uniform(-25, 25), self.y, vx, vy, life))

        for _ in range(25):
            vx = random.uniform(-140.0, 140.0)
            vy = random.uniform(-260.0, -90.0)
            life = random.uniform(0.5, 0.88)
            self.smoke_puffs.append(VolcanicSmokePuff(self.x + random.uniform(-40, 40), self.y, vx, vy, life))

    def update(self, dt: float):
        super().update(dt)
        if not self.active: return
        
        # Progressive cinder emission during the roaring eruption peak
        if 0.08 <= self.time <= 0.45 and random.random() < 0.65:
            vx = random.uniform(-320.0, 320.0)
            vy = random.uniform(-560.0, -220.0)
            self.cinders.append(VolcanicCinder(self.x + random.uniform(-20, 20), self.y - 10, vx, vy, random.uniform(0.4, 0.7)))

        # Update cinders
        self.cinders = [c for c in self.cinders if c.update(dt)]
        # Update smoke
        self.smoke_puffs = [s for s in self.smoke_puffs if s.update(dt)]

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if not self.active: return
        cam_x, cam_y = camera_offset.x, camera_offset.y
        cx, cy = int(self.x - cam_x), int(self.y - cam_y)
        progress = clamp(self.time / self.duration, 0.0, 1.0)
        
        # 1. Draw expanding billowing background smoke
        for s in self.smoke_puffs:
            s.draw(surface, cam_x, cam_y)
            
        # 2. Render Molten Ground Fissures
        fissure_alpha = int(255 * math.sin(progress * math.pi))
        if fissure_alpha > 0:
            for fx, fy in self.fissure_points:
                gpx, gpy = int(fx - cam_x), int(fy - cam_y)
                # Outer fiery glow
                pygame.draw.circle(surface, clamp_color((220, 70, 0, int(fissure_alpha * 0.5))), (gpx, gpy), random.randint(6, 12))
                # Molten white-hot seam
                pygame.draw.line(surface, clamp_color((255, 240, 140, fissure_alpha)), (cx, cy), (gpx, gpy), max(1, random.randint(2, 4)))

        # 3. Vertical Roaring Magma Pillar Mesh
        # Height and width curves driven by anime easing
        pillar_height_max = self.radius * 2.5
        if progress < 0.25:
            growth = ease_out_expo(progress / 0.25)
            alpha = int(255 * growth)
        elif progress < 0.70:
            growth = 1.0
            alpha = 255
        else:
            decay_prog = (progress - 0.70) / 0.30
            growth = 1.0 - ease_in_quad(decay_prog)
            alpha = int(255 * (1.0 - decay_prog))
            
        cur_height = pillar_height_max * growth
        base_width = (self.radius * 0.75) * (1.0 - progress * 0.4)
        
        if cur_height > 10 and alpha > 0:
            pillar_surf = pygame.Surface((int(base_width * 2 + 60), int(cur_height + 40)), pygame.SRCALPHA)
            pcx = pillar_surf.get_width() // 2
            p_bottom = pillar_surf.get_height() - 10
            
            # Procedural wavy polygon points for turbulent flame contours
            segments = 20
            outer_pts_left = []
            outer_pts_right = []
            core_pts_left = []
            core_pts_right = []
            
            for seg in range(segments + 1):
                sy = p_bottom - (cur_height / segments) * seg
                h_ratio = seg / segments
                taper = 1.0 - (h_ratio ** 1.3) * 0.65
                w = (base_width * taper) + math.sin(seg * 0.8 + self.time * 24.0) * 14.0
                core_w = w * 0.45
                
                outer_pts_left.append((pcx - w, sy))
                outer_pts_right.append((pcx + w, sy))
                core_pts_left.append((pcx - core_w, sy))
                core_pts_right.append((pcx + core_w, sy))
                
            outer_poly = outer_pts_left + list(reversed(outer_pts_right))
            core_poly = core_pts_left + list(reversed(core_pts_right))
            
            # Layer 1: Crimson Plasma Corona
            pygame.draw.polygon(pillar_surf, clamp_color((230, 45, 0, int(alpha * 0.65))), outer_poly)
            # Layer 2: Radiant Blazing Fire
            pygame.draw.polygon(pillar_surf, clamp_color((255, 140, 20, int(alpha * 0.85))), outer_poly, max(2, int(12 * growth)))
            # Layer 3: White-Hot Incandescent Core
            if len(core_poly) >= 3:
                pygame.draw.polygon(pillar_surf, clamp_color((255, 255, 220, alpha)), core_poly)
                
            surface.blit(pillar_surf, (cx - pcx, cy - p_bottom), special_flags=pygame.BLEND_RGBA_ADD)

        # 4. Ballistic Heavy Cinders (Drawn over pillar)
        for c in self.cinders:
            c.draw(surface, cam_x, cam_y)

        # 5. Anime Impact Frame Flash at eruption apex
        if progress < 0.12:
            flash_alpha = int(255 * (1.0 - (progress / 0.12)))
            pygame.draw.line(surface, clamp_color((255, 255, 255, flash_alpha)), (cx - 150, cy), (cx + 150, cy), 6)
            pygame.draw.line(surface, clamp_color((255, 200, 100, flash_alpha)), (cx, cy), (cx, cy - cur_height), 8)


# ========================================================================================
# 5. ARCHETYPE 2: LUNARIA (WATER/ARCANE) - SINGULARITY (BLACK HOLE)
# ========================================================================================

class LunariaSingularityVFX(BaseUltimateAoE_VFX):
    """
    Lunaria: Singularidade Cósmica.
    Creates a gravitational vortex that first sucks inward space-time, light lines, and
    stardust particles into a dense singularity, followed by an anime freeze and an
    expanding celestial gravitational shockwave.
    """
    def __init__(self, x: float, y: float, radius: float, character_id: str):
        super().__init__(x, y, radius, character_id)
        self.duration = 0.95
        self.implosion_duration = 0.45
        self.center_y = self.y - self.radius * 0.25
        self.motes: List[SingularityMote] = []
        
        # Pre-spawn stardust motes around perimeter
        for _ in range(55):
            dist = random.uniform(self.radius * 0.5, self.radius * 1.25)
            ang = random.uniform(0.0, math.tau)
            life = random.uniform(0.35, 0.75)
            self.motes.append(SingularityMote(self.x, self.center_y, dist, ang, life))

    def update(self, dt: float):
        super().update(dt)
        if not self.active: return
        
        # Inward spiral motes
        if self.time < self.implosion_duration and len(self.motes) < 70:
            if random.random() < 0.7:
                dist = random.uniform(self.radius * 0.8, self.radius * 1.3)
                ang = random.uniform(0.0, math.tau)
                self.motes.append(SingularityMote(self.x, self.center_y, dist, ang, 0.4))
                
        self.motes = [m for m in self.motes if m.update_vortex(dt, self.x, self.center_y)]

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if not self.active: return
        cam_x, cam_y = camera_offset.x, camera_offset.y
        cx, cy = int(self.x - cam_x), int(self.center_y - cam_y)
        
        # ==================== PHASE 1: IMPLOSION VORTEX ====================
        if self.time < self.implosion_duration:
            t_imp = self.time / self.implosion_duration
            inv_t = 1.0 - t_imp
            vortex_rad = int(self.radius * ease_out_expo(inv_t))
            
            # 1. Inward Light Inflow Filaments
            num_rays = 14
            for i in range(num_rays):
                ang = (i / num_rays) * math.tau + (t_imp * 6.0)
                outer_dist = self.radius * (0.8 + 0.3 * math.sin(i * 1.5))
                curr_dist = lerp(outer_dist, 4.0, ease_in_expo(t_imp))
                
                sx = cx + int(math.cos(ang) * curr_dist)
                sy = cy + int(math.sin(ang) * curr_dist)
                ray_alpha = int(220 * t_imp)
                pygame.draw.line(surface, clamp_color((130, 220, 255, ray_alpha)), (cx, cy), (sx, sy), 2)
                pygame.draw.circle(surface, clamp_color((255, 255, 255, ray_alpha)), (sx, sy), 3)

            # 2. Inward Spiraling Stardust
            for m in self.motes:
                m.draw(surface, cam_x, cam_y)

            # 3. Accretion Disk Spiral Arms
            if vortex_rad > 8:
                surf_dim = vortex_rad * 2 + 20
                v_surf = pygame.Surface((surf_dim, surf_dim), pygame.SRCALPHA)
                sc = surf_dim // 2
                
                for arm in range(3):
                    arm_offset = arm * (math.tau / 3.0)
                    spiral_pts = []
                    steps = 25
                    for s in range(steps):
                        frac = s / steps
                        r = vortex_rad * (1.0 - frac)
                        theta = arm_offset + frac * 4.5 + self.time * 12.0
                        spiral_pts.append((sc + math.cos(theta) * r, sc + math.sin(theta) * r))
                    if len(spiral_pts) > 1:
                        pygame.draw.lines(v_surf, clamp_color((180, 100, 255, int(200 * t_imp))), False, spiral_pts, 3)
                        pygame.draw.lines(v_surf, clamp_color((100, 240, 255, int(255 * t_imp))), False, spiral_pts, 1)
                        
                surface.blit(v_surf, (cx - sc, cy - sc), special_flags=pygame.BLEND_RGBA_ADD)

            # 4. Dense Event Horizon Core
            core_r = max(3, int(18 * inv_t))
            pygame.draw.circle(surface, clamp_color((10, 5, 25, 240)), (cx, cy), core_r)
            pygame.draw.circle(surface, clamp_color((180, 240, 255, 255)), (cx, cy), core_r, 2)
            pygame.draw.circle(surface, clamp_color((255, 255, 255, 255)), (cx, cy), max(1, core_r // 3))

        # ==================== PHASE 2: DETONATION SHOCKWAVE ====================
        else:
            t_det = (self.time - self.implosion_duration) / (self.duration - self.implosion_duration)
            t_det_clamped = clamp(t_det, 0.0, 1.0)
            
            wave_rad = int(self.radius * 1.25 * ease_out_expo(t_det_clamped))
            wave_alpha = int(255 * (1.0 - ease_in_quad(t_det_clamped)))
            
            if wave_rad > 4 and wave_alpha > 0:
                # Chromatic Aberration Wavefront (Double shock ring)
                # Outer cyan perimeter ring
                pygame.draw.circle(surface, clamp_color((80, 220, 255, wave_alpha)), (cx, cy), wave_rad, 5)
                # Inner astral violet wavefront
                inner_wave = max(1, wave_rad - 8)
                pygame.draw.circle(surface, clamp_color((210, 90, 255, int(wave_alpha * 0.85))), (cx, cy), inner_wave, 3)
                pygame.draw.circle(surface, clamp_color((255, 255, 255, wave_alpha)), (cx, cy), wave_rad, 2)

                # Radiating Cosmic Supernova Spikes
                num_spikes = 12
                for i in range(num_spikes):
                    ang = (i / num_spikes) * math.tau + t_det_clamped * 1.5
                    spike_len = wave_rad + int(35 * math.sin(i * 2.0))
                    ex = cx + int(math.cos(ang) * spike_len)
                    ey = cy + int(math.sin(ang) * spike_len)
                    pygame.draw.line(surface, clamp_color((220, 245, 255, int(wave_alpha * 0.75))), (cx, cy), (ex, ey), 2)
                    pygame.draw.circle(surface, clamp_color((255, 255, 255, wave_alpha)), (cx, cy), 3)

                # Lingering central nebula aura
                nebula_r = max(4, int(self.radius * 0.45 * (1.0 - t_det_clamped)))
                pygame.draw.circle(surface, clamp_color((140, 100, 255, int(wave_alpha * 0.4))), (cx, cy), nebula_r)
                pygame.draw.circle(surface, clamp_color((255, 255, 255, wave_alpha)), (cx, cy), max(2, nebula_r // 2))


# ========================================================================================
# 6. ARCHETYPE 3: ASTRA (ICE) - SHARD BLIZZARD
# ========================================================================================

class ShardSpikeData:
    """Individual geometric glacial spike sprouting violently from the frozen ground."""
    __slots__ = ("offset_x", "width", "target_height", "tilt_angle", "color_edge", "delay")

    def __init__(self, offset_x: float, max_height: float):
        self.offset_x = offset_x
        self.width = random.uniform(16.0, 32.0)
        self.target_height = max_height * random.uniform(0.65, 1.15)
        # Splay spikes outward naturally
        self.tilt_angle = (offset_x / 160.0) * 0.35 + random.uniform(-0.08, 0.08)
        self.delay = random.uniform(0.02, 0.16)
        self.color_edge = random.choice([
            (225, 250, 255),
            (175, 235, 255),
            (255, 255, 255)
        ])


class AstraShardBlizzardVFX(BaseUltimateAoE_VFX):
    """
    Astra: Tempestade de Estilhaços.
    Instead of a round explosion, ground freezes beneath her and dozens of faceted
    geometric ice shards aggressively sprout upwards, kicking up diamond dust gales.
    """
    def __init__(self, x: float, y: float, radius: float, character_id: str):
        super().__init__(x, y, radius, character_id)
        self.duration = 0.85
        self.shards: List[ShardSpikeData] = []
        self.diamond_dust: List[DiamondDustParticle] = []
        
        # Generate 20 geometric ice spikes across ground perimeter
        num_shards = 20
        span = self.radius * 0.92
        step = (span * 2) / num_shards
        for i in range(num_shards):
            ox = -span + i * step + random.uniform(-10, 10)
            dist_factor = 1.0 - abs(ox / span) * 0.4
            self.shards.append(ShardSpikeData(ox, self.radius * 1.35 * dist_factor))
            
        # Spawn initial diamond dust gale
        for _ in range(35):
            vx = random.uniform(-260.0, 260.0)
            vy = random.uniform(-240.0, -80.0)
            self.diamond_dust.append(DiamondDustParticle(self.x + random.uniform(-span, span), self.y, vx, vy, random.uniform(0.4, 0.8)))

    def update(self, dt: float):
        super().update(dt)
        if not self.active: return
        
        # Wind gusts during shard emergence
        if 0.15 <= self.time <= 0.55 and random.random() < 0.6:
            vx = random.uniform(-300.0, 300.0)
            vy = random.uniform(-180.0, -40.0)
            self.diamond_dust.append(DiamondDustParticle(self.x + random.uniform(-self.radius, self.radius), self.y - 30, vx, vy, 0.45))
            
        self.diamond_dust = [d for d in self.diamond_dust if d.update(dt)]

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if not self.active: return
        cam_x, cam_y = camera_offset.x, camera_offset.y
        cx, cy = int(self.x - cam_x), int(self.y - cam_y)
        progress = clamp(self.time / self.duration, 0.0, 1.0)
        
        # 1. Permafrost Ground Freezing Flash
        frost_alpha = int(255 * math.sin(progress * math.pi))
        if frost_alpha > 0:
            span = int(self.radius * 0.98)
            # Jagged crystalline frost shelf along the floor
            frost_pts = []
            for i in range(-span, span + 1, 14):
                f_height = random.randint(4, 12) if abs(i) < span * 0.8 else random.randint(2, 6)
                frost_pts.append((cx + i, cy - f_height))
            frost_pts.append((cx + span, cy + 6))
            frost_pts.append((cx - span, cy + 6))
            pygame.draw.polygon(surface, clamp_color((130, 220, 255, int(frost_alpha * 0.6))), frost_pts)
            pygame.draw.polygon(surface, clamp_color((255, 255, 255, frost_alpha)), frost_pts, 2)

        # 2. Geometric Sharp Glacial Shards (Faceted 3D Crystalline Look)
        for s in self.shards:
            shard_local_time = self.time - s.delay
            if shard_local_time <= 0: continue
            
            # Emergence animation driven by ease_out_back for aggressive pop
            sprout_t = clamp(shard_local_time / 0.28, 0.0, 1.0)
            h = s.target_height * ease_out_back(sprout_t, s=2.1)
            
            # Fade out towards the end
            if progress > 0.65:
                decay = (progress - 0.65) / 0.35
                h *= (1.0 - decay)
                alpha = int(255 * (1.0 - decay))
            else:
                alpha = 255
                
            if h <= 2 or alpha <= 0: continue
            
            sx = cx + s.offset_x
            sy = cy
            
            # Calculate 3D faceted crystal vertices
            tip_x = sx + math.sin(s.tilt_angle) * h
            tip_y = sy - math.cos(s.tilt_angle) * h
            
            half_w = s.width * 0.5
            perp_x = math.cos(s.tilt_angle) * half_w
            perp_y = math.sin(s.tilt_angle) * half_w
            
            left_base = (sx - perp_x, sy - perp_y)
            right_base = (sx + perp_x, sy + perp_y)
            mid_ridge = (sx + math.sin(s.tilt_angle) * h * 0.35, sy - math.cos(s.tilt_angle) * h * 0.35)
            
            facet_left = [left_base, (tip_x, tip_y), mid_ridge]
            facet_right = [right_base, (tip_x, tip_y), mid_ridge]
            
            # Facet Left: Lit cyan crystal face
            pygame.draw.polygon(surface, clamp_color((140, 225, 255, alpha)), facet_left)
            # Facet Right: Deep glacial teal shadow face
            pygame.draw.polygon(surface, clamp_color((60, 150, 220, alpha)), facet_right)
            
            # Specular Highlights along razor edges and ridge
            pygame.draw.polygon(surface, clamp_color((255, 255, 255, alpha)), [left_base, (tip_x, tip_y), right_base], 1)
            pygame.draw.line(surface, clamp_color((255, 255, 255, alpha)), (tip_x, tip_y), mid_ridge, 2)

        # 3. Diamond Dust Gales and Spinning Ice Crystals
        for d in self.diamond_dust:
            d.draw(surface, cam_x, cam_y)

        # 4. Horizontal Gale Wind Streaks
        if 0.15 <= progress <= 0.60:
            wind_alpha = int(180 * math.sin(((progress - 0.15) / 0.45) * math.pi))
            for i in range(5):
                wy = cy - int(self.radius * (0.2 + i * 0.2))
                wx_start = cx - int(self.radius * 0.9)
                wx_end = cx + int(self.radius * 0.9)
                pygame.draw.line(surface, clamp_color((220, 250, 255, wind_alpha)), (wx_start, wy), (wx_end, wy), 1)


# ========================================================================================
# 7. ARCHETYPE 4: RYUU / FIGHTER (KI) - FIGHTER'S DOMAIN
# ========================================================================================

class RyuuKiDomainVFX(BaseUltimateAoE_VFX):
    """
    Ryuu / Fighter: Domínio de Luta.
    Forms a static golden energy dome / hollow sphere enclosing the arena,
    cracking the ground into radiant tectonic fissures and sending shock rings
    ascending up the perimeter of the dome.
    """
    def __init__(self, x: float, y: float, radius: float, character_id: str):
        super().__init__(x, y, radius, character_id)
        self.duration = 0.88
        self.shock_rings: List[Dict[str, float]] = []
        self.ground_cracks: List[List[Tuple[float, float]]] = []
        
        # Pre-generate radial ground fracture lines
        num_fissures = 10
        for i in range(num_fissures):
            ang = math.pi + (i / num_fissures) * math.pi  # Along floor
            length = random.uniform(self.radius * 0.4, self.radius * 0.95)
            crack = [(self.x, self.y)]
            cur_x, cur_y = self.x, self.y
            steps = random.randint(4, 7)
            for s in range(steps):
                cur_x += math.cos(ang) * (length / steps) + random.uniform(-6, 6)
                cur_y += random.uniform(-4, 5)
                crack.append((cur_x, cur_y))
            self.ground_cracks.append(crack)

        # Schedule ascending shock rings that travel up the spherical dome
        self.shock_rings = [
            {"time_start": 0.10, "speed": 1.4},
            {"time_start": 0.25, "speed": 1.6},
            {"time_start": 0.40, "speed": 1.8}
        ]

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if not self.active: return
        cam_x, cam_y = camera_offset.x, camera_offset.y
        cx, cy = int(self.x - cam_x), int(self.y - cam_y)
        progress = clamp(self.time / self.duration, 0.0, 1.0)
        
        # 1. Radiant Tectonic Ground Fractures
        crack_alpha = int(255 * math.sin(progress * math.pi))
        if crack_alpha > 0:
            for crack in self.ground_cracks:
                pts = [(int(px - cam_x), int(py - cam_y)) for px, py in crack]
                # Golden magma underglow
                pygame.draw.lines(surface, clamp_color((255, 170, 20, int(crack_alpha * 0.6))), False, pts, 6)
                # Intense white-hot Ki vein
                pygame.draw.lines(surface, clamp_color((255, 255, 200, crack_alpha)), False, pts, 2)

        # 2. Hollow Golden Ki Energy Dome (Hemisphere over ground)
        dome_t = ease_out_back(clamp(self.time / 0.32, 0.0, 1.0))
        dome_r = int(self.radius * dome_t)
        
        if progress > 0.70:
            dome_alpha = int(255 * (1.0 - ((progress - 0.70) / 0.30)))
        else:
            dome_alpha = int(255 * clamp(self.time / 0.15, 0.0, 1.0))
            
        if dome_r > 5 and dome_alpha > 0:
            dome_rect = pygame.Rect(cx - dome_r, cy - dome_r, dome_r * 2, dome_r * 2)
            
            # Outer containment boundary arc
            pygame.draw.arc(surface, clamp_color((255, 200, 30, dome_alpha)), dome_rect, 0, math.pi, 6)
            pygame.draw.arc(surface, clamp_color((255, 255, 255, dome_alpha)), dome_rect, 0, math.pi, 2)
            
            # Internal Golden Forcefield Glow (Semi-transparent additive hemisphere)
            dome_surf = pygame.Surface((dome_r * 2 + 8, dome_r + 8), pygame.SRCALPHA)
            dcx = dome_r + 4
            dcy = dome_r + 4
            pygame.draw.circle(dome_surf, clamp_color((255, 190, 40, int(dome_alpha * 0.22))), (dcx, dcy), dome_r)
            pygame.draw.rect(dome_surf, (0, 0, 0, 0), (0, dcy, dome_r * 2 + 8, dome_r + 8))
            
            # Geodesic energy arcs (meridian longitudes)
            for m in [0.35, 0.70]:
                mr_w = int(dome_r * m)
                m_rect = pygame.Rect(dcx - mr_w, dcy - dome_r, mr_w * 2, dome_r * 2)
                pygame.draw.arc(dome_surf, clamp_color((255, 240, 150, int(dome_alpha * 0.45))), m_rect, 0, math.pi, 2)
                
            surface.blit(dome_surf, (cx - dcx, cy - dcy), special_flags=pygame.BLEND_RGBA_ADD)

        # 3. Ascending Horizontal Shock Rings traveling up the Dome
        for ring in self.shock_rings:
            rt = self.time - ring["time_start"]
            if 0.0 <= rt <= 0.45:
                r_prog = rt / 0.45
                h_pos = dome_r * r_prog
                h_ratio = clamp(h_pos / max(1, dome_r), 0.0, 1.0)
                ring_w = int(dome_r * math.sqrt(max(0.0, 1.0 - h_ratio ** 2)))
                ring_y = int(cy - h_pos)
                r_alpha = int(255 * (1.0 - r_prog))
                
                if ring_w > 4 and r_alpha > 0:
                    ring_rect = pygame.Rect(cx - ring_w, ring_y - 6, ring_w * 2, 12)
                    pygame.draw.ellipse(surface, clamp_color((255, 225, 80, r_alpha)), ring_rect, 4)
                    pygame.draw.ellipse(surface, clamp_color((255, 255, 255, r_alpha)), ring_rect, 1)

        # 4. Vertical Golden Ki Geysers & Sparks
        if 0.15 <= progress <= 0.70:
            for _ in range(3):
                gx = cx + random.randint(-dome_r + 10, dome_r - 10)
                gh = random.randint(20, int(dome_r * 0.8))
                pygame.draw.line(surface, clamp_color((255, 255, 220, 200)), (gx, cy), (gx, cy - gh), 2)


# ========================================================================================
# 8. ARCHETYPE 5: SAMURAI (WIND) - JUDGEMENT CUT (DIMENSIONAL SLASH)
# ========================================================================================

class SlashLineData:
    """Individual anime dimensional slash line tearing through space."""
    __slots__ = ("x1", "y1", "x2", "y2", "trigger_time", "duration", "color")

    def __init__(self, cx: float, cy: float, radius: float):
        ang = random.uniform(0.0, math.pi)
        length = random.uniform(radius * 0.8, radius * 1.6)
        mid_ox = random.uniform(-radius * 0.6, radius * 0.6)
        mid_oy = random.uniform(-radius * 0.6, radius * 0.6)
        
        dx = math.cos(ang) * (length * 0.5)
        dy = math.sin(ang) * (length * 0.5)
        
        self.x1 = cx + mid_ox - dx
        self.y1 = cy + mid_oy - dy
        self.x2 = cx + mid_ox + dx
        self.y2 = cy + mid_oy + dy
        
        self.trigger_time = random.uniform(0.10, 0.42)
        self.duration = random.uniform(0.25, 0.45)
        self.color = random.choice([
            (255, 255, 255),
            (140, 230, 255),
            (80, 190, 255),
            (210, 245, 255)
        ])


class SamuraiJudgementCutVFX(BaseUltimateAoE_VFX):
    """
    Samurai: Judgement Cut (Cortes Dimensionais).
    Anime time-freeze stillness: space desaturates/darkens inside the cut sphere,
    followed by dozens of razor-sharp white and sky-blue dimensional slashes
    crisscrossing space at chaotic angles, shattering reality into glass polygon shards.
    """
    def __init__(self, x: float, y: float, radius: float, character_id: str):
        super().__init__(x, y, radius, character_id)
        self.duration = 0.82
        self.center_y = self.y - self.radius * 0.2
        self.slashes: List[SlashLineData] = []
        self.glass_shards: List[Dict[str, Any]] = []
        
        # Generate 32 rapid dimensional slashes
        for _ in range(32):
            self.slashes.append(SlashLineData(self.x, self.center_y, self.radius))
            
        # Pre-generate broken reality glass shards for the sheath impact
        for _ in range(16):
            ox = random.uniform(-self.radius * 0.7, self.radius * 0.7)
            oy = random.uniform(-self.radius * 0.7, self.radius * 0.7)
            pts = []
            poly_r = random.uniform(12.0, 24.0)
            base_ang = random.uniform(0.0, math.tau)
            for i in range(random.randint(3, 5)):
                a = base_ang + i * (math.tau / 4.0) + random.uniform(-0.3, 0.3)
                pts.append((ox + math.cos(a) * poly_r, oy + math.sin(a) * poly_r))
            self.glass_shards.append({
                "pts": pts,
                "vx": (ox / self.radius) * 80.0 + random.uniform(-20, 20),
                "vy": (oy / self.radius) * 80.0 + random.uniform(-20, 20),
                "rot": 0.0,
                "rot_spd": random.uniform(-4.0, 4.0)
            })

    def update(self, dt: float):
        super().update(dt)
        if not self.active: return
        
        # Drift glass shards during shatter phase (time > 0.45)
        if self.time > 0.45:
            for g in self.glass_shards:
                g["rot"] += g["rot_spd"] * dt

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if not self.active: return
        cam_x, cam_y = camera_offset.x, camera_offset.y
        cx, cy = int(self.x - cam_x), int(self.center_y - cam_y)
        progress = clamp(self.time / self.duration, 0.0, 1.0)
        
        # 1. Spatial Desaturation / Dimensional Void Sphere
        if progress < 0.65:
            void_alpha = int(140 * math.sin((progress / 0.65) * math.pi))
            void_surf = pygame.Surface((int(self.radius * 2 + 10), int(self.radius * 2 + 10)), pygame.SRCALPHA)
            vc = void_surf.get_width() // 2
            pygame.draw.circle(void_surf, (15, 20, 35, void_alpha), (vc, vc), int(self.radius))
            pygame.draw.circle(void_surf, clamp_color((120, 230, 255, int(void_alpha * 0.75))), (vc, vc), int(self.radius), 2)
            surface.blit(void_surf, (cx - vc, cy - vc))

        # 2. Razor-Sharp Dimensional Katana Cuts
        for s in self.slashes:
            slash_t = self.time - s.trigger_time
            if 0.0 <= slash_t <= s.duration:
                st_prog = slash_t / s.duration
                alpha = int(255 * (1.0 - ease_in_quad(st_prog)))
                if alpha <= 0: continue
                
                sx1, sy1 = int(s.x1 - cam_x), int(s.y1 - cam_y)
                sx2, sy2 = int(s.x2 - cam_x), int(s.y2 - cam_y)
                
                # Outer electric aura
                pygame.draw.line(surface, clamp_color((*s.color[:3], int(alpha * 0.7))), (sx1, sy1), (sx2, sy2), 5)
                # Pure white razor beam
                pygame.draw.line(surface, clamp_color((255, 255, 255, alpha)), (sx1, sy1), (sx2, sy2), 2)
                # Diamond terminal sparks
                pygame.draw.circle(surface, clamp_color((255, 255, 255, alpha)), (sx1, sy1), 3)
                pygame.draw.circle(surface, clamp_color((255, 255, 255, alpha)), (sx2, sy2), 3)

        # 3. Anime Impact Frame Flash at Sheath Moment (t ~ 0.44)
        if 0.40 <= self.time <= 0.48:
            flash_p = (self.time - 0.40) / 0.08
            flash_alpha = int(240 * math.sin(flash_p * math.pi))
            pygame.draw.line(surface, clamp_color((255, 255, 255, flash_alpha)), (cx - self.radius, cy - self.radius), (cx + self.radius, cy + self.radius), 4)
            pygame.draw.line(surface, clamp_color((255, 255, 255, flash_alpha)), (cx - self.radius, cy + self.radius), (cx + self.radius, cy - self.radius), 4)

        # 4. Shattered Space (Geometric Glass Shards)
        if self.time > 0.44:
            shatter_prog = (self.time - 0.44) / (self.duration - 0.44)
            shatter_alpha = int(220 * (1.0 - ease_in_quad(shatter_prog)))
            if shatter_alpha > 0:
                for g in self.glass_shards:
                    drift_x = g["vx"] * shatter_prog
                    drift_y = g["vy"] * shatter_prog
                    pts = [(int(px + drift_x + cx), int(py + drift_y + cy)) for px, py in g["pts"]]
                    if len(pts) >= 3:
                        pygame.draw.polygon(surface, clamp_color((160, 230, 255, int(shatter_alpha * 0.4))), pts)
                        pygame.draw.polygon(surface, clamp_color((255, 255, 255, shatter_alpha)), pts, 1)


# ========================================================================================
# 9. ARCHETYPE 6: SHINOBI (SHADOW) - CLONE SHADOW DANCE
# ========================================================================================

class CloneDashVector:
    """Individual shadow clone trajectory blitzing through the darkness."""
    __slots__ = ("start_pos", "end_pos", "time_start", "duration", "color")

    def __init__(self, cx: float, cy: float, radius: float, time_start: float):
        ang1 = random.uniform(0.0, math.tau)
        ang2 = ang1 + random.uniform(math.pi * 0.6, math.pi * 1.4)
        dist1 = random.uniform(radius * 0.5, radius * 0.95)
        dist2 = random.uniform(radius * 0.5, radius * 0.95)
        
        self.start_pos = (cx + math.cos(ang1) * dist1, cy + math.sin(ang1) * dist1)
        self.end_pos = (cx + math.cos(ang2) * dist2, cy + math.sin(ang2) * dist2)
        self.time_start = time_start
        self.duration = random.uniform(0.18, 0.28)
        self.color = random.choice([
            (190, 80, 255),
            (230, 110, 255),
            (140, 50, 220)
        ])


class ShinobiShadowDanceVFX(BaseUltimateAoE_VFX):
    """
    Shinobi: Dança dos Clones.
    Volumetric purple shadow mist covers the area, while dark phantom silhouettes
    and high-speed clone motion streak lines blitz back and forth across the darkness.
    """
    def __init__(self, x: float, y: float, radius: float, character_id: str):
        super().__init__(x, y, radius, character_id)
        self.duration = 0.88
        self.center_y = self.y - self.radius * 0.15
        self.clone_dashes: List[CloneDashVector] = []
        self.shadow_clouds: List[Dict[str, Any]] = []
        
        # Schedule 8 zig-zagging clone dash strikes
        for i in range(8):
            t_start = 0.08 + i * 0.07
            self.clone_dashes.append(CloneDashVector(self.x, self.center_y, self.radius, t_start))
            
        # Pre-generate rolling shadow mist clouds
        for _ in range(14):
            ox = random.uniform(-self.radius * 0.8, self.radius * 0.8)
            oy = random.uniform(-self.radius * 0.6, self.radius * 0.6)
            self.shadow_clouds.append({
                "pos": (ox, oy),
                "radius": random.uniform(35.0, 70.0),
                "shade": random.randint(15, 35)
            })

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if not self.active: return
        cam_x, cam_y = camera_offset.x, camera_offset.y
        cx, cy = int(self.x - cam_x), int(self.center_y - cam_y)
        progress = clamp(self.time / self.duration, 0.0, 1.0)
        
        # 1. Volumetric Dark Purple Mist Covering the Area
        mist_alpha = int(160 * math.sin(progress * math.pi))
        if mist_alpha > 0:
            for sc in self.shadow_clouds:
                mx = int(cx + sc["pos"][0])
                my = int(cy + sc["pos"][1])
                mr = int(sc["radius"])
                pygame.draw.circle(surface, clamp_color((sc["shade"] + 20, sc["shade"], sc["shade"] + 45, mist_alpha)), (mx, my), mr)

        # 2. Blitzing Shadow Clone Vectors (Speed Lines & Phantom Silhouettes)
        for dash in self.clone_dashes:
            dt_dash = self.time - dash.time_start
            if 0.0 <= dt_dash <= dash.duration:
                dash_prog = dt_dash / dash.duration
                head_t = ease_out_expo(dash_prog)
                
                hx = lerp(dash.start_pos[0], dash.end_pos[0], head_t) - cam_x
                hy = lerp(dash.start_pos[1], dash.end_pos[1], head_t) - cam_y
                
                tail_t = max(0.0, head_t - 0.35)
                tx = lerp(dash.start_pos[0], dash.end_pos[0], tail_t) - cam_x
                ty = lerp(dash.start_pos[1], dash.end_pos[1], tail_t) - cam_y
                
                alpha = int(255 * (1.0 - dash_prog))
                
                # Motion speed streak
                pygame.draw.line(surface, clamp_color((*dash.color[:3], alpha)), (int(tx), int(ty)), (int(hx), int(hy)), 4)
                pygame.draw.line(surface, clamp_color((255, 255, 255, alpha)), (int(tx), int(ty)), (int(hx), int(hy)), 2)
                
                # Dark Phantom Silhouette at head
                pygame.draw.circle(surface, clamp_color((20, 5, 30, alpha)), (int(hx), int(hy)), 8)
                # Glowing Crimson Shinobi Eye Streak
                eye_col = (255, 40, 110, alpha)
                pygame.draw.circle(surface, clamp_color(eye_col), (int(hx), int(hy)), 3)
                
                # Terminus Cross-Slash when clone completes dash
                if dash_prog > 0.75:
                    cross_alpha = int(255 * ((dash_prog - 0.75) / 0.25))
                    c_size = 18
                    pygame.draw.line(surface, clamp_color((255, 200, 255, cross_alpha)), (int(hx - c_size), int(hy - c_size)), (int(hx + c_size), int(hy + c_size)), 2)
                    pygame.draw.line(surface, clamp_color((255, 200, 255, cross_alpha)), (int(hx - c_size), int(hy + c_size)), (int(hx + c_size), int(hy - c_size)), 2)

        # 3. Perimeter Shadow Tentacles / Smoke Tendrils
        if 0.20 <= progress <= 0.75:
            t_prog = (progress - 0.20) / 0.55
            tentacle_alpha = int(180 * math.sin(t_prog * math.pi))
            for i in range(8):
                ang = (i / 8.0) * math.tau + progress * 2.0
                dist = self.radius * 0.85
                tx = cx + int(math.cos(ang) * dist)
                ty = cy + int(math.sin(ang) * dist)
                pygame.draw.circle(surface, clamp_color((180, 70, 255, tentacle_alpha)), (tx, ty), 5)


# ========================================================================================
# 10. ARCHETYPE 7: SHAIA (LIGHT/SACRED) - DIVINE JUDGEMENT
# ========================================================================================

class DivineLaserLance:
    """Individual orbital laser beam raining from the heavens."""
    __slots__ = ("offset_x", "width", "time_start", "duration", "color_core", "color_glow")

    def __init__(self, offset_x: float, width: float, time_start: float):
        self.offset_x = offset_x
        self.width = width
        self.time_start = time_start
        self.duration = random.uniform(0.28, 0.42)
        self.color_core = (255, 255, 255)
        self.color_glow = (255, 220, 80)


class ShaiaDivineJudgementVFX(BaseUltimateAoE_VFX):
    """
    Shaia: Julgamento Divino.
    Projects an intricate golden sacred magic seal on the ground, while multiple intense,
    thin and thick orbital divine laser pillars rain down from the sky, searing burning
    holy glyphs and craters into the earth.
    """
    def __init__(self, x: float, y: float, radius: float, character_id: str):
        super().__init__(x, y, radius, character_id)
        self.duration = 0.92
        self.lasers: List[DivineLaserLance] = []
        self.impact_sparks: List[BaseVFXParticle] = []
        
        # Central primary mega laser
        self.lasers.append(DivineLaserLance(0.0, 32.0, 0.12))
        
        # Secondary satellite laser strikes raining rhythmically across radius
        num_lasers = 8
        span = self.radius * 0.85
        for i in range(num_lasers):
            ox = random.uniform(-span, span)
            w = random.uniform(8.0, 16.0)
            t_start = 0.15 + i * 0.05
            self.lasers.append(DivineLaserLance(ox, w, t_start))

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if not self.active: return
        cam_x, cam_y = camera_offset.x, camera_offset.y
        cx, cy = int(self.x - cam_x), int(self.y - cam_y)
        progress = clamp(self.time / self.duration, 0.0, 1.0)
        
        # 1. Sacred Ground Magic Seal (Intricate geometric holy circle)
        seal_alpha = int(255 * math.sin(progress * math.pi))
        if seal_alpha > 0:
            seal_r = int(self.radius * 0.95 * ease_out_expo(clamp(self.time / 0.25, 0.0, 1.0)))
            if seal_r > 8:
                seal_rect = pygame.Rect(cx - seal_r, cy - int(seal_r * 0.35), seal_r * 2, int(seal_r * 0.7))
                pygame.draw.ellipse(surface, clamp_color((255, 215, 60, seal_alpha)), seal_rect, 3)
                pygame.draw.ellipse(surface, clamp_color((255, 255, 255, seal_alpha)), seal_rect, 1)
                
                # Inner concentric rune band
                inner_rect = pygame.Rect(cx - int(seal_r * 0.65), cy - int(seal_r * 0.22), int(seal_r * 1.3), int(seal_r * 0.44))
                pygame.draw.ellipse(surface, clamp_color((255, 240, 140, int(seal_alpha * 0.7))), inner_rect, 2)
                
                # 8-Pointed Holy Star inside seal
                star_pts = []
                for i in range(8):
                    ang = (i / 8.0) * math.tau + (progress * 0.8)
                    dist = seal_r * (0.85 if (i % 2 == 0) else 0.4)
                    star_pts.append((cx + int(math.cos(ang) * dist), cy + int(math.sin(ang) * (dist * 0.35))))
                pygame.draw.polygon(surface, clamp_color((255, 230, 100, int(seal_alpha * 0.5))), star_pts, 2)

        # 2. Orbital Laser Beams Raining from Sky
        sky_y = cy - 650
        for laser in self.lasers:
            lt = self.time - laser.time_start
            if 0.0 <= lt <= laser.duration:
                l_prog = lt / laser.duration
                if l_prog < 0.20:
                    beam_alpha = int(255 * (l_prog / 0.20))
                    w_factor = l_prog / 0.20
                else:
                    beam_alpha = int(255 * (1.0 - (l_prog - 0.20) / 0.80))
                    w_factor = 1.0 - ((l_prog - 0.20) / 0.80) * 0.4
                    
                cur_w = max(2, int(laser.width * w_factor))
                lx = cx + int(laser.offset_x)
                
                # Outer Holy Aura Beam
                pygame.draw.line(surface, clamp_color((*laser.color_glow[:3], int(beam_alpha * 0.75))), (lx, sky_y), (lx, cy), cur_w + 6)
                # Pure White-Hot Laser Core
                pygame.draw.line(surface, clamp_color((*laser.color_core[:3], beam_alpha)), (lx, sky_y), (lx, cy), cur_w)
                
                # Ground Impact Searing Scar / Flare
                impact_r = int((cur_w + 10) * 1.5)
                impact_rect = pygame.Rect(lx - impact_r, cy - int(impact_r * 0.4), impact_r * 2, int(impact_r * 0.8))
                pygame.draw.ellipse(surface, clamp_color((255, 255, 255, beam_alpha)), impact_rect)
                pygame.draw.ellipse(surface, clamp_color((255, 200, 40, int(beam_alpha * 0.8))), impact_rect, 2)

        # 3. Anime Impact Frame Flash at first laser strike
        if 0.12 <= self.time <= 0.18:
            flash_p = (self.time - 0.12) / 0.06
            flash_alpha = int(240 * math.sin(flash_p * math.pi))
            pygame.draw.line(surface, clamp_color((255, 255, 255, flash_alpha)), (cx - self.radius, cy), (cx + self.radius, cy), 4)

        # 4. Falling Celestial Sparks & Feathers
        if 0.25 <= progress <= 0.85:
            for _ in range(4):
                fx = cx + random.randint(-int(self.radius * 0.8), int(self.radius * 0.8))
                fy = cy - random.randint(20, 180)
                pygame.draw.circle(surface, clamp_color((255, 255, 200, 220)), (fx, fy), 2)


# ========================================================================================
# 11. POLYMORPHIC REGISTRY POPULATION
# ========================================================================================

_AOE_VFX_REGISTRY.update({
    "ignis": IgnisVolcanicEruptionVFX,
    "lunaria": LunariaSingularityVFX,
    "astra": AstraShardBlizzardVFX,
    "fighter": RyuuKiDomainVFX,
    "ryuu": RyuuKiDomainVFX,
    "samurai": SamuraiJudgementCutVFX,
    "shinobi": ShinobiShadowDanceVFX,
    "shaia": ShaiaDivineJudgementVFX,
})

