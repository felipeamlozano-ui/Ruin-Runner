"""
Comprehensive Unit & Integration Tests for:
1. 5 Bosses refactoring (SkeletonBoss, DemonSlimeBoss, MonsterCreatureBoss, SamuraiBoss, ImpalerBoss)
2. Grimoire of Ascension UI (MagicBookScene) with animated opening, closing, page flips, and 9-slice buttons
3. Dynamic InputPromptIcon in HUD hotbar with tactile click feedback
4. Scenery texturing (rocks with base colliders and Y-sort) & multi-layered cloud parallax
"""

import sys
import os
import unittest
import pygame

# Set headless SDL dummy video driver for automated testing
os.environ["SDL_VIDEODRIVER"] = "dummy"

sys.path.insert(0, os.path.abspath("src"))
sys.path.insert(0, os.path.abspath("."))

from entities.player import Player
from entities.boss import SkeletonBoss, BossShockwave
from entities.bosses_pack import DemonSlimeBoss, MonsterCreatureBoss, SamuraiBoss, ImpalerBoss, FirePuddle, GroundSpike, HomingOrb
from scenes.magic_book_scene import MagicBookScene, SKILL_TREE_DATA
from ui.hud import HUD
from ui.input_prompt_icon import InputPromptIcon
from engine.v3.weather.clouds import CloudsManager, ParallaxBackground
from entities.prop import Prop
from engine.stage_manager import STAGE_CATALOG


class TestBossesRefactor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((640, 360))

    def test_boss1_skeleton_boss(self):
        boss = SkeletonBoss(200, 200)
        self.assertIn("ESPADACHIM", boss.name.upper())
        self.assertFalse(boss.is_dead)
        self.assertEqual(boss.scale, 1.20)
        self.assertTrue(boss.can_interrupt)
        
        # Test super armor during attack
        boss.state = "ATTACK_1"
        boss.can_interrupt = False
        boss.take_damage(20)
        self.assertNotEqual(boss.state, "HURT", "Super armor must prevent normal damage stagger during attack")

        # Test rotation deadzone
        boss.facing_right = True
        player = Player(210, 200) # Only 10px delta (< 38px deadzone)
        boss.update(0.016, [], player)
        self.assertTrue(boss.facing_right, "Boss must not flip instantly during small micro-steps")

        # Test Shockwave
        shock = BossShockwave(200, 280, moving_right=True)
        self.assertTrue(shock.active)
        shock.update(0.016)
        self.assertTrue(shock.active)

    def test_boss2_demon_slime_scale_and_moveset(self):
        boss = DemonSlimeBoss(300, 200)
        self.assertIn("DEMÔNIO", boss.name.upper())
        self.assertGreaterEqual(boss.scale, 1.60, "Demon Slime scale must be increased by at least 60%")
        self.assertGreaterEqual(boss.rect.width, 110)
        self.assertGreaterEqual(boss.rect.height, 150)
        
        # Test PointLight2D pulse
        player = Player(100, 200)
        boss.update(0.05, [], player)
        self.assertTrue(hasattr(boss, "fire_light"))
        self.assertGreater(boss.fire_light.radius, 100)

        # Test Fire Puddle hazard
        puddle = FirePuddle(250, 280, damage=15, duration=3.0)
        self.assertTrue(puddle.update(0.1, player))
        self.assertEqual(puddle.duration, 3.0)

    def test_boss3_monster_creature_levitation_and_orbs(self):
        boss = MonsterCreatureBoss(400, 200)
        self.assertIn("BEHOLDER", boss.name.upper())
        self.assertGreaterEqual(boss.scale, 1.80, "Monster Creature must be scaled up by at least 50%")
        
        # Test levitation oscillation
        player = Player(100, 200)
        boss.update(0.1, [], player)
        self.assertTrue(hasattr(boss, "float_offset_y"))

        # Test Homing Orb hazard
        orb = HomingOrb(300, 150, target=player)
        self.assertTrue(orb.update(0.016, player))

    def test_boss4_samurai_scale_and_moveset(self):
        boss = SamuraiBoss(350, 200)
        self.assertIn("SAMURAI", boss.name.upper())
        self.assertGreaterEqual(boss.scale, 2.0, "Samurai scale must be doubled")
        self.assertGreaterEqual(boss.rect.height, 120)

        # Test parry posture
        boss.state = "PARRY"
        boss.state_timer = 0.4
        player = Player(340, 200)
        p_hp_before = player.health
        boss.take_damage(25, attacker=player)
        self.assertLess(player.health, p_hp_before, "Attacking samurai during parry must inflict counter damage")
        self.assertEqual(player.state, "HURT", "Player must suffer stagger upon being parried")

    def test_boss5_impaler_moveset_and_enrage(self):
        boss = ImpalerBoss(500, 200)
        self.assertIn("RUÍNAS", boss.name.upper())
        self.assertTrue(hasattr(boss, "_ember_particles"))
        
        # Test Ground Spike hazard
        spike = GroundSpike(250, 280, damage=35)
        self.assertEqual(spike.state, "TELEGRAPH")
        spike.update(0.75)
        self.assertEqual(spike.state, "ERUPT")

        # Test Enrage trigger (<40% HP)
        player = Player(100, 200)
        boss.health = boss.max_health * 0.35
        boss.update(0.05, [], player)
        self.assertTrue(boss.enraged)


class TestGrimoireScene(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((640, 360))

    def test_grimoire_animations_and_assets(self):
        scene = MagicBookScene(None)
        self.assertEqual(scene.state, "OPENING")
        self.assertGreater(len(scene.open_frames), 0, "Open book frames must be loaded")
        self.assertGreater(len(scene.close_frames), 0, "Close book frames must be loaded")
        self.assertGreater(len(scene.turn_right_frames), 0, "Turn right frames must be loaded")
        self.assertGreater(len(scene.turn_left_frames), 0, "Turn left frames must be loaded")
        self.assertGreater(len(scene.icon_surfs), 0, "Dedicated spell icons must be loaded")

        # Advance opening animation to IDLE
        scene.update(scene.anim_duration + 0.05)
        self.assertEqual(scene.state, "IDLE")

        # Test page flip right transition
        scene._trigger_page_flip(1)
        self.assertEqual(scene.state, "FLIP_RIGHT")
        scene.update(scene.flip_duration + 0.05)
        self.assertEqual(scene.state, "IDLE")
        self.assertEqual(scene.page_index, 1)

        # Test textured button rendering
        surf = pygame.Surface((640, 360))
        scene.draw(surf)
        self.assertIsNotNone(scene.btn_upgrade_surf)


class TestInputPromptIconAndHUD(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((640, 360))

    def test_input_prompt_icon(self):
        icon = InputPromptIcon("ATTACK", player_index=0, size=16)
        self.assertEqual(icon.label, "J")
        self.assertEqual(icon.get_width(), 16)
        self.assertEqual(icon.get_height(), 16)
        self.assertFalse(icon.is_pressed())

        surf = pygame.Surface((100, 100))
        icon.draw(surf, 10, 10)

    def test_hud_hotbar_with_icons(self):
        player = Player(100, 200, character_id="shaia", player_index=0)
        hud = HUD(player, stage_title="TESTE DE HUD")
        self.assertIn("attack", hud.input_icons)
        self.assertIn("magic", hud.input_icons)
        self.assertIn("dash", hud.input_icons)
        self.assertIn("aoe", hud.input_icons)
        self.assertIn("shield", hud.input_icons)
        self.assertIn("ultimate", hud.input_icons)

        surf = pygame.Surface((640, 360))
        hud.draw(surf)


class TestSceneryAndCloudsParallax(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((640, 360))

    def test_rock_props_with_colliders_and_shadows(self):
        rock = Prop(300, 240, prop_type="rock", scale=1.0)
        self.assertIsNotNone(rock.image)
        self.assertTrue(hasattr(rock, "hitbox"))
        self.assertTrue(hasattr(rock, "y_sort_pivot"))
        self.assertAlmostEqual(rock.y_sort_pivot, rock.rect.bottom, delta=1.0)

        # Test stage catalog has rocks on wall bases and corners
        t1 = STAGE_CATALOG["terrae_1"]
        rock_props = [p for p in t1.props if p[2] == "rock"]
        self.assertGreaterEqual(len(rock_props), 4, "Stage must contain multiple rock props")

    def test_clouds_multi_layer_parallax(self):
        cm = CloudsManager(theme="white", map_width=3200, cloud_count=12)
        self.assertEqual(len(cm.clouds), 12)
        
        # Verify layers
        dist_layers = [c for c in cm.clouds if c.layer == "distant"]
        mid_layers = [c for c in cm.clouds if c.layer == "mid"]
        self.assertGreater(len(dist_layers), 0)
        self.assertGreater(len(mid_layers), 0)

        for c in dist_layers:
            self.assertGreaterEqual(c.motion_scale, 0.15)
            self.assertLessEqual(c.motion_scale, 0.25)
        for c in mid_layers:
            self.assertAlmostEqual(c.motion_scale, 0.40, delta=0.01)

        # Test continuous independent autoscroll
        x0 = cm.clouds[0].x
        cm.update(0.1)
        self.assertNotEqual(cm.clouds[0].x, x0, "Clouds must autoscroll independently")


if __name__ == "__main__":
    unittest.main()
