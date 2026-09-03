import pygame
import os

from engine.animation import load_animation_folder, AnimationManager

class Prop:
    """A static or destructible background/foreground prop."""
    def __init__(self, x: float, y: float, prop_type: str, scale: float = 1.0):
        self.prop_type = prop_type
        self.active = True
        self.anim_manager = None
        self.image = None
        self.scale = scale
        
        if prop_type == "barrel":
            self.image = pygame.image.load(os.path.join("assets", "sprites", "prop", "barrel_001.png")).convert_alpha()
        elif prop_type == "chest":
            self.anim_manager = AnimationManager()
            self.anim_manager.add_animation("open", load_animation_folder(os.path.join("assets", "sprites", "prop"), "chest_open", 10, False, scale))
            self.anim_manager.play("open")
            # Force it to first frame and pause
            self.image = self.anim_manager.animations["open"].frames[0]
            self.opened = False
        elif prop_type == "barricade":
            self.image = pygame.image.load(os.path.join("assets", "sprites", "prop", "baricade_export.png")).convert_alpha()
        elif prop_type == "rock":
            rock_sheet_path = os.path.join("Legacy-Fantasy - High Forest 2.3", "Assets", "Props-Rocks.png")
            if os.path.exists(rock_sheet_path):
                sheet = pygame.image.load(rock_sheet_path).convert_alpha()
                # Natural rounded mossy stone boulder
                sub = sheet.subsurface(pygame.Rect(160, 160, 64, 48)).copy()
                bbox = sub.get_bounding_rect()
                self.image = sub.subsurface(bbox).copy()
            else:
                self.image = pygame.Surface((32, 32))
        else:
            self.image = pygame.Surface((32, 32))
            
        if scale != 1.0 and self.image:
            self.image = pygame.transform.scale(self.image, (int(self.image.get_width() * scale), int(self.image.get_height() * scale)))
            
        # We align the prop so its bottom sits on the provided Y
        self.rect = self.image.get_frect(midbottom=(x, y))
        
    def update(self, dt: float, player, spawn_collectible_callback):
        if not self.active: return
        
        if self.prop_type == "chest":
            if self.opened:
                self.anim_manager.update(dt)
            elif self.rect.colliderect(player.rect):
                # Open chest on touch!
                self.opened = True
                spawn_collectible_callback(self.rect.centerx, self.rect.bottom)
                
        if self.prop_type == "barricade":
            # Barricade acts as a trap that damages player (smaller hitbox so player has to get close)
            if self.rect.inflate(-25, -25).colliderect(player.rect):
                player.take_damage(1)
                
    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if not self.active: return
        draw_x = self.rect.x - camera_offset.x
        draw_y = self.rect.y - camera_offset.y
        
        if self.prop_type == "chest" and self.opened:
            img = self.anim_manager.get_current_frame()
            if img:
                surface.blit(img, (draw_x, draw_y))
        elif self.image:
            if self.prop_type == "rock":
                # Draw subtle soft ground shadow
                shadow_w = int(self.rect.width * 0.9)
                shadow_h = 8
                shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
                pygame.draw.ellipse(shadow_surf, (0, 0, 0, 90), (0, 0, shadow_w, shadow_h))
                surface.blit(shadow_surf, (draw_x + (self.rect.width - shadow_w)//2, draw_y + self.rect.height - 4))
                
            surface.blit(self.image, (draw_x, draw_y))
