import pygame
import math
import random
from config.settings import SETTINGS

class LightSource:
    """A dynamic point light source with radial quadratic falloff."""
    def __init__(self, x: float, y: float, radius: int, color: tuple, intensity: float = 1.0, flicker: bool = False):
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.intensity = intensity
        self.flicker = flicker
        self.flicker_phase = random.uniform(0, 6.28)

class AmbientParticle:
    """Drifting atmospheric particle (leaf in forest, ember in dungeon)."""
    def __init__(self, w: int, h: int, theme: str):
        self.theme = theme
        self.x = random.uniform(0, w)
        self.y = random.uniform(0, h)
        
        if theme == "forest":
            # Leaf particle
            self.vx = random.uniform(25.0, 55.0)
            self.vy = random.uniform(15.0, 40.0)
            self.size = random.uniform(2.0, 4.5)
            self.color = random.choice([
                (120, 190, 40),
                (160, 210, 60),
                (210, 180, 50),
                (180, 140, 40)
            ])
            self.alpha = random.randint(140, 220)
            self.sway_speed = random.uniform(2.0, 4.0)
            self.sway_amp = random.uniform(20.0, 45.0)
        else:
            # Dungeon / Throne ember
            self.vx = random.uniform(-10.0, 10.0)
            self.vy = random.uniform(-25.0, -50.0)
            self.size = random.uniform(1.2, 3.0)
            self.color = random.choice([
                (255, 140, 40),
                (255, 80, 30),
                (210, 50, 40),
                (180, 110, 255)
            ])
            self.alpha = random.randint(120, 200)
            self.sway_speed = random.uniform(1.5, 3.0)
            self.sway_amp = random.uniform(10.0, 25.0)
            
        self.phase = random.uniform(0, 6.28)

    def update(self, dt: float, w: int, h: int):
        self.phase += dt * self.sway_speed
        sway = math.sin(self.phase) * self.sway_amp * dt
        self.x += (self.vx + sway) * dt
        self.y += self.vy * dt
        
        # Wrap around screen bounds
        if self.y > h + 10:
            self.y = -10
            self.x = random.uniform(0, w)
        elif self.y < -10:
            self.y = h + 10
            self.x = random.uniform(0, w)
            
        if self.x > w + 20:
            self.x = -10
        elif self.x < -20:
            self.x = w + 10

    def draw(self, surface: pygame.Surface, camera_offset_x: float = 0):
        draw_x = self.x - camera_offset_x * 0.7
        # Repeat wrap if needed
        p_surf = pygame.Surface((int(self.size * 2), int(self.size * 2)), pygame.SRCALPHA)
        pygame.draw.circle(p_surf, (*self.color, self.alpha), (int(self.size), int(self.size)), int(self.size))
        surface.blit(p_surf, (draw_x - self.size, self.y - self.size))

class LightingEngine:
    """Advanced lighting engine featuring Light Ray Tracing (God Rays), Dynamic Point Lights, and Atmospheric Particles."""
    _RADIAL_CACHE = {}

    def __init__(self, theme: str = "forest"):
        self.theme = theme
        self.time = 0.0
        
        # Light ray tracing shafts (God Rays)
        self.num_rays = 6
        self.ray_angles = []
        self.ray_widths = []
        self.ray_alphas = []
        
        for i in range(self.num_rays):
            self.ray_widths.append(random.uniform(35.0, 75.0))
            self.ray_alphas.append(random.uniform(18.0, 38.0))
            
        # Pre-build Vignette surface
        self.vignette = pygame.Surface((SETTINGS.GAME_WIDTH, SETTINGS.GAME_HEIGHT), pygame.SRCALPHA)
        gw, gh = SETTINGS.GAME_WIDTH, SETTINGS.GAME_HEIGHT
        cx, cy = gw // 2, gh // 2
        for r in range(max(gw, gh), 0, -12):
            norm = r / max(gw, gh)
            if norm > 0.65:
                a = int(140 * ((norm - 0.65) / 0.35)**1.5)
                pygame.draw.circle(self.vignette, (0, 0, 0, a), (cx, cy), r, width=12)
                
        # Ambient Particles
        self.particles: list[AmbientParticle] = []
        for _ in range(35):
            self.particles.append(AmbientParticle(SETTINGS.GAME_WIDTH * 3, SETTINGS.GAME_HEIGHT, self.theme))
            
    @classmethod
    def get_radial_light_surface(cls, radius: int, color: tuple) -> pygame.Surface:
        key = (radius, color)
        if key not in cls._RADIAL_CACHE:
            surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            r, g, b = color[:3]
            for step in range(radius, 0, -2):
                fraction = 1.0 - (step / radius)
                alpha = int(255 * (fraction ** 2.2))
                pygame.draw.circle(surf, (r, g, b, alpha), (radius, radius), step)
            cls._RADIAL_CACHE[key] = surf
        return cls._RADIAL_CACHE[key]

    def update(self, dt: float):
        self.time += dt
        
        if SETTINGS.AMBIENT_PARTICLES:
            for p in self.particles:
                p.update(dt, SETTINGS.GAME_WIDTH * 3, SETTINGS.GAME_HEIGHT)

    def draw_god_rays(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        """God rays removed per user request to improve visual clarity and interaction."""
        return

    def draw_point_lights(self, surface: pygame.Surface, lights: list[LightSource], camera_offset: pygame.math.Vector2):
        """Draws dynamic point lights (fireballs, player aura, torches) with soft radiance."""
        if not SETTINGS.DYNAMIC_LIGHTS or not lights:
            return
            
        light_layer = pygame.Surface((SETTINGS.GAME_WIDTH, SETTINGS.GAME_HEIGHT), pygame.SRCALPHA)
        
        for l in lights:
            rad = l.radius
            if l.flicker:
                flicker_scale = 0.92 + 0.08 * math.sin(self.time * 8.0 + l.flicker_phase)
                rad = int(rad * flicker_scale)
                
            light_surf = self.get_radial_light_surface(rad, l.color)
            screen_x = l.x - camera_offset.x - rad
            screen_y = l.y - camera_offset.y - rad
            
            # Fast offscreen culling
            if -rad * 2 <= screen_x <= SETTINGS.GAME_WIDTH and -rad * 2 <= screen_y <= SETTINGS.GAME_HEIGHT:
                temp = light_surf.copy()
                if l.intensity < 1.0:
                    temp.set_alpha(int(255 * l.intensity))
                light_layer.blit(temp, (screen_x, screen_y))
                
        # Blit with standard alpha blend
        surface.blit(light_layer, (0, 0))

    def draw_ambient_particles(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        """Draws ambient windblown leaves or floating embers."""
        if not SETTINGS.AMBIENT_PARTICLES:
            return
        for p in self.particles:
            p.draw(surface, camera_offset.x)

    def draw_vignette(self, surface: pygame.Surface):
        """Draws cinematic lens vignette for added visual depth."""
        if SETTINGS.VIGNETTE_ENABLED:
            surface.blit(self.vignette, (0, 0))
