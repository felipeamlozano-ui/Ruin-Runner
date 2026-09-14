import pygame
import os
import math
import random
from collections import deque
from typing import List, Tuple, Dict, Optional
from engine.animation import Animation, AnimationManager, load_spritesheet, load_animation_folder

# ========================================================================================
# 1. CORE MATH & HIGH-DPI UTILITIES
# ========================================================================================
def clamp_color(color: Tuple[float, ...]) -> Tuple[int, ...]:
    if len(color) == 4:
        return (max(0, min(255, int(color[0]))), max(0, min(255, int(color[1]))), 
                max(0, min(255, int(color[2]))), max(0, min(255, int(color[3]))))
    return (max(0, min(255, int(color[0]))), max(0, min(255, int(color[1]))), max(0, min(255, int(color[2]))))

def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * max(0.0, min(1.0, t))

def ease_out_expo(t: float) -> float:
    return 1.0 if t >= 1.0 else 1.0 - (2.0 ** (-10.0 * t))

def ease_out_back(t: float) -> float:
    c1 = 1.70158
    c3 = c1 + 1.0
    t = t - 1.0
    return 1.0 + c3 * (t ** 3) + c1 * (t ** 2)


# ========================================================================================
# 2. HD-2D HIGH-DPI PALETTES & STYLES
# ========================================================================================
class HighDPIEnergyPalette:
    __slots__ = ("core", "inner_glow", "outer_glow", "tail_base", "tail_tip", "spark", "style")
    def __init__(self, core, inner_glow, outer_glow, tail_base, tail_tip, spark, style="fire"):
        self.core = core               
        self.inner_glow = inner_glow   
        self.outer_glow = outer_glow   
        self.tail_base = tail_base     
        self.tail_tip = tail_tip       
        self.spark = spark
        self.style = style # 'fire', 'water', 'ice', 'ki', 'shadow', 'wind', 'void'

def get_high_dpi_palette(ptype: str, is_enemy: bool) -> HighDPIEnergyPalette:
    if is_enemy:
        if ptype in ("boss_fireball", "blood"):
            return HighDPIEnergyPalette((255, 200, 200), (255, 50, 50), (180, 0, 0), (120, 0, 0), (50, 0, 0), (255, 100, 100), "void")
        elif ptype in ("acid", "necrotic"):
            return HighDPIEnergyPalette((220, 255, 220), (100, 255, 50), (20, 180, 20), (0, 120, 0), (0, 50, 0), (150, 255, 100), "void")
        else:
            return HighDPIEnergyPalette((255, 200, 255), (180, 50, 255), (100, 0, 200), (60, 0, 120), (20, 0, 40), (200, 100, 255), "void")
        
    if ptype in ("fireball", "fire_spark", "fire_sphere"):
        return HighDPIEnergyPalette((255, 255, 255), (255, 220, 80), (255, 100, 0), (220, 50, 0), (100, 10, 0), (255, 150, 50), "fire")
    elif ptype in ("arcane_bolt", "arcane_sphere"):
        return HighDPIEnergyPalette((255, 255, 255), (150, 240, 255), (40, 180, 255), (20, 120, 220), (10, 50, 150), (200, 255, 255), "water")
    elif ptype in ("frost_lance", "frost_orb"):
        return HighDPIEnergyPalette((255, 255, 255), (255, 180, 255), (180, 80, 255), (120, 40, 220), (60, 0, 120), (255, 200, 255), "ice")
    elif ptype == "ki_blast":
        return HighDPIEnergyPalette((255, 255, 255), (255, 240, 100), (255, 180, 20), (200, 120, 0), (100, 50, 0), (255, 255, 150), "ki")
    elif ptype == "shuriken":
        return HighDPIEnergyPalette((230, 220, 255), (160, 100, 255), (100, 40, 200), (60, 0, 150), (30, 0, 80), (180, 120, 255), "shadow")
    elif ptype == "vacuum_slash":
        return HighDPIEnergyPalette((255, 255, 255), (200, 250, 255), (100, 200, 255), (50, 150, 220), (20, 80, 150), (220, 255, 255), "wind")
    else:
        return HighDPIEnergyPalette((255, 255, 255), (255, 240, 150), (255, 200, 80), (200, 150, 40), (100, 80, 10), (255, 255, 200), "fire")


# ========================================================================================
# 3. HIGH-DPI PROCEDURAL ORB FACTORY
# ========================================================================================
class HighDPIOrbFactory:
    _cache: Dict[Tuple, pygame.Surface] = {}

    @classmethod
    def get_orb(cls, radius: int, palette: HighDPIEnergyPalette) -> pygame.Surface:
        key = ("hd_orb", radius, palette.outer_glow)
        if key in cls._cache: return cls._cache[key]
        
        scale_hi = 2
        hi_rad = radius * scale_hi
        surf = pygame.Surface((hi_rad * 2, hi_rad * 2), pygame.SRCALPHA)
        cx, cy = hi_rad, hi_rad
        
        for r in range(hi_rad, 0, -1):
            t = r / hi_rad
            if t > 0.75: continue 
            elif t > 0.5: color = (*palette.outer_glow[:3], 220)
            elif t > 0.25: color = palette.inner_glow
            else: color = palette.core
            pygame.draw.circle(surf, color, (cx, cy), r)
            
        final_size = radius * 2
        final_surf = pygame.transform.smoothscale(surf, (final_size, final_size))
        
        cls._cache[key] = final_surf
        return final_surf


# ========================================================================================
# 4. CHARACTERISTIC ROCKET TAIL ENGINE
# ========================================================================================
class RocketTailEngine:
    """Cauda dinâmica. O comportamento dos blocos varia baseado no elemento."""
    def __init__(self, palette: HighDPIEnergyPalette, max_length: int = 16):
        self.history = deque(maxlen=max_length)
        self.palette = palette
        
    def add_point(self, x: float, y: float, vx: float, vy: float):
        self.history.appendleft({"x": x, "y": y, "vx": vx, "vy": vy})
        
    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        if len(self.history) < 2: return
        trail_surf = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        
        for i, pt in enumerate(self.history):
            progress = i / len(self.history)
            
            # Comportamento característico do tamanho e onda
            if self.palette.style == "wind":
                # Vento: Cauda afiada, longa, sem ondulação
                size = int(lerp(12.0, 1.0, progress))
                wave = 0
            elif self.palette.style == "shadow":
                # Sombra: Blocos falham/glitcham (pula alguns frames)
                if random.random() < 0.15: continue
                size = int(lerp(10.0, 2.0, progress))
                wave = math.sin(i * 1.5) * 5.0 * progress
            elif self.palette.style == "ki":
                # Ki: Pulsos de energia
                pulse = 1.2 if i % 4 == 0 else 0.8
                size = int(lerp(10.0, 4.0, progress) * pulse)
                wave = math.sin(i * 0.5) * 2.0 * progress
            elif self.palette.style == "water":
                # Água/Arcano: Ondulação suave e contínua
                size = int(lerp(11.0, 4.0, progress))
                wave = math.sin(i * 0.6) * 4.0 * progress
            else:
                # Fogo/Void: Caótico, blocos dispersos
                size = int(lerp(10.0, 3.0, progress))
                wave = math.sin(i * 1.2) * 6.0 * progress
                
            if size <= 0: continue
            
            px, py = int(pt["x"] - cam_x), int(pt["y"] - cam_y)
            color = self.palette.tail_base if progress < 0.5 else self.palette.tail_tip
            alpha = int(255 * (1.0 - progress))
            
            rect = pygame.Rect(px - size, py - size + int(wave), size * 2, size * 2)
            pygame.draw.rect(trail_surf, clamp_color((*color[:3], alpha)), rect)

        surface.blit(trail_surf, (0, 0))


# ========================================================================================
# 5. CHARACTER-SPECIFIC PARTICLE SYSTEMS (VFX SIGNATURES)
# ========================================================================================
class BaseParticle:
    def update(self, dt: float) -> bool: return False
    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float): pass

class SmokeParticle(BaseParticle):
    """Fumaça de Fogo (Ignis). Sobe lentamente, cresce e dissipa."""
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "size", "color")
    def __init__(self, x, y, vx, vy, life, color):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.color = color
        self.size = random.uniform(3.0, 8.0)

    def update(self, dt: float) -> bool:
        self.vx *= 0.92
        self.vy *= 0.92
        self.vy -= 40.0 * dt # Flutua para cima
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.size += 15.0 * dt # Fumaça expande
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        if self.life <= 0: return
        t = self.life / self.max_life
        alpha = int(180 * t)
        dx, dy = int(self.x - cam_x), int(self.y - cam_y)
        pygame.draw.circle(surface, clamp_color((*self.color[:3], alpha)), (dx, dy), int(self.size))

class StardustParticle(BaseParticle):
    """Poeira Estelar (Lunaria). Brilha intensamente, encolhe e flutua suavemente."""
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size", "phase")
    def __init__(self, x, y, vx, vy, life, color):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.color = color
        self.size = random.uniform(1.5, 4.0)
        self.phase = random.uniform(0, math.tau)

    def update(self, dt: float) -> bool:
        self.vx *= 0.85
        self.vy *= 0.85
        self.vy += math.sin(self.phase + self.life * 5) * 20 * dt # Movimento de folha caindo
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        if self.life <= 0: return
        t = self.life / self.max_life
        alpha = int(255 * ease_out_expo(t * 2))
        dx, dy = int(self.x - cam_x), int(self.y - cam_y)
        sz = max(1, int(self.size * t))
        
        # Desenha uma mini-estrela/brilho
        pygame.draw.line(surface, clamp_color((*self.color[:3], alpha)), (dx - sz*2, dy), (dx + sz*2, dy), 1)
        pygame.draw.line(surface, clamp_color((*self.color[:3], alpha)), (dx, dy - sz*2), (dx, dy + sz*2), 1)
        pygame.draw.circle(surface, clamp_color((255, 255, 255, alpha)), (dx, dy), sz)

class IceShardParticle(BaseParticle):
    """Fragmentos de Gelo (Astra). Caem com gravidade pesada e giram."""
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "angle", "rot_spd", "size")
    def __init__(self, x, y, vx, vy, life, color):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.color = color
        self.size = random.uniform(3.0, 6.0)
        self.angle = random.uniform(0, math.tau)
        self.rot_spd = random.uniform(-10, 10)

    def update(self, dt: float) -> bool:
        self.vy += 300.0 * dt # Gravidade
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.angle += self.rot_spd * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        if self.life <= 0: return
        t = self.life / self.max_life
        alpha = int(255 * t)
        dx, dy = self.x - cam_x, self.y - cam_y
        
        # Desenha um losango rotacionado
        pts = []
        for i in range(4):
            ang = self.angle + i * (math.pi / 2)
            dist = self.size if i % 2 == 0 else self.size * 0.5
            pts.append((dx + math.cos(ang) * dist, dy + math.sin(ang) * dist))
            
        pygame.draw.polygon(surface, clamp_color((*self.color[:3], alpha)), pts)
        pygame.draw.polygon(surface, clamp_color((255, 255, 255, alpha)), pts, 1)

class KiRingParticle(BaseParticle):
    """Anéis Expansivos (Ryuu). Explodem para fora para simular quebra da barreira."""
    __slots__ = ("x", "y", "life", "max_life", "color", "max_radius")
    def __init__(self, x, y, life, color):
        self.x, self.y = x, y
        self.life = self.max_life = life
        self.color = color
        self.max_radius = random.uniform(15.0, 35.0)

    def update(self, dt: float) -> bool:
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        if self.life <= 0: return
        t = 1.0 - (self.life / self.max_life)
        ease = ease_out_expo(t)
        alpha = int(200 * (1.0 - ease))
        if alpha <= 0: return
        
        r = int(self.max_radius * ease)
        dx, dy = int(self.x - cam_x), int(self.y - cam_y)
        if r > 0:
            pygame.draw.circle(surface, clamp_color((*self.color[:3], alpha)), (dx, dy), r, max(1, int(4 * (1.0 - ease))))

class ShadowMistParticle(BaseParticle):
    """Névoa Sombria (Shinobi). Nuvens amorfas que ficam para trás lentamente."""
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size")
    def __init__(self, x, y, vx, vy, life, color):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.color = color
        self.size = random.uniform(8.0, 16.0)

    def update(self, dt: float) -> bool:
        self.vx *= 0.8 # Para rápido
        self.vy *= 0.8
        self.size += 5.0 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        if self.life <= 0: return
        t = self.life / self.max_life
        alpha = int(120 * t) # Sempre meio translúcido
        dx, dy = int(self.x - cam_x), int(self.y - cam_y)
        pygame.draw.circle(surface, clamp_color((*self.color[:3], alpha)), (dx, dy), int(self.size))

class WindCrescentParticle(BaseParticle):
    """Cortes de Vento (Samurai). Linhas curvas afiadas."""
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "angle", "scale")
    def __init__(self, x, y, vx, vy, life, color, angle):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.color = color
        self.angle = angle
        self.scale = random.uniform(0.5, 1.5)

    def update(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        if self.life <= 0: return
        t = self.life / self.max_life
        alpha = int(255 * t)
        dx, dy = int(self.x - cam_x), int(self.y - cam_y)
        
        # Desenha um arco 
        rect_w = int(20 * self.scale)
        rect_h = int(10 * self.scale)
        arc_rect = pygame.Rect(dx - rect_w//2, dy - rect_h//2, rect_w, rect_h)
        # Gambiarra para girar o arco desenhando numa surface temp
        temp = pygame.Surface((rect_w, rect_h), pygame.SRCALPHA)
        pygame.draw.arc(temp, clamp_color((*self.color[:3], alpha)), (0, 0, rect_w, rect_h), 0, math.pi, 2)
        rotated = pygame.transform.rotate(temp, math.degrees(self.angle))
        rw, rh = rotated.get_size()
        surface.blit(rotated, (dx - rw//2, dy - rh//2))

class BloodDripParticle(BaseParticle):
    """Gotas Ácidas/Sanguíneas (Inimigos). Pingam pesadamente para o chão."""
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size")
    def __init__(self, x, y, vx, vy, life, color):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.color = color
        self.size = random.uniform(1.5, 3.5)

    def update(self, dt: float) -> bool:
        self.vy += 450.0 * dt # Alta gravidade (peso do líquido)
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        if self.life <= 0: return
        t = self.life / self.max_life
        alpha = int(255 * t)
        dx, dy = int(self.x - cam_x), int(self.y - cam_y)
        # Gota afunilada
        pygame.draw.line(surface, clamp_color((*self.color[:3], alpha)), (dx, dy), (dx, dy - int(self.size*2)), int(self.size))
        pygame.draw.circle(surface, clamp_color((*self.color[:3], alpha)), (dx, dy), int(self.size))

class EnergyStreak(BaseParticle):
    """Fallback Clássico de Alta Velocidade"""
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "length")
    def __init__(self, x, y, vx, vy, life, color, length):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.color = color
        self.length = length

    def update(self, dt: float) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        if self.life <= 0: return
        t = self.life / self.max_life
        alpha = int(255 * t)
        dx, dy = self.x - cam_x, self.y - cam_y
        speed = math.hypot(self.vx, self.vy)
        if speed > 0:
            nx, ny = self.vx / speed, self.vy / speed
            pygame.draw.line(surface, clamp_color((*self.color[:3], alpha)), (dx, dy), (dx - nx * self.length, dy - ny * self.length), 1)


class ImpactSparkStreak(BaseParticle):
    """Faísca cinética direcional com rastro esticado e atenuação de velocidade."""
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "core_color", "width", "drag")
    def __init__(self, x: float, y: float, vx: float, vy: float, life: float, color: Tuple[int, ...], core_color: Tuple[int, ...] = (255, 255, 255), width: int = 2):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = self.max_life = life
        self.color = color
        self.core_color = core_color
        self.width = width
        self.drag = 0.90

    def update(self, dt: float) -> bool:
        factor = (self.drag ** (dt * 60))
        self.vx *= factor
        self.vy *= factor
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        if self.life <= 0: return
        t = max(0.0, min(1.0, self.life / self.max_life))
        alpha = int(255 * (t ** 0.8))
        if alpha <= 0: return
        dx, dy = self.x - cam_x, self.y - cam_y
        speed = math.hypot(self.vx, self.vy)
        if speed > 15:
            tail_len = min(15.0, max(3.0, speed * 0.04))
            nx, ny = self.vx / speed, self.vy / speed
            tx, ty = dx - nx * tail_len, dy - ny * tail_len
            col = self.color if t < 0.65 else self.core_color
            pygame.draw.line(surface, clamp_color((*col[:3], alpha)), (int(dx), int(dy)), (int(tx), int(ty)), self.width)
        else:
            pygame.draw.circle(surface, clamp_color((*self.color[:3], alpha)), (int(dx), int(dy)), max(1, self.width // 2))


class ShockwaveRingParticle(BaseParticle):
    """Anel de choque expansivo de alta definição com dissipação rápida e borda dupla."""
    __slots__ = ("x", "y", "life", "max_life", "max_radius", "outer_color", "inner_color")
    def __init__(self, x: float, y: float, max_radius: float = 32.0, life: float = 0.18, outer_color: Tuple[int, ...] = (255, 160, 40), inner_color: Tuple[int, ...] = (255, 255, 255)):
        self.x = x
        self.y = y
        self.life = self.max_life = life
        self.max_radius = max_radius
        self.outer_color = outer_color
        self.inner_color = inner_color

    def update(self, dt: float) -> bool:
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        if self.life <= 0: return
        t = max(0.0, min(1.0, 1.0 - (self.life / self.max_life)))
        ease = ease_out_expo(t)
        cur_r = int(self.max_radius * ease)
        if cur_r < 2: return
        
        alpha = max(0, min(255, int(230 * (1.0 - ease))))
        if alpha <= 0: return
        
        dx, dy = int(self.x - cam_x), int(self.y - cam_y)
        ring_surf = pygame.Surface((cur_r * 2 + 8, cur_r * 2 + 8), pygame.SRCALPHA)
        rc = cur_r + 4
        
        thickness = max(1, int(3 * (1.0 - ease)))
        pygame.draw.circle(ring_surf, clamp_color((*self.outer_color[:3], alpha)), (rc, rc), cur_r, thickness)
        pygame.draw.circle(ring_surf, clamp_color((*self.inner_color[:3], int(alpha * 0.9))), (rc, rc), cur_r, 1)
        
        surface.blit(ring_surf, (dx - rc, dy - rc), special_flags=pygame.BLEND_RGBA_ADD)


# ========================================================================================
# 6. DYNAMIC TRAJECTORY SYSTEM
# ========================================================================================
class Trajectory:
    def update(self, pos: pygame.math.Vector2, vel: pygame.math.Vector2, dt: float, target: Optional[pygame.FRect] = None):
        pass

class LinearTrajectory(Trajectory):
    def update(self, pos: pygame.math.Vector2, vel: pygame.math.Vector2, dt: float, target: Optional[pygame.FRect] = None):
        pos += vel * dt

class WaveTrajectory(Trajectory):
    """Magias de sombra/fantasma se movem em senóide leve."""
    def __init__(self, amplitude=30.0, freq=8.0):
        self.amp = amplitude
        self.freq = freq
        self.time = 0.0
        self.base_y = None
        
    def update(self, pos: pygame.math.Vector2, vel: pygame.math.Vector2, dt: float, target: Optional[pygame.FRect] = None):
        if self.base_y is None: self.base_y = pos.y
        self.time += dt
        pos.x += vel.x * dt
        pos.y = self.base_y + math.sin(self.time * self.freq) * self.amp
        vel.y = math.cos(self.time * self.freq) * self.amp * self.freq


# ========================================================================================
# 7. LEGACY & PROCEDURAL HIT ANIMATIONS (Hit Starburst Factory)
# ========================================================================================
_FIREBALL_CACHES = {}
_PURPLE_SPHERE_FLY_FRAMES = None
_PURPLE_SPHERE_HIT_FRAMES = None
_SPHERE_CACHES = {}
_SHURIKEN_FRAMES = None
_WIND_SLASH_FRAMES = None

def _get_fallback_anim(color: Tuple[int, ...]) -> Animation:
    surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.circle(surf, color, (16, 16), 16)
    return Animation([surf], 24, False)

def get_fireball_anims(color: str = "red") -> Tuple[Animation, Animation]:
    global _FIREBALL_CACHES
    if color not in _FIREBALL_CACHES:
        fb = _get_fallback_anim((255, 100, 100))
        _FIREBALL_CACHES[color] = (fb.frames, fb.frames)
    return Animation(_FIREBALL_CACHES[color][0], 24, True), Animation(_FIREBALL_CACHES[color][1], 24, False)

def get_purple_sphere_anims() -> Tuple[Animation, Animation]:
    surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    return Animation([surf], 24, True), Animation([surf], 24, False)

def get_sphere_projectile_anims(color: str = "blue", scale: float = 0.60) -> Tuple[Animation, Animation]:
    surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    return Animation([surf], 24, True), Animation([surf], 24, False)

def get_shuriken_anims() -> Tuple[Animation, Animation]:
    surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    return Animation([surf], 30, True), Animation([surf], 24, False)

def get_vacuum_slash_anims() -> Tuple[Animation, Animation]:
    surf = pygame.Surface((32, 32), pygame.SRCALPHA)
    return Animation([surf], 20, True), Animation([surf], 24, False)


class HitAnimationFactory:
    """
    Carrega, escala e tintura os frames de vfx_hit (starburst pixel art)
    com base na paleta elementar do projétil, mantendo cache otimizado.
    """
    _grayscale_cache: Optional[List[pygame.Surface]] = None
    _anim_cache: Dict[Tuple[float, str, Tuple[int, ...]], Animation] = {}

    @classmethod
    def _load_grayscale_frames(cls) -> List[pygame.Surface]:
        if cls._grayscale_cache is not None:
            return cls._grayscale_cache
            
        vfx_path = os.path.join("assets", "sprites", "vfx", "vfx_hit")
        frames: List[pygame.Surface] = []
        if os.path.exists(vfx_path):
            files = sorted([f for f in os.listdir(vfx_path) if f.endswith(".png") and f.startswith("vfx_hit")])
            for f in files:
                full_path = os.path.join(vfx_path, f)
                try:
                    surf = pygame.image.load(full_path).convert_alpha()
                    gray = pygame.transform.grayscale(surf)
                    frames.append(gray)
                except Exception:
                    pass
                    
        cls._grayscale_cache = frames
        return frames

    @classmethod
    def get_hit_animation(cls, palette: HighDPIEnergyPalette, scale: float = 0.65, fps: int = 28) -> Animation:
        cache_key = (round(scale, 2), palette.style, palette.inner_glow)
        if cache_key in cls._anim_cache:
            cached = cls._anim_cache[cache_key]
            return Animation(cached.frames, fps=cached.fps, loop=False)

        grays = cls._load_grayscale_frames()
        if not grays:
            # Fallback procedural seguro
            surf = pygame.Surface((32, 32), pygame.SRCALPHA)
            pygame.draw.circle(surf, palette.inner_glow, (16, 16), 14)
            return Animation([surf], fps=24, loop=False)

        tint_color = palette.inner_glow
        if palette.style == "fire":
            tint_color = (255, 140, 25)
        elif palette.style == "void":
            tint_color = palette.inner_glow

        tinted_frames: List[pygame.Surface] = []
        for g_surf in grays:
            gw, gh = g_surf.get_size()
            target_w = max(16, int(gw * scale))
            target_h = max(16, int(gh * scale))
            scaled_gray = pygame.transform.smoothscale(g_surf, (target_w, target_h))
            
            tint_surf = pygame.Surface((target_w, target_h), pygame.SRCALPHA)
            tint_surf.fill((*tint_color[:3], 255))
            
            final_surf = scaled_gray.copy()
            final_surf.blit(tint_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            tinted_frames.append(final_surf)

        anim = Animation(tinted_frames, fps=fps, loop=False)
        cls._anim_cache[cache_key] = anim
        return Animation(tinted_frames, fps=fps, loop=False)


# ========================================================================================
# 8. MAIN PROJECTILE CLASS (O Foguete Dinâmico e Personalizado)
# ========================================================================================
class Projectile:
    """
    Projétil de Alta Definição (High-DPI), com cauda em blocos dinâmica,
    malha de textura limpa e SISTEMA DE PARTÍCULAS EXCLUSIVO POR PERSONAGEM.
    """
    def __init__(
        self, 
        x: float, 
        y: float, 
        facing_right: bool, 
        is_enemy: bool = False, 
        projectile_type: str = None, 
        is_burn: bool = False, 
        color: str = None, 
        damage: int = None,
        trajectory_type: str = "linear"
    ):
        self.active = True
        self.is_enemy = is_enemy
        self.facing_right = facing_right
        self.state = "fly"
        self.is_burn = is_burn
        self.time_alive = 0.0
        self.hit_entities = set()
        
        self.projectile_type = projectile_type or ("purple_sphere" if is_enemy else "fireball")
        
        speed = 380
        if is_enemy:
            self.damage = damage if damage is not None else 12
            speed = 160
        else:
            DAMAGE_FALLBACK = {"arcane_bolt": 5, "arcane_sphere": 45, "fire_spark": 6, "fire_sphere": 48, "frost_lance": 5, "frost_orb": 42, "shuriken": 40, "vacuum_slash": 40, "ki_blast": 40, "fireball": 40}
            self.damage = damage if damage is not None else DAMAGE_FALLBACK.get(self.projectile_type, 40)
            
        self.pos = pygame.math.Vector2(x, y)
        self.velocity = pygame.math.Vector2(speed if facing_right else -speed, 0)
        
        self.radius = 14
        self.rect = pygame.FRect(self.pos.x, self.pos.y, self.radius * 2, self.radius * 2)
        
        self.palette = get_high_dpi_palette(self.projectile_type, self.is_enemy)
        self.orb_surf = HighDPIOrbFactory.get_orb(self.radius, self.palette)
        self.tail = RocketTailEngine(self.palette, max_length=14)
        
        self.particles: List[BaseParticle] = []
        self.spawn_timer = 0.0
        
        # Shuriken/Shadow usa trajetória wave sutil para parecer fantasmagórica
        if self.palette.style == "shadow":
            self.trajectory = WaveTrajectory(amplitude=20.0, freq=5.0)
        else:
            self.trajectory = LinearTrajectory()
        
        # Escala do impacto baseada no porte da magia
        if self.projectile_type in ("arcane_sphere", "fire_sphere", "frost_orb", "boss_fireball"):
            self.impact_scale = 0.85
        elif self.projectile_type in ("arcane_bolt", "fire_spark", "frost_lance"):
            self.impact_scale = 0.55
        else:
            self.impact_scale = 0.68
            
        self.impact_angle = 0.0

        self.anim_manager = AnimationManager()
        fly_anim, _ = get_fireball_anims("red" if not is_enemy else "blue")
        hit_anim = HitAnimationFactory.get_hit_animation(self.palette, scale=self.impact_scale, fps=28)
        self.anim_manager.add_animation("fly", fly_anim)
        self.anim_manager.add_animation("hit", hit_anim)
        self.has_hit = False
        self.anim_manager.play("fly")

    def can_deal_damage(self) -> bool:
        return self.active and self.state == "fly" and not self.has_hit

    def explode(self):
        if self.state != "hit":
            self.state = "hit"
            self.has_hit = True
            self.damage = 0
            
            # Registra o vetor de impacto antes de zerar velocidade para espalhamento direcional
            vx, vy = self.velocity.x, self.velocity.y
            if vx == 0 and vy == 0:
                vx = 1.0 if self.facing_right else -1.0
                vy = 0.0
            self.impact_angle = math.atan2(vy, vx)
            
            self.velocity.update(0, 0)
            self.anim_manager.play("hit", force_reset=True)
            self._trigger_shatter_vfx()

    def _trigger_shatter_vfx(self):
        """Gera o impacto visual dinâmico com anéis de choque, faíscas cinéticas e detritos elementares."""
        cx, cy = self.rect.centerx, self.rect.centery
        rebound_angle = self.impact_angle + math.pi
        
        # 1. Anel de Choque Expansivo Luminoso
        shock_rad = 36.0 if self.impact_scale >= 0.8 else 28.0
        self.particles.append(ShockwaveRingParticle(
            cx, cy,
            max_radius=shock_rad,
            life=0.18,
            outer_color=self.palette.outer_glow,
            inner_color=self.palette.core
        ))
        
        # 2. Faíscas Cinéticas de Alta Velocidade (Cone de ricochete + dispersão radial)
        num_sparks = 14 if self.impact_scale >= 0.8 else 10
        for _ in range(num_sparks):
            if random.random() < 0.65:
                ang = rebound_angle + random.uniform(-math.radians(65), math.radians(65))
            else:
                ang = random.uniform(0, math.tau)
            
            spd = random.uniform(180, 420)
            svx = math.cos(ang) * spd
            svy = math.sin(ang) * spd
            life = random.uniform(0.18, 0.32)
            self.particles.append(ImpactSparkStreak(
                cx, cy, svx, svy, life,
                color=self.palette.spark,
                core_color=self.palette.core,
                width=2
            ))
            
        # 3. Detritos e Partículas Especializadas por Elemento
        if self.palette.style == "fire":
            # Brasas quentes e pequenas lufadas de fumaça
            for _ in range(4):
                fx = random.uniform(-100, 100)
                fy = random.uniform(-120, 40)
                self.particles.append(SmokeParticle(cx, cy, fx, fy, 0.45, (45, 45, 45)))
            for _ in range(6):
                ang = random.uniform(0, math.tau)
                spd = random.uniform(80, 200)
                self.particles.append(EnergyStreak(cx, cy, math.cos(ang)*spd, math.sin(ang)*spd, 0.25, self.palette.spark, 8))
        elif self.palette.style == "ice":
            # Cristais de gelo angulares que caem com peso e giram
            for _ in range(8):
                ang = random.uniform(0, math.tau)
                spd = random.uniform(100, 320)
                self.particles.append(IceShardParticle(cx, cy, math.cos(ang)*spd, math.sin(ang)*spd, 0.45, self.palette.spark))
        elif self.palette.style == "ki":
            # Anel secundário de pressão de Ki + faíscas douradas
            self.particles.append(KiRingParticle(cx, cy, 0.35, self.palette.outer_glow))
            for _ in range(6):
                ang = random.uniform(0, math.tau)
                spd = random.uniform(140, 280)
                self.particles.append(EnergyStreak(cx, cy, math.cos(ang)*spd, math.sin(ang)*spd, 0.28, self.palette.core, 12))
        elif self.palette.style == "shadow":
            # Névoa sombria se dissipando
            for _ in range(5):
                ang = random.uniform(0, math.tau)
                spd = random.uniform(40, 120)
                self.particles.append(ShadowMistParticle(cx, cy, math.cos(ang)*spd, math.sin(ang)*spd, 0.5, self.palette.outer_glow))
        elif self.palette.style == "wind":
            # Lâminas de vento cortantes em arco
            for _ in range(3):
                ang = self.impact_angle + random.uniform(-0.8, 0.8)
                spd = random.uniform(120, 240)
                self.particles.append(WindCrescentParticle(cx, cy, math.cos(ang)*spd, math.sin(ang)*spd, 0.25, self.palette.inner_glow, ang))
        elif self.palette.style == "void":
            # Gotas densas de ácido ou sangue com gravidade
            for _ in range(7):
                ang = rebound_angle + random.uniform(-math.radians(70), math.radians(70))
                spd = random.uniform(100, 260)
                self.particles.append(BloodDripParticle(cx, cy, math.cos(ang)*spd, math.sin(ang)*spd, 0.5, self.palette.inner_glow))
        else:
            # Estilo water / arcane: Poeira estelar cintilante
            for _ in range(8):
                ang = random.uniform(0, math.tau)
                spd = random.uniform(80, 240)
                self.particles.append(StardustParticle(cx, cy, math.cos(ang)*spd, math.sin(ang)*spd, 0.5, self.palette.spark))

    def update(self, dt: float, tiles: Optional[List[pygame.FRect]] = None, target: Optional[pygame.FRect] = None):
        if not self.active: return
        
        self.time_alive += dt
        self.anim_manager.update(dt)
        self.particles = [p for p in self.particles if p.update(dt)]
        
        if self.state == "hit":
            hit_anim = self.anim_manager.animations.get("hit")
            anim_done = hit_anim.finished if hit_anim else True
            if anim_done and len(self.particles) == 0:
                self.active = False
            return
            
        self.trajectory.update(self.pos, self.velocity, dt, target)
        self.rect.center = self.pos
        
        # Cauda
        back_x = self.rect.centerx - (self.velocity.normalize().x * self.radius)
        self.tail.add_point(back_x, self.rect.centery, self.velocity.x, self.velocity.y)
        
        # ================================================================
        # EMISSÃO DE PARTÍCULAS CARACTERÍSTICAS (VFX SIGNATURE)
        # ================================================================
        self.spawn_timer += dt
        emission_rate = 0.02
        if self.palette.style == "ki": emission_rate = 0.1 # Ki emite anéis devagar
        
        if self.spawn_timer >= emission_rate:
            self.spawn_timer -= emission_rate
            cx, cy = self.rect.centerx, self.rect.centery
            vx = -self.velocity.x * random.uniform(0.1, 0.3) + random.uniform(-20, 20)
            vy = -self.velocity.y * random.uniform(0.1, 0.3) + random.uniform(-20, 20)
            
            if self.palette.style == "fire":
                # Fumaça Negra e Brasas que caem
                self.particles.append(SmokeParticle(cx, cy, vx*0.5, vy*0.5, 0.6, (40, 40, 40)))
                if random.random() < 0.5:
                    self.particles.append(EnergyStreak(cx, cy, vx, vy, 0.3, self.palette.spark, 5))
                    
            elif self.palette.style == "water":
                # Poeira Estelar Flutuante
                self.particles.append(StardustParticle(cx, cy, vx*0.2, vy*0.2, 0.8, self.palette.spark))
                
            elif self.palette.style == "ice":
                # Estilhaços de Gelo caindo
                self.particles.append(IceShardParticle(cx, cy, vx, vy, 0.5, self.palette.core))
                
            elif self.palette.style == "ki":
                # Anéis Expansivos
                self.particles.append(KiRingParticle(cx, cy, 0.4, self.palette.outer_glow))
                
            elif self.palette.style == "shadow":
                # Névoa Sombria
                self.particles.append(ShadowMistParticle(cx, cy, vx*0.5, vy*0.5, 0.7, self.palette.outer_glow))
                
            elif self.palette.style == "wind":
                # Lâminas Crescentes
                angle = math.atan2(self.velocity.y, self.velocity.x) + random.uniform(-0.5, 0.5)
                self.particles.append(WindCrescentParticle(cx, cy, vx, vy, 0.3, self.palette.inner_glow, angle))
                
            elif self.palette.style == "void":
                # Gotas de Ácido/Sangue dos inimigos
                self.particles.append(BloodDripParticle(cx, cy, vx*0.3, vy*0.3, 0.6, self.palette.inner_glow))
        
        if tiles:
            for tile in tiles:
                if self.rect.colliderect(tile):
                    self.explode()
                    break

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if not self.active: return
        cam_x, cam_y = camera_offset.x, camera_offset.y
        cx, cy = int(self.rect.centerx - cam_x), int(self.rect.centery - cam_y)
        
        if self.state == "fly":
            # 1. Desenha as partículas características (Atrás do Orbe)
            for p in self.particles: p.draw(surface, cam_x, cam_y)
            
            # 2. Desenha a cauda de blocos
            self.tail.draw(surface, cam_x, cam_y)
            
            # 3. Desenha o Núcleo HD por cima de tudo
            surface.blit(self.orb_surf, (cx - self.radius, cy - self.radius))

        elif self.state == "hit":
            # 1. Partículas (anel de choque, faíscas cinéticas e detritos elementares)
            for p in self.particles:
                p.draw(surface, cam_x, cam_y)
            
            # 2. Hit Starburst animado (vfx_hit com blend aditivo)
            hit_anim = self.anim_manager.animations.get("hit")
            if hit_anim and not hit_anim.finished:
                frame = hit_anim.get_current_frame()
                if frame:
                    fw, fh = frame.get_size()
                    surface.blit(frame, (cx - fw // 2, cy - fh // 2), special_flags=pygame.BLEND_RGBA_ADD)
            
            # 3. Instant Hit Glint (Flash de impacto em cruz nos frames 0 a 2)
            if hit_anim and hit_anim.current_frame < 3 and not hit_anim.finished:
                glint_progress = hit_anim.current_frame / 3.0
                glint_sz = int((14 + self.radius * 0.6) * (1.0 - glint_progress))
                if glint_sz > 2:
                    glint_surf = pygame.Surface((glint_sz * 2 + 6, glint_sz * 2 + 6), pygame.SRCALPHA)
                    gc = glint_sz + 3
                    glint_alpha = max(0, min(255, int(255 * (1.0 - glint_progress))))
                    core_col = clamp_color((*self.palette.core[:3], glint_alpha))
                    glow_col = clamp_color((*self.palette.inner_glow[:3], int(glint_alpha * 0.7)))
                    
                    pygame.draw.line(glint_surf, glow_col, (gc - glint_sz, gc), (gc + glint_sz, gc), 3)
                    pygame.draw.line(glint_surf, glow_col, (gc, gc - glint_sz), (gc, gc + glint_sz), 3)
                    pygame.draw.line(glint_surf, core_col, (gc - glint_sz, gc), (gc + glint_sz, gc), 1)
                    pygame.draw.line(glint_surf, core_col, (gc, gc - glint_sz), (gc, gc + glint_sz), 1)
                    pygame.draw.circle(glint_surf, core_col, (gc, gc), max(2, glint_sz // 3))
                    
                    surface.blit(glint_surf, (cx - gc, cy - gc), special_flags=pygame.BLEND_RGBA_ADD)


# ========================================================================================
# 9. ULTIMATE AoE IMPACT FRAMES (POLYMOPRHIC HIGH-DPI ENGINE)
# ========================================================================================
from entities.ultimate_aoe_vfx import (
    UltimateAoE_VFX,
    BaseUltimateAoE_VFX,
    IgnisVolcanicEruptionVFX,
    LunariaSingularityVFX,
    AstraShardBlizzardVFX,
    RyuuKiDomainVFX,
    SamuraiJudgementCutVFX,
    ShinobiShadowDanceVFX,
    ShaiaDivineJudgementVFX
)