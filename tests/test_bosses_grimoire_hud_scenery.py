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
from engine.stage_manager import STAGE_CATALOG, STAGE_MGR


class TestBossesRefactor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((640, 360))

    def test_boss1_skeleton_boss(self):
        boss = SkeletonBoss(200, 200)
        self.assertTrue("REI ESQUELETO" in boss.name.upper() or "ESPADACHIM" in boss.name.upper())
        self.assertFalse(boss.is_dead)
        self.assertEqual(boss.scale, 1.0, "Skeleton Boss must use native 1:1 scale for crisp pixel art")
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
        self.assertEqual(boss.scale, 2.0, "Samurai scale must be crisp integer 2.0x")
        self.assertGreaterEqual(boss.rect.height, 65, "Samurai rect fitted to prevent midair floating")

        # Test parry posture
        boss.state = "PARRY"
        boss.state_timer = 0.4
        player = Player(340, 200)
        p_hp_before = player.health
        boss.take_damage(25, attacker=player)
        self.assertLess(player.health, p_hp_before, "Attacking samurai during parry must inflict counter damage")
        self.assertEqual(player.state, "HURT", "Player must suffer stagger upon being parried")

    def test_boss5_impaler_removed(self):
        boss = ImpalerBoss(500, 200)
        self.assertTrue(isinstance(boss, SkeletonBoss), "ImpalerBoss must redirect to SkeletonBoss")


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

    def test_terrae_1_and_3_scenery_and_clouds(self):
        """Verify fine-tuned cloud horizons, tinting, opacity, and parallax layers for Mundo 1-1 and 1-3."""
        # 1. Mundo 1-1 StageConfig verification
        t1 = STAGE_CATALOG["terrae_1"]
        self.assertEqual(t1.sky_horizon_y, 48)
        self.assertEqual(t1.cloud_count, 6)
        self.assertEqual(t1.cloud_tint, (255, 190, 140))
        self.assertEqual(t1.cloud_opacity_scale, 0.40)
        self.assertEqual(t1.layer_files, ["sea.png", "bamboo.png", "bridge.png"])
        self.assertEqual(t1.layer_initial_offsets, [0, 0, 0])

        # ParallaxRenderer with split layers and initial offsets
        STAGE_MGR.load_stage("terrae_1")
        p_rend = STAGE_MGR.parallax_renderer
        self.assertIsNotNone(p_rend)
        self.assertTrue(p_rend.has_split_layers)
        self.assertEqual(len(p_rend.layers), 3)
        for layer in p_rend.layers:
            self.assertEqual(layer[3], 0)

        # Drawing split layers & Silksong foreground silhouette
        test_surf = pygame.Surface((640, 360), pygame.SRCALPHA)
        p_rend.draw_sky_layer(test_surf, cam_x=0)
        p_rend.draw_midground_layer(test_surf, cam_x=0)
        p_rend.draw_foreground_layer(test_surf, cam_x=0)
        self.assertIsNotNone(p_rend.foreground_silhouette_surf)
        p_rend.draw_foreground_silhouette(test_surf, cam_x=0)
        p_rend.draw(test_surf, cam_x=100)

        # CloudsManager with low-horizon and sunset tinting
        cm1 = CloudsManager(
            theme=t1.cloud_theme,
            map_width=t1.map_width,
            cloud_count=t1.cloud_count,
            screen_w=640,
            sky_horizon_y=t1.sky_horizon_y,
            cloud_tint=t1.cloud_tint,
            cloud_opacity_scale=t1.cloud_opacity_scale
        )
        self.assertEqual(len(cm1.clouds), 6)
        for c in cm1.clouds:
            self.assertLessEqual(c.y + c.h, 48.0, f"Cloud base {c.y + c.h} exceeds horizon {48.0}")
            self.assertGreaterEqual(c.alpha, 40, f"Cloud alpha {c.alpha} below minimum 40")
            self.assertLessEqual(c.alpha, 85, f"Cloud alpha {c.alpha} above maximum 85")

        cm1.draw(test_surf, (0, 0), 640, 360)

        # 2. Mundo 1-3 StageConfig verification
        t3 = STAGE_CATALOG["terrae_3"]
        self.assertEqual(t3.sky_horizon_y, 75)
        self.assertEqual(t3.cloud_count, 14)
        self.assertEqual(t3.cloud_tint, (225, 235, 240))
        self.assertEqual(t3.cloud_opacity_scale, 1.0)

        cm3 = CloudsManager(
            theme=t3.cloud_theme,
            map_width=t3.map_width,
            cloud_count=t3.cloud_count,
            screen_w=640,
            sky_horizon_y=t3.sky_horizon_y,
            cloud_tint=t3.cloud_tint,
            cloud_opacity_scale=t3.cloud_opacity_scale
        )
        self.assertEqual(len(cm3.clouds), 14)
        cm3.draw(test_surf, (50, 0), 640, 360)


class TestSilksongLightingPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((640, 360))

    def test_silksong_lighting_features(self):
        from engine.lighting import LightingEngine, LightSource
        le = LightingEngine(theme="sunset", screen_w=640, screen_h=360, floor_y=280)

        # 1. Static AO Map & Anamorphic Vignette
        self.assertIsNotNone(le._static_ao_map)
        self.assertEqual(le._static_ao_map.get_size(), (640, 360))

        # 2. Hero Glow & Rim Light
        self.assertIsNotNone(le._hero_glow_surf)
        self.assertIsNotNone(le._hero_rim_surf)

        # 3. Dynamic Foot Contact AO Stamps
        self.assertIsNotNone(le._ao_stamp_small)
        self.assertIsNotNone(le._ao_stamp_med)
        self.assertIsNotNone(le._ao_stamp_large)

        # 4. Volumetric Diagonal God Rays
        self.assertEqual(len(le._god_ray_surfs), 3)

        # 5. Fixed Dust Motes Pool
        self.assertEqual(le.num_dust, 45)
        self.assertEqual(len(le.dust_halo_surfs), 3)
        self.assertEqual(len(le.dust_x), 45)
        self.assertEqual(len(le.dust_layer), 45)

        # 6. Render passes
        screen = pygame.Surface((640, 360))
        cam_offset = pygame.math.Vector2(100, 0)

        # Background dust batch
        le.draw_ambient_particles_background(screen, cam_offset)

        # Entity Contact AO
        from entities.prop import Prop
        dummy_prop = Prop(150, 270, "rock", 1.0)
        le.draw_entity_ao(screen, [dummy_prop], cam_offset)

        # Foreground dust batch
        le.draw_ambient_particles_foreground(screen, cam_offset)

        # God Rays
        le.draw_god_rays(screen, cam_offset)

        # Point lights + Hero Glow pass
        lights = [LightSource(200, 250, 48, (255, 180, 80), 0.85, flicker=True)]
        le.draw_point_lights(screen, lights, cam_offset, hero_pos=(160, 270))

        # Additive Bloom pass
        emissives = [(200, 250, 24, (255, 140, 50), 0.40)]
        le.draw_additive_glows(screen, emissives, cam_offset)

        # Update cycle (simulating 60 frames)
        for _ in range(60):
            le.update(1.0 / 60.0)


if __name__ == "__main__":
    unittest.main()
