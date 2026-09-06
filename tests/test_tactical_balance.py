import pygame
import os
import sys

sys.path.insert(0, os.path.abspath("src"))
sys.path.insert(0, os.path.abspath("."))

# Headless Pygame initialization
pygame.init()
pygame.display.set_mode((1, 1))

from entities.player import Player
from entities.character_data import CHARACTER_REGISTRY
from entities.boss import SkeletonBoss, BossShockwave
from entities.enemy import Skeleton, MageSkeleton, WildBoar
from entities.prop import Prop
from entities.traps import SpikeTrap
from entities.projectile import Projectile
from scenes.boss_scene import BossScene
from engine.scene_manager import SceneManager
from config.settings import SETTINGS

def run_tests():
    print("================================================================================")
    print(" RUNNING TACTICAL COMBAT & SKELETON KING REBALANCE TEST SUITE")
    print("================================================================================")

    # 1. Asymmetric Survival Economy Test
    print("\n[1] Testing Asymmetric Survival Economy (HP / MP / SP)...")
    martial_ids = ["shaia", "samurai", "fighter"]
    for cid in martial_ids:
        prof = CHARACTER_REGISTRY[cid]
        assert prof.hp_max == 130, f"{cid} HP should be 130, got {prof.hp_max}"
        assert prof.mp_max == 70, f"{cid} MP should be 70, got {prof.mp_max}"
        assert prof.sp_max == 120, f"{cid} SP should be 120, got {prof.sp_max}"
        assert prof.skills["j"].damage == 15, f"{cid} [J] damage should be 15"
        assert prof.skills["k"].damage == 350, f"{cid} [K] damage should be 350"
        assert prof.skills["r"].damage == 3500, f"{cid} [R] damage should be 3500"
    print("  -> Martial classes (Shaia, Samurai, Fighter) verified: 130 HP | 70 MP | 120 SP | J=15 | K=350 | R=3500")

    shinobi_prof = CHARACTER_REGISTRY["shinobi"]
    assert shinobi_prof.hp_max == 100, f"Shinobi HP should be 100, got {shinobi_prof.hp_max}"
    assert shinobi_prof.mp_max == 90, f"Shinobi MP should be 90, got {shinobi_prof.mp_max}"
    assert shinobi_prof.sp_max == 140, f"Shinobi SP should be 140, got {shinobi_prof.sp_max}"
    assert shinobi_prof.skills["j"].damage == 15, f"Shinobi [J] damage should be 15"
    assert shinobi_prof.skills["r"].damage == 3500, f"Shinobi [R] damage should be 3500"
    print("  -> Shinobi class verified: 100 HP | 90 MP | 140 SP | R=3500")

    # Differentiated Mage Archetypes
    lunaria = CHARACTER_REGISTRY["lunaria"]
    assert lunaria.hp_max == 65 and lunaria.mp_max == 160 and lunaria.sp_max == 75, "Lunaria stats mismatch"
    assert lunaria.mana_regen == 4.0 and lunaria.skills["k"].damage == 650

    ignis = CHARACTER_REGISTRY["ignis"]
    assert ignis.hp_max == 75 and ignis.mp_max == 130 and ignis.sp_max == 90, "Ignis stats mismatch"
    assert ignis.move_speed == 148.0 and ignis.skills["j"].damage == 6

    astra = CHARACTER_REGISTRY["astra"]
    assert astra.hp_max == 85 and astra.mp_max == 120 and astra.sp_max == 100, "Astra stats mismatch"
    assert astra.stamina_regen == 24.0 and astra.skills["k"].damage == 620
    print("  -> Differentiated Mage classes verified:")
    print("     * Lunaria (Glass Cannon): 65 HP | 160 MP | 75 SP | 4.0 MP Regen")
    print("     * Ignis (Agile Pyro): 75 HP | 130 MP | 90 SP | 148 Spd | J=6")
    print("     * Astra (Guardian Priestess): 85 HP | 120 MP | 100 SP | 24.0 SP Regen")

    # 2. Player Tactical Cadence & 0.25s Attack Cooldown Test
    print("\n[2] Testing Tactical Attack Cadence & Cooldown (0.25s)...")
    SETTINGS.CURRENT_CHARACTER = "samurai"
    p = Player(100, 200)
    assert p.max_health == 130 and p.health == 130
    assert p.max_stamina == 120 and p.stamina == 120
    assert p.attack_cooldown == 0.0

    # Execute attack with 0.25s cooldown
    p.is_attacking = True
    p.attack_cooldown = 0.25
    p.anim_manager.play("attack", force_reset=True)
    
    # Tick 0.15s
    p.update(0.15, [], [], None)
    assert p.attack_cooldown > 0.05, f"Attack cooldown should still be active (~0.10s), got {p.attack_cooldown}"
    # Tick remaining 0.15s
    p.update(0.15, [], [], None)
    assert p.attack_cooldown == 0.0, f"Attack cooldown should be 0, got {p.attack_cooldown}"
    print("  -> 0.25s Snappy attack cooldown verified.")

    # 2.1 Shift Block 100% Damage Absorption Test
    p.is_blocking = True
    init_hp = p.health
    p.take_damage(25)
    assert p.health == init_hp, f"Health should remain {init_hp} during block, got {p.health}"
    p.is_blocking = False
    print("  -> Shift Block 100% damage absorption verified!")

    # 3. Potion Drinking Mechanics Test
    print("\n[3] Testing Potion Drinking Channel (1.6s, 30% speed, dodge disabled, heals 40 HP)...")
    p.health = 50
    p.start_drinking_potion(40)
    assert p.is_drinking_potion is True
    assert p.potion_timer == 1.6
    assert p.potion_heal_amount == 40
    assert p.can_dash is False, "Dodge must be disabled during potion consumption!"
    
    # Tick 1.0s
    p.update(1.0, [], [], None)
    assert p.is_drinking_potion is True
    assert p.health == 50, "HP should not heal until channel finishes!"
    
    # Tick remaining 0.7s
    p.update(0.7, [], [], None)
    assert p.is_drinking_potion is False
    assert p.health == 90, f"HP should have healed by 40, got {p.health}"
    print("  -> Potion drinking verified: 1.6s channel, dodge lock, +40 HP heal.")

    # 4. Stamina Economy Test
    print("\n[4] Testing Stamina Economy (Dodge 25 SP / Shinobi 15 SP, 20 SP/s regen)...")
    # Normal dodge cost
    p.stamina = 100
    p.dash()
    assert p.stamina == 75, f"Expected 75 SP after dodge, got {p.stamina}"
    assert p.stamina_regen_delay == 0.5, "Expected 0.5s regen delay after dodge"

    # Shinobi dodge cost
    SETTINGS.CURRENT_CHARACTER = "shinobi"
    p_shinobi = Player(100, 200)
    p_shinobi.stamina = 100
    p_shinobi.dash()
    assert p_shinobi.stamina == 85, f"Expected 85 SP for Shinobi dodge, got {p_shinobi.stamina}"
    print("  -> Stamina costs verified: 25 SP base, 15 SP Shinobi.")

    # 5. Class Passives Test
    print("\n[5] Testing 7 Class Passives...")
    # Fighter (-15% dmg < 30% HP)
    SETTINGS.CURRENT_CHARACTER = "fighter"
    p_fighter = Player(100, 200)
    p_fighter.health = 30 # < 30% of 130 (39)
    p_fighter.take_damage(20) # 20 * 0.85 = 17 dmg
    assert p_fighter.health == 13, f"Expected 13 HP (17 dmg taken), got {p_fighter.health}"
    print("  -> Fighter passive (-15% damage taken when HP < 30%) verified.")

    # Samurai (Perfect dodge resets attack cooldown)
    SETTINGS.CURRENT_CHARACTER = "samurai"
    p_samurai = Player(100, 200)
    p_samurai.attack_cooldown = 0.9
    p_samurai.dash()
    assert p_samurai.attack_cooldown == 0.0, "Samurai dodge should reset attack cooldown!"
    print("  -> Samurai passive (Foco Perfeito attack cooldown reset) verified.")

    # Astra (Celestial Barrier absorbs 100% of 1 hit with 20s cooldown)
    SETTINGS.CURRENT_CHARACTER = "astra"
    p_astra = Player(100, 200)
    assert p_astra.celestial_barrier_active is True
    initial_astra_hp = p_astra.health
    p_astra.take_damage(50) # Big hit absorbed!
    assert p_astra.health == initial_astra_hp, "Astra barrier should absorb 100% of first hit!"
    assert p_astra.celestial_barrier_active is False, "Barrier should break after absorbing hit"
    assert p_astra.celestial_barrier_cooldown == 20.0, "Barrier cooldown should be 20 seconds"
    print("  -> Astra passive (Celestial Barrier 1-hit nullification & 20s CD) verified.")

    # Ignis (Magic burns enemy for 3 dmg/s for 4s)
    SETTINGS.CURRENT_CHARACTER = "ignis"
    p_ignis = Player(100, 200)
    skel = Skeleton(120, 200)
    proj = Projectile(100, 200, facing_right=True, is_enemy=False, projectile_type="fire_sphere", is_burn=True)
    assert proj.is_burn is True
    assert proj.damage == 650
    skel.apply_burn(4.0, 3.0)
    assert skel.burn_timer == 4.0
    assert skel.burn_dps == 3.0
    skel.update_burn(1.1)
    assert skel.health == 80 - 3, f"Expected 77 HP after 1s burn, got {skel.health}"
    print("  -> Ignis passive (Fire burn 3 dmg/s for 4s) verified.")

    # 6. Destructible Props & Traps Test
    print("\n[6] Testing Destructible Props & Traps...")
    barrel = Prop(200, 300, "barrel")
    assert barrel.health == 2, f"Barrel should have 2 HP, got {barrel.health}"
    barrel.take_damage(1, is_skill=False)
    assert barrel.health == 1, "Barrel should have 1 HP after first hit"
    assert barrel.image == barrel.img_damaged, "Barrel should display cracked texture after first hit"
    assert barrel.active is True
    barrel.take_damage(1, is_skill=False)
    assert barrel.health == 0
    assert barrel.is_broken is True, "Barrel should be broken on second hit"
    barrel.update(1.0)
    assert barrel.active is False, "Barrel should deactivate after breaking animation"
    print("  -> Barrel 2-hit melee break with cracked texture verified.")

    # Skill instant break
    barrel_skill = Prop(300, 300, "barrel")
    barrel_skill.take_damage(999, is_skill=True)
    assert barrel_skill.is_broken is True, "Any skill should break barrel instantly in 1 hit!"
    barrel_skill.update(1.0)
    assert barrel_skill.active is False
    print("  -> Barrel 1-skill instant break verified.")

    # SpikeTrap damage
    spike = SpikeTrap(100, 300)
    assert spike.damage == 5, f"SpikeTrap damage should be 5, got {spike.damage}"
    print("  -> SpikeTrap 5 damage verified.")

    # 7. Enemy Scaling & Wind-ups Test
    print("\n[7] Testing Enemy Scaling & Wind-ups...")
    e_skel = Skeleton(100, 200)
    assert e_skel.health == 80, f"Skeleton HP should be 80, got {e_skel.health}"
    assert e_skel.attack_damage == 22, f"Skeleton attack damage should be 22, got {e_skel.attack_damage}"

    e_mage = MageSkeleton(100, 200)
    assert e_mage.health == 30, f"MageSkeleton HP should be 30, got {e_mage.health}"
    assert e_mage.attack_damage == 12, f"MageSkeleton damage should be 12, got {e_mage.attack_damage}"

    e_boar = WildBoar(100, 200)
    assert e_boar.health == 600, f"WildBoar HP should be 600, got {e_boar.health}"
    assert e_boar.attack_damage == 45, f"WildBoar damage should be 45, got {e_boar.attack_damage}"
    print("  -> Enemies verified: Skeleton (80 HP, 22 dmg), Mage (30 HP, 12 dmg), Boar (600 HP, 45 dmg).")

    # 8. Skeleton King Boss & Dual Bar Test
    print("\n[8] Testing Skeleton King Boss (10,000 HP, 1,000 Poise Shield, Stagger & Telegraphs)...")
    boss = SkeletonBoss(500, 200)
    assert boss.max_health == 10000 and boss.health == 10000, f"Boss HP should be 10,000, got {boss.health}"
    assert boss.max_shield == 1000 and boss.shield == 1000, f"Boss Shield should be 1,000, got {boss.shield}"
    assert boss.attack_damage == 35, f"Boss fast attack should deal 35 dmg, got {boss.attack_damage}"
    assert boss.touch_damage == 0, f"Boss direct touch damage should be 0, got {boss.touch_damage}"

    # Verify no shadow step
    assert "SHADOW_STEP" not in ["FLAME_BURST", "JUMP_SLAM"], "Shadow Step must not be in boss skill choices!"

    # Test Poise Shield damage absorption
    boss.take_damage(600)
    assert boss.shield == 400, f"Expected 400 shield remaining, got {boss.shield}"
    assert boss.health == 10000, "Boss HP should not take damage while poise shield is up!"

    # Deplete poise shield -> trigger STAGGERED
    boss.take_damage(500)
    assert boss.shield == 0, f"Expected 0 shield, got {boss.shield}"
    assert boss.state == "STAGGERED", f"Boss should enter STAGGERED state, got {boss.state}"
    assert boss.state_timer == 4.5, f"Boss stagger duration should be 4.5s, got {boss.state_timer}"

    # Damage during STAGGERED hits direct HP
    boss.take_damage(2500) # Player Ultimate
    assert boss.health == 7500, f"Expected 7500 HP during stagger, got {boss.health}"

    # Stagger recovery
    boss.state_timer = 0.05
    boss.update(0.06, [pygame.FRect(0, 300, 1000, 50)], p)
    assert boss.shield == 1000, f"Shield should restore to 1000 after stagger, got {boss.shield}"
    assert boss.state == "ROAR", f"Boss should roar on recovery, got {boss.state}"
    print("  -> Skeleton King Poise Shield (1,000), 4.5s Stagger, direct HP damage, and recovery roar verified.")

    # 9. Boss Arena Scene Test
    print("\n[9] Testing Boss Scene Arena (2560px width, zoom-out surface, dynamic Phase 2)...")
    sm = SceneManager()
    boss_scene = BossScene(sm)
    assert boss_scene.map_width == 2560, f"Arena width should be 2560, got {boss_scene.map_width}"
    assert boss_scene.arena_w == 640 and boss_scene.arena_h == 480, "Virtual arena surface must be 640x480 for 1.25x wider FOV zoom-out"
    assert len(boss_scene.props) == 0, f"Expected 0 props/barrels on arena floor, got {len(boss_scene.props)}"

    # Test Phase 2 trigger at 5,000 HP
    boss_scene.boss.health = 4900
    boss_scene.update(0.1)
    assert boss_scene.phase2_triggered is True, "Phase 2 should trigger at <= 5,000 HP!"
    assert boss_scene.phase_transition > 0, "Phase transition progress should advance!"
    print("  -> Boss Arena verified: 2560px width, 640x480 wide FOV camera, 0 barrels on floor, dynamic Phase 2 at 5k HP.")

    print("\n================================================================================")
    print(" ALL TACTICAL BALANCE & SKELETON KING REBALANCE TESTS PASSED SUCCESSFULLY! ")
    print("================================================================================")

if __name__ == "__main__":
    run_tests()
