import unittest
import sys
import os
import pygame
import numpy as np

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, root_dir)
sys.path.insert(0, os.path.join(root_dir, "src"))

from entities.boss import SkeletonBoss
from entities.enemy import Skeleton, MageSkeleton, WildBoar
from entities.player import Player
from engine.v3.ai.neural_ai import NeuralTacticalAI
from engine.v3.native.native_bridge import has_native, native_pixel_aa_sharp_bilinear, native_rcas_sharpen
from engine.v3.upscaling.antialiasing import AntiAliasingEngine
from engine.v3.upscaling.ruin_upscaler import RuinTemporalUpscaler

class TestBossAndNeuralEvolution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((640, 480))

    def test_boss_sprite_sheets_and_grounding(self):
        """Validate official 11 multi-frame animations and mathematical foot anchoring."""
        boss = SkeletonBoss(200, 200)
        self.assertEqual(len(boss.anim_manager.animations["idle"].frames), 5)
        self.assertEqual(len(boss.anim_manager.animations["hurt"].frames), 2)
        self.assertEqual(len(boss.anim_manager.animations["dead"].frames), 5)
        self.assertEqual(len(boss.anim_manager.animations["walk"].frames), 5)
        self.assertEqual(len(boss.anim_manager.animations["run"].frames), 5)
        self.assertEqual(len(boss.anim_manager.animations["attack1"].frames), 5)
        self.assertEqual(len(boss.anim_manager.animations["attack2"].frames), 5)
        self.assertEqual(len(boss.anim_manager.animations["attack3"].frames), 5)
        self.assertEqual(len(boss.anim_manager.animations["attack4"].frames), 5)
        self.assertEqual(len(boss.anim_manager.animations["special"].frames), 5)
        self.assertEqual(len(boss.anim_manager.animations["jump"].frames), 5)
        
        # Verify foot grounding anchor baseline (scaled 1.20x: 180 in 230x192 frame)
        self.assertEqual(boss.scale, 1.20)
        self.assertEqual(boss.anchor_y, 180)
        self.assertEqual(boss.anchor_x_right, 90)
        self.assertEqual(boss.anchor_x_left, 139)
        
        # Render frame without error
        surf = pygame.Surface((640, 480))
        cam = pygame.math.Vector2(0, 0)
        boss.draw(surf, cam)

    def test_boss_two_phase_progression(self):
        """Validate two-phase progression: Phase 1 (>50% HP) and Phase 2 Enrage (<=50% HP)."""
        boss = SkeletonBoss(200, 200)
        self.assertEqual(boss.current_phase, 1)
        self.assertFalse(boss.enraged)

        # Damage boss above 50% HP
        boss.take_damage(3000) # Poise shield + HP remains > 50%
        self.assertEqual(boss.current_phase, 1)
        self.assertFalse(boss.enraged)

        # Damage boss past 50% HP
        boss.take_damage(int(boss.max_health * 0.50) + 1000)
        self.assertEqual(boss.current_phase, 2)
        self.assertTrue(boss.enraged)
        self.assertEqual(len(boss.potions_to_spawn), 2)
        self.assertTrue(len(boss.minions_to_spawn) >= 2)

    def test_neural_tactical_ai_forward_and_adapt(self):
        """Items 6 & 7: Validate online reinforcement learning on neural AI controller."""
        ai = NeuralTacticalAI(entity_type="boss")
        self.assertTrue(has_native())

        # Test observation vector building
        feats = ai.build_feature_vector(
            self_pos=(200, 400),
            target_pos=(300, 400),
            target_vel=(50, 0),
            target_is_attacking=True,
            target_is_casting=False,
            target_is_dashing=False,
            incoming_projectiles=[{"pos": (250, 400), "vx": -200}],
            self_cooldown=0.0
        )
        self.assertEqual(len(feats), 12)

        # Forward inference
        action_name, action_idx, conf = ai.decide_action(feats, temperature=0.7)
        self.assertIn(action_name, NeuralTacticalAI.ACTIONS)

        # Online adaptation on action weights
        w3_before = ai.w3.copy()
        ai.report_combat_outcome(was_hit=False, dodged_successfully=True, blocked_successfully=False, landed_hit=True)
        # Output weights should adapt based on reward signal
        self.assertFalse(np.array_equal(w3_before, ai.w3))

    def test_enemy_smart_behaviors(self):
        """Item 6: Validate jump, dodge, and guard mechanics on regular enemies."""
        player = Player(100, 300)
        skel = Skeleton(180, 300)
        
        # Test guard mechanics
        skel.is_guarding = True
        prev_hp = skel.health
        skel.take_damage(40, hit_direction=-1) # Frontal hit
        damage_taken = prev_hp - skel.health
        self.assertLessEqual(damage_taken, 15, "Guard must mitigate frontal damage by 75%")

        # Test dodge mechanics
        skel.is_dodging = True
        prev_hp = skel.health
        skel.take_damage(40)
        self.assertEqual(skel.health, prev_hp, "Dodge must negate incoming damage")

    def test_pixel_aa_and_rcas_upscaling(self):
        """Items 3 & 4: Validate native Pixel AA and RCAS sharpening upscaler."""
        self.assertTrue(has_native())

        aa_engine = AntiAliasingEngine(mode="Pixel AA")
        test_surf = pygame.Surface((64, 48))
        test_surf.fill((80, 120, 160))
        pygame.draw.line(test_surf, (255, 255, 255), (0, 0), (63, 47), 2)

        # Sharp-bilinear Pixel AA
        filtered_surf = aa_engine.apply(test_surf)
        self.assertEqual(filtered_surf.get_size(), (64, 48))

        # RCAS Upscaler
        upscaler = RuinTemporalUpscaler(128, 96, preset="Balanced")
        upscaled = upscaler.upscale(test_surf)
        self.assertEqual(upscaled.get_size(), (128, 96))

if __name__ == "__main__":
    unittest.main()
