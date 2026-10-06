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
        elif self.item_type == "golden_potion":
            potion_path = os.path.join("assets", "sprites", "item", "item_food", "item_potion_red.png")
            if os.path.exists(potion_path):
                raw = pygame.image.load(potion_path).convert_alpha()
                # Tint golden for rejuvenation potion
                tinted = raw.copy()
                tinted.fill((255, 215, 60, 160), special_flags=pygame.BLEND_RGBA_MULT)
                self.image = tinted
            else:
                self.image = pygame.Surface((16, 16))
                self.image.fill((255, 215, 0))
            img_width, img_height = self.image.get_size()
        elif self.item_type in ("potion", "chicken"):
            self.item_type = "potion" # Universal potion standardization
            potion_path = os.path.join("assets", "sprites", "item", "item_food", "item_potion_red.png")
            if os.path.exists(potion_path):
                self.image = pygame.image.load(potion_path).convert_alpha()
            else:
                self.image = pygame.Surface((16, 16))
                self.image.fill((220, 40, 40))
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
            player.inventory['crystals'] = player.inventory.get('crystals', 0) + self.value
            from engine.save_manager import SAVE
            SAVE.add_orbs(self.value)
        elif self.item_type == "potion":
            from engine.save_manager import SAVE
            alchemy_bonus = SAVE.get_skill_level("alchemist_elixir") * 20
            heal_amount = 40 + alchemy_bonus
            if hasattr(player, "start_drinking_potion"):
                player.start_drinking_potion(heal_amount=heal_amount)
            else:
                player.health = min(player.max_health, player.health + heal_amount)
        elif self.item_type == "golden_potion":
            from engine.save_manager import SAVE
            alchemy_bonus = SAVE.get_skill_level("alchemist_elixir") * 20
            heal_amount = 75 + alchemy_bonus
            if hasattr(player, "start_drinking_potion"):
                player.start_drinking_potion(heal_amount=heal_amount)
            else:
                player.health = min(player.max_health, player.health + heal_amount)
            player.stamina = min(getattr(player, "max_stamina", 120.0), player.stamina + 50.0)
            
        self.active = False
        
    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if self.active:
            img = None
            if self.anim_manager:
                img = self.anim_manager.get_current_frame()
            elif self.image:
                img = self.image
                
            if img:
                draw_x = self.rect.centerx - camera_offset.x
                draw_y = self.rect.bottom - camera_offset.y
                
                # Ground contact shadow beneath floating collectible
                shadow_w = 16
                shadow_h = 5
                shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
                pygame.draw.ellipse(shadow_surf, (0, 0, 0, 80), (0, 0, shadow_w, shadow_h))
                ground_y = (self.start_y + self.rect.height + 2) if hasattr(self, "start_y") else self.rect.bottom
                surface.blit(shadow_surf, (draw_x - shadow_w // 2, ground_y - camera_offset.y - shadow_h // 2))
                
                img_rect = img.get_rect(midbottom=(draw_x, draw_y))
                surface.blit(img, img_rect)
