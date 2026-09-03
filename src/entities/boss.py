import pygame
import os
import random
from engine.animation import AnimationManager, load_animation_folder, load_spritesheet
from entities.projectile import Projectile

class BossShockwave:
    """Ground shockwave traveling along the floor created by Boss Jump Slam."""
    def __init__(self, x: float, y: float, moving_right: bool):
        self.rect = pygame.FRect(x, y - 20, 36, 40)
        self.velocity_x = 350.0 if moving_right else -350.0
        self.active = True
        self.damage = 1
        self.moving_right = moving_right
        
        shock_path = os.path.join("assets", "sprites", "vfx", "vfx_ground_shock")
        self.anim = load_animation_folder(shock_path, "vfx_ground_shock", fps=18, loop=True, scale=1.4)
        self.lifetime = 2.0
        
    def update(self, dt: float, tiles: list[pygame.FRect]):
        if not self.active: return
        self.anim.update(dt)
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.active = False
            return
            
        self.rect.x += self.velocity_x * dt
        for t in tiles:
            if t.width < 100 and self.rect.colliderect(t): # collided with wall
                self.active = False
                break
                
    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if self.active:
            img = self.anim.get_current_frame()
            if not self.moving_right:
                img = pygame.transform.flip(img, True, False)
            draw_x = self.rect.centerx - camera_offset.x - img.get_width() / 2
            draw_y = self.rect.bottom - camera_offset.y - img.get_height()
            surface.blit(img, (draw_x, draw_y))

class SkeletonBoss:
    """Epic Skeleton King Boss with Multi-Phase AI and Dynamic Skills."""
    def __init__(self, x: float, y: float):
        self.pos = pygame.math.Vector2(x, y)
        self.velocity = pygame.math.Vector2(0, 0)
        self.rect = pygame.FRect(x, y, 54, 96)
        
        self.max_health = 450 # Significantly increased HP for challenging boss fight
        self.health = self.max_health
        self.is_dead = False
        self.facing_right = False
        self.enraged = False
        self.hit_count = 0
        self.potions_to_spawn = []
        self.potion_dropped_50 = False # Drop only 1 potion at 50% HP
        self.slow_timer = 0.0
        self.slow_factor = 1.0
        
        # Boss Combat & AI State
        self.state = "IDLE" # IDLE, CHASE, ATTACK, FLAME_BURST, JUMP_SLAM, SHADOW_STEP, ROAR
        self.state_timer = 0.0
        self.skill_cooldown = 2.0
        self.attack_cooldown = 0.8
        self.has_hit_player = False
        
        # Summon threshold triggers (Multi-Wave Escalation)
        self.summoned_75 = False
        self.summoned_50 = False
        self.summoned_25 = False
        self.minions_to_spawn = []
        
        # Projectiles & Shockwaves
        self.projectiles = []
        self.shockwaves = []
        
        # Smoke VFX for Teleport
        self.smoke_active = False
        self.smoke_timer = 0.0
        self.smoke_pos = pygame.math.Vector2(0, 0)
        vfx_smoke_path = os.path.join("assets", "sprites", "vfx", "vfx_smoke")
        self.smoke_anim = load_animation_folder(vfx_smoke_path, "vfx_smoke", 22, False, 2.0)
        
        # Animations
        self.anim_manager = AnimationManager()
        scale = 1.45
        base_path = os.path.join("assets", "sprites", "skeleton")
        
        self.anim_manager.add_animation("idle", load_animation_folder(base_path, "common_01_idle", 10, True, scale))
        self.anim_manager.add_animation("walk", load_animation_folder(base_path, "common_11_walk", 12, True, scale))
        self.anim_manager.add_animation("attack", load_animation_folder(base_path, "attack_01_sword", 14, False, scale))
        self.anim_manager.add_animation("jump", load_animation_folder(base_path, "common_21_jump_up", 12, False, scale))
        self.anim_manager.add_animation("slam", load_animation_folder(base_path, "damage_11_blow_landing", 14, False, scale))
        self.anim_manager.add_animation("cast", load_animation_folder(base_path, "misc_01_enter", 12, False, scale))
        self.anim_manager.add_animation("hurt", load_animation_folder(base_path, "damage_02_damage_body", 10, False, scale))
        self.anim_manager.add_animation("dead", load_animation_folder(base_path, "damage_11_blow_landing", 8, False, scale))
        
        self.anim_manager.play("idle")
        
    def apply_slow(self, duration: float = 2.5, factor: float = 0.35):
        """Applies slow-motion status effect from player Ultimate skill."""
        if not self.is_dead:
            self.slow_timer = max(self.slow_timer, duration)
            self.slow_factor = factor

    def take_damage(self, amount: int):
        if self.is_dead or self.state == "SHADOW_STEP":
            return
            
        self.health -= amount
        self.hit_count += 1
        
        # Drop ONLY ONE healing potion when health drops to 50% or below per user request!
        if self.health <= self.max_health // 2 and not self.potion_dropped_50:
            self.potion_dropped_50 = True
            self.potions_to_spawn.append((self.rect.centerx, self.rect.centery - 20))
            
        if self.health <= 0:
            self.health = 0
            self.is_dead = True
            self.state = "DEAD"
            self.anim_manager.play("dead", force_reset=True)
            self.velocity.x = 0
            self.velocity.y = -100
        else:
            # Check Enrage at 50% HP
            if self.health <= self.max_health // 2 and not self.enraged:
                self.enraged = True
                self.state = "ROAR"
                self.state_timer = 1.0
                self.anim_manager.play("cast", force_reset=True)
                
            # Check Minion Reinforcements
            if self.health <= 335 and not self.summoned_75:
                self.summoned_75 = True
                self.minions_to_spawn.extend([("skeleton", self.rect.x - 120), ("mage", self.rect.x + 120)])
            if self.health <= 225 and not self.summoned_50:
                self.summoned_50 = True
                self.minions_to_spawn.extend([("boar", self.rect.x - 140), ("mage", self.rect.x + 140)])
            if self.health <= 110 and not self.summoned_25:
                self.summoned_25 = True
                self.minions_to_spawn.extend([("mage", self.rect.x - 160), ("mage", self.rect.x + 160)])

    def update(self, dt: float, tiles: list[pygame.FRect], player = None):
        if self.slow_timer > 0:
            self.slow_timer -= dt
            effective_dt = dt * self.slow_factor
        else:
            effective_dt = dt
            
        self.anim_manager.update(effective_dt)
        
        if self.smoke_active:
            self.smoke_anim.update(effective_dt)
            self.smoke_timer -= effective_dt
            if self.smoke_timer <= 0 or self.smoke_anim.finished:
                self.smoke_active = False
                
        # Update shockwaves
        for sw in self.shockwaves[:]:
            sw.update(dt, tiles)
            if not sw.active:
                self.shockwaves.remove(sw)
            elif player and sw.rect.colliderect(player.rect):
                player.take_damage(sw.damage)
                sw.active = False
                self.shockwaves.remove(sw)
                
        if self.is_dead:
            # Gravity for corpse
            self.velocity.y += 800 * dt
            self.pos.y += self.velocity.y * dt
            self.rect.y = self.pos.y
            for t in tiles:
                if self.rect.colliderect(t) and self.velocity.y > 0:
                    self.rect.bottom = t.top
                    self.pos.y = self.rect.y
                    self.velocity.y = 0
            return
            
        if self.skill_cooldown > 0:
            self.skill_cooldown -= dt
        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt
            
        if player:
            self.facing_right = player.rect.centerx > self.rect.centerx
            dx = player.rect.centerx - self.rect.centerx
            dist = abs(dx)
            
            speed_mult = 1.35 if self.enraged else 1.0
            
            # State Machine
            if self.state == "IDLE":
                self.anim_manager.play("idle")
                self.velocity.x = 0
                self.state_timer -= dt
                if self.state_timer <= 0:
                    self.state = "CHASE"
                    
            elif self.state == "CHASE":
                self.anim_manager.play("walk")
                self.velocity.x = (140.0 * speed_mult) if self.facing_right else (-140.0 * speed_mult)
                
                # Check Melee Attack
                if dist < 75 and self.attack_cooldown <= 0:
                    self.state = "ATTACK"
                    self.has_hit_player = False
                    self.velocity.x = (180.0 * speed_mult) if self.facing_right else (-180.0 * speed_mult) # lunge
                    self.anim_manager.play("attack", force_reset=True)
                    
                # Check Special Skills
                elif self.skill_cooldown <= 0:
                    chosen_skill = random.choice(["FLAME_BURST", "JUMP_SLAM", "SHADOW_STEP"])
                    self.state = chosen_skill
                    self.state_timer = 0.0
                    self.skill_cooldown = 2.8 if not self.enraged else 1.8
                    
                    if chosen_skill == "FLAME_BURST":
                        self.velocity.x = 0
                        self.anim_manager.play("cast", force_reset=True)
                        self.state_timer = 0.6
                        
                    elif chosen_skill == "JUMP_SLAM":
                        self.velocity.y = -650 # Huge jump
                        self.velocity.x = (250.0 * speed_mult) if self.facing_right else (-250.0 * speed_mult)
                        self.anim_manager.play("jump", force_reset=True)
                        
                    elif chosen_skill == "SHADOW_STEP":
                        # Teleport behind Arani with smoke puff
                        self.smoke_active = True
                        self.smoke_timer = 0.5
                        self.smoke_pos = pygame.math.Vector2(self.rect.centerx, self.rect.centery)
                        self.smoke_anim.reset()
                        
                        target_x = player.rect.centerx + (-90 if player.facing_right else 90)
                        self.rect.x = max(100, min(1400, target_x))
                        self.pos.x = self.rect.x
                        self.facing_right = player.rect.centerx > self.rect.centerx
                        self.state = "ATTACK"
                        self.has_hit_player = False
                        self.anim_manager.play("attack", force_reset=True)
                        
            elif self.state == "ATTACK":
                self.velocity.x *= 0.9
                if self.anim_manager.is_finished("attack"):
                    self.state = "IDLE"
                    self.state_timer = 0.4
                    self.attack_cooldown = 0.9 if not self.enraged else 0.5
                    
            elif self.state == "FLAME_BURST":
                self.velocity.x = 0
                self.state_timer -= dt
                if self.state_timer <= 0:
                    # Shoot 3 fireballs
                    proj_x = self.rect.right if self.facing_right else self.rect.left - 24
                    proj_y = self.rect.centery - 10
                    
                    p1 = Projectile(proj_x, proj_y, self.facing_right, is_enemy=True, projectile_type="boss_fireball")
                    p2 = Projectile(proj_x, proj_y - 25, self.facing_right, is_enemy=True, projectile_type="boss_fireball")
                    p2.velocity.y = -70
                    p3 = Projectile(proj_x, proj_y + 25, self.facing_right, is_enemy=True, projectile_type="boss_fireball")
                    p3.velocity.y = 70
                    
                    self.projectiles.extend([p1, p2, p3])
                    self.state = "IDLE"
                    self.state_timer = 0.5
                    
            elif self.state == "JUMP_SLAM":
                # Wait for landing
                pass
                
            elif self.state == "ROAR":
                self.velocity.x = 0
                self.state_timer -= dt
                if self.state_timer <= 0:
                    self.state = "CHASE"
                    
        # Apply physics
        self.velocity.y += 900 * dt
        self.velocity.y = min(self.velocity.y, 800)
        
        self.pos.x += self.velocity.x * dt
        self.rect.x = self.pos.x
        for t in tiles:
            if self.rect.colliderect(t):
                if self.velocity.x > 0: self.rect.right = t.left
                elif self.velocity.x < 0: self.rect.left = t.right
                self.pos.x = self.rect.x
                self.velocity.x = 0
                break
                
        self.pos.y += self.velocity.y * dt
        self.rect.y = self.pos.y
        for t in tiles:
            if self.rect.colliderect(t):
                if self.velocity.y > 0:
                    self.rect.bottom = t.top
                    self.pos.y = self.rect.y
                    
                    # If was jump-slamming, create shockwaves upon hitting ground!
                    if self.state == "JUMP_SLAM":
                        self.state = "IDLE"
                        self.state_timer = 0.5
                        self.anim_manager.play("slam", force_reset=True)
                        # Shockwaves left and right
                        sw_left = BossShockwave(self.rect.left, self.rect.bottom, moving_right=False)
                        sw_right = BossShockwave(self.rect.right, self.rect.bottom, moving_right=True)
                        self.shockwaves.extend([sw_left, sw_right])
                        
                    self.velocity.y = 0
                elif self.velocity.y < 0:
                    self.rect.top = t.bottom
                    self.pos.y = self.rect.y
                    self.velocity.y = 0
                break
                
    def get_attack_hitbox(self) -> pygame.FRect:
        if self.state != "ATTACK" or self.has_hit_player:
            return None
            
        cur_frame = self.anim_manager.animations["attack"].current_frame
        if 2 <= cur_frame <= 5:
            hitbox_w = 65
            hitbox_h = 75
            hitbox_y = self.rect.centery - hitbox_h / 2
            if self.facing_right:
                return pygame.FRect(self.rect.right - 10, hitbox_y, hitbox_w, hitbox_h)
            else:
                return pygame.FRect(self.rect.left - hitbox_w + 10, hitbox_y, hitbox_w, hitbox_h)
        return None

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        # Draw shockwaves
        for sw in self.shockwaves:
            sw.draw(surface, camera_offset)
            
        # Draw teleport smoke puff
        if self.smoke_active:
            smoke_frame = self.smoke_anim.get_current_frame()
            if smoke_frame:
                s_rect = smoke_frame.get_rect(center=(self.smoke_pos.x - camera_offset.x, self.smoke_pos.y - camera_offset.y))
                surface.blit(smoke_frame, s_rect)
                
        img = self.anim_manager.get_current_frame()
        img_rect = img.get_rect()
        draw_x = self.rect.centerx - camera_offset.x - img_rect.width / 2
        draw_y = self.rect.bottom - camera_offset.y - img_rect.height
        
        if not self.facing_right:
            img = pygame.transform.flip(img, True, False)
            
        # If slowed by ultimate, tint icy cyan; if enraged, tint red/purple
        if self.slow_timer > 0 and not self.is_dead:
            tinted = img.copy()
            tinted.fill((140, 205, 255), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(tinted, (draw_x, draw_y))
        elif self.enraged and not self.is_dead:
            tinted = img.copy()
            tinted.fill((255, 120, 120), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(tinted, (draw_x, draw_y))
        else:
            surface.blit(img, (draw_x, draw_y))
