"""
Ruin Engine V3.0 — Master Decoupled 15-Pass Multipass Rendering Pipeline.
Executes camera framing, culling, chunk caching, lighting, shadows, GPU particles, postFX, and FSR upscaling.
"""

from dataclasses import dataclass, field
import pygame
from typing import List, Tuple, Any, Optional

from engine.v3.core.profiler import PROFILER
from engine.v3.core.surface_pool import SURFACE_POOL
from engine.v3.core.adaptive_quality import ADAPTIVE_QUALITY
from engine.v3.camera.camera_v3 import CameraV3
from engine.v3.spatial.quadtree import QuadTree
from engine.v3.spatial.chunk_renderer import ChunkRenderer
from engine.v3.lighting.raycasting2d import LightRayCaster
from engine.v3.lighting.shadows import ShadowRenderer
from engine.v3.lighting.volumetric import VolumetricLightingEngine
from engine.v3.lighting.ambient_occlusion import AmbientOcclusion2D
from engine.v3.lighting.normal_maps import NormalMapLighting
from engine.v3.particles.particle_engine import ParticleEngine
from engine.v3.particles.trail_renderer import TrailRenderer
from engine.v3.particles.hit_effects import HitEffectsManager
from engine.v3.postfx.post_processor import PostProcessor
from engine.v3.upscaling.fsr2d import FSR2D
from engine.v3.upscaling.antialiasing import AntiAliasingEngine
from engine.v3.weather.weather_engine import WeatherEngine

@dataclass
class RenderContext:
    """Carries frame state and render buffers sequentially across the 15 pipeline stages."""
    camera: CameraV3
    internal_buffer: pygame.Surface
    window_surface: pygame.Surface
    visible_rect: pygame.Rect
    camera_offset: pygame.math.Vector2
    stage_theme: str = "forest"
    entities: List[Any] = field(default_factory=list)
    lights: List[Any] = field(default_factory=list)
    occluders: List[Tuple[float, float, float, float]] = field(default_factory=list)
    dt: float = 0.016

class MasterRenderPipeline:
    """
    Executes the 15 distinct passes of the Ruin Engine V3.0 graphical architecture.
    """
    def __init__(self, internal_w: int = 512, internal_h: int = 384, window_w: int = 1280, window_h: int = 720):
        self.iw = internal_w
        self.ih = internal_h
        self.ww = window_w
        self.wh = window_h

        # Core subsystem modules
        self.quadtree = QuadTree(0, 0, 8192, 2048)
        self.chunk_renderer = ChunkRenderer(chunk_size=32, tile_size=16)
        self.ray_caster = LightRayCaster()
        self.shadow_renderer = ShadowRenderer()
        self.volumetric = VolumetricLightingEngine(internal_w, internal_h)
        self.ao = AmbientOcclusion2D()
        self.particles = ParticleEngine(capacity=4000)
        self.hit_effects = HitEffectsManager()
        self.post_processor = PostProcessor(internal_w, internal_h)
        self.fsr = FSR2D(window_w, window_h, preset="Balanced")
        self.aa = AntiAliasingEngine(mode="FXAA")
        self.weather = WeatherEngine(self.particles)

        # Feature flags
        self.enable_lighting = True
        self.enable_shadows = True
        self.enable_volumetrics = True
        self.enable_bloom = True
        self.enable_postfx = True
        self.enable_fsr = True

    def execute(
        self,
        internal_buf: pygame.Surface,
        window_buf: pygame.Surface,
        camera: CameraV3,
        draw_background_callback: Any,
        draw_world_callback: Any,
        draw_hud_callback: Any,
        lights: List[Any],
        occluders: List[Tuple[float, float, float, float]],
        entities: List[Any],
        stage_theme: str,
        dt: float
    ) -> None:
        """Runs all 15 stages in strictly decoupled, deterministic sequence."""
        PROFILER.begin_frame()

        # PASS 1: Camera
        cam_offset = camera.offset
        visible_rect = pygame.Rect(int(cam_offset.x), int(cam_offset.y), self.iw, self.ih)

        ctx = RenderContext(
            camera=camera,
            internal_buffer=internal_buf,
            window_surface=window_buf,
            visible_rect=visible_rect,
            camera_offset=cam_offset,
            stage_theme=stage_theme,
            entities=entities,
            lights=lights,
            occluders=occluders,
            dt=dt
        )

        # PASS 2 & 3: Frustum & Occlusion Culling
        visible_entities = [e for e in entities if hasattr(e, "rect") and visible_rect.colliderect(e.rect)]

        # PASS 4: QuadTree spatial population
        self.quadtree.clear()
        for e in visible_entities:
            self.quadtree.insert(e, (e.rect.x, e.rect.y, e.rect.width, e.rect.height))

        # PASS 5 & 6: Chunks & Tilemap Background
        if draw_background_callback:
            draw_background_callback(internal_buf, cam_offset)

        # PASS 7 & 8: Static & Animated Sprites (Entities)
        if draw_world_callback:
            draw_world_callback(internal_buf, cam_offset)

        # PASS 9: Advanced Geometry & Atmospheric Volumetrics
        if self.enable_volumetrics and ADAPTIVE_QUALITY.profile.volumetric_step <= 10:
            if "floresta" in stage_theme.lower():
                self.volumetric.render_god_rays(internal_buf, (180 - cam_offset.x, -20 - cam_offset.y), intensity=0.6)
            elif "proibida" in stage_theme.lower() or "cripta" in stage_theme.lower():
                self.volumetric.render_volumetric_fog(internal_buf, density=0.25)

        # PASS 10 & 11: Lighting & Shadows
        if self.enable_lighting and lights:
            for l in lights:
                lx = getattr(l, "x", getattr(getattr(l, "rect", None), "centerx", 0))
                ly = getattr(l, "y", getattr(getattr(l, "rect", None), "centery", 0))
                radius = getattr(l, "radius", 60)
                color = getattr(l, "color", (255, 200, 100))
                intensity = getattr(l, "intensity", 1.0)

                # Shadow pass
                if self.enable_shadows and occluders:
                    mask = self.shadow_renderer.render_shadow_mask(
                        self.iw, self.ih, lx, ly, radius, occluders, cam_offset,
                        soft_rays=ADAPTIVE_QUALITY.profile.shadow_softness_rays
                    )
                    internal_buf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
                    SURFACE_POOL.release(mask)

                # Light visibility polygon cone
                poly = self.ray_caster.compute_visibility_polygon(lx, ly, radius, occluders)
                self.ray_caster.render_light_cone(internal_buf, lx, ly, radius, color, intensity, poly, cam_offset)

        # PASS 12: VFX & Particle Renderer
        self.particles.update(dt)
        self.particles.render(internal_buf, cam_offset)
        self.hit_effects.update(dt)
        self.hit_effects.render(internal_buf, cam_offset)

        # PASS 13: PostFX Renderer (Bloom, Color Grading, Vignette)
        if self.enable_postfx:
            if self.enable_bloom and ADAPTIVE_QUALITY.profile.bloom_passes > 0:
                # threshold=0.95: Only the absolute brightest emissive pixels (fire, magic VFX,
                # bright particle cores) get bloom. Characters, walls, ground — zero bloom.
                # intensity=0.08: Subtle glow, no blowout, no ghosting trails.
                self.post_processor.bloom.apply_bloom(internal_buf, threshold=0.95, intensity=0.08)

            # Stage LUT color grading
            self.post_processor.color_grading.apply_grading(internal_buf, theme=stage_theme)
            self.post_processor.apply_vignette(internal_buf)

        # PASS 14: Super Resolution (FSR 2D) & Anti-Aliasing
        if self.enable_fsr and (self.ww != self.iw or self.wh != self.ih):
            upscaled = self.fsr.upscale(internal_buf)
            final_view = self.aa.apply(upscaled)
            window_buf.blit(final_view, (0, 0))
        else:
            final_view = self.aa.apply(internal_buf)
            window_buf.blit(pygame.transform.scale(final_view, (self.ww, self.wh)), (0, 0))

        # PASS 15: HUD, UI, & F3 Profiler Overlay
        if draw_hud_callback:
            draw_hud_callback(window_buf)

        PROFILER.render_overlay(window_buf)

        # Dynamic Adaptive Quality adjustment
        ADAPTIVE_QUALITY.update(PROFILER.fps)
