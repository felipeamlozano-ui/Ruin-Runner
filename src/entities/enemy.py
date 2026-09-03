import pygame
import os
import math
import random
from config.constants import GRAVITY, MAX_FALL_SPEED
import engine.resource_manager as rm
from engine.animation import AnimationManager, load_animation_folder

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
        
        self.health = 3
        self.is_dead = False
        self.facing_right = False
        self.on_ground = False
        
        self.anim_manager = AnimationManager()
        self.state = "IDLE"
        self.slow_timer = 0.0
        self.slow_factor = 1.0

    def apply_slow(self, duration: float = 2.5, factor: float = 0.25):
        """Applies slow-motion status effect from player Ultimate skill."""
        if not self.is_dead:
            self.slow_timer = max(self.slow_timer, duration)
            self.slow_factor = factor

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
        if self.slow_timer > 0:
            self.slow_timer -= dt
            effective_dt = dt * self.slow_factor
        else:
            effective_dt = dt
            
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
            
        # Draw icy tint when slowed
        if self.slow_timer > 0 and not self.is_dead:
            tinted = img.copy()
            tinted.fill((130, 205, 255), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(tinted, (draw_x, draw_y))
        else:
            surface.blit(img, (draw_x, draw_y))


# ─────────────────────────────────────────────────────────────────────────────
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

        # ── VFX state ──────────────────────────────────────────────────────
        self._time = 0.0
        # Sword slash arc drawn over attack frames 2-5
        self._slash_timer = 0.0          # countdown for how long arc is visible
        self._slash_dir = 1              # +1 right / -1 left
        # Eye glow during windup (frame 0-1 of attack)
        self._eye_glow_timer = 0.0
        # Particles
        self._particles: list[_Particle] = []

    def _spawn_slash_particles(self):
        """Emit crimson sparks from the sword tip on attack."""
        tip_x = self.rect.right + 15 if self.facing_right else self.rect.left - 15
        tip_y = self.rect.centery - 5
        for _ in range(8):
            angle = random.uniform(-0.6, 0.6) + (0 if self.facing_right else math.pi)
            speed = random.uniform(60, 140)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed - 30
            color = random.choice([(255, 50, 20), (255, 130, 30), (255, 200, 60)])
            self._particles.append(_Particle(tip_x, tip_y, vx, vy, random.uniform(0.18, 0.38), color, radius=random.uniform(1.5, 3.5), gravity=280))

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
            self._eye_glow_timer = 0.25    # eye flash on windup
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
        self._time += dt
        # Decay VFX timers
        if self._eye_glow_timer > 0:
            self._eye_glow_timer -= dt
        if self._slash_timer > 0:
            self._slash_timer -= dt

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
                cur_frame = self.anim_manager.animations["attack"].current_frame
                # Trigger slash arc + particles once at frame 2
                if cur_frame == 2 and self._slash_timer <= 0:
                    self._slash_timer = 0.18
                    self._slash_dir = 1 if self.facing_right else -1
                    self._spawn_slash_particles()
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
        anim_dt = dt * (self.slow_factor if self.slow_timer > 0 else 1.0)
        self.anim_manager.update(anim_dt)
        # Update particles
        self._particles = [p for p in self._particles if p.update(dt)]

    def _draw_eye_glow(self, surface, cx, cy, cam_x, cam_y):
        """Draw red crimson eye glow flare during windup."""
        t = max(0, self._eye_glow_timer) / 0.25
        if t <= 0:
            return
        alpha = int(220 * t)
        glow_r = int(7 * t)
        eye_offset_x = 5 if self.facing_right else -5
        ex = cx + eye_offset_x - cam_x
        ey = cy - cam_y - 28
        if glow_r > 0:
            gs = pygame.Surface((glow_r * 4, glow_r * 4), pygame.SRCALPHA)
            pygame.draw.circle(gs, (255, 30, 30, alpha), (glow_r * 2, glow_r * 2), glow_r * 2)
            surface.blit(gs, (ex - glow_r * 2, ey - glow_r * 2))

    def _draw_slash_arc(self, surface, cx, cy, cam_x, cam_y):
        """Draw a glowing crimson sword-slash arc."""
        if self._slash_timer <= 0:
            return
        progress = max(0, self._slash_timer / 0.18)  # 0→1 fade in/out
        alpha = int(200 * progress)
        arc_r = 26
        start_angle = -math.pi * 0.5
        span = math.pi * 1.0
        if self._slash_dir < 0:
            start_angle = -math.pi * 0.5
            span = -math.pi * 1.0
        # Draw multiple offset arcs for glow thickness
        tip_x = (cx + arc_r * 0.7 * self._slash_dir) - cam_x
        tip_y = cy - cam_y - 10
        rect_size = arc_r * 2 + 10
        arc_surf = pygame.Surface((rect_size + 10, rect_size + 10), pygame.SRCALPHA)
        for glow_w, glow_col in [(7, (255, 80, 20, alpha // 3)), (4, (255, 150, 50, alpha // 2)), (2, (255, 240, 120, alpha))]:
            pygame.draw.arc(arc_surf, glow_col,
                            pygame.Rect(5, 5, rect_size, rect_size),
                            start_angle, start_angle + span, glow_w)
        surface.blit(arc_surf, (tip_x - rect_size // 2 - 5, tip_y - rect_size // 2 - 5))

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if self.is_dead and self.anim_manager.is_finished("dead"):
            return

        cam_x, cam_y = camera_offset.x, camera_offset.y
        img = self.anim_manager.get_current_frame()
        img_rect = img.get_rect()
        draw_x = self.rect.centerx - cam_x - img_rect.width / 2
        draw_y = self.rect.bottom - cam_y - img_rect.height
        cx, cy = self.rect.centerx, self.rect.centery

        if not self.facing_right:
            img = pygame.transform.flip(img, True, False)

        # VFX: slash arc (draw behind sprite)
        self._draw_slash_arc(surface, cx, cy, cam_x, cam_y)

        # Draw sprite with tint
        if self.slow_timer > 0 and not self.is_dead:
            tinted = img.copy()
            tinted.fill((130, 205, 255), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(tinted, (draw_x, draw_y))
        else:
            surface.blit(img, (draw_x, draw_y))

        # VFX: eye glow on windup (over sprite)
        self._draw_eye_glow(surface, cx, cy, cam_x, cam_y)

        # Draw particles
        for p in self._particles:
            p.draw(surface, cam_x, cam_y)


# ─────────────────────────────────────────────────────────────────────────────
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
        alpha_scale = min(1.0, self._cast_charge * 2)
        alpha_base = int(160 * alpha_scale)

        tip_x = (cx + 16 * (1 if self.facing_right else -1)) - cam_x
        tip_y = cy - cam_y - 10

        # Outer spinning ring
        ring_surf = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
        rc = radius + 4
        for i, (rr, col_alpha) in enumerate([(radius, alpha_base), (radius - 3, alpha_base // 2)]):
            col = (200 - i * 40, 30 + i * 20, 255, col_alpha)
            if rr > 0:
                pygame.draw.circle(ring_surf, col, (rc, rc), rr, 2)

        # Spinning rune spokes
        for i in range(6):
            angle = self._rune_angle + i * (math.pi / 3)
            sx = rc + int(math.cos(angle) * radius)
            sy = rc + int(math.sin(angle) * radius)
            ex = rc + int(math.cos(angle + math.pi) * (radius // 2))
            ey = rc + int(math.sin(angle + math.pi) * (radius // 2))
            pygame.draw.line(ring_surf, (220, 100, 255, alpha_base // 2), (sx, sy), (ex, ey), 1)

        surface.blit(ring_surf, (tip_x - rc, tip_y - rc))

        # Inner glow pulse
        pulse = 0.5 + 0.5 * math.sin(self._cast_charge * math.pi * 4)
        if radius > 4:
            glow_s = pygame.Surface((radius, radius), pygame.SRCALPHA)
            pygame.draw.circle(glow_s, (200, 80, 255, int(80 * pulse * alpha_scale)),
                               (radius // 2, radius // 2), radius // 2)
            surface.blit(glow_s, (tip_x - radius // 2, tip_y - radius // 2))

    def _draw_shoot_flash(self, surface, cx, cy, cam_x, cam_y, alpha):
        """Arcane flash burst at the moment of firing."""
        tip_x = (cx + 20 * (1 if self.facing_right else -1)) - cam_x
        tip_y = cy - cam_y - 8
        burst_r = 14
        bs = pygame.Surface((burst_r * 2, burst_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(bs, (255, 150, 255, alpha), (burst_r, burst_r), burst_r)
        pygame.draw.circle(bs, (255, 255, 255, alpha // 2), (burst_r, burst_r), burst_r // 2)
        surface.blit(bs, (tip_x - burst_r, tip_y - burst_r))

    def update(self, dt: float, tiles: list[pygame.FRect], player):
        self._time += dt
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
        anim_dt = dt * (self.slow_factor if self.slow_timer > 0 else 1.0)
        self.anim_manager.update(anim_dt)
        
    def get_attack_hitbox(self) -> pygame.FRect:
        # Full body attack during charge
        if self.state == "CHARGE" and not self.is_dead:
            return self.rect
        return None
