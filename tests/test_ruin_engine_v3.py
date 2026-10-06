"""
Ruin Engine V3.0 — Comprehensive Automated Test Suite.
Validates all 15 decoupled pipeline stages, ECS, Lighting, Shadows, Particles, FSR, and Profiler.
"""

import math
import sys
from pathlib import Path
import unittest
import numpy as np
import pygame

# Dynamic path configuration for clean module resolution
sys.path.append(str(Path(__file__).parent.parent / "src"))

# Initialize headless pygame for testing
pygame.init()
pygame.display.set_mode((512, 384))

from engine.v3.core.jit_backend import is_jit_enabled, get_jit_info
from engine.v3.core.surface_pool import SurfacePool, SURFACE_POOL
from engine.v3.core.memory_manager import MemoryManager, MEMORY_MANAGER
from engine.v3.core.profiler import Profiler, PROFILER
from engine.v3.core.adaptive_quality import AdaptiveQualityGovernor, ADAPTIVE_QUALITY
from engine.v3.ecs.components import (
    TransformComponent, PhysicsComponent, AnimationComponent, HealthComponent,
    ManaComponent, StaminaComponent, LightSourceComponent, HitboxComponent, HurtboxComponent
)
from engine.v3.ecs.world import ECSWorld
from engine.v3.ecs.systems import PhysicsSystem, CombatHitboxSystem
from engine.v3.spatial.quadtree import QuadTree, SpatialChunkCache
from engine.v3.spatial.chunk_renderer import Chunk, ChunkRenderer
from engine.v3.lighting.raycasting2d import LightRayCaster
from engine.v3.lighting.shadows import ShadowRenderer
from engine.v3.lighting.volumetric import VolumetricLightingEngine
from engine.v3.lighting.ambient_occlusion import AmbientOcclusion2D
from engine.v3.lighting.normal_maps import NormalMapLighting
from engine.v3.lighting.fake_rtx import FakeRTXEngine
from engine.v3.geometry.sdf_2d import sdf_box, sdf_circle, op_union, op_subtract
from engine.v3.geometry.marching_squares import MarchingSquares
from engine.v3.geometry.spline_renderer import SplineRenderer
from engine.v3.geometry.procedural_fx import ProceduralWater, ProceduralLava, VerletRope
from engine.v3.particles.particle_engine import (
    ParticleEngine, PARTICLE_BLOOD, PARTICLE_FIRE, PARTICLE_MAGIC, PARTICLE_DUST
)
from engine.v3.particles.trail_renderer import TrailRenderer
from engine.v3.particles.hit_effects import HitEffectsManager
from engine.v3.postfx.bloom import BloomEngine
from engine.v3.postfx.color_grading import ColorGradingEngine
from engine.v3.postfx.post_processor import PostProcessor
from engine.v3.upscaling.fsr2d import FSR2D
from engine.v3.upscaling.tsr import TemporalSuperResolution
from engine.v3.upscaling.antialiasing import AntiAliasingEngine
from engine.v3.weather.weather_engine import WeatherEngine, WEATHER_RAIN, WEATHER_LEAVES
from engine.v3.camera.camera_v3 import CameraV3
from engine.v3.core.pipeline import MasterRenderPipeline

class TestRuinEngineV3(unittest.TestCase):
    def test_jit_backend_diagnostics(self):
        info = get_jit_info()
        self.assertIn("numba_available", info)
        self.assertIn("backend", info)
        print(f"[TEST JIT] Active Backend: {info['backend']}")

    def test_surface_pool_lifecycle(self):
        pool = SurfacePool()
        surf1 = pool.acquire(128, 128)
        self.assertIsInstance(surf1, pygame.Surface)
        self.assertEqual(surf1.get_size(), (128, 128))
        pool.release(surf1)

        # Re-acquire same size should hit cache
        surf2 = pool.acquire(128, 128)
        stats = pool.get_stats()
        self.assertGreaterEqual(stats["cache_hits"], 1)
        pool.release(surf2)

    def test_memory_manager_tracking(self):
        mm = MemoryManager()
        mm.register_surface(256, 256, 4)
        stats = mm.get_memory_stats()
        self.assertIn("ram_mb", stats)
        self.assertIn("vram_mb", stats)
        self.assertGreater(stats["ram_mb"], 0.0)
        mm.unregister_surface(256, 256, 4)

    def test_profiler_and_f3_overlay(self):
        profiler = Profiler()
        profiler.begin_frame()
        profiler.record_draw_calls(5)
        profiler.record_particles(120)
        profiler.record_chunks(4)
        profiler.record_light(16)
        profiler.record_shadow()

        self.assertEqual(profiler.metrics["draw_calls"], 5)
        self.assertEqual(profiler.metrics["particles"], 120)
        self.assertEqual(profiler.metrics["chunks_rendered"], 4)
        self.assertEqual(profiler.metrics["lights_count"], 1)
        self.assertEqual(profiler.metrics["ray_count"], 16)

        # Test overlay rendering
        surf = pygame.Surface((512, 384))
        profiler.enabled = True
        profiler.render_overlay(surf)
        profiler.enabled = False

    def test_adaptive_quality_governor(self):
        gov = AdaptiveQualityGovernor(target_fps=60.0)
        initial_tier = gov.current_tier
        # Simulate severe framerate drop
        for _ in range(gov.hysteresis_threshold + 5):
            gov.update(current_fps=40.0)
        self.assertGreaterEqual(gov.current_tier, initial_tier)

        # Manual tier set
        gov.set_manual_tier(0)
        self.assertEqual(gov.current_tier, 0)
        self.assertEqual(gov.profile.max_particles, 4000)

    def test_ecs_world_and_systems(self):
        world = ECSWorld()
        phys_system = PhysicsSystem()
        combat_system = CombatHitboxSystem()
        world.register_system(phys_system)
        world.register_system(combat_system)

        # Entity 1: Attacker
        e1 = world.create_entity()
        world.add_component(e1, TransformComponent(x=100.0, y=200.0))
        world.add_component(e1, PhysicsComponent(vx=50.0, on_ground=True))
        world.add_component(e1, HitboxComponent(width=40.0, height=40.0, damage=35.0, active=True))

        # Entity 2: Defender
        e2 = world.create_entity()
        world.add_component(e2, TransformComponent(x=110.0, y=200.0))
        world.add_component(e2, HurtboxComponent(width=40.0, height=40.0))
        world.add_component(e2, HealthComponent(current_hp=100.0, max_hp=100.0))

        # Update world
        world.update(0.1)

        # Verify physics motion
        t1 = world.get_component(e1, TransformComponent)
        self.assertGreater(t1.x, 100.0)

        # Verify combat damage resolution
        h2 = world.get_component(e2, HealthComponent)
        self.assertEqual(h2.current_hp, 65.0)

    def test_quadtree_spatial_partitioning(self):
        qt = QuadTree(0, 0, 1000, 1000, max_objects=4)
        for i in range(20):
            qt.insert(f"item_{i}", (i * 40.0, i * 40.0, 32.0, 32.0))

        # Query range
        results = qt.query_range((0, 0, 150, 150))
        self.assertTrue(len(results) > 0)
        self.assertIn("item_0", results)

    def test_chunk_renderer_caching_and_culling(self):
        cr = ChunkRenderer(chunk_size=16, tile_size=16)
        tile = pygame.Surface((16, 16))
        tile.fill((100, 150, 200))
        cr.add_tile(0, 0, tile)
        cr.add_tile(5, 5, tile)

        target = pygame.Surface((512, 384))
        drawn = cr.render(target, pygame.math.Vector2(0, 0), 512, 384)
        self.assertGreaterEqual(drawn, 1)

    def test_2d_ray_casting_visibility_polygon(self):
        caster = LightRayCaster()
        occluders = [
            (100.0, 50.0, 100.0, 150.0),
            (200.0, 100.0, 250.0, 100.0)
        ]
        poly = caster.compute_visibility_polygon(150.0, 100.0, 80.0, occluders)
        self.assertGreaterEqual(len(poly), 3)

        surf = pygame.Surface((512, 384))
        caster.render_light_cone(surf, 150.0, 100.0, 80.0, (255, 200, 100), 1.0, poly, pygame.math.Vector2(0, 0))

    def test_2d_shadow_polygons_and_soft_penumbra(self):
        shadows = ShadowRenderer(shadow_length=300.0)
        quad = shadows.project_shadow_polygon(50.0, 50.0, (100.0, 80.0), (120.0, 80.0))
        self.assertEqual(len(quad), 4)

        mask = shadows.render_shadow_mask(
            512, 384, 50.0, 50.0, 150.0,
            [(100.0, 80.0, 120.0, 80.0)], pygame.math.Vector2(0, 0), soft_rays=4
        )
        self.assertIsInstance(mask, pygame.Surface)
        SURFACE_POOL.release(mask)

    def test_volumetric_lighting_and_fog(self):
        vol = VolumetricLightingEngine(512, 384)
        vol.update(0.016)
        surf = pygame.Surface((512, 384))
        vol.render_god_rays(surf, (256, 50), intensity=0.5, num_shafts=4)
        vol.render_volumetric_fog(surf, density=0.2)

    def test_ambient_occlusion_2d(self):
        ao = AmbientOcclusion2D(tile_size=16)
        mask = [[True if (x < 4 and y < 4) else False for x in range(10)] for y in range(10)]
        baked = ao.bake_corner_occlusion(10, 10, mask)
        self.assertEqual(baked.get_size(), (160, 160))

        surf = pygame.Surface((512, 384))
        ao.render_dynamic_entity_ao(surf, [(100.0, 200.0, 24.0)], pygame.math.Vector2(0, 0))

    def test_normal_map_lighting(self):
        sprite = pygame.Surface((32, 32))
        sprite.fill((200, 50, 50))
        norm = NormalMapLighting.generate_procedural_normal_map(sprite)
        self.assertEqual(norm.get_size(), (32, 32))

        shaded = NormalMapLighting.render_shaded_sprite(
            sprite, (100, 100), (120, 90, 40), normal_map=norm
        )
        self.assertEqual(shaded.get_size(), (32, 32))

    def test_fake_rtx_sdf_ray_marching(self):
        rtx = FakeRTXEngine(512, 384)
        boxes = [(100.0, 100.0, 50.0, 50.0)]
        hit, dist, hx, hy, nx, ny = rtx.march_ray_sdf(50.0, 125.0, 1.0, 0.0, boxes)
        self.assertTrue(hit)
        self.assertAlmostEqual(hx, 100.0, delta=2.0)

        secondary = rtx.calculate_fake_indirect_bounce(50.0, 125.0, (255, 200, 100), boxes, num_rays=8)
        self.assertTrue(len(secondary) > 0)

    def test_sdf_primitives_and_booleans(self):
        d_c = sdf_circle(10.0, 0.0, 0.0, 0.0, 5.0)
        self.assertAlmostEqual(d_c, 5.0)
        d_b = sdf_box(10.0, 0.0, 0.0, 0.0, 4.0, 4.0)
        self.assertAlmostEqual(d_b, 6.0)
        u = op_union(d_c, d_b)
        self.assertAlmostEqual(u, 5.0)

    def test_marching_squares_contours(self):
        field = np.zeros((8, 8), dtype=np.float32)
        field[2:6, 2:6] = 1.0
        segments = MarchingSquares.extract_contours(field, iso_value=0.5, cell_size=16.0)
        self.assertGreater(len(segments), 0)

    def test_spline_renderer_ribbons(self):
        pts = [(0.0, 0.0), (50.0, 20.0), (100.0, -10.0), (150.0, 30.0)]
        spline = SplineRenderer.generate_catmull_rom_spline(pts, subdivisions=4)
        self.assertGreater(len(spline), len(pts))
        ribbon = SplineRenderer.build_ribbon_mesh(spline, half_width_start=10.0, half_width_end=2.0)
        self.assertGreater(len(ribbon), 4)

    def test_procedural_water_lava_rope(self):
        water = ProceduralWater(0, 300, 200, 50)
        water.splash(100, 15.0)
        water.update(0.016)
        surf = pygame.Surface((512, 384))
        water.render(surf, pygame.math.Vector2(0, 0))

        lava = ProceduralLava(0, 350, 200, 30)
        lava.update(0.016)
        lava.render(surf, pygame.math.Vector2(0, 0))

        rope = VerletRope(100, 50, num_links=6, link_length=12.0)
        rope.update(0.016)
        rope.render(surf, pygame.math.Vector2(0, 0))

    def test_particle_engine_simd_burst(self):
        pe = ParticleEngine(capacity=500)
        pe.spawn_burst(100, 100, count=30, p_type=PARTICLE_BLOOD)
        pe.spawn_burst(100, 100, count=30, p_type=PARTICLE_FIRE)
        alive = pe.update(0.016)
        self.assertGreaterEqual(alive, 50)

        surf = pygame.Surface((512, 384))
        pe.render(surf, pygame.math.Vector2(0, 0))

    def test_trail_renderer_deques(self):
        tr = TrailRenderer(max_length=12, color=(100, 200, 255))
        for i in range(8):
            tr.add_point(i * 15.0, 100.0 + math.sin(i) * 10.0)
        tr.update()
        surf = pygame.Surface((512, 384))
        tr.render(surf, pygame.math.Vector2(0, 0))

    def test_hit_effects_manager(self):
        hem = HitEffectsManager()
        hem.trigger_hitstop(0.06)
        hem.trigger_impact_frame(2)
        hem.trigger_chromatic_flash(1.0)
        hem.spawn_sparks(100, 100, count=8)
        hem.spawn_shockwave(100, 100, max_radius=60.0)

        is_hitstopped = hem.update(0.016)
        self.assertTrue(is_hitstopped)

        surf = pygame.Surface((512, 384))
        hem.render(surf, pygame.math.Vector2(0, 0))

    def test_bloom_hdr_multipass(self):
        bloom = BloomEngine(512, 384, downsample_scale=0.25)
        surf = pygame.Surface((512, 384))
        # Draw bright highlight
        pygame.draw.circle(surf, (255, 255, 255), (256, 192), 30)
        bloom.apply_bloom(surf, threshold=0.70, intensity=1.0)

    def test_color_grading_luts(self):
        cg = ColorGradingEngine()
        surf = pygame.Surface((64, 64))
        surf.fill((120, 120, 120))
        cg.apply_grading(surf, theme="catacombs")
        cg.apply_grading(surf, theme="forest")
        cg.apply_grading(surf, theme="blood_moon")

    def test_fsr2d_and_tsr_upscaling(self):
        fsr = FSR2D(1280, 720, preset="Balanced")
        low_res = pygame.Surface((fsr.vw, fsr.vh))
        low_res.fill((80, 120, 180))
        upscaled = fsr.upscale(low_res)
        self.assertEqual(upscaled.get_size(), (1280, 720))

        tsr = TemporalSuperResolution(512, 384)
        f1 = pygame.Surface((512, 384))
        f1.fill((50, 60, 70))
        res = tsr.resolve(f1)
        self.assertEqual(res.get_size(), (512, 384))

    def test_antialiasing_modes(self):
        aa = AntiAliasingEngine(mode="FXAA")
        surf = pygame.Surface((128, 128))
        pygame.draw.line(surf, (255, 255, 255), (0, 0), (128, 128), 2)
        out = aa.apply(surf)
        self.assertEqual(out.get_size(), (128, 128))

    def test_weather_engine_presets(self):
        pe = ParticleEngine(capacity=200)
        weather = WeatherEngine(pe)
        weather.set_stage_preset("Catacumbas")
        self.assertEqual(weather.current_weather, "dust")

        weather.set_stage_preset("Floresta Ancestral")
        self.assertEqual(weather.current_weather, "leaves")

        weather.update(0.016, pygame.Rect(0, 0, 512, 384))

    def test_camera_v3_trauma_and_lookahead(self):
        cam = CameraV3(2000, 1000, 512, 384)
        target = pygame.FRect(200, 200, 32, 48)
        cam.add_trauma(0.8)
        cam.update(target, target_facing=1, target_vx=100.0, dt=0.016)
        self.assertGreater(cam.trauma, 0.0)
        off = cam.offset
        self.assertIsInstance(off, pygame.math.Vector2)

    def test_master_render_pipeline_15_passes(self):
        pipe = MasterRenderPipeline(512, 384, 512, 384)
        cam = CameraV3(1000, 600, 512, 384)
        internal = pygame.Surface((512, 384))
        window = pygame.Surface((512, 384))

        lights = [
            LightRayCaster(), # Dummy object with x, y, radius
        ]
        lights[0].x = 250
        lights[0].y = 200
        lights[0].radius = 70
        lights[0].color = (255, 180, 80)
        lights[0].intensity = 1.0

        occluders = [(200, 180, 200, 240)]

        pipe.execute(
            internal_buf=internal,
            window_buf=window,
            camera=cam,
            draw_background_callback=lambda s, o: s.fill((20, 25, 35)),
            draw_world_callback=None,
            draw_hud_callback=None,
            lights=lights,
            occluders=occluders,
            entities=[],
            stage_theme="forest",
            dt=0.016
        )
        self.assertGreaterEqual(PROFILER.metrics["draw_calls"], 1)

if __name__ == "__main__":
    unittest.main()
