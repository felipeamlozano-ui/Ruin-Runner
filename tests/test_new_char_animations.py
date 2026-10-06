"""Animation / interaction sanity tests for the 4 newest heroes."""
import os
import sys
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((640, 480))

from entities.player import Player  # noqa: E402

HEROES = ("knight", "wizard", "samurai_archer", "kunoichi")
REQUIRED = ("idle", "walk", "run", "attack", "cast_magic", "whirlwind", "guard",
            "jump", "fall", "landing", "dash", "dead", "hurt")


def _floor():
    return [pygame.FRect(0, 400, 2000, 60)]


def test_animation_sets():
    for hid in HEROES:
        p = Player(200, 300, character_id=hid)
        for name in REQUIRED:
            assert p.anim_manager.has_animation(name), f"{hid}: missing '{name}'"
            assert p.anim_manager.animations[name].frames, f"{hid}: '{name}' has no frames"
        print(f"[OK] {hid}: animation set complete")


def test_body_anchor_inside_frame():
    for hid in HEROES:
        p = Player(200, 300, character_id=hid)
        w = p.anim_manager.get_current_frame().get_width()
        for state in ("idle", "walk", "run", "dash"):
            ax = p._anchor_x(state, w)
            assert 0 < ax < w, f"{hid}/{state}: anchor {ax} outside frame {w}"
        print(f"[OK] {hid}: body anchors valid")


def test_projectile_release_is_delayed():
    for hid in ("wizard", "samurai_archer"):
        p = Player(200, 300, character_id=hid)
        tiles = _floor()
        for _ in range(30):
            p.update(1 / 60, tiles, [], None)
        p.mana = p.max_mana
        n0 = len(p.projectiles)
        p.attack_cooldown = 0.0
        # Emulate input-driven [J] through update(): spawn happens inside _handle_input
        p.is_attacking = True
        p.projectiles.append(object())  # simulate a spawn this frame
        p._defer_new_projectiles(n0)
        assert len(p.projectiles) == n0, f"{hid}: projectile not deferred"
        for _ in range(30):
            p.update(1 / 60, tiles, [], None)
        assert len(p.projectiles) == n0 + 1, f"{hid}: projectile never released"
        print(f"[OK] {hid}: projectile release synced to animation")


def test_random_simulation():
    rng = random.Random(7)
    for hid in HEROES:
        p = Player(200, 300, character_id=hid)
        tiles = _floor()
        for i in range(600):
            p.mana = p.max_mana
            p.stamina = p.max_stamina
            action = rng.random()
            if action < 0.05:
                p.attack()
            elif action < 0.08:
                p.cast_skill()
            elif action < 0.10:
                p.take_damage(1)
            elif action < 0.12:
                p.dash()
            p.update(1 / 60, tiles, [], None)
            img = p.anim_manager.get_current_frame()
            assert img.get_width() > 0
            p.projectiles.clear()
        assert not p.is_dead or p.health <= 0
        print(f"[OK] {hid}: 600-frame random simulation")


if __name__ == "__main__":
    test_animation_sets()
    test_body_anchor_inside_frame()
    test_projectile_release_is_delayed()
    test_random_simulation()
    print("ALL NEW HERO ANIMATION TESTS PASSED")
