import pygame
import os
import math
from engine.animation import load_animation_folder, AnimationManager

import random

class Collectible:
    """Base class for items that can be picked up."""
    def __init__(self, x: float, y: float, item_type: str, value: int = 1, is_dropped: bool = False):
        self.item_type = item_type
        self.value = value
        self.rect = pygame.FRect(x, y, 16, 16)
        self.active = True
        
        self.anim_manager = None
        self.image = None
        
        # Determine image/animation
        if self.item_type == "orb":
            self.anim_manager = AnimationManager()
            self.anim_manager.add_animation("spin", load_animation_folder(os.path.join("assets", "sprites", "item", "item_orb"), "item_orb_cure", 15, True, 1.0))
            self.anim_manager.play("spin")
            img_width, img_height = self.anim_manager.get_current_frame().get_size()
        elif self.item_type == "chicken":
            original_img = pygame.image.load(os.path.join("assets", "sprites", "item", "item_food", "item_chicken.png")).convert_alpha()
            # Hitbox do frango igual a da poção, conforme pedido!
            potion_img = pygame.image.load(os.path.join("assets", "sprites", "item", "item_food", "item_potion_red.png"))
            img_width, img_height = potion_img.get_size()
            
            # Diminui visualmente o tamanho da imagem também para caber no novo padrão
            self.image = pygame.transform.scale(original_img, (img_width, img_height))
        elif self.item_type == "potion":
            self.image = pygame.image.load(os.path.join("assets", "sprites", "item", "item_food", "item_potion_red.png")).convert_alpha()
            img_width, img_height = self.image.get_size()
        else:
            self.image = pygame.Surface((16, 16))
            self.image.fill((255, 255, 0))
            img_width, img_height = 16, 16
            
        self.rect = pygame.FRect(x - img_width/2, y - img_height, img_width, img_height)
        self.start_y = self.rect.y
        self.time = 0.0
        
        # Falling & Bouncing Physics Animation for boss drops
        self.is_dropped = is_dropped
        if is_dropped:
            self.velocity_x = random.uniform(-110.0, 110.0)
            self.velocity_y = -260.0 # Tossed upwards out of the boss
            self.target_ground_y = 340.0
            self.bounces = 0
            self.falling = True
        else:
            self.falling = False
            self.velocity_x = 0.0
            self.velocity_y = 0.0
            
    def update(self, dt: float):
        if not self.active: return
        
        if self.anim_manager:
            self.anim_manager.update(dt)
            
        if self.falling:
            self.velocity_y += 750 * dt
            self.rect.x += self.velocity_x * dt
            self.rect.y += self.velocity_y * dt
            
            if self.rect.bottom >= self.target_ground_y:
                self.rect.bottom = self.target_ground_y
                self.bounces += 1
                if self.bounces < 3:
                    # Bouncy landing!
                    self.velocity_y = -abs(self.velocity_y) * 0.45
                    self.velocity_x *= 0.5
                else:
                    self.falling = False
                    self.start_y = self.rect.y
        else:
            # Floating hover effect once settled
            self.time += dt * 4
            self.rect.y = self.start_y + math.sin(self.time) * 3
        
    def collect(self, player):
        if not self.active: return
        
        if self.item_type == "orb":
            player.inventory['crystals'] += self.value
            print(f"Got Orb! Total: {player.inventory['crystals']}")
        elif self.item_type == "potion":
            player.health = player.max_health # Heals to full 20 HP!
            print(f"Full Heal ({int(player.max_health)} HP)!")
        elif self.item_type == "chicken":
            player.health = player.max_health # Heals to full 20 HP!
            player.stamina = 100.0
            print("Full Heal + Full Stamina!")
            
        self.active = False
        
    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if self.active:
            img = None
            if self.anim_manager:
                img = self.anim_manager.get_current_frame()
            elif self.image:
                img = self.image
                
            if img:
                # Centraliza a imagem desenhada com a hitbox para evitar desalinhamento visual
                draw_x = self.rect.centerx - camera_offset.x
                draw_y = self.rect.bottom - camera_offset.y
                img_rect = img.get_rect(midbottom=(draw_x, draw_y))
                surface.blit(img, img_rect)
