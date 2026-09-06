import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.abspath("src"))
sys.path.insert(0, os.path.abspath("."))

import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from engine.scene_manager import SceneManager
from entities.projectile import Projectile
from entities.enemy import Skeleton
from scenes.boss_scene import BossScene
from scenes.level_scene import LevelScene

def test_projectile_single_hit_damage():
    print("\n=== Test 1: Projectile can_deal_damage & explode disarm ===")
    p = Projectile(100, 100, facing_right=True, is_enemy=False, projectile_type="fireball", damage=120)
    assert p.can_deal_damage() is True
    assert p.damage == 120
    
    p.explode()
    assert p.can_deal_damage() is False
    assert p.damage == 0
    assert p.has_hit is True
    assert p.state == "hit"
    print("Verified: Projectile immediately disarms damage and flags can_deal_damage=False on explode!")

    print("\n=== Test 2: Multi-Frame Boss Poise Shield Hit (No Multi-Hit Multiplication) ===")
    sm = SceneManager()
    boss_sc = BossScene(sm)
    boss = boss_sc.boss
    initial_shield = boss.shield
    assert initial_shield == 1000, f"Expected 1000 shield, got {initial_shield}"

    # Spawn projectile right on the edge of the Boss hitbox
    # Skill [K] deals 120 damage
    k_damage = 120
    proj = Projectile(
        boss.rect.centerx - 20,
        boss.rect.centery,
        facing_right=True,
        is_enemy=False,
        projectile_type="fireball",
        damage=k_damage
    )
    boss_sc.projectiles.append(proj)

    # Run 30 consecutive frames of updates (approx 0.5s at 60 FPS, covers full explosion animation)
    for frame in range(30):
        boss_sc.update(0.016)

    # Expected: Boss poise shield took exactly 120 damage once!
    expected_shield = initial_shield - k_damage
    assert boss.shield == expected_shield, \
        f"Boss shield should be {expected_shield} after single hit, but got {boss.shield} (multi-hit occurred!)"
    assert boss.health == boss.max_health, "Health should not be touched while shield was active"
    print(f"Verified: Boss shield took exactly {k_damage} damage over 30 frames (Remaining: {boss.shield}/1000)!")

    print("\n=== Test 3: Multi-Frame LevelScene Enemy Hit (No Multi-Hit Multiplication) ===")
    lvl = LevelScene(stage=1, scene_manager=sm)
    # Ground in LevelScene is at y=340. Skeleton height is 70, so y=270 sits on the floor.
    skel = Skeleton(lvl.player.rect.x + 200, 270)
    skel.health = 200
    lvl.enemies = [skel]

    test_damage = 45
    # Projectile at centery ~295, well above ground y=340
    lvl_proj = Projectile(
        skel.rect.centerx - 30,
        skel.rect.centery - 10,
        facing_right=True,
        is_enemy=False,
        projectile_type="arcane_sphere",
        damage=test_damage
    )
    lvl.projectiles.append(lvl_proj)

    for frame in range(30):
        lvl.update(0.016)

    expected_skel_hp = 200 - test_damage
    assert skel.health == expected_skel_hp, \
        f"Skeleton HP should be {expected_skel_hp} after single hit, but got {skel.health} (multi-hit occurred!)"
    print(f"Verified: Enemy took exactly {test_damage} damage over 30 frames (Remaining HP: {skel.health}/200)!")

    print("\n>>> ALL SKILL DAMAGE SINGLE-HIT TESTS PASSED! <<<")

if __name__ == "__main__":
    test_projectile_single_hit_damage()
