import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
from engine.game import Game
from config.settings import SETTINGS

def run_smoke_test(coop=False, char1="aurelia", char2="boran"):
    print(f"\n--- Smoke Test: Game Loop (Co-op={coop}, P1={char1}, P2={char2}) ---")
    SETTINGS.COOP_ENABLED = coop
    SETTINGS.CURRENT_CHARACTER = char1
    SETTINGS.P2_CHARACTER = char2
    SETTINGS.DEV_MODE = False
    
    game = Game()
    # Advance to LevelScene
    from scenes.level_scene import LevelScene
    lvl = LevelScene(stage=1, scene_manager=game.scene_manager)
    game.scene_manager.change_scene(lvl)
    
    # Run 60 frames
    for frame in range(60):
        game._handle_events()
        game._update()
        game._draw()
    print(f"  OK! Ran 60 frames successfully.")
    pygame.quit()

if __name__ == "__main__":
    run_smoke_test(coop=False, char1="archer")
    pygame.init()
    run_smoke_test(coop=True, char1="aurelia", char2="boran")
    print("\nSmoke tests completed successfully!")
