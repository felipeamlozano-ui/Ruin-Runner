import os
import sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.abspath("src"))
sys.path.insert(0, os.path.abspath("."))

import pygame
pygame.init()

from engine.game import Game
from scenes.character_select_scene import CharacterSelectScene
from scenes.level_scene import LevelScene
from scenes.boss_scene import BossScene

def test_game_full_loop():
    print("Testing full Game runtime simulation (120 frames)...")
    game = Game()
    
    # 1. Start in MainMenu
    for _ in range(20):
        game._handle_events()
        game._update()
        game._draw()
        
    # 2. Switch to CharacterSelectScene
    cs_scene = CharacterSelectScene(game.scene_manager)
    game.scene_manager.change_scene(cs_scene)
    
    for i in range(7):
        cs_scene._select_character(i)
        for key in ["j", "k", "e", "shift", "q", "r"]:
            cs_scene._trigger_dojo_move(key)
            game._update()
            game._draw()
            
    # 3. Switch to LevelScene Stage 1
    lvl = LevelScene(stage=1, scene_manager=game.scene_manager)
    game.scene_manager.change_scene(lvl)
    for _ in range(40):
        game._update()
        game._draw()
        
    # 4. Switch to BossScene
    boss_sc = BossScene(scene_manager=game.scene_manager)
    game.scene_manager.change_scene(boss_sc)
    for _ in range(40):
        game._update()
        game._draw()
        
    print("Full game runtime simulation completed without errors!")

if __name__ == "__main__":
    test_game_full_loop()
