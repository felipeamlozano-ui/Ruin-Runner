import os
import sys
import time

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
from scenes.level_scene import LevelScene

SETTINGS.COOP_ENABLED = True
SETTINGS.CURRENT_CHARACTER = "aurelia"
SETTINGS.P2_CHARACTER = "boran"

game = Game()
lvl = LevelScene(stage=1, scene_manager=game.scene_manager)
game.scene_manager.change_scene(lvl)

# Warmup 10 frames
for _ in range(10):
    game._handle_events()
    game._update()
    game._draw()

# Profile 60 frames breakdown
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

for _ in range(60):
    game._handle_events()
    game._update()
    game._draw()

profiler.disable()
stats = pstats.Stats(profiler).sort_stats("cumulative")
stats.print_stats(35)
