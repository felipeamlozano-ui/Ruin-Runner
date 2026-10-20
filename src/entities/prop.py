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
            raw_intact = pygame.image.load(os.path.join(prop_dir, "barrel_001.png")).convert_alpha()
            raw_damaged = pygame.image.load(os.path.join(prop_dir, "barrel_002.png")).convert_alpha()
            raw_brk1 = pygame.image.load(os.path.join(prop_dir, "barrel_break01.png")).convert_alpha()
            raw_brk2 = pygame.image.load(os.path.join(prop_dir, "barrel_break02.png")).convert_alpha()
            
            def _clean_frame(raw_img: pygame.Surface) -> pygame.Surface:
                img = raw_img.copy()
                w, h = img.get_size()
                for py in range(h):
                    for px in range(w):
                        c = img.get_at((px, py))
                        if c.a > 0 and (c.r > 150 and c.b > 150 and c.g < 80):
                            img.set_at((px, py), (0, 0, 0, 0))
                bbox_c = img.get_bounding_rect()
                return img.subsurface(bbox_c).copy()

            clean_intact = _clean_frame(raw_intact)
            clean_dmg = _clean_frame(raw_damaged)
            clean_b1 = _clean_frame(raw_brk1)
            clean_b2 = _clean_frame(raw_brk2)

            # Calibrate barrel scale relative to protagonist (natural waist-high proportion ~48px)
            target_h = max(42, int(48 * scale))
            target_w = max(30, int(target_h * (clean_intact.get_width() / clean_intact.get_height())))

            self.img_intact = pygame.transform.scale(clean_intact, (target_w, target_h))
            self.img_damaged = pygame.transform.scale(clean_dmg, (target_w, target_h))
            brk1 = pygame.transform.scale(clean_b1, (int(target_h * clean_b1.get_width() / clean_b1.get_height()), target_h))
            brk2 = pygame.transform.scale(clean_b2, (int(target_h * clean_b2.get_width() / clean_b2.get_height()), target_h))
            
            self.image = self.img_intact
            
            # Breaking animation frames
            self.anim_manager = AnimationManager()
            self.anim_manager.add_animation("break", Animation([brk1, brk2], fps=8, loop=False))
            
            # Debris wood VFX
            debris_path = os.path.join("assets", "sprites", "vfx", "vfx_debris_wood")
            if os.path.exists(debris_path):
                self.debris_anim = load_animation_folder(debris_path, "vfx_debris_wood", fps=18, loop=False, scale=max(0.7, scale * 0.7))
                
        elif prop_type == "chest":
            self.anim_manager = AnimationManager()
            self.anim_manager.add_animation("open", load_animation_folder(prop_dir, "chest_open", 10, False, max(0.9, scale)))
            self.anim_manager.play("open")
            self.image = self.anim_manager.animations["open"].frames[0]
            self.opened = False
        elif prop_type == "barricade":
            bar_path = os.path.join(prop_dir, "baricade_export.png")
            if os.path.exists(bar_path):
                raw_bar = pygame.image.load(bar_path).convert_alpha()
                bbox_bar = raw_bar.get_bounding_rect()
                cropped_bar = raw_bar.subsurface(bbox_bar).copy()
                target_h = max(38, int(48 * scale))
                target_w = max(32, int(target_h * (bbox_bar.width / bbox_bar.height)))
                self.image = pygame.transform.smoothscale(cropped_bar, (target_w, target_h))
            else:
                self.image = pygame.Surface((32, 32))
        elif prop_type in ("rock", "stone", "stone_cluster", "cave_rock", "canyon_rock", "middle_lane_rock"):
            rocks_dir = os.path.join("assets", "sprites", "rocks", "PNG")
            rock_candidates = []
            
            # 1. Middle Lane Rocks (variations 1 and 2)
            for sub in ("middle_lane_rocks1", "middle_lane_rocks2"):
                p_sub = os.path.join(rocks_dir, sub)
                if os.path.exists(p_sub):
                    for f in sorted(os.listdir(p_sub)):
                        if f.endswith(".png"):
                            rock_candidates.append(os.path.join(p_sub, f))
                            
            # 2. Cave Rocks
            p_cave = os.path.join(rocks_dir, "cave_rocks")
            if os.path.exists(p_cave):
                for f in sorted(os.listdir(p_cave)):
                    if f.endswith(".png"):
                        rock_candidates.append(os.path.join(p_cave, f))
                        
            # 3. Canyon Rocks
            p_canyon = os.path.join(rocks_dir, "canyon_rocks")
            if os.path.exists(p_canyon):
                for f in sorted(os.listdir(p_canyon)):
                    if f.endswith(".png"):
                        rock_candidates.append(os.path.join(p_canyon, f))

            valid_rocks = [p for p in rock_candidates if os.path.exists(p)]
            if valid_rocks:
                # Deterministic pick based on spawn coordinate
                idx = int((abs(x) * 7 + abs(y) * 13)) % len(valid_rocks)
                raw_rock = pygame.image.load(valid_rocks[idx])
                disp = pygame.display.get_surface()
                if disp:
                    raw_rock = raw_rock.convert_alpha()
                target_w = max(20, int(raw_rock.get_width() * 0.45 * scale))
                target_h = max(14, int(raw_rock.get_height() * (target_w / raw_rock.get_width())))
                self.image = pygame.transform.scale(raw_rock, (target_w, target_h))
            else:
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
        self.y_sort_pivot = float(self.rect.bottom)
        # Dedicated base collider for natural depth and player Y-sorting around rocks
        self.hitbox = pygame.FRect(self.rect.left + 4, self.rect.bottom - max(10, self.rect.height * 0.35), max(8, self.rect.width - 8), max(8, self.rect.height * 0.35))
        
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
            if not self.is_broken:
                # Dual-layer grounded contact shadow under barrel base
                shadow_w = int(self.rect.width * 1.05)
                shadow_h = 10
                shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
                pygame.draw.ellipse(shadow_surf, (0, 0, 0, 115), (0, 0, shadow_w, shadow_h))
                core_w, core_h = max(2, int(shadow_w * 0.65)), max(2, int(shadow_h * 0.65))
                pygame.draw.ellipse(shadow_surf, (0, 0, 0, 160), ((shadow_w - core_w) // 2, (shadow_h - core_h) // 2, core_w, core_h))
                surface.blit(shadow_surf, (self.rect.centerx - camera_offset.x - shadow_w // 2, self.rect.bottom - camera_offset.y - shadow_h // 2 + 1))
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
                
        elif self.prop_type == "chest":
            shadow_w = int(self.rect.width * 1.0)
            shadow_h = 8
            shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_surf, (0, 0, 0, 105), (0, 0, shadow_w, shadow_h))
            core_w, core_h = max(2, int(shadow_w * 0.65)), max(2, int(shadow_h * 0.65))
            pygame.draw.ellipse(shadow_surf, (0, 0, 0, 150), ((shadow_w - core_w) // 2, (shadow_h - core_h) // 2, core_w, core_h))
            surface.blit(shadow_surf, (self.rect.centerx - camera_offset.x - shadow_w // 2, self.rect.bottom - camera_offset.y - shadow_h // 2 + 1))
            if self.opened:
                img = self.anim_manager.get_current_frame()
                if img:
                    surface.blit(img, (draw_x, draw_y))
            elif self.image:
                surface.blit(self.image, (draw_x, draw_y))
        elif self.image:
            shadow_w = int(self.rect.width * 0.95)
            shadow_h = 8
            shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_surf, (0, 0, 0, 100), (0, 0, shadow_w, shadow_h))
            core_w, core_h = max(2, int(shadow_w * 0.65)), max(2, int(shadow_h * 0.65))
            pygame.draw.ellipse(shadow_surf, (0, 0, 0, 140), ((shadow_w - core_w) // 2, (shadow_h - core_h) // 2, core_w, core_h))
            surface.blit(shadow_surf, (self.rect.centerx - camera_offset.x - shadow_w // 2, self.rect.bottom - camera_offset.y - shadow_h // 2 + 1))
            surface.blit(self.image, (draw_x, draw_y))
            
        # Draw flying wood particles
        for p in self.particles:
            p.draw(surface, camera_offset.x, camera_offset.y)
