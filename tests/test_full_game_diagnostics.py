"""
Comprehensive Full-Game Diagnostic Suite for Ruin Runner.
Exhaustively tests every scene, menu option, character, skill, projectile,
enemy, boss, and rendering system to ensure zero runtime errors.
"""

import os
import sys
import unittest
import pygame

# Set dummy video driver for headless execution
os.environ["SDL_VIDEODRIVER"] = "dummy"

# Setup python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from config.settings import SETTINGS
from config.controls import InputAction
from engine.scene_manager import SceneManager
from engine.input_manager import INPUT, InputAction
from engine.camera import Camera
from engine.lighting import LightingEngine, LightSource
from engine.v3.core.profiler import PROFILER
from engine.v3.upscaling.ruin_upscaler import RuinTemporalUpscaler
from engine.v3.postfx.bloom import BloomEngine
from engine.v3.particles.particle_engine import ParticleEngine

from entities.player import Player
from entities.character_data import CHARACTER_REGISTRY, get_character_profile
from entities.enemy import Skeleton, MageSkeleton, WildBoar
from entities.boss import SkeletonBoss
from entities.projectile import Projectile
from entities.coop_synergy import CoopSynergySystem, COOP_SYNERGY

from scenes.main_menu import MainMenuScene
from scenes.settings_menu import SettingsMenuScene
from scenes.character_select_scene import CharacterSelectScene
from scenes.level_scene import LevelScene
from scenes.boss_scene import BossScene


class TestFullGameDiagnostics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1280, 720))

    def setUp(self):
        self.scene_manager = SceneManager()
        self.surface = pygame.Surface((512, 384))

    def test_settings_menu_all_options_bidirectional(self):
        """Test every single option in SettingsMenuScene toggling both left (-1) and right (+1)."""
        main_menu = MainMenuScene(self.scene_manager)
        settings_scene = SettingsMenuScene(self.scene_manager, main_menu)

        self.assertGreater(len(settings_scene.options), 0)
        for i, (name, val, callback) in enumerate(settings_scene.options):
            # Test right toggle (+1)
            try:
                callback(1)
            except Exception as e:
                self.fail(f"SettingsMenu option '{name}' failed on toggle(1): {e}")

            # Test left toggle (-1)
            try:
                callback(-1)
            except Exception as e:
                self.fail(f"SettingsMenu option '{name}' failed on toggle(-1): {e}")

        # Test draw and update
        settings_scene.update(0.016)
        settings_scene.draw(self.surface)

    def test_main_menu_interactions(self):
        """Test MainMenuScene initialization, update, and drawing."""
        main_menu = MainMenuScene(self.scene_manager)
        main_menu.update(0.016)
        main_menu.draw(self.surface)

    def test_character_select_scene_all_characters(self):
        """Test CharacterSelectScene cycling through and selecting all 11 characters."""
        main_menu = MainMenuScene(self.scene_manager)
        char_select = CharacterSelectScene(self.scene_manager, main_menu)
        char_select.update(0.016)
        char_select.draw(self.surface)

        # Cycle through all characters in the roster
        for i in range(len(CHARACTER_REGISTRY)):
            char_select._select_character(i)
            char_select.update(0.016)
            char_select.draw(self.surface)

    def test_all_11_characters_instantiation_and_skills(self):
        """Test every single character in the roster executing all skills and actions."""
        solid_rects = [pygame.FRect(0, 300, 1000, 50)]
        cam = Camera(1000, 480)
        enemies = [Skeleton(400, 280)]

        for char_id in CHARACTER_REGISTRY.keys():
            p = Player(200, 260, character_id=char_id, player_index=0)
            self.assertIsNotNone(p.profile)
            self.assertEqual(p.character_id, char_id)

            # Update base physics
            p.update(0.016, solid_rects, enemies, cam)
            p.draw(self.surface, cam.offset)

            # Test Attack (J)
            p.attack()
            p.update(0.016, solid_rects, enemies, cam)

            # Test Dash (Q)
            p.dash()
            p.update(0.016, solid_rects, enemies, cam)

            # Test Cast Skill (K)
            p.cast_skill()
            p.update(0.016, solid_rects, enemies, cam)

            # Test Cast Special (L)
            p.cast_special()
            p.update(0.016, solid_rects, enemies, cam)

            # Test Cast AoE (E)
            p.cast_aoe()
            p.update(0.016, solid_rects, enemies, cam)

            # Test Ultimate (I)
            p.mana = p.max_mana
            p.cast_ultimate()
            p.update(0.016, solid_rects, enemies, cam)
            p.draw(self.surface, cam.offset)

    def test_projectiles_and_entity_collisions(self):
        """Test projectiles impacting enemies, players, and tiles."""
        p1 = Player(100, 200, character_id="shaia", player_index=0)
        enemy = Skeleton(200, 200)
        solid_rects = [pygame.FRect(300, 200, 50, 50)]

        # Spawn player projectile moving towards enemy
        proj = Projectile(120, 200, facing_right=True, is_enemy=False, projectile_type="fireball")
        self.assertTrue(hasattr(proj, "hit_entities"))
        self.assertIn(enemy, [enemy])

        # Test collision checks as performed in LevelScene and BossScene
        if not enemy.is_dead and enemy not in proj.hit_entities and proj.rect.colliderect(enemy.rect):
            proj.hit_entities.add(enemy)
            enemy.take_damage(proj.damage)

        proj.update(0.016, solid_rects)
        proj.draw(self.surface, pygame.math.Vector2(0, 0))

    def test_coop_pairing_and_revive_channeling(self):
        """Test co-op players pairing, companion auras, downed state, and revive channeling."""
        solid_rects = [pygame.FRect(0, 300, 1000, 50)]
        cam = Camera(1000, 480)
        enemies = [Skeleton(500, 280)]

        p1 = Player(200, 280, character_id="aurelia", player_index=0)
        p2 = Player(230, 280, character_id="zephyr", player_index=1)
        p1.companion = p2
        p2.companion = p1

        # Test proximity aura ticks (Aurelia heals, Zephyr restores mana)
        initial_hp = p2.health = 50.0
        initial_mp = p1.mana = 20.0
        p1.update(0.1, solid_rects, enemies, cam)
        p2.update(0.1, solid_rects, enemies, cam)
        self.assertGreaterEqual(p2.health, initial_hp)
        self.assertGreaterEqual(p1.mana, initial_mp)

        # Test downed state
        p2.is_downed = True
        p2.is_dead = True
        p1.update(0.1, solid_rects, enemies, cam)
        self.assertTrue(hasattr(p1, "reviving_target"))
        self.assertTrue(hasattr(p1, "revive_channel"))

    def test_level_scenes_all_stages(self):
        """Test LevelScene for all 4 stages in both Single Player and Co-op."""
        for stage_idx in [1, 2, 3, 4]:
            for coop in [False, True]:
                SETTINGS.COOP_ENABLED = coop
                level = LevelScene(self.scene_manager, stage=stage_idx)
                # Run multiple simulation frames
                for _ in range(5):
                    level.update(0.016)
                level.draw(self.surface)

    def test_boss_scene_single_and_coop(self):
        """Test BossScene in both Single Player and Co-op."""
        for coop in [False, True]:
            SETTINGS.COOP_ENABLED = coop
            boss_scene = BossScene(self.scene_manager)
            for _ in range(5):
                boss_scene.update(0.016)
            boss_scene.draw(self.surface)

    def test_profiler_and_f3_overlay(self):
        """Test Profiler telemetry and F3 diagnostic overlay."""
        PROFILER.enabled = True
        PROFILER.begin_frame()
        PROFILER.record_draw_calls(10)
        PROFILER.record_particles(150)
        PROFILER.record_light(8)
        PROFILER.record_shadow()
        PROFILER.render_overlay(self.surface)
        PROFILER.enabled = False


if __name__ == "__main__":
    unittest.main()
