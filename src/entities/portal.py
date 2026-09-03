import pygame
import math
import os
from engine.animation import AnimationManager, load_animation_folder

class Portal:
    def __init__(self, x: float, y: float):
        self.rect = pygame.FRect(x, y, 32, 64)
        self.active = True
        
        # We can use orb cure animation or something to look like a portal
        self.anim_manager = AnimationManager()
        self.anim_manager.add_animation("idle", load_animation_folder(os.path.join("assets", "sprites", "vfx", "vfx_twinkle"), "vfx_twinkle", 15, True, 2.0))
        self.anim_manager.play("idle")
        
    def update(self, dt: float):
        if self.active:
            self.anim_manager.update(dt)
            
    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if self.active:
            draw_x = self.rect.centerx - camera_offset.x
            draw_y = self.rect.centery - camera_offset.y
            img = self.anim_manager.get_current_frame()
            if img:
                img_rect = img.get_rect(center=(draw_x, draw_y))
                surface.blit(img, img_rect)
