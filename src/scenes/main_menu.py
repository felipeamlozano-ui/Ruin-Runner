"""
Ruin Engine — Hollow Knight Aesthetic Main Menu Scene.
Atmospheric void mist, procedural crests, classic serif typography, and elegant selection markers.
"""

import math
import sys
import pygame
from engine.scene_manager import Scene
from ui.menu import Menu, MenuOption
from engine.input_manager import INPUT
from engine.save_manager import SAVE
from config.settings import SETTINGS
from ui.hollow_ui import AtmosphereFX, HollowCrestRenderer, HollowText, HollowFonts

class MainMenuScene(Scene):
    """Grand Gothic Main Menu inspired by Hollow Knight."""
    
    internal_size = (640, 360)
    
    def __init__(self, scene_manager):
        self.scene_manager = scene_manager
        
        self.width = 640
        self.height = 360
        
        # Atmospheric Void Mist & Particles
        self.atmosphere = AtmosphereFX(self.width, self.height, theme="void", particle_count=48)
        
        self.menu = Menu("RUIN RUNNER", [
            MenuOption("INICIAR CAMPANHA", self.open_story_mode),
            MenuOption("MODO COOPERATIVO", self.open_coop_mode),
            MenuOption("CONFRONTO DE CHEFES", self.open_boss_battle),
            MenuOption("MODO ARCADE", self.start_game),
            MenuOption("SANTUÁRIO DO TUTORIAL", self.open_tutorial),
            MenuOption("GRIMOIRE DE HABILIDADES", self.open_magic_book),
            MenuOption("SELEÇÃO DE HERÓIS", self.open_character_select),
            MenuOption("CONFIGURAÇÕES", self.open_settings),
            MenuOption("SAIR DO JOGO", self.quit_game)
        ])
        
        self.time_sec = 0.0

    def open_story_mode(self):
        SETTINGS.COOP_ENABLED = False
        from scenes.story_select_scene import StorySelectScene
        self.scene_manager.change_scene(StorySelectScene(self.scene_manager))

    def open_coop_mode(self):
        SETTINGS.COOP_ENABLED = True
        from scenes.character_select_scene import CharacterSelectScene
        self.scene_manager.change_scene(CharacterSelectScene(self.scene_manager, self))

    def open_boss_battle(self):
        SETTINGS.COOP_ENABLED = False
        from scenes.boss_select_scene import BossSelectScene
        self.scene_manager.change_scene(BossSelectScene(self.scene_manager, return_scene=self))

    def open_tutorial(self):
        SETTINGS.COOP_ENABLED = False
        from scenes.tutorial_scene import TutorialScene
        char = getattr(SETTINGS, "CURRENT_CHARACTER", "knight")
        self.scene_manager.change_scene(TutorialScene(self.scene_manager, character=char))

    def open_magic_book(self):
        from scenes.magic_book_scene import MagicBookScene
        self.scene_manager.change_scene(MagicBookScene(self.scene_manager, return_scene=self))

    def start_game(self):
        SETTINGS.COOP_ENABLED = False
        from scenes.loading_scene import LoadingScene
        if SETTINGS.DEV_MODE and SETTINGS.DEV_START_BOSS:
            from scenes.boss_scene import BossScene
            boss_scene = BossScene(self.scene_manager)
            loading = LoadingScene(
                self.scene_manager,
                boss_scene,
                title="SALA DO BOSS: O REI ESQUELETO",
                tip="Modo Dev Ativo: Iniciando confronto diretamente na sala do Boss!"
            )
            self.scene_manager.change_scene(loading)
        else:
            from scenes.level_scene import LevelScene
            lvl1 = LevelScene(stage=1, scene_manager=self.scene_manager)
            loading = LoadingScene(
                self.scene_manager,
                lvl1,
                title="FASE 1: AS CATACUMBAS",
                tip="Dica: Use [Shift] para esquivar ou defender e [1] para poções!"
            )
            self.scene_manager.change_scene(loading)
        
    def open_character_select(self):
        SETTINGS.COOP_ENABLED = False
        from scenes.character_select_scene import CharacterSelectScene
        self.scene_manager.change_scene(CharacterSelectScene(self.scene_manager, self))
        
    def open_settings(self):
        from scenes.settings_menu import SettingsMenuScene
        self.scene_manager.change_scene(SettingsMenuScene(self.scene_manager, self))
        
    def quit_game(self):
        pygame.quit()
        sys.exit()

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        pass
        
    def update(self, dt: float) -> None:
        self.time_sec += dt
        self.atmosphere.update(dt)
        self.menu.handle_input(INPUT)
        
    def draw(self, surface: pygame.Surface) -> None:
        sw, sh = surface.get_size()
        cx = sw // 2
        
        # 1. Dark Void Atmosphere Background with Floating Spores
        self.atmosphere.draw_background(surface, show_rays=False)
        
        # 2. Top Delicate Flourish
        HollowCrestRenderer.draw_top_flourish(surface, cx, 16, width=140)
        
        # 3. Grand Hollow Knight Luminous Title
        HollowText.render_title_with_glow(surface, "RUIN RUNNER", cx, 40, size=28, letter_spacing=5)
        
        # 4. Master Under-Title Baroque Crest
        HollowCrestRenderer.draw_master_title_crest(surface, cx, 68, width=260)
        
        # 5. Top Left Soul Orbs Indicator (clean & discrete)
        orbs_count = SAVE.get_orbs()
        f_orbs = HollowFonts.get(11)
        orbs_surf = f_orbs.render(f"ORBES: {orbs_count}", True, (170, 205, 240))
        surface.blit(orbs_surf, (22, 14))
        
        # Dev Mode Badge (if active)
        if SETTINGS.DEV_MODE:
            f_dev = HollowFonts.get(10, italic=True)
            d_surf = f_dev.render("[MODO DEV: BOSS RUSH ATIVO]", True, (245, 150, 75))
            surface.blit(d_surf, d_surf.get_rect(center=(cx, 88)))
        
        # 6. Central Menu Options Deck
        self.menu.draw(surface, cx, 114)
        
        # 7. Discrete Hollow Knight Footer
        f_footer = HollowFonts.get(9)
        v_surf = f_footer.render("v3.2.0 • RUIN RUNNER", True, (80, 90, 110))
        surface.blit(v_surf, (22, sh - 18))
        
        hint_surf = f_footer.render("[↑/↓ NAVEGAR]   [ENTER/Z CONFIRMAR]", True, (95, 105, 125))
        surface.blit(hint_surf, hint_surf.get_rect(center=(cx, sh - 18)))
        
        c_surf = f_footer.render("TEAM RUIN", True, (80, 90, 110))
        surface.blit(c_surf, (sw - c_surf.get_width() - 22, sh - 18))
