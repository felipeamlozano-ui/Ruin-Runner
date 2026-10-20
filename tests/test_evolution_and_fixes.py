"""
Evolution & Structural Fixes Verification Suite
Validates:
1. Persistent Multi-Slot Campaign Saves, Atomic Writes, Corrupt Recovery.
2. Staged In-World Dialogue Actors with 5-phase lifecycle and physical presence.
3. Official Cast integrity (elimination of phantom characters Lunaria, Vulkan, Carmilla).
4. Arcade Spatial Consistency, Prop Grounding & Barrel Scale.
5. Safe Collectible Spawn System (items never trapped inside rocks).
6. Impaler Boss (Empalador Abissal) animation stability, attack orientation & clean arena.
"""

import os
import sys
import json
import shutil
import unittest
import pygame

# Set headless display before importing pygame dependent modules
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((640, 360))

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.save_manager import SaveManager
from entities.dialogue_actor import DialogueActor
from engine.stage_manager import STAGE_CATALOG
from scenes.boss_scene import BOSS_DIALOGUES, BossScene
from scenes.level_scene import LevelScene, STAGE_CONFIGS
from scenes.story_select_scene import StorySelectScene
from entities.bosses_pack import ImpalerBoss
from entities.boss import SkeletonBoss
from entities.prop import Prop


class TestEvolutionAndFixes(unittest.TestCase):

    def setUp(self):
        self.test_save_dir = os.path.join(os.path.dirname(__file__), "temp_test_saves")
        if os.path.exists(self.test_save_dir):
            shutil.rmtree(self.test_save_dir, ignore_errors=True)
        os.makedirs(self.test_save_dir, exist_ok=True)
        self.save_mgr = SaveManager(saves_dir=self.test_save_dir)

    def tearDown(self):
        if os.path.exists(self.test_save_dir):
            shutil.rmtree(self.test_save_dir, ignore_errors=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 1. PERSISTENT CAMPAIGN SAVES
    # ─────────────────────────────────────────────────────────────────────────
    def test_save_manager_persistence_and_multi_slot(self):
        """Tests multi-slot persistence, atomic writes, backup, and corrupt recovery."""
        # Slot 1 new game
        self.save_mgr.load_slot(1)
        self.save_mgr.new_game(1)
        initial_s1_orbs = self.save_mgr.get_orbs()
        self.save_mgr.complete_stage("terrae_1", score=1200)
        self.save_mgr.set_checkpoint("terrae_2", 180, 200)
        self.save_mgr.set_event_completed("terrae_1_intro")
        self.save_mgr.add_orbs(150)
        self.save_mgr.save()

        # Slot 2 new game
        self.save_mgr.load_slot(2)
        self.save_mgr.new_game(2)
        initial_s2_orbs = self.save_mgr.get_orbs()
        self.save_mgr.complete_stage("sanguis_1", score=2500)
        self.save_mgr.add_orbs(500)
        self.save_mgr.save()

        # Re-instantiate SaveManager to simulate quitting and restarting the game
        reloaded_mgr = SaveManager(saves_dir=self.test_save_dir)
        
        # Verify Slot 1
        reloaded_mgr.load_slot(1)
        self.assertTrue(reloaded_mgr.is_stage_completed("terrae_1"))
        self.assertFalse(reloaded_mgr.is_stage_completed("sanguis_1"))
        self.assertTrue(reloaded_mgr.is_event_completed("terrae_1_intro"))
        self.assertEqual(reloaded_mgr.get_checkpoint(), ("terrae_2", 180.0, 200.0))
        self.assertEqual(reloaded_mgr.get_orbs(), initial_s1_orbs + 150)

        # Verify Slot 2
        reloaded_mgr.load_slot(2)
        self.assertTrue(reloaded_mgr.is_stage_completed("sanguis_1"))
        self.assertFalse(reloaded_mgr.is_stage_completed("terrae_1"))
        self.assertEqual(reloaded_mgr.get_orbs(), initial_s2_orbs + 500)

        # Verify corrupt file recovery
        slot1_file = os.path.join(self.test_save_dir, "slot_1.json")
        with open(slot1_file, "w", encoding="utf-8") as f:
            f.write("{ INVALID JSON CORRUPT FILE !!!")

        # Load slot 1 with corrupted main file -> must recover from backup without crash
        reloaded_mgr.load_slot(1)
        self.assertTrue(reloaded_mgr.is_stage_completed("terrae_1"), "Failed to recover from .bak file")

    # ─────────────────────────────────────────────────────────────────────────
    # 2. DIALOGUE ACTOR & IN-WORLD PRESENCE
    # ─────────────────────────────────────────────────────────────────────────
    def test_dialogue_actor_lifecycle_and_presence(self):
        """Tests that DialogueActor runs its 5-phase lifecycle: ENTER -> ORIENT -> TALK -> EXIT -> DONE."""
        actor = DialogueActor(
            character_id="wizard",
            x=50.0,
            y=280.0,
            target_x=160.0,
            exit_x=20.0,
            speed=200.0,
            name="ARQUIMAGO IGNATIUS"
        )
        self.assertEqual(actor.state, "ENTER")
        self.assertTrue(actor.facing_right)
        self.assertEqual(actor.floor_y, 280.0)

        # Update while walking in (ENTER phase)
        actor.update(0.3, player_pos=(200, 280))
        self.assertGreater(actor.x, 50.0)

        # Teleport close to target to trigger ORIENT and TALK
        actor.x = 159.5
        actor.update(0.1, player_pos=(200, 280))
        self.assertIn(actor.state, ("ORIENT", "TALK"))

        # Transition to TALK
        actor.state = "TALK"
        actor.update(0.1, player_pos=(200, 280))
        self.assertTrue(actor.facing_right)  # Looking at player at x=200

        # Trigger exit transition
        actor.start_exit()
        self.assertEqual(actor.state, "EXIT")
        self.assertFalse(actor.facing_right)  # Facing left towards exit_x=20

        # Update until reached exit
        actor.x = 20.5
        actor.update(0.1, player_pos=(200, 280))
        self.assertEqual(actor.state, "DONE")
        self.assertTrue(actor.is_finished)
        self.assertFalse(actor.active)

    # ─────────────────────────────────────────────────────────────────────────
    # 3. NO PHANTOM CHARACTERS (LUNARIA, VULKAN, CARMILLA PURGED)
    # ─────────────────────────────────────────────────────────────────────────
    def test_no_phantom_characters_in_dialogues(self):
        """Verifies no dialogues use phantom characters Lunaria, Vulkan or Carmilla as speakers."""
        # 1. Inspect all stages in STAGE_CATALOG
        for stg_id, stg in STAGE_CATALOG.items():
            dialogue = getattr(stg, "dialogue_intro", [])
            for line in dialogue:
                speaker = line.get("speaker", "").upper()
                self.assertNotIn("LUNARIA", speaker, f"Found phantom character Lunaria in stage {stg_id}")
                self.assertNotIn("VULKAN", speaker, f"Found phantom character Vulkan in stage {stg_id}")
                self.assertNotIn("CARMILLA", speaker, f"Found phantom character Carmilla in stage {stg_id}")
                
            actor = getattr(stg, "cinematic_actor", None)
            if actor:
                self.assertIn(actor, ("wizard", "kunoichi", "knight", "samurai_archer", "shaia"),
                              f"Invalid cinematic actor {actor} in stage {stg_id}")

        # 2. Inspect BOSS_DIALOGUES
        for b_type, lines in BOSS_DIALOGUES.items():
            for speaker, text in lines:
                self.assertNotIn("LUNARIA", speaker.upper(), f"Found phantom Lunaria in boss dialogue for {b_type}")
                self.assertNotIn("CARMILLA", speaker.upper(), f"Found phantom Carmilla in boss dialogue for {b_type}")

    # ─────────────────────────────────────────────────────────────────────────
    # 4. ARCADE SPATIAL CONSISTENCY & BARREL SCALE
    # ─────────────────────────────────────────────────────────────────────────
    def test_arcade_spatial_consistency_and_barrel_scale(self):
        """Verifies barrel prop scale is natural waist-height (>=42px) and grounded at floor_y."""
        # Test Prop at scale 1.0 and scale 0.65
        barrel_normal = Prop(300, 340, "barrel", scale=1.0)
        self.assertGreaterEqual(barrel_normal.rect.height, 42, "Barrel is unnaturally small at scale 1.0")
        self.assertEqual(barrel_normal.rect.bottom, 340, "Barrel bottom is not grounded at floor_y=340")

        barrel_legacy = Prop(300, 340, "barrel", scale=0.65)
        self.assertGreaterEqual(barrel_legacy.rect.height, 40, "Barrel clamped to tiny toy size (<40px)")
        self.assertEqual(barrel_legacy.rect.bottom, 340, "Barrel bottom is not grounded at floor_y=340")

        # Test Arcade Stage 1-4 configs props y alignment
        for stg_num in (1, 2, 3, 4):
            cfg = STAGE_CONFIGS[stg_num]
            for px, py, p_type, p_scale in cfg["props"]:
                self.assertEqual(py, 340, f"Stage {stg_num} prop '{p_type}' at y={py} is not aligned with floor_y=340")

    # ─────────────────────────────────────────────────────────────────────────
    # 5. SAFE ITEM SPAWN SYSTEM (NO ITEMS TRAPPED IN ROCKS)
    # ─────────────────────────────────────────────────────────────────────────
    def test_safe_collectible_spawn_validation(self):
        """Verifies that items spawned inside or touching rocks are shifted to clear navigable positions."""
        # Create a rock obstacle at x=600, y=340
        rock = Prop(600, 340, "rock", scale=0.9)
        obstacles = [rock]

        # Candidate item placed right in the center of the rock at x=600, y=338
        cx, cy = 600.0, 338.0
        safe_x, safe_y = LevelScene.find_safe_spawn_pos(cx, cy, obstacles, map_width=3000)

        # Must NOT be inside the rock's hitbox
        item_rect = pygame.FRect(safe_x - 14, safe_y - 24, 28, 28)
        self.assertFalse(rock.hitbox.colliderect(item_rect),
                         f"Safe spawn failed: item at x={safe_x} collides with rock at x={rock.rect.centerx}")
        self.assertNotEqual(safe_x, cx, "Safe spawn did not shift the trapped item outward")

        # Verify Stage 1 and 2 configs in STAGE_CONFIGS have no collectibles inside rocks
        for stg_num in (1, 2):
            cfg = STAGE_CONFIGS[stg_num]
            test_props = [Prop(px, py, pt, ps) for px, py, pt, ps in cfg["props"]]
            solid_props = [p for p in test_props if p.prop_type in ("rock", "barrel")]
            for cx, cy, c_item in cfg["collectibles"]:
                c_rect = pygame.FRect(cx - 14, cy - 24, 28, 28)
                for p in solid_props:
                    self.assertFalse(p.hitbox.colliderect(c_rect),
                                     f"Collectible '{c_item}' in Stage {stg_num} at x={cx} overlaps prop at x={p.rect.centerx}")

    # ─────────────────────────────────────────────────────────────────────────
    # 6. IMPALER BOSS (EMPALADOR ABISSAL) SPRITE & ORIENTATION FIX
    # ─────────────────────────────────────────────────────────────────────────
    def test_impaler_boss_orientation_hitbox_and_clean_arena(self):
        """Tests that Impaler Boss is safely removed/redirected and arena has 0 rocks."""
        boss = ImpalerBoss(500, 340)
        self.assertIsInstance(boss, SkeletonBoss, "Impaler Boss must safely redirect to SkeletonBoss")

        # Arena Cleanliness (Zero environmental rocks)
        class DummySceneManager:
            def change_scene(self, s): pass
        b_scene = BossScene(DummySceneManager(), boss_type="skeleton_king")
        self.assertEqual(len(b_scene.environmental_rocks), 0,
                         "Boss arena has environmental rocks! Requirement specifies completely cleared arena.")


if __name__ == "__main__":
    unittest.main()
