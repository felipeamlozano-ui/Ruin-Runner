"""
Automated Test Suite for Ruin Runner AAA Expansion:
- SaveManager & Orb Economy
- Clouds Atmospheric System (craftpix-801184)
- Rock Props & Biome Platforms (craftpix-675652)
- Interactive Keyboard Overlay & Tutorial Scene (craftpix-726651)
- Magic Book Skill Tree & Upgrades (craftpix-809047)
- 4K Parallax StageManager & Dual-Slice 60 FPS Engine
- ScoreSystem & Letter Ranks
- Deep-Fold PixelPlanetRenderer (3D rotating planets)
- Tabbed AAA Settings Menu
- Emote-Free verification
"""

import os
import sys
import pygame

# Set up paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_save_manager_and_orbs():
    from engine.save_manager import SaveManager
    test_file = "test_save_data.json"
    if os.path.exists(test_file):
        os.remove(test_file)
        
    sm = SaveManager(filepath=test_file)
    assert sm.get_orbs() >= 100
    
    # Add orbs
    sm.add_orbs(50)
    assert sm.get_orbs() == 170
    
    # Spend orbs
    assert sm.spend_orbs(30) is True
    assert sm.get_orbs() == 140
    assert sm.spend_orbs(9999) is False
    
    # Skills
    sm.set_skill_level("blade_sharpness", 2)
    assert sm.get_skill_level("blade_sharpness") == 2
    
    # Tutorial
    assert sm.is_tutorial_completed() is False
    sm.set_tutorial_completed(True)
    assert sm.is_tutorial_completed() is True
    
    # Clean up
    if os.path.exists(test_file):
        os.remove(test_file)

def test_clouds_manager():
    from engine.v3.weather.clouds import CloudsManager
    cm = CloudsManager(theme="white", map_width=1280, cloud_count=6)
    assert len(cm.clouds) > 0
    
    surf = pygame.Surface((640, 480))
    cm.update(0.016, wind=20.0)
    cm.draw(surf, (0, 0), 640, 480)

def test_rock_props():
    from entities.rock_obstacle import RockProp
    for biome in ["road", "cave", "canyon", "ice", "stalagmite"]:
        rock = RockProp(100, 300, biome=biome, variant=1, scale=1.0)
        assert rock.image is not None
        assert rock.rect.width > 0
        
        surf = pygame.Surface((640, 480))
        rock.draw(surf, (0, 0))

def test_keyboard_overlay_and_tutorial():
    from ui.keyboard_overlay import KeyboardOverlay
    from scenes.tutorial_scene import TutorialScene
    from engine.scene_manager import SceneManager
    
    overlay = KeyboardOverlay()
    surf = pygame.Surface((640, 480))
    overlay.update(0.016)
    skip_rect = overlay.draw_hud(surf, {"A", "D", "SPACE", "J"}, "TEST TASK", "Test Desc", 1, 8)
    assert skip_rect.width > 0
    
    sm = SceneManager()
    tut = TutorialScene(sm, character="knight")
    assert tut.step == 1
    tut.update(0.016)
    tut.draw(surf)

def test_magic_book_scene():
    from scenes.magic_book_scene import MagicBookScene
    from engine.scene_manager import SceneManager
    from engine.save_manager import SAVE
    
    SAVE.add_orbs(100)
    sm = SceneManager()
    mb = MagicBookScene(sm)
    assert mb.book_surf is not None
    assert len(mb.icon_surfs) > 0
    
    surf = pygame.Surface((640, 480))
    mb.update(0.016)
    mb.draw(surf)
    
    # Flip pages
    mb._change_page(1)
    assert mb.page_index == 1
    mb._change_page(-1)
    assert mb.page_index == 0

def test_stage_manager_and_parallax():
    from engine.stage_manager import STAGE_MGR, STAGE_CATALOG
    assert len(STAGE_CATALOG) >= 8
    
    # Test loading RPG stage and Vampire stage
    cfg_rpg = STAGE_MGR.load_stage("terrae_1")
    assert cfg_rpg is not None
    assert STAGE_MGR.parallax_renderer is not None
    assert len(STAGE_MGR.parallax_renderer.layers) > 0
    
    surf = pygame.Surface((640, 480))
    STAGE_MGR.parallax_renderer.draw(surf, cam_x=120)
    
    cfg_vamp = STAGE_MGR.load_stage("sanguis_1")
    assert cfg_vamp is not None
    assert len(STAGE_MGR.parallax_renderer.layers) > 0
    STAGE_MGR.parallax_renderer.draw(surf, cam_x=250)

def test_score_system():
    from engine.score_system import ScoreSystem
    ss = ScoreSystem("test_stage")
    ss.add_hit()
    assert ss.combo_count == 1
    assert ss.combo_multiplier == 1.1
    
    ss.add_kill("mage")
    assert ss.score > 0
    assert ss.enemies_defeated == 1
    
    final = ss.calculate_final_score()
    assert final["rank"] in ["S", "A", "B", "C", "D"]
    assert final["total_score"] >= ss.score

def test_pixel_planet_renderer():
    from engine.v3.planets.planet_renderer import PixelPlanetRenderer
    pp = PixelPlanetRenderer("terrae", radius=24, target_size=96)
    assert len(pp.frames) == 24
    
    surf = pygame.Surface((640, 480))
    pp.update(0.016)
    pp.draw(surf, (320, 240))

def test_settings_menu_tabs():
    from scenes.settings_menu import SettingsMenuScene
    from engine.scene_manager import SceneManager
    
    sm = SceneManager()
    menu = SettingsMenuScene(sm, previous_scene=None)
    assert len(menu.TABS) == 4
    
    surf = pygame.Surface((640, 480))
    menu.draw(surf)
    
    # Switch tab
    menu.active_tab = 1
    menu.draw(surf)

def test_no_emotes_present():
    """Verify that no emote systems or actions exist in the active codebase."""
    from config.controls import InputAction
    action_names = [a.value.lower() for a in InputAction]
    assert "emote" not in action_names

if __name__ == "__main__":
    pygame.init()
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.display.set_mode((640, 480), pygame.NOFRAME)
    test_funcs = [
        test_save_manager_and_orbs,
        test_clouds_manager,
        test_rock_props,
        test_keyboard_overlay_and_tutorial,
        test_magic_book_scene,
        test_stage_manager_and_parallax,
        test_score_system,
        test_pixel_planet_renderer,
        test_settings_menu_tabs,
        test_no_emotes_present
    ]
    print(f"=== RUNNING {len(test_funcs)} TEST CASES FOR NEW SYSTEMS ===")
    all_passed = True
    for fn in test_funcs:
        try:
            fn()
            print(f"[PASS] {fn.__name__}")
        except Exception as e:
            print(f"[FAIL] {fn.__name__}: {e}")
            import traceback
            traceback.print_exc()
            all_passed = False
            
    if all_passed:
        print("\nALL 10 TEST SUITES PASSED 100%!")
        sys.exit(0)
    else:
        print("\nSOME TESTS FAILED.")
        sys.exit(1)
