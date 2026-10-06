import os
import sys
import pygame

# Set dummy headless video driver
os.environ["SDL_VIDEODRIVER"] = "dummy"

sys.path.insert(0, os.path.abspath("src"))
sys.path.insert(0, os.path.abspath("."))

from entities.character_data import CHARACTER_ORDER, get_character_profile
from entities.player import Player
from entities.projectile import Projectile
from entities.ultimate_aoe_vfx import UltimateAoE_VFX, _AOE_VFX_REGISTRY
from entities.ultimate_system import create_ultimate

def test_all_characters_and_skills():
    pygame.init()
    screen = pygame.display.set_mode((640, 384))
    
    print("=== TEST 1: All 11 Characters Skills & Profiles ===")
    for cid in CHARACTER_ORDER:
        profile = get_character_profile(cid)
        print(f"Checking {cid}: {profile.name} - Archetype: {profile.archetype}")
        
        # Instantiate Player
        p = Player(100, 200, character_id=cid)
        assert p.character_id == cid
        
        # Test Attack [J]
        p.attack()
        assert p.is_attacking or len(p.projectiles) > 0
        p.update(0.016, [], [])
        
        # Test Skill [K]
        p.is_attacking = False
        p.mana = p.max_mana
        p.cast_skill()
        p.update(0.016, [], [])
        
        # Test AoE [E]
        p.is_casting_magic = False
        p.mana = p.max_mana
        p.stamina = p.max_stamina
        p.cast_aoe()
        assert p.is_casting_aoe
        assert p.aoe_vfx is not None
        p.aoe_vfx.update(0.016)
        p.aoe_vfx.draw(screen, pygame.math.Vector2(0, 0))
        
        # Test Ultimate [R]
        p.is_casting_aoe = False
        p.mana = p.max_mana
        p.cast_ultimate()
        assert p.is_casting_ultimate
        p.ultimate_controller.update(0.016, p)
        p.ultimate_controller.draw_world(screen, pygame.math.Vector2(0, 0))
        
        print(f"  -> SUCCESS: {cid} [J], [K], [E], [R] verified cleanly!")
        
    print("\n=== TEST 2: All Projectile Types & Dedicated Renderers ===")
    ptypes = [
        "fireball", "fire_spark", "fire_sphere", "arcane_bolt", "arcane_sphere",
        "frost_lance", "frost_orb", "ki_blast", "shuriken", "vacuum_slash",
        "holy_ray", "heal_orb", "arrow_fast", "arrow_fire", "wind_blade", "mana_orb", "earth_spike"
    ]
    for pt in ptypes:
        proj = Projectile(100, 100, True, is_enemy=False, projectile_type=pt)
        assert proj.active
        # Simulate fly
        proj.update(0.016)
        proj.draw(screen, pygame.math.Vector2(0, 0))
        # Simulate explode
        proj.explode()
        proj.update(0.016)
        proj.draw(screen, pygame.math.Vector2(0, 0))
        print(f"  -> Projectile '{pt}' fly + impact + draw verified!")
        
    print("\n=== TEST 3: All 11 AoE VFX Classes in Registry ===")
    for cid in ["shaia", "lunaria", "ignis", "astra", "shinobi", "samurai", "fighter", "aurelia", "archer", "zephyr", "boran"]:
        vfx = UltimateAoE_VFX(200, 200, 80, cid)
        assert vfx is not None
        vfx.update(0.05)
        vfx.draw(screen, pygame.math.Vector2(0, 0))
        print(f"  -> AoE VFX for {cid} ({type(vfx).__name__}) verified!")
        
    print("\n=== TEST 4: Co-op Healer / Support Synergies ===")
    # Aurelia + Boran
    aurelia = Player(100, 200, character_id="aurelia")
    boran = Player(150, 200, character_id="boran")
    aurelia.companion = boran
    boran.companion = aurelia
    
    # Damage Boran
    boran.health = 50
    boran.mana = 10
    
    # Aurelia casts [K] (Heal Orb + Dawn Grace)
    aurelia.mana = 100
    aurelia.cast_skill()
    assert boran.health > 50, f"Expected Boran to be healed, got {boran.health}"
    print(f"  -> Aurelia [K] healed Boran: HP now {boran.health}")
    
    # Zephyr + Boran (Ether Stream)
    zephyr = Player(100, 200, character_id="zephyr")
    zephyr.companion = boran
    boran.companion = zephyr
    boran.mana = 10
    zephyr.mana = 100
    zephyr.cast_skill()
    assert boran.mana > 10, f"Expected Boran to receive mana, got {boran.mana}"
    print(f"  -> Zephyr [K] gave mana to Boran: MP now {boran.mana}")
    
    # Aurelia Ultimate (Milagre da Alvorada)
    boran.health = 20
    aurelia.mana = aurelia.max_mana
    aurelia.is_casting_magic = False
    assert aurelia.cast_ultimate()
    # Advance ultimate past climax (0.75s)
    aurelia.ultimate_controller.update(0.80, aurelia, [])
    assert boran.health == boran.max_health, f"Expected Boran to be at 100% HP ({boran.max_health}), got {boran.health}"
    print(f"  -> Aurelia Ultimate restored Boran to 100% HP: {boran.health}/{boran.max_health}")
    
    # Zephyr Ultimate (Convergência de Éter)
    boran.mana = 5
    boran.stamina = 10
    zephyr.mana = zephyr.max_mana
    zephyr.is_casting_magic = False
    assert zephyr.cast_ultimate()
    zephyr.ultimate_controller.update(0.80, zephyr, [])
    assert boran.mana == boran.max_mana, f"Expected Boran to be at 100% MP, got {boran.mana}"
    assert boran.stamina == boran.max_stamina, f"Expected Boran to be at 100% SP, got {boran.stamina}"
    print(f"  -> Zephyr Ultimate restored Boran to 100% MP ({boran.mana}) and 100% SP ({boran.stamina})")
    
    print("\nALL SKILL & CHARACTER TESTS PASSED PERFECTLY!")

if __name__ == "__main__":
    test_all_characters_and_skills()
