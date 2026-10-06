import unittest
import sys
import os
import pygame

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Headless mode for CI/tests
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((640, 360))

from scenes.magic_book_scene import MagicBookScene
from scenes.settings_menu import SettingsMenuScene
from scenes.story_select_scene import StorySelectScene, WORLDS_INFO
from scenes.tutorial_scene import TutorialScene
from scenes.boss_scene import BossScene
from engine.stage_manager import STAGE_CATALOG
from entities.boss import (
    SkeletonBoss,
    DemonSlimeBoss,
    SamuraiBoss,
    ImpalerBoss,
    MonsterCreatureBoss,
)


class TestBossesAndScenes(unittest.TestCase):
    def setUp(self):
        self.surface = pygame.Surface((640, 360))

    def test_magic_book_scene(self):
        """Test MagicBookScene initialization, update, and drawing."""
        scene = MagicBookScene(None)
        scene.update(0.016)
        scene.draw(self.surface)
        self.assertIsNotNone(scene.book_surf)
        self.assertEqual(len(scene.skills), 2)

    def test_settings_menu_scene(self):
        """Test SettingsMenuScene tabs and options."""
        scene = SettingsMenuScene(None, None)
        scene.update(0.016)
        scene.draw(self.surface)
        self.assertEqual(len(scene.TABS), 4)
        self.assertGreater(len(scene.options), 10)

    def test_story_select_scene(self):
        """Test StorySelectScene world cards and planet rendering."""
        scene = StorySelectScene(None)
        scene.update(0.016)
        scene.draw(self.surface)
        self.assertEqual(len(WORLDS_INFO), 4)

    def test_tutorial_scene(self):
        """Test TutorialScene initialization and draw."""
        scene = TutorialScene(None)
        scene.update(0.016)
        scene.draw(self.surface)
        self.assertEqual(scene.total_steps, 8)

    def test_all_five_bosses(self):
        """Test that each boss instantiates, updates, takes damage, and draws."""
        boss_map = {
            "skeleton_king": SkeletonBoss,
            "demon_slime": DemonSlimeBoss,
            "samurai": SamuraiBoss,
            "impaler": ImpalerBoss,
            "monster_creature": MonsterCreatureBoss,
        }
        for b_type, b_class in boss_map.items():
            scene = BossScene(None, boss_type=b_type)
            self.assertIsInstance(scene.boss, b_class)
            # Update several frames to ensure AI and animation cycles run
            for _ in range(10):
                scene.update(0.016)
            scene.draw(self.surface)
            # Test damage and hp property (2500 penetrates shield to reduce health)
            initial_hp = scene.boss.hp
            scene.boss.take_damage(2500)
            self.assertLess(scene.boss.hp, initial_hp)
            self.assertEqual(scene.boss.hp, scene.boss.health)
            self.assertEqual(scene.boss.max_hp, scene.boss.max_health)

    def test_stage_catalog_boss_routes(self):
        """Test that stages properly route to their boss types."""
        expected_bosses = {
            "terrae_3": "demon_slime",
            "sanguis_3": "impaler",
            "glacies_3": "monster_creature",
            "aetheria_3": "samurai",
        }
        for stage_id, expected_boss in expected_bosses.items():
            config = STAGE_CATALOG.get(stage_id)
            self.assertIsNotNone(config, f"Stage {stage_id} not found in catalog")
            self.assertEqual(config.boss_type, expected_boss)


if __name__ == "__main__":
    unittest.main()
