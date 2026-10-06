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
        
    if ptype in ("fireball", "fire_spark", "fire_sphere", "arrow_fire"):
        return HighDPIEnergyPalette((255, 255, 255), (255, 220, 80), (255, 100, 0), (220, 50, 0), (100, 10, 0), (255, 150, 50), "fire")
    elif ptype in ("arcane_bolt", "arcane_sphere"):
        return HighDPIEnergyPalette((255, 255, 255), (150, 240, 255), (40, 180, 255), (20, 120, 220), (10, 50, 150), (200, 255, 255), "water")
    elif ptype in ("frost_lance", "frost_orb"):
        return HighDPIEnergyPalette((255, 255, 255), (255, 180, 255), (180, 80, 255), (120, 40, 220), (60, 0, 120), (255, 200, 255), "ice")
    elif ptype == "ki_blast":
        return HighDPIEnergyPalette((255, 255, 255), (255, 240, 100), (255, 180, 20), (200, 120, 0), (100, 50, 0), (255, 255, 150), "ki")
    elif ptype == "shuriken":
        return HighDPIEnergyPalette((230, 220, 255), (160, 100, 255), (100, 40, 200), (60, 0, 150), (30, 0, 80), (180, 120, 255), "shadow")
    elif ptype in ("vacuum_slash", "wind_blade"):
        return HighDPIEnergyPalette((240, 255, 255), (80, 240, 240), (20, 180, 200), (10, 120, 150), (5, 60, 80), (160, 255, 255), "wind")
    elif ptype == "holy_ray":
        return HighDPIEnergyPalette((255, 255, 255), (255, 245, 150), (255, 210, 50), (230, 170, 20), (130, 90, 0), (255, 255, 190), "holy")
    elif ptype == "spear_light":
        return HighDPIEnergyPalette((255, 255, 255), (255, 240, 140), (255, 200, 30), (210, 160, 10), (120, 80, 0), (255, 255, 180), "holy")
    elif ptype in ("solar_plasma", "supernova_orb"):
        return HighDPIEnergyPalette((255, 255, 255), (255, 230, 110), (255, 140, 25), (230, 75, 5), (130, 25, 0), (255, 245, 140), "fire")
    elif ptype in ("arrow_spirit", "arrow_scatter"):
        return HighDPIEnergyPalette((240, 255, 245), (120, 255, 190), (30, 220, 140), (10, 160, 90), (5, 90, 45), (180, 255, 220), "spirit")
    elif ptype == "shadow_shuriken":
        return HighDPIEnergyPalette((255, 220, 240), (230, 70, 140), (160, 20, 90), (100, 10, 60), (45, 0, 30), (255, 140, 190), "shadow")
    elif ptype == "heal_orb":
        return HighDPIEnergyPalette((255, 255, 255), (150, 255, 190), (60, 230, 130), (25, 170, 85), (5, 95, 45), (190, 255, 220), "heal")
    elif ptype == "arrow_fast":
        return HighDPIEnergyPalette((245, 255, 245), (130, 230, 130), (45, 170, 65), (25, 120, 45), (10, 65, 25), (190, 255, 190), "arrow")
    elif ptype == "mana_orb":
        return HighDPIEnergyPalette((255, 255, 255), (130, 240, 255), (70, 150, 255), (35, 80, 220), (15, 35, 130), (190, 245, 255), "mana")
    elif ptype == "earth_spike":
        return HighDPIEnergyPalette((255, 235, 190), (230, 160, 70), (150, 90, 30), (100, 55, 20), (55, 30, 10), (255, 190, 100), "earth")
    else:
        return HighDPIEnergyPalette((255, 255, 255), (255, 240, 150), (255, 200, 80), (200, 150, 40), (100, 80, 10), (255, 255, 200), "fire")


# ========================================================================================
# 3. HIGH-DPI PROCEDURAL ORB FACTORY
# ========================================================================================
class HighDPIOrbFactory:
    _cache: Dict[Tuple, pygame.Surface] = {}

    @classmethod
    def get_orb(cls, radius: int, palette: HighDPIEnergyPalette) -> pygame.Surface:
        key = ("hd_orb", radius, palette.outer_glow, palette.inner_glow, palette.core)
        if key in cls._cache: return cls._cache[key]
        
        scale_hi = 2
        hi_rad = radius * scale_hi
        surf = pygame.Surface((hi_rad * 2, hi_rad * 2), pygame.SRCALPHA)
        cx, cy = hi_rad, hi_rad
        
        # Smooth continuous energy core gradient without hard step boundaries
        for r in range(hi_rad, 0, -1):
            t = r / float(hi_rad)
            if t > 0.85:
                # Soft outermost aura tapering smoothly to zero
                alpha = int(170 * ((1.0 - t) / 0.15) ** 1.8)
                color = (*palette.outer_glow[:3], max(0, min(255, alpha)))
            elif t > 0.48:
                # Smooth blend from outer glow to vibrant inner glow
                blend_t = (t - 0.48) / 0.37
                r_c = int(lerp(palette.inner_glow[0], palette.outer_glow[0], blend_t))
                g_c = int(lerp(palette.inner_glow[1], palette.outer_glow[1], blend_t))
                b_c = int(lerp(palette.inner_glow[2], palette.outer_glow[2], blend_t))
                alpha = int(lerp(250, 170, blend_t))
                color = (r_c, g_c, b_c, alpha)
            elif t > 0.20:
                # Smooth blend from inner glow to hot brilliant core
                blend_t = (t - 0.20) / 0.28
                r_c = int(lerp(palette.core[0], palette.inner_glow[0], blend_t))
                g_c = int(lerp(palette.core[1], palette.inner_glow[1], blend_t))
                b_c = int(lerp(palette.core[2], palette.inner_glow[2], blend_t))
                color = (r_c, g_c, b_c, 255)
            else:
                # Pure incandescent core
                color = (*palette.core[:3], 255)
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
        pts = [(int(pt["x"] - cam_x), int(pt["y"] - cam_y)) for pt in self.history]
        min_x = min(p[0] for p in pts) - 20
        max_x = max(p[0] for p in pts) + 20
        min_y = min(p[1] for p in pts) - 20
        max_y = max(p[1] for p in pts) + 20
        
        w = max(16, max_x - min_x)
        h = max(16, max_y - min_y)
        
        from engine.v3.core.surface_pool import SURFACE_POOL
        trail_surf = SURFACE_POOL.acquire(w, h, pygame.SRCALPHA)
        trail_surf.fill((0, 0, 0, 0))
        
        for i, pt in enumerate(self.history):
            progress = i / len(self.history)
            
            # Comportamento característico do tamanho e onda
            if self.palette.style == "wind":
                # Vento: Cauda afiada, longa, sem ondulação
                size = int(lerp(10.0, 1.0, progress))
                wave = 0
            elif self.palette.style == "arrow":
                # Flecha: Traço aerodinâmico estrito de alta velocidade
                size = int(lerp(6.0, 1.0, progress))
                wave = 0
            elif self.palette.style == "holy":
                # Raio Sagrado: Feixe volumoso brilhante com micro-vibração
                size = int(lerp(12.0, 2.5, progress))
                wave = math.sin(i * 0.4) * 1.5 * progress
            elif self.palette.style == "heal":
                # Cura / Bênção: Traço suave e helicoidal ondulante
                size = int(lerp(10.0, 2.0, progress))
                wave = math.sin(i * 0.8) * 3.2 * progress
            elif self.palette.style == "mana":
                # Éter / Mana: Pulso espiralado e ressonante
                size = int(lerp(11.0, 2.5, progress))
                wave = math.sin(i * 1.1) * 3.8 * progress
            elif self.palette.style == "earth":
                # Rocha / Terra: Blocos pesados e irregulares
                size = int(lerp(9.0, 2.0, progress))
                wave = math.sin(i * 2.2) * 4.2 * progress
            elif self.palette.style == "shadow":
                # Sombra: Blocos falham/glitcham (pula alguns frames)
                if random.random() < 0.15: continue
                size = int(lerp(9.0, 2.0, progress))
                wave = math.sin(i * 1.5) * 4.0 * progress
            elif self.palette.style == "ki":
                # Ki: Pulsos de energia
                pulse = 1.2 if i % 4 == 0 else 0.8
                size = int(lerp(9.0, 3.0, progress) * pulse)
                wave = math.sin(i * 0.5) * 2.0 * progress
            elif self.palette.style == "water":
                # Água/Arcano: Ondulação suave e contínua
                size = int(lerp(10.0, 3.0, progress))
                wave = math.sin(i * 0.6) * 3.5 * progress
            else:
                # Fogo/Void: Caótico, blocos dispersos
                size = int(lerp(9.0, 2.5, progress))
                wave = math.sin(i * 1.2) * 4.5 * progress
                
            if size <= 0: continue
            
            px, py = int(pt["x"] - cam_x) - min_x, int(pt["y"] - cam_y) - min_y
            color = self.palette.tail_base if progress < 0.5 else self.palette.tail_tip
            alpha = int(240 * (1.0 - progress))
            
            rect = pygame.Rect(px - size, py - size + int(wave), size * 2, size * 2)
            pygame.draw.rect(trail_surf, clamp_color((*color[:3], alpha)), rect)

        surface.blit(trail_surf, (min_x, min_y))
        SURFACE_POOL.release(trail_surf)


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

class HolyCrossParticle(BaseParticle):
    """Partículas de Cruz Sagrada (Aurelia). Sobem suavemente, giram e emitem brilho dourado."""
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size", "angle", "rot_speed")
    def __init__(self, x, y, vx, vy, life, color):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.color = color
        self.size = random.uniform(3.0, 6.0)
        self.angle = random.uniform(0, math.pi)
        self.rot_speed = random.uniform(-2.0, 2.0)

    def update(self, dt: float) -> bool:
        self.vy -= 25.0 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.angle += self.rot_speed * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        if self.life <= 0: return
        t = self.life / self.max_life
        alpha = int(255 * ease_out_expo(t))
        dx, dy = int(self.x - cam_x), int(self.y - cam_y)
        sz = int(self.size)
        c = clamp_color((*self.color[:3], alpha))
        cw = clamp_color((255, 255, 255, alpha))
        pygame.draw.line(surface, c, (dx - sz, dy), (dx + sz, dy), 2)
        pygame.draw.line(surface, c, (dx, dy - sz - 1), (dx, dy + sz + 1), 2)
        pygame.draw.circle(surface, cw, (dx, dy), 1)

class RuneSparkParticle(BaseParticle):
    """Runas Etéreas / Losangos de Mana (Zephyr). Flutuam em órbita suave."""
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size", "phase")
    def __init__(self, x, y, vx, vy, life, color):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.color = color
        self.size = random.uniform(2.5, 5.0)
        self.phase = random.uniform(0, math.tau)

    def update(self, dt: float) -> bool:
        self.vx *= 0.90
        self.vy *= 0.90
        self.x += (self.vx + math.sin(self.phase + self.life * 6) * 15) * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        if self.life <= 0: return
        t = self.life / self.max_life
        alpha = int(240 * t)
        dx, dy = int(self.x - cam_x), int(self.y - cam_y)
        sz = int(self.size)
        pts = [(dx, dy - sz), (dx + sz, dy), (dx, dy + sz), (dx - sz, dy)]
        pygame.draw.polygon(surface, clamp_color((*self.color[:3], alpha)), pts)
        pygame.draw.polygon(surface, clamp_color((255, 255, 255, alpha)), pts, 1)

class EarthRubbleParticle(BaseParticle):
    """Estilhaços Rochosos de Basalto (Boran). Caem com gravidade pesada e quicam."""
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size", "angle", "rot_speed")
    def __init__(self, x, y, vx, vy, life, color):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.color = color
        self.size = random.uniform(3.0, 7.0)
        self.angle = random.uniform(0, math.tau)
        self.rot_speed = random.uniform(-8.0, 8.0)

    def update(self, dt: float) -> bool:
        self.vy += 400.0 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.angle += self.rot_speed * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        if self.life <= 0: return
        t = self.life / self.max_life
        alpha = int(255 * min(1.0, t * 1.5))
        dx, dy = self.x - cam_x, self.y - cam_y
        sz = self.size
        pts = [
            (dx + math.cos(self.angle) * sz, dy + math.sin(self.angle) * sz),
            (dx + math.cos(self.angle + 1.8) * (sz * 0.8), dy + math.sin(self.angle + 1.8) * (sz * 0.8)),
            (dx + math.cos(self.angle + 3.6) * (sz * 1.1), dy + math.sin(self.angle + 3.6) * (sz * 1.1)),
            (dx + math.cos(self.angle + 5.0) * (sz * 0.7), dy + math.sin(self.angle + 5.0) * (sz * 0.7)),
        ]
        pygame.draw.polygon(surface, clamp_color((*self.color[:3], alpha)), pts)
        pygame.draw.polygon(surface, clamp_color((60, 40, 20, alpha)), pts, 1)

class LeafWindParticle(BaseParticle):
    """Motes e Folhas Eólicas (Kaelen). Cortam o ar em espirais de alta velocidade."""
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size", "angle")
    def __init__(self, x, y, vx, vy, life, color):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.color = color
        self.size = random.uniform(2.0, 5.0)
        self.angle = random.uniform(0, math.tau)

    def update(self, dt: float) -> bool:
        self.vx *= 0.94
        self.vy += math.sin(self.life * 12.0) * 40.0 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.angle += 6.0 * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        if self.life <= 0: return
        t = self.life / self.max_life
        alpha = int(240 * t)
        dx, dy = self.x - cam_x, self.y - cam_y
        sz = self.size
        p1 = (dx + math.cos(self.angle) * sz * 1.8, dy + math.sin(self.angle) * sz * 1.8)
        p2 = (dx + math.cos(self.angle + math.pi/2) * (sz * 0.6), dy + math.sin(self.angle + math.pi/2) * (sz * 0.6))
        p3 = (dx - math.cos(self.angle) * sz * 1.8, dy - math.sin(self.angle) * sz * 1.8)
        p4 = (dx - math.cos(self.angle + math.pi/2) * (sz * 0.6), dy - math.sin(self.angle + math.pi/2) * (sz * 0.6))
        pygame.draw.polygon(surface, clamp_color((*self.color[:3], alpha)), [p1, p2, p3, p4])


class JadeSpiritParticle(BaseParticle):
    """Fogo Fátuo / Espírito de Jade (Hanzo). Flutua em espiral etérea com rastro suave."""
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size", "phase")
    def __init__(self, x, y, vx, vy, life, color):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.color = color
        self.size = random.uniform(2.5, 5.5)
        self.phase = random.uniform(0, math.tau)

    def update(self, dt: float) -> bool:
        self.vx *= 0.90
        self.vy *= 0.90
        self.vy += math.sin(self.phase + self.life * 8.0) * 35.0 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        if self.life <= 0: return
        t = self.life / self.max_life
        alpha = int(240 * t)
        dx, dy = int(self.x - cam_x), int(self.y - cam_y)
        sz = max(1, int(self.size * t))
        pygame.draw.circle(surface, clamp_color((*self.color[:3], alpha)), (dx, dy), sz + 2)
        pygame.draw.circle(surface, clamp_color((255, 255, 255, alpha)), (dx, dy), max(1, sz // 2))

class SolarFlareParticle(BaseParticle):
    """Brasas de Plasma Solar (Ignatius). Expulsas em micro-erupções incandescentes."""
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size")
    def __init__(self, x, y, vx, vy, life, color):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.color = color
        self.size = random.uniform(3.0, 7.0)

    def update(self, dt: float) -> bool:
        self.vx *= 0.92
        self.vy *= 0.92
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.size = max(1.0, self.size - 4.0 * dt)
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        if self.life <= 0: return
        t = self.life / self.max_life
        alpha = int(255 * (t ** 0.8))
        dx, dy = int(self.x - cam_x), int(self.y - cam_y)
        pygame.draw.circle(surface, clamp_color((*self.color[:3], alpha)), (dx, dy), int(self.size))
        pygame.draw.circle(surface, (255, 255, 220, alpha), (dx, dy), max(1, int(self.size * 0.4)))


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
        self.color = color or ("purple" if is_enemy else "red")
        self.time_alive = 0.0
        self.hit_entities = set()
        
        self.projectile_type = projectile_type or ("purple_sphere" if is_enemy else "fireball")
        
        speed = 380
        if is_enemy:
            self.damage = damage if damage is not None else 12
            speed = 160
        else:
            SPEED_MAP = {
                "arrow_fast": 560,
                "arrow_fire": 480,
                "holy_ray": 520,
                "spear_light": 580,
                "wind_blade": 440,
                "earth_spike": 360,
                "heal_orb": 340,
                "mana_orb": 350,
                "solar_plasma": 440,
                "supernova_orb": 260,
                "arrow_spirit": 620,
                "arrow_scatter": 520,
                "shadow_shuriken": 460,
            }
            speed = SPEED_MAP.get(self.projectile_type, 380)
            DAMAGE_FALLBACK = {
                "arcane_bolt": 5, "arcane_sphere": 45, "fire_spark": 6, "fire_sphere": 48,
                "frost_lance": 5, "frost_orb": 42, "shuriken": 40, "vacuum_slash": 40,
                "ki_blast": 40, "fireball": 40,
                "holy_ray": 48, "heal_orb": 45, "arrow_fast": 58, "arrow_fire": 62,
                "wind_blade": 46, "mana_orb": 40, "earth_spike": 65,
                "spear_light": 55, "solar_plasma": 58, "supernova_orb": 80,
                "arrow_spirit": 60, "arrow_scatter": 28, "shadow_shuriken": 52
            }
            self.damage = damage if damage is not None else DAMAGE_FALLBACK.get(self.projectile_type, 40)
            
        self.pos = pygame.math.Vector2(x, y)
        self.velocity = pygame.math.Vector2(speed if facing_right else -speed, 0)
        
        RADIUS_MAP = {
            "arrow_fast": 10, "arrow_fire": 12, "holy_ray": 12, "spear_light": 13,
            "wind_blade": 12, "earth_spike": 16, "solar_plasma": 14, "supernova_orb": 20,
            "arrow_spirit": 11, "arrow_scatter": 9, "shadow_shuriken": 15
        }
        self.radius = RADIUS_MAP.get(self.projectile_type, 14)
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
        if self.projectile_type in ("arcane_sphere", "fire_sphere", "frost_orb", "boss_fireball", "earth_spike", "supernova_orb"):
            self.impact_scale = 0.95 if self.projectile_type == "supernova_orb" else 0.85
        elif self.projectile_type in ("arcane_bolt", "fire_spark", "frost_lance", "arrow_fast", "arrow_scatter"):
            self.impact_scale = 0.50 if self.projectile_type == "arrow_scatter" else 0.55
        elif self.projectile_type in ("spear_light", "shadow_shuriken", "arrow_spirit"):
            self.impact_scale = 0.80
        else:
            self.impact_scale = 0.70
            
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
        elif self.palette.style == "holy":
            # Cruzes e feixes sagrados dourados
            for _ in range(7):
                self.particles.append(HolyCrossParticle(cx, cy, random.uniform(-60, 60), random.uniform(-100, 30), 0.55, self.palette.core))
            for _ in range(6):
                ang = random.uniform(0, math.tau)
                spd = random.uniform(120, 280)
                self.particles.append(EnergyStreak(cx, cy, math.cos(ang)*spd, math.sin(ang)*spd, 0.28, self.palette.inner_glow, 10))
        elif self.palette.style == "heal":
            # Cruzes de restauração e poeira curativa
            for _ in range(6):
                self.particles.append(HolyCrossParticle(cx, cy, random.uniform(-50, 50), random.uniform(-80, 20), 0.65, self.palette.inner_glow))
            for _ in range(8):
                ang = random.uniform(0, math.tau)
                spd = random.uniform(60, 200)
                self.particles.append(StardustParticle(cx, cy, math.cos(ang)*spd, math.sin(ang)*spd, 0.5, self.palette.spark))
        elif self.palette.style == "arrow":
            # Folhas eólicas e faíscas cinéticas pontiagudas
            for _ in range(5):
                self.particles.append(LeafWindParticle(cx, cy, random.uniform(-80, 80), random.uniform(-60, 60), 0.45, self.palette.inner_glow))
            for _ in range(6):
                ang = rebound_angle + random.uniform(-0.8, 0.8)
                spd = random.uniform(150, 320)
                self.particles.append(EnergyStreak(cx, cy, math.cos(ang)*spd, math.sin(ang)*spd, 0.22, self.palette.core, 9))
        elif self.palette.style == "mana":
            # Runas etéreas e poeira cintilante
            for _ in range(7):
                self.particles.append(RuneSparkParticle(cx, cy, random.uniform(-70, 70), random.uniform(-70, 70), 0.55, self.palette.spark))
            for _ in range(6):
                ang = random.uniform(0, math.tau)
                spd = random.uniform(100, 260)
                self.particles.append(EnergyStreak(cx, cy, math.cos(ang)*spd, math.sin(ang)*spd, 0.25, self.palette.inner_glow, 8))
        elif self.palette.style == "earth":
            # Estilhaços de basalto pesados e fumaça de poeira
            for _ in range(8):
                self.particles.append(EarthRubbleParticle(cx, cy, random.uniform(-140, 140), random.uniform(-260, -40), 0.65, self.palette.inner_glow))
            for _ in range(4):
                self.particles.append(SmokeParticle(cx, cy, random.uniform(-60, 60), random.uniform(-60, 10), 0.5, (100, 75, 45)))
        elif self.palette.style == "spirit":
            # Chamas fátuas e espíritos de jade
            for _ in range(7):
                ang = rebound_angle + random.uniform(-0.9, 0.9)
                spd = random.uniform(120, 280)
                self.particles.append(JadeSpiritParticle(cx, cy, math.cos(ang)*spd, math.sin(ang)*spd, 0.45, self.palette.inner_glow))
            for _ in range(5):
                self.particles.append(StardustParticle(cx, cy, random.uniform(-80, 80), random.uniform(-80, 80), 0.5, self.palette.spark))
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
                if self.projectile_type in ("solar_plasma", "supernova_orb"):
                    self.particles.append(SolarFlareParticle(cx, cy, vx*0.4, vy*0.4, 0.4, self.palette.spark))
                else:
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
                
            elif self.palette.style == "holy":
                # Cruzes Sagradas Luminosas
                self.particles.append(HolyCrossParticle(cx, cy, vx*0.15, vy*0.15, 0.55, self.palette.core))
                
            elif self.palette.style == "heal":
                # Bênção / Poeira de Cura
                self.particles.append(HolyCrossParticle(cx, cy, vx*0.1, vy*0.1, 0.6, self.palette.inner_glow))
                
            elif self.palette.style == "arrow":
                # Motes de Vento e Folhas
                self.particles.append(LeafWindParticle(cx, cy, vx*0.25, vy*0.25, 0.4, self.palette.inner_glow))

            elif self.palette.style == "spirit":
                # Fogo Fátuo / Espíritos de Jade
                self.particles.append(JadeSpiritParticle(cx, cy, vx*0.2, vy*0.2, 0.45, self.palette.inner_glow))
                if random.random() < 0.4:
                    self.particles.append(EnergyStreak(cx, cy, vx, vy, 0.22, self.palette.spark, 7))
                
            elif self.palette.style == "mana":
                # Runas de Éter
                self.particles.append(RuneSparkParticle(cx, cy, vx*0.2, vy*0.2, 0.5, self.palette.spark))
                
            elif self.palette.style == "earth":
                # Detritos de Rocha e Poeira
                self.particles.append(EarthRubbleParticle(cx, cy, vx*0.25, vy*0.25, 0.45, self.palette.inner_glow))
                
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
            
            if self.projectile_type in ("arrow_fast", "arrow_fire"):
                self._draw_arrow(surface, cx, cy)
            elif self.projectile_type in ("wind_blade", "vacuum_slash"):
                self._draw_crescent_blade(surface, cx, cy)
            elif self.projectile_type == "holy_ray":
                self._draw_holy_ray(surface, cx, cy)
            elif self.projectile_type == "spear_light":
                self._draw_spear_light(surface, cx, cy)
            elif self.projectile_type in ("solar_plasma", "supernova_orb"):
                self._draw_solar_plasma(surface, cx, cy)
            elif self.projectile_type in ("arrow_spirit", "arrow_scatter"):
                self._draw_arrow_spirit(surface, cx, cy)
            elif self.projectile_type == "shadow_shuriken":
                self._draw_shadow_shuriken(surface, cx, cy)
            elif self.projectile_type == "earth_spike":
                self._draw_earth_spike(surface, cx, cy)
            elif self.projectile_type in ("heal_orb", "mana_orb"):
                self._draw_orb_with_runes(surface, cx, cy)
            else:
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

    def _draw_arrow(self, surface: pygame.Surface, cx: int, cy: int):
        """Desenha uma flecha aerodinâmica afiada com ponta penetrante e aletas de penas."""
        dir_mult = 1.0 if self.facing_right else -1.0
        length = 34
        half_l = length // 2
        
        # 1. Haste de madeira reforçada / energia
        shaft_start = (cx - int(dir_mult * half_l), cy)
        shaft_end = (cx + int(dir_mult * half_l), cy)
        pygame.draw.line(surface, self.palette.tail_tip, shaft_start, shaft_end, 3)
        pygame.draw.line(surface, self.palette.core, shaft_start, shaft_end, 1)
        
        # 2. Ponta afiada em ponta de lança
        tip_x = cx + int(dir_mult * (half_l + 4))
        tip_base_x = cx + int(dir_mult * (half_l - 6))
        tip_pts = [
            (tip_x, cy),
            (tip_base_x, cy - 5),
            (tip_base_x + int(dir_mult * 2), cy),
            (tip_base_x, cy + 5)
        ]
        pygame.draw.polygon(surface, self.palette.core, tip_pts)
        pygame.draw.polygon(surface, self.palette.inner_glow, tip_pts, 1)
        
        # 3. Penas traseiras (Fletching)
        rear_x = cx - int(dir_mult * (half_l - 4))
        tail_x = cx - int(dir_mult * (half_l + 2))
        fletch_color = self.palette.spark
        pygame.draw.line(surface, fletch_color, (rear_x, cy - 4), (tail_x, cy - 8), 2)
        pygame.draw.line(surface, fletch_color, (rear_x, cy + 4), (tail_x, cy + 8), 2)
        
        # 4. Aura Elemental (Chama envolvente ou aerodinâmica de vento)
        if self.projectile_type == "arrow_fire":
            glow_surf = pygame.Surface((44, 24), pygame.SRCALPHA)
            pygame.draw.ellipse(glow_surf, (255, 120, 20, 140), (2, 2, 40, 20))
            pygame.draw.ellipse(glow_surf, (255, 240, 100, 210), (8, 6, 28, 12))
            surface.blit(glow_surf, (cx - 22, cy - 12), special_flags=pygame.BLEND_RGBA_ADD)
        else:
            glow_surf = pygame.Surface((40, 18), pygame.SRCALPHA)
            pygame.draw.ellipse(glow_surf, (*self.palette.inner_glow[:3], 120), (2, 2, 36, 14))
            surface.blit(glow_surf, (cx - 20, cy - 9), special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_crescent_blade(self, surface: pygame.Surface, cx: int, cy: int):
        """Desenha foice sônica de vácuo cortante em arco giratório de alta pressão."""
        rot = (self.time_alive * 900.0) % 360.0
        rad = self.radius + 4
        blade_surf = pygame.Surface((rad * 2 + 4, rad * 2 + 4), pygame.SRCALPHA)
        bc = rad + 2
        arc_rect = pygame.Rect(bc - rad, bc - rad, rad * 2, rad * 2)
        pygame.draw.arc(blade_surf, self.palette.inner_glow, arc_rect, 0.4, 2.7, 4)
        pygame.draw.arc(blade_surf, self.palette.core, arc_rect, 0.6, 2.5, 2)
        rotated = pygame.transform.rotate(blade_surf, rot if self.facing_right else -rot)
        rw, rh = rotated.get_size()
        surface.blit(rotated, (cx - rw // 2, cy - rh // 2), special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_holy_ray(self, surface: pygame.Surface, cx: int, cy: int):
        """Desenha feixe solar concentrado perfurante (Lança de Fótons)."""
        w, h = 48, 16
        ray_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(ray_surf, (*self.palette.outer_glow[:3], 130), (0, 0, w, h))
        pygame.draw.ellipse(ray_surf, (*self.palette.inner_glow[:3], 210), (4, 3, w - 8, h - 6))
        pygame.draw.ellipse(ray_surf, (255, 255, 255, 255), (8, 6, w - 16, 4))
        glint_x = (w - 6) if self.facing_right else 6
        pygame.draw.circle(ray_surf, (255, 255, 255, 255), (glint_x, h // 2), 3)
        surface.blit(ray_surf, (cx - w // 2, cy - h // 2), special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_earth_spike(self, surface: pygame.Surface, cx: int, cy: int):
        """Desenha estalagmite pontiaguda de pedra/basalto rachado."""
        dir_mult = 1.0 if self.facing_right else -1.0
        pts_top = [
            (cx + int(dir_mult * 16), cy),
            (cx - int(dir_mult * 12), cy - 10),
            (cx - int(dir_mult * 6), cy),
        ]
        pts_bot = [
            (cx + int(dir_mult * 16), cy),
            (cx - int(dir_mult * 6), cy),
            (cx - int(dir_mult * 12), cy + 10),
        ]
        pygame.draw.polygon(surface, self.palette.inner_glow, pts_top)
        pygame.draw.polygon(surface, self.palette.outer_glow, pts_bot)
        pygame.draw.polygon(surface, (40, 25, 10), pts_top, 1)
        pygame.draw.polygon(surface, (40, 25, 10), pts_bot, 1)
        pygame.draw.line(surface, self.palette.core, (cx - int(dir_mult * 8), cy), (cx + int(dir_mult * 12), cy), 2)

    def _draw_orb_with_runes(self, surface: pygame.Surface, cx: int, cy: int):
        """Desenha o orbe místico com satélites rúnicos em órbita 3D."""
        surface.blit(self.orb_surf, (cx - self.radius, cy - self.radius))
        is_heal = (self.projectile_type == "heal_orb")
        for i in range(3):
            ang = self.time_alive * 6.0 + i * (math.tau / 3.0)
            orb_r = self.radius + 6.0
            ox = cx + int(math.cos(ang) * orb_r)
            oy = cy + int(math.sin(ang) * (orb_r * 0.45))
            if is_heal:
                pygame.draw.line(surface, self.palette.core, (ox - 3, oy), (ox + 3, oy), 2)
                pygame.draw.line(surface, self.palette.core, (ox, oy - 3), (ox, oy + 3), 2)
            else:
                r_pts = [(ox, oy - 3), (ox + 3, oy), (ox, oy + 3), (ox - 3, oy)]
                pygame.draw.polygon(surface, self.palette.core, r_pts)
                pygame.draw.polygon(surface, self.palette.spark, r_pts, 1)

    def _draw_spear_light(self, surface: pygame.Surface, cx: int, cy: int):
        """Desenha lança sagrada de luz penetrante (Galahad) com cruzeta radiante e brilho dourado."""
        dir_mult = 1.0 if self.facing_right else -1.0
        w, h = 42, 18
        spear_surf = pygame.Surface((w, h), pygame.SRCALPHA)
        scy = h // 2
        p_tip = (w - 2, scy) if self.facing_right else (2, scy)
        p_base = (4, scy) if self.facing_right else (w - 4, scy)
        pygame.draw.line(spear_surf, self.palette.outer_glow, p_base, p_tip, 6)
        pygame.draw.line(spear_surf, self.palette.inner_glow, p_base, p_tip, 3)
        pygame.draw.line(spear_surf, (255, 255, 255), p_base, p_tip, 1)
        guard_x = int(w * 0.45) if self.facing_right else int(w * 0.55)
        pygame.draw.line(spear_surf, self.palette.inner_glow, (guard_x, 2), (guard_x, h - 2), 3)
        pygame.draw.line(spear_surf, (255, 255, 255), (guard_x, 4), (guard_x, h - 4), 1)
        tip_pts = [
            p_tip,
            (guard_x + int(dir_mult * 6), scy - 5),
            (guard_x + int(dir_mult * 4), scy),
            (guard_x + int(dir_mult * 6), scy + 5)
        ]
        pygame.draw.polygon(spear_surf, self.palette.core, tip_pts)
        surface.blit(spear_surf, (cx - w // 2, cy - h // 2), special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_solar_plasma(self, surface: pygame.Surface, cx: int, cy: int):
        """Desenha orbe de plasma solar com proeminências e corona em rotação (Ignatius)."""
        surface.blit(self.orb_surf, (cx - self.radius, cy - self.radius))
        rot = self.time_alive * 8.0
        rad = self.radius + 3
        flare_surf = pygame.Surface((rad * 2 + 8, rad * 2 + 8), pygame.SRCALPHA)
        fc = rad + 4
        for i in range(4):
            ang = rot + i * (math.pi / 2.0)
            fx = fc + int(math.cos(ang) * (rad - 1))
            fy = fc + int(math.sin(ang) * (rad - 1))
            pygame.draw.circle(flare_surf, self.palette.inner_glow, (fx, fy), max(2, rad // 4))
            pygame.draw.circle(flare_surf, (255, 255, 220), (fx, fy), max(1, rad // 8))
        surface.blit(flare_surf, (cx - fc, cy - fc), special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_arrow_spirit(self, surface: pygame.Surface, cx: int, cy: int):
        """Desenha flecha espiritual de jade com rastro espectral fluido (Hanzo)."""
        dir_mult = 1.0 if self.facing_right else -1.0
        length = 32 if self.projectile_type == "arrow_spirit" else 22
        half_l = length // 2
        p1 = (cx - int(dir_mult * half_l), cy)
        p2 = (cx + int(dir_mult * half_l), cy)
        pygame.draw.line(surface, self.palette.outer_glow, p1, p2, 4)
        pygame.draw.line(surface, self.palette.inner_glow, p1, p2, 2)
        pygame.draw.line(surface, (255, 255, 255), p1, p2, 1)
        tip_x = cx + int(dir_mult * (half_l + 3))
        base_x = cx + int(dir_mult * (half_l - 5))
        pts = [(tip_x, cy), (base_x, cy - 4), (base_x + int(dir_mult * 2), cy), (base_x, cy + 4)]
        pygame.draw.polygon(surface, self.palette.core, pts)
        pygame.draw.polygon(surface, self.palette.inner_glow, pts, 1)
        wave_surf = pygame.Surface((36, 16), pygame.SRCALPHA)
        pygame.draw.ellipse(wave_surf, (*self.palette.inner_glow[:3], 130), (2, 2, 32, 12))
        surface.blit(wave_surf, (cx - 18, cy - 8), special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_shadow_shuriken(self, surface: pygame.Surface, cx: int, cy: int):
        """Desenha shuriken sombrio quadripolar em rotação ultrarrápida com bordas carmesins (Ayame)."""
        rot = (self.time_alive * 1200.0) % 360.0
        sz = self.radius + 5
        sh_surf = pygame.Surface((sz * 2 + 4, sz * 2 + 4), pygame.SRCALPHA)
        sc = sz + 2
        blade_pts = []
        for i in range(8):
            ang = (i * math.pi / 4.0)
            dist = sz if i % 2 == 0 else sz * 0.32
            blade_pts.append((sc + math.cos(ang) * dist, sc + math.sin(ang) * dist))
        pygame.draw.polygon(sh_surf, (30, 5, 20), blade_pts)
        pygame.draw.polygon(sh_surf, self.palette.inner_glow, blade_pts, 2)
        pygame.draw.circle(sh_surf, self.palette.core, (sc, sc), max(2, sz // 4))
        pygame.draw.circle(sh_surf, (15, 0, 10), (sc, sc), max(1, sz // 6))
        rotated = pygame.transform.rotate(sh_surf, rot)
        rw, rh = rotated.get_size()
        surface.blit(rotated, (cx - rw // 2, cy - rh // 2))

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
    ShaiaDivineJudgementVFX,
    AureliaSanctuaryAoE_VFX,
    KaelenArrowRainAoE_VFX,
    ZephyrEtherVortexAoE_VFX,
    BoranSeismicWaveAoE_VFX
)