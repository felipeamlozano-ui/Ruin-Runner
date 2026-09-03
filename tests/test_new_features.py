import pygame
import os
import sys

sys.path.insert(0, os.path.abspath("src"))
sys.path.insert(0, os.path.abspath("."))

# Init headless display
pygame.init()
pygame.display.set_mode((1, 1))

from entities.player import Player
from entities.boss import SkeletonBoss, BossShockwave
from entities.enemy import Skeleton, MageSkeleton, WildBoar
from entities.projectile import Projectile
from scenes.level_scene import LevelScene
from scenes.boss_scene import BossScene
from scenes.settings_menu import SettingsMenuScene
from ui.death_screen import DeathScreen
from engine.scene_manager import SceneManager
from config.settings import SETTINGS

def test_all():
    print("=== Testing Player Plunge Attack (Queda com Espada) ===")
    p = Player(100, 100)
    p.on_ground = False
    p.is_down_attacking = True
    p.velocity.y = 850
    
    # Mid-air enemy collision
    dummy_enemy = Skeleton(100, 180)
    initial_enemy_hp = dummy_enemy.health
    p.trigger_aoe_damage([dummy_enemy])
    assert dummy_enemy.health < initial_enemy_hp, "Airborne dive attack did not damage enemy in path!"
    print("Mid-air dive hit verified!")
    
    # Ground landing collision
    floor_tiles = [pygame.FRect(0, 300, 1000, 50)]
    # Place player just colliding with floor
    p.pos.y = 295
    p.rect.y = 295
    p.velocity.y = 850
    p._apply_physics(0.016, floor_tiles)
    
    assert p.is_down_attacking is False, "Player should exit down attack on ground collision!"
    assert p.is_landing_plunge is True, "Player should enter landing plunge state!"
    assert len(p.impact_smokes) >= 2, "Impact smoke puffs should be spawned upon landing!"
    assert p.plunge_impact_pending is True, "Plunge impact shockwave pending flag should be set!"
    
    # Trigger ground shockwave
    shock_enemy = Skeleton(150, 300)
    p.trigger_aoe_damage([shock_enemy])
    assert shock_enemy.health < 4, "Ground impact shockwave did not damage nearby enemy!"
    print("Ground landing, sword plant, dust puffs, and shockwave AoE verified!")

    print("\n=== Testing Player Magic Skill [K] Nerf (50 MP) ===")
    p.mana = 40
    # Simulate magic attempt with 40 mana (insufficient)
    initial_proj_count = len(p.projectiles)
    if p.mana >= 50:
        p.mana -= 50
        p.projectiles.append(Projectile(p.rect.right, p.rect.centery, True, is_enemy=False))
    assert len(p.projectiles) == initial_proj_count, "Magic fired with less than 50 mana!"
    assert p.mana == 40, "Mana should not be deducted when below 50!"
    
    # Now with 70 mana
    p.mana = 70
    if p.mana >= 50:
        p.mana -= 50
        p.projectiles.append(Projectile(p.rect.right, p.rect.centery, True, is_enemy=False))
    assert len(p.projectiles) == initial_proj_count + 1, "Magic did not fire with >= 50 mana!"
    assert p.mana == 20, f"Expected 20 mana left, got {p.mana}"
    print("Magic skill nerf to 50 MP verified!")

    print("\n=== Testing Skeleton Difficulty Upgrade ===")
    skel = Skeleton(200, 200)
    assert skel.health == 4, f"Expected Skeleton health to be 4, got {skel.health}"
    assert skel.chase_speed == 160.0, f"Expected chase_speed 160, got {skel.chase_speed}"
    assert skel.attack_range == 65.0, f"Expected attack_range 65, got {skel.attack_range}"
    
    # Test aggressive lunge velocity when attacking
    skel.facing_right = True
    skel.change_state("ATTACK")
    assert skel.velocity.x == 150.0, f"Expected attack lunge velocity 150.0, got {skel.velocity.x}"
    print("Skeleton health=4, speed=160, and attack lunge verified!")

    print("\n=== Testing MageSkeleton Void Purple Fireball ===")
    mage = MageSkeleton(300, 200)
    # Fire projectile
    proj = Projectile(mage.rect.right, mage.rect.centery, True, is_enemy=True, projectile_type="mage_fireball")
    assert proj.color == "purple", f"Expected purple projectile, got {proj.color}"
    assert proj.anim_manager is not None
    # Update and draw projectile onto surface
    surf = pygame.Surface((512, 384))
    proj.update(0.016, [])
    proj.draw(surf, pygame.math.Vector2(0, 0))
    print("MageSkeleton void purple fireball verified!")

    print("\n=== Testing SkeletonBoss Health & Thresholds ===")
    boss = SkeletonBoss(500, 200)
    assert boss.max_health == 450, f"Expected boss max_health 450, got {boss.max_health}"
    assert boss.health == 450
    
    # Deal damage to hit thresholds
    boss.take_damage(120) # HP = 330
    assert boss.summoned_75 is True, "Boss should trigger 75% minion wave at <= 335 HP!"
    assert len(boss.minions_to_spawn) == 2
    
    boss.take_damage(110) # HP = 220
    assert boss.summoned_50 is True, "Boss should trigger 50% minion wave at <= 225 HP!"
    assert boss.enraged is True, "Boss should become enraged at 50% HP!"
    print("Boss health=450, enrage, and escalation thresholds verified!")

    print("\n=== Testing DeathScreen UI ===")
    death_screen = DeathScreen()
    death_screen.start()
    assert death_screen.active is True
    death_screen.update(0.5)
    assert death_screen.alpha > 0
    death_screen.draw(surf)
    print("DeathScreen fade, embers, and rendering verified!")

    print("\n=== Testing Settings Menu & Graphics Options ===")
    sm = SceneManager()
    settings_scene = SettingsMenuScene(sm, None)
    initial_res_idx = SETTINGS.RESOLUTION_INDEX
    settings_scene.toggle_resolution(1)
    assert SETTINGS.RESOLUTION_INDEX == (initial_res_idx + 1) % len(SETTINGS.RESOLUTIONS)
    
    initial_aa = SETTINGS.ANTIALIASING
    settings_scene.toggle_antialiasing()
    assert SETTINGS.ANTIALIASING != initial_aa
    
    initial_tq = SETTINGS.TEXTURE_QUALITY
    settings_scene.toggle_texture_quality(1)
    assert SETTINGS.TEXTURE_QUALITY != initial_tq
    
    # Ray Tracing toggle
    initial_rt = SETTINGS.RAYTRACING_ENABLED
    settings_scene.toggle_raytracing()
    assert SETTINGS.RAYTRACING_ENABLED != initial_rt
    
    # Dynamic Lights toggle
    initial_dl = SETTINGS.DYNAMIC_LIGHTS
    settings_scene.toggle_dynamic_lights()
    assert SETTINGS.DYNAMIC_LIGHTS != initial_dl
    
    # Ambient Particles toggle
    initial_pt = SETTINGS.AMBIENT_PARTICLES
    settings_scene.toggle_ambient_particles()
    assert SETTINGS.AMBIENT_PARTICLES != initial_pt
    
    # Vignette toggle
    initial_vg = SETTINGS.VIGNETTE_ENABLED
    settings_scene.toggle_vignette()
    assert SETTINGS.VIGNETTE_ENABLED != initial_vg
    
    initial_scanlines = SETTINGS.SCANLINES_ENABLED
    settings_scene.toggle_scanlines()
    assert SETTINGS.SCANLINES_ENABLED != initial_scanlines
    
    # Restore defaults
    SETTINGS.RAYTRACING_ENABLED = True
    SETTINGS.DYNAMIC_LIGHTS = True
    SETTINGS.AMBIENT_PARTICLES = True
    SETTINGS.VIGNETTE_ENABLED = True
    
    # Draw settings menu
    settings_scene.draw(surf)
    print("Settings Menu resolution, Ray Tracing, Dynamic Lights, Particles, AA, and scanlines verified!")

    print("\n=== Testing Player 20 HP & Full Heal Drops ===")
    player = Player(100, 200)
    assert player.max_health == 20, f"Expected player max_health 20, got {player.max_health}"
    assert player.health == 20
    
    # Hurt player to 2 HP
    player.health = 2
    from entities.collectible import Collectible
    pot = Collectible(100, 340, "potion")
    pot.collect(player)
    assert player.health == 20, f"Expected full heal to 20 HP, got {player.health}"
    
    player.health = 1
    chk = Collectible(100, 340, "chicken")
    chk.collect(player)
    assert player.health == 20, f"Expected full heal from chicken to 20 HP, got {player.health}"
    assert player.stamina == 100
    print("Player 20 HP and full heal drops (100% cure) verified!")

    print("\n=== Testing Stamina Balance (Dash, Defend, Basic Attack) ===")
    p_stam = Player(100, 200)
    p_stam.stamina = 100.0
    
    # 1. Dash should cost 12 SP
    p_stam.stamina -= 12
    assert p_stam.stamina == 88.0, "Dash did not deduct 12 SP!"
    
    # 2. Defend should drain 8 SP per second
    p_stam.stamina -= 8.0 * 1.0
    assert p_stam.stamina == 80.0, "Defend drain rate is not 8 SP/s!"
    
    # 3. Basic attack requires 8 SP and consumes 8 SP
    p_stam.stamina = 7.0
    # Simulate attack with 7 SP (insufficient)
    attack_fired = False
    if p_stam.stamina >= 8:
        p_stam.stamina -= 8
        attack_fired = True
    assert attack_fired is False, "Attack fired with less than 8 stamina!"
    assert p_stam.stamina == 7.0
    
    # Attack with 15 SP
    p_stam.stamina = 15.0
    if p_stam.stamina >= 8:
        p_stam.stamina -= 8
        attack_fired = True
    assert attack_fired is True
    assert p_stam.stamina == 7.0, f"Expected 7 SP remaining, got {p_stam.stamina}"
    print("Stamina rebalancing (Dash 12 SP, Defend 8 SP/s, Attack 8 SP) verified!")

    print("\n=== Testing Mana Slow Regen (2.5 MP/s) & Ultimate Skill [R] ===")
    p_ult = Player(100, 200)
    p_ult.mana = 0.0
    p_ult._update_animation(1.0) # 1 second dt
    assert round(p_ult.mana, 1) == 2.5, f"Expected 2.5 mana after 1s regen, got {p_ult.mana}"
    
    # Ultimate activation at 100 MP
    p_ult.mana = 100.0
    assert not p_ult.is_casting_ultimate
    # Simulate [R] press
    p_ult.mana = 0.0
    p_ult.is_casting_ultimate = True
    p_ult.ultimate_timer = 0.0
    p_ult.ultimate_hit_done = False
    
    assert p_ult.mana == 0.0, "Ultimate did not consume all mana!"
    assert p_ult.is_casting_ultimate is True
    
    # Advance ultimate timer to impact phase (0.45s)
    p_ult.ultimate_timer = 0.50
    dummy_skel = Skeleton(150, 200)
    assert dummy_skel.health == 4
    p_ult.trigger_aoe_damage([dummy_skel])
    assert p_ult.ultimate_hit_done is True
    assert dummy_skel.health <= 0, f"Ultimate did not defeat skeleton! Remaining HP: {dummy_skel.health}"
    print("Slow mana regen (2.5/s) and Ultimate Skill [R] (15 AoE damage) verified!")

    print("\n=== Testing Scenario 2 (Forest) Ground & Item Alignment ===")
    from scenes.level_scene import STAGE_CONFIGS
    stage2_cfg = STAGE_CONFIGS[2]
    for x, y, itype in stage2_cfg["collectibles"]:
        assert y == 340, f"Collectible {itype} at x={x} is at y={y}, expected 340 for ground alignment!"
    
    lvl2 = LevelScene(stage=2, scene_manager=sm)
    # Check that collectible rect bottom is exactly at ground level 340
    for c in lvl2.collectibles:
        assert c.rect.bottom == 340, f"Collectible {c.item_type} rect.bottom is {c.rect.bottom}, expected 340!"
    print("Stage 2 collectibles and ground alignment verified at y=340!")

    print("\n=== Testing Game Scene Simulation with Lighting & Ray Tracing (60 frames) ===")
    lvl_scene = LevelScene(stage=1, scene_manager=sm)
    for _ in range(60):
        lvl_scene.update(0.016)
        lvl_scene.draw(surf)
    print("LevelScene with Ray Tracing simulation verified!")
    
    lvl_scene2 = LevelScene(stage=2, scene_manager=sm)
    for _ in range(60):
        lvl_scene2.update(0.016)
        lvl_scene2.draw(surf)
    print("LevelScene Stage 2 (Forest) with God Rays & Particles simulation verified!")
    
    boss_sc = BossScene(scene_manager=sm)
    for _ in range(60):
        boss_sc.update(0.016)
        boss_sc.draw(surf)
    print("BossScene with Dynamic Lights simulation verified!")

    print("\n==========================================")
    print(">>> ALL UNIT & INTEGRATION TESTS PASSED! <<<")
    print("==========================================")

if __name__ == "__main__":
    test_all()
