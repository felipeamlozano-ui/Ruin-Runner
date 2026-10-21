"""
Automated Capture for Catacombs Lighting & Shadow Audit
Generates:
1. catacombs_01_spawn_idle.png (Shaia idle at spawn in Catacombs)
2. catacombs_shaia_shooting_match.png (Shaia shooting/combat with lanterns, magic, shadows)
"""

import os
import sys
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((640, 360))

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config.settings import SETTINGS
SETTINGS.RUIN_ENGINE_V3 = True
SETTINGS.SHADOWS_2D = "Suaves"
SETTINGS.BLOOM_ENABLED = True

from scenes.level_scene import LevelScene
from entities.player import Player
from entities.projectile import Projectile

class DummySceneManager:
    def change_scene(self, s): pass

def generate_captures():
    sm = DummySceneManager()
    
    # 1. Catacombs Spawn Idle
    scene1 = LevelScene(sm, stage=1)
    scene1.player.rect.x = 120
    scene1.player.rect.bottom = scene1.floor_y
    scene1.camera.offset.x = 0
    scene1.camera.offset.y = 0
    # Step physics and lighting a few frames
    for _ in range(15):
        scene1.update(0.016)
    
    surf1 = pygame.Surface((640, 360))
    scene1.draw(surf1)
    out1_root = os.path.join(ROOT_DIR, "catacombs_01_spawn_idle.png")
    out1_test = os.path.join(ROOT_DIR, "tests", "output", "catacombs_01_spawn_idle.png")
    pygame.image.save(surf1, out1_root)
    pygame.image.save(surf1, out1_test)
    print(f"Generated {out1_root}")
    
    # 2. Catacombs Shaia Shooting Match
    scene2 = LevelScene(sm, stage=1)
    scene2.player.rect.x = 240
    scene2.player.rect.bottom = scene2.floor_y
    scene2.camera.offset.x = 80
    scene2.camera.offset.y = 0
    
    # Spawn a projectile in flight
    proj = Projectile(
        scene2.player.rect.centerx + 40,
        scene2.player.rect.centery - 10,
        facing_right=True,
        is_enemy=False,
        projectile_type="fireball",
        damage=45
    )
    scene2.projectiles.append(proj)
    
    # Add an enemy fireball for combat read
    enemy_proj = Projectile(
        scene2.player.rect.centerx + 220,
        scene2.player.rect.centery - 15,
        facing_right=False,
        is_enemy=True,
        projectile_type="mage_fireball",
        damage=25
    )
    scene2.projectiles.append(enemy_proj)
    
    # Step simulation 10 frames
    for _ in range(10):
        scene2.update(0.016)
    
    surf2 = pygame.Surface((640, 360))
    scene2.draw(surf2)
    out2_root = os.path.join(ROOT_DIR, "catacombs_shaia_shooting_match.png")
    out2_test = os.path.join(ROOT_DIR, "tests", "output", "catacombs_shaia_shooting_match.png")
    pygame.image.save(surf2, out2_root)
    pygame.image.save(surf2, out2_test)
    print(f"Generated {out2_root}")

if __name__ == "__main__":
    generate_captures()
