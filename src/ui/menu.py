import pygame
from typing import List, Callable
from config.colors import UI_TEXT, UI_HIGHLIGHT, BLACK
from config.settings import SETTINGS

class MenuOption:
    def __init__(self, text: str, on_select: Callable):
        self.text = text
        self.on_select = on_select

class Menu:
    """Base class for navigable menus (Main Menu, Pause, Settings)."""
    
    def __init__(self, title: str, options: List[MenuOption]):
        self.title = title
        self.options = options
        self.selected_index = 0
        self.font_title = pygame.font.Font(None, 48)
        self.font_option = pygame.font.Font(None, 32)
        
    def handle_input(self, input_manager) -> bool:
        """Returns True if the menu consumed the input."""
        if input_manager.is_action_just_pressed("UP"):
            self.selected_index = (self.selected_index - 1) % len(self.options)
            return True
        elif input_manager.is_action_just_pressed("DOWN"):
            self.selected_index = (self.selected_index + 1) % len(self.options)
            return True
        elif input_manager.is_action_just_pressed("JUMP") or input_manager.is_action_just_pressed("ACTION"):
            self.options[self.selected_index].on_select()
            return True
        return False
            
    def draw(self, surface: pygame.Surface, x: int, y: int):
        # Draw Title
        title_surf = self.font_title.render(self.title, True, UI_TEXT)
        title_rect = title_surf.get_rect(center=(x, y))
        
        # Outline for PS1 retro text style
        pygame.draw.rect(surface, BLACK, title_rect.inflate(4, 4))
        surface.blit(title_surf, title_rect)
        
        # Draw Options
        start_y = y + 50
        for i, option in enumerate(self.options):
            color = UI_HIGHLIGHT if i == self.selected_index else UI_TEXT
            prefix = "> " if i == self.selected_index else "  "
            opt_surf = self.font_option.render(f"{prefix}{option.text}", True, color)
            opt_rect = opt_surf.get_rect(center=(x, start_y + (i * 30)))
            
            # Simple shadow/outline
            shadow = self.font_option.render(f"{prefix}{option.text}", True, BLACK)
            surface.blit(shadow, (opt_rect.x + 2, opt_rect.y + 2))
            
            surface.blit(opt_surf, opt_rect)
