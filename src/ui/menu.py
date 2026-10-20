import math
import pygame
from typing import List, Callable
from ui.hollow_ui import HollowFonts, HollowCrestRenderer

class MenuOption:
    def __init__(self, text: str, on_select: Callable):
        self.text = text
        self.on_select = on_select

class Menu:
    """Navigable menu component redesigned in the elegant Hollow Knight aesthetic."""
    
    def __init__(self, title: str, options: List[MenuOption]):
        self.title = title
        self.options = options
        self.selected_index = 0
        self._time = 0.0
        
    def handle_input(self, input_manager) -> bool:
        """Returns True if the menu consumed the input."""
        self._time += 0.016
        
        # Navigation
        if input_manager.is_action_just_pressed("UP") or (hasattr(input_manager, "is_key_just_pressed") and input_manager.is_key_just_pressed(pygame.K_w)):
            self.selected_index = (self.selected_index - 1) % len(self.options)
            return True
        elif input_manager.is_action_just_pressed("DOWN") or (hasattr(input_manager, "is_key_just_pressed") and input_manager.is_key_just_pressed(pygame.K_s)):
            self.selected_index = (self.selected_index + 1) % len(self.options)
            return True
        elif (input_manager.is_action_just_pressed("JUMP") 
              or input_manager.is_action_just_pressed("ACTION")
              or input_manager.is_action_just_pressed("ATTACK")):
            if 0 <= self.selected_index < len(self.options):
                self.options[self.selected_index].on_select()
                return True
        return False
            
    def draw(self, surface: pygame.Surface, x: int, y: int):
        self._time += 0.016
        num_opts = len(self.options)
        
        # Adaptive font sizing and vertical spacing
        if num_opts > 7:
            font = HollowFonts.get(13)
            spacing = 22
            start_y = y
        else:
            font = HollowFonts.get(15)
            spacing = 28
            start_y = y
            
        pulse = 0.85 + 0.15 * math.sin(self._time * 5.0)
        marker_alpha = int(220 * pulse)
        
        for i, option in enumerate(self.options):
            is_sel = (i == self.selected_index)
            cur_y = start_y + (i * spacing)
            
            # Text rendering
            col = (255, 255, 255) if is_sel else (145, 155, 175)
            from engine.text_cache import get_cached_text
            shadow_surf = get_cached_text(font, option.text, (0, 0, 0))
            opt_surf = get_cached_text(font, option.text, col)
            
            opt_w = opt_surf.get_width()
            opt_x = x - opt_w // 2
            
            surface.blit(shadow_surf, (opt_x + 1, cur_y + 1))
            surface.blit(opt_surf, (opt_x, cur_y))
            
            # Hollow Knight selection marker wings flanking the active item
            if is_sel:
                marker_size = 5.5
                HollowCrestRenderer.draw_selection_marker(
                    surface, opt_x - 18, cur_y + opt_surf.get_height() // 2,
                    size=marker_size, is_right=False, alpha=marker_alpha
                )
                HollowCrestRenderer.draw_selection_marker(
                    surface, opt_x + opt_w + 18, cur_y + opt_surf.get_height() // 2,
                    size=marker_size, is_right=True, alpha=marker_alpha
                )
