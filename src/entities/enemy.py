import pygame
import os
import math
import random
from config.constants import GRAVITY, MAX_FALL_SPEED
import engine.resource_manager as rm
from engine.animation import AnimationManager, load_animation_folder, load_spritesheet
from engine.v3.ai.neural_ai import NeuralTacticalAI
from entities.projectile import Projectile

# ─────────────────────────────────────────────────────────────────────────────
# Particle helpers
# ─────────────────────────────────────────────────────────────────────────────
class _Particle:
    """Generic ephemeral visual particle."""
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "radius", "gravity")
    def __init__(self, x, y, vx, vy, life, color, radius=2.0, gravity=0.0):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.color = color
        self.radius = radius
        self.gravity = gravity

    def update(self, dt):
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface, cam_x, cam_y):
        alpha = int(255 * max(0, self.life / self.max_life))
        r = max(1, int(self.radius * (self.life / self.max_life)))
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (r, r), r)
        surface.blit(s, (self.x - cam_x - r, self.y - cam_y - r))

# ─────────────────────────────────────────────────────────────────────────────
class Enemy:
    def __init__(self, x: float, y: float, width: float, height: float):
        self.pos = pygame.math.Vector2(x, y)
        self.velocity = pygame.math.Vector2(0, 0)
        self.rect = pygame.FRect(x, y, width, height)
        self.ground_y = self.rect.bottom
        
        self.health = 3
        self.is_dead = False
        self.facing_right = False
        self.on_ground = False
        
        self.anim_manager = AnimationManager()
        self.state = "IDLE"
        self.slow_timer = 0.0
        self.slow_factor = 1.0
        self.burn_timer = 0.0
        self.burn_dps = 3.0
        self.burn_tick = 0.0
        self.is_guarding = False
        self.guard_timer = 0.0
        self.is_dodging = False
        self.dodge_timer = 0.0
        self._guard_sparks: list[_Particle] = []

    def apply_burn(self, duration: float = 4.0, dps: float = 3.0):
        """Applies burning status effect from Ignis fire skills."""
        if not self.is_dead:
            self.burn_timer = max(self.burn_timer, duration)
            self.burn_dps = dps

    def apply_slow(self, duration: float = 2.5, factor: float = 0.25):
        """Applies slow-motion status effect from player Ultimate skill."""
        if not self.is_dead:
            self.slow_timer = max(self.slow_timer, duration)
            self.slow_factor = factor

    def update_burn(self, dt: float):
        if self.burn_timer > 0 and not self.is_dead:
            self.burn_timer -= dt
            self.burn_tick += dt
            if self.burn_tick >= 1.0:
                self.burn_tick = 0.0
                self.take_damage(int(self.burn_dps))

    def take_damage(self, amount: int, hit_direction: int = 0):
        if self.is_dead:
            return
            
        if self.is_dodging:
            return # Dodged evasively!
            
        if self.is_guarding:
            is_frontal = (hit_direction == 0) or (hit_direction > 0 and self.facing_right) or (hit_direction < 0 and not self.facing_right)
            if is_frontal:
                amount = max(1, int(amount * 0.25)) # Guard absorbs 75%
                sx = self.rect.right if self.facing_right else self.rect.left
                sy = self.rect.centery
                for _ in range(6):
                    self._guard_sparks.append(_Particle(sx, sy, random.uniform(-50, 50), random.uniform(-80, 10), 0.22, (255, 215, 80), radius=2.5, gravity=180))
            else:
                self.is_guarding = False # Flanked!
        
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
        if self.slow_timer > 0:
            self.slow_timer -= dt
            effective_dt = dt * self.slow_factor
        else:
            effective_dt = dt
            
        if self.dodge_timer > 0:
            self.dodge_timer -= effective_dt
            if self.dodge_timer <= 0:
                self.is_dodging = False
        if self.guard_timer > 0:
            self.guard_timer -= effective_dt
            if self.guard_timer <= 0:
                self.is_guarding = False
        self._guard_sparks = [p for p in self._guard_sparks if p.update(effective_dt)]
            
        # Apply Gravity
        self.velocity.y += GRAVITY * (self.slow_factor if self.slow_timer > 0 else 1.0)
        self.velocity.y = min(self.velocity.y, MAX_FALL_SPEED)
        
        # Move X
        self.pos.x += self.velocity.x * effective_dt
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
        self.pos.y += self.velocity.y * effective_dt
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

        if self.on_ground:
            self.ground_y = self.rect.bottom
        else:
            floor_below = None
            for tile in tiles:
                if tile.left < self.rect.centerx < tile.right and tile.top >= self.rect.bottom - 4:
                    if floor_below is None or tile.top < floor_below:
                        floor_below = tile.top
            if floor_below is not None:
                self.ground_y = floor_below

    def update(self, dt: float, tiles: list[pygame.FRect], player):
        pass

    def draw_contact_shadow(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2, width: int = None, height: int = None, alpha: int = 125):
        """Renders grounded dual-layer contact drop shadow anchored to foot pivot."""
        if self.is_dead:
            return
        ground_y = getattr(self, "ground_y", self.rect.bottom)
        air_height = max(0, ground_y - self.rect.bottom)
        scale = max(0.4, 1.0 - air_height / 250.0)
        sw = int((width if width is not None else max(44, int(self.rect.width * 1.25))) * scale)
        sh = int((height if height is not None else 12) * scale)
        a = int(alpha * scale)
        if sw > 2 and sh > 2 and a > 0:
            shadow_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
            # Outer soft falloff
            pygame.draw.ellipse(shadow_surf, (0, 0, 0, a), (0, 0, sw, sh))
            # Inner dark contact core
            core_w, core_h = max(2, int(sw * 0.62)), max(2, int(sh * 0.62))
            pygame.draw.ellipse(shadow_surf, (0, 0, 0, min(255, int(a * 1.35))), ((sw - core_w) // 2, (sh - core_h) // 2, core_w, core_h))
            surface.blit(shadow_surf, (self.rect.centerx - camera_offset.x - sw // 2, ground_y - camera_offset.y - sh // 2 + 1))

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if self.is_dead and self.anim_manager.is_finished("dead"):
            return # Don't draw if fully dead (or could draw last frame)

        # Draw soft contact drop shadow under feet (Grounded presence)
        self.draw_contact_shadow(surface, camera_offset)

        img = self.anim_manager.get_current_frame()
        img_rect = img.get_rect()
            
        draw_x = self.rect.centerx - camera_offset.x - img_rect.width / 2
        draw_y = self.rect.bottom - camera_offset.y - img_rect.height
        
        if not self.facing_right:
            img = pygame.transform.flip(img, True, False)
            
        # Draw icy tint when slowed
        if self.slow_timer > 0 and not self.is_dead:
            tinted = img.copy()
            tinted.fill((130, 205, 255), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(tinted, (draw_x, draw_y))
        else:
            surface.blit(img, (draw_x, draw_y))
            
        # Draw Guard Shield if active
        if self.is_guarding and not self.is_dead:
            bx = (self.rect.right - camera_offset.x + 2) if self.facing_right else (self.rect.left - camera_offset.x - 12)
            by = self.rect.centery - camera_offset.y - 20
            bs = pygame.Surface((10, 42), pygame.SRCALPHA)
            pygame.draw.rect(bs, (240, 230, 200, 220), (0, 0, 10, 42), border_radius=3)
            pygame.draw.rect(bs, (255, 215, 80), (0, 0, 10, 42), 1, border_radius=3)
            surface.blit(bs, (bx, by))
            
        for spk in self._guard_sparks:
            spk.draw(surface, camera_offset.x, camera_offset.y)


# ─────────────────────────────────────────────────────────────────────────────
class SkeletonWarrior(Enemy):
    """
    Elite Skeleton Swordsman using newly implemented Craftpix sprite sheets.
    Features 3-hit melee sword combos, charging run-attacks, and defensive shield guards.
    Scaled to 1.33x (80px height) to match protagonist Ignis scale.
    """
    def __init__(self, x: float, y: float):
        super().__init__(x, y, 36, 80)
        self.health = 160
        self.attack_damage = 22
        self.touch_damage = 5
        self.speed = 50.0
        self.chase_speed = 95.0
        self.vision_range = 380.0
        self.attack_range = 65.0
        
        scale = 1.33
        base_path = os.path.join("assets", "sprites", "enemies", "skeleton_warrior")
        self.anim_manager.add_animation("idle", load_spritesheet(os.path.join(base_path, "Idle.png"), 128, 128, fps=8, loop=True, scale=scale))
        self.anim_manager.add_animation("walk", load_spritesheet(os.path.join(base_path, "Walk.png"), 128, 128, fps=8, loop=True, scale=scale))
        self.anim_manager.add_animation("run", load_spritesheet(os.path.join(base_path, "Run.png"), 128, 128, fps=10, loop=True, scale=scale))
        self.anim_manager.add_animation("attack", load_spritesheet(os.path.join(base_path, "Attack_1.png"), 128, 128, fps=10, loop=False, scale=scale))
        self.anim_manager.add_animation("attack2", load_spritesheet(os.path.join(base_path, "Attack_2.png"), 128, 128, fps=11, loop=False, scale=scale))
        self.anim_manager.add_animation("attack3", load_spritesheet(os.path.join(base_path, "Attack_3.png"), 128, 128, fps=9, loop=False, scale=scale))
        self.anim_manager.add_animation("run_attack", load_spritesheet(os.path.join(base_path, "Run+attack.png"), 128, 128, fps=11, loop=False, scale=scale))
        self.anim_manager.add_animation("protect", load_spritesheet(os.path.join(base_path, "Protect.png"), 128, 128, fps=6, loop=True, scale=scale))
        self.anim_manager.add_animation("hurt", load_spritesheet(os.path.join(base_path, "Hurt.png"), 128, 128, fps=10, loop=False, scale=scale))
        self.anim_manager.add_animation("dead", load_spritesheet(os.path.join(base_path, "Dead.png"), 128, 128, fps=8, loop=False, scale=scale))
        
        self.anim_manager.play("idle")
        
        self.state_timer = 0.0
        self.patrol_dir = -1
        self.neural_ai = NeuralTacticalAI(entity_type="enemy", difficulty_scale=0.85)
        self.neural_eval_timer = random.uniform(0.0, 0.25)
        self.dodge_cooldown = 0.0
        self.guard_cooldown = 0.0
        self.combo_step = 1
        
        self._time = 0.0
        self._slash_timer = 0.0
        self._slash_dir = 1
        self._particles: list[_Particle] = []

    def _spawn_slash_particles(self):
        tip_x = self.rect.right + 12 if self.facing_right else self.rect.left - 12
        tip_y = self.rect.centery - 5
        for _ in range(7):
            angle = random.uniform(-0.6, 0.6) + (0 if self.facing_right else math.pi)
            speed = random.uniform(60, 130)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - 25
            color = random.choice([(255, 60, 30), (255, 140, 40), (255, 210, 80)])
            self._particles.append(_Particle(tip_x, tip_y, vx, vy, random.uniform(0.18, 0.35), color, radius=random.uniform(1.5, 3.0), gravity=260))

    def change_state(self, new_state: str):
        super().change_state(new_state)
        self.state_timer = 0.0
        
        if self.state == "IDLE":
            self.velocity.x = 0
            self.anim_manager.play("idle")
            self.state_timer = random.uniform(0.6, 1.8)
        elif self.state == "PATROL":
            self.anim_manager.play("walk")
            self.state_timer = random.uniform(1.5, 3.0)
            self.patrol_dir = random.choice([-1, 1])
            self.facing_right = self.patrol_dir > 0
        elif self.state == "CHASE":
            self.anim_manager.play("run")
        elif self.state == "PROTECT":
            self.velocity.x = 0
            self.is_guarding = True
            self.guard_timer = 0.65
            self.guard_cooldown = 2.5
            self.anim_manager.play("protect", force_reset=True)
        elif self.state in ("ATTACK", "ATTACK2", "ATTACK3", "RUN_ATTACK"):
            self.is_guarding = False
            if self.state == "RUN_ATTACK":
                self.velocity.x = 110.0 if self.facing_right else -110.0
                self.anim_manager.play("run_attack", force_reset=True)
            elif self.state == "ATTACK2":
                self.velocity.x = 40.0 if self.facing_right else -40.0
                self.anim_manager.play("attack2", force_reset=True)
            elif self.state == "ATTACK3":
                self.velocity.x = 60.0 if self.facing_right else -60.0
                self.anim_manager.play("attack3", force_reset=True)
            else:
                self.velocity.x = 50.0 if self.facing_right else -50.0
                self.anim_manager.play("attack", force_reset=True)
        elif self.state == "HURT":
            self.is_guarding = False
            self.velocity.x = -40 if self.facing_right else 40
            self.anim_manager.play("hurt", force_reset=True)
        elif self.state == "DEAD":
            self.is_guarding = False
            self.velocity.x = 0
            self.anim_manager.play("dead", force_reset=True)

    def get_attack_hitbox(self) -> pygame.FRect:
        if self.state not in ("ATTACK", "ATTACK2", "ATTACK3", "RUN_ATTACK"):
            return None
            
        cur_anim = self.anim_manager.animations.get(self.anim_manager.current_state)
        if not cur_anim:
            return None
        cf = cur_anim.current_frame
        
        hit_w, hit_h = 56, 64
        is_active = False
        if self.state == "ATTACK" and 2 <= cf <= 3:
            is_active = True
        elif self.state == "ATTACK2" and 2 <= cf <= 4:
            hit_w = 64
            is_active = True
        elif self.state == "ATTACK3" and 2 <= cf <= 3:
            hit_w, hit_h = 70, 70
            is_active = True
        elif self.state == "RUN_ATTACK" and 3 <= cf <= 5:
            hit_w = 64
            is_active = True
            
        if not is_active:
            return None
            
        hitbox_y = self.rect.centery - hit_h / 2
        if self.facing_right:
            return pygame.FRect(self.rect.right, hitbox_y, hit_w, hit_h)
        else:
            return pygame.FRect(self.rect.left - hit_w, hitbox_y, hit_w, hit_h)

    def update(self, dt: float, tiles: list[pygame.FRect], player):
        self._time += dt
        self.update_burn(dt)
        if self.guard_cooldown > 0:
            self.guard_cooldown -= dt
        if self._slash_timer > 0:
            self._slash_timer -= dt

        if not self.is_dead:
            self.state_timer -= dt
            dist_to_player = player.rect.centerx - self.rect.centerx
            abs_dist = abs(dist_to_player)
            player_in_range = abs_dist < self.vision_range and abs(player.rect.centery - self.rect.centery) < 130
            
            if self.is_guarding:
                self.guard_timer -= dt
                if self.guard_timer <= 0:
                    self.is_guarding = False
                    self.change_state("IDLE")
            elif self.state == "HURT":
                if self.anim_manager.is_finished("hurt"):
                    self.change_state("IDLE")
            elif self.state in ("ATTACK", "ATTACK2", "ATTACK3", "RUN_ATTACK"):
                self.velocity.x *= 0.88
                cur_anim_name = self.anim_manager.current_state
                cur_anim = self.anim_manager.animations.get(cur_anim_name)
                if cur_anim and cur_anim.current_frame == 2 and self._slash_timer <= 0:
                    self._slash_timer = 0.16
                    self._spawn_slash_particles()
                if self.anim_manager.is_finished(cur_anim_name):
                    # Possibility to chain attack
                    if abs_dist <= self.attack_range and random.random() < 0.45:
                        if cur_anim_name == "ATTACK":
                            self.change_state("ATTACK2")
                        elif cur_anim_name == "ATTACK2":
                            self.change_state("ATTACK3")
                        else:
                            self.change_state("IDLE")
                    else:
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
                else:
                    self.facing_right = dist_to_player > 0
                    # Check defensive guard trigger against incoming player attacks
                    if getattr(player, "is_attacking", False) and abs_dist < 85 and self.guard_cooldown <= 0 and random.random() < 0.35:
                        self.change_state("PROTECT")
                    elif abs_dist <= self.attack_range:
                        self.change_state("ATTACK")
                    elif 100 < abs_dist < 180 and random.random() < 0.18:
                        self.change_state("RUN_ATTACK")
                    else:
                        self.velocity.x = self.chase_speed if self.facing_right else -self.chase_speed

        self._apply_physics(dt, tiles)
        anim_dt = dt * (self.slow_factor if self.slow_timer > 0 else 1.0)
        self.anim_manager.update(anim_dt)
        self._particles = [p for p in self._particles if p.update(dt)]

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if self.is_dead and self.anim_manager.is_finished("dead"):
            return

        self.draw_contact_shadow(surface, camera_offset, width=46, height=12)

        cam_x, cam_y = camera_offset.x, camera_offset.y
        img = self.anim_manager.get_current_frame()
        draw_x = self.rect.centerx - cam_x - 85
        draw_y = self.rect.bottom - cam_y - 170

        if not self.facing_right:
            img = pygame.transform.flip(img, True, False)

        if self.slow_timer > 0 and not self.is_dead:
            tinted = img.copy()
            tinted.fill((130, 205, 255), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(tinted, (draw_x, draw_y))
        else:
            surface.blit(img, (draw_x, draw_y))

        for p in self._particles:
            p.draw(surface, cam_x, cam_y)
        for spk in self._guard_sparks:
            spk.draw(surface, cam_x, cam_y)


# ─────────────────────────────────────────────────────────────────────────────
class SkeletonSpearman(Enemy):
    """
    Skeleton Spearman with exceptional forward melee reach (~140px).
    Keeps players at bay with thrusting combos and braced spear stance.
    Scaled to 1.33x (80px height) to match protagonist Ignis scale.
    """
    def __init__(self, x: float, y: float):
        super().__init__(x, y, 36, 80)
        self.health = 180
        self.attack_damage = 25
        self.touch_damage = 5
        self.speed = 45.0
        self.chase_speed = 85.0
        self.vision_range = 400.0
        self.attack_range = 135.0 # Extended spear reach
        
        scale = 1.33
        base_path = os.path.join("assets", "sprites", "enemies", "skeleton_spearman")
        self.anim_manager.add_animation("idle", load_spritesheet(os.path.join(base_path, "Idle.png"), 128, 128, fps=8, loop=True, scale=scale))
        self.anim_manager.add_animation("walk", load_spritesheet(os.path.join(base_path, "Walk.png"), 128, 128, fps=8, loop=True, scale=scale))
        self.anim_manager.add_animation("run", load_spritesheet(os.path.join(base_path, "Run.png"), 128, 128, fps=10, loop=True, scale=scale))
        self.anim_manager.add_animation("attack", load_spritesheet(os.path.join(base_path, "Attack_1.png"), 128, 128, fps=8, loop=False, scale=scale))
        self.anim_manager.add_animation("attack2", load_spritesheet(os.path.join(base_path, "Attack_2.png"), 128, 128, fps=9, loop=False, scale=scale))
        self.anim_manager.add_animation("run_attack", load_spritesheet(os.path.join(base_path, "Run+attack.png"), 128, 128, fps=10, loop=False, scale=scale))
        self.anim_manager.add_animation("protect", load_spritesheet(os.path.join(base_path, "Protect.png"), 128, 128, fps=6, loop=True, scale=scale))
        self.anim_manager.add_animation("hurt", load_spritesheet(os.path.join(base_path, "Hurt.png"), 128, 128, fps=10, loop=False, scale=scale))
        self.anim_manager.add_animation("dead", load_spritesheet(os.path.join(base_path, "Dead.png"), 128, 128, fps=8, loop=False, scale=scale))
        
        self.anim_manager.play("idle")
        self.state_timer = 0.0
        self.patrol_dir = -1
        self.guard_cooldown = 0.0
        self._thrust_sparks: list[_Particle] = []

    def change_state(self, new_state: str):
        super().change_state(new_state)
        self.state_timer = 0.0
        
        if self.state == "IDLE":
            self.velocity.x = 0
            self.anim_manager.play("idle")
            self.state_timer = random.uniform(0.8, 2.0)
        elif self.state == "PATROL":
            self.anim_manager.play("walk")
            self.state_timer = random.uniform(1.8, 3.2)
            self.patrol_dir = random.choice([-1, 1])
            self.facing_right = self.patrol_dir > 0
        elif self.state == "CHASE":
            self.anim_manager.play("run")
        elif self.state == "PROTECT":
            self.velocity.x = 0
            self.is_guarding = True
            self.guard_timer = 0.70
            self.guard_cooldown = 3.0
            self.anim_manager.play("protect", force_reset=True)
        elif self.state in ("ATTACK", "ATTACK2", "RUN_ATTACK"):
            self.is_guarding = False
            if self.state == "RUN_ATTACK":
                self.velocity.x = 100.0 if self.facing_right else -100.0
                self.anim_manager.play("run_attack", force_reset=True)
            elif self.state == "ATTACK2":
                self.velocity.x = 30.0 if self.facing_right else -30.0
                self.anim_manager.play("attack2", force_reset=True)
            else:
                self.velocity.x = 40.0 if self.facing_right else -40.0
                self.anim_manager.play("attack", force_reset=True)
        elif self.state == "HURT":
            self.is_guarding = False
            self.velocity.x = -40 if self.facing_right else 40
            self.anim_manager.play("hurt", force_reset=True)
        elif self.state == "DEAD":
            self.is_guarding = False
            self.velocity.x = 0
            self.anim_manager.play("dead", force_reset=True)

    def get_attack_hitbox(self) -> pygame.FRect:
        if self.state not in ("ATTACK", "ATTACK2", "RUN_ATTACK"):
            return None
        cur_anim = self.anim_manager.animations.get(self.anim_manager.current_state)
        if not cur_anim:
            return None
        cf = cur_anim.current_frame
        
        hit_w, hit_h = 106, 46
        is_active = False
        if self.state == "ATTACK" and 1 <= cf <= 3:
            hit_w = 112
            is_active = True
        elif self.state == "ATTACK2" and 1 <= cf <= 3:
            hit_w, hit_h = 86, 64
            is_active = True
        elif self.state == "RUN_ATTACK" and 2 <= cf <= 4:
            hit_w = 106
            is_active = True
            
        if not is_active:
            return None
            
        hitbox_y = self.rect.centery - hit_h / 2
        if self.facing_right:
            return pygame.FRect(self.rect.right, hitbox_y, hit_w, hit_h)
        else:
            return pygame.FRect(self.rect.left - hit_w, hitbox_y, hit_w, hit_h)

    def update(self, dt: float, tiles: list[pygame.FRect], player):
        self.update_burn(dt)
        if self.guard_cooldown > 0:
            self.guard_cooldown -= dt

        if not self.is_dead:
            self.state_timer -= dt
            dist_to_player = player.rect.centerx - self.rect.centerx
            abs_dist = abs(dist_to_player)
            player_in_range = abs_dist < self.vision_range and abs(player.rect.centery - self.rect.centery) < 130
            
            if self.is_guarding:
                self.guard_timer -= dt
                if self.guard_timer <= 0:
                    self.is_guarding = False
                    self.change_state("IDLE")
            elif self.state == "HURT":
                if self.anim_manager.is_finished("hurt"):
                    self.change_state("IDLE")
            elif self.state in ("ATTACK", "ATTACK2", "RUN_ATTACK"):
                self.velocity.x *= 0.86
                cur_name = self.anim_manager.current_state
                if self.anim_manager.is_finished(cur_name):
                    if abs_dist <= self.attack_range and cur_name == "ATTACK" and random.random() < 0.4:
                        self.change_state("ATTACK2")
                    else:
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
                else:
                    self.facing_right = dist_to_player > 0
                    if getattr(player, "is_attacking", False) and abs_dist < 110 and self.guard_cooldown <= 0 and random.random() < 0.35:
                        self.change_state("PROTECT")
                    elif abs_dist <= self.attack_range:
                        self.change_state("ATTACK")
                    elif 120 < abs_dist < 200 and random.random() < 0.2:
                        self.change_state("RUN_ATTACK")
                    else:
                        self.velocity.x = self.chase_speed if self.facing_right else -self.chase_speed

        self._apply_physics(dt, tiles)
        anim_dt = dt * (self.slow_factor if self.slow_timer > 0 else 1.0)
        self.anim_manager.update(anim_dt)
        self._thrust_sparks = [p for p in self._thrust_sparks if p.update(dt)]

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if self.is_dead and self.anim_manager.is_finished("dead"):
            return

        self.draw_contact_shadow(surface, camera_offset, width=48, height=13)

        cam_x, cam_y = camera_offset.x, camera_offset.y
        img = self.anim_manager.get_current_frame()
        draw_x = self.rect.centerx - cam_x - 85
        draw_y = self.rect.bottom - cam_y - 170

        if not self.facing_right:
            img = pygame.transform.flip(img, True, False)

        if self.slow_timer > 0 and not self.is_dead:
            tinted = img.copy()
            tinted.fill((130, 205, 255), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(tinted, (draw_x, draw_y))
        else:
            surface.blit(img, (draw_x, draw_y))

        for p in self._thrust_sparks:
            p.draw(surface, cam_x, cam_y)
        for spk in self._guard_sparks:
            spk.draw(surface, cam_x, cam_y)


# ─────────────────────────────────────────────────────────────────────────────
class SkeletonArcher(Enemy):
    """
    Ranged Skeleton Archer. Fires bow arrows at long range, leaps backwards
    with acrobatic evasion when players close in, and uses dagger defense.
    Scaled to 1.33x (80px height) to match protagonist Ignis scale.
    """
    def __init__(self, x: float, y: float):
        super().__init__(x, y, 34, 80)
        self.health = 130
        self.attack_damage = 18
        self.touch_damage = 3
        self.speed = 45.0
        self.chase_speed = 70.0
        self.vision_range = 480.0
        self.attack_range = 420.0
        
        scale = 1.33
        base_path = os.path.join("assets", "sprites", "enemies", "skeleton_archer")
        self.anim_manager.add_animation("idle", load_spritesheet(os.path.join(base_path, "Idle.png"), 128, 128, fps=8, loop=True, scale=scale))
        self.anim_manager.add_animation("walk", load_spritesheet(os.path.join(base_path, "Walk.png"), 128, 128, fps=8, loop=True, scale=scale))
        self.anim_manager.add_animation("shot", load_spritesheet(os.path.join(base_path, "Shot_1.png"), 128, 128, fps=13, loop=False, scale=scale))
        self.anim_manager.add_animation("shot_fast", load_spritesheet(os.path.join(base_path, "Shot_2.png"), 128, 128, fps=15, loop=False, scale=scale))
        self.anim_manager.add_animation("evasion", load_spritesheet(os.path.join(base_path, "Evasion.png"), 128, 128, fps=12, loop=False, scale=scale))
        self.anim_manager.add_animation("attack", load_spritesheet(os.path.join(base_path, "Attack_1.png"), 128, 128, fps=10, loop=False, scale=scale))
        self.anim_manager.add_animation("hurt", load_spritesheet(os.path.join(base_path, "Hurt.png"), 128, 128, fps=10, loop=False, scale=scale))
        self.anim_manager.add_animation("dead", load_spritesheet(os.path.join(base_path, "Dead.png"), 128, 128, fps=8, loop=False, scale=scale))
        
        self.anim_manager.play("idle")
        self.state_timer = 0.0
        self.patrol_dir = -1
        self.evasion_cooldown = 0.0
        self.shot_cooldown = 1.2
        self.arrow_fired = False
        self.projectiles: list[Projectile] = []

    def change_state(self, new_state: str):
        super().change_state(new_state)
        self.state_timer = 0.0
        
        if self.state == "IDLE":
            self.velocity.x = 0
            self.anim_manager.play("idle")
            self.state_timer = random.uniform(0.6, 1.6)
        elif self.state == "PATROL":
            self.anim_manager.play("walk")
            self.state_timer = random.uniform(1.5, 3.0)
            self.patrol_dir = random.choice([-1, 1])
            self.facing_right = self.patrol_dir > 0
        elif self.state == "CHASE":
            self.anim_manager.play("walk")
        elif self.state == "EVASION":
            self.is_dodging = True
            self.evasion_cooldown = 3.0
            dodge_dir = -1 if self.facing_right else 1
            self.velocity.x = dodge_dir * 240.0
            self.velocity.y = -180.0
            self.anim_manager.play("evasion", force_reset=True)
        elif self.state == "SHOT":
            self.velocity.x = 0
            self.arrow_fired = False
            self.anim_manager.play("shot", force_reset=True)
        elif self.state == "SHOT_FAST":
            self.velocity.x = 0
            self.arrow_fired = False
            self.anim_manager.play("shot_fast", force_reset=True)
        elif self.state == "ATTACK":
            self.velocity.x = 25 if self.facing_right else -25
            self.anim_manager.play("attack", force_reset=True)
        elif self.state == "HURT":
            self.is_dodging = False
            self.velocity.x = -35 if self.facing_right else 35
            self.anim_manager.play("hurt", force_reset=True)
        elif self.state == "DEAD":
            self.is_dodging = False
            self.velocity.x = 0
            self.anim_manager.play("dead", force_reset=True)

    def get_attack_hitbox(self) -> pygame.FRect:
        if self.state != "ATTACK":
            return None
        cur_anim = self.anim_manager.animations.get("attack")
        if cur_anim and 2 <= cur_anim.current_frame <= 3:
            hit_w, hit_h = 48, 54
            hitbox_y = self.rect.centery - hit_h / 2
            if self.facing_right:
                return pygame.FRect(self.rect.right, hitbox_y, hit_w, hit_h)
            else:
                return pygame.FRect(self.rect.left - hit_w, hitbox_y, hit_w, hit_h)
        return None

    def _fire_arrow(self):
        arrow_x = self.rect.right + 14 if self.facing_right else self.rect.left - 14
        arrow_y = self.rect.centery - 10
        self.projectiles.append(Projectile(arrow_x, arrow_y, self.facing_right, is_enemy=True, projectile_type="arrow_fast", damage=18))

    def update(self, dt: float, tiles: list[pygame.FRect], player):
        self.update_burn(dt)
        if self.evasion_cooldown > 0:
            self.evasion_cooldown -= dt
        if self.shot_cooldown > 0:
            self.shot_cooldown -= dt

        if not self.is_dead:
            self.state_timer -= dt
            dist_to_player = player.rect.centerx - self.rect.centerx
            abs_dist = abs(dist_to_player)
            player_in_range = abs_dist < self.vision_range and abs(player.rect.centery - self.rect.centery) < 140

            if self.state == "EVASION":
                if self.anim_manager.is_finished("evasion") or self.on_ground and self.anim_manager.animations["evasion"].current_frame >= 4:
                    self.is_dodging = False
                    self.facing_right = dist_to_player > 0
                    self.change_state("SHOT_FAST")
            elif self.state == "HURT":
                if self.anim_manager.is_finished("hurt"):
                    self.change_state("IDLE")
            elif self.state in ("SHOT", "SHOT_FAST"):
                cur_anim = self.anim_manager.animations.get(self.anim_manager.current_state)
                target_frame = 9 if self.state == "SHOT" else 7
                if cur_anim and cur_anim.current_frame >= target_frame and not self.arrow_fired:
                    self.arrow_fired = True
                    self._fire_arrow()
                    self.shot_cooldown = 1.8
                if self.anim_manager.is_finished(self.anim_manager.current_state):
                    self.change_state("IDLE")
            elif self.state == "ATTACK":
                if self.anim_manager.is_finished("attack"):
                    self.change_state("IDLE")
            elif self.state == "IDLE":
                if player_in_range and not player.invulnerable:
                    if abs_dist < 85 and self.evasion_cooldown <= 0:
                        self.facing_right = dist_to_player > 0
                        self.change_state("EVASION")
                    elif abs_dist <= self.attack_range and self.shot_cooldown <= 0:
                        self.facing_right = dist_to_player > 0
                        self.change_state("SHOT")
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
                self.facing_right = dist_to_player > 0
                if abs_dist < 85 and self.evasion_cooldown <= 0:
                    self.change_state("EVASION")
                elif abs_dist < 50:
                    self.change_state("ATTACK")
                elif abs_dist <= self.attack_range and self.shot_cooldown <= 0:
                    self.change_state("SHOT")
                else:
                    if abs_dist < 180:
                        # Reposition away from player
                        flee_dir = -1 if dist_to_player > 0 else 1
                        self.velocity.x = self.speed * flee_dir
                    else:
                        chase_dir = 1 if dist_to_player > 0 else -1
                        self.velocity.x = self.chase_speed * chase_dir

        self._apply_physics(dt, tiles)
        anim_dt = dt * (self.slow_factor if self.slow_timer > 0 else 1.0)
        self.anim_manager.update(anim_dt)

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if self.is_dead and self.anim_manager.is_finished("dead"):
            return

        self.draw_contact_shadow(surface, camera_offset, width=44, height=12)

        cam_x, cam_y = camera_offset.x, camera_offset.y
        img = self.anim_manager.get_current_frame()
        draw_x = self.rect.centerx - cam_x - 85
        draw_y = self.rect.bottom - cam_y - 170

        if not self.facing_right:
            img = pygame.transform.flip(img, True, False)

        if self.slow_timer > 0 and not self.is_dead:
            tinted = img.copy()
            tinted.fill((130, 205, 255), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(tinted, (draw_x, draw_y))
        else:
            surface.blit(img, (draw_x, draw_y))


# ─────────────────────────────────────────────────────────────────────────────
class Skeleton(SkeletonWarrior):
    """Backwards compatibility alias for SkeletonWarrior."""
    pass



# ─────────────────────────────────────────────────────────────────────────────
class MageSkeleton(Skeleton):
    def __init__(self, x: float, y: float):
        super().__init__(x, y)
        self.health = 60 # Reescalado para novo balanceamento tático (2x)
        self.attack_damage = 12 # Projétil mágico contínuo
        self.touch_damage = 3
        # Different AI parameters for ranged (deliberate caster pacing)
        self.speed = 40.0
        self.chase_speed = 60.0
        self.vision_range = 500.0
        self.attack_range = 350.0
        
        self.projectiles = []
        self.attack_cooldown = 0.0

        # ── VFX: runic cast circle ─────────────────────────────────────────
        self._cast_charge = 0.0        # 0 → 1 progress during ATTACK windup
        self._cast_active = False
        self._rune_angle = 0.0         # spinning rune ring
        self._cast_particles: list[_Particle] = []
        self._float_phase = random.uniform(0, math.pi * 2)  # unique float offset
        self._float_offset = 0.0       # vertical levitation offset applied in draw
        
    def _spawn_cast_particles(self):
        """Emit void/arcane sparks during cast charge."""
        hx = self.rect.right if self.facing_right else self.rect.left
        hy = self.rect.centery - 8
        for _ in range(4):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(20, 55)
            color = random.choice([(180, 40, 255), (220, 100, 255), (90, 0, 180)])
            self._cast_particles.append(_Particle(hx, hy, math.cos(angle) * speed, math.sin(angle) * speed - 15,
                                                  random.uniform(0.25, 0.5), color, radius=2.0, gravity=100))

    def _draw_cast_circle(self, surface, cx, cy, cam_x, cam_y):
        """Draw a spinning runic circle at staff/hand when casting."""
        if not self._cast_active or self._cast_charge <= 0:
            return

        radius = int(14 + self._cast_charge * 18)
        alpha_scale = min(1.0, max(0.0, self._cast_charge * 2))
        alpha_base = max(0, min(255, int(160 * alpha_scale)))

        tip_x = (cx + 16 * (1 if self.facing_right else -1)) - cam_x
        tip_y = cy - cam_y - 10

        # Outer spinning ring
        ring_surf = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
        rc = radius + 4
        for i, (rr, col_alpha) in enumerate([(radius, alpha_base), (radius - 3, alpha_base // 2)]):
            c_alpha = max(0, min(255, int(col_alpha)))
            col = (200 - i * 40, 30 + i * 20, 255, c_alpha)
            if rr > 0:
                pygame.draw.circle(ring_surf, col, (rc, rc), rr, 2)

        # Spinning rune spokes
        spoke_alpha = max(0, min(255, alpha_base // 2))
        for i in range(6):
            angle = self._rune_angle + i * (math.pi / 3)
            sx = rc + int(math.cos(angle) * radius)
            sy = rc + int(math.sin(angle) * radius)
            ex = rc + int(math.cos(angle + math.pi) * (radius // 2))
            ey = rc + int(math.sin(angle + math.pi) * (radius // 2))
            pygame.draw.line(ring_surf, (220, 100, 255, spoke_alpha), (sx, sy), (ex, ey), 1)

        surface.blit(ring_surf, (tip_x - rc, tip_y - rc))

        # Inner glow pulse
        pulse = 0.5 + 0.5 * math.sin(self._cast_charge * math.pi * 4)
        if radius > 4:
            glow_s = pygame.Surface((radius, radius), pygame.SRCALPHA)
            inner_alpha = max(0, min(255, int(80 * pulse * alpha_scale)))
            pygame.draw.circle(glow_s, (200, 80, 255, inner_alpha),
                               (radius // 2, radius // 2), radius // 2)
            surface.blit(glow_s, (tip_x - radius // 2, tip_y - radius // 2))

    def _draw_shoot_flash(self, surface, cx, cy, cam_x, cam_y, alpha):
        """Arcane flash burst at the moment of firing."""
        tip_x = (cx + 20 * (1 if self.facing_right else -1)) - cam_x
        tip_y = cy - cam_y - 8
        burst_r = 14
        alpha = max(0, min(255, int(alpha)))
        bs = pygame.Surface((burst_r * 2, burst_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(bs, (255, 150, 255, alpha), (burst_r, burst_r), burst_r)
        pygame.draw.circle(bs, (255, 255, 255, max(0, min(255, alpha // 2))), (burst_r, burst_r), burst_r // 2)
        surface.blit(bs, (tip_x - burst_r, tip_y - burst_r))

    def update(self, dt: float, tiles: list[pygame.FRect], player):
        self._time += dt
        self.update_burn(dt)
        self._rune_angle += dt * 2.8  # spin rune ring

        # Levitation: smooth sinusoidal bob
        self._float_offset = math.sin(self._time * 2.8 + self._float_phase) * 3.5

        if self._cast_active:
            self._cast_charge = min(1.0, self._cast_charge + dt * 1.8)
            if random.random() < 0.35:
                self._spawn_cast_particles()

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
                    self._cast_active = False
                    self._cast_charge = 0.0
                    self.change_state("IDLE")
                # Shoot projectile at specific frame (e.g. frame 3)
                elif self.anim_manager.animations["attack"].current_frame == 3 and self.attack_cooldown <= 0:
                    from entities.projectile import Projectile
                    proj_x = self.rect.right if self.facing_right else self.rect.left - 16
                    proj_y = self.rect.centery
                    self.projectiles.append(Projectile(proj_x, proj_y, self.facing_right, is_enemy=True, projectile_type="mage_fireball"))
                    self.attack_cooldown = 1.8 # Cooldown
                    # Shoot flash particles
                    cx2 = self.rect.centerx
                    cy2 = self.rect.centery
                    for _ in range(12):
                        ang = random.uniform(0, math.pi * 2)
                        spd = random.uniform(50, 120)
                        col = random.choice([(230, 80, 255), (180, 50, 255), (255, 200, 255)])
                        self._cast_particles.append(_Particle(proj_x, proj_y, math.cos(ang)*spd, math.sin(ang)*spd,
                                                              0.22, col, radius=2.5, gravity=120))
            elif self.state == "IDLE":
                self._cast_active = False
                self._cast_charge = 0.0
                if player_in_range and not player.invulnerable:
                    if abs_dist <= self.attack_range and self.attack_cooldown <= 0:
                        self.facing_right = dist_to_player > 0
                        self.change_state("ATTACK")
                    else:
                        self.change_state("CHASE")
                elif self.state_timer <= 0:
                    self.change_state("PATROL")
            elif self.state == "PATROL":
                self._cast_active = False
                if player_in_range and not player.invulnerable:
                    self.change_state("CHASE")
                elif self.state_timer <= 0:
                    self.change_state("IDLE")
                else:
                    self.velocity.x = self.speed * self.patrol_dir
                    
            elif self.state == "CHASE":
                self._cast_active = False
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

        # Activate cast VFX when entering ATTACK
        if self.state == "ATTACK" and not self._cast_active:
            self._cast_active = True
            self._cast_charge = 0.0

        self._apply_physics(dt, tiles)
        anim_dt = dt * (self.slow_factor if self.slow_timer > 0 else 1.0)
        self.anim_manager.update(anim_dt)
        self._cast_particles = [p for p in self._cast_particles if p.update(dt)]
        
    def get_attack_hitbox(self) -> pygame.FRect:
        # Mage skeleton doesn't do melee damage
        return None

    def change_state(self, new_state: str):
        # Need to call Skeleton's change_state (not Enemy directly)
        Enemy.change_state(self, new_state)
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
            self.velocity.x = 0
            self.anim_manager.play("attack", force_reset=True)
        elif self.state == "HURT":
            self.velocity.x = 0
            self.anim_manager.play("hurt", force_reset=True)
        elif self.state == "DEAD":
            self.velocity.x = 0
            self.anim_manager.play("dead", force_reset=True)
        
    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if self.is_dead and self.anim_manager.is_finished("dead"):
            return

        # Mage floats, but its shadow stays anchored on the floor below
        self.draw_contact_shadow(surface, camera_offset, width=42, height=12, alpha=110)

        cam_x, cam_y = camera_offset.x, camera_offset.y
        img = self.anim_manager.get_current_frame()
        img_rect = img.get_rect()

        # Apply levitation float offset
        float_y = self._float_offset
        draw_x = self.rect.centerx - cam_x - img_rect.width / 2
        draw_y = self.rect.bottom - cam_y - img_rect.height + float_y
        cx, cy = self.rect.centerx, self.rect.centery + float_y

        if not self.facing_right:
            img = pygame.transform.flip(img, True, False)

        # Cast circle VFX (behind sprite)
        self._draw_cast_circle(surface, cx, cy, cam_x, cam_y)

        # Tint mage skeleton purple to distinguish; if slowed, tint icy cyan
        tinted = img.copy()
        if self.slow_timer > 0 and not self.is_dead:
            tinted.fill((120, 190, 255), special_flags=pygame.BLEND_RGBA_MULT)
        else:
            tinted.fill((200, 100, 255), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(tinted, (draw_x, draw_y))

        # Shoot flash (on fire frame)
        if self.state == "ATTACK" and self.anim_manager.animations["attack"].current_frame == 3:
            self._draw_shoot_flash(surface, cx, cy, cam_x, cam_y, 180)

        # Casting particles (arcane sparks)
        for p in self._cast_particles:
            p.draw(surface, cam_x, cam_y)


# ─────────────────────────────────────────────────────────────────────────────
class WildBoar(Enemy):
    """Charging Beast from Legacy-Fantasy that rushes at Arani upon seeing her."""
    def __init__(self, x: float, y: float):
        super().__init__(x, y, 46, 38)
        self.health = 1200 # Reescalado para mini-tank tático (2x)
        self.attack_damage = 45 # Investida pesada telegrafada
        self.touch_damage = 10
        
        boar_base = os.path.join("Legacy-Fantasy - High Forest 2.3", "Mob", "Boar")
        from engine.animation import load_spritesheet
        scale = 1.35
        
        idle_path = os.path.join(boar_base, "Idle", "Idle-Sheet.png")
        walk_path = os.path.join(boar_base, "Walk", "Walk-Base-Sheet.png")
        run_path = os.path.join(boar_base, "Run", "Run-Sheet.png")
        hit_path = os.path.join(boar_base, "Hit-Vanish", "Hit-Sheet.png")
        
        self.anim_manager.add_animation("idle", load_spritesheet(idle_path, 48, 32, fps=8, loop=True, scale=scale))
        self.anim_manager.add_animation("walk", load_spritesheet(walk_path, 48, 32, fps=7, loop=True, scale=scale))
        self.anim_manager.add_animation("run", load_spritesheet(run_path, 48, 32, fps=9, loop=True, scale=scale))
        self.anim_manager.add_animation("hurt", load_spritesheet(hit_path, 48, 32, fps=12, loop=False, scale=scale))
        self.anim_manager.add_animation("dead", load_spritesheet(hit_path, 48, 32, fps=10, loop=False, scale=scale))
        
        self.anim_manager.play("idle")
        
        self.speed = 35.0
        self.charge_speed = 135.0
        self.vision_range = 450.0
        self.state_timer = 0.0
        self.patrol_dir = -1
        self.scrape_timer = 0.0 # Telegraphed paw scrape before charge
        self.dust_particles: list[_Particle] = []
        
    def _spawn_dust(self):
        px = self.rect.centerx + (-12 if self.facing_right else 12)
        py = self.rect.bottom - 4
        for _ in range(3):
            vx = random.uniform(-40, -10) if self.facing_right else random.uniform(10, 40)
            vy = random.uniform(-25, -5)
            col = random.choice([(140, 120, 90), (180, 160, 120), (110, 90, 70)])
            self.dust_particles.append(_Particle(px, py, vx, vy, random.uniform(0.2, 0.4), col, radius=random.uniform(2, 4), gravity=80))

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
        elif self.state == "WINDUP":
            self.velocity.x = 0
            self.scrape_timer = 0.6 # Raspa a pata no chão por 0.6s
            self.anim_manager.play("idle")
        elif self.state == "CHARGE":
            self.anim_manager.play("run")
        elif self.state == "HURT":
            self.velocity.x = -60 if self.facing_right else 60
            self.anim_manager.play("hurt", force_reset=True)
        elif self.state == "DEAD":
            self.velocity.x = 0
            self.anim_manager.play("dead", force_reset=True)
            
    def update(self, dt: float, tiles: list[pygame.FRect], player):
        self.update_burn(dt)
        self.dust_particles = [p for p in self.dust_particles if p.update(dt)]
        
        if not self.is_dead:
            self.state_timer -= dt
            dist_to_player = player.rect.centerx - self.rect.centerx
            abs_dist = abs(dist_to_player)
            player_in_range = abs_dist < self.vision_range and abs(player.rect.centery - self.rect.centery) < 100
            
            if self.state == "HURT":
                if self.anim_manager.is_finished("hurt"):
                    self.change_state("WINDUP")
            elif self.state == "IDLE":
                if player_in_range and not player.invulnerable:
                    self.facing_right = dist_to_player > 0
                    self.change_state("WINDUP")
                elif self.state_timer <= 0:
                    self.change_state("PATROL")
            elif self.state == "PATROL":
                if player_in_range and not player.invulnerable:
                    self.facing_right = dist_to_player > 0
                    self.change_state("WINDUP")
                elif self.state_timer <= 0:
                    self.change_state("IDLE")
                else:
                    self.velocity.x = self.speed * self.patrol_dir
            elif self.state == "WINDUP":
                self.velocity.x = 0
                self.scrape_timer -= dt
                if random.random() < 0.4:
                    self._spawn_dust()
                if self.scrape_timer <= 0:
                    self.change_state("CHARGE")
            elif self.state == "CHARGE":
                if not player_in_range:
                    self.change_state("IDLE")
                else:
                    self.patrol_dir = 1 if dist_to_player > 0 else -1
                    self.facing_right = self.patrol_dir > 0
                    self.velocity.x = self.charge_speed * self.patrol_dir
                    # Charging leap over player slashes / traps
                    if self.on_ground and abs_dist < 140 and random.random() < 0.25:
                        self.velocity.y = -290.0
                        self.on_ground = False
                    
        self._apply_physics(dt, tiles)
        anim_dt = dt * (self.slow_factor if self.slow_timer > 0 else 1.0)
        self.anim_manager.update(anim_dt)
        
    def get_attack_hitbox(self) -> pygame.FRect:
        # Full body attack during charge
        if self.state == "CHARGE" and not self.is_dead:
            return self.rect
        return None

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        super().draw(surface, camera_offset)
        for p in self.dust_particles:
            p.draw(surface, camera_offset.x, camera_offset.y)
