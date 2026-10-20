"""
Visual Validation & Screenshot Generator
Renders high-fidelity frames of:
1. StorySelectScene (Persistent campaign slots, world carousel, progress).
2. LevelScene (Staged in-world dialogue with DialogueActor present on floor).
3. Arcade Mode (Waist-high barrel scale, grounded props, safe item spawn outside rock).
4. ImpalerBoss Arena (Clean arena without rocks, correctly oriented boss).
Saves images to artifact directory and tests/output.
"""

import os
import sys
import pygame

os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((640, 480))

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.save_manager import SAVE
from engine.stage_manager import STAGE_MGR
from scenes.story_select_scene import StorySelectScene
from scenes.level_scene import LevelScene
from scenes.boss_scene import BossScene

ARTIFACT_DIR = r"C:\Users\Felipe\.gemini\antigravity-ide\brain\b98ddebb-0ce2-4b42-9ac4-5d0ad0e43b00"
OUTPUT_DIR = os.path.join(ROOT_DIR, "tests", "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
if os.path.exists(ARTIFACT_DIR):
    os.makedirs(os.path.join(ARTIFACT_DIR, "screenshots"), exist_ok=True)

class DummyManager:
    def change_scene(self, s): pass

def save_surface(surf, filename):
    local_path = os.path.join(OUTPUT_DIR, filename)
    pygame.image.save(surf, local_path)
    print(f"Saved local screenshot: {local_path}")
    if os.path.exists(ARTIFACT_DIR):
        artifact_path = os.path.join(ARTIFACT_DIR, "screenshots", filename)
        pygame.image.save(surf, artifact_path)
        print(f"Saved artifact screenshot: {artifact_path}")

def render_story_select():
    scene = StorySelectScene(DummyManager())
    # Advance animation a few steps
    for _ in range(15):
        scene.update(0.033)
    surf = pygame.Surface((640, 360))
    scene.draw(surf)
    save_surface(surf, "01_story_campaign_select_slots.png")

def render_staged_dialogue():
    SAVE.load_slot(1)
    stage_cfg = STAGE_MGR.load_stage("terrae_1")
    scene = LevelScene(DummyManager(), stage=stage_cfg)
    # Simulate actor entering and talking
    for _ in range(30):
        scene.update(0.033)
    surf = pygame.Surface((640, 360))
    scene.draw(surf)
    save_surface(surf, "02_staged_dialogue_actor_presence.png")

def render_arcade_spatial_consistency():
    scene = LevelScene(DummyManager(), stage=1)
    # Position camera near x=400 to view barrel, rock, and safe potion
    scene.camera.offset.x = 200.0
    for _ in range(10):
        scene.lighting.update(0.033)
    surf = pygame.Surface((640, 360))
    scene.draw(surf)
    save_surface(surf, "03_arcade_barrel_scale_and_safe_spawn.png")

def render_impaler_boss_arena():
    scene = BossScene(DummyManager(), boss_type="impaler")
    # Step boss update once
    scene.update(0.033)
    surf = pygame.Surface((640, 480))
    scene.draw(surf)
    save_surface(surf, "04_impaler_boss_arena_clean.png")

if __name__ == "__main__":
    print("Generating validation screenshots...")
    render_story_select()
    render_staged_dialogue()
    render_arcade_spatial_consistency()
    render_impaler_boss_arena()
    print("All validation screenshots generated successfully!")
