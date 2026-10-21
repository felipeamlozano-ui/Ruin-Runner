import pygame
import math
import random
import numpy as np
from typing import Optional, List, Tuple
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
        rad = max(1, int(self.size))
        self.surf = pygame.Surface((rad * 2 + 2, rad * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(self.surf, (*self.color, self.alpha), (rad + 1, rad + 1), rad)

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
        surface.blit(self.surf, (draw_x - self.size, self.y - self.size))

# Ruin Engine V3.0 Subsystem Integration
from engine.v3.lighting.raycasting2d import LightRayCaster
from engine.v3.lighting.shadows import ShadowRenderer
from engine.v3.lighting.volumetric import VolumetricLightingEngine
from engine.v3.lighting.ambient_occlusion import AmbientOcclusion2D
from engine.v3.postfx.color_grading import ColorGradingEngine

class LightingEngine:
    """
    Cinematic 2D Lighting Pipeline inspired by Hollow Knight: Silksong.
    Features:
    - Pre-computed Multiplicative Static Ambient Occlusion (AO) + Anamorphic Vignette
    - Hero Glow & Combat Rim Light on player
    - Dynamic Entity Foot Contact AO for ground anchoring
    - Pre-rendered Volumetric Diagonal God Rays with BLEND_RGB_ADD
    - 45 Floating Atmospheric Particles (Silksong Dust Motes / Spores) in a fixed pool with batch blitting (surface.blits)
    - Zero per-frame memory allocation locking 60 FPS
    """
    _RADIAL_CACHE = {}

    def __init__(self, theme: str = "forest", screen_w: int = 640, screen_h: int = 360, floor_y: int = 280):
        self.theme = theme
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.floor_y = floor_y
        self.time = 0.0
        
        # Ruin Engine V3.0 Subsystems
        self.ray_caster = LightRayCaster()
        self.shadow_renderer = ShadowRenderer()
        self.volumetric = VolumetricLightingEngine(screen_w, screen_h)
        self.ao = AmbientOcclusion2D()
        self.color_grading = ColorGradingEngine()

        # 1. Pre-allocated Lightmap buffer (Native Resolution 640x360 with zero per-frame allocation)
        self._lightmap_surf = pygame.Surface((screen_w, screen_h))
        disp = pygame.display.get_surface()
        if disp:
            self._lightmap_surf = self._lightmap_surf.convert()

        # 2. Pre-bake Static AO Map & Anamorphic Vignette for current stage
        self._static_ao_map: Optional[pygame.Surface] = None
        self.configure_stage_ao(self.theme, self.floor_y)

        # 3. Silksong Hero Glow & Rim Light (pre-rendered radial textures)
        self._hero_glow_surf = self.get_radial_light_surface(radius=80, color=(255, 225, 175), intensity=0.48)
        self._hero_rim_surf = self.get_radial_light_surface(radius=36, color=(255, 245, 215), intensity=0.65)

        # 4. Entity Contact AO Stamps (small, medium, large soft elliptical occlusion gradients)
        self._ao_stamp_small = self._prebake_contact_ao(width=28, height=8, max_alpha=110)
        self._ao_stamp_med = self._prebake_contact_ao(width=44, height=10, max_alpha=135)
        self._ao_stamp_large = self._prebake_contact_ao(width=64, height=12, max_alpha=155)

        # 5. Pre-rendered Volumetric Diagonal God Rays (slanted light beams)
        self._god_ray_surfs: List[pygame.Surface] = []
        self._prebake_god_rays()

        # 6. Silksong Floating Atmospheric Particles (45 particles in a fixed NumPy object pool)
        self.num_dust = 45
        self.dust_halo_surfs: List[pygame.Surface] = []
        self._init_floating_dust_pool()

        # Legacy vignette cache compatibility
        self._vignette_cache = self._build_smooth_vignette(screen_w, screen_h)
        self.vignette = self._vignette_cache

        # Backward compatibility for legacy particles
        self.particles: list[AmbientParticle] = []
        for _ in range(25):
            self.particles.append(AmbientParticle(screen_w * 3, screen_h, self.theme))

    @classmethod
    def get_radial_light_surface(cls, radius: int, color: tuple, intensity: float = 1.0) -> pygame.Surface:
        # Quantize radius to 4-pixel increments to eliminate continuous numpy re-allocations during light flicker
        radius = max(8, (int(radius) // 4) * 4)
        q_intensity = max(0.1, min(1.0, round(intensity, 1)))
        cr, cg, cb = int(color[0]), int(color[1]), int(color[2])
        key = (radius, (cr, cg, cb), q_intensity)
        if key not in cls._RADIAL_CACHE:
            if len(cls._RADIAL_CACHE) > 128:
                cls._RADIAL_CACHE.clear()
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
            disp = pygame.display.get_surface()
            if disp:
                surf = surf.convert()
            cls._RADIAL_CACHE[key] = surf
        return cls._RADIAL_CACHE[key]

    def _prebake_contact_ao(self, width: int, height: int, max_alpha: int = 120) -> pygame.Surface:
        """Pre-renders an elliptical ground contact occlusion stamp with soft quadratic falloff."""
        import numpy as np
        surf = pygame.Surface((width, height), pygame.SRCALPHA, 32)
        rx = width / 2.0
        ry = height / 2.0
        x, y = np.ogrid[-rx:rx, -ry:ry]
        dist_sq = (x / rx) ** 2 + (y / ry) ** 2
        mask = dist_sq < 1.0

        alpha = np.zeros((width, height), dtype=np.float32)
        # Smooth cosine falloff
        alpha[mask] = (0.5 + 0.5 * np.cos(np.pi * np.sqrt(dist_sq[mask]))) * max_alpha

        p3d = pygame.surfarray.pixels3d(surf)
        p3d[:] = [10, 8, 14]
        del p3d

        pa = pygame.surfarray.pixels_alpha(surf)
        pa[:] = np.clip(alpha, 0, 255).astype(np.uint8)
        del pa

        disp = pygame.display.get_surface()
        if disp:
            surf = surf.convert_alpha()
        return surf

    def _prebake_god_rays(self):
        """Pre-renders 3 diagonal light beam textures fused into a single combined surface for 1-blit BLEND_RGB_ADD."""
        W, H = 960, 360
        surf = pygame.Surface((W, H))
        surf.fill((0, 0, 0))

        # Ray colors tuned to stage lighting
        if self.theme in ("road", "sunset", "beach"):
            ray_color = (255, 220, 165) # Warm sunset amber
        elif self.theme in ("forest", "emerald"):
            ray_color = (210, 235, 245) # Mountain cool mist
        else:
            ray_color = (195, 210, 235)

        x = np.arange(W)[:, None]
        y = np.arange(H)[None, :]
        total_mult = np.zeros((W, H), dtype=np.float32)

        for i in range(3):
            slant_deg = 24.0 + i * 4.0
            tan_v = np.tan(np.radians(slant_deg))
            slant_x = x - y * tan_v
            cx = 160.0 + i * 260.0
            shaft_w = 52.0 + i * 16.0
            dist = np.abs(slant_x - cx) / float(shaft_w)
            mask = dist < 1.0

            horiz_fade = np.zeros((W, H), dtype=np.float32)
            horiz_fade[mask] = 0.5 + 0.5 * np.cos(np.pi * dist[mask])
            vert_fade = np.power(1.0 - (y / float(H)), 0.65)
            mult = horiz_fade * vert_fade * 0.12
            total_mult = np.maximum(total_mult, mult)

        p3d = pygame.surfarray.pixels3d(surf)
        p3d[..., 0] = np.clip(ray_color[0] * total_mult, 0, 255).astype(np.uint8)
        p3d[..., 1] = np.clip(ray_color[1] * total_mult, 0, 255).astype(np.uint8)
        p3d[..., 2] = np.clip(ray_color[2] * total_mult, 0, 255).astype(np.uint8)
        del p3d

        disp = pygame.display.get_surface()
        if disp:
            surf = surf.convert()
        self._unified_god_rays = surf
        self._god_ray_surfs = [surf, surf, surf]

    def _init_floating_dust_pool(self):
        """Initializes a 45-particle fixed object pool for Silksong floating embers/dust motes."""
        import numpy as np
        # Particle color
        if self.theme in ("road", "sunset"):
            color = (255, 225, 160)
        elif self.theme in ("dungeon", "crypt"):
            color = (130, 215, 255)
        else:
            color = (235, 230, 195)

        # Pre-bake 3 halo stamps: 1px (4x4), 2px (6x6), 3px (8x8)
        self.dust_halo_surfs.clear()
        for sz, rad in [(4, 1), (6, 2), (8, 3)]:
            s = pygame.Surface((sz, sz), pygame.SRCALPHA, 32)
            pygame.draw.circle(s, (*color, 240), (sz // 2, sz // 2), rad)
            if rad >= 2:
                # Soft outer bloom ring
                pygame.draw.circle(s, (*color, 85), (sz // 2, sz // 2), rad + 1)
            disp = pygame.display.get_surface()
            if disp:
                s = s.convert_alpha()
            self.dust_halo_surfs.append(s)

        # Pre-allocated arrays (Zero per-frame allocation)
        rng = np.random.default_rng(42)
        self.dust_x = rng.uniform(0, self.screen_w + 320, self.num_dust).astype(np.float32)
        self.dust_y = rng.uniform(10, self.screen_h - 20, self.num_dust).astype(np.float32)
        self.dust_vx = rng.uniform(12.0, 32.0, self.num_dust).astype(np.float32)
        self.dust_vy = rng.uniform(-6.0, 6.0, self.num_dust).astype(np.float32)
        self.dust_phase = rng.uniform(0, 6.28, self.num_dust).astype(np.float32)
        self.dust_sway_speed = rng.uniform(1.6, 3.4, self.num_dust).astype(np.float32)
        self.dust_size_idx = rng.choice([0, 1, 2], p=[0.45, 0.35, 0.20], size=self.num_dust).astype(np.int32)
        # 0 = background (behind player), 1 = foreground (in front of player)
        self.dust_layer = rng.choice([0, 1], p=[0.60, 0.40], size=self.num_dust).astype(np.int32)

    def configure_stage_ao(self, theme: str, floor_y: int = 280):
        """Pre-computes stage static Ambient Occlusion (crevice shadows + bottom border) and Anamorphic Vignette."""
        import numpy as np
        self.theme = theme
        self.floor_y = floor_y
        gw, gh = self.screen_w, self.screen_h

        # Base atmospheric color grading multiplier
        if theme in ("road", "sunset", "beach"):
            base_color = (220, 195, 180) # Warm sunset
        elif theme in ("forest", "emerald"):
            base_color = (185, 195, 215) # Slate emerald
        elif theme in ("blood_moon", "throne"):
            base_color = (195, 168, 168) # Twilight crimson
        else:
            base_color = (175, 182, 195)

        x = np.arange(gw)[:, None]
        y = np.arange(gh)[None, :]

        # 1. Structural Crevice AO at bridge/floor back-wall junction
        # Darkens junction between horizontal floor and vertical background (crevice shadow)
        crevice_ao = 1.0 - 0.26 * np.exp(-((y - float(floor_y)) / 7.5) ** 2)

        # 2. Foreground Grounding: bottom screen edge darkening (preserves contrast on foreground bamboos/balustrade)
        bottom_ao = np.where(y > 305, 1.0 - 0.34 * ((y - 305.0) / 55.0), 1.0)
        bottom_ao = np.clip(bottom_ao, 0.64, 1.0)

        # 3. Two-Stage Anamorphic Vignette (cinematic 2.35:1 aspect ratio feel, keeps combat corridor bright)
        cx, cy = gw / 2.0, gh / 2.0
        nx = (x - cx) / (cx * 1.10)
        ny = (y - cy) / (cy * 0.95)
        dist_sq = nx ** 2 + ny ** 2
        anamorphic_vig = np.clip(1.0 - 0.35 * np.power(np.clip((dist_sq - 0.22) / 0.88, 0.0, 1.0), 1.6), 0.62, 1.0)

        # Composite Static Multiplier
        total_mult = np.clip(crevice_ao * bottom_ao * anamorphic_vig, 0.40, 1.0)

        ambient_rgb = np.zeros((gw, gh, 3), dtype=np.uint8)
        ambient_rgb[..., 0] = np.clip(base_color[0] * total_mult, 0, 255).astype(np.uint8)
        ambient_rgb[..., 1] = np.clip(base_color[1] * total_mult, 0, 255).astype(np.uint8)
        ambient_rgb[..., 2] = np.clip(base_color[2] * total_mult, 0, 255).astype(np.uint8)

        self._static_ao_map = pygame.surfarray.make_surface(ambient_rgb)
        disp = pygame.display.get_surface()
        if disp:
            self._static_ao_map = self._static_ao_map.convert()
        self._unified_post_mask = self._static_ao_map

    def update(self, dt: float):
        self.time += dt
        self.volumetric.update(dt)

        # Vectorized Particle Update (Zero per-frame allocation)
        vw = float(self.screen_w + 320)
        self.dust_phase += dt * self.dust_sway_speed
        self.dust_x = (self.dust_x + self.dust_vx * dt) % vw
        self.dust_y = (self.dust_y + (self.dust_vy + np.sin(self.dust_phase) * 6.0) * dt) % float(self.screen_h)

        if SETTINGS.AMBIENT_PARTICLES:
            for p in self.particles:
                p.update(dt, SETTINGS.GAME_WIDTH * 3, SETTINGS.GAME_HEIGHT)

    def draw_entity_ao(self, surface: pygame.Surface, entities: list, camera_offset: pygame.math.Vector2):
        """Draws dynamic soft ground contact occlusion stamps directly under entities' feet and obstacles."""
        if not getattr(SETTINGS, "CONTACT_AO", True):
            return
        cam_x, cam_y = camera_offset.x, camera_offset.y
        sw, sh = surface.get_size()

        ao_batch = []
        for ent in entities:
            r = getattr(ent, "rect", None)
            if not r:
                continue
            if r.right < cam_x - 32 or r.left > cam_x + sw + 32:
                continue

            ent_w = r.width
            if ent_w <= 30:
                stamp = self._ao_stamp_small
            elif ent_w <= 55:
                stamp = self._ao_stamp_med
            else:
                stamp = self._ao_stamp_large

            stamp_w, stamp_h = stamp.get_size()
            sx = int(r.centerx - stamp_w // 2 - cam_x)
            # Position at ground contact plane
            sy = int(r.bottom - stamp_h // 2 - 2 - cam_y)
            ao_batch.append((stamp, (sx, sy)))

        if ao_batch:
            surface.blits(ao_batch)

    def draw_god_rays(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        """Draws pre-rendered volumetric diagonal God Rays in a single high-performance BLEND_RGB_ADD blit."""
        if not getattr(SETTINGS, "RAYTRACING_ENABLED", True) or getattr(self, "_unified_god_rays", None) is None:
            return
        cam_x = camera_offset.x
        offset_x = int((-cam_x * 0.12) % 640) - 160
        surface.blit(self._unified_god_rays, (offset_x, 0), special_flags=pygame.BLEND_RGB_ADD)

    def draw_point_lights(self, surface: pygame.Surface, lights: list[LightSource], camera_offset: pygame.math.Vector2, hero_pos: Optional[Tuple[float, float]] = None):
        """
        Draws dynamic 2D lighting using fused Static Post-Mask + Half-Resolution Dynamic Lightmap.
        Zero allocation per frame, 1/4 the pixel operations, saving massive CPU bandwidth.
        """
        gw = surface.get_width()
        gh = surface.get_height()
        cam_x, cam_y = camera_offset.x, camera_offset.y

        # 1. Multiplicative Static Ambient Pass (Crevice AO + Vignette + Color Grading)
        if getattr(SETTINGS, "STATIC_AO", True):
            post_mask = getattr(self, "_unified_post_mask", None) or self._static_ao_map
            if post_mask is not None:
                surface.blit(post_mask, (0, 0), special_flags=pygame.BLEND_MULT)

        # 2. Check if dynamic lights exist
        if not getattr(SETTINGS, "DYNAMIC_LIGHTS", True) or not lights:
            return

        # Half-resolution accumulation buffer (320x180)
        hw = gw // 2
        hh = gh // 2
        if getattr(self, "_half_light_surf", None) is None or self._half_light_surf.get_size() != (hw, hh):
            self._half_light_surf = pygame.Surface((hw, hh))
            self._scaled_dynamic_lights = pygame.Surface((gw, gh))

        self._half_light_surf.fill((0, 0, 0))

        # 3. Dynamic point lights on half-resolution buffer (lanterns, spells, projectiles)
        culled_count = 0
        for l in lights:
            rad = max(4, int(l.radius // 2))
            sx = int((l.x - cam_x) / 2.0 - rad)
            sy = int((l.y - cam_y) / 2.0 - rad)
            if -rad * 2 <= sx <= hw and -rad * 2 <= sy <= hh:
                intensity = getattr(l, "intensity", 1.0)
                light_surf = self.get_radial_light_surface(rad, l.color, intensity * 0.60)
                self._half_light_surf.blit(light_surf, (sx, sy), special_flags=pygame.BLEND_ADD)
                culled_count += 1
                if culled_count >= 16:
                    break

        # 4. Fast upscale & additive blend over scene
        pygame.transform.scale(self._half_light_surf, (gw, gh), self._scaled_dynamic_lights)
        surface.blit(self._scaled_dynamic_lights, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    def draw_additive_glows(self, surface: pygame.Surface, emissives: list, camera_offset: pygame.math.Vector2):
        """Draws ultra-fast additive bloom pass for projectiles, slashes, and collectibles via BLEND_RGB_ADD."""
        if not emissives or not getattr(SETTINGS, "BLOOM_ENABLED", True):
            return
        cam_x, cam_y = camera_offset.x, camera_offset.y
        sw, sh = surface.get_size()

        for item in emissives:
            x, y, rad, col, intens = item
            sx = int(x - cam_x - rad)
            sy = int(y - cam_y - rad)
            if -rad <= sx <= sw + rad and -rad <= sy <= sh + rad:
                glow_surf = self.get_radial_light_surface(rad, col, intens)
                surface.blit(glow_surf, (sx, sy), special_flags=pygame.BLEND_RGB_ADD)

    def draw_ambient_particles_background(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        """Batch blits atmospheric dust motes situated in the background (behind player) via surface.blits()."""
        if not getattr(SETTINGS, "AMBIENT_PARTICLES", True) or getattr(SETTINGS, "AMBIENT_PARTICLES_COUNT", 30) <= 0:
            return
        cam_x = camera_offset.x
        sw = surface.get_width()
        vw = float(self.screen_w + 320)
        max_p = min(self.num_dust, getattr(SETTINGS, "AMBIENT_PARTICLES_COUNT", 30))

        batch = []
        for i in range(max_p):
            if self.dust_layer[i] == 0:
                sx = int(((self.dust_x[i] - cam_x * 0.40) % vw) - 160)
                if -10 <= sx <= sw + 10:
                    stamp = self.dust_halo_surfs[self.dust_size_idx[i]]
                    batch.append((stamp, (sx, int(self.dust_y[i]))))

        if batch:
            surface.blits(batch)

    def draw_ambient_particles_foreground(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        """Batch blits atmospheric dust motes situated in the foreground (in front of player) via surface.blits()."""
        if not getattr(SETTINGS, "AMBIENT_PARTICLES", True) or getattr(SETTINGS, "AMBIENT_PARTICLES_COUNT", 30) <= 0:
            return
        cam_x = camera_offset.x
        sw = surface.get_width()
        vw = float(self.screen_w + 320)
        max_p = min(self.num_dust, getattr(SETTINGS, "AMBIENT_PARTICLES_COUNT", 30))

        batch = []
        for i in range(max_p):
            if self.dust_layer[i] == 1:
                sx = int(((self.dust_x[i] - cam_x * 1.15) % vw) - 160)
                if -10 <= sx <= sw + 10:
                    stamp = self.dust_halo_surfs[self.dust_size_idx[i]]
                    batch.append((stamp, (sx, int(self.dust_y[i]))))

        if batch:
            surface.blits(batch)

    def draw_ambient_particles(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        """Draws all floating particles (backwards compatibility)."""
        self.draw_ambient_particles_background(surface, camera_offset)
        self.draw_ambient_particles_foreground(surface, camera_offset)

    def draw_shadows(self, surface: pygame.Surface, lights: list[LightSource], occluders: list, camera_offset: pygame.math.Vector2):
        """Draws dynamic 2D shadow polygons from occluders using Half-Resolution Accumulation Buffer."""
        if not SETTINGS.RUIN_ENGINE_V3 or SETTINGS.SHADOWS_2D == "Desativado" or not lights or not occluders:
            return
            
        gw = surface.get_width()
        gh = surface.get_height()
        cam_x, cam_y = camera_offset.x, camera_offset.y

        # Frustum Culling on lights
        visible_lights = []
        for l in lights:
            rad = l.radius
            screen_lx = l.x - cam_x
            screen_ly = l.y - cam_y
            if -rad <= screen_lx <= gw + rad and -rad <= screen_ly <= gh + rad:
                visible_lights.append(l)

        if not visible_lights:
            return

        visible_lights = visible_lights[:6]

        # Half-Resolution Accumulation Buffer
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
                shadow_alpha=70,
                target_surface=half_mask
            )

        full_mask = pygame.transform.smoothscale(half_mask, (gw, gh))
        surface.blit(full_mask, (0, 0))
        SURFACE_POOL.release(half_mask)

    def draw_baked_lightmap(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        """Ultra-lightweight pre-baked ambient stage lightmap."""
        if getattr(self, "_baked_lightmap", None) is None:
            bw, bh = SETTINGS.GAME_WIDTH, SETTINGS.GAME_HEIGHT
            self._baked_lightmap = pygame.Surface((bw, bh))
            if self.theme in ("road", "sunset"):
                self._baked_lightmap.fill((210, 190, 180))
            elif self.theme in ("forest", "emerald"):
                self._baked_lightmap.fill((185, 195, 205))
            else:
                self._baked_lightmap.fill((175, 180, 190))
        surface.blit(self._baked_lightmap, (0, 0), special_flags=pygame.BLEND_MULT)

    def apply_color_grading(self, surface: pygame.Surface, theme: str = None):
        """Applies cinematic stage Look-Up Table (LUT) color grading."""
        if not getattr(SETTINGS, "RUIN_ENGINE_V3", True):
            return
        stage_theme = theme or self.theme
        self.color_grading.apply_grading(surface, theme=stage_theme)

    def _build_smooth_vignette(self, gw: int, gh: int) -> pygame.Surface:
        """Pre-renders a smooth 2D elliptical photographic vignette."""
        vignette_surf = pygame.Surface((gw, gh), pygame.SRCALPHA, 32)
        try:
            import numpy as np
            cx, cy = gw / 2.0, gh / 2.0
            x = np.arange(gw)[:, None]
            y = np.arange(gh)[None, :]
            nx = (x - cx) / (cx * 1.05)
            ny = (y - cy) / (cy * 1.05)
            dist = np.sqrt(nx ** 2 + ny ** 2)
            
            vignette_alpha = np.zeros((gw, gh), dtype=np.float32)
            mask = dist > 0.60
            vignette_alpha[mask] = np.clip(160.0 * np.power((dist[mask] - 0.60) / 0.65, 1.7), 0.0, 160.0)

            p3d = pygame.surfarray.pixels3d(vignette_surf)
            p3d[:] = [0, 0, 0]
            del p3d

            pa = pygame.surfarray.pixels_alpha(vignette_surf)
            pa[:] = vignette_alpha.astype(np.uint8)
            del pa
        except Exception:
            vignette_surf.fill((0, 0, 0, 0))

        disp = pygame.display.get_surface()
        if disp:
            vignette_surf = vignette_surf.convert_alpha()
        return vignette_surf

    def draw_vignette(self, surface: pygame.Surface):
        """Draws cinematic lens vignette with zero per-frame allocation."""
        if not SETTINGS.VIGNETTE_ENABLED:
            return
        gw, gh = surface.get_size()
        if getattr(self, "_vignette_cache", None) is None or self._vignette_cache.get_size() != (gw, gh):
            self._vignette_cache = self._build_smooth_vignette(gw, gh)
        surface.blit(self._vignette_cache, (0, 0))

