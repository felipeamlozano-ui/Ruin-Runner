"""
Ruin Runner — Production Reproducible Benchmark & Stress Test Suite.
Implements the 8 required benchmark scenarios:
1. Benchmark_Catacombs
2. Benchmark_AncientForest
3. Benchmark_Crypt
4. Benchmark_ForbiddenForest
5. Benchmark_Boss
6. Benchmark_Coop
7. Benchmark_MaxVFX
8. Benchmark_MaxParticles
And the extreme STRESS TEST scenario (100+ enemies, 4000+ particles, 30+ lights, dual coop players).
Outputs detailed metrics and writes performance_baseline.json.
"""

import os
import sys
import time
import json
import argparse
import psutil
import pygame
import numpy as np

# Bootstrap Python paths
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Headless mode for automated benchmarks if desired
if "--headless" in sys.argv:
    os.environ["SDL_VIDEODRIVER"] = "dummy"

from config.settings import SETTINGS
from engine.camera import Camera
from engine.lighting import LightingEngine, LightSource
from engine.v3.core.profiler import PROFILER
from engine.v3.core.pipeline import MasterRenderPipeline
from engine.v3.postfx.bloom import BloomEngine
from engine.v3.upscaling.ruin_upscaler import RuinTemporalUpscaler
from engine.v3.particles.particle_engine import ParticleEngine
from engine.v3.lighting.materials import MATERIAL_REGISTRY, MaterialType
from engine.v3.native.native_bridge import has_native
from entities.player import Player
from entities.enemy import Skeleton, MageSkeleton, WildBoar
from entities.boss import SkeletonBoss
from entities.coop_synergy import CoopSynergySystem


def run_scenario(name: str, duration_sec: float, setup_fn, update_draw_fn) -> dict:
    """Executes a benchmark scenario with warmup and telemetry recording."""
    print(f"\n========================================================================")
    print(f" RUNNING: {name}")
    print(f" Target: 60+ FPS (<= 16.67 ms) | Duration: {duration_sec:.1f}s")
    print(f"========================================================================")

    ctx = setup_fn()

    # 1. Warm-up phase (50 frames)
    for _ in range(50):
        update_draw_fn(ctx, 0.016)

    # 2. Main benchmark capture
    frame_times = []
    start_time = time.perf_counter()
    end_time = start_time + duration_sec
    process = psutil.Process()

    while time.perf_counter() < end_time:
        t0 = time.perf_counter()
        update_draw_fn(ctx, 0.016)
        t1 = time.perf_counter()
        frame_times.append((t1 - t0) * 1000.0)

    # 3. Telemetry calculations
    ft_arr = np.array(frame_times, dtype=np.float64)
    total_frames = len(ft_arr)
    avg_frametime = float(np.mean(ft_arr))
    avg_fps = 1000.0 / avg_frametime if avg_frametime > 0 else 0.0
    p50 = float(np.percentile(ft_arr, 50))
    p95 = float(np.percentile(ft_arr, 95))
    p99 = float(np.percentile(ft_arr, 99))
    variance = float(np.var(ft_arr))

    # 1% low & 0.1% low
    sorted_ft = np.sort(ft_arr)
    one_pct_idx = max(0, int(total_frames * 0.99))
    point_one_idx = max(0, int(total_frames * 0.999))
    one_percent_low = 1000.0 / sorted_ft[one_pct_idx] if sorted_ft[one_pct_idx] > 0 else 0.0
    point_one_percent_low = 1000.0 / sorted_ft[point_one_idx] if sorted_ft[point_one_idx] > 0 else 0.0

    ram_mb = process.memory_info().rss / (1024 * 1024)
    cpu_pct = process.cpu_percent()

    print(f"  Total Frames Rendered : {total_frames:,}")
    print(f"  Average Framerate      : {avg_fps:6.1f} FPS")
    print(f"  Average Frame Time     : {avg_frametime:6.2f} ms")
    print(f"  Frame Pacing (P50/P99) : P50={p50:.2f}ms | P95={p95:.2f}ms | P99={p99:.2f}ms")
    print(f"  1% Low / 0.1% Low      : 1%={one_percent_low:5.1f} FPS | 0.1%={point_one_percent_low:5.1f} FPS")
    print(f"  Frame-time Variance    : {variance:.4f} ms^2")
    print(f"  RAM Footprint          : {ram_mb:5.1f} MB (Budget: <500 MB)")

    return {
        "scenario": name,
        "total_frames": total_frames,
        "avg_fps": round(avg_fps, 2),
        "avg_frametime_ms": round(avg_frametime, 3),
        "p50_ms": round(p50, 3),
        "p95_ms": round(p95, 3),
        "p99_ms": round(p99, 3),
        "one_percent_low_fps": round(one_percent_low, 2),
        "point_one_percent_low_fps": round(point_one_percent_low, 2),
        "frametime_variance": round(variance, 4),
        "ram_mb": round(ram_mb, 2),
        "cpu_percent": round(cpu_pct, 2)
    }


def setup_level_scene(stage: int, coop: bool = False):
    from scenes.level_scene import LevelScene
    SETTINGS.COOP_ENABLED = coop
    scene = LevelScene(stage=stage)
    surface = pygame.Surface((512, 384))
    return {"scene": scene, "surface": surface}

def update_draw_level(ctx, dt: float):
    scene = ctx["scene"]
    surf = ctx["surface"]
    scene.update(dt)
    scene.draw(surf)


def setup_boss_scene(coop: bool = False):
    from scenes.boss_scene import BossScene
    SETTINGS.COOP_ENABLED = coop
    scene = BossScene(None)
    surface = pygame.Surface((512, 384))
    return {"scene": scene, "surface": surface}

def update_draw_boss(ctx, dt: float):
    scene = ctx["scene"]
    surf = ctx["surface"]
    scene.update(dt)
    scene.draw(surf)


def setup_max_vfx():
    surface = pygame.Surface((512, 384))
    bloom = BloomEngine(512, 384)
    upscaler = RuinTemporalUpscaler(1280, 720, preset="Balanced")
    particles = ParticleEngine(capacity=4000)
    lighting = LightingEngine(theme="forest")

    # Spawn glowing orbs & lights
    lights = [
        LightSource(100 + i * 40, 150 + (i % 3) * 30, 70, (255, 180, 50), 0.9, True)
        for i in range(12)
    ]
    return {
        "surface": surface,
        "bloom": bloom,
        "upscaler": upscaler,
        "particles": particles,
        "lighting": lighting,
        "lights": lights,
        "time": 0.0
    }

def update_draw_max_vfx(ctx, dt: float):
    surf = ctx["surface"]
    bloom = ctx["bloom"]
    upscaler = ctx["upscaler"]
    particles = ctx["particles"]
    lighting = ctx["lighting"]
    lights = ctx["lights"]
    ctx["time"] += dt

    surf.fill((20, 25, 40))

    # Burst particles
    particles.spawn_burst(256, 192, 50, (255, 200, 80), speed_range=(80, 300))
    particles.update(dt)
    particles.render(surf, pygame.math.Vector2(0, 0))

    # Lighting & Volumetrics
    lighting.draw_point_lights(surf, lights, pygame.math.Vector2(0, 0))
    lighting.draw_god_rays(surf, pygame.math.Vector2(0, 0))

    # Physical Bloom
    bloom.apply_bloom(surf, threshold=0.70, intensity=1.2)

    # Ruin TSR Upscale to 720p
    upscaled = upscaler.upscale(surf, cam_x=ctx["time"] * 20.0, cam_y=0.0)


def setup_max_particles():
    surface = pygame.Surface((512, 384))
    particles = ParticleEngine(capacity=4000)
    # Pre-spawn 4000 particles
    for i in range(400):
        particles.spawn_burst(
            (i * 13) % 512,
            (i * 17) % 384,
            10,
            (255, 160 + (i % 80), 50),
            speed_range=(60, 220)
        )
    return {"surface": surface, "particles": particles}

def update_draw_max_particles(ctx, dt: float):
    surf = ctx["surface"]
    particles = ctx["particles"]
    surf.fill((15, 15, 25))
    particles.update(dt)
    particles.render(surf, pygame.math.Vector2(0, 0))


def setup_stress_test():
    """
    STRESS TEST SCENARIO:
    - 100+ active enemies with collision & AI
    - 4,000 particles
    - 30 dynamic point lights
    - Dual Co-op players with active auras
    - Volumetric lighting + Bloom + TSR Upscaler
    """
    surface = pygame.Surface((512, 384))
    cam = Camera(4000, 480)
    p1 = Player(300, 320, character_id="shaia", player_index=0)
    p2 = Player(380, 320, character_id="aurelia", player_index=1)
    p1.companion = p2
    p2.companion = p1

    enemies = []
    for i in range(110):
        ex = 150 + (i * 32)
        ey = 320
        if i % 3 == 0:
            enemies.append(MageSkeleton(ex, ey))
        elif i % 3 == 1:
            enemies.append(WildBoar(ex, ey))
        else:
            enemies.append(Skeleton(ex, ey))

    particles = ParticleEngine(capacity=4000)
    bloom = BloomEngine(512, 384)
    lighting = LightingEngine(theme="dungeon")
    lights = [
        LightSource(200 + i * 90, 280, 65, (255, 120 + (i % 100), 50), 0.8, True)
        for i in range(32)
    ]
    upscaler = RuinTemporalUpscaler(1280, 720, preset="Balanced")
    solid_rects = [pygame.FRect(0, 340, 4000, 50)]

    return {
        "surface": surface,
        "camera": cam,
        "p1": p1,
        "p2": p2,
        "enemies": enemies,
        "particles": particles,
        "bloom": bloom,
        "lighting": lighting,
        "lights": lights,
        "upscaler": upscaler,
        "solid_rects": solid_rects
    }

def update_draw_stress(ctx, dt: float):
    surf = ctx["surface"]
    cam = ctx["camera"]
    p1 = ctx["p1"]
    p2 = ctx["p2"]
    enemies = ctx["enemies"]
    particles = ctx["particles"]
    bloom = ctx["bloom"]
    lighting = ctx["lighting"]
    lights = ctx["lights"]
    upscaler = ctx["upscaler"]
    solid_rects = ctx["solid_rects"]

    # Update players
    p1.update(dt, solid_rects, enemies, cam)
    p2.update(dt, solid_rects, enemies, cam)
    cam.update_coop(p1, p2, dt)

    # Update enemies targeting nearest player
    for e in enemies:
        t = p1 if abs(e.rect.centerx - p1.rect.centerx) < abs(e.rect.centerx - p2.rect.centerx) else p2
        e.update(dt, solid_rects, t)

    # Particles
    particles.spawn_burst(p1.rect.centerx, p1.rect.centery, 25, (255, 200, 100))
    particles.update(dt)

    # Render
    surf.fill((20, 20, 30))
    for e in enemies:
        if cam.viewport.colliderect(e.rect):
            e.draw(surf, cam.offset)
    p1.draw(surf, cam.offset)
    p2.draw(surf, cam.offset)
    particles.render(surf, cam.offset)
    lighting.draw_point_lights(surf, lights, cam.offset)
    bloom.apply_bloom(surf, threshold=0.72, intensity=1.0)
    upscaler.upscale(surf, cam_x=cam.offset.x, cam_y=cam.offset.y)


def main():
    parser = argparse.ArgumentParser(description="Ruin Runner AAA Benchmark Suite")
    parser.add_argument("--duration", type=float, default=5.0, help="Duration in seconds per scenario")
    parser.add_argument("--stress-only", action="store_true", help="Run only the extreme stress test")
    parser.add_argument("--headless", action="store_true", help="Run headlessly with dummy video driver")
    parser.add_argument("--output", type=str, default="performance_baseline.json", help="Output JSON path")
    args = parser.parse_args()

    pygame.init()
    pygame.display.set_mode((1280, 720))

    results = []

    if args.stress_only:
        res = run_scenario("Benchmark_StressTest_100Enemies_4000Particles", args.duration, setup_stress_test, update_draw_stress)
        results.append(res)
    else:
        scenarios = [
            ("Benchmark_Catacombs", lambda: setup_level_scene(stage=1, coop=False), update_draw_level),
            ("Benchmark_AncientForest", lambda: setup_level_scene(stage=2, coop=False), update_draw_level),
            ("Benchmark_Crypt", lambda: setup_level_scene(stage=3, coop=False), update_draw_level),
            ("Benchmark_ForbiddenForest", lambda: setup_level_scene(stage=4, coop=False), update_draw_level),
            ("Benchmark_Boss", lambda: setup_boss_scene(coop=False), update_draw_boss),
            ("Benchmark_Coop", lambda: setup_level_scene(stage=2, coop=True), update_draw_level),
            ("Benchmark_MaxVFX", setup_max_vfx, update_draw_max_vfx),
            ("Benchmark_MaxParticles", setup_max_particles, update_draw_max_particles),
            ("Benchmark_StressTest_Extreme", setup_stress_test, update_draw_stress),
        ]

        for name, setup_fn, update_draw_fn in scenarios:
            res = run_scenario(name, args.duration, setup_fn, update_draw_fn)
            results.append(res)

    # Save to JSON
    baseline_path = args.output
    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hardware_target": "AMD Ryzen 5 5500U (Vega 7 iGPU, 6C/12T, 8GB RAM)",
        "platform": sys.platform,
        "python_version": sys.version,
        "pygame_version": pygame.version.ver,
        "native_c_simd_active": has_native(),
        "scenarios": results
    }

    with open(baseline_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n[Ruin Engine V3.0] Baseline saved to: {baseline_path}")


if __name__ == "__main__":
    main()
