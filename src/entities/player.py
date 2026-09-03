import pygame
import os
import math
import random
from config.constants import GRAVITY, MAX_FALL_SPEED, ACCELERATION, MAX_SPEED, JUMP_FORCE, FRICTION
from engine.input_manager import INPUT
import engine.resource_manager as rm
from utils.math_utils import clamp
from engine.animation import AnimationManager, load_animation_folder

class AfterImage:
    """Ghost trail image left behind during a dash."""
    def __init__(self, surf: pygame.Surface, x: float, y: float, facing_right: bool, duration: float = 0.28):
        self.surf = surf.copy()
        # Tint with glowing cyan/blue
        self.surf.fill((60, 180, 255), special_flags=pygame.BLEND_RGBA_MULT)
        self.x = x
        self.y = y
        self.facing_right = facing_right
        self.duration = duration
        self.timer = 0.0
        self.alpha = 190
        
    def update(self, dt: float) -> bool:
        self.timer += dt
        progress = min(1.0, self.timer / self.duration)
        self.alpha = max(0, int(190 * (1.0 - progress)))
        return self.timer < self.duration
        
    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        temp = self.surf.copy()
        temp.set_alpha(self.alpha)
        draw_x = self.x - camera_offset.x
        draw_y = self.y - camera_offset.y
        surface.blit(temp, (draw_x, draw_y))

class ImpactSmoke:
    """Ground dust puff left behind when landing from a plunge attack."""
    def __init__(self, x: float, y: float):
        vfx_smoke_path = os.path.join("assets", "sprites", "vfx", "vfx_smoke")
        self.anim = load_animation_folder(vfx_smoke_path, "vfx_smoke", 20, False, 1.3)
        self.x = x
        self.y = y
        self.active = True
        
    def update(self, dt: float):
        self.anim.update(dt)
        if self.anim.finished:
            self.active = False
            
    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if self.active:
            frame = self.anim.get_current_frame()
            r = frame.get_rect(center=(self.x - camera_offset.x, self.y - camera_offset.y))
            surface.blit(frame, r)

class UltimateSlash:
    """Radiant phantom sword slash cutting across screen during Ultimate."""
    def __init__(self, start_pos: tuple, end_pos: tuple, color=(255, 235, 120), width=5):
        self.start = start_pos
        self.end = end_pos
        self.color = color
        self.width = width
        self.life = 0.35
        self.timer = 0.0
        
    def update(self, dt: float) -> bool:
        self.timer += dt
        return self.timer < self.life
        
    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        progress = self.timer / self.life
        alpha = max(0, int(255 * (1.0 - progress)))
        p1 = (self.start[0] - camera_offset.x, self.start[1] - camera_offset.y)
        p2 = (self.end[0] - camera_offset.x, self.end[1] - camera_offset.y)
        
        gw, gh = surface.get_size()
        line_surf = pygame.Surface((gw, gh), pygame.SRCALPHA)
        # Wide radiant glow
        pygame.draw.line(line_surf, (*self.color, int(alpha * 0.45)), p1, p2, int(self.width * 3))
        # Brilliant bright core
        pygame.draw.line(line_surf, (255, 255, 255, alpha), p1, p2, self.width)
        surface.blit(line_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

class Player:
    def __init__(self, x: float, y: float):
        # Position & Physics
        self.pos = pygame.math.Vector2(x, y)
        self.velocity = pygame.math.Vector2(0, 0)
        self.rect = pygame.FRect(x, y, 32, 80)
        
        # State
        self.on_ground = False
        self.can_double_jump = False
        
        # Stats
        self.max_health = 20 # 20 HP as requested
        self.health = self.max_health
        self.max_mana = 100.0
        self.mana = self.max_mana
        self.stamina = 100.0
        
        # Combat & Inventory
        self.invulnerable = False
        self.invulnerability_timer = 0.0
        self.is_blocking = False
        self.is_dashing = False
        self.dash_timer = 0.0
        self.dash_duration = 0.22
        self.dash_cooldown = 0.0
        self.dash_speed = 750.0
        self.dash_ghost_timer = 0.0
        self.after_images: list[AfterImage] = []
        
        # AoE Nova Skill
        self.is_casting_aoe = False
        self.aoe_timer = 0.0
        self.aoe_hit_done = False
        self.aoe_radius = 150.0
        
        # Ultimate Skill [R] - Devastating Celestial Cleave
        self.is_casting_ultimate = False
        self.ultimate_timer = 0.0
        self.ultimate_hit_done = False
        self.ultimate_slashes: list[UltimateSlash] = []
        self.ultimate_shockwave_anim = load_animation_folder(os.path.join("assets", "sprites", "vfx", "vfx_ground_shock"), "vfx_ground_shock", 16, False, 1.8)
        self.ultimate_shockwave_active = False
        self.ultimate_shockwave_pos = (0, 0)
        self.ultimate_shockwave_timer = 0.0
        
        # Downward Aerial Plunge Attack
        self.is_down_attacking = False
        self.is_landing_plunge = False
        self.plunge_recovery = 0.0
        self.plunge_hit_enemies = set()
        self.plunge_impact_pending = False
        self.impact_smokes: list[ImpactSmoke] = []
        
        self.projectiles = []
        self.inventory = {'crystals': 0, 'relics': 0}
        
        # Visuals & Animation
        self.facing_right = True
        self.anim_manager = AnimationManager()
        
        base_path = os.path.join("assets", "sprites", "shaia", "sprites_common")
        attack_path = os.path.join("assets", "sprites", "shaia", "sprites_attack")
        append_path = os.path.join("assets", "sprites", "shaia", "sprites_append")
        scale = 0.65
        
        self.anim_manager.add_animation("idle", load_animation_folder(base_path, "common_00_idle_stand_A", 15, True, scale))
        self.anim_manager.add_animation("walk", load_animation_folder(base_path, "common_11_walk", 15, True, scale))
        self.anim_manager.add_animation("jump", load_animation_folder(base_path, "common_21_jump_up", 15, False, scale))
        self.anim_manager.add_animation("fall", load_animation_folder(base_path, "common_21_jump_down", 15, True, scale))
        self.anim_manager.add_animation("attack", load_animation_folder(attack_path, "attack_01_cobination01", 14, False, scale))
        self.anim_manager.add_animation("dash", load_animation_folder(append_path, "common_12_guard_dash", 24, False, scale))
        self.anim_manager.add_animation("whirlwind", load_animation_folder(attack_path, "attack_04_cobination04", 18, False, scale))
        self.anim_manager.add_animation("heavy_slash", load_animation_folder(attack_path, "attack_03_cobination03", 16, False, scale))
        self.anim_manager.add_animation("jump_attack", load_animation_folder(attack_path, "attack_21_jump_attack", 16, True, scale))
        self.anim_manager.add_animation("landing", load_animation_folder(base_path, "common_22_landing", 14, False, scale))
        
        damage_path = os.path.join("assets", "sprites", "shaia", "sprites_damage")
        self.anim_manager.add_animation("dead", load_animation_folder(damage_path, "damage_11_blow_landing_A", 10, False, scale))
        self.anim_manager.add_animation("guard", load_animation_folder(base_path, "common_31_guard_stand", 10, True, scale))
        
        # Guard shield barrier visual effect
        vfx_guard_path = os.path.join("assets", "sprites", "vfx", "vfx_guard")
        self.shield_anim = load_animation_folder(vfx_guard_path, "vfx_guard", 18, True, 1.3)
        
        self.anim_manager.play("idle")
        
        self.is_attacking = False
        self.is_dead = False
        
    def update(self, dt: float, tiles: list[pygame.FRect]):
        if self.invulnerable:
            self.invulnerability_timer -= dt
            if self.invulnerability_timer <= 0:
                self.invulnerable = False
                
        if self.dash_cooldown > 0:
            self.dash_cooldown -= dt
            
        # Update After-Images (Ghost trail)
        self.after_images = [img for img in self.after_images if img.update(dt)]
        
        # Update Dash State
        if self.is_dashing:
            self.dash_timer -= dt
            self.dash_ghost_timer += dt
            
            # Spawn ghost clone every 0.04s during dash
            if self.dash_ghost_timer >= 0.04:
                self.dash_ghost_timer = 0.0
                curr_img = self.anim_manager.get_current_frame()
                img_rect = curr_img.get_rect()
                draw_x = self.rect.centerx - img_rect.width / 2
                draw_y = self.rect.bottom - img_rect.height
                if not self.facing_right:
                    curr_img = pygame.transform.flip(curr_img, True, False)
                self.after_images.append(AfterImage(curr_img, draw_x, draw_y, self.facing_right))
                
            if self.dash_timer <= 0:
                self.is_dashing = False
                self.velocity.x *= 0.3
                
        # Update Whirlwind Tempest Skill State
        if self.is_casting_aoe:
            self.aoe_timer -= dt
            if self.anim_manager.is_finished("whirlwind") or self.aoe_timer <= 0:
                self.is_casting_aoe = False
                
        # Check if attack animation finished
        if self.is_attacking and self.anim_manager.is_finished("attack"):
            self.is_attacking = False
            
        # Update Impact Smokes (Plunge VFX)
        for s in self.impact_smokes[:]:
            s.update(dt)
            if not s.active:
                self.impact_smokes.remove(s)
                
        # Update Plunge landing recovery
        if self.is_landing_plunge:
            self.plunge_recovery -= dt
            if self.plunge_recovery <= 0:
                self.is_landing_plunge = False

        # Update Ultimate Skill State
        if self.is_casting_ultimate:
            self.ultimate_timer += dt
            self.invulnerable = True
            self.invulnerability_timer = 0.5
            
            # Spawn phantom blade slashes during phase 1 (0.30s to 1.15s)
            if 0.30 <= self.ultimate_timer <= 1.15 and random.random() < 0.65:
                angle = random.uniform(-0.6, 0.6)
                cx = self.rect.centerx + random.uniform(-70, 70)
                cy = self.rect.centery + random.uniform(-40, 30)
                length = random.uniform(150, 240)
                dx = math.cos(angle) * length
                dy = math.sin(angle) * length
                self.ultimate_slashes.append(UltimateSlash((cx - dx, cy - dy), (cx + dx, cy + dy)))
                
            # Ground shockwave at feet
            if self.ultimate_shockwave_active:
                self.ultimate_shockwave_anim.update(dt)
                self.ultimate_shockwave_timer -= dt
                if self.ultimate_shockwave_timer <= 0 or self.ultimate_shockwave_anim.finished:
                    self.ultimate_shockwave_active = False
                    
            if self.ultimate_timer >= 1.35:
                self.is_casting_ultimate = False
                
        # Update active Ultimate slashes
        for slash in self.ultimate_slashes[:]:
            if not slash.update(dt):
                self.ultimate_slashes.remove(slash)

        self._handle_input(dt)
        self._apply_physics(dt, tiles)
        self._update_animation(dt)
        self.anim_manager.update(dt)
        
    def get_attack_hitbox(self) -> pygame.FRect:
        """Returns the hitbox for the attack if currently attacking, else None."""
        if self.is_down_attacking:
            return pygame.FRect(self.rect.x - 12, self.rect.bottom - 10, self.rect.width + 24, 38)
            
        if not self.is_attacking:
            return None
        
        hitbox_width = 44
        hitbox_height = 54
        hitbox_y = self.rect.centery - hitbox_height / 2
        if self.facing_right:
            return pygame.FRect(self.rect.right, hitbox_y, hitbox_width, hitbox_height)
        else:
            return pygame.FRect(self.rect.left - hitbox_width, hitbox_y, hitbox_width, hitbox_height)
            
    def trigger_aoe_damage(self, enemies: list, camera = None):
        """Applies radial AoE damage to all enemies in range if casting AoE, Plunge landing, or Ultimate."""
        # 1. Whirlwind AoE Skill
        if self.is_casting_aoe and not self.aoe_hit_done:
            self.aoe_hit_done = True
            for e in enemies:
                if not e.is_dead:
                    dist = pygame.math.Vector2(e.rect.center).distance_to(pygame.math.Vector2(self.rect.center))
                    if dist <= self.aoe_radius:
                        e.take_damage(2)
                        # Knockback
                        e.velocity.y = -220
                        e.velocity.x = 260 if e.rect.centerx > self.rect.centerx else -260
                        
        # 2. Downward Plunge Ground Impact Shockwave
        if self.plunge_impact_pending:
            self.plunge_impact_pending = False
            if camera:
                camera.shake(8.5, 0.28)
            for e in enemies:
                if not e.is_dead:
                    dist = pygame.math.Vector2(e.rect.center).distance_to(pygame.math.Vector2(self.rect.centerx, self.rect.bottom))
                    if dist <= 135:
                        e.take_damage(2)
                        e.velocity.y = -260
                        e.velocity.x = 280 if e.rect.centerx > self.rect.centerx else -280
                        
        # 3. Direct mid-air hits while plunging down
        if self.is_down_attacking:
            down_hitbox = self.get_attack_hitbox()
            if down_hitbox:
                for e in enemies:
                    if not e.is_dead and e not in self.plunge_hit_enemies and down_hitbox.colliderect(e.rect):
                        self.plunge_hit_enemies.add(e)
                        e.take_damage(2)
                        e.velocity.y = -120
                        
        # 4. Ultimate Skill Screen-Clearing Devastation
        if self.is_casting_ultimate and not self.ultimate_hit_done and self.ultimate_timer >= 0.45:
            self.ultimate_hit_done = True
            if camera:
                camera.shake(16.0, 0.65)
            for e in enemies:
                if not e.is_dead:
                    dist = pygame.math.Vector2(e.rect.center).distance_to(pygame.math.Vector2(self.rect.center))
                    if dist <= 380:
                        e.take_damage(15) # Devastating Ultimate damage
                        e.velocity.y = -320
                        e.velocity.x = 350 if e.rect.centerx > self.rect.centerx else -350
        
    def _update_animation(self, dt: float):
        # Mana regeneration (slowed down to 2.5 MP per second)
        if self.mana < self.max_mana:
            self.mana = min(self.max_mana, self.mana + 2.5 * dt)
            
        if self.is_dead:
            self.anim_manager.play("dead")
        elif self.is_casting_ultimate:
            if self.ultimate_timer < 0.35:
                self.anim_manager.play("guard") # Gathering celestial power
            elif self.ultimate_timer < 0.95:
                self.anim_manager.play("whirlwind") # Blistering spin slashes
            else:
                self.anim_manager.play("heavy_slash") # Finisher downward cleave
        elif self.is_dashing:
            self.anim_manager.play("dash")
        elif self.is_down_attacking:
            self.anim_manager.play("jump_attack")
        elif self.is_landing_plunge:
            self.anim_manager.play("landing")
        elif self.is_casting_aoe:
            self.anim_manager.play("whirlwind")
        elif self.is_blocking:
            self.anim_manager.play("guard")
            self.shield_anim.update(dt)
        elif self.is_attacking:
            self.anim_manager.play("attack")
        elif not self.on_ground:
            if self.velocity.y < 0:
                self.anim_manager.play("jump")
            else:
                self.anim_manager.play("fall")
        elif abs(self.velocity.x) > 10:
            self.anim_manager.play("walk")
        else:
            self.anim_manager.play("idle")
            
    def _handle_input(self, dt: float):
        if self.is_dead:
            self.velocity.x *= FRICTION
            if abs(self.velocity.x) < 5:
                self.velocity.x = 0
            return
            
        # Lock controls during ground impact recovery of plunge attack or Ultimate casting
        if self.is_landing_plunge or self.is_casting_ultimate:
            self.velocity.x = 0
            return
            
        # Aerial Downward Plunge Attack [J while airborne]
        if not self.on_ground and INPUT.is_action_just_pressed("ATTACK") and not self.is_dashing and not self.is_down_attacking and not self.is_blocking:
            self.is_down_attacking = True
            self.is_attacking = False
            self.velocity.x = 0
            self.velocity.y = 850 # High speed downward dive
            self.anim_manager.play("jump_attack", force_reset=True)
            self.plunge_hit_enemies.clear()
            return
            
        if self.is_down_attacking:
            self.velocity.x = 0
            self.velocity.y = max(self.velocity.y, 850)
            return

        # Ultimate Skill [R] - Devastating Celestial Cleave (costs 100 MP)
        if INPUT.is_action_just_pressed("ULTIMATE") and not self.is_attacking and not self.is_blocking and not self.is_dashing:
            if self.mana >= 100:
                self.mana = 0.0 # Drains all mana
                self.is_casting_ultimate = True
                self.ultimate_timer = 0.0
                self.ultimate_hit_done = False
                self.velocity.x = 0
                self.anim_manager.play("guard", force_reset=True)
                self.ultimate_shockwave_active = True
                self.ultimate_shockwave_pos = (self.rect.centerx, self.rect.bottom)
                self.ultimate_shockwave_timer = 0.8
                self.ultimate_shockwave_anim.reset()
                return

        # Dash [Q] - Reduced stamina cost to 12 SP
        if INPUT.is_action_just_pressed("DASH") and not self.is_dashing and self.dash_cooldown <= 0 and self.stamina >= 12:
            self.stamina -= 12
            self.is_dashing = True
            self.dash_timer = self.dash_duration
            self.dash_cooldown = 0.45
            self.invulnerable = True
            self.invulnerability_timer = self.dash_duration + 0.1
            self.velocity.y = 0
            self.velocity.x = self.dash_speed if self.facing_right else -self.dash_speed
            self.anim_manager.play("dash", force_reset=True)
            return
            
        # If currently dashing, lock controls to maintain high-speed thrust
        if self.is_dashing:
            return
            
        # Whirlwind Tempest Skill [E]
        if INPUT.is_action_just_pressed("SKILL_AOE") and not self.is_casting_aoe and not self.is_attacking and not self.is_blocking:
            if self.mana >= 35:
                self.mana -= 35
                self.is_casting_aoe = True
                self.aoe_timer = 0.6
                self.aoe_hit_done = False
                self.anim_manager.play("whirlwind", force_reset=True)
                
        # Blocking [Shift] - Reduced stamina drain to 8 SP/s
        if INPUT.is_action_pressed("DEFEND") and self.stamina > 0:
            self.is_blocking = True
            self.stamina -= 8 * dt # Drain 8 stamina per second (reduced from 20)
            self.velocity.x = 0 # Cannot move while blocking
            return # Skip other inputs
        else:
            self.is_blocking = False
            # Regenerate stamina slowly
            self.stamina = min(100.0, self.stamina + 8 * dt)
            
        if self.is_attacking:
            # Stop horizontal movement while attacking on ground
            if self.on_ground:
                self.velocity.x *= FRICTION
                if abs(self.velocity.x) < 5:
                    self.velocity.x = 0
            return
            
        # Horizontal Movement
        axis = INPUT.get_axis()
        
        if axis.x != 0:
            self.velocity.x += axis.x * ACCELERATION * dt
            self.velocity.x = clamp(self.velocity.x, -MAX_SPEED, MAX_SPEED)
            self.facing_right = axis.x > 0
        else:
            # Apply friction
            self.velocity.x *= FRICTION
            if abs(self.velocity.x) < 5:
                self.velocity.x = 0
                
        # Jumping
        if INPUT.is_action_just_pressed("JUMP") and not self.is_blocking:
            if self.on_ground:
                self.velocity.y = JUMP_FORCE
                self.on_ground = False
                self.can_double_jump = True
            elif self.can_double_jump:
                self.velocity.y = JUMP_FORCE * 0.82
                self.can_double_jump = False
                
        # Ground Attack [J / X] - Consumes 8 stamina per swing!
        if INPUT.is_action_just_pressed("ATTACK") and not self.is_attacking and not self.is_blocking:
            if self.stamina >= 8:
                self.stamina -= 8
                self.is_attacking = True
                self.anim_manager.play("attack", force_reset=True)
            
        # Magic Projectile [K / C] - Costs 50 MP
        if INPUT.is_action_just_pressed("MAGIC") and not self.is_attacking and not self.is_blocking:
            if self.mana >= 50:
                self.mana -= 50
                from entities.projectile import Projectile
                proj_x = self.rect.right if self.facing_right else self.rect.left - 20
                proj_y = self.rect.centery - 10
                self.projectiles.append(Projectile(proj_x, proj_y, self.facing_right, is_enemy=False))
                
    def _apply_physics(self, dt: float, tiles: list[pygame.FRect]):
        if not self.is_dashing:
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
                    
                    # If was diving with plunge attack, plant sword in ground with shockwave!
                    if self.is_down_attacking:
                        self.is_down_attacking = False
                        self.is_landing_plunge = True
                        self.plunge_recovery = 0.35
                        self.plunge_impact_pending = True
                        self.anim_manager.play("landing", force_reset=True)
                        self.impact_smokes.append(ImpactSmoke(self.rect.left - 15, self.rect.bottom - 10))
                        self.impact_smokes.append(ImpactSmoke(self.rect.right + 15, self.rect.bottom - 10))
                        
                elif self.velocity.y < 0:
                    self.rect.top = tile.bottom
                self.pos.y = self.rect.y
                self.velocity.y = 0
                break
                
    def take_damage(self, amount: int):
        if self.is_blocking or self.is_dashing or self.is_casting_ultimate:
            return # 100% Blocked or Phased during Dash / Ultimate!
            
        if not self.invulnerable and not self.is_dead:
            self.health -= amount
            if self.health <= 0:
                self.health = 0
                self.is_dead = True
                self.velocity.y = -150
                self.velocity.x = -100 if self.facing_right else 100
                self.anim_manager.play("dead", force_reset=True)
            else:
                self.invulnerable = True
                self.invulnerability_timer = 1.0 # 1 second of i-frames
                self.velocity.y = -150
                self.velocity.x = -100 if self.facing_right else 100

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2 = pygame.math.Vector2(0, 0)):
        # 1. Draw Impact Smokes (Dust clouds on floor)
        for s in self.impact_smokes:
            s.draw(surface, camera_offset)
            
        # 2. Draw After-Images (Ghost trail)
        for ghost in self.after_images:
            ghost.draw(surface, camera_offset)
            
        # 3. Draw Subtle Celestial Ring when 100 MP (Ultimate Ready)
        if self.mana >= 100 and not self.is_dead and not self.is_casting_ultimate:
            pulse_rad = int(32 + 3 * math.sin(pygame.time.get_ticks() * 0.006))
            aura_surf = pygame.Surface((pulse_rad * 2, pulse_rad * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura_surf, (255, 220, 90, 20), (pulse_rad, pulse_rad), pulse_rad)
            pygame.draw.circle(aura_surf, (255, 240, 150, 45), (pulse_rad, pulse_rad), pulse_rad, width=2)
            surface.blit(aura_surf, (self.rect.centerx - camera_offset.x - pulse_rad, self.rect.centery - camera_offset.y - pulse_rad), special_flags=pygame.BLEND_RGBA_ADD)

        # 4. Ultimate Visual Sequence (Eclipse overlay & divine light beam)
        if self.is_casting_ultimate:
            gw, gh = surface.get_size()
            dark_surf = pygame.Surface((gw, gh), pygame.SRCALPHA)
            dark_alpha = 110 if self.ultimate_timer < 0.35 else max(0, int(110 * (1.0 - (self.ultimate_timer - 0.35) / 1.0)))
            dark_surf.fill((10, 6, 20, dark_alpha))
            surface.blit(dark_surf, (0, 0))
            
            # Soft vertical beam of divine radiance striking down to the ground
            if self.ultimate_timer < 0.65:
                beam_w = 46
                beam_h = max(10, min(gh, int(self.rect.bottom - camera_offset.y + 5)))
                beam_surf = pygame.Surface((beam_w, beam_h), pygame.SRCALPHA)
                beam_x = int(self.rect.centerx - camera_offset.x - beam_w // 2)
                pygame.draw.rect(beam_surf, (255, 235, 120, 35), (0, 0, beam_w, beam_h))
                pygame.draw.rect(beam_surf, (255, 255, 255, 75), (beam_w // 4, 0, beam_w // 2, beam_h))
                surface.blit(beam_surf, (beam_x, 0), special_flags=pygame.BLEND_RGBA_ADD)

        img = self.anim_manager.get_current_frame()
        
        # Calculate rendering position (+7 ground offset so feet touch ground squarely)
        img_rect = img.get_rect()
        draw_x = self.rect.centerx - camera_offset.x - img_rect.width / 2
        draw_y = self.rect.bottom - camera_offset.y - img_rect.height + 7
        
        if not self.facing_right:
            img = pygame.transform.flip(img, True, False)
            
        # Blink when invulnerable (unless dashing/ultimate)
        if self.is_dashing or self.is_casting_ultimate or not self.invulnerable or int(self.invulnerability_timer * 10) % 2 == 0:
            surface.blit(img, (draw_x, draw_y))
            
            # Draw magical shield effect in front of player when blocking
            if self.is_blocking:
                shield_frame = self.shield_anim.get_current_frame()
                if shield_frame:
                    if not self.facing_right:
                        shield_frame = pygame.transform.flip(shield_frame, True, False)
                    shield_rect = shield_frame.get_rect()
                    s_offset_x = 24 if self.facing_right else -24
                    s_x = self.rect.centerx - camera_offset.x + s_offset_x - shield_rect.width / 2
                    s_y = self.rect.centery - camera_offset.y - shield_rect.height / 2 + 7
                    surface.blit(shield_frame, (s_x, s_y))
                    
        # 5. Draw Ultimate Slashes across screen
        for slash in self.ultimate_slashes:
            slash.draw(surface, camera_offset)
            
        # 6. Draw Ultimate Ground Shockwave
        if self.is_casting_ultimate and self.ultimate_shockwave_active:
            sh_frame = self.ultimate_shockwave_anim.get_current_frame()
            if sh_frame:
                sh_r = sh_frame.get_rect(center=(self.ultimate_shockwave_pos[0] - camera_offset.x, self.ultimate_shockwave_pos[1] - camera_offset.y))
                surface.blit(sh_frame, sh_r)
