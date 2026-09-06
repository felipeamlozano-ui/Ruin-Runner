import pygame
import os
import random
import math

from engine.animation import load_animation_folder, AnimationManager, Animation

class WoodParticle:
    """Lightweight physics-driven wood splinter particle."""
    __slots__ = ("x", "y", "vx", "vy", "gravity", "life", "max_life", "size", "color")
    def __init__(self, x: float, y: float, vx: float, vy: float, color: tuple, size: float = 3.0):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.gravity = 500.0
        self.life = self.max_life = random.uniform(0.35, 0.7)
        self.size = size
        self.color = color

    def update(self, dt: float) -> bool:
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        t = max(0.0, self.life / self.max_life)
        alpha = int(255 * t)
        s = pygame.Surface((int(self.size * 2), int(self.size * 2)), pygame.SRCALPHA)
        pygame.draw.rect(s, (*self.color, alpha), (0, 0, int(self.size * 2), int(self.size)))
        surface.blit(s, (self.x - cam_x - self.size, self.y - cam_y - self.size))

class Prop:
    """A static or destructible background/foreground prop."""
    def __init__(self, x: float, y: float, prop_type: str, scale: float = 1.0):
        self.prop_type = prop_type
        self.active = True
        self.anim_manager = None
        self.image = None
        self.scale = scale
        self.health = 2 if prop_type == "barrel" else 1
        self.is_broken = False
        self.debris_anim = None
        self.particles: list[WoodParticle] = []
        self.barricade_damage_cooldown = 0.0
        
        prop_dir = os.path.join("assets", "sprites", "prop")
        
        if prop_type == "barrel":
            self.img_intact = pygame.image.load(os.path.join(prop_dir, "barrel_001.png")).convert_alpha()
            self.img_damaged = pygame.image.load(os.path.join(prop_dir, "barrel_002.png")).convert_alpha()
            brk1 = pygame.image.load(os.path.join(prop_dir, "barrel_break01.png")).convert_alpha()
            brk2 = pygame.image.load(os.path.join(prop_dir, "barrel_break02.png")).convert_alpha()
            
            if scale != 1.0:
                w, h = int(self.img_intact.get_width() * scale), int(self.img_intact.get_height() * scale)
                self.img_intact = pygame.transform.scale(self.img_intact, (w, h))
                self.img_damaged = pygame.transform.scale(self.img_damaged, (w, h))
                brk1 = pygame.transform.scale(brk1, (int(brk1.get_width() * scale), int(brk1.get_height() * scale)))
                brk2 = pygame.transform.scale(brk2, (int(brk2.get_width() * scale), int(brk2.get_height() * scale)))
                
            self.image = self.img_intact
            
            # Breaking animation frames
            self.anim_manager = AnimationManager()
            self.anim_manager.add_animation("break", Animation([brk1, brk2], fps=8, loop=False))
            
            # Debris wood VFX
            debris_path = os.path.join("assets", "sprites", "vfx", "vfx_debris_wood")
            if os.path.exists(debris_path):
                self.debris_anim = load_animation_folder(debris_path, "vfx_debris_wood", fps=18, loop=False, scale=scale * 1.3)
                
        elif prop_type == "chest":
            self.anim_manager = AnimationManager()
            self.anim_manager.add_animation("open", load_animation_folder(prop_dir, "chest_open", 10, False, scale))
            self.anim_manager.play("open")
            self.image = self.anim_manager.animations["open"].frames[0]
            self.opened = False
        elif prop_type == "barricade":
            bar_path = os.path.join(prop_dir, "baricade_export.png")
            if os.path.exists(bar_path):
                self.image = pygame.image.load(bar_path).convert_alpha()
            else:
                self.image = pygame.Surface((32, 32))
            if scale != 1.0 and self.image:
                self.image = pygame.transform.scale(self.image, (int(self.image.get_width() * scale), int(self.image.get_height() * scale)))
        elif prop_type == "rock":
            rock_sheet_path = os.path.join("Legacy-Fantasy - High Forest 2.3", "Assets", "Props-Rocks.png")
            if os.path.exists(rock_sheet_path):
                sheet = pygame.image.load(rock_sheet_path).convert_alpha()
                sub = sheet.subsurface(pygame.Rect(160, 160, 64, 48)).copy()
                bbox = sub.get_bounding_rect()
                self.image = sub.subsurface(bbox).copy()
            else:
                self.image = pygame.Surface((32, 32))
            if scale != 1.0 and self.image:
                self.image = pygame.transform.scale(self.image, (int(self.image.get_width() * scale), int(self.image.get_height() * scale)))
        else:
            self.image = pygame.Surface((32, 32))
            
        self.rect = self.image.get_frect(midbottom=(x, y))
        
    def take_damage(self, amount: int = 1, is_skill: bool = False, spawn_collectible_callback = None) -> bool:
        """Applies damage to destructible props. Returns True if destroyed."""
        if not self.active or self.is_broken or self.prop_type != "barrel":
            return False
            
        if is_skill or amount >= 10:
            self.health = 0
        else:
            self.health -= 1
            
        cx, cy = self.rect.centerx, self.rect.centery
        colors = [(139, 90, 43), (160, 110, 60), (105, 65, 30), (180, 130, 75)]
        
        if self.health == 1:
            # First hit: switch to cracked barrel and spawn small splinter burst
            self.image = self.img_damaged
            for _ in range(6):
                ang = random.uniform(math.pi * 0.7, math.pi * 1.3)
                spd = random.uniform(60, 140)
                self.particles.append(WoodParticle(cx, cy, math.cos(ang) * spd, math.sin(ang) * spd, random.choice(colors), random.uniform(2, 4)))
            return False
            
        elif self.health <= 0:
            # Destroyed!
            self.is_broken = True
            self.anim_manager.play("break", force_reset=True)
            if self.debris_anim:
                self.debris_anim.reset()
                
            for _ in range(16):
                ang = random.uniform(-math.pi * 0.9, -math.pi * 0.1)
                spd = random.uniform(100, 260)
                self.particles.append(WoodParticle(cx, cy, math.cos(ang) * spd, math.sin(ang) * spd, random.choice(colors), random.uniform(2.5, 5.0)))
                
            # 40% chance to drop healing potion or mana crystal
            if spawn_collectible_callback and random.random() < 0.40:
                drop_type = "potion" if random.random() < 0.65 else "crystal"
                spawn_collectible_callback(self.rect.centerx, self.rect.bottom, drop_type)
            return True

    def update(self, dt: float, player = None, spawn_collectible_callback = None):
        if not self.active:
            return
            
        # Update wood particles
        self.particles = [p for p in self.particles if p.update(dt)]
        
        if self.prop_type == "barrel":
            if self.is_broken:
                if self.anim_manager:
                    self.anim_manager.update(dt)
                if self.debris_anim:
                    self.debris_anim.update(dt)
                if (not self.debris_anim or self.debris_anim.finished) and len(self.particles) == 0:
                    self.active = False
            return
            
        if self.prop_type == "chest":
            if self.opened:
                self.anim_manager.update(dt)
            elif player and self.rect.colliderect(player.rect):
                self.opened = True
                if spawn_collectible_callback:
                    spawn_collectible_callback(self.rect.centerx, self.rect.bottom, "potion")
                    
        if self.prop_type == "barricade":
            if self.barricade_damage_cooldown > 0:
                self.barricade_damage_cooldown -= dt
            if player and self.barricade_damage_cooldown <= 0:
                # Stepping or colliding on barricade deals punishing 3-4 hazard damage
                if self.rect.inflate(-20, -15).colliderect(player.rect):
                    player.take_damage(3)
                    self.barricade_damage_cooldown = 0.6
                    
    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if not self.active:
            return
        draw_x = self.rect.x - camera_offset.x
        draw_y = self.rect.y - camera_offset.y
        
        if self.prop_type == "barrel":
            if self.is_broken:
                # Draw breaking frames and debris VFX
                brk_frame = self.anim_manager.get_current_frame()
                if brk_frame:
                    surface.blit(brk_frame, (draw_x, draw_y))
                if self.debris_anim and not self.debris_anim.finished:
                    df = self.debris_anim.get_current_frame()
                    if df:
                        dx = self.rect.centerx - camera_offset.x - df.get_width() / 2
                        dy = self.rect.centery - camera_offset.y - df.get_height() / 2
                        surface.blit(df, (dx, dy))
            elif self.image:
                surface.blit(self.image, (draw_x, draw_y))
                
        elif self.prop_type == "chest" and self.opened:
            img = self.anim_manager.get_current_frame()
            if img:
                surface.blit(img, (draw_x, draw_y))
        elif self.image:
            if self.prop_type == "rock":
                shadow_w = int(self.rect.width * 0.9)
                shadow_h = 8
                shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
                pygame.draw.ellipse(shadow_surf, (0, 0, 0, 90), (0, 0, shadow_w, shadow_h))
                surface.blit(shadow_surf, (draw_x + (self.rect.width - shadow_w)//2, draw_y + self.rect.height - 4))
                
            surface.blit(self.image, (draw_x, draw_y))
            
        # Draw flying wood particles
        for p in self.particles:
            p.draw(surface, camera_offset.x, camera_offset.y)
