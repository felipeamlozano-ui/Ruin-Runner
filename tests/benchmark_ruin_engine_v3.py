"""
Ruin Engine V3.0 — Comprehensive Production Benchmark Suite.
Measures real performance metrics (FPS, Frametime, RAM, CPU, Ray Casting, Bloom, Blur, FSR, and Particles)
on the target Ryzen 5 5500U profile.
"""

import os
import sys
import time
from pathlib import Path
import psutil
import numpy as np
import pygame

sys.path.append(str(Path(__file__).parent.parent / "src"))

pygame.init()
pygame.display.set_mode((512, 384))

from engine.v3.core.jit_backend import get_jit_info
from engine.v3.core.profiler import PROFILER
from engine.v3.core.adaptive_quality import ADAPTIVE_QUALITY
from engine.v3.lighting.raycasting2d import LightRayCaster
from engine.v3.lighting.shadows import ShadowRenderer
from engine.v3.particles.particle_engine import ParticleEngine, PARTICLE_BLOOD, PARTICLE_FIRE
from engine.v3.postfx.bloom import BloomEngine
from engine.v3.upscaling.fsr2d import FSR2D
from engine.v3.upscaling.antialiasing import AntiAliasingEngine
from engine.v3.camera.camera_v3 import CameraV3
from engine.v3.core.pipeline import MasterRenderPipeline

def run_benchmarks():
    print("=" * 72)
    print(" RUIN ENGINE V3.0 — PRODUCTION BENCHMARK SUITE")
    print(" Hardware Target: AMD Ryzen 5 5500U (Vega 7 iGPU, 6C/12T, 8GB RAM)")
    print(f" Backend: {get_jit_info()['backend']}")
    print("=" * 72)

    process = psutil.Process(os.getpid())
    results = {}

    # 1. 2D Ray Casting Benchmark
    print("\n[1/7] Benchmarking 2D Ray Casting (Visibility Polygons)...")
    caster = LightRayCaster()
    occluders = [
        (float(i * 30), 100.0, float(i * 30 + 20), 100.0) for i in range(25)
    ] + [
        (150.0, float(i * 25), 150.0, float(i * 25 + 15)) for i in range(20)
    ]

    ray_iterations = 200
    t0 = time.perf_counter()
    for _ in range(ray_iterations):
        caster.compute_visibility_polygon(250.0, 180.0, 160.0, occluders)
    t1 = time.perf_counter()
    avg_ray_time_ms = ((t1 - t0) / ray_iterations) * 1000.0
    results["ray_casting_ms"] = avg_ray_time_ms
    print(f"  -> Ray Casting Latency: {avg_ray_time_ms:.3f} ms per light source")

    # 2. Shadow Polygons Benchmark
    print("\n[2/7] Benchmarking 2D Shadow Polygon Extrusion (Soft Penumbra)...")
    shadows = ShadowRenderer(shadow_length=400.0)
    shadow_iterations = 150
    t0 = time.perf_counter()
    for _ in range(shadow_iterations):
        mask = shadows.render_shadow_mask(512, 384, 250.0, 180.0, 160.0, occluders, pygame.math.Vector2(0, 0), soft_rays=4)
    t1 = time.perf_counter()
    avg_shadow_time_ms = ((t1 - t0) / shadow_iterations) * 1000.0
    results["shadow_polygons_ms"] = avg_shadow_time_ms
    print(f"  -> Shadow Polygons Latency (4-ray soft): {avg_shadow_time_ms:.3f} ms per frame")

    # 3. Particle System Kinematics Benchmark
    print("\n[3/7] Benchmarking GPU-Style Particle Engine (SoA NumPy/Numba SIMD)...")
    particle_counts = [1000, 2000, 4000]
    particle_results = {}

    for count in particle_counts:
        pe = ParticleEngine(capacity=count)
        # Pre-fill
        for _ in range(count):
            pe.spawn(256.0, 192.0, np.random.uniform(-100, 100), np.random.uniform(-100, 100), (255, 100, 50, 255), size=2.5, lifetime=2.0)

        p_iterations = 120
        t0 = time.perf_counter()
        for _ in range(p_iterations):
            pe.update(0.016)
        t1 = time.perf_counter()
        avg_particle_ms = ((t1 - t0) / p_iterations) * 1000.0
        particle_results[count] = avg_particle_ms
        print(f"  -> {count:4d} Particles Kinematics: {avg_particle_ms:.3f} ms/frame ({count / (avg_particle_ms * 0.001):,.0f} particles/sec)")
    results["particles"] = particle_results

    # 4. HDR Bloom Multipass Benchmark
    print("\n[4/7] Benchmarking HDR Bloom (Threshold + Separable 1D Blur + Additive Composite)...")
    bloom = BloomEngine(512, 384, downsample_scale=0.25)
    test_surf = pygame.Surface((512, 384))
    test_surf.fill((30, 40, 60))
    pygame.draw.circle(test_surf, (255, 240, 200), (256, 192), 60)
    pygame.draw.circle(test_surf, (255, 255, 255), (100, 100), 40)

    bloom_iterations = 100
    t0 = time.perf_counter()
    for _ in range(bloom_iterations):
        bloom.apply_bloom(test_surf, threshold=0.70, intensity=1.2, blur_radius=4)
    t1 = time.perf_counter()
    avg_bloom_ms = ((t1 - t0) / bloom_iterations) * 1000.0
    results["bloom_ms"] = avg_bloom_ms
    print(f"  -> HDR Bloom Pass Latency: {avg_bloom_ms:.3f} ms per frame")

    # 5. FSR 2D & EASU + RCAS Sharpening Benchmark
    print("\n[5/7] Benchmarking FSR 2D Upscaling (EASU + Contrast-Adaptive Sharpening)...")
    fsr_targets = [
        ("720p", 1280, 720),
        ("900p", 1600, 900),
        ("1080p", 1920, 1080)
    ]
    fsr_results = {}

    for res_name, tw, th in fsr_targets:
        fsr = FSR2D(tw, th, preset="Balanced")
        low_res = pygame.Surface((fsr.vw, fsr.vh))
        low_res.fill((60, 80, 120))
        pygame.draw.rect(low_res, (220, 180, 70), (40, 40, 80, 80))

        # Warmup
        fsr.upscale(low_res)

        fsr_iterations = 60
        t0 = time.perf_counter()
        for _ in range(fsr_iterations):
            fsr.upscale(low_res)
        t1 = time.perf_counter()
        avg_fsr_ms = ((t1 - t0) / fsr_iterations) * 1000.0
        fsr_results[res_name] = avg_fsr_ms
        print(f"  -> FSR 2D Upscale to {res_name} ({tw}x{th}): {avg_fsr_ms:.3f} ms/frame")
    results["fsr"] = fsr_results

    # 6. Anti-Aliasing (FXAA) Benchmark
    print("\n[6/7] Benchmarking Fast Approximate Anti-Aliasing (FXAA)...")
    aa = AntiAliasingEngine(mode="FXAA")
    aa_iterations = 60
    t0 = time.perf_counter()
    for _ in range(aa_iterations):
        aa.apply(test_surf)
    t1 = time.perf_counter()
    avg_aa_ms = ((t1 - t0) / aa_iterations) * 1000.0
    results["fxaa_ms"] = avg_aa_ms
    print(f"  -> FXAA Edge Smoothing Latency: {avg_aa_ms:.3f} ms per frame")

    # 7. End-to-End Master Pipeline (All 15 Passes Active)
    print("\n[7/7] Benchmarking Full 15-Pass Master Rendering Pipeline...")
    pipe = MasterRenderPipeline(512, 384, 1280, 720)
    cam = CameraV3(2048, 768, 512, 384)
    internal_buf = pygame.Surface((512, 384))
    window_buf = pygame.Surface((1280, 720))

    # Spawn test particles and lights
    pipe.particles.spawn_burst(256, 192, count=300, p_type=PARTICLE_BLOOD)
    pipe.particles.spawn_burst(200, 150, count=300, p_type=PARTICLE_FIRE)

    class MockLight:
        def __init__(self, x, y, r, c):
            self.x, self.y, self.radius, self.color, self.intensity = x, y, r, c, 1.0

    lights = [
        MockLight(200, 180, 90, (255, 180, 60)),
        MockLight(350, 220, 80, (120, 180, 255))
    ]

    full_iterations = 180
    t0 = time.perf_counter()
    for _ in range(full_iterations):
        pipe.execute(
            internal_buf=internal_buf,
            window_buf=window_buf,
            camera=cam,
            draw_background_callback=lambda s, o: s.fill((25, 30, 42)),
            draw_world_callback=None,
            draw_hud_callback=None,
            lights=lights,
            occluders=occluders,
            entities=[],
            stage_theme="forest",
            dt=0.016
        )
    t1 = time.perf_counter()

    total_time = t1 - t0
    avg_frame_time_ms = (total_time / full_iterations) * 1000.0
    measured_fps = full_iterations / total_time
    mem_info = process.memory_info()
    ram_mb = mem_info.rss / (1024 * 1024)
    cpu_pct = process.cpu_percent()

    results["full_pipeline_ms"] = avg_frame_time_ms
    results["fps"] = measured_fps
    results["ram_mb"] = ram_mb

    print("-" * 72)
    print(f" FULL PIPELINE FRAME TIME : {avg_frame_time_ms:6.3f} ms")
    print(f" EQUIVALENT FRAMERATE     : {measured_fps:6.1f} FPS")
    print(f" PROCESS RAM FOOTPRINT    : {ram_mb:6.1f} MB (Budget: <500 MB on 8GB machine)")
    print("-" * 72)

    return results

if __name__ == "__main__":
    run_benchmarks()
