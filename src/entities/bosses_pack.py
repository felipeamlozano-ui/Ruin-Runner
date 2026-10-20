"""
Ruin Engine — Bosses Pack (Deep Refactor).
Implements the 4 distinct boss entities utilizing extracted official assets:
1. DemonSlimeBoss: "O Titã Demoníaco" (Flame titan, pounce, conical fireballs, igneous puddles, fire light)
2. SamuraiBoss: "Lorde Samurai Amaldiçoado" (Double scale, Iaijutsu flash cut, parry stance, wind blade)
3. MonsterCreatureBoss: "O Olho / Beholder das Trevas" (Levitating chimera, telegraph laser, homing orbs, teleport)
4. ImpalerBoss: "O Empalador Abissal" (Rim light, trident embers, double sweep, ground spike rain, heaven dive)
"""

import os
import math
import random
import pygame
from config.constants import GRAVITY, MAX_FALL_SPEED
from engine.animation import Animation, AnimationManager, load_spritesheet
from entities.boss import BossShockwave, _BossParticle, SkeletonBoss
from entities.projectile import Projectile

# ─────────────────────────────────────────────────────────────────────────────
# Base Boss with hp, shield and max_hp properties
# ─────────────────────────────────────────────────────────────────────────────
class BaseBoss:
    @property
    def hp(self) -> float:
        return self.health

    @hp.setter
    def hp(self, val: float):
        self.health = val

    @property
    def max_hp(self) -> float:
        return self.max_health

    def draw_contact_shadow(self, surface: pygame.Surface, camera: tuple, width: int = None, height: int = None, alpha: int = 135):
        """Draws grounded dual-layer contact drop shadow under boss base."""
        if getattr(self, "is_dead", False):
            return
        cam_x, cam_y = camera
        sw = width if width is not None else int(self.rect.width * 1.3)
        sh = height if height is not None else 18
        shadow_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, alpha), (0, 0, sw, sh))
        core_w, core_h = max(2, int(sw * 0.65)), max(2, int(sh * 0.65))
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, min(255, int(alpha * 1.4))), ((sw - core_w) // 2, ((sh - core_h) // 2), core_w, core_h))
        surface.blit(shadow_surf, (self.rect.centerx - cam_x - sw // 2, self.rect.bottom - cam_y - sh // 2))


# ─────────────────────────────────────────────────────────────────────────────
# Hazard 1: Fire Puddle (Demônio de Chamas - Area Denial)
# ─────────────────────────────────────────────────────────────────────────────
class FirePuddle:
    __slots__ = ("rect", "lifetime", "max_lifetime", "damage", "tick_timer", "particles", "duration")
    def __init__(self, x: float, y: float, damage: int = 16, duration: float = 3.0):
        self.rect = pygame.FRect(x - 28, y - 6, 56, 14)
        self.duration = duration
        self.lifetime = self.max_lifetime = duration
        self.damage = damage
        self.tick_timer = 0.0
        self.particles: list[_BossParticle] = []

    def update(self, dt: float, target=None) -> bool:
        self.lifetime -= dt
        self.tick_timer += dt
        
        # Spawn small ember particles
        if random.random() < 0.4:
            px = random.uniform(self.rect.left + 4, self.rect.right - 4)
            self.particles.append(_BossParticle(
                px, self.rect.centery,
                random.uniform(-10, 10), random.uniform(-40, -15),
                random.uniform(0.3, 0.6), (255, 140, 30), radius=2.0, gravity=-20
            ))
        self.particles = [p for p in self.particles if p.update(dt)]
        
        # Continuous contact damage
        if target and not getattr(target, "is_dead", False) and self.rect.colliderect(target.rect):
            if self.tick_timer >= 0.4:
                self.tick_timer = 0.0
                target.take_damage(self.damage)
                if hasattr(target, "apply_burn"):
                    target.apply_burn(2.0, 3.0)
        return self.lifetime > 0

    def draw(self, surface: pygame.Surface, camera: tuple):
        cam_x, cam_y = camera
        t = max(0.0, self.lifetime / self.max_lifetime)
        alpha = int(220 * min(1.0, t * 2.0))
        p_surf = pygame.Surface((int(self.rect.width), int(self.rect.height)), pygame.SRCALPHA)
        # Pulsing lava edge & core
        pulse = 0.85 + 0.15 * math.sin(pygame.time.get_ticks() * 0.012)
        pygame.draw.ellipse(p_surf, (220, 50, 10, int(alpha * 0.8)), (0, 0, int(self.rect.width), int(self.rect.height)))
        cw = int(self.rect.width * 0.65 * pulse)
        ch = int(self.rect.height * 0.65 * pulse)
        pygame.draw.ellipse(p_surf, (255, 190, 40, alpha), ((int(self.rect.width) - cw)//2, (int(self.rect.height) - ch)//2, cw, ch))
        surface.blit(p_surf, (self.rect.x - cam_x, self.rect.y - cam_y), special_flags=pygame.BLEND_RGBA_ADD)
        for p in self.particles:
            p.draw(surface, cam_x, cam_y)


# ─────────────────────────────────────────────────────────────────────────────
# Hazard 2: Ground Spear Eruption (Senhor das Ruínas)
# ─────────────────────────────────────────────────────────────────────────────
class GroundSpike:
    __slots__ = ("x", "y", "state", "timer", "damage", "has_hit", "width", "height")
    def __init__(self, x: float, y: float, damage: int = 35):
        self.x = float(x)
        self.y = float(y)
        self.state = "TELEGRAPH"  # TELEGRAPH -> ERUPT -> RETRACT
        self.timer = 0.70         # 0.7s telegraph
        self.damage = damage
        self.has_hit = False
        self.width = 38
        self.height = 70

    def update(self, dt: float, target=None) -> bool:
        self.timer -= dt
        if self.state == "TELEGRAPH":
            if self.timer <= 0:
                self.state = "ERUPT"
                self.timer = 0.35
        elif self.state == "ERUPT":
            # Check damage (hitbox strictly matches visual spike height from base Y upwards)
            if not self.has_hit and target and not getattr(target, "is_dead", False):
                h_cur = max(16.0, self.height * min(1.0, (0.35 - self.timer) / 0.10))
                hitbox = pygame.FRect(self.x - self.width // 2, self.y - h_cur, self.width, h_cur)
                if hitbox.colliderect(target.rect):
                    self.has_hit = True
                    target.take_damage(self.damage)
            if self.timer <= 0:
                self.state = "RETRACT"
                self.timer = 0.25
        elif self.state == "RETRACT":
            if self.timer <= 0:
                return False
        return True

    def draw(self, surface: pygame.Surface, camera: tuple):
        cam_x, cam_y = camera
        sx = self.x - cam_x
        sy = self.y - cam_y
        if self.state == "TELEGRAPH":
            # Warning glyph on the ground (contact shadow + glowing runic circle)
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.02)
            gw = int(self.width * (0.9 + 0.3 * pulse))
            g_surf = pygame.Surface((gw, 14), pygame.SRCALPHA)
            pygame.draw.ellipse(g_surf, (0, 0, 0, 120), (0, 0, gw, 14))
            pygame.draw.ellipse(g_surf, (255, 60, 30, int(200 * pulse)), (0, 0, gw, 14), 2)
            pygame.draw.ellipse(g_surf, (255, 180, 60, int(140 * pulse)), (2, 2, gw - 4, 10), 1)
            surface.blit(g_surf, (sx - gw // 2, sy - 7))
        elif self.state == "ERUPT":
            # Stone & flame spikes thrusting up
            h_cur = self.height * min(1.0, (0.35 - self.timer) / 0.10)
            # Contact base glow
            base_surf = pygame.Surface((self.width + 12, 12), pygame.SRCALPHA)
            pygame.draw.ellipse(base_surf, (255, 80, 20, 140), (0, 0, self.width + 12, 12))
            surface.blit(base_surf, (sx - (self.width + 12) // 2, sy - 6))
            
            pts = [
                (sx - self.width // 2, sy),
                (sx - self.width // 4, sy - h_cur * 0.65),
                (sx, sy - h_cur),
                (sx + self.width // 4, sy - h_cur * 0.70),
                (sx + self.width // 2, sy)
            ]
            pygame.draw.polygon(surface, (140, 25, 20), pts)
            pygame.draw.lines(surface, (255, 140, 40), True, pts, 2)
        elif self.state == "RETRACT":
            # Sinking back down
            h_cur = self.height * max(0.0, self.timer / 0.25)
            pts = [(sx - self.width // 2, sy), (sx, sy - h_cur), (sx + self.width // 2, sy)]
            pygame.draw.polygon(surface, (90, 20, 20), pts)
            pygame.draw.lines(surface, (180, 60, 30), True, pts, 1)


# ─────────────────────────────────────────────────────────────────────────────
# Hazard 3: Homing Orb (Beholder das Trevas)
# ─────────────────────────────────────────────────────────────────────────────
class HomingOrb:
    __slots__ = ("x", "y", "vx", "vy", "speed", "life", "damage", "active")
    def __init__(self, x: float, y: float, target_x: float = 0.0, target_y: float = 0.0, damage: int = 26, target=None):
        self.x = float(x)
        self.y = float(y)
        self.speed = 135.0
        self.damage = damage
        self.life = 3.2
        self.active = True
        
        if target is not None and hasattr(target, "rect"):
            target_x = float(target.rect.centerx)
            target_y = float(target.rect.centery)
            
        ang = math.atan2(target_y - y, target_x - x)
        self.vx = math.cos(ang) * self.speed
        self.vy = math.sin(ang) * self.speed

    def update(self, dt: float, target=None) -> bool:
        if not self.active:
            return False
        self.life -= dt
        if self.life <= 0:
            self.active = False
            return False

        # Smooth steering towards target
        if target and not getattr(target, "is_dead", False):
            tx, ty = target.rect.centerx, target.rect.centery
            desired_ang = math.atan2(ty - self.y, tx - self.x)
            cur_ang = math.atan2(self.vy, self.vx)
            diff = (desired_ang - cur_ang + math.pi) % (math.pi * 2) - math.pi
            cur_ang += diff * min(1.0, dt * 2.8)
            self.vx = math.cos(cur_ang) * self.speed
            self.vy = math.sin(cur_ang) * self.speed

        self.x += self.vx * dt
        self.y += self.vy * dt
        
        # Floor collision check
        if self.y >= 320.0:
            self.active = False
            return False
            
        # Target collision check
        if target and not getattr(target, "is_dead", False):
            if pygame.FRect(self.x - 10, self.y - 10, 20, 20).colliderect(target.rect):
                target.take_damage(self.damage)
                self.active = False
                return False
        return True

    def draw(self, surface: pygame.Surface, camera: tuple):
        if not self.active:
            return
        cam_x, cam_y = camera
        sx, sy = self.x - cam_x, self.y - cam_y
        rad = 9
        s = pygame.Surface((rad * 2 + 4, rad * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(s, (140, 30, 220, 210), (rad + 2, rad + 2), rad)
        pygame.draw.circle(s, (240, 160, 255, 255), (rad + 2, rad + 2), rad // 2)
        surface.blit(s, (sx - rad - 2, sy - rad - 2), special_flags=pygame.BLEND_RGBA_ADD)


# ─────────────────────────────────────────────────────────────────────────────
# Lighting: PointLight2D Node
# ─────────────────────────────────────────────────────────────────────────────
class PointLight2D:
    """Dynamic point light node with smooth fire pulsation."""
    def __init__(self, color: tuple = (255, 120, 30), base_radius: int = 140, pulse_speed: float = 8.0, pulse_amp: int = 16):
        self.color = color
        self.base_radius = base_radius
        self.radius = base_radius
        self.pulse_speed = pulse_speed
        self.pulse_amp = pulse_amp

    def update(self, dt: float, time_val: float):
        self.radius = int(self.base_radius + math.sin(time_val * self.pulse_speed) * self.pulse_amp)

    def draw(self, surface: pygame.Surface, pos: tuple, camera: tuple):
        cam_x, cam_y = camera
        r = max(10, self.radius)
        l_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(l_surf, (self.color[0], max(0, self.color[1] - 40), 20, 40), (r, r), r)
        pygame.draw.circle(l_surf, (self.color[0], self.color[1], 40, 70), (r, r), int(r * 0.55))
        pygame.draw.circle(l_surf, (255, 220, 80, 110), (r, r), int(r * 0.25))
        surface.blit(l_surf, (int(pos[0] - cam_x - r), int(pos[1] - cam_y - r)), special_flags=pygame.BLEND_RGBA_ADD)


# ─────────────────────────────────────────────────────────────────────────────
# 1. DemonSlimeBoss: O Titã Demoníaco (Demônio de Chamas)
# ─────────────────────────────────────────────────────────────────────────────
class DemonSlimeBoss(BaseBoss):
    """
    Demonic slime titan wielding an abyssal blade.
    Scaled up with a proportional hitbox, warm orange dynamic point light,
    grounded charging cleave, conical fireball burst, and 3-second area denial igneous trails.
    """
    def __init__(self, x: float, y: float):
        self.name = "Demônio de Chamas"
        self.ground_y = 320.0
        self.scale = 1.70  # +70% base scale
        self.rect = pygame.FRect(x, self.ground_y - 165, 125, 165)
        self.pos = pygame.math.Vector2(self.rect.x, self.rect.y)
        self.velocity = pygame.math.Vector2(0, 0)
        
        self.max_health = 18000
        self.health = self.max_health
        self.max_shield = 900
        self.shield = self.max_shield
        self.shield_recharge_cooldown = 0.0
        
        self.attack_damage = 40
        self.touch_damage = 0
        self.is_dead = False
        self.facing_right = False
        self.on_ground = True
        
        self.fire_light = PointLight2D(color=(255, 120, 30), base_radius=140, pulse_speed=8.0, pulse_amp=16)
        
        self.current_phase = 1
        self.enraged = False
        self.potion_dropped_50 = False
        self.potions_to_spawn = []
        self.minions_to_spawn = []
        self.projectiles = []
        self.shockwaves = []
        self.puddles: list[FirePuddle] = []
        self._particles: list[_BossParticle] = []
        
        # Speeds & AI Moveset (grounded heavy strides)
        self.walk_speed = 90.0
        self.run_speed = 155.0
        self.state = "IDLE"
        self.state_timer = 0.0
        self.attack_cooldown = 0.8
        self.pounce_cooldown = 2.5
        self.fireball_cooldown = 3.0
        self.puddle_spawn_timer = 0.0
        self.has_attacked = False
        self.can_interrupt = True
        self._time = 0.0
        
        self.anim_manager = AnimationManager()
        self._load_animations()
        self.anim_manager.play("idle")

    def _load_animations(self):
        base_dir = os.path.join("assets", "sprites", "bosses", "demon_slime", "boss_demon_slime_FREE_v1.0", "individual sprites")
        sc = self.scale
        import re
        def natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]
        
        def load_folder(f_name, anim_key, fps, loop=True):
            p = os.path.join(base_dir, f_name)
            frames = []
            if os.path.exists(p):
                for f in sorted(os.listdir(p), key=natural_sort_key):
                    if f.endswith(".png"):
                        raw = pygame.image.load(os.path.join(p, f)).convert_alpha()
                        scaled = pygame.transform.scale(raw, (int(raw.get_width() * sc), int(raw.get_height() * sc)))
                        frames.append(scaled)
            if frames:
                self.anim_manager.add_animation(anim_key, Animation(frames, fps, loop))

        load_folder("01_demon_idle", "idle", 8, True)
        load_folder("02_demon_walk", "walk", 10, True)
        load_folder("03_demon_cleave", "cleave", 12, False)
        load_folder("04_demon_take_hit", "hurt", 12, False)
        load_folder("05_demon_death", "death", 10, False)

    def take_damage(self, amount: int, hit_direction: int = 0):
        if self.is_dead:
            return
            
        if self.shield > 0:
            self.shield -= amount
            if self.shield < 0:
                self.health += self.shield
                self.shield = 0
        else:
            self.health -= amount
            
        self.shield_recharge_cooldown = 4.0
        if self.health <= self.max_health * 0.5 and not self.potion_dropped_50:
            self.potion_dropped_50 = True
            self.enraged = True
            self.potions_to_spawn.append((self.rect.centerx, self.rect.bottom - 20))
            
        if self.health <= 0:
            self.health = 0
            self.is_dead = True
            self.state = "DEATH"
            self.anim_manager.play("death", force_reset=True)
        elif self.can_interrupt and self.state not in ("CLEAVE", "CHARGE_WINDUP", "CHARGE_SLASH", "DEATH") and self.shield <= 0 and random.random() < 0.2:
            self.state = "HURT"
            self.state_timer = 0.25
            self.anim_manager.play("hurt", force_reset=True)

    def get_attack_hitbox(self) -> pygame.FRect:
        if self.state in ("CLEAVE", "CHARGE_SLASH") and not self.has_attacked:
            frame_idx = self.anim_manager.current_animation.current_frame
            if 4 <= frame_idx <= 12 or self.state == "CHARGE_SLASH":
                hx = self.rect.right - 10 if self.facing_right else self.rect.left - 135
                return pygame.FRect(hx, self.rect.y + 15, 145, 130)
        return None

    def update(self, dt: float, solid_rects: list, target=None, camera=None):
        self._time += dt
        self.fire_light.update(dt, self._time)
        self.anim_manager.update(dt)
        self.state_timer -= dt
        self.attack_cooldown -= dt
        self.pounce_cooldown -= dt
        self.fireball_cooldown -= dt
        self.puddle_spawn_timer -= dt
        
        # Shield recharge
        if self.shield < self.max_shield:
            self.shield_recharge_cooldown -= dt
            if self.shield_recharge_cooldown <= 0:
                self.shield = min(self.max_shield, self.shield + 45.0 * dt)
                
        # Gravity & Physics with clean X / Y separation
        self.velocity.y = min(MAX_FALL_SPEED, self.velocity.y + GRAVITY * dt)
        
        # Horizontal Movement & Collision
        self.pos.x += self.velocity.x * dt
        self.rect.x = int(self.pos.x)
        for s in solid_rects:
            if self.rect.colliderect(s) and s.top < 200: # Lateral wall barrier
                if self.velocity.x > 0:
                    self.rect.right = s.left
                elif self.velocity.x < 0:
                    self.rect.left = s.right
                self.pos.x = float(self.rect.x)
                self.velocity.x = 0
                break

        # Vertical Movement & Collision
        self.pos.y += self.velocity.y * dt
        self.rect.y = int(self.pos.y)
        self.on_ground = False
        for s in solid_rects:
            if self.rect.colliderect(s):
                if self.velocity.y > 0 and s.top > 100:
                    self.rect.bottom = s.top
                    self.pos.y = float(self.rect.y)
                    self.velocity.y = 0
                    self.on_ground = True
                    break
                elif self.velocity.y < 0 and s.bottom < self.rect.bottom:
                    self.rect.top = s.bottom
                    self.pos.y = float(self.rect.y)
                    self.velocity.y = 0
                    break

        # Hard bounds floor safety clamp
        if self.rect.bottom > self.ground_y:
            self.rect.bottom = self.ground_y
            self.pos.y = float(self.rect.y)
            self.velocity.y = 0
            self.on_ground = True
                    
        # Update shockwaves
        for sw in self.shockwaves[:]:
            sw.update(dt, solid_rects)
            if not sw.active:
                self.shockwaves.remove(sw)

        # Update igneous puddles & check damage against player
        self.puddles = [p for p in self.puddles if p.update(dt, target)]
        self._particles = [p for p in self._particles if p.update(dt)]

        if self.is_dead:
            return

        # AI Behavior
        if target:
            dx = target.rect.centerx - self.rect.centerx
            dist = abs(dx)
            
            # Deadzone flip
            if self.state in ("IDLE", "WALK", "RUN") and dist > 36:
                self.facing_right = dx > 0
            
            # Drop igneous puddles while charging
            if self.state in ("WALK", "RUN", "CHARGE_SLASH") and self.puddle_spawn_timer <= 0:
                self.puddle_spawn_timer = 0.55
                self.puddles.append(FirePuddle(self.rect.centerx, self.rect.bottom))
            
            if self.state == "IDLE":
                if self.state_timer <= 0:
                    if dist <= 140 and self.attack_cooldown <= 0:
                        self.state = "CLEAVE"
                        self.can_interrupt = False
                        self.has_attacked = False
                        self.velocity.x = 0
                        self.anim_manager.play("cleave", force_reset=True)
                    elif 160 < dist <= 380 and self.pounce_cooldown <= 0 and self.on_ground:
                        # Grounded heavy charging slash
                        self.state = "CHARGE_WINDUP"
                        self.can_interrupt = False
                        self.state_timer = 0.40
                        self.velocity.x = 0
                        self.anim_manager.play("idle")
                    elif dist > 220 and self.fireball_cooldown <= 0:
                        # Conical Fire Projectiles from Horns
                        self.state = "FIRE_CAST"
                        self.can_interrupt = False
                        self.state_timer = 0.35
                        self.velocity.x = 0
                        self.anim_manager.play("idle")
                    else:
                        self.state = "WALK"
                        self.state_timer = random.uniform(1.0, 2.0)
                        self.anim_manager.play("walk")

            elif self.state == "FIRE_CAST":
                if self.state_timer <= 0:
                    self.fireball_cooldown = 3.5 if not self.enraged else 2.2
                    horn_x = self.rect.centerx + (25 if self.facing_right else -25)
                    horn_y = self.rect.y + 35
                    base_dir = 1.0 if self.facing_right else -1.0
                    for angle_deg in (-16, 0, 16):
                        rad = math.radians(angle_deg)
                        vx = (base_dir * math.cos(rad)) * 340.0
                        vy = math.sin(rad) * 340.0
                        proj = Projectile(horn_x, horn_y, self.facing_right, is_enemy=True, projectile_type="fire_orb", damage=32)
                        proj.velocity.x = vx
                        proj.velocity.y = vy
                        self.projectiles.append(proj)
                    self.state = "IDLE"
                    self.can_interrupt = True
                    self.state_timer = 0.4

            elif self.state == "CHARGE_WINDUP":
                # Grounded fire spark charging
                for _ in range(3):
                    self._particles.append(_BossParticle(
                        self.rect.centerx + random.uniform(-25, 25), self.rect.bottom - 10,
                        random.uniform(-30, 30), random.uniform(-50, -15),
                        0.35, (255, 140, 30), radius=3.0, gravity=-20
                    ))
                if self.state_timer <= 0:
                    self.state = "CHARGE_SLASH"
                    self.pounce_cooldown = 4.0 if not self.enraged else 2.5
                    charge_dir = 1.0 if self.facing_right else -1.0
                    self.velocity.x = charge_dir * (165.0 if not self.enraged else 210.0)
                    self.state_timer = 0.65
                    self.anim_manager.play("walk", force_reset=True)

            elif self.state == "CHARGE_SLASH":
                if dist <= 120 or self.state_timer <= 0:
                    self.state = "CLEAVE"
                    self.can_interrupt = False
                    self.has_attacked = False
                    self.velocity.x = 0
                    self.anim_manager.play("cleave", force_reset=True)

            elif self.state == "WALK":
                spd = self.run_speed if self.enraged else self.walk_speed
                self.velocity.x = spd if self.facing_right else -spd
                if dist <= 130 and self.attack_cooldown <= 0:
                    self.state = "CLEAVE"
                    self.can_interrupt = False
                    self.has_attacked = False
                    self.velocity.x = 0
                    self.anim_manager.play("cleave", force_reset=True)
                elif self.state_timer <= 0:
                    self.state = "IDLE"
                    self.state_timer = random.uniform(0.4, 0.9)
                    self.velocity.x = 0
                    self.anim_manager.play("idle")

            elif self.state == "CLEAVE":
                self.velocity.x *= 0.85
                frame_idx = self.anim_manager.current_animation.current_frame
                if frame_idx == 7 and not self.has_attacked:
                    self.has_attacked = True
                    sw_x = self.rect.right + 10 if self.facing_right else self.rect.left - 40
                    self.shockwaves.append(BossShockwave(sw_x, self.rect.bottom, self.facing_right, speed=250, damage=38))
                    if self.enraged:
                        self.shockwaves.append(BossShockwave(sw_x, self.rect.bottom, not self.facing_right, speed=210, damage=25))
                if self.anim_manager.is_finished("cleave"):
                    self.state = "IDLE"
                    self.can_interrupt = True
                    self.state_timer = 0.4
                    self.attack_cooldown = 0.8 if not self.enraged else 0.4
                    self.anim_manager.play("idle")

            elif self.state == "HURT":
                self.velocity.x *= 0.8
                if self.anim_manager.is_finished("hurt") or self.state_timer <= 0:
                    self.state = "IDLE"
                    self.state_timer = 0.25
                    self.anim_manager.play("idle")

    def draw(self, surface: pygame.Surface, camera: tuple):
        cam_x, cam_y = camera
        
        # 1. Igneous puddles drawn on the ground
        for pud in self.puddles:
            pud.draw(surface, camera)
            
        # 2. Centered contact drop shadow (no detached gizmo circle!)
        if not self.is_dead:
            self.draw_contact_shadow(surface, camera, width=130, height=24)
            
        # 3. Dynamic Point Light: delegated to Scene's LightingEngine (avoid redundant debug circles)
        if not self.is_dead and getattr(self, "show_debug_gizmos", False):
            self.fire_light.draw(surface, (self.rect.centerx, self.rect.centery), camera)

        # 4. Boss Sprite Rendering
        frame = self.anim_manager.get_current_frame()
        if not frame:
            return
            
        if self.facing_right:
            frame = pygame.transform.flip(frame, True, False)
            
        fw, fh = frame.get_width(), frame.get_height()
        # Strictly center sprite horizontally and place feet on rect bottom
        draw_x = self.rect.centerx - fw // 2 - cam_x
        draw_y = self.rect.bottom - fh + 8 - cam_y
        
        if self.enraged and not self.is_dead:
            glow_surf = pygame.Surface(frame.get_size(), pygame.SRCALPHA)
            glow_surf.fill((255, 60, 20, 45))
            frame_copy = frame.copy()
            frame_copy.blit(glow_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            surface.blit(frame_copy, (draw_x, draw_y))
        else:
            surface.blit(frame, (draw_x, draw_y))
            
        # 5. Shockwaves & Particles
        for sw in self.shockwaves:
            sw.draw(surface, pygame.math.Vector2(cam_x, cam_y))
        for p in self._particles:
            p.draw(surface, cam_x, cam_y)


# ─────────────────────────────────────────────────────────────────────────────
# 2. SamuraiBoss: Lorde Samurai Amaldiçoado (O Samurai Idoso)
# ─────────────────────────────────────────────────────────────────────────────
class SamuraiBoss(BaseBoss):
    """
    Cursed elderly ronin swordmaster.
    Crisp integer scale (2.0x) with recalculated colliders and exact sandal-to-floor alignment.
    Moveset:
      - Iaijutsu Quick Draw: Sheathes katana, stands still for 0.75s, then flashes across screen cutting with fair reaction window.
      - Defensive Parry: 0.35s parry posture. Deflects player blows with minor stagger, allowing tactical counters.
      - Wind Blade: Vertical slash firing a crescent wind projectile.
    """
    def __init__(self, x: float, y: float):
        self.name = "O Samurai Idoso"
        self.ground_y = 320.0
        self.scale = 2.0  # Crisp integer 2x pixel art
        self.rect = pygame.FRect(x, self.ground_y - 72, 44, 72)
        self.pos = pygame.math.Vector2(self.rect.x, self.rect.y)
        self.velocity = pygame.math.Vector2(0, 0)
        
        self.max_health = 18000
        self.health = self.max_health
        self.max_shield = 950
        self.shield = self.max_shield
        self.shield_recharge_cooldown = 0.0
        
        self.attack_damage = 38
        self.touch_damage = 0
        self.is_dead = False
        self.facing_right = False
        self.on_ground = True
        
        self.current_phase = 1
        self.enraged = False
        self.potion_dropped_50 = False
        self.potions_to_spawn = []
        self.minions_to_spawn = []
        self.projectiles = []
        self.shockwaves = []
        self._particles: list[_BossParticle] = []
        self._shadow_trail: list[tuple[pygame.Surface, float, float, float]] = []
        
        # Ground stride speed calibrated to fluid ronin movement
        self.run_speed = 125.0
        self.state = "IDLE"
        self.state_timer = 0.0
        self.attack_cooldown = 0.8
        self.iai_cooldown = 4.0
        self.parry_cooldown = 4.5
        self.wind_blade_cooldown = 3.0
        self.has_attacked = False
        self.can_interrupt = True
        self._time = 0.0
        
        self.anim_manager = AnimationManager()
        self._load_animations()
        self.anim_manager.play("idle")

    def _load_animations(self):
        p = os.path.join("assets", "sprites", "bosses", "samurai", "FREE_Samurai 2D Pixel Art v1.2", "Sprites")
        sc = self.scale
        
        def load_sheet(file_name, anim_key, frame_w, count, fps, loop=True):
            fp = os.path.join(p, file_name)
            if os.path.exists(fp):
                sheet = pygame.image.load(fp).convert_alpha()
                frames = []
                for i in range(count):
                    sub = sheet.subsurface((i * frame_w, 0, frame_w, 96))
                    scaled = pygame.transform.scale(sub, (int(frame_w * sc), int(96 * sc)))
                    frames.append(scaled)
                self.anim_manager.add_animation(anim_key, Animation(frames, fps, loop))

        load_sheet("IDLE.png", "idle", 96, 10, 10, True)
        load_sheet("RUN.png", "run", 96, 16, 14, True)
        load_sheet("ATTACK 1.png", "attack", 96, 7, 14, False)
        load_sheet("HURT.png", "hurt", 96, 4, 12, False)

    def take_damage(self, amount: int, hit_direction: int = 0, attacker=None):
        if self.is_dead:
            return
            
        # ── PARRY COUNTER ──
        if self.state == "PARRY":
            # Deflects player blow with blade sparks
            for _ in range(12):
                self._particles.append(_BossParticle(
                    self.rect.centerx, self.rect.centery,
                    random.uniform(-140, 140), random.uniform(-140, 50),
                    0.35, (255, 235, 120), radius=3.0, gravity=160
                ))
            if attacker and hasattr(attacker, "take_damage"):
                attacker.take_damage(14)
                attacker.state = "HURT"
                if hasattr(attacker, "hurt_timer"):
                    attacker.hurt_timer = 0.3
                    
            self.state = "IDLE"
            self.state_timer = 0.45
            self.can_interrupt = True
            self.anim_manager.play("idle", force_reset=True)
            return
            
        if self.shield > 0:
            self.shield -= amount
            if self.shield < 0:
                self.health += self.shield
                self.shield = 0
        else:
            self.health -= amount
            
        self.shield_recharge_cooldown = 4.0
        if self.health <= self.max_health * 0.5 and not self.potion_dropped_50:
            self.potion_dropped_50 = True
            self.enraged = True
            self.potions_to_spawn.append((self.rect.centerx, self.rect.bottom - 20))
            
        if self.health <= 0:
            self.health = 0
            self.is_dead = True
            self.state = "DEATH"
        elif self.can_interrupt and self.state not in ("ATTACK", "IAI_STANCE", "IAI_SLASH", "PARRY", "DEATH") and self.shield <= 0 and random.random() < 0.25:
            self.state = "HURT"
            self.state_timer = 0.20
            self.anim_manager.play("hurt", force_reset=True)

    def get_attack_hitbox(self) -> pygame.FRect:
        if self.state in ("ATTACK", "IAI_SLASH") and not self.has_attacked:
            frame_idx = self.anim_manager.current_animation.current_frame
            if 2 <= frame_idx <= 5 or self.state == "IAI_SLASH":
                hw = 110 if self.state == "IAI_SLASH" else 95
                hx = self.rect.right - 5 if self.facing_right else self.rect.left - hw + 5
                return pygame.FRect(hx, self.rect.y + 10, hw, 65)
        return None

    def update(self, dt: float, solid_rects: list, target=None, camera=None):
        self._time += dt
        self.anim_manager.update(dt)
        self.state_timer -= dt
        self.attack_cooldown -= dt
        self.iai_cooldown -= dt
        self.parry_cooldown -= dt
        self.wind_blade_cooldown -= dt
        
        # Shield recharge
        if self.shield < self.max_shield:
            self.shield_recharge_cooldown -= dt
            if self.shield_recharge_cooldown <= 0:
                self.shield = min(self.max_shield, self.shield + 45.0 * dt)
                
        # Gravity & Physics with clean X / Y separation
        self.velocity.y = min(MAX_FALL_SPEED, self.velocity.y + GRAVITY * dt)
        
        # Horizontal Movement & Collision
        self.pos.x += self.velocity.x * dt
        self.rect.x = int(self.pos.x)
        for s in solid_rects:
            if self.rect.colliderect(s) and s.top < 200: # Lateral wall barrier
                if self.velocity.x > 0:
                    self.rect.right = s.left
                elif self.velocity.x < 0:
                    self.rect.left = s.right
                self.pos.x = float(self.rect.x)
                self.velocity.x = 0
                break

        # Vertical Movement & Collision
        self.pos.y += self.velocity.y * dt
        self.rect.y = int(self.pos.y)
        self.on_ground = False
        for s in solid_rects:
            if self.rect.colliderect(s):
                if self.velocity.y > 0 and s.top > 100:
                    self.rect.bottom = s.top
                    self.pos.y = float(self.rect.y)
                    self.velocity.y = 0
                    self.on_ground = True
                    break
                elif self.velocity.y < 0 and s.bottom < self.rect.bottom:
                    self.rect.top = s.bottom
                    self.pos.y = float(self.rect.y)
                    self.velocity.y = 0
                    break

        # Hard bounds floor safety clamp
        if self.rect.bottom > self.ground_y:
            self.rect.bottom = self.ground_y
            self.pos.y = float(self.rect.y)
            self.velocity.y = 0
            self.on_ground = True

        # Fade shadow trail afterimages
        new_trail = []
        for srf, ax, ay, alpha in self._shadow_trail:
            alpha -= dt * 700.0
            if alpha > 0:
                new_trail.append((srf, ax, ay, alpha))
        self._shadow_trail = new_trail
        self._particles = [p for p in self._particles if p.update(dt)]

        if self.is_dead:
            self.velocity.x = 0
            return

        # AI Behavior
        if target:
            dx = target.rect.centerx - self.rect.centerx
            dist = abs(dx)
            
            # Deadzone on flip (38px)
            if self.state in ("IDLE", "RUN") and dist > 38:
                self.facing_right = dx > 0
            
            if self.state == "IDLE":
                if self.state_timer <= 0:
                    if dist <= 110 and self.attack_cooldown <= 0:
                        # Close range melee combo
                        self.facing_right = dx > 0
                        self.state = "ATTACK"
                        self.can_interrupt = False
                        self.has_attacked = False
                        self.velocity.x = 0
                        self.anim_manager.play("attack", force_reset=True)
                    elif dist <= 160 and self.parry_cooldown <= 0 and random.random() < 0.35:
                        # Defensive Parry Window (0.35s)
                        self.facing_right = dx > 0
                        self.state = "PARRY"
                        self.can_interrupt = False
                        self.state_timer = 0.35
                        self.velocity.x = 0
                        self.parry_cooldown = 4.5
                        self.anim_manager.play("idle")
                    elif 150 < dist <= 380 and self.iai_cooldown <= 0:
                        # Postura de Saque Rápido (Iaijutsu telegraph)
                        self.facing_right = dx > 0
                        self.state = "IAI_STANCE"
                        self.can_interrupt = False
                        self.state_timer = 0.75  # Fair 0.75s telegraph!
                        self.velocity.x = 0
                        self.iai_cooldown = 4.5 if not self.enraged else 3.0
                        self.anim_manager.play("idle")
                    elif dist > 180 and self.wind_blade_cooldown <= 0:
                        # Lâmina de Vento (Wind Blade)
                        self.facing_right = dx > 0
                        self.state = "WIND_SLASH"
                        self.can_interrupt = False
                        self.has_attacked = False
                        self.state_timer = 0.40
                        self.velocity.x = 0
                        self.wind_blade_cooldown = 3.0
                        self.anim_manager.play("attack", force_reset=True)
                    else:
                        self.state = "RUN"
                        self.state_timer = random.uniform(1.0, 1.8)
                        self.anim_manager.play("run")

            elif self.state == "IAI_STANCE":
                if dist > 20:
                    self.facing_right = dx > 0
                # Telegraph: Charging flash sparks on blade hilt
                if random.random() < 0.7:
                    self._particles.append(_BossParticle(
                        self.rect.centerx + (20 if self.facing_right else -20),
                        self.rect.centery,
                        random.uniform(-30, 30), random.uniform(-40, 10),
                        0.3, (255, 240, 100), radius=2.5, gravity=50
                    ))
                if self.state_timer <= 0:
                    # Flash Step Across Arena with balanced speed
                    self.state = "IAI_SLASH"
                    self.has_attacked = False
                    self.state_timer = 0.30
                    flash_dir = 1.0 if self.facing_right else -1.0
                    self.velocity.x = flash_dir * 320.0  # Fair, dodgeable flash cut
                    self.anim_manager.play("attack", force_reset=True)
                    if camera:
                        camera.shake(8.0, 0.25)

            elif self.state == "IAI_SLASH":
                # Leave shadow trail
                frame = self.anim_manager.get_current_frame()
                if frame:
                    fw, fh = frame.get_width(), frame.get_height()
                    fx = self.rect.centerx - int(48 * self.scale)
                    fy = self.rect.bottom - int(80 * self.scale)
                    self._shadow_trail.append((frame.copy(), fx, fy, 200.0))
                if self.state_timer <= 0 or self.anim_manager.is_finished("attack"):
                    self.state = "IDLE"
                    self.can_interrupt = True
                    self.state_timer = 0.55  # Vulnerability punish window
                    self.velocity.x = 0
                    self.anim_manager.play("idle")

            elif self.state == "PARRY":
                # Defensive stance glint
                if random.random() < 0.4:
                    self._particles.append(_BossParticle(
                        self.rect.centerx, self.rect.centery,
                        random.uniform(-30, 30), random.uniform(-40, 10),
                        0.25, (180, 220, 255), radius=2.0, gravity=30
                    ))
                if self.state_timer <= 0:
                    self.state = "IDLE"
                    self.can_interrupt = True
                    self.anim_manager.play("idle")

            elif self.state == "WIND_SLASH":
                frame_idx = self.anim_manager.current_animation.current_frame
                if frame_idx == 3 and not self.has_attacked:
                    self.has_attacked = True
                    # Launch vertical wind crescent blade
                    p_x = self.rect.right + 15 if self.facing_right else self.rect.left - 35
                    proj = Projectile(p_x, self.rect.centery - 10, self.facing_right, is_enemy=True, projectile_type="wind_blade", damage=32)
                    proj.velocity.x = 340.0 if self.facing_right else -340.0
                    self.projectiles.append(proj)
                if self.anim_manager.is_finished("attack"):
                    self.state = "IDLE"
                    self.can_interrupt = True
                    self.state_timer = 0.4
                    self.anim_manager.play("idle")

            elif self.state == "RUN":
                self.velocity.x = self.run_speed if self.facing_right else -self.run_speed
                if dist <= 110 and self.attack_cooldown <= 0:
                    self.state = "ATTACK"
                    self.can_interrupt = False
                    self.has_attacked = False
                    self.velocity.x = 0
                    self.anim_manager.play("attack", force_reset=True)
                elif self.state_timer <= 0:
                    self.state = "IDLE"
                    self.state_timer = random.uniform(0.3, 0.7)
                    self.velocity.x = 0
                    self.anim_manager.play("idle")

            elif self.state == "ATTACK":
                self.velocity.x *= 0.88
                if self.anim_manager.is_finished("attack"):
                    self.state = "IDLE"
                    self.can_interrupt = True
                    self.state_timer = 0.35
                    self.attack_cooldown = 0.6 if not self.enraged else 0.3
                    self.anim_manager.play("idle")

            elif self.state == "HURT":
                self.velocity.x *= 0.8
                if self.anim_manager.is_finished("hurt") or self.state_timer <= 0:
                    self.state = "IDLE"
                    self.state_timer = 0.25
                    self.anim_manager.play("idle")

    def draw(self, surface: pygame.Surface, camera: tuple):
        cam_x, cam_y = camera
        
        # 1. Contact shadow aligned strictly under sandals on the floor
        if not self.is_dead:
            self.draw_contact_shadow(surface, camera, width=54, height=14)
            
        # 2. Draw afterimages (Iaijutsu flash step)
        for aft, ax, ay, alpha in self._shadow_trail:
            if not self.facing_right:
                aft = pygame.transform.flip(aft, True, False)
            ghost = aft.copy()
            ghost.set_alpha(int(alpha))
            surface.blit(ghost, (ax - cam_x, ay - cam_y))

        # 3. Sprite drawing with exact sandal pivot alignment (no floating!)
        frame = self.anim_manager.get_current_frame()
        if not frame:
            return
            
        if not self.facing_right:
            frame = pygame.transform.flip(frame, True, False)
            
        # Center 96px frame at rect center and align feet (Y=80 in frame) with rect.bottom
        draw_x = self.rect.centerx - int(48 * self.scale) - cam_x
        draw_y = self.rect.bottom - int(80 * self.scale) - cam_y
        
        surface.blit(frame, (draw_x, draw_y))
        
        # 4. Particles
        for p in self._particles:
            p.draw(surface, cam_x, cam_y)


# ─────────────────────────────────────────────────────────────────────────────
# 3. MonsterCreatureBoss: O Olho / Beholder das Trevas (Monstro Quimérico)
# ─────────────────────────────────────────────────────────────────────────────
class MonsterCreatureBoss(BaseBoss):
    """
    Floating dark beholder chimera.
    Scale 2.0x, elevated above the floor with smooth sinusoidal levitation.
    Moveset:
      - Aerial Gliding: Keeps medium distance, smoothly retreating if player gets too close.
      - Ocular Laser: Telegraphed line of sight for 0.8s, followed by a continuous piercing beam.
      - Multiple Glares: 3 homing dark orbs tracking the player slowly and exploding.
      - Shadow Teleport: At 50% HP or when cornered, vanishes into dark void fog and reappears across arena.
    """
    def __init__(self, x: float, y: float):
        self.name = "O Olho / Beholder das Trevas"
        self.ground_y = 320.0
        self.scale = 2.0  # Crisp scale
        # Hitbox elevated in the air so ground shots pass underneath!
        self.rect = pygame.FRect(x, 102, 84, 96)
        self.pos = pygame.math.Vector2(self.rect.x, 150.0)
        self.velocity = pygame.math.Vector2(0, 0)
        
        self.max_health = 17500
        self.health = self.max_health
        self.max_shield = 800
        self.shield = self.max_shield
        self.shield_recharge_cooldown = 0.0
        
        self.attack_damage = 36
        self.touch_damage = 0
        self.is_dead = False
        self.facing_right = False
        self.on_ground = True  # Hovering entity
        self.is_floating = True
        
        self.current_phase = 1
        self.enraged = False
        self.potion_dropped_50 = False
        self.teleported_50 = False
        self.potions_to_spawn = []
        self.minions_to_spawn = []
        self.projectiles = []
        self.shockwaves = []
        self.homing_orbs: list[HomingOrb] = []
        self._particles: list[_BossParticle] = []
        
        # Aerial Floating & AI
        self.fly_speed = 140.0
        self.float_offset_y = 0.0
        self.state = "IDLE"
        self.state_timer = 0.0
        self.attack_cooldown = 0.8
        self.laser_cooldown = 4.0
        self.orbs_cooldown = 3.5
        self.can_interrupt = True
        self._time = 0.0
        self.laser_target = None
        
        self.anim_manager = AnimationManager()
        self._load_animations()
        self.anim_manager.play("idle")

    def _load_animations(self):
        p = os.path.join("assets", "sprites", "bosses", "monster_creature", "pixel-0063-4100537309.png")
        if not os.path.exists(p):
            p_dir = os.path.join("assets", "sprites", "bosses", "monster_creature")
            pngs = [f for f in sorted(os.listdir(p_dir)) if f.endswith(".png")]
            p = os.path.join(p_dir, pngs[0]) if pngs else ""
            
        base_raw = pygame.image.load(p).convert_alpha() if (p and os.path.exists(p)) else pygame.Surface((64, 96), pygame.SRCALPHA)
        sc = self.scale
        bw, bh = int(base_raw.get_width() * sc), int(base_raw.get_height() * sc)
        base = pygame.transform.scale(base_raw, (bw, bh))

        # 1. IDLE: Natural organic breathing (squash & stretch breathing + subtle ocular core glow)
        idle_frames = []
        for i in range(8):
            t = math.sin(i / 8.0 * math.pi * 2.0)
            sw = max(1, int(bw * (1.0 - t * 0.035)))
            sh = max(1, int(bh * (1.0 + t * 0.045)))
            f_surf = pygame.transform.scale(base, (sw, sh))
            canvas = pygame.Surface((bw + 8, bh + 12), pygame.SRCALPHA)
            canvas.blit(f_surf, ((bw + 8 - sw) // 2, bh + 12 - sh))
            idle_frames.append(canvas)
        self.anim_manager.add_animation("idle", Animation(idle_frames, 8, True))

        # 2. WALK / FLY: Gliding hover with wing flap & aerodynamic pitch
        walk_frames = []
        for i in range(8):
            t = math.sin(i / 8.0 * math.pi * 2.0)
            rot_surf = pygame.transform.rotozoom(base, -3.5 * t, 1.0)
            canvas = pygame.Surface((bw + 16, bh + 16), pygame.SRCALPHA)
            canvas.blit(rot_surf, ((canvas.get_width() - rot_surf.get_width()) // 2, (canvas.get_height() - rot_surf.get_height()) // 2))
            walk_frames.append(canvas)
        self.anim_manager.add_animation("walk", Animation(walk_frames, 10, True))

        # 3. ATTACK: Rearing back, charging dark ocular corona, and lunging forward
        attack_frames = []
        for i in range(10):
            if i < 4:
                t = i / 3.0
                sw, sh = int(bw * (1.0 + t * 0.06)), int(bh * (1.0 - t * 0.08))
                f_surf = pygame.transform.scale(base, (sw, sh))
                glow = pygame.Surface(f_surf.get_size(), pygame.SRCALPHA)
                glow.fill((160, 40, 240, int(90 * t)))
                f_surf.blit(glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            else:
                t = (i - 4) / 5.0
                sw, sh = int(bw * (1.0 - t * 0.04)), int(bh * (1.0 + t * 0.08))
                f_surf = pygame.transform.scale(base, (sw, sh))
                glow = pygame.Surface(f_surf.get_size(), pygame.SRCALPHA)
                glow.fill((255, 120, 255, int(120 * (1.0 - t))))
                f_surf.blit(glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            canvas = pygame.Surface((bw + 20, bh + 20), pygame.SRCALPHA)
            canvas.blit(f_surf, ((canvas.get_width() - f_surf.get_width()) // 2, canvas.get_height() - f_surf.get_height()))
            attack_frames.append(canvas)
        self.anim_manager.add_animation("attack", Animation(attack_frames, 12, False))

        # 4. HURT: Red/crimson hit tint preserving alpha channel (NO white salt statue!)
        hurt_frames = []
        for i in range(4):
            f_surf = base.copy()
            tint = pygame.Surface(f_surf.get_size(), pygame.SRCALPHA)
            tint.fill((255, 120, 120, 255))
            f_surf.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            hurt_frames.append(f_surf)
        self.anim_manager.add_animation("hurt", Animation(hurt_frames, 12, False))

        # 5. DEATH: Dissolving dark void disintegration
        death_frames = []
        for i in range(12):
            prog = i / 11.0
            alpha = max(0, int(255 * (1.0 - prog)))
            sw = max(1, int(bw * (1.0 - prog * 0.3)))
            sh = max(1, int(bh * (1.0 + prog * 0.4)))
            f_surf = pygame.transform.scale(base, (sw, sh)).copy()
            f_surf.set_alpha(alpha)
            canvas = pygame.Surface((bw + 20, int(bh * 1.5)), pygame.SRCALPHA)
            canvas.blit(f_surf, ((canvas.get_width() - sw) // 2, canvas.get_height() - sh))
            death_frames.append(canvas)
        self.anim_manager.add_animation("death", Animation(death_frames, 8, False))

    def take_damage(self, amount: int, hit_direction: int = 0):
        if self.is_dead:
            return
            
        if self.shield > 0:
            self.shield -= amount
            if self.shield < 0:
                self.health += self.shield
                self.shield = 0
        else:
            self.health -= amount
            
        self.shield_recharge_cooldown = 4.0
        if self.health <= self.max_health * 0.5 and not self.potion_dropped_50:
            self.potion_dropped_50 = True
            self.enraged = True
            self.potions_to_spawn.append((self.rect.centerx, self.rect.bottom - 20))
            # Trigger emergency teleport away to opposite corner
            self._trigger_teleport()
            
        if self.health <= 0:
            self.health = 0
            self.is_dead = True
            self.state = "DEATH"
            self.anim_manager.play("death", force_reset=True)
        elif self.can_interrupt and self.state not in ("LASER_BEAM", "TELEPORT", "DEATH") and self.shield <= 0 and random.random() < 0.2:
            self.state = "HURT"
            self.state_timer = 0.25
            self.anim_manager.play("hurt", force_reset=True)

    def _trigger_teleport(self):
        """Teleports through dark void fog to opposite side of the arena."""
        self.state = "TELEPORT"
        self.can_interrupt = False
        self.state_timer = 0.55
        for _ in range(25):
            self._particles.append(_BossParticle(
                self.rect.centerx, self.rect.centery,
                random.uniform(-140, 140), random.uniform(-140, 140),
                0.55, (120, 20, 200), radius=4.0, gravity=-20
            ))

    def get_attack_hitbox(self) -> pygame.FRect:
        if self.state == "ATTACK" and not self.has_attacked:
            frame_idx = self.anim_manager.current_animation.current_frame
            if 2 <= frame_idx <= 4:
                hx = self.rect.right - 10 if self.facing_right else self.rect.left - 90
                return pygame.FRect(hx, self.rect.y + 10, 100, 80)
        return None

    def update(self, dt: float, solid_rects: list, target=None, camera=None):
        self._time += dt
        self.anim_manager.update(dt)
        self.state_timer -= dt
        self.attack_cooldown -= dt
        self.laser_cooldown -= dt
        self.orbs_cooldown -= dt
        
        # Smooth sinusoidal levitation oscillation in midair
        self.float_offset_y = math.sin(self._time * 3.5) * 12.0
        
        # Shield recharge
        if self.shield < self.max_shield:
            self.shield_recharge_cooldown -= dt
            if self.shield_recharge_cooldown <= 0:
                self.shield = min(self.max_shield, self.shield + 40.0 * dt)
                
        # Hovering physics: smoothly bob at mid-air altitude Y=150
        target_y = 150.0 + self.float_offset_y
        self.pos.y += (target_y - self.pos.y) * min(1.0, 5.0 * dt)
        self.pos.x += self.velocity.x * dt
        
        # Clamp horizontal movement within arena bounds
        if self.pos.x < 35:
            self.pos.x = 35.0
            self.velocity.x = 0
        elif self.pos.x + self.rect.width > 605:
            self.pos.x = 605.0 - self.rect.width
            self.velocity.x = 0
            
        self.rect.center = (int(self.pos.x + self.rect.width / 2), int(self.pos.y))
        
        # Update homing orbs & particles
        self.homing_orbs = [o for o in self.homing_orbs if o.update(dt, target)]
        self._particles = [p for p in self._particles if p.update(dt)]

        if self.is_dead:
            self.velocity.x = 0
            return

        # AI Behavior
        if target:
            dx = target.rect.centerx - self.rect.centerx
            dist = abs(dx)
            
            # Deadzone on flip
            if self.state in ("IDLE", "FLY_FAR", "FLOAT") and dist > 38:
                self.facing_right = dx > 0
                
            if self.state == "IDLE":
                if self.state_timer <= 0:
                    # Aerial distance control: keep 190-260px distance
                    if dist < 140:
                        # Too close! Glides away rapidly
                        self.state = "FLY_FAR"
                        self.state_timer = random.uniform(0.8, 1.4)
                        self.anim_manager.play("walk")
                    elif self.laser_cooldown <= 0:
                        # Ocular Laser (Telegraphed line of sight for 0.8s)
                        self.state = "LASER_TELEGRAPH"
                        self.can_interrupt = False
                        self.state_timer = 0.80
                        self.velocity.x = 0
                        self.laser_cooldown = 5.0 if not self.enraged else 3.5
                        self.anim_manager.play("idle")
                    elif self.orbs_cooldown <= 0:
                        # Multiple Homing Orbs
                        self.state = "ORBS_CAST"
                        self.can_interrupt = False
                        self.state_timer = 0.45
                        self.velocity.x = 0
                        self.orbs_cooldown = 4.2 if not self.enraged else 2.8
                        self.anim_manager.play("attack", force_reset=True)
                    else:
                        # Idle hovering
                        self.state = "FLOAT"
                        self.state_timer = random.uniform(0.6, 1.2)
                        self.anim_manager.play("idle")

            elif self.state == "HURT":
                self.velocity.x *= 0.85
                if self.anim_manager.is_finished("hurt") or self.state_timer <= 0:
                    self.state = "IDLE"
                    self.can_interrupt = True
                    self.state_timer = 0.25
                    self.anim_manager.play("idle")

            elif self.state == "TELEPORT":
                if self.state_timer <= 0:
                    # Move to opposite side of 640px arena
                    arena_mid = 320
                    new_x = 120 if self.rect.centerx > arena_mid else 480
                    self.pos.x = float(new_x)
                    self.rect.centerx = int(self.pos.x + self.rect.width / 2)
                    self.state = "IDLE"
                    self.can_interrupt = True
                    self.state_timer = 0.5
                    for _ in range(25):
                        self._particles.append(_BossParticle(
                            self.rect.centerx, self.rect.centery,
                            random.uniform(-140, 140), random.uniform(-140, 140),
                            0.55, (120, 20, 200), radius=4.0, gravity=-20
                        ))

            elif self.state == "FLY_FAR":
                escape_dir = -1.0 if dx > 0 else 1.0
                self.velocity.x = escape_dir * (self.fly_speed * 1.5)
                if dist >= 220 or self.state_timer <= 0:
                    self.velocity.x = 0
                    self.state = "IDLE"
                    self.state_timer = 0.3
                    self.anim_manager.play("idle")

            elif self.state == "FLOAT":
                drift_dir = 1.0 if dx > 0 else -1.0
                if dist > 260:
                    self.velocity.x = drift_dir * self.fly_speed
                elif dist < 180:
                    self.velocity.x = -drift_dir * self.fly_speed
                else:
                    self.velocity.x *= 0.85
                if self.state_timer <= 0:
                    self.state = "IDLE"

            elif self.state == "LASER_TELEGRAPH":
                self.laser_target = (target.rect.centerx, target.rect.centery)
                if self.state_timer <= 0:
                    self.state = "LASER_BEAM"
                    self.state_timer = 0.60
                    if camera:
                        camera.shake(7.0, 0.4)

            elif self.state == "LASER_BEAM":
                if self.laser_target and not target.is_dead:
                    target.take_damage(int(55.0 * dt))
                if self.state_timer <= 0:
                    self.state = "IDLE"
                    self.can_interrupt = True
                    self.state_timer = 0.5
                    self.laser_target = None
                    self.anim_manager.play("idle")

            elif self.state == "ORBS_CAST":
                if self.state_timer <= 0:
                    cx = self.rect.centerx
                    cy = self.rect.centery - 10
                    for off_y in (-30, 0, 30):
                        self.homing_orbs.append(HomingOrb(cx, cy + off_y, target.rect.centerx, target.rect.centery, damage=28))
                    self.state = "IDLE"
                    self.can_interrupt = True
                    self.state_timer = 0.4
                    self.anim_manager.play("idle")

    def draw(self, surface: pygame.Surface, camera: tuple):
        cam_x, cam_y = camera
        
        # 1. Ground contact shadow projected at arena floor level Y = ground_y (320)
        if not self.is_dead:
            ground_y = self.ground_y
            float_dist = max(10.0, ground_y - self.rect.bottom)
            sh_scale = max(0.4, 1.0 - float_dist / 320.0)
            sw, sh = int(80 * sh_scale), int(16 * sh_scale)
            sh_alpha = int(105 * sh_scale)
            if sw > 4 and sh > 4 and sh_alpha > 0:
                shadow_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
                pygame.draw.ellipse(shadow_surf, (0, 0, 0, sh_alpha), (0, 0, sw, sh))
                core_w, core_h = int(sw * 0.6), int(sh * 0.6)
                pygame.draw.ellipse(shadow_surf, (0, 0, 0, min(255, int(sh_alpha * 1.4))), ((sw - core_w)//2, (sh - core_h)//2, core_w, core_h))
                surface.blit(shadow_surf, (self.rect.centerx - cam_x - sw // 2, ground_y - cam_y - sh // 2))

        # 2. Draw Homing Orbs
        for orb in self.homing_orbs:
            orb.draw(surface, camera)

        # 3. Draw Laser Telegraph or Active Laser Beam
        if self.state == "LASER_TELEGRAPH" and self.laser_target:
            eye_x = self.rect.centerx - cam_x
            eye_y = self.rect.centery - 10 - cam_y
            tx = self.laser_target[0] - cam_x
            ty = self.laser_target[1] - cam_y
            pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.03)
            pygame.draw.line(surface, (255, 60, 160, int(150 * pulse)), (eye_x, eye_y), (tx, ty), 1)
        elif self.state == "LASER_BEAM" and self.laser_target:
            eye_x = self.rect.centerx - cam_x
            eye_y = self.rect.centery - 10 - cam_y
            tx = self.laser_target[0] - cam_x
            ty = self.laser_target[1] - cam_y
            pygame.draw.line(surface, (160, 20, 240), (eye_x, eye_y), (tx, ty), 12)
            pygame.draw.line(surface, (255, 120, 255), (eye_x, eye_y), (tx, ty), 6)
            pygame.draw.line(surface, (255, 255, 255), (eye_x, eye_y), (tx, ty), 2)

        # 4. Floating Chimera Sprite strictly centered with hitbox
        frame = self.anim_manager.get_current_frame()
        if not frame:
            return
            
        if not self.facing_right:
            frame = pygame.transform.flip(frame, True, False)
            
        fw = frame.get_width()
        fh = frame.get_height()
        draw_x = self.rect.centerx - fw // 2 - cam_x
        draw_y = self.rect.centery - fh // 2 - cam_y
        
        surface.blit(frame, (draw_x, draw_y))
        
        # 5. Particles
        for p in self._particles:
            p.draw(surface, cam_x, cam_y)



# ─────────────────────────────────────────────────────────────────────────────
# 4. ImpalerBoss (REMOVIDO / DEPRECATED)
# Mantido como classe de redirecionamento para SkeletonBoss para evitar quebras em testes
# ─────────────────────────────────────────────────────────────────────────────
class ImpalerBoss(SkeletonBoss):
    """
    O Boss Empalador Abissal foi totalmente removido do jogo conforme solicitado.
    Esta classe atua apenas como alias seguro para retrocompatibilidade de testes.
    """
    def __init__(self, x: float = 500, y: float = 320):
        super().__init__(x, y)
        self.name = "O Rei Esqueleto"
