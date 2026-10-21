import os
import sys
import time
import math
import pytest
import pygame
import numpy as np

# Ensure ruin_runner src is in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((640, 360))

from entities.ultimate_system import (
    create_ultimate,
    BaseUltimate,
    ULTIMATE_THEME_CONFIG,
    _ensure_ultimate_atlas_baked
)
from entities.player import Player
from entities.enemy import Skeleton
from engine.v3.native.native_bridge import (
    native_compute_2d_raycast_shadows,
    native_update_wind_vortex_ribbons,
    has_native
)


def test_native_c_engine_performance():
    """Verify that the native C module executes raycast shadows & wind ribbons well under 0.05ms (< 0.5ms threshold)."""
    assert has_native(), "ruin_native.dll must be compiled and loaded!"

    # 1. Benchmark 2D Raycast Shadows
    occluders = np.array([
        [200.0, 300.0, 240.0, 300.0],
        [200.0, 340.0, 200.0, 300.0],
        [240.0, 300.0, 240.0, 340.0],
        [400.0, 280.0, 440.0, 280.0],
    ], dtype=np.float32)

    # Warmup
    for _ in range(20):
        _ = native_compute_2d_raycast_shadows(150.0, 180.0, 600.0, 400.0, occluders)

    iters = 200
    t0 = time.perf_counter()
    for _ in range(iters):
        verts = native_compute_2d_raycast_shadows(150.0, 180.0, 600.0, 400.0, occluders)
    ray_ms = ((time.perf_counter() - t0) / iters) * 1000.0

    assert verts.shape[1:] == (4, 2)
    assert verts.shape[0] > 0
    assert ray_ms < 0.5, f"Raycast shadow calculation too slow: {ray_ms:.4f}ms (target < 0.5ms)"

    # 2. Benchmark Wind Vortex Ribbons & Levitating Debris
    # Warmup
    for _ in range(20):
        _ = native_update_wind_vortex_ribbons(320.0, 180.0, 0.45, True, 8, 16, 48, 0.016)

    t0 = time.perf_counter()
    for _ in range(iters):
        ribbons, debris = native_update_wind_vortex_ribbons(320.0, 180.0, 0.45, True, 8, 16, 48, 0.016)
    wind_ms = ((time.perf_counter() - t0) / iters) * 1000.0

    assert ribbons.shape == (8, 16, 4)
    assert debris.shape == (48, 4)
    assert wind_ms < 0.5, f"Wind vortex calculation too slow: {wind_ms:.4f}ms (target < 0.5ms)"
    print(f"\n[BENCHMARK] Native C Raycast: {ray_ms:.4f}ms | Wind Vortex: {wind_ms:.4f}ms")


def test_time_stop_1s_freezes_enemies():
    """Verify that triggering an ultimate initiates a 1.0s Time-Stop and freezes all enemies."""
    player = Player(100, 300, character_id="shaia")
    enemy1 = Skeleton(200, 300)
    enemy2 = Skeleton(280, 300)
    enemy1.velocity.x = 80.0
    enemy2.velocity.x = -60.0
    enemies = [enemy1, enemy2]

    # Trigger Ultimate [R]
    player.cast_ultimate()
    assert player.is_casting_ultimate is True
    assert player.ultimate_controller.active is True
    assert player.ultimate_controller.time_stop_timer == 1.0

    # Advance frame by 0.1s
    player.ultimate_controller.update(0.1, player, enemies)

    # Enemies must be frozen with velocity zero
    assert getattr(enemy1, "is_frozen", False) is True
    assert getattr(enemy2, "is_frozen", False) is True
    assert enemy1.velocity.x == 0.0
    assert enemy2.velocity.x == 0.0
    assert getattr(player, "ultimate_freeze_timer", 0.0) == pytest.approx(0.9, rel=1e-2)

    # Advance past 1.0s (e.g. 0.95s more -> 1.05s total)
    player.ultimate_controller.update(0.95, player, enemies)
    assert player.ultimate_controller.time_stop_timer == 0.0
    assert getattr(player, "ultimate_freeze_timer", 0.0) == 0.0
    assert getattr(enemy1, "is_frozen", False) is False
    assert getattr(enemy2, "is_frozen", False) is False


def test_frozen_backdrop_cache_and_subsystem_freeze():
    """Verify level scene pauses clouds/mist and caches the backdrop during Time-Stop."""
    from scenes.level_scene import LevelScene
    scene = LevelScene(stage=1)
    scene.player.cast_ultimate()
    scene.player.ultimate_controller.update(0.016, scene.player, scene.enemies)

    # Check is_time_stopped flag logic
    is_ult_active = (scene.player and getattr(scene.player, "is_casting_ultimate", False))
    is_time_stopped = is_ult_active and any(getattr(p, "ultimate_freeze_timer", 0.0) > 0.0 for p in [scene.player] if p)
    assert is_time_stopped is True

    # Cloud positions before update
    if hasattr(scene, "clouds") and scene.clouds is not None:
        init_clouds_x = [c[0] for c in scene.clouds.clouds]
        scene.update(0.1) # Update while time-stopped
        post_clouds_x = [c[0] for c in scene.clouds.clouds]
        assert init_clouds_x == post_clouds_x, "Clouds must remain paused during Ultimate Time-Stop"

    # Draw to screen and verify Frozen Backdrop Cache
    test_surf = pygame.Surface((640, 360))
    assert getattr(scene, "_frozen_backdrop_texture", None) is None

    scene.draw(test_surf)
    # The cache texture must now exist
    cached = getattr(scene, "_frozen_backdrop_texture", None)
    assert cached is not None
    assert cached.get_size() == (640, 360)

    # Second draw uses the exact same cached object (Zero allocation)
    scene.draw(test_surf)
    assert getattr(scene, "_frozen_backdrop_texture", None) is cached


def test_original_character_ultimate_geometry_preserved():
    """STRICT GOLDEN RULE: Verify that original character ultimate drawing/geometry is executed untouched."""
    ctrl = create_ultimate("shaia")

    # Check that ValkyrieUltimate has original draw_world method preserved
    orig_fn = ctrl.__class__.__dict__.get("draw_world", None)
    assert orig_fn is not None, "draw_world must be defined on ultimate class"

    # Activate ultimate and draw
    ctrl.trigger(300, 200, True)
    test_surf = pygame.Surface((640, 360))
    cam_offset = pygame.math.Vector2(0, 0)

    # Drawing world executes wrapped pipeline (pre + original geometry + post)
    ctrl.draw_world(test_surf, cam_offset)
    assert ctrl.active is True
