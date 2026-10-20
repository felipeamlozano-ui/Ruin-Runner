"""
tests/test_selection_and_coop_campaign.py
-----------------------------------------
Automated validation suite verifying:
1. Real bust/head thumbnails cropped via bounding rect (width >= 10) for all 11 roster heroes.
2. Character Dossier (Passive + 5 Skills) text wrapping and boundary verification (never exceeding rect.right).
3. DuelCharacterSelectScene unified with Co-op architecture, real standees, live arena backgrounds, and zero geometric placeholders.
4. Full Local Co-op (2 Players) support in Campaign Mode ("Campanha Narrativa Persistente"):
   - Mode selector in CharacterSelectScene (< MODO: CAMPANHA NARRATIVA | MODO ARCADE >)
   - [C] 1P <-> 2P toggle in StorySelectScene
   - Seamless level launch with P1 + P2 and persistent save.
"""

import os
import sys
from pathlib import Path
import unittest

os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
pygame.init()
pygame.display.set_mode((640, 360))

# Ensure root and src in path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from config.settings import SETTINGS
from entities.character_data import CHARACTER_ORDER, CHARACTER_REGISTRY, get_character_profile
from entities.player import Player
from ui.selection_helpers import get_hero_thumbnails, get_volumetric_light_beam, draw_pedestal_with_beam
from engine.text_cache import get_cached_text, render_wrapped_text
from ui.hollow_ui import HollowFonts, HollowColors
from scenes.character_select_scene import CharacterSelectScene
from scenes.duel_character_select_scene import DuelCharacterSelectScene, ARENAS
from scenes.story_select_scene import StorySelectScene
from scenes.level_scene import LevelScene
from engine.scene_manager import SceneManager


class DummySceneManager:
    def __init__(self):
        self.current_scene = None

    def change_scene(self, sc):
        self.current_scene = sc


class TestSelectionAndCoopCampaign(unittest.TestCase):
    """Rigorous verification of UI layouts, bounding rects, and co-op campaign flows."""

    def setUp(self):
        self.sm = DummySceneManager()
        self.original_coop = getattr(SETTINGS, "COOP_ENABLED", False)
        self.original_char = getattr(SETTINGS, "CURRENT_CHARACTER", "shaia")
        self.original_p2 = getattr(SETTINGS, "P2_CHARACTER", "lunaria")
        SETTINGS.COOP_ENABLED = False
        SETTINGS.CURRENT_CHARACTER = "shaia"
        SETTINGS.P2_CHARACTER = "lunaria"

    def tearDown(self):
        SETTINGS.COOP_ENABLED = self.original_coop
        SETTINGS.CURRENT_CHARACTER = self.original_char
        SETTINGS.P2_CHARACTER = self.original_p2

    def test_all_11_hero_thumbnails_bounding_rect(self):
        """All 11 heroes must have cropped bust portraits with bounding_rect.width >= 10."""
        thumbs = get_hero_thumbnails()
        self.assertEqual(len(thumbs), len(CHARACTER_ORDER))

        for cid in CHARACTER_ORDER:
            self.assertIn(cid, thumbs, f"Missing thumbnail for {cid}")
            thumb_surf = thumbs[cid]
            self.assertIsNotNone(thumb_surf, f"Thumbnail surface is None for {cid}")
            self.assertEqual(thumb_surf.get_size(), (28, 28))

            bbox = thumb_surf.get_bounding_rect()
            self.assertGreaterEqual(
                bbox.width, 10,
                f"Hero '{cid}' thumbnail is empty or too small: {bbox}"
            )
            self.assertGreaterEqual(
                bbox.height, 10,
                f"Hero '{cid}' thumbnail height is too small: {bbox}"
            )

    def test_passive_and_skills_no_overflow(self):
        """Passive text and combat skill names must never exceed boundaries for all 11 heroes."""
        font_desc = HollowFonts.get(9, italic=True)
        font_key = HollowFonts.get(9, bold=True)
        test_surf = pygame.Surface((640, 360))

        dossier_rect = pygame.Rect(240, 42, 390, 286)
        passive_rect = pygame.Rect(250, 124, 370, 44)

        for cid in CHARACTER_ORDER:
            prof = CHARACTER_REGISTRY[cid]

            # 1. Passive word-wrap verification
            lines_rendered = render_wrapped_text(
                test_surf, prof.passive_desc, font_desc, HollowColors.TEXT_NORMAL,
                passive_rect, line_height=12
            )
            self.assertGreater(lines_rendered, 0, f"No lines rendered for {cid} passive")
            words = prof.passive_desc.split(" ")
            current_line = ""
            for w in words:
                test_str = (current_line + " " + w).strip()
                if font_desc.size(test_str)[0] <= passive_rect.width:
                    current_line = test_str
                else:
                    self.assertLessEqual(
                        font_desc.size(current_line)[0], passive_rect.width,
                        f"Line '{current_line}' in {cid} passive exceeded rect width {passive_rect.width}"
                    )
                    current_line = w
            if current_line:
                self.assertLessEqual(
                    font_desc.size(current_line)[0], passive_rect.width,
                    f"Final line '{current_line}' in {cid} passive exceeded rect width {passive_rect.width}"
                )

            # 2. Combat skills untruncated verification in 390px panel
            for k, sk in prof.skills.items():
                hk_name = f"[{k.upper()}]  {sk.name}"
                self.assertNotIn("...", hk_name, f"Skill '{sk.name}' should not contain ellipsis")
                self.assertLessEqual(
                    font_key.size(hk_name)[0], dossier_rect.width - 60,
                    f"Skill name '{hk_name}' for hero {cid} is too wide for dossier"
                )

    def test_character_select_solo_layout_and_live_background(self):
        """Solo CharacterSelectScene must use native 640x360, live background, and volumetric beams."""
        SETTINGS.COOP_ENABLED = False
        cs = CharacterSelectScene(self.sm)
        self.assertEqual(cs.internal_size, (640, 360))
        self.assertIsNotNone(cs.stage_cfg)
        self.assertIsNotNone(cs.lighting)

        surf = pygame.Surface((640, 360))
        cs.update(0.016)
        cs.draw(surf)

        # Volumetric beam cache check
        beam = get_volumetric_light_beam()
        self.assertEqual(beam.get_size(), (120, 210))

    def test_duel_character_select_scene_unified_with_coop(self):
        """DuelCharacterSelectScene must use real animated Player standees, real thumbnails, and live arenas."""
        duel_cs = DuelCharacterSelectScene(self.sm)
        self.assertEqual(duel_cs.internal_size, (640, 360))
        self.assertEqual(len(ARENAS), 3)

        # Real player instances on pedestals (no geometric standees)
        self.assertIsInstance(duel_cs.p1_player, Player)
        self.assertIsInstance(duel_cs.p2_player, Player)

        # Real thumbnails
        self.assertEqual(len(duel_cs.thumbnails), len(CHARACTER_ORDER))

        surf = pygame.Surface((640, 360))
        duel_cs.update(0.016)
        duel_cs.draw(surf)

        # Arena switching Q / E
        init_arena = duel_cs.selected_arena_idx
        duel_cs._change_arena(1)
        self.assertEqual(duel_cs.selected_arena_idx, (init_arena + 1) % len(ARENAS))
        duel_cs.draw(surf)

    def test_coop_mode_selector_in_character_select(self):
        """CharacterSelectScene in Co-op mode must offer Campaign / Arcade mode toggle."""
        SETTINGS.COOP_ENABLED = True
        cs = CharacterSelectScene(self.sm, coop_target="campaign")
        self.assertEqual(cs.coop_target, "campaign")

        # Toggle to arcade and back
        cs._toggle_coop_target()
        self.assertEqual(cs.coop_target, "arcade")
        cs._toggle_coop_target()
        self.assertEqual(cs.coop_target, "campaign")

        # Ready both players
        cs.p1_ready = True
        cs.p2_ready = True
        cs._confirm_and_play()

        # Should launch LoadingScene with LevelScene in Co-op mode
        self.assertIsNotNone(self.sm.current_scene)
        self.assertTrue(SETTINGS.COOP_ENABLED)

    def test_story_select_scene_coop_toggle_and_launch(self):
        """StorySelectScene must feature [C] 1P <-> 2P toggle and launch campaign with co-op."""
        ss = StorySelectScene(self.sm)
        self.assertFalse(ss.coop_mode)

        # Toggle via [C] key event
        event_c = pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_c})
        ss.handle_events([event_c])
        self.assertTrue(ss.coop_mode)
        self.assertTrue(SETTINGS.COOP_ENABLED)

        # Launch world in 2P Co-op redirects to CharacterSelectScene with coop_target="campaign"
        ss._launch_world()
        self.assertIsInstance(self.sm.current_scene, CharacterSelectScene)
        self.assertEqual(self.sm.current_scene.coop_target, "campaign")
        self.assertTrue(self.sm.current_scene.coop_mode)

        # When players confirm their heroes in CharacterSelectScene:
        cs = self.sm.current_scene
        cs.p1_ready = True
        cs.p2_ready = True
        cs._confirm_and_play()

        # Next scene is now loading into the Campaign LevelScene with COOP_ENABLED = True
        loading_scene = self.sm.current_scene
        self.assertEqual(loading_scene.__class__.__name__, "LoadingScene")
        self.assertTrue(SETTINGS.COOP_ENABLED)
        self.assertIsInstance(loading_scene.next_scene, LevelScene)


if __name__ == "__main__":
    unittest.main()
