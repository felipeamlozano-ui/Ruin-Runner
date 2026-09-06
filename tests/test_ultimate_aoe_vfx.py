"""
Unit and Integration Test Suite for the Polymorphic UltimateAoE_VFX System.
Validates all 7 character VFX archetypes, color clamping safety, animation
progression, and Pygame surface rendering.
"""

import sys
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.abspath("src"))
sys.path.insert(0, os.path.abspath("."))

import pygame
pygame.init()
pygame.display.set_mode((800, 600))

from entities.ultimate_aoe_vfx import (
    clamp_color,
    lerp,
    lerp_color,
    ease_out_expo,
    ease_out_back,
    ease_in_quad,
    UltimateAoE_VFX,
    BaseUltimateAoE_VFX,
    IgnisVolcanicEruptionVFX,
    LunariaSingularityVFX,
    AstraShardBlizzardVFX,
    RyuuKiDomainVFX,
    SamuraiJudgementCutVFX,
    ShinobiShadowDanceVFX,
    ShaiaDivineJudgementVFX,
)
from entities.character_data import CHARACTER_ORDER
from entities.player import Player


def test_clamp_color_safety():
    """Validates that clamp_color strictly forces all RGB and RGBA channels into [0, 255]."""
    # Overflows and negatives
    raw_rgb = (-50.4, 300.9, 128.0)
    clamped_rgb = clamp_color(raw_rgb)
    assert clamped_rgb == (0, 255, 128)
    assert all(isinstance(c, int) for c in clamped_rgb)
    
    # 4-channel RGBA
    raw_rgba = (999.0, -100.0, 255.4, 312.8)
    clamped_rgba = clamp_color(raw_rgba)
    assert clamped_rgba == (255, 0, 255, 255)
    
    # Interpolation with clamp
    interp = lerp_color((0, 0, 0, 0), (300, -50, 200, 400), 0.5)
    assert interp == (150, 0, 100, 200)


def test_polymorphic_subclass_dispatch():
    """Validates that UltimateAoE_VFX factory instantiates the correct subclass for every hero."""
    expected_classes = {
        "ignis": IgnisVolcanicEruptionVFX,
        "lunaria": LunariaSingularityVFX,
        "astra": AstraShardBlizzardVFX,
        "fighter": RyuuKiDomainVFX,
        "ryuu": RyuuKiDomainVFX,
        "samurai": SamuraiJudgementCutVFX,
        "shinobi": ShinobiShadowDanceVFX,
        "shaia": ShaiaDivineJudgementVFX,
    }
    
    for cid, expected_cls in expected_classes.items():
        vfx = UltimateAoE_VFX(200.0, 300.0, 150.0, cid)
        assert isinstance(vfx, expected_cls), f"Expected {cid} to dispatch to {expected_cls.__name__}"
        assert isinstance(vfx, BaseUltimateAoE_VFX), "Must inherit from BaseUltimateAoE_VFX"
        assert isinstance(vfx, UltimateAoE_VFX), "Must be an instance of UltimateAoE_VFX"
        assert vfx.active is True
        assert vfx.radius == 150.0
        assert vfx.duration > 0.5


def test_full_vfx_simulation_and_render_all_heroes():
    """Runs a 60-frame update and render simulation on a real Pygame surface for all 7 archetypes."""
    test_surface = pygame.Surface((800, 600), pygame.SRCALPHA)
    cam_offset = pygame.math.Vector2(50.0, 100.0)
    dt = 0.016  # 60 FPS delta time
    
    for cid in CHARACTER_ORDER:
        vfx = UltimateAoE_VFX(400.0, 300.0, 160.0, cid)
        total_time = 0.0
        frames_rendered = 0
        
        while vfx.active and total_time < 2.0:
            vfx.update(dt)
            vfx.draw(test_surface, cam_offset)
            total_time += dt
            frames_rendered += 1
            
        assert not vfx.active, f"VFX for {cid} should have expired within its duration!"
        assert frames_rendered >= 30, f"VFX for {cid} terminated prematurely: {frames_rendered} frames"
        print(f"Verified {cid} VFX: {frames_rendered} frames simulated successfully.")


def test_player_integration_aoe_visuals():
    """Validates that Player entity correctly executes UltimateAoE_VFX when casting AoE."""
    test_surface = pygame.Surface((800, 600), pygame.SRCALPHA)
    cam_offset = pygame.math.Vector2(0.0, 0.0)
    
    for cid in CHARACTER_ORDER:
        player = Player(200.0, 300.0, character_id=cid)
        player.is_casting_aoe = True
        player.aoe_timer = 0.85
        
        # Simulate 10 frames of player updating and drawing
        for _ in range(10):
            player.update(0.016, [])
            player.draw(test_surface, cam_offset)

            
        assert player.aoe_vfx is not None, f"Player {cid} should have instantiated aoe_vfx"
        assert player.aoe_vfx.active is True, f"Player {cid} aoe_vfx should be active"
        print(f"Verified Player [{cid}] AoE skill execution.")


if __name__ == "__main__":
    print("=== Running UltimateAoE_VFX Comprehensive Test Suite ===")
    test_clamp_color_safety()
    print("[OK] Color Clamping Safety verified!")
    test_polymorphic_subclass_dispatch()
    print("[OK] Polymorphic Subclass Dispatch verified for all archetypes!")
    test_full_vfx_simulation_and_render_all_heroes()
    print("[OK] Full 60-FPS VFX simulation & surface render verified for all 7 heroes!")
    test_player_integration_aoe_visuals()
    print("[OK] Player integration verified across all 7 heroes!")
    print("\nALL ULTIMATE AoE VFX TESTS PASSED!")
