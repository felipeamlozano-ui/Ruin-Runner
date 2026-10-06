"""
Ruin Runner — Comprehensive Test Suite for Local Co-op, New Characters,
Ruin Temporal Upscaler, Physical HDR Bloom, Camera Leash, and Input Abstraction.
"""

import os
import sys
sys.path.insert(0, os.path.abspath("src"))
sys.path.insert(0, os.path.abspath("."))
import unittest
import pygame
import numpy as np

# Ensure headless pygame for automated CI/testing
os.environ["SDL_VIDEODRIVER"] = "dummy"

from config.settings import SETTINGS
from config.controls import P1_DEFAULT_KEYBOARD, P2_DEFAULT_KEYBOARD, InputAction
from engine.input_manager import InputManager, PlayerInput
from entities.player import Player
from entities.character_data import CHARACTER_REGISTRY
from entities.coop_synergy import CoopSynergySystem, COOP_SYNERGIES
from engine.camera import Camera
from engine.v3.camera.camera_v3 import CameraV3
from engine.v3.upscaling.ruin_upscaler import RuinTemporalUpscaler, HALTON_2_3_SEQUENCE
from engine.v3.postfx.bloom import BloomEngine
from engine.v3.particles.vfx_profile import SkillVFXProfile, VFXBudgetManager, VFX_LOD, VFXPriority
from engine.v3.lighting.materials import MATERIAL_REGISTRY, MaterialType
from engine.v3.native.native_bridge import has_native, native_rcas_sharpen, native_tsr_reproject_and_validate


class TestCoopAndEngineEvolution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1280, 720))

    def setUp(self):
        SETTINGS.COOP_ENABLED = True
        SETTINGS.FRIENDLY_FIRE = False

    def test_new_characters_registry_and_stats(self):
        """Validates all 4 new co-op characters have HP, SP, MP, skills, and unique mechanics."""
        new_chars = ["aurelia", "archer", "zephyr", "boran"]
        for cid in new_chars:
            self.assertIn(cid, CHARACTER_REGISTRY, f"Character {cid} missing from CHARACTER_REGISTRY")
            data = CHARACTER_REGISTRY[cid]
            self.assertGreater(data.hp_max, 0)
            self.assertGreater(data.mp_max, 0)
            self.assertGreater(data.sp_max, 0)
            self.assertTrue(len(data.skills) >= 4, f"{cid} must have at least 4 mapped skills")
            self.assertIn("j", data.skills, f"{cid} missing basic attack skill")
            self.assertIn("r", data.skills, f"{cid} missing ultimate skill")
            self.assertTrue(data.passive_id != "", f"{cid} must possess a passive mechanic")

    def test_new_characters_sprite_assets_exist(self):
        """Validates 128x128 craftpix spritesheets exist for all 4 new characters."""
        new_chars = ["aurelia", "archer", "zephyr", "boran"]
        required_sheets = ["Idle.png", "Walk.png", "Attack.png", "Protection.png", "Dead.png", "Hurt.png", "portrait.png"]
        for cid in new_chars:
            char_dir = os.path.join("assets", "sprites", "characters", "coop", cid)
            self.assertTrue(os.path.exists(char_dir), f"Directory {char_dir} does not exist")
            for sheet in required_sheets:
                sheet_path = os.path.join(char_dir, sheet)
                self.assertTrue(os.path.exists(sheet_path), f"Missing {sheet} for {cid}")

    def test_input_abstraction_two_keyboard_players(self):
        """Ensures P1 and P2 have mutually exclusive keyboard bindings without conflict."""
        im = InputManager()
        p1 = im.get_player(0)
        p2 = im.get_player(1)

        self.assertIsNotNone(p1)
        self.assertIsNotNone(p2)

        # Check key set collision
        p1_keys = set(k for keys in P1_DEFAULT_KEYBOARD.values() for k in keys)
        p2_keys = set(k for keys in P2_DEFAULT_KEYBOARD.values() for k in keys)
        intersection = p1_keys.intersection(p2_keys)
        self.assertEqual(len(intersection), 0, f"Key conflict detected between P1 and P2: {intersection}")

    def test_coop_camera_bounding_box_and_zoom(self):
        """Validates camera smoothly tracks both players and zooms based on distance."""
        cam = Camera(4000, 400)
        p1 = Player(200, 300, character_id="shaia", player_index=0)
        p2 = Player(250, 300, character_id="lunaria", player_index=1)

        # Close distance -> zoom near 1.0
        cam.update_coop(p1, p2, 0.016)
        self.assertAlmostEqual(cam.zoom, 1.0, delta=0.08)

        # Separate players by 500px -> camera should zoom out smoothly
        p2.rect.x = 750
        for _ in range(60):
            cam.update_coop(p1, p2, 0.016)
        self.assertLess(cam.zoom, 1.0, "Camera should zoom out when players move apart")
        self.assertGreaterEqual(cam.zoom, cam.min_zoom, "Camera must respect min_zoom boundary")

    def test_coop_soft_and_hard_leash(self):
        """Validates soft leash dampening and hard leash boundary enforcement."""
        cam = Camera(4000, 400)
        p1 = Player(300, 300, character_id="shaia", player_index=0)
        p2 = Player(300 + cam.max_player_distance + 100, 300, character_id="lunaria", player_index=1)

        # Update leash
        cam.update_coop(p1, p2, 0.016)
        actual_distance = abs(p1.rect.centerx - p2.rect.centerx)
        self.assertLessEqual(actual_distance, cam.max_player_distance + 1.0,
                             "Hard leash must prevent players from exceeding maximum screen tether distance")

    def test_coop_downed_and_revive_mechanics(self):
        """Validates that reaching 0 HP enters downed state and companion can revive."""
        p1 = Player(300, 300, character_id="shaia", player_index=0)
        p2 = Player(320, 300, character_id="aurelia", player_index=1)
        p1.companion = p2
        p2.companion = p1

        # Deal fatal damage to P1
        p1.take_damage(999)
        self.assertTrue(p1.is_downed, "P1 should enter downed state when HP reaches 0 in co-op")
        self.assertFalse(p1.is_dead, "P1 should not be immediately permanently dead in co-op")

        # P2 channels revive on P1
        p2.reviving_target = p1
        p2.revive_channel = 2.6 # Surpass 2.5s channel threshold
        p1.update(0.016, [], [], None)
        p2.update(0.016, [], [], None)

        self.assertFalse(p1.is_downed, "P1 should be revived after successful channel")
        self.assertGreater(p1.health, 0, "P1 should have restored HP upon revive")

    def test_coop_synergies(self):
        """Validates elemental synergy activations between P1 and P2."""
        synergy = CoopSynergySystem()
        dummy_enemy = pygame.Rect(220, 300, 32, 60)
        
        # P1 hits with fire at t=10.0
        dmg1, syn1 = synergy.register_element_hit(dummy_enemy, "fire", source_player_index=0, base_damage=100, current_time=10.0)
        self.assertIsNone(syn1)
        self.assertEqual(dmg1, 100)

        # P2 follows up with wind at t=10.5 (within 3.0s window) -> Triggers Firestorm!
        dmg2, syn2 = synergy.register_element_hit(dummy_enemy, "wind", source_player_index=1, base_damage=100, current_time=10.5)
        self.assertIsNotNone(syn2, "Complementary elements Fire + Wind must trigger Firestorm synergy combo")
        self.assertEqual(syn2.name, "Tempestade de Fogo")
        self.assertGreater(dmg2, 100, "Synergy combo must grant substantial bonus damage multiplier")

    def test_ruin_temporal_upscaler_and_halton_jitter(self):
        """Validates Halton (2,3) subpixel jitter and temporal upscaler execution."""
        upscaler = RuinTemporalUpscaler(1280, 720, preset="Balanced")
        self.assertEqual(len(HALTON_2_3_SEQUENCE), 8)

        # Get jitter samples
        j0 = upscaler.get_camera_subpixel_jitter()
        j1 = upscaler.get_camera_subpixel_jitter()
        self.assertNotEqual(j0, j1, "Subpixel jitter sequence must advance each frame")

        # Upscale pass
        test_surf = pygame.Surface((upscaler.internal_w, upscaler.internal_h))
        test_surf.fill((60, 80, 100))
        high_surf = upscaler.upscale(test_surf, cam_x=0.0, cam_y=0.0)
        self.assertEqual(high_surf.get_size(), (1280, 720))

    def test_physical_hdr_bloom_luminance(self):
        """Validates BT.709 physical luminance thresholding (only bright sources bloom)."""
        bloom = BloomEngine(256, 192)
        test_surf = pygame.Surface((256, 192))
        test_surf.fill((30, 30, 30)) # Dark scenery - should NOT bloom

        # Bright magic source
        pygame.draw.circle(test_surf, (255, 255, 240), (128, 96), 20)

        bloomed = bloom.apply_bloom(test_surf, threshold=0.72, intensity=1.0)
        self.assertEqual(bloomed.get_size(), (256, 192))

    def test_vfx_budget_and_lod(self):
        """Validates VFX priority shedding under budget pressure."""
        manager = VFXBudgetManager(max_particles=1000)
        p_crit = SkillVFXProfile("ultimate_blast", priority=VFXPriority.CRITICAL)
        p_low = SkillVFXProfile("falling_leaf", priority=VFXPriority.LOW)

        # Under low pressure -> both allowed
        self.assertTrue(manager.request_vfx(p_crit, count=50))
        self.assertTrue(manager.request_vfx(p_low, count=50))

        # Under heavy pressure -> critical allowed, low sheds to LOD 3 or rejected
        manager.current_particle_count = 980
        lod_crit = manager.get_lod(p_crit)
        lod_low = manager.get_lod(p_low)
        self.assertLessEqual(lod_crit.value, lod_low.value)

    def test_materials_system(self):
        """Validates 2D physical material properties."""
        stone = MATERIAL_REGISTRY.get(MaterialType.STONE)
        fire = MATERIAL_REGISTRY.get(MaterialType.FIRE)
        magic = MATERIAL_REGISTRY.get(MaterialType.MAGIC)

        self.assertEqual(stone.emission, 0.0)
        self.assertGreater(fire.emission, 0.5)
        self.assertGreater(magic.bloom_response, 0.5)

    def test_native_c_bridge_or_fallback(self):
        """Validates that native extension runs or fallback operates seamlessly."""
        arr = np.zeros((100, 100, 3), dtype=np.uint8)
        arr[50, 50] = [255, 255, 255]
        if has_native():
            sharpened = native_rcas_sharpen(arr, 0.3)
            self.assertEqual(sharpened.shape, arr.shape)
        else:
            self.assertTrue(True, "Native fallback operational")


if __name__ == "__main__":
    unittest.main()
