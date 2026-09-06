import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.abspath("src"))
sys.path.insert(0, os.path.abspath("."))

import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from config.settings import SETTINGS
from engine.scene_manager import SceneManager
from engine.game import Game
from scenes.main_menu import MainMenuScene
from scenes.settings_menu import SettingsMenuScene
from scenes.character_select_scene import CharacterSelectScene
from scenes.boss_scene import BossScene
from scenes.level_scene import LevelScene
from scenes.loading_scene import LoadingScene

def test_dev_mode_workflow():
    print("\n=== Test 1: Game Always Starts in MainMenuScene ===")
    SETTINGS.DEV_MODE = True
    SETTINGS.DEV_START_BOSS = True
    game = Game()
    assert isinstance(game.scene_manager.current_scene, MainMenuScene), \
        f"Game should always start in MainMenuScene, got {type(game.scene_manager.current_scene)}"
    print("Verified: Game starts in MainMenuScene even with DEV_MODE=True!")

    print("\n=== Test 2: SettingsMenuScene Toggles DEV_MODE ===")
    sm = SceneManager()
    menu = MainMenuScene(sm)
    settings_scene = SettingsMenuScene(sm, menu)
    
    initial_mode = SETTINGS.DEV_MODE
    settings_scene.toggle_dev_mode()
    assert SETTINGS.DEV_MODE == (not initial_mode), "toggle_dev_mode should invert DEV_MODE"
    assert SETTINGS.DEV_START_BOSS == SETTINGS.DEV_MODE, "DEV_START_BOSS should sync with DEV_MODE"
    
    # Toggle back to False for next test
    SETTINGS.DEV_MODE = False
    SETTINGS.DEV_START_BOSS = False
    print("Verified: SettingsMenuScene toggles DEV_MODE and syncs DEV_START_BOSS!")

    print("\n=== Test 3: MainMenu Start Game with DEV_MODE ===")
    # 3a. With DEV_MODE = False -> LevelScene stage 1
    SETTINGS.DEV_MODE = False
    SETTINGS.DEV_START_BOSS = False
    menu_scene = MainMenuScene(sm)
    menu_scene.start_game()
    assert isinstance(sm.current_scene, LoadingScene), "Expected LoadingScene"
    assert isinstance(sm.current_scene.next_scene, LevelScene), "Expected LevelScene as next scene"
    assert sm.current_scene.next_scene.stage == 1, "Expected stage 1"
    print("Verified: MainMenu with DEV_MODE=False launches LevelScene Stage 1!")

    # 3b. With DEV_MODE = True -> BossScene
    SETTINGS.DEV_MODE = True
    SETTINGS.DEV_START_BOSS = True
    menu_scene2 = MainMenuScene(sm)
    menu_scene2.start_game()
    assert isinstance(sm.current_scene, LoadingScene), "Expected LoadingScene"
    assert isinstance(sm.current_scene.next_scene, BossScene), "Expected BossScene as next scene in DEV_MODE"
    print("Verified: MainMenu with DEV_MODE=True launches BossScene directly!")

    print("\n=== Test 4: CharacterSelect Play with DEV_MODE ===")
    # 4a. With DEV_MODE = False -> LevelScene
    SETTINGS.DEV_MODE = False
    SETTINGS.DEV_START_BOSS = False
    cs = CharacterSelectScene(sm, menu)
    cs._confirm_and_play()
    assert isinstance(sm.current_scene, LoadingScene), "Expected LoadingScene"
    assert isinstance(sm.current_scene.next_scene, LevelScene), "Expected LevelScene"
    print("Verified: CharacterSelect with DEV_MODE=False launches LevelScene!")

    # 4b. With DEV_MODE = True -> BossScene
    SETTINGS.DEV_MODE = True
    SETTINGS.DEV_START_BOSS = True
    cs2 = CharacterSelectScene(sm, menu)
    cs2._confirm_and_play()
    assert isinstance(sm.current_scene, LoadingScene), "Expected LoadingScene"
    assert isinstance(sm.current_scene.next_scene, BossScene), "Expected BossScene in DEV_MODE"
    print("Verified: CharacterSelect with DEV_MODE=True launches BossScene!")

    # Reset to default False
    SETTINGS.DEV_MODE = False
    SETTINGS.DEV_START_BOSS = False
    print("\n>>> ALL DEV MODE TESTS PASSED! <<<")

if __name__ == "__main__":
    test_dev_mode_workflow()
