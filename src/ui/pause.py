import pygame
import sys
from ui.menu import Menu, MenuOption
from ui.hollow_ui import HollowCrestRenderer, HollowFonts, HollowColors
from engine.input_manager import INPUT
from config.settings import SETTINGS

class PauseMenu:
    """Authentic Hollow Knight style Overlay Pause Menu drawn over active gameplay."""
    def __init__(self, scene_manager, unpause_callback):
        self.scene_manager = scene_manager
        self.unpause_callback = unpause_callback
        
        self.menu = Menu("PAUSA", [
            MenuOption("Continuar", self.unpause_callback),
            MenuOption("Configurações", self.open_settings),
            MenuOption("Menu Principal", self.go_main_menu),
            MenuOption("Sair do Jogo", self.quit_game)
        ])
        
        self.font_hint = HollowFonts.get(10)
        
    def open_settings(self):
        from scenes.settings_menu import SettingsMenuScene
        self.scene_manager.change_scene(SettingsMenuScene(self.scene_manager, self.scene_manager.current_scene))
        
    def go_main_menu(self):
        from scenes.main_menu import MainMenuScene
        self.scene_manager.change_scene(MainMenuScene(self.scene_manager))
        
    def quit_game(self):
        pygame.quit()
        sys.exit()
        
    def update(self, dt: float = 0.016):
        self.menu.handle_input(INPUT)
        
    def draw(self, surface: pygame.Surface):
        gw = surface.get_width()
        gh = surface.get_height()
        cx = gw // 2
        cy = gh // 2
        
        # 1. Dark Vignette Overlay
        overlay = pygame.Surface((gw, gh), pygame.SRCALPHA)
        overlay.fill((6, 7, 10, 205))
        surface.blit(overlay, (0, 0))
        
        # 2. Central Filigree Plaque
        plaque_w = 320
        plaque_h = 240
        plaque_rect = pygame.Rect(cx - plaque_w // 2, cy - plaque_h // 2 - 10, plaque_w, plaque_h)
        HollowCrestRenderer.draw_filigree_panel(surface, plaque_rect, bg_color=(10, 12, 18, 235), border_color=(75, 82, 100), corner_flourish=True)
        
        # 3. Top Flourish, Title & Section Divider
        HollowCrestRenderer.draw_top_flourish(surface, cx, plaque_rect.top + 16, width=120, alpha=210)
        
        from engine.text_cache import get_cached_text
        title_font = HollowFonts.get(18, bold=True)
        title_surf = get_cached_text(title_font, "PAUSA", HollowColors.TEXT_TITLE)
        surface.blit(title_surf, title_surf.get_rect(center=(cx, plaque_rect.top + 34)))
        
        HollowCrestRenderer.draw_section_divider(surface, cx, plaque_rect.top + 52, width=240, alpha=200)
        
        # 4. Hollow Menu Options
        self.menu.draw(surface, cx, plaque_rect.top + 72)
        
        # 5. Bottom Hint
        hint_str = "[W/S] Navegar   •   [ENTER] Confirmar   •   [ESC] Voltar"
        hint_surf = get_cached_text(self.font_hint, hint_str, HollowColors.TEXT_MUTED)
        surface.blit(hint_surf, hint_surf.get_rect(center=(cx, plaque_rect.bottom - 16)))

