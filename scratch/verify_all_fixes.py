import sys
import os
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "src"))
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
pygame.init()
pygame.font.init()
pygame.display.set_mode((640, 480))

from config.settings import SETTINGS
from engine.scene_manager import SceneManager
from scenes.boss_scene import BossScene, BOSS_DIALOGUES
from scenes.tutorial_scene import TutorialScene
from scenes.level_scene import LevelScene
from ui.dialogue_box import DialogueBox

os.makedirs("Testes/validation", exist_ok=True)

print("=" * 60)
print("RUIN RUNNER — FORENSIC VERIFICATION SUITE")
print("=" * 60)

# -----------------------------------------------------------------------------
# 1. BOSS SCENE & DEMON SLIME ARENA
# -----------------------------------------------------------------------------
print("\n[TEST 1] Verifying Demon Slime Boss Arena...")
sm = SceneManager()
boss_scene = BossScene(sm, boss_type="demon_slime")

# Advance dialogue to dismiss intro
boss_scene.dialogue_box.is_finished = True

# Verify central rocks removed
rock_xs = [r.x for r in boss_scene.environmental_rocks]
print(f"Environmental rock count: {len(boss_scene.environmental_rocks)}, X coords: {rock_xs}")
assert len(boss_scene.environmental_rocks) <= 2, "Too many rocks in arena!"
for rx in rock_xs:
    assert rx < 100 or rx > boss_scene.map_width - 100, f"Rock at x={rx} is in the central combat area!"

# Verify player can move past previous 615 barrier
boss_scene.player.rect.x = 800
boss_scene.player.pos.x = 800.0
boss_scene.update(0.016)
print(f"Player x after update at x=800: {boss_scene.player.rect.x}")
assert boss_scene.player.rect.x >= 790, "Player was blocked by old 615 barrier!"

# Render arena and save screenshot
test_surf = pygame.Surface((640, 480))
boss_scene.draw(test_surf)
pygame.image.save(test_surf, "Testes/validation/1_demon_slime_arena.png")
print("Saved Testes/validation/1_demon_slime_arena.png")

# -----------------------------------------------------------------------------
# 2. TUTORIAL SCENE PROJECTILE LIFECYCLE
# -----------------------------------------------------------------------------
print("\n[TEST 2] Verifying Tutorial Fireball Lifecycle...")
tut_scene = TutorialScene(sm, character="shaia")
tut_scene.step = 4

# Simulate pressing [K] to cast fireball
dummy_hp_before = tut_scene.dummy.hp
tut_scene.player.mana = 100.0
tut_scene.player.cast_skill()

# Verify fireball spawned into player or scene
tut_scene.update(0.016)
assert len(tut_scene.projectiles) > 0, "No projectile transferred to TutorialScene.projectiles!"
proj = tut_scene.projectiles[0]
print(f"Spawned projectile: {proj.projectile_type}, active={proj.active}, pos=({proj.rect.x}, {proj.rect.y})")

# Render frame with active fireball in flight
tut_surf = pygame.Surface((640, 360))
tut_scene.draw(tut_surf)
pygame.image.save(tut_surf, "Testes/validation/2_tutorial_fireball_flight.png")
print("Saved Testes/validation/2_tutorial_fireball_flight.png")

# Advance physics until projectile impacts dummy
impacted = False
for _ in range(60):
    tut_scene.update(0.016)
    if tut_scene.dummy.hp < dummy_hp_before:
        impacted = True
        break

print(f"Dummy took damage from projectile: {impacted} (HP before: {dummy_hp_before}, after: {tut_scene.dummy.hp})")
assert impacted, "Projectile did not hit/damage the dummy!"

# -----------------------------------------------------------------------------
# 3. STAGE 4-3 FLOOR PERSPECTIVE & GEOMETRY
# -----------------------------------------------------------------------------
print("\n[TEST 3] Verifying Stage 4-3 ('Altar da Névoa Dourada') Floor...")
lvl_scene = LevelScene(sm, stage="aetheria_3")
lvl_surf = pygame.Surface((512, 384))
lvl_scene.draw(lvl_surf)
pygame.image.save(lvl_surf, "Testes/validation/3_stage_4_3_floor_dialogue.png")

# Also save clean gameplay frame with dialogue dismissed
if lvl_scene.dialogue_box:
    lvl_scene.dialogue_box.is_finished = True
lvl_surf_clean = pygame.Surface((640, 360))
lvl_scene.draw(lvl_surf_clean)
pygame.image.save(lvl_surf_clean, "Testes/validation/3_stage_4_3_gameplay.png")
print("Saved Testes/validation/3_stage_4_3_gameplay.png")

# -----------------------------------------------------------------------------
# 4. DIALOGUE BOX TEXT INTEGRITY
# -----------------------------------------------------------------------------
print("\n[TEST 4] Verifying Demon Slime Dialogue Text...")
db = DialogueBox(BOSS_DIALOGUES["demon_slime"])
demon_line = db.lines[0]["text"]
db.char_index = len(demon_line) # fully revealed

diag_surf = pygame.Surface((640, 480), pygame.SRCALPHA)
db.draw(diag_surf)
pygame.image.save(diag_surf, "Testes/validation/4_demon_slime_dialogue.png")
print("Saved Testes/validation/4_demon_slime_dialogue.png")

# Also test on native 512x384 buffer
diag_surf_512 = pygame.Surface((512, 384), pygame.SRCALPHA)
db.draw(diag_surf_512)
pygame.image.save(diag_surf_512, "Testes/validation/4_demon_slime_dialogue_512.png")
print("Saved Testes/validation/4_demon_slime_dialogue_512.png")

print("\n" + "=" * 60)
print("ALL FORENSIC VERIFICATIONS PASSED SUCCESSFULLY!")
print("=" * 60)
