import os
import sys
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
import pygame

# Initialize pygame headless
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((512, 384))

from config.settings import SETTINGS
from entities.character_data import CHARACTER_ORDER, CHARACTER_REGISTRY, get_character_profile
from entities.player import Player
from scenes.character_select_scene import CharacterSelectScene
from scenes.settings_menu import SettingsMenuScene

class MockSceneManager:
    def __init__(self):
        self.current_scene = None
    def change_scene(self, scene):
        self.current_scene = scene

def test_character_animations():
    print("\n--- Testing All 11 Character Sprites & Animations ---")
    coop_chars = ["aurelia", "archer", "zephyr", "boran"]
    all_chars = CHARACTER_ORDER
    surface = pygame.Surface((512, 384))
    
    for cid in all_chars:
        p = Player(100, 100, character_id=cid)
        print(f"Testing character '{cid}':")
        anims = ["idle", "walk", "attack", "guard", "dead", "jump", "fall"]
        for anim in anims:
            if anim in p.anim_manager.animations:
                a_obj = p.anim_manager.animations[anim]
                num_frames = len(a_obj.frames)
                assert num_frames > 0, f"Character {cid} animation {anim} has 0 frames!"
                # Render one frame
                p.anim_manager.play(anim, force_reset=True)
                p.anim_manager.update(0.1)
                p.draw(surface, pygame.math.Vector2(0, 0))
        print(f"  OK! All core animations verified ({len(p.anim_manager.animations)} total anims).")

def test_solo_character_select():
    print("\n--- Testing Solo CharacterSelectScene ---")
    SETTINGS.COOP_ENABLED = False
    sm = MockSceneManager()
    scene = CharacterSelectScene(sm)
    surface = pygame.Surface((512, 384))
    
    # Test all 11 character selections
    for i in range(len(CHARACTER_ORDER)):
        scene._select_character(i)
        scene.update(0.016)
        scene.draw(surface)
        assert scene.selected_index == i
    print(f"  OK! Successfully cycled through all {len(CHARACTER_ORDER)} characters in Solo mode.")

def test_coop_character_select():
    print("\n--- Testing Co-op Split-Screen CharacterSelectScene ---")
    SETTINGS.COOP_ENABLED = True
    sm = MockSceneManager()
    scene = CharacterSelectScene(sm)
    surface = pygame.Surface((512, 384))
    
    # Test P1 and P2 selections
    for p1_i in [0, 4, 7, 8, 9, 10]:
        scene._select_p1_character(p1_i)
        for p2_i in [1, 5, 8, 9, 10]:
            scene._select_p2_character(p2_i)
            scene.update(0.016)
            scene.draw(surface)
            assert scene.p1_selected_index == p1_i
            assert scene.p2_selected_index == p2_i
            
    # Test Ready toggles
    scene.p1_ready = True
    scene.p2_ready = True
    scene.update(0.016)
    scene.draw(surface)
    assert scene.both_ready_timer > 0.0
    
    # Test confirm
    scene._confirm_and_play()
    assert sm.current_scene is not None
    print("  OK! Co-op split-screen dual selector and synchronized ready confirmed.")

def test_settings_menu_no_p2():
    print("\n--- Testing Settings Menu ---")
    sm = MockSceneManager()
    menu = SettingsMenuScene(sm, previous_scene=None)
    option_names = [opt[0] for opt in menu.options]
    assert "Personagem Jogador 2" not in option_names, "Personagem Jogador 2 still in settings menu!"
    assert "Modo Co-op Local" in option_names
    print("  OK! 'Personagem Jogador 2' successfully removed from Settings Menu.")

if __name__ == "__main__":
    test_character_animations()
    test_solo_character_select()
    test_coop_character_select()
    test_settings_menu_no_p2()
    print("\n==============================================")
    print("ALL TESTS PASSED WITH 100% SUCCESS!")
    print("==============================================")
