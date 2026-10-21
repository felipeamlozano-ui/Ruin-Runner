"""
tests/test_presets_and_duel.py
------------------------------
Unit tests for:
1. Standardized Graphics Presets (Low, Medium, High, Ultra) and persistence.
2. Low-level System Optimizer (GC Freeze, Vectorized NumPy arrays, Texture Pool).
3. Silksong Game Feel Engine (Hit-stop, directional micro-shake, pooled dust, slash arcs).
4. Modo de Duelo 1v1 (DuelCharacterSelectScene, DuelScene, round state machine, HUD).
"""

import os
import sys
import gc
import json
import unittest
from pathlib import Path

# Add project root and src to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
pygame.init()
pygame.display.set_mode((640, 360))

from config.settings import SETTINGS
from engine.system_optimizer import (
    freeze_gc_for_gameplay,
    collect_garbage_transition,
    VectorizedParticleSystem,
    TexturePool,
    create_hardware_display,
    RENDER_FALLBACK_CHAIN
)
from engine.game_feel import GAME_FEEL
from scenes.main_menu import MainMenuScene
from scenes.duel_character_select_scene import DuelCharacterSelectScene, ROSTER_GRID
from scenes.duel_scene import DuelScene
from engine.scene_manager import SceneManager


class TestGraphicsPresets(unittest.TestCase):
    """Tests the 4 master graphics presets and settings persistence."""

    def setUp(self):
        self.original_preset = SETTINGS.GRAPHICS_PRESET

    def tearDown(self):
        SETTINGS.apply_graphics_preset(self.original_preset)

    def test_low_preset(self):
        SETTINGS.apply_graphics_preset("low")
        self.assertEqual(SETTINGS.GRAPHICS_PRESET, "low")
        self.assertEqual(SETTINGS.CLOUDS_COUNT, 0)
        self.assertEqual(SETTINGS.MIST_LAYERS, 0)
        self.assertFalse(SETTINGS.AMBIENT_PARTICLES)
        self.assertFalse(SETTINGS.RAYTRACING_ENABLED)
        self.assertFalse(SETTINGS.DYNAMIC_LIGHTS)
        self.assertFalse(SETTINGS.BLOOM_ENABLED)
        self.assertFalse(SETTINGS.CONTACT_AO)
        self.assertFalse(SETTINGS.FOREGROUND_SILHOUETTE)
        self.assertTrue(SETTINGS.VIGNETTE_ENABLED)
        self.assertFalse(SETTINGS.GAME_FEEL_REACTIVE)

    def test_medium_preset(self):
        SETTINGS.apply_graphics_preset("medium")
        self.assertEqual(SETTINGS.GRAPHICS_PRESET, "medium")
        self.assertEqual(SETTINGS.CLOUDS_COUNT, 8)
        self.assertEqual(SETTINGS.MIST_LAYERS, 1)
        self.assertTrue(SETTINGS.AMBIENT_PARTICLES)
        self.assertEqual(SETTINGS.AMBIENT_PARTICLES_COUNT, 15)
        self.assertFalse(SETTINGS.RAYTRACING_ENABLED)
        self.assertFalse(SETTINGS.DYNAMIC_LIGHTS)
        self.assertFalse(SETTINGS.BLOOM_ENABLED)
        self.assertTrue(SETTINGS.STATIC_AO)
        self.assertFalse(SETTINGS.CONTACT_AO)
        self.assertTrue(SETTINGS.FOREGROUND_SILHOUETTE)
        self.assertTrue(SETTINGS.VIGNETTE_ENABLED)

    def test_high_preset(self):
        SETTINGS.apply_graphics_preset("high")
        self.assertEqual(SETTINGS.GRAPHICS_PRESET, "high")
        self.assertEqual(SETTINGS.CLOUDS_COUNT, 14)
        self.assertEqual(SETTINGS.MIST_LAYERS, 3)
        self.assertTrue(SETTINGS.AMBIENT_PARTICLES)
        self.assertEqual(SETTINGS.AMBIENT_PARTICLES_COUNT, 30)
        self.assertTrue(SETTINGS.RAYTRACING_ENABLED)
        self.assertTrue(SETTINGS.DYNAMIC_LIGHTS)
        self.assertTrue(SETTINGS.BLOOM_ENABLED)
        self.assertTrue(SETTINGS.STATIC_AO)
        self.assertTrue(SETTINGS.CONTACT_AO)
        self.assertTrue(SETTINGS.FOREGROUND_SILHOUETTE)
        self.assertTrue(SETTINGS.VIGNETTE_ENABLED)
        self.assertTrue(SETTINGS.GAME_FEEL_REACTIVE)

    def test_ultra_preset(self):
        SETTINGS.apply_graphics_preset("ultra")
        self.assertEqual(SETTINGS.GRAPHICS_PRESET, "ultra")
        self.assertEqual(SETTINGS.CLOUDS_COUNT, 20)
        self.assertEqual(SETTINGS.MIST_LAYERS, 3)
        self.assertTrue(SETTINGS.AMBIENT_PARTICLES)
        self.assertEqual(SETTINGS.AMBIENT_PARTICLES_COUNT, 60)
        self.assertTrue(SETTINGS.RAYTRACING_ENABLED)
        self.assertTrue(SETTINGS.DYNAMIC_LIGHTS)
        self.assertTrue(SETTINGS.BLOOM_ENABLED)
        self.assertTrue(SETTINGS.STATIC_AO)
        self.assertTrue(SETTINGS.CONTACT_AO)
        self.assertTrue(SETTINGS.FOREGROUND_SILHOUETTE)
        self.assertTrue(SETTINGS.VIGNETTE_ENABLED)
        self.assertTrue(SETTINGS.GAME_FEEL_REACTIVE)

    def test_settings_save_and_load(self):
        test_file = PROJECT_ROOT / "config" / "test_temp_settings.json"
        try:
            SETTINGS.apply_graphics_preset("ultra")
            SETTINGS.save_settings(str(test_file))
            self.assertTrue(test_file.exists())

            # Temporarily change
            SETTINGS.apply_graphics_preset("low")
            self.assertEqual(SETTINGS.GRAPHICS_PRESET, "low")

            # Load back
            SETTINGS.load_settings(str(test_file))
            self.assertEqual(SETTINGS.GRAPHICS_PRESET, "ultra")
        finally:
            if test_file.exists():
                test_file.unlink()


class TestSystemOptimizer(unittest.TestCase):
    """Tests GC Freeze, Vectorized particles, and Texture Pool."""

    def test_gc_freeze(self):
        freeze_gc_for_gameplay("TestCombat")
        self.assertFalse(gc.isenabled())
        collect_garbage_transition()
        self.assertFalse(gc.isenabled())  # Stays disabled during gameplay
        gc.enable()  # Reset

    def test_vectorized_particles(self):
        ps = VectorizedParticleSystem(count=45, bounds=(640, 360))
        self.assertEqual(len(ps.x), 45)
        self.assertEqual(len(ps.y), 45)
        self.assertEqual(ps.x.dtype, "float32")

        # Vectorized update
        ps.update(dt=0.016, wind=5.0)
        positions = ps.get_positions()
        self.assertEqual(positions.shape, (45, 2))
        self.assertTrue((positions[:, 0] >= 0).all())
        self.assertTrue((positions[:, 0] <= 640).all())

        # Resize count
        ps.set_count(15)
        self.assertEqual(len(ps.x), 15)

    def test_texture_pool(self):
        surf = TexturePool.get_or_create("temp_test_ao", 32, 32, has_alpha=True)
        self.assertIsNotNone(surf)
        self.assertEqual(surf.get_size(), (32, 32))
        TexturePool.clear_stage_buffers()
        self.assertIsNone(TexturePool.get("temp_test_ao"))

    def test_vulkan_render_driver_and_fallback(self):
        self.assertEqual(RENDER_FALLBACK_CHAIN[0], "vulkan")
        self.assertIn("direct3d11", RENDER_FALLBACK_CHAIN)
        self.assertIn("opengl", RENDER_FALLBACK_CHAIN)
        display_surf, active_driver = create_hardware_display((640, 360), pygame.SCALED)
        self.assertIsNotNone(display_surf)
        self.assertEqual(display_surf.get_size(), (640, 360))
        self.assertIn(active_driver, ["vulkan", "direct3d11", "opengl", "software"])


class TestGameFeelEngine(unittest.TestCase):
    """Tests hit-stop, directional micro-shake, and object pooled VFX."""

    def setUp(self):
        SETTINGS.GAME_FEEL_REACTIVE = True
        SETTINGS.DYNAMIC_LIGHTS = True

    def test_hit_stop_and_shake(self):
        dummy_entity = object()
        GAME_FEEL.trigger_hit_stop(dummy_entity, duration_ms=50.0, shake_px=4.0, direction=1.0)
        self.assertTrue(GAME_FEEL.is_in_hit_stop(dummy_entity))

        # Check vibration offset
        GAME_FEEL.update(0.01)
        sx, sy = GAME_FEEL.get_entity_shake_offset(dummy_entity)
        self.assertNotEqual(sx, 0.0)
        self.assertEqual(sy, 0.0)

        # Let hit-stop expire
        GAME_FEEL.update(0.06)
        self.assertFalse(GAME_FEEL.is_in_hit_stop(dummy_entity))

    def test_dust_pooling(self):
        for p in GAME_FEEL.dust_pool:
            p.active = False
        initial_active = sum(1 for p in GAME_FEEL.dust_pool if p.active)
        GAME_FEEL.emit_dust(100, 200, dust_type="landing")
        active_after = sum(1 for p in GAME_FEEL.dust_pool if p.active)
        self.assertGreater(active_after, initial_active)

    def test_slash_arcs_and_transient_lights(self):
        GAME_FEEL.emit_slash_arc(150, 150, radius=28.0, color=(255, 230, 160))
        active_arcs = [a for a in GAME_FEEL.arc_pool if a.active]
        self.assertGreaterEqual(len(active_arcs), 1)

        lights = GAME_FEEL.get_active_point_lights()
        self.assertGreaterEqual(len(lights), 1)

    def test_foliage_wind_sway(self):
        sway1 = GAME_FEEL.get_foliage_wind_sway(0.0)
        sway2 = GAME_FEEL.get_foliage_wind_sway(0.5)
        self.assertIsInstance(sway1, float)
        self.assertNotEqual(sway1, sway2)


class TestDuelMode(unittest.TestCase):
    """Tests 1v1 Local Versus Mode scenes, cursors, HUD, and rounds."""

    def setUp(self):
        self.sm = SceneManager()

    def test_main_menu_has_duel_option(self):
        menu_scene = MainMenuScene(self.sm)
        option_titles = [opt.text for opt in menu_scene.menu.options]
        self.assertIn("MODO DE DUELO", option_titles)
        coop_idx = option_titles.index("MODO COOPERATIVO")
        duel_idx = option_titles.index("MODO DE DUELO")
        self.assertEqual(duel_idx, coop_idx + 1)

    def test_duel_character_select_scene(self):
        cs = DuelCharacterSelectScene(self.sm)
        self.assertEqual(len(ROSTER_GRID), 2)
        self.assertEqual(len(ROSTER_GRID[0]), 7)

        # Independent P1 cursor movement
        cs.handle_events([pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_d})])
        self.assertEqual(cs.p1_pos, [0, 1])

        # Independent P2 cursor movement
        cs.handle_events([pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_LEFT})])
        self.assertEqual(cs.p2_pos, [0, 5])

        # Confirm P1
        cs.handle_events([pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_j})])
        self.assertTrue(cs.p1_ready)

        # Confirm P2
        cs.handle_events([pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN})])
        self.assertTrue(cs.p2_ready)

    def test_duel_scene_combat_and_hud(self):
        duel = DuelScene(self.sm, p1_char="shaia", p2_char="lunaria", arena_id="terrae_1")
        self.assertEqual(duel.state, "INTRO")
        self.assertEqual(duel.round_number, 1)
        self.assertEqual(duel.p1_rounds_won, 0)
        self.assertEqual(duel.p2_rounds_won, 0)

        # Progress into FIGHT state
        duel.update(1.9)
        self.assertEqual(duel.state, "FIGHT")
        duel.update(0.1)
        self.assertLess(duel.round_time, 99.0)

        # Test Draw does not raise
        surf = pygame.Surface((640, 360))
        duel.draw(surf)

        # Simulate P2 defeat
        duel.player2.health = 0
        duel.update(0.1)
        self.assertEqual(duel.state, "ROUND_OVER")
        self.assertEqual(duel.p1_rounds_won, 1)

    def test_duel_health_multiplier_and_restricted_mana(self):
        """Verifies multiplied HP pool and restricted starting mana in Duel Mode."""
        duel = DuelScene(self.sm, p1_char="shaia", p2_char="lunaria", arena_id="terrae_1")
        # Base HP for Shaia is 100, Lunaria is 80. Multiplied 6x:
        self.assertGreaterEqual(duel.player1.max_health, 600)
        self.assertGreaterEqual(duel.player2.max_health, 480)
        self.assertEqual(duel.player1.health, duel.player1.max_health)

        # Mana should be restricted (capped at 80, starts at 20)
        self.assertLessEqual(duel.player1.max_mana, 80.0)
        self.assertEqual(duel.player1.mana, 20.0)
        self.assertLess(duel.player1.mana_regen, duel.player1.profile.mana_regen)

    def test_duel_parry_and_guard_break_mechanics(self):
        """Verifies Perfect Parry nullifies damage and staggers, and Guard Break stuns on stamina depletion."""
        duel = DuelScene(self.sm, p1_char="shaia", p2_char="lunaria", arena_id="terrae_1")
        duel.update(1.9) # Enter FIGHT state

        p1 = duel.player1
        p2 = duel.player2

        # 1. Test Perfect Parry: P2 blocks with active parry window
        p2.is_blocking = True
        p2.parry_window_timer = 0.20
        p2_hp_before = p2.health
        p1.pos.x = p2.pos.x - 20
        duel._resolve_strike(attacker=p1, defender=p2, attacker_idx=0, defender_idx=1)

        # P2 took 0 damage and gained parry score
        self.assertEqual(p2.health, p2_hp_before)
        self.assertGreater(duel.p2_score, 0)
        self.assertEqual(duel.p2_stats["parries"], 1)
        # Attacker P1 was staggered
        self.assertGreater(p1.hurt_timer, 0.0)

        # 2. Test Guard Break: P2 blocks with 0 stamina
        p2.is_blocking = True
        p2.parry_window_timer = 0.0
        p2.stamina = 0.0
        duel._resolve_strike(attacker=p1, defender=p2, attacker_idx=0, defender_idx=1)

        # P2 guard broken
        self.assertGreater(p2.guard_break_timer, 0.0)
        self.assertEqual(duel.p1_stats["guard_breaks"], 1)
        self.assertGreater(duel.p1_score, 0)

    def test_duel_dodge_evasion_mechanics(self):
        """Verifies Dash/Dodge invulnerability cleanly evades melee strikes."""
        duel = DuelScene(self.sm, p1_char="shaia", p2_char="lunaria", arena_id="terrae_1")
        duel.update(1.9) # Enter FIGHT state

        p1 = duel.player1
        p2 = duel.player2
        p2.is_dashing = True
        p2_hp_before = p2.health
        p1.pos.x = p2.pos.x - 20

        # P1 strikes while P2 is dodging
        duel._resolve_strike(attacker=p1, defender=p2, attacker_idx=0, defender_idx=1)

        # P2 takes 0 damage and earns perfect dodge score
        self.assertEqual(p2.health, p2_hp_before)
        self.assertGreater(duel.p2_score, 0)

    def test_duel_command_map_and_huds(self):
        """Verifies standard HUD integration and Command Map presence in DuelScene."""
        duel = DuelScene(self.sm, p1_char="shaia", p2_char="lunaria", arena_id="terrae_1")
        self.assertIsNotNone(duel.hud1)
        self.assertIsNotNone(duel.hud2)
        self.assertTrue(duel.show_command_map)

        # Toggle Command Map
        duel.handle_events([pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_TAB})])
        self.assertFalse(duel.show_command_map)
        duel.handle_events([pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_TAB})])
        self.assertTrue(duel.show_command_map)

        # Surface rendering does not crash
        surf = pygame.Surface((640, 360))
        duel.draw(surf)


if __name__ == "__main__":
    unittest.main()
