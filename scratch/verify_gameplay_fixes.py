import os
import sys
import math
import pygame

# Initialize headless pygame
os.environ["SDL_VIDEODRIVER"] = "dummy"
pygame.init()
pygame.display.set_mode((640, 360))

# Add project root and src to path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from entities.player import Player
from entities.enemy import SkeletonWarrior, SkeletonSpearman, SkeletonArcher, MageSkeleton
from entities.boss import SkeletonBoss
from entities.prop import Prop
from scenes.level_scene import LevelScene
from scenes.boss_scene import BossScene
from engine.v3.planets.planet_renderer import PixelPlanetRenderer
from engine.v3.weather.clouds import CloudsManager

def test_point_1_dynamic_shadow_and_ysort():
    print("Testing Point 1: Dynamic Shadow & Y-Sort on Obstacles...")
    p = Player(300, 200, character_id="shaia")
    ground_tile = pygame.FRect(0, 320, 1000, 50)
    barrel = pygame.FRect(280, 260, 40, 60) # barrel from y=260 to y=320
    
    # 1. Player standing on barrel
    p.rect.bottom = barrel.top
    p.pos.y = p.rect.y
    p.velocity.y = 0
    p.on_ground = True
    p._apply_physics(0.016, [ground_tile, barrel])
    
    assert p.on_ground, "Player should be grounded on barrel"
    assert p.shadow_surface_y == barrel.top, f"Shadow surface Y should be {barrel.top}, got {p.shadow_surface_y}"
    assert p.standing_on_obstacle_bottom == barrel.bottom, "Should detect standing on obstacle"
    assert p.y_sort_pivot == barrel.bottom + 0.1, f"y_sort_pivot should be {barrel.bottom + 0.1}, got {p.y_sort_pivot}"
    
    # 2. Player jumping in air above barrel
    p.rect.bottom = barrel.top - 30
    p.pos.y = p.rect.y
    p.velocity.y = -50
    p.on_ground = False
    p._apply_physics(0.016, [ground_tile, barrel])
    assert p.shadow_surface_y == barrel.top, f"Air shadow surface Y should be {barrel.top}, got {p.shadow_surface_y}"
    print("  -> Point 1 PASSED!")

def test_point_2_archer_scale_anchor_and_spawn():
    print("Testing Point 2: Archer Scale, Pivot & Spawn Point...")
    p = Player(200, 200, character_id="samurai_archer")
    # Anchor must be fixed 60.0 for all states
    for st in ["idle", "run", "attack", "jump", "dash"]:
        ax = p._anchor_x(st, 128)
        assert ax == 60.0, f"Archer anchor for {st} must be 60.0, got {ax}"
    
    # Unified spawn point
    sp_r = p.get_projectile_spawn_point()
    p.facing_right = False
    sp_l = p.get_projectile_spawn_point()
    assert sp_r[1] == sp_l[1] == p.rect.bottom - 46, "Spawn point Y must match bow height"
    assert sp_r[0] == p.rect.centerx + 34
    assert sp_l[0] == p.rect.centerx - 34
    
    # State reset cleans pending shots & flash
    p.magic_sigil_timer = 0.38
    p.is_attacking = True
    p.dash()
    assert p.magic_sigil_timer == 0.0, "Dash must clear magic sigil / bow flash timer"
    assert not p.is_attacking, "Dash must cancel attacking state"
    print("  -> Point 2 PASSED!")

def test_point_3_scenery_and_parallax():
    print("Testing Point 3: Catacombs & Bamboo Coast Parallax...")
    # Boss scene pillars and banners
    class DummyManager:
        pass
    boss_sc = BossScene(DummyManager(), boss_type="skeleton_king")
    for px in boss_sc.pillar_x_coords:
        # Archway spans in 512px dungeon center tile: x % 512 between 185 and 325
        local_x = px % 512
        assert not (185 <= local_x <= 325), f"Pillar at x={px} (local {local_x}) must not be inside archway span (185..325)"
    
    # Clouds upper sky bounds
    cm = CloudsManager(theme="gray", map_width=2000, cloud_count=10)
    for c in cm.clouds:
        if c.layer == "distant":
            assert 4 <= c.y <= 24, f"Distant cloud Y {c.y} outside upper sky band"
        elif c.layer == "mid":
            assert 12 <= c.y <= 36, f"Mid cloud Y {c.y} outside upper sky band"
    print("  -> Point 3 PASSED!")

def test_point_4_ui_hud_and_texts():
    print("Testing Point 4: UI, HUD & Text Synchronizations...")
    # Menu footer text
    with open("src/scenes/main_menu.py", "r", encoding="utf-8") as f:
        menu_code = f.read()
    assert "[W/S ou SETAS NAVEGAR]" in menu_code, "Menu navigation must use compatible ASCII glyphs"
    assert "↑" not in menu_code and "↓" not in menu_code, "Missing arrow glyphs must not exist in menu footer"
    
    # Boss name synchronization
    boss = SkeletonBoss(200, 200)
    assert boss.name == "O Rei Esqueleto", f"Boss name must be 'O Rei Esqueleto', got {boss.name}"
    
    # HUD posture bar separation
    with open("src/ui/hud.py", "r", encoding="utf-8") as f:
        hud_code = f.read()
    assert "POSTURA:" in hud_code
    assert "total_h = 52" in hud_code, "Boss HUD frame must be expanded to 52px"
    assert "get_bounding_rect" in hud_code, "Skill icons must crop transparent borders"
    
    # Planet renderer pole gap elimination
    renderer = PixelPlanetRenderer("terrae", 24, 48)
    assert len(renderer.frames) > 0
    assert renderer.frames[0].get_size() == (48, 48)
    print("  -> Point 4 PASSED!")

def test_point_5_enemy_collision_feedback_and_spawn():
    print("Testing Point 5: Enemy Collision Feedback & Safe Spawning...")
    # Safe spawn
    rock_prop = Prop(300, 280, "rock", 1.0)
    safe_x, safe_y = LevelScene.find_safe_spawn_pos(300, 280, [rock_prop], 3000)
    assert safe_x != 300, f"Safe spawn should move enemy outside rock, got {safe_x}"
    
    # Patrol collision reverses patrol_dir
    skel = SkeletonWarrior(200, 200)
    skel.state = "PATROL"
    skel.patrol_dir = 1
    skel.velocity.x = 40.0
    wall = pygame.FRect(210, 180, 50, 100)
    skel._apply_physics(0.016, [wall])
    assert skel.patrol_dir == -1, f"Patrol dir should reverse on obstacle collision, got {skel.patrol_dir}"
    
    # Death feedback: particles and fade
    skel.health = 10
    skel.take_damage(50)
    assert skel.is_dead, "Enemy should be dead"
    assert len(skel._bone_particles) > 0, "Enemy should scatter bone particles on death"
    assert not skel.is_death_complete, "Death should not complete instantly on frame 0"
    
    # Simulate death duration and animation progression
    skel._apply_physics(skel.death_duration + 0.1, [])
    skel.anim_manager.update(2.0)
    # Clear particles
    skel._bone_particles.clear()
    assert skel.is_death_complete, "Death should complete after timer, animation and particles end"
    print("  -> Point 5 PASSED!")

if __name__ == "__main__":
    test_point_1_dynamic_shadow_and_ysort()
    test_point_2_archer_scale_anchor_and_spawn()
    test_point_3_scenery_and_parallax()
    test_point_4_ui_hud_and_texts()
    test_point_5_enemy_collision_feedback_and_spawn()
    print("\nALL 5 POINTS VERIFIED SUCCESSFULLY!")
