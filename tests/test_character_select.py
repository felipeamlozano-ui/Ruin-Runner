import os
import sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.abspath("src"))
sys.path.insert(0, os.path.abspath("."))

import pygame
pygame.init()
pygame.display.set_mode((512, 384))

from scenes.character_select_scene import CharacterSelectScene, CHARACTER_ORDER
from entities.character_data import CHARACTER_REGISTRY

from engine.scene_manager import SceneManager

def test_character_select_all_profiles():
    print("Testing CharacterSelectScene across all 7 heroes...")
    sm = SceneManager()
    scene = CharacterSelectScene(sm)
    surface = pygame.Surface((512, 384))
    
    assert len(CHARACTER_ORDER) >= 7, f"Expected at least 7 characters, got {len(CHARACTER_ORDER)}"
    
    for idx, cid in enumerate(CHARACTER_ORDER):
        scene._select_character(idx)
        prof = scene.profile
        
        # Verify asymmetric status
        assert prof.hp_max > 0, f"{cid} HP max must be positive, got {prof.hp_max}"
        assert prof.mp_max > 0, f"{cid} MP max must be positive, got {prof.mp_max}"
        assert prof.sp_max > 0, f"{cid} SP max must be positive, got {prof.sp_max}"
            
        # Verify passive info
        assert prof.passive_name != "", f"{cid} missing passive name"
        assert prof.passive_desc != "", f"{cid} missing passive description"
        
        # Test update and draw
        scene.update(0.016)
        scene.draw(surface)
        
        # Test Dojo actions
        for key in ["j", "k", "e", "shift", "q", "r", "space"]:
            scene._trigger_dojo_move(key)
            scene.update(0.016)
            scene.draw(surface)
            
        print(f"  -> [OK] Hero {idx + 1}/7: {prof.name} ({prof.title}) - Passive: {prof.passive_name}")
        
    print("All CharacterSelectScene tests passed successfully!")

if __name__ == "__main__":
    test_character_select_all_profiles()
