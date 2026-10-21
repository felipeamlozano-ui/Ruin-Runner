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

def capture_ultimate():
    screen = pygame.display.set_mode((640, 360))
    scene = LevelScene(stage=1)

    # Position player near the first skeleton minion (x=450)
    scene.player.pos.x = 340.0
    scene.player.rect.x = 340
    scene.player.pos.y = scene.floor_y - scene.player.rect.height
    scene.player.rect.bottom = scene.floor_y
    scene.camera.target = scene.player
    scene.camera.offset.x = 100.0

    # Warm up a few frames
    for _ in range(5):
        scene.update(0.016)

    # Trigger Ultimate [R]
    scene.player.cast_ultimate()

    # Step simulation to t = 0.35s (active Time-Stop, full Sakuga wind ribbons, volumetric rays, dimmed backdrop)
    for _ in range(22):
        scene.update(0.016)

    # Render frame
    render_surf = pygame.Surface((640, 360))
    scene.draw(render_surf)

    out_path = os.path.join(os.path.dirname(__file__), "..", "catacombs_ultimate_timestop.png")
    pygame.image.save(render_surf, out_path)
    print(f"Saved: {out_path} ({os.path.getsize(out_path)} bytes)")

if __name__ == "__main__":
    capture_ultimate()
