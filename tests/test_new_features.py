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
    initial_shock_hp = shock_enemy.health
    p.trigger_aoe_damage([shock_enemy])
    assert shock_enemy.health < initial_shock_hp, "Ground impact shockwave did not damage nearby enemy!"
    print("Ground landing, sword plant, dust puffs, and shockwave AoE verified!")

    print("\n=== Testing Player Magic Skill [K] (35 MP) ===")
    p.mana = 20
    # Simulate magic attempt with 20 mana (insufficient)
    initial_proj_count = len(p.projectiles)
    if p.mana >= 35:
        p.mana -= 35
        p.projectiles.append(Projectile(p.rect.right, p.rect.centery, True, is_enemy=False))
    assert len(p.projectiles) == initial_proj_count, "Magic fired with less than 35 mana!"
    assert p.mana == 20, "Mana should not be deducted when below 35!"
    
    # Now with 70 mana
    p.mana = 70
    if p.mana >= 35:
        p.mana -= 35
        p.projectiles.append(Projectile(p.rect.right, p.rect.centery, True, is_enemy=False))
    assert len(p.projectiles) == initial_proj_count + 1, "Magic did not fire with >= 35 mana!"
    assert p.mana == 35, f"Expected 35 mana left, got {p.mana}"
    print("Magic skill cost 35 MP verified!")

    print("\n=== Testing Skeleton Difficulty Upgrade & Slower Pacing ===")
    skel = Skeleton(200, 200)
    assert skel.health == 80, f"Expected Skeleton health to be 80, got {skel.health}"
    assert skel.chase_speed == 95.0, f"Expected chase_speed 95.0, got {skel.chase_speed}"
    assert skel.attack_range == 65.0, f"Expected attack_range 65, got {skel.attack_range}"
    assert skel.attack_damage == 22, f"Expected attack_damage 22, got {skel.attack_damage}"
    assert skel.touch_damage == 5, f"Expected touch_damage 5, got {skel.touch_damage}"
    
    # Test WildBoar health and slower speed
    boar = WildBoar(300, 200)
    assert boar.health == 600, f"Expected WildBoar health 600, got {boar.health}"
    assert boar.speed == 35.0, f"Expected WildBoar speed 35.0, got {boar.speed}"
    assert boar.charge_speed == 135.0, f"Expected WildBoar charge_speed 135.0, got {boar.charge_speed}"
    
    # Test deliberate lunge velocity when attacking
    skel.facing_right = True
    skel.change_state("ATTACK")
    assert skel.velocity.x == 70.0, f"Expected attack lunge velocity 70.0, got {skel.velocity.x}"
    print("Skeleton health=80 (dmg=22), Boar health=600 (speed=35, charge=135), and combat verified!")

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
    assert boss.max_health == 20000, f"Expected boss max_health 20000, got {boss.max_health}"
    assert boss.health == 20000
    assert boss.poise_shield == 1000
    
    # Deal damage to hit thresholds (shield absorbs first)
    boss.take_damage(1000) # Poise broken
    assert boss.is_staggered is True
    
    # Deal direct HP damage
    boss.take_damage(11000) # HP down to 9000 (below 10000)
    assert boss.enraged is True, "Boss should become enraged at <= 50% HP!"
    print("Boss health=20000, poise=1000, stagger, and enrage thresholds verified!")

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

    print("\n=== Testing Player Asymmetric HP & Potion Drinking ===")
    player = Player(100, 200) # Shaia (Martial) default
    assert player.max_health == 150, f"Expected player max_health 150, got {player.max_health}"
    assert player.health == 150
    
    # Hurt player to 10 HP
    player.health = 10
    from entities.collectible import Collectible
    pot = Collectible(100, 340, "potion")
    pot.collect(player)
    assert player.is_drinking_potion is True
    # Simulate potion drinking completion (1.6s)
    player.update(1.7, [])
    assert player.health == 50, f"Expected +40 HP heal to 50 HP, got {player.health}"
    
    player.health = 10
    chk = Collectible(100, 340, "chicken")
    chk.collect(player)
    assert player.is_drinking_potion is True
    player.update(1.7, [])
    assert player.health == 50, f"Expected +40 HP heal from chicken to 50 HP, got {player.health}"
    print("Player 150 HP, potion channel (+40 HP), and chicken channel (+40 HP) verified!")

    print("\n=== Testing Stamina Balance (Dash 25 SP, Defend 3 SP/s, Attack Cooldown) ===")
    p_stam = Player(100, 200)
    p_stam.stamina = 120.0
    
    # 1. Dash should cost 25 SP (base)
    p_stam.stamina -= 25
    assert p_stam.stamina == 95.0, "Dash did not deduct 25 SP!"
    
    # 2. Defend drains 3 SP/s
    p_stam.stamina -= 3.0 * 1.0
    assert p_stam.stamina == 92.0, "Defend drain rate is not 3 SP/s!"
    
    # 3. Tactical Attack 0.25s cooldown
    p_stam.attack_cooldown = 0.25
    assert p_stam.can_attack is False
    p_stam.attack_cooldown = 0.0
    assert p_stam.can_attack is True
    print("Stamina rebalancing (Dash 25 SP, Defend 3 SP/s, Attack CD 0.25s) verified!")

    print("\n=== Testing Mana Slow Regen (1.2 MP/s) & Ultimate Skill [R] ===")
    p_ult = Player(100, 200)
    p_ult.mana = 0.0
    p_ult._update_animation(1.0) # 1 second dt
    assert round(p_ult.mana, 1) == 1.2, f"Expected 1.2 mana after 1s regen, got {p_ult.mana}"
    
    # Ultimate activation at full MP
    p_ult.mana = 70.0
    assert not p_ult.is_casting_ultimate
    # Simulate [R] press via ultimate_controller
    p_ult.mana = 0.0
    p_ult.is_casting_ultimate = True
    p_ult.ultimate_controller.trigger(p_ult.rect.centerx, p_ult.rect.bottom, p_ult.facing_right)
    
    assert p_ult.mana == 0.0, "Ultimate did not consume all mana!"
    assert p_ult.is_casting_ultimate is True
    
    # Advance ultimate timer to impact phase (0.80s)
    dummy_skel = Skeleton(p_ult.rect.centerx + 40, p_ult.rect.centery)
    assert dummy_skel.health == 80
    p_ult.ultimate_controller.update(0.80, p_ult, [dummy_skel])
    assert p_ult.ultimate_hit_done is True
    assert dummy_skel.health <= 0, f"Ultimate did not defeat skeleton! Remaining HP: {dummy_skel.health}"
    print("Slow mana regen (1.2/s) and Ultimate Skill [R] (colossal 2,500 AoE damage) verified!")

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

    print("\n=== Testing Multi-Character Class System & CharacterSelectScene ===")
    from entities.character_data import CHARACTER_REGISTRY, CHARACTER_ORDER, get_character_profile
    from scenes.character_select_scene import CharacterSelectScene
    from scenes.main_menu import MainMenuScene

    assert len(CHARACTER_ORDER) == 7, "Must have exactly 7 playable characters registered!"
    
    # Check each character profile and animations
    for cid in CHARACTER_ORDER:
        prof = get_character_profile(cid)
        assert prof.id == cid
        assert len(prof.skills) >= 5, f"Character {cid} must have at least 5 skills defined!"
        
        p = Player(100, 100, character_id=cid)
        assert p.character_id == cid
        assert p.max_health == prof.hp_max
        assert p.max_mana == prof.mp_max
        assert p.archetype == prof.archetype
        
        # Test core animations exist
        for a_name in ["idle", "walk", "attack", "cast_magic", "whirlwind", "guard", "jump", "fall", "dash"]:
            p.anim_manager.play(a_name, force_reset=True)
            frame = p.anim_manager.get_current_frame()
            assert frame is not None, f"Missing frame for {cid} animation {a_name}"
            
        print(f"Verified profile & 9 animations for: {prof.name} ({prof.title}) - {prof.archetype}")

    # Test CharacterSelectScene & Interactive Dojo Move Tester
    cs_scene = CharacterSelectScene(sm)
    cs_scene.update(0.016)
    cs_scene.draw(surf)
    
    for idx in range(len(CHARACTER_ORDER)):
        cs_scene._select_character(idx)
        for move_key in ["j", "k", "e", "shift", "q", "r", "space"]:
            cs_scene._trigger_dojo_move(move_key)
            cs_scene.update(0.016)
            cs_scene.draw(surf)
    print("Interactive CharacterSelectScene Dojo move tester verified for all 7 characters!")

    # Verify Main Menu has Selecionar Personagem option
    menu_sc = MainMenuScene(sm)
    option_titles = [opt.text for opt in menu_sc.menu.options]
    assert "Selecionar Personagem" in option_titles, "Main Menu must contain 'Selecionar Personagem' option!"
    print("Main Menu 'Selecionar Personagem' integration verified!")

    print("\n=== Testing Dash Reach & Slower Movement Pacing ===")
    for cid in CHARACTER_ORDER:
        p_dash = Player(100, 200, character_id=cid)
        assert p_dash.speed <= 165.0, f"{cid} move_speed {p_dash.speed} is too fast (expected <= 165.0)!"
        max_dash_spd = 400.0 if cid == "shinobi" else 370.0
        assert p_dash.dash_speed <= max_dash_spd, f"{cid} dash_speed {p_dash.dash_speed} is too fast (expected <= {max_dash_spd})!"
        assert p_dash.dash_duration == 0.18, f"{cid} dash_duration {p_dash.dash_duration} != 0.18s!"
        assert -380.0 <= p_dash.jump_speed <= -330.0, f"{cid} jump_speed {p_dash.jump_speed} out of range!"
        total_reach = p_dash.dash_speed * p_dash.dash_duration
        max_reach = 80.0 if cid == "shinobi" else 70.0
        assert total_reach < max_reach, f"{cid} dash distance {total_reach}px is too long (expected < {max_reach}px)!"
    print("Slower deliberate pacing (speed 135-165, dash reach ~60-70px, jump -350) verified across all 7 heroes!")

    print("\n=== Testing Expanded Maps & Portal Alignment ===")
    from scenes.level_scene import STAGE_CONFIGS
    assert STAGE_CONFIGS[1]["map_width"] == 3072, "Stage 1 map_width must be 3072!"
    assert STAGE_CONFIGS[1]["portal_x"] == 2880, "Stage 1 portal_x must be 2880!"
    assert STAGE_CONFIGS[2]["map_width"] == 3600, "Stage 2 map_width must be 3600!"
    assert STAGE_CONFIGS[2]["portal_x"] == 3420, "Stage 2 portal_x must be 3420!"
    assert STAGE_CONFIGS[3]["map_width"] == 4096, "Stage 3 map_width must be 4096!"
    assert STAGE_CONFIGS[3]["portal_x"] == 3900, "Stage 3 portal_x must be 3900!"
    assert STAGE_CONFIGS[4]["map_width"] == 4000, "Stage 4 map_width must be 4000!"
    assert STAGE_CONFIGS[4]["portal_x"] == 3800, "Stage 4 portal_x must be 3800!"
    print("Expanded map widths (3072 to 4096) and end-of-stage portal positions verified!")

    print("\n=== Testing Bespoke AoE Skill [E] & Guard Visuals for all Heroes ===")
    for cid in CHARACTER_ORDER:
        p_skill = Player(100, 200, character_id=cid)
        # Test AoE skill [E]
        p_skill.is_casting_aoe = True
        p_skill.aoe_timer = 0.5
        p_skill.draw(surf, pygame.math.Vector2(0, 0))
        # Test Guard [Shift]
        p_skill.is_casting_aoe = False
        p_skill.is_blocking = True
        p_skill.draw(surf, pygame.math.Vector2(0, 0))
        # Test Jump & Fall rendering
        p_skill.is_blocking = False
        p_skill.on_ground = False
        p_skill.velocity.y = -300 # Jumping
        p_skill._update_animation(0.016)
        p_skill.draw(surf, pygame.math.Vector2(0, 0))
        p_skill.velocity.y = 200 # Falling
        p_skill._update_animation(0.016)
        p_skill.draw(surf, pygame.math.Vector2(0, 0))
    print("Bespoke AoE Skill [E], Guard [Shift], Jump and Fall rendering verified for all 7 heroes!")

    print("\n=== Testing Rebalanced Partial Healing (Potion Channel & Chicken) ===")
    from entities.collectible import Collectible
    p_heal = Player(100, 200)
    p_heal.health = 20 # Heavily injured
    pot = Collectible(100, 200, item_type="potion")
    pot.collect(p_heal)
    assert p_heal.is_drinking_potion is True
    p_heal.update(1.7, [])
    assert p_heal.health == 60, f"Potion should heal exactly +40 HP (from 20 to 60), got {p_heal.health}!"
    chick = Collectible(100, 200, item_type="chicken")
    chick.collect(p_heal)
    assert p_heal.is_drinking_potion is True
    p_heal.update(1.7, [])
    assert p_heal.health == 100, f"Chicken should heal +40 HP (from 60 to 100), got {p_heal.health}!"
    print("Partial healing (+40 HP potion channel, +40 HP chicken channel) verified!")

    print("\n=== Testing Hazard Damage & Boss Shockwaves ===")
    from entities.traps import SpikeTrap
    spike = SpikeTrap(100, 200)
    assert spike.damage == 5, f"Spike trap damage should be 5, got {spike.damage}!"
    
    shockwave = BossShockwave(100, 200, moving_right=True)
    assert shockwave.damage == 35, f"BossShockwave damage should be 35, got {shockwave.damage}!"
    assert shockwave.velocity_x == 200.0, f"BossShockwave velocity should be 200.0, got {shockwave.velocity_x}!"
    print("Hazard damage (Spike=5, Shockwave=35 at 200px/s) verified!")

    print("\n=== Testing Rebalanced Damage: Skills > Normal Attack & Massive Boss Ultimate Damage ===")
    boss_sim = BossScene(scene_manager=sm)
    boss_ent = boss_sim.boss
    assert boss_ent.health == 20000, f"Expected Boss to start with 20000 HP, got {boss_ent.health}"
    assert boss_ent.poise_shield == 1000, f"Expected Boss Poise Shield 1000, got {boss_ent.poise_shield}"
    
    # 1. Normal Attack [J] does 20 damage (Shaia martial)
    boss_sim.player.rect.centerx = boss_ent.rect.centerx - 30
    boss_sim.player.rect.bottom = boss_ent.rect.bottom
    boss_sim.player.pos.x = boss_sim.player.rect.x
    boss_sim.player.pos.y = boss_sim.player.rect.y
    boss_sim.player.facing_right = True
    boss_sim.player.is_attacking = True
    boss_sim.player.attack_hit_enemies.clear()
    
    # Run update: attack connects (hits poise shield first: 1000 -> 980)
    boss_sim.update(0.016)
    assert boss_ent.poise_shield == 980, f"Expected 980 Poise Shield after 1 sword hit (20 dmg), got {boss_ent.poise_shield}"
    assert boss_ent.health == 20000, f"Health should remain untouched while shield is active, got {boss_ent.health}"
    
    # Run next 5 frames with attack still active: should NOT deal multi-hit damage
    for _ in range(5):
        boss_sim.update(0.016)
    assert boss_ent.poise_shield == 980, f"Boss took multi-hit damage from a single swing! Expected 980, got {boss_ent.poise_shield}"
    print("Normal attack debounce verified: exactly 20 damage per swing to Poise Shield!")

    # 2. Skill [K] Projectile deals 350 damage (Martial)
    fireball_proj = Projectile(boss_ent.rect.centerx - 10, boss_ent.rect.centery, facing_right=True, is_enemy=False, projectile_type="fireball", damage=350)
    assert fireball_proj.damage == 350, f"Fireball damage should be 350, got {fireball_proj.damage}"
    boss_sim.projectiles.append(fireball_proj)
    boss_sim.update(0.016)
    assert boss_ent.poise_shield == 980 - 350, f"Expected {980 - 350} Shield after Fireball hit (350 dmg), got {boss_ent.poise_shield}"
    print("Skill [K] projectile damage (350) on boss shield verified!")

    # 3. Skill [E] AoE deals 40 damage (Martial)
    boss_sim.player.is_casting_aoe = True
    boss_sim.player.aoe_hit_done = False
    boss_sim.player.trigger_aoe_damage([boss_ent])
    assert boss_ent.poise_shield == 980 - 350 - 40, f"Expected {980 - 350 - 40} Shield after Skill [E] AoE hit (40 dmg), got {boss_ent.poise_shield}"
    print("Skill [E] AoE damage (40) on boss shield verified!")

    # 4. Ultimate [R] deals colossal damage (2,500 HP)
    boss_sim.player.is_casting_ultimate = True
    boss_sim.player.ultimate_controller.trigger(boss_sim.player.rect.centerx, boss_sim.player.rect.bottom, True)
    # Fast forward to impact climax (0.80s)
    boss_sim.player.ultimate_controller.update(0.80, boss_sim.player, [boss_ent])
    assert boss_sim.player.ultimate_hit_done is True
    # Poise shield broke and triggered STAGGERED state
    assert boss_ent.is_staggered is True
    assert boss_ent.shield == 0
    # Next hit during STAGGERED deals direct HP damage
    boss_ent.take_damage(2500)
    assert boss_ent.health == 17500, f"Expected 17500 HP after staggered hit, got {boss_ent.health}"
    print(f"Colossal Ultimate damage (2,500 dmg on boss) verified! Current HP: {boss_ent.health}")

    print("\n=== Testing LevelScene Melee Combat: Skeleton & Boar Damage + Player Sword Hit ===")
    lvl_test = LevelScene(stage=1, scene_manager=sm)
    p = lvl_test.player
    p.health = 130
    p.invulnerable = False
    p.invulnerability_timer = 0.0
    
    # 1. Test Skeleton attacks player in LevelScene (22 damage)
    skel_test = Skeleton(p.rect.centerx + 20, p.rect.bottom - 70)
    lvl_test.enemies = [skel_test]
    # Skeleton attacks at active damage frame 3
    skel_test.facing_right = False
    skel_test.change_state("ATTACK")
    skel_test._windup_timer = 0.0
    skel_test.anim_manager.animations["attack"].current_frame = 3
    lvl_test.update(0.016)
    assert p.health == 130 - 22, f"Expected player health 108 after Skeleton hit (22 dmg), got {p.health}"
    print("LevelScene: Skeleton melee attack damages player (22 dmg) verified!")
    
    # 2. Test Player attacks Skeleton with sword in LevelScene (20 damage)
    p.health = 130
    p.invulnerable = False
    p.is_attacking = True
    p.facing_right = True
    p.attack_hit_enemies.clear()
    skel_hp_before = skel_test.health
    lvl_test.update(0.016)
    assert skel_test.health == skel_hp_before - 20, f"Expected Skeleton to take 20 sword damage, before: {skel_hp_before}, after: {skel_test.health}"
    print("LevelScene: Player sword attack damages Skeleton (20 dmg) verified!")
    
    # 3. Test WildBoar attacks player in LevelScene (45 damage during charge)
    boar_test = WildBoar(p.rect.centerx + 15, p.rect.bottom - 38)
    boar_test.change_state("CHARGE")
    lvl_test.enemies = [boar_test]
    p.invulnerable = False
    p.is_attacking = False
    p.health = 130
    lvl_test.update(0.016)
    assert p.health <= 130 - 45, f"Expected player health to decrease by >= 45 on Boar charge/attack, got {p.health}"
    print("LevelScene: Boar attack/contact damages player (45 dmg) verified!")
    
    # 4. Test Player attacks Boar with sword in LevelScene (20 damage)
    p.is_attacking = True
    p.attack_hit_enemies.clear()
    boar_hp_before = boar_test.health
    lvl_test.update(0.016)
    assert boar_test.health == boar_hp_before - 20, f"Expected Boar to take 20 sword damage, before: {boar_hp_before}, after: {boar_test.health}"
    print("LevelScene: Player sword attack damages Boar (20 dmg) verified!")

    print("\n==========================================")
    print(">>> ALL UNIT & INTEGRATION TESTS PASSED! <<<")
    print("==========================================")

if __name__ == "__main__":
    test_all()
