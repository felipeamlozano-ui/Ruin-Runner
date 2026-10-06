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

# Ruin Engine V3.0 Subsystem Integration
from engine.v3.lighting.raycasting2d import LightRayCaster
from engine.v3.lighting.shadows import ShadowRenderer
from engine.v3.lighting.volumetric import VolumetricLightingEngine
from engine.v3.lighting.ambient_occlusion import AmbientOcclusion2D
from engine.v3.postfx.color_grading import ColorGradingEngine

class LightingEngine:
    """Advanced lighting engine featuring Light Ray Tracing (God Rays), Dynamic Point Lights, Atmospheric Particles, and Color Grading."""
    _RADIAL_CACHE = {}

    def __init__(self, theme: str = "forest"):
        self.theme = theme
        self.time = 0.0
        
        # Ruin Engine V3.0 Subsystems
        self.ray_caster = LightRayCaster()
        self.shadow_renderer = ShadowRenderer()
        self.volumetric = VolumetricLightingEngine(SETTINGS.GAME_WIDTH, SETTINGS.GAME_HEIGHT)
        self.ao = AmbientOcclusion2D()
        self.color_grading = ColorGradingEngine()
        
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
    def get_radial_light_surface(cls, radius: int, color: tuple, intensity: float = 1.0) -> pygame.Surface:
        radius = max(8, int(radius))
        q_intensity = max(0.1, min(1.0, round(intensity, 1)))
        cr, cg, cb = int(color[0]), int(color[1]), int(color[2])
        key = (radius, (cr, cg, cb), q_intensity)
        if key not in cls._RADIAL_CACHE:
            import numpy as np
            size = radius * 2
            y, x = np.ogrid[-radius:radius, -radius:radius]
            dist_sq = (x * x + y * y).astype(np.float32) / float(radius * radius)
            mask = dist_sq < 1.0
            
            # Smooth cubic polynomial falloff: (1 - dist_sq)^2.5 with zero slope at edge
            falloff = np.zeros_like(dist_sq)
            falloff[mask] = np.power(1.0 - dist_sq[mask], 2.5) * q_intensity
            
            rgb = np.zeros((size, size, 3), dtype=np.uint8)
            rgb[..., 0] = np.clip(cr * falloff, 0, 255).astype(np.uint8)
            rgb[..., 1] = np.clip(cg * falloff, 0, 255).astype(np.uint8)
            rgb[..., 2] = np.clip(cb * falloff, 0, 255).astype(np.uint8)
            
            surf = pygame.surfarray.make_surface(rgb)
            cls._RADIAL_CACHE[key] = surf
        return cls._RADIAL_CACHE[key]

    def update(self, dt: float):
        self.time += dt
        self.volumetric.update(dt)
        
        if SETTINGS.AMBIENT_PARTICLES:
            for p in self.particles:
                p.update(dt, SETTINGS.GAME_WIDTH * 3, SETTINGS.GAME_HEIGHT)

    def draw_god_rays(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        """God rays removed per user request (commit 57c80d3) to guarantee visual clarity and prevent blinding searchlights."""
        return

    def draw_shadows(self, surface: pygame.Surface, lights: list[LightSource], occluders: list, camera_offset: pygame.math.Vector2):
        """Draws dynamic 2D shadow polygons from occluders using Half-Resolution Accumulation Buffer."""
        if not SETTINGS.RUIN_ENGINE_V3 or SETTINGS.SHADOWS_2D == "Desativado" or not lights or not occluders:
            return
            
        gw = surface.get_width()
        gh = surface.get_height()
        cam_x, cam_y = camera_offset.x, camera_offset.y

        # 1. Frustum Culling on lights: filter lights that actually illuminate the visible viewport
        visible_lights = []
        for l in lights:
            rad = l.radius
            screen_lx = l.x - cam_x
            screen_ly = l.y - cam_y
            if -rad <= screen_lx <= gw + rad and -rad <= screen_ly <= gh + rad:
                visible_lights.append(l)

        if not visible_lights:
            return

        visible_lights = visible_lights[:6] # Cap to nearest 6 visible lights

        # 2. Half-Resolution Accumulation Buffer (256x192 for 512x384)
        # Reduces polygon fill operations by 75% while bilinear smoothscale naturally anti-aliases penumbras!
        half_w = max(64, gw // 2)
        half_h = max(48, gh // 2)
        from engine.v3.core.surface_pool import SURFACE_POOL
        half_mask = SURFACE_POOL.acquire(half_w, half_h, pygame.SRCALPHA)
        half_mask.fill((0, 0, 0, 0))

        scale_factor = 0.5
        half_cam = pygame.math.Vector2(cam_x * scale_factor, cam_y * scale_factor)
        half_occluders = [
            (x1 * scale_factor, y1 * scale_factor, x2 * scale_factor, y2 * scale_factor)
            for x1, y1, x2, y2 in occluders
        ]

        soft_rays = 2 if SETTINGS.SHADOWS_2D == "Suaves" else 1

        for l in visible_lights:
            hlx = l.x * scale_factor
            hly = l.y * scale_factor
            hradius = l.radius * scale_factor
            self.shadow_renderer.render_shadow_mask(
                half_w, half_h,
                hlx, hly, hradius, half_occluders, half_cam,
                soft_rays=soft_rays,
                target_surface=half_mask
            )

        # 3. Single upscale with smooth bilinear filtering (naturally softens all shadow penumbras!)
        full_mask = pygame.transform.smoothscale(half_mask, (gw, gh))
        surface.blit(full_mask, (0, 0))
        SURFACE_POOL.release(half_mask)

    def draw_baked_lightmap(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        """Ultra-lightweight pre-baked ambient stage lightmap (0 GPU ray-casting overhead)."""
        if getattr(self, "_baked_lightmap", None) is None:
            bw, bh = SETTINGS.GAME_WIDTH, SETTINGS.GAME_HEIGHT
            self._baked_lightmap = pygame.Surface((bw, bh))
            if self.theme == "forest":
                self._baked_lightmap.fill((180, 190, 180))
            elif self.theme in ("blood_moon", "throne"):
                self._baked_lightmap.fill((185, 175, 175))
            else:
                self._baked_lightmap.fill((175, 180, 190))
        surface.blit(self._baked_lightmap, (0, 0), special_flags=pygame.BLEND_MULT)

    def draw_point_lights(self, surface: pygame.Surface, lights: list[LightSource], camera_offset: pygame.math.Vector2):
        """Draws dynamic 2D lighting using a dedicated Multiplicative Lightmap.
        Prevents burning out and overexposing diffuse textures while creating rich,
        atmospheric depth (Dead Cells / Hollow Knight standard).
        """
        if not SETTINGS.DYNAMIC_LIGHTS or not lights:
            self.draw_baked_lightmap(surface, camera_offset)
            return
            
        gw = surface.get_width()
        gh = surface.get_height()
        cam_x, cam_y = camera_offset.x, camera_offset.y

        # 1. Allocate / reuse Lightmap buffer matching current surface dimensions
        if getattr(self, "_lightmap_surf", None) is None or self._lightmap_surf.get_size() != (gw, gh):
            self._lightmap_surf = pygame.Surface((gw, gh))

        # 2. Base atmospheric ambient lighting (deep moody darkness without bleaching or crushing blacks)
        if self.theme == "forest":
            ambient_color = (128, 138, 128)
        elif self.theme in ("blood_moon", "throne"):
            ambient_color = (132, 118, 122)
        elif self.theme in ("crypt", "cripta"):
            ambient_color = (115, 120, 135)
        else:
            ambient_color = (122, 128, 140)

        self._lightmap_surf.fill(ambient_color)

        # 3. Frustum cull and accumulate lights onto lightmap with BLEND_ADD
        culled_count = 0
        emissive_cores = []
        for l in lights:
            rad = int(l.radius)
            screen_x = int(l.x - cam_x - rad)
            screen_y = int(l.y - cam_y - rad)
            
            # Fast offscreen culling with margin
            if -rad * 2 <= screen_x <= gw and -rad * 2 <= screen_y <= gh:
                intensity = getattr(l, "intensity", 1.0)
                light_surf = self.get_radial_light_surface(rad, l.color, intensity * 0.65)
                self._lightmap_surf.blit(light_surf, (screen_x, screen_y), special_flags=pygame.BLEND_ADD)
                
                # Register lantern core for a tiny, soft specular emissive highlight
                if intensity > 0.45:
                    emissive_cores.append((screen_x + rad, screen_y + rad, l.color))

                culled_count += 1
                if culled_count >= 16:
                    break

        # 4. Multiply Lightmap over the scene diffuse (scene * lightmap)
        surface.blit(self._lightmap_surf, (0, 0), special_flags=pygame.BLEND_MULT)

        # 5. Very subtle soft additive core (soft glow on lantern bulb, radius 10px)
        for cx, cy, col in emissive_cores:
            core_surf = self.get_radial_light_surface(10, col, 0.10)
            surface.blit(core_surf, (cx - 10, cy - 10), special_flags=pygame.BLEND_ADD)


    def apply_color_grading(self, surface: pygame.Surface, theme: str = None):
        """Applies cinematic stage Look-Up Table (LUT) color grading."""
        if not getattr(SETTINGS, "RUIN_ENGINE_V3", True):
            return
        stage_theme = theme or self.theme
        self.color_grading.apply_grading(surface, theme=stage_theme)

    def draw_ambient_particles(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        """Draws ambient windblown leaves or floating embers."""
        if not SETTINGS.AMBIENT_PARTICLES:
            return
        for p in self.particles:
            p.draw(surface, camera_offset.x)

    def draw_vignette(self, surface: pygame.Surface):
        """Draws cinematic lens vignette for added visual depth."""
        if not SETTINGS.VIGNETTE_ENABLED:
            return
        gw, gh = surface.get_size()
        if getattr(self, "_vignette_cache", None) is None or self._vignette_cache.get_size() != (gw, gh):
            self._vignette_cache = pygame.Surface((gw, gh), pygame.SRCALPHA)
            cx, cy = gw // 2, gh // 2
            max_r = max(gw, gh)
            for r in range(max_r, 0, -12):
                norm = r / max_r
                if norm > 0.65:
                    a = int(115 * ((norm - 0.65) / 0.35)**1.5)
                    pygame.draw.circle(self._vignette_cache, (0, 0, 0, a), (cx, cy), r, width=12)
        surface.blit(self._vignette_cache, (0, 0))

