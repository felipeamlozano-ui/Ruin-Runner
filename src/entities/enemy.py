import pygame
import os
import random
from config.constants import GRAVITY, MAX_FALL_SPEED
import engine.resource_manager as rm
from engine.animation import AnimationManager, load_animation_folder

class Enemy:
    def __init__(self, x: float, y: float, width: float, height: float):
        self.pos = pygame.math.Vector2(x, y)
        self.velocity = pygame.math.Vector2(0, 0)
        self.rect = pygame.FRect(x, y, width, height)
        
        self.health = 3
        self.is_dead = False
        self.facing_right = False
        self.on_ground = False
        
        self.anim_manager = AnimationManager()
        self.state = "IDLE"

    def take_damage(self, amount: int):
        if self.is_dead:
            return
        
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.die()
        else:
            self.change_state("HURT")
            
    def die(self):
        self.is_dead = True
        self.change_state("DEAD")

    def change_state(self, new_state: str):
        self.state = new_state
        
    def _apply_physics(self, dt: float, tiles: list[pygame.FRect]):
        # Apply Gravity
        self.velocity.y += GRAVITY
        self.velocity.y = min(self.velocity.y, MAX_FALL_SPEED)
        
        # Move X
        self.pos.x += self.velocity.x * dt
        self.rect.x = self.pos.x
        
        # Collide X
        for tile in tiles:
            if self.rect.colliderect(tile):
                if self.velocity.x > 0:
                    self.rect.right = tile.left
                elif self.velocity.x < 0:
                    self.rect.left = tile.right
                self.pos.x = self.rect.x
                self.velocity.x = 0
                break
                
        # Move Y
        self.pos.y += self.velocity.y * dt
        self.rect.y = self.pos.y
        
        self.on_ground = False
        # Collide Y
        for tile in tiles:
            if self.rect.colliderect(tile):
                if self.velocity.y > 0:
                    self.rect.bottom = tile.top
                    self.on_ground = True
                elif self.velocity.y < 0:
                    self.rect.top = tile.bottom
                self.pos.y = self.rect.y
                self.velocity.y = 0
                break

    def update(self, dt: float, tiles: list[pygame.FRect], player):
        pass

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if self.is_dead and self.anim_manager.is_finished("dead"):
            return # Don't draw if fully dead (or could draw last frame)

        img = self.anim_manager.get_current_frame()
        img_rect = img.get_rect()
        
        draw_x = self.rect.centerx - camera_offset.x - img_rect.width / 2
        draw_y = self.rect.bottom - camera_offset.y - img_rect.height
        
        if not self.facing_right:
            img = pygame.transform.flip(img, True, False)
            
        surface.blit(img, (draw_x, draw_y))


class Skeleton(Enemy):
    def __init__(self, x: float, y: float):
        super().__init__(x, y, 32, 70)
        self.health = 4 # Increased difficulty (doubled HP)
        
        scale = 0.65
        base_path = os.path.join("assets", "sprites", "skeleton")
        
        self.anim_manager.add_animation("idle", load_animation_folder(base_path, "common_01_idle", 10, True, scale))
        self.anim_manager.add_animation("walk", load_animation_folder(base_path, "common_11_walk", 12, True, scale))
        self.anim_manager.add_animation("attack", load_animation_folder(base_path, "attack_01_sword", 12, False, scale))
        self.anim_manager.add_animation("hurt", load_animation_folder(base_path, "damage_02_damage_body", 10, False, scale))
        self.anim_manager.add_animation("dead", load_animation_folder(base_path, "damage_11_blow_landing", 10, False, scale))
        
        self.anim_manager.play("idle")
        
        # AI variables (Enhanced aggression & speed)
        self.state_timer = 0.0
        self.patrol_dir = -1
        self.speed = 90.0
        self.chase_speed = 160.0
        self.vision_range = 380.0
        self.attack_range = 65.0

    def change_state(self, new_state: str):
        super().change_state(new_state)
        self.state_timer = 0.0
        
        if self.state == "IDLE":
            self.velocity.x = 0
            self.anim_manager.play("idle")
            self.state_timer = random.uniform(0.6, 2.0)
        elif self.state == "PATROL":
            self.anim_manager.play("walk")
            self.state_timer = random.uniform(1.5, 3.0)
            self.patrol_dir = random.choice([-1, 1])
            self.facing_right = self.patrol_dir > 0
        elif self.state == "CHASE":
            self.anim_manager.play("walk")
        elif self.state == "ATTACK":
            # Fast aggressive lunge forward when attacking
            self.velocity.x = (150.0 if self.facing_right else -150.0)
            self.anim_manager.play("attack", force_reset=True)
        elif self.state == "HURT":
            self.velocity.x = 0
            self.anim_manager.play("hurt", force_reset=True)
        elif self.state == "DEAD":
            self.velocity.x = 0
            self.anim_manager.play("dead", force_reset=True)

    def get_attack_hitbox(self) -> pygame.FRect:
        """Returns the hitbox for the attack if currently attacking, else None."""
        if self.state != "ATTACK":
            return None
        
        # Only deal damage in the middle of the attack animation
        if self.anim_manager.animations["attack"].current_frame < 3:
            return None
            
        hitbox_width = 32
        hitbox_height = 42
        hitbox_y = self.rect.centery - hitbox_height / 2
        if self.facing_right:
            return pygame.FRect(self.rect.right, hitbox_y, hitbox_width, hitbox_height)
        else:
            return pygame.FRect(self.rect.left - hitbox_width, hitbox_y, hitbox_width, hitbox_height)

    def update(self, dt: float, tiles: list[pygame.FRect], player):
        if not self.is_dead:
            self.state_timer -= dt
            
            # Distance to player
            dist_to_player = player.rect.centerx - self.rect.centerx
            abs_dist = abs(dist_to_player)
            player_in_range = abs_dist < self.vision_range and abs(player.rect.centery - self.rect.centery) < 120
            
            if self.state == "HURT":
                if self.anim_manager.is_finished("hurt"):
                    self.change_state("IDLE")
            elif self.state == "ATTACK":
                self.velocity.x *= 0.9 # Smooth lunge deceleration
                if self.anim_manager.is_finished("attack"):
                    self.change_state("IDLE")
            elif self.state == "IDLE":
                if player_in_range and not player.invulnerable:
                    self.change_state("CHASE")
                elif self.state_timer <= 0:
                    self.change_state("PATROL")
            elif self.state == "PATROL":
                if player_in_range and not player.invulnerable:
                    self.change_state("CHASE")
                elif self.state_timer <= 0:
                    self.change_state("IDLE")
                else:
                    self.velocity.x = self.speed * self.patrol_dir
                    
            elif self.state == "CHASE":
                if not player_in_range or player.invulnerable:
                    self.change_state("IDLE")
                elif abs_dist <= self.attack_range:
                    self.facing_right = dist_to_player > 0
                    self.change_state("ATTACK")
                else:
                    self.facing_right = dist_to_player > 0
                    self.velocity.x = self.chase_speed if self.facing_right else -self.chase_speed
                    

        self._apply_physics(dt, tiles)
        self.anim_manager.update(dt)

class MageSkeleton(Skeleton):
    def __init__(self, x: float, y: float):
        super().__init__(x, y)
        self.health = 2
        # Different AI parameters for ranged
        self.speed = 60.0
        self.chase_speed = 90.0
        self.vision_range = 500.0
        self.attack_range = 350.0
        
        self.projectiles = []
        self.attack_cooldown = 0.0
        
    def update(self, dt: float, tiles: list[pygame.FRect], player):
        if not self.is_dead:
            self.state_timer -= dt
            self.attack_cooldown -= dt
            
            # Distance to player
            dist_to_player = player.rect.centerx - self.rect.centerx
            abs_dist = abs(dist_to_player)
            player_in_range = abs_dist < self.vision_range and abs(player.rect.centery - self.rect.centery) < 150
            
            if self.state == "HURT":
                if self.anim_manager.is_finished("hurt"):
                    self.change_state("IDLE")
            elif self.state == "ATTACK":
                if self.anim_manager.is_finished("attack"):
                    self.change_state("IDLE")
                # Shoot projectile at specific frame (e.g. frame 3)
                elif self.anim_manager.animations["attack"].current_frame == 3 and self.attack_cooldown <= 0:
                    from entities.projectile import Projectile
                    proj_x = self.rect.right if self.facing_right else self.rect.left - 16
                    proj_y = self.rect.centery
                    self.projectiles.append(Projectile(proj_x, proj_y, self.facing_right, is_enemy=True, projectile_type="mage_fireball"))
                    self.attack_cooldown = 1.8 # Cooldown
            elif self.state == "IDLE":
                if player_in_range and not player.invulnerable:
                    if abs_dist <= self.attack_range and self.attack_cooldown <= 0:
                        self.facing_right = dist_to_player > 0
                        self.change_state("ATTACK")
                    else:
                        self.change_state("CHASE")
                elif self.state_timer <= 0:
                    self.change_state("PATROL")
            elif self.state == "PATROL":
                if player_in_range and not player.invulnerable:
                    self.change_state("CHASE")
                elif self.state_timer <= 0:
                    self.change_state("IDLE")
                else:
                    self.velocity.x = self.speed * self.patrol_dir
                    
            elif self.state == "CHASE":
                if not player_in_range or player.invulnerable:
                    self.change_state("IDLE")
                elif abs_dist <= self.attack_range and self.attack_cooldown <= 0:
                    self.facing_right = dist_to_player > 0
                    self.change_state("ATTACK")
                else:
                    # Move towards player, but stop if too close
                    if abs_dist < 150:
                        self.velocity.x = 0
                        self.anim_manager.play("idle")
                    else:
                        self.patrol_dir = 1 if dist_to_player > 0 else -1
                        self.facing_right = self.patrol_dir > 0
                        self.velocity.x = self.chase_speed * self.patrol_dir
                        self.anim_manager.play("walk")

        self._apply_physics(dt, tiles)
        self.anim_manager.update(dt)
        
    def get_attack_hitbox(self) -> pygame.FRect:
        # Mage skeleton doesn't do melee damage
        return None
        
    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if self.is_dead and self.anim_manager.is_finished("dead"):
            return 
            
        img = self.anim_manager.get_current_frame()
        img_rect = img.get_rect()
        draw_x = self.rect.centerx - camera_offset.x - img_rect.width / 2
        draw_y = self.rect.bottom - camera_offset.y - img_rect.height
        
        if not self.facing_right:
            img = pygame.transform.flip(img, True, False)
            
        # Tint mage skeleton purple to distinguish from regular skeleton
        tinted = img.copy()
        tinted.fill((200, 100, 255), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(tinted, (draw_x, draw_y))


class WildBoar(Enemy):
    """Charging Beast from Legacy-Fantasy that rushes at Arani upon seeing her."""
    def __init__(self, x: float, y: float):
        super().__init__(x, y, 46, 38)
        self.health = 3
        
        boar_base = os.path.join("Legacy-Fantasy - High Forest 2.3", "Mob", "Boar")
        from engine.animation import load_spritesheet
        scale = 1.35
        
        idle_path = os.path.join(boar_base, "Idle", "Idle-Sheet.png")
        walk_path = os.path.join(boar_base, "Walk", "Walk-Base-Sheet.png")
        run_path = os.path.join(boar_base, "Run", "Run-Sheet.png")
        hit_path = os.path.join(boar_base, "Hit-Vanish", "Hit-Sheet.png")
        
        self.anim_manager.add_animation("idle", load_spritesheet(idle_path, 48, 32, fps=8, loop=True, scale=scale))
        self.anim_manager.add_animation("walk", load_spritesheet(walk_path, 48, 32, fps=10, loop=True, scale=scale))
        self.anim_manager.add_animation("run", load_spritesheet(run_path, 48, 32, fps=14, loop=True, scale=scale))
        self.anim_manager.add_animation("hurt", load_spritesheet(hit_path, 48, 32, fps=12, loop=False, scale=scale))
        self.anim_manager.add_animation("dead", load_spritesheet(hit_path, 48, 32, fps=10, loop=False, scale=scale))
        
        self.anim_manager.play("idle")
        
        self.speed = 70.0
        self.charge_speed = 230.0
        self.vision_range = 450.0
        self.state_timer = 0.0
        self.patrol_dir = -1
        
    def change_state(self, new_state: str):
        super().change_state(new_state)
        self.state_timer = 0.0
        if self.state == "IDLE":
            self.velocity.x = 0
            self.anim_manager.play("idle")
            self.state_timer = random.uniform(1.0, 2.5)
        elif self.state == "PATROL":
            self.anim_manager.play("walk")
            self.state_timer = random.uniform(2.0, 3.5)
            self.patrol_dir = random.choice([-1, 1])
            self.facing_right = self.patrol_dir > 0
        elif self.state == "CHARGE":
            self.anim_manager.play("run")
        elif self.state == "HURT":
            self.velocity.x = -60 if self.facing_right else 60
            self.anim_manager.play("hurt", force_reset=True)
        elif self.state == "DEAD":
            self.velocity.x = 0
            self.anim_manager.play("dead", force_reset=True)
            
    def update(self, dt: float, tiles: list[pygame.FRect], player):
        if not self.is_dead:
            self.state_timer -= dt
            dist_to_player = player.rect.centerx - self.rect.centerx
            abs_dist = abs(dist_to_player)
            player_in_range = abs_dist < self.vision_range and abs(player.rect.centery - self.rect.centery) < 100
            
            if self.state == "HURT":
                if self.anim_manager.is_finished("hurt"):
                    self.change_state("CHARGE")
            elif self.state == "IDLE":
                if player_in_range and not player.invulnerable:
                    self.change_state("CHARGE")
                elif self.state_timer <= 0:
                    self.change_state("PATROL")
            elif self.state == "PATROL":
                if player_in_range and not player.invulnerable:
                    self.change_state("CHARGE")
                elif self.state_timer <= 0:
                    self.change_state("IDLE")
                else:
                    self.velocity.x = self.speed * self.patrol_dir
            elif self.state == "CHARGE":
                if not player_in_range:
                    self.change_state("IDLE")
                else:
                    self.patrol_dir = 1 if dist_to_player > 0 else -1
                    self.facing_right = self.patrol_dir > 0
                    self.velocity.x = self.charge_speed * self.patrol_dir
                    
        self._apply_physics(dt, tiles)
        self.anim_manager.update(dt)
        
    def get_attack_hitbox(self) -> pygame.FRect:
        # Full body attack during charge
        if self.state == "CHARGE" and not self.is_dead:
            return self.rect
        return None

