import pygame
from ui.menu import Menu, MenuOption
from engine.input_manager import INPUT
from config.settings import SETTINGS
import sys

class PauseMenu:
    """Overlay Pause Menu drawn over the LevelScene."""
    def __init__(self, scene_manager, unpause_callback):
        self.scene_manager = scene_manager
        self.unpause_callback = unpause_callback
        
        self.menu = Menu("PAUSED", [
            MenuOption("Resume", self.unpause_callback),
            MenuOption("Settings", self.open_settings),
            MenuOption("Main Menu", self.go_main_menu),
            MenuOption("Quit", self.quit_game)
        ])
        
        # Dark overlay
        self.overlay = pygame.Surface((SETTINGS.GAME_WIDTH, SETTINGS.GAME_HEIGHT))
        self.overlay.set_alpha(180)
        self.overlay.fill((0, 0, 0))
        
    def open_settings(self):
        from scenes.settings_menu import SettingsMenuScene
        self.scene_manager.change_scene(SettingsMenuScene(self.scene_manager, self.scene_manager.current_scene))
        
    def go_main_menu(self):
        from scenes.main_menu import MainMenuScene
        self.scene_manager.change_scene(MainMenuScene(self.scene_manager))
        
    def quit_game(self):
        pygame.quit()
        sys.exit()
        
    def update(self):
        self.menu.handle_input(INPUT)
        
    def draw(self, surface: pygame.Surface):
        surface.blit(self.overlay, (0, 0))
        self.menu.draw(surface, SETTINGS.GAME_WIDTH // 2, SETTINGS.GAME_HEIGHT // 2 - 40)
