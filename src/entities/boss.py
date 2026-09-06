import pygame
import os
import math
import random
from engine.animation import AnimationManager, load_animation_folder, load_spritesheet
from entities.projectile import Projectile

# ─────────────────────────────────────────────────────────────────────────────
# Lightweight particle for VFX
# ─────────────────────────────────────────────────────────────────────────────
class _BossParticle:
    __slots__ = ("x","y","vx","vy","life","max_life","color","radius","gravity")
    def __init__(self, x, y, vx, vy, life, color, radius=3.0, gravity=0.0):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = float(vx), float(vy)
        self.life = self.max_life = float(life)
        self.color = color
        self.radius = float(radius)
        self.gravity = float(gravity)

    def update(self, dt):
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface, cam_x, cam_y):
        t = max(0.0, self.life / self.max_life)
        alpha = int(255 * t)
        r = max(1, int(self.radius * t))
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (r, r), r)
        surface.blit(s, (self.x - cam_x - r, self.y - cam_y - r))


# ─────────────────────────────────────────────────────────────────────────────
class BossShockwave:
    """Ground shockwave traveling along the floor created by Boss Jump Slam."""
    def __init__(self, x: float, y: float, moving_right: bool):
        self.rect = pygame.FRect(x, y - 20, 36, 40)
        self.velocity_x = 200.0 if moving_right else -200.0
        self.active = True
        self.damage = 35
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


# ─────────────────────────────────────────────────────────────────────────────
class SkeletonBoss:
    """Epic Skeleton King Boss with Multi-Phase AI and Dynamic Skills."""
    def __init__(self, x: float, y: float):
        self.pos = pygame.math.Vector2(x, y)
        self.velocity = pygame.math.Vector2(0, 0)
        self.rect = pygame.FRect(x, y, 54, 96)
        
        self.max_health = 20000 # Epic 20,000 HP boss
        self.health = self.max_health
        self.max_shield = 2000  # 2,000 Poise Shield
        self.shield = self.max_shield
        self.shield_recharge_cooldown = 0.0 # 20s cooldown after stagger before shield recharge begins
        self.attack_damage = 35 # Sword cleave damage (35)
        self.touch_damage = 0   # No contact/body collision damage
        self.is_dead = False
        self.facing_right = False
        self.enraged = False
        self.hit_count = 0
        self.potions_to_spawn = []
        self.potion_dropped_50 = False # Drop only 1 potion at 50% HP
        self.slow_timer = 0.0
        self.slow_factor = 1.0
        
        # Ignis Burn passive support
        self.burn_timer = 0.0
        self.burn_dps = 0.0
        self.burn_tick_timer = 0.0
        
        # Boss Combat & AI State
        self.state = "IDLE" # IDLE, CHASE, ATTACK, FLAME_BURST, JUMP_SLAM, ROAR, STAGGERED
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
        
        # Stun VFX Animation
        vfx_stun_path = os.path.join("assets", "sprites", "vfx", "vfx_stun")
        self.stun_anim = load_animation_folder(vfx_stun_path, "vfx_stun", 16, True, 1.4)
        
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

        # ── VFX state ──────────────────────────────────────────────────────
        self._time = 0.0
        self._particles: list[_BossParticle] = []

        # FLAME_BURST: necromantic ground summoning circle
        self._flame_charge = 0.0          # 0→1 charge progress
        self._flame_sigil_angle = 0.0     # rotating pentagram/rune
        self._flame_active = False

        # JUMP_SLAM: impact debris
        self._slam_impact_timer = 0.0     # countdown for crater flash
        self._slam_debris: list[_BossParticle] = []

        # SHADOW_STEP: vortex after-images
        self._shadow_afterimages: list[dict] = []  # {surf, x, y, alpha, timer}
        self._shadow_vortex_particles: list[_BossParticle] = []
        self._shadow_arrive_flash = 0.0   # timer for arrival burst

        # ROAR / ENRAGE: shockwave ring + flame aura
        self._roar_ring_radius = 0.0      # expanding ring on roar
        self._roar_ring_timer = 0.0
        self._enrage_flame_particles: list[_BossParticle] = []

        # ATTACK melee: giant slash arc
        self._melee_slash_timer = 0.0
        self._melee_slash_dir = 1
        self._attack_windup = 0.0  # telegraph pause before lunge

    @property
    def poise_shield(self) -> int:
        return self.shield

    @poise_shield.setter
    def poise_shield(self, val: int):
        self.shield = val

    @property
    def is_staggered(self) -> bool:
        return self.state == "STAGGERED"

    # ──────────────────────────────────────────────────────────────────────────
    def apply_slow(self, duration: float = 2.5, factor: float = 0.35):
        """Applies slow-motion status effect from player Ultimate skill."""
        if not self.is_dead:
            self.slow_timer = max(self.slow_timer, duration)
            self.slow_factor = factor

    def apply_burn(self, duration: float = 4.0, dps: float = 3.0):
        """Applies burn damage over time (Ignis passive)."""
        if not self.is_dead:
            self.burn_timer = max(self.burn_timer, duration)
            self.burn_dps = dps

    def take_damage(self, amount: int):
        if self.is_dead:
            return
            
        self.hit_count += 1
        
        # Poise Shield absorption:
        if self.shield > 0:
            self.shield -= amount
            if self.shield <= 0:
                self.shield = 0
                self.shield_recharge_cooldown = 20.0 # 20 seconds cooldown before shield can start regenerating
                self.state = "STAGGERED"
                self.state_timer = 4.5
                self.velocity.x = 0
                self.anim_manager.play("hurt", force_reset=True)
        else:
            # Shield is down: direct damage to HP
            self.health -= amount
            if self.health <= 0:
                self.health = 0
                self.is_dead = True
                self.state = "DEAD"
                self.anim_manager.play("dead", force_reset=True)
                self.velocity.x = 0
                self.velocity.y = -100
                return
                
            # Check Enrage at 50% HP (10,000 HP)
            if self.health <= self.max_health // 2 and not self.enraged:
                self.enraged = True
                self.state = "ROAR"
                self.state_timer = 1.0
                self.anim_manager.play("cast", force_reset=True)
                # ROAR: expanding shockwave ring
                self._roar_ring_radius = 5.0
                self._roar_ring_timer = 0.7
                self._spawn_roar_burst()

        # Drop ONLY ONE healing potion when health drops to 50% or below per user request!
        if self.health <= self.max_health // 2 and not self.potion_dropped_50:
            self.potion_dropped_50 = True
            self.potions_to_spawn.append((self.rect.centerx, self.rect.centery - 20))
            
        # Check Minion Reinforcements
        if self.health <= 15000 and not self.summoned_75:
            self.summoned_75 = True
            self.minions_to_spawn.extend([("skeleton", self.rect.x - 120), ("mage", self.rect.x + 120)])
        if self.health <= 10000 and not self.summoned_50:
            self.summoned_50 = True
            self.minions_to_spawn.extend([("boar", self.rect.x - 140), ("mage", self.rect.x + 140)])
        if self.health <= 5000 and not self.summoned_25:
            self.summoned_25 = True
            self.minions_to_spawn.extend([("mage", self.rect.x - 160), ("mage", self.rect.x + 160)])

    # ── VFX helpers ────────────────────────────────────────────────────────
    def _spawn_roar_burst(self):
        """Spawn explosion of crimson energy when enrage triggers."""
        cx, cy = self.rect.centerx, self.rect.centery
        for _ in range(30):
            angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(80, 220)
            color = random.choice([(255, 60, 30), (255, 140, 50), (255, 200, 80)])
            self._particles.append(_BossParticle(cx, cy, math.cos(angle)*spd, math.sin(angle)*spd,
                                                 random.uniform(0.4, 0.9), color, radius=random.uniform(3, 7), gravity=180))

    def _spawn_flame_particles(self):
        """Soul particles sucked toward boss hands during FLAME_BURST charge."""
        cx = self.rect.centerx
        base_y = self.rect.bottom
        spread = 180
        for _ in range(5):
            ox = random.uniform(-spread, spread)
            oy = random.uniform(-30, 30)
            px, py = cx + ox, base_y + oy
            # Aim toward hands
            hx = cx + (22 if self.facing_right else -22)
            hy = self.rect.centery - 10
            dx, dy = hx - px, hy - py
            dist = max(1, math.hypot(dx, dy))
            spd = random.uniform(90, 170)
            color = random.choice([(140, 40, 255), (200, 60, 255), (80, 0, 180)])
            self._particles.append(_BossParticle(px, py, (dx/dist)*spd, (dy/dist)*spd,
                                                 random.uniform(0.2, 0.45), color, radius=random.uniform(2, 5), gravity=0))

    def _spawn_flame_burst_explosion(self):
        """Detonation flash when fireballs are fired."""
        hx = self.rect.centerx + (25 if self.facing_right else -25)
        hy = self.rect.centery - 10
        for _ in range(22):
            angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(60, 180)
            color = random.choice([(255, 80, 30), (255, 160, 40), (200, 40, 255), (255, 230, 60)])
            self._particles.append(_BossParticle(hx, hy, math.cos(angle)*spd, math.sin(angle)*spd,
                                                 random.uniform(0.22, 0.5), color, radius=random.uniform(3, 7), gravity=120))

    def _spawn_slam_debris(self):
        """Bone and rock debris flying from slam impact."""
        cx, cy = self.rect.centerx, self.rect.bottom
        for _ in range(20):
            angle = random.uniform(-math.pi + 0.2, -0.2)  # upward cone
            spd = random.uniform(100, 300)
            color = random.choice([(220, 210, 190), (160, 140, 110), (100, 90, 80), (255, 80, 20)])
            self._slam_debris.append(_BossParticle(cx, cy, math.cos(angle)*spd, math.sin(angle)*spd,
                                                   random.uniform(0.5, 1.1), color, radius=random.uniform(2, 5), gravity=550))

    def _spawn_shadow_vortex(self, x, y, is_arrival):
        """Purple void particles for teleport departure/arrival."""
        for _ in range(18):
            angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(40, 100)
            inward = -1 if not is_arrival else 1
            color = random.choice([(120, 0, 200), (180, 50, 255), (60, 0, 140)])
            vx = math.cos(angle) * spd * inward
            vy = math.sin(angle) * spd * inward - 20
            self._shadow_vortex_particles.append(_BossParticle(x, y, vx, vy,
                                                               random.uniform(0.3, 0.55), color, radius=random.uniform(3, 6), gravity=0))

    def _spawn_enrage_flames(self):
        """Continuous demonic flame particles rising from boss shoulders while enraged."""
        for side in [-18, 18]:
            ox = self.rect.centerx + side
            oy = self.rect.top + 10
            color = random.choice([(255, 80, 30), (255, 50, 20), (200, 30, 200), (255, 160, 30)])
            vx = random.uniform(-20, 20)
            vy = random.uniform(-70, -140)
            self._enrage_flame_particles.append(_BossParticle(ox, oy, vx, vy,
                                                              random.uniform(0.25, 0.55), color, radius=random.uniform(2.5, 5), gravity=-50))

    # ──────────────────────────────────────────────────────────────────────────
    def update(self, dt: float, tiles: list[pygame.FRect], player = None):
        self._time += dt

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
                
        # ── VFX updates ──────────────────────────────────────────────────
        # Roar ring decay
        if self._roar_ring_timer > 0:
            self._roar_ring_timer -= dt
            self._roar_ring_radius += dt * 320

        # Slam impact crater flash timer
        if self._slam_impact_timer > 0:
            self._slam_impact_timer -= dt

        # Enrage continuous flames
        if self.enraged and not self.is_dead and random.random() < 0.6:
            self._spawn_enrage_flames()

        # Flame burst charge VFX
        if self._flame_active:
            self._flame_charge = min(1.0, self._flame_charge + dt * 1.6)
            self._flame_sigil_angle += dt * 2.5
            if random.random() < 0.55:
                self._spawn_flame_particles()

        # Melee slash timer decay
        if self._melee_slash_timer > 0:
            self._melee_slash_timer -= dt

        # Shadow arrive flash decay
        if self._shadow_arrive_flash > 0:
            self._shadow_arrive_flash -= dt

        # Update all particle lists
        self._particles = [p for p in self._particles if p.update(dt)]
        self._slam_debris = [p for p in self._slam_debris if p.update(dt)]
        self._shadow_vortex_particles = [p for p in self._shadow_vortex_particles if p.update(dt)]
        self._enrage_flame_particles = [p for p in self._enrage_flame_particles if p.update(dt)]
        # Decay after-images
        for ai in self._shadow_afterimages:
            ai["timer"] -= dt
        self._shadow_afterimages = [ai for ai in self._shadow_afterimages if ai["timer"] > 0]

        # Update shockwaves
        for sw in self.shockwaves[:]:
            sw.update(dt, tiles)
            if not sw.active:
                self.shockwaves.remove(sw)
            elif player and sw.rect.colliderect(player.rect):
                player.take_damage(sw.damage)
                sw.active = False
                self.shockwaves.remove(sw)

        # Burn damage tick (Ignis passive)
        if self.burn_timer > 0 and not self.is_dead:
            self.burn_timer -= dt
            self.burn_tick_timer += dt
            if self.burn_tick_timer >= 1.0:
                self.burn_tick_timer = 0.0
                self.take_damage(int(round(self.burn_dps)))
            if random.random() < 0.25:
                bx = self.rect.centerx + random.uniform(-16, 16)
                by = self.rect.centery + random.uniform(-25, 25)
                self._particles.append(_BossParticle(bx, by, random.uniform(-10, 10), random.uniform(-40, -80), 0.35, (255, 120, 20), radius=2.5, gravity=-20))

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
        if self.shield_recharge_cooldown > 0:
            self.shield_recharge_cooldown -= dt
            if self.shield_recharge_cooldown <= 0 and self.shield <= 0 and self.state != "STAGGERED" and not self.is_dead:
                # 20s cooldown elapsed after stagger: restore 2,000 shield and roar
                self.shield = self.max_shield
                self.state = "ROAR"
                self.state_timer = 1.0
                self.anim_manager.play("cast", force_reset=True)
                self._roar_ring_radius = 5.0
                self._roar_ring_timer = 0.7
                self._spawn_roar_burst()
            
        if player:
            self.facing_right = player.rect.centerx > self.rect.centerx
            dx = player.rect.centerx - self.rect.centerx
            dist = abs(dx)
            
            speed_mult = 1.35 if self.enraged else 1.0
            
            # State Machine
            if self.state == "STAGGERED":
                self.velocity.x = 0
                self.state_timer -= dt
                self.anim_manager.play("hurt")
                self.stun_anim.update(effective_dt)
                if self.state_timer <= 0:
                    # Stagger stun ends: boss resumes action without shield (shield has 20s recharge cooldown)
                    self.state = "CHASE"
                    self.anim_manager.play("walk", force_reset=True)
                    if dist < 140:
                        repel_dir = 1 if player.rect.centerx > self.rect.centerx else -1
                        player.velocity.x = repel_dir * 320
                        player.velocity.y = -180

            elif self.state == "IDLE":
                self.anim_manager.play("idle")
                self.velocity.x = 0
                self.state_timer -= dt
                if self.state_timer <= 0:
                    self.state = "CHASE"
                    
            elif self.state == "CHASE":
                self.anim_manager.play("walk")
                self.velocity.x = (90.0 * speed_mult) if self.facing_right else (-90.0 * speed_mult)
                
                # Check Melee Attack (35 damage) — wind-up gives player time to run!
                if dist < 75 and self.attack_cooldown <= 0:
                    self.state = "ATTACK"
                    self.has_hit_player = False
                    self.velocity.x = 0  # stop during wind-up
                    self.anim_manager.play("attack", force_reset=True)
                    self._melee_slash_timer = 0.0  # reset
                    self._attack_windup = 1.0  # 1.0s telegraph before lunge
                    
                # Check Special Skills (No teleport; ground pursuit only!)
                elif self.skill_cooldown <= 0:
                    chosen_skill = random.choice(["FLAME_BURST", "JUMP_SLAM"])
                    self.state = chosen_skill
                    self.state_timer = 0.0
                    self.skill_cooldown = 2.8 if not self.enraged else 1.8
                    
                    if chosen_skill == "FLAME_BURST":
                        self.velocity.x = 0
                        self.anim_manager.play("cast", force_reset=True)
                        self.state_timer = 0.75 # Telegraph cast wind-up!
                        self._flame_active = True
                        self._flame_charge = 0.0
                        
                    elif chosen_skill == "JUMP_SLAM":
                        self.velocity.y = -560 # Heavy jump slam
                        self.velocity.x = (160.0 * speed_mult) if self.facing_right else (-160.0 * speed_mult)
                        self.anim_manager.play("jump", force_reset=True)
                        
            elif self.state == "ATTACK":
                # Wind-up telegraph: boss is stationary letting player react
                if self._attack_windup > 0:
                    self._attack_windup -= dt
                    self.velocity.x = 0
                else:
                    # Lunge phase after wind-up
                    self.velocity.x = (140.0 * speed_mult) if self.facing_right else (-140.0 * speed_mult)
                cur_frame = self.anim_manager.animations["attack"].current_frame
                # Trigger melee slash arc at frame 4 (late in animation)
                if cur_frame >= 4 and self._melee_slash_timer <= 0:
                    self._melee_slash_timer = 0.22
                    self._melee_slash_dir = 1 if self.facing_right else -1
                if self.anim_manager.is_finished("attack"):
                    self.state = "IDLE"
                    self.state_timer = 0.5
                    self.attack_cooldown = 2.0 if not self.enraged else 1.2
                    
            elif self.state == "FLAME_BURST":
                self.velocity.x = 0
                self.state_timer -= dt
                if self.state_timer <= 0:
                    # Shoot 3 fireballs (85 dmg each)
                    proj_x = self.rect.right if self.facing_right else self.rect.left - 24
                    proj_y = self.rect.centery - 10
                    
                    p1 = Projectile(proj_x, proj_y, self.facing_right, is_enemy=True, projectile_type="boss_fireball")
                    p2 = Projectile(proj_x, proj_y - 28, self.facing_right, is_enemy=True, projectile_type="boss_fireball")
                    p3 = Projectile(proj_x, proj_y + 28, self.facing_right, is_enemy=True, projectile_type="boss_fireball")
                    
                    self.projectiles.extend([p1, p2, p3])
                    # Explosion VFX
                    self._spawn_flame_burst_explosion()
                    self._flame_active = False
                    self._flame_charge = 0.0
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
                    
                    # If was jump-slamming, create shockwaves and deal crater impact upon hitting ground!
                    if self.state == "JUMP_SLAM":
                        self.state = "IDLE"
                        self.state_timer = 0.6
                        self.anim_manager.play("slam", force_reset=True)
                        # Shockwaves left and right (deal 35 dmg)
                        sw_left = BossShockwave(self.rect.left, self.rect.bottom, moving_right=False)
                        sw_right = BossShockwave(self.rect.right, self.rect.bottom, moving_right=True)
                        self.shockwaves.extend([sw_left, sw_right])
                        # Heavy crater impact damage: 85 dmg if caught in direct slam impact
                        if player and abs(player.rect.centerx - self.rect.centerx) < 70 and abs(player.rect.bottom - self.rect.bottom) < 40:
                            player.take_damage(85)
                        # Slam debris particles
                        self._spawn_slam_debris()
                        self._slam_impact_timer = 0.22
                        
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

    # ── Draw Helpers ──────────────────────────────────────────────────────
    def _draw_flame_sigil(self, surface, cam_x, cam_y):
        """Necromantic summoning circle on the ground during FLAME_BURST charge."""
        if not self._flame_active or self._flame_charge <= 0:
            return
        t = self._flame_charge
        alpha = max(0, min(255, int(200 * min(1.0, t * 2))))
        radius = int(30 + t * 36)
        cx = self.rect.centerx - cam_x
        cy = self.rect.bottom - cam_y - 4  # on ground level

        sigil_surf = pygame.Surface((radius * 2 + 12, radius * 2 + 12), pygame.SRCALPHA)
        rc = radius + 6

        # Outer circle
        pygame.draw.circle(sigil_surf, (140, 30, 200, alpha), (rc, rc), radius, 2)
        pygame.draw.circle(sigil_surf, (200, 60, 255, max(0, min(255, alpha // 2))), (rc, rc), radius - 6, 1)

        # Pentagram / star rune spokes
        num_pts = 5
        for i in range(num_pts):
            angle = self._flame_sigil_angle + (i * 2 * math.pi / num_pts)
            # Outer pt → inner pt (offset by 2 spokes) for star
            angle2 = self._flame_sigil_angle + ((i + 2) * 2 * math.pi / num_pts)
            sx = rc + int(math.cos(angle) * radius)
            sy = rc + int(math.sin(angle) * radius)
            ex = rc + int(math.cos(angle2) * radius)
            ey = rc + int(math.sin(angle2) * radius)
            pygame.draw.line(sigil_surf, (180, 50, 255, alpha), (sx, sy), (ex, ey), 1)

        # Pulsing inner glow
        pulse = 0.5 + 0.5 * math.sin(self._time * 6)
        if radius > 10:
            inner_r = radius // 2
            ig = pygame.Surface((inner_r * 2, inner_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(ig, (200, 80, 255, max(0, min(255, int(90 * pulse * min(1.0, t * 2))))), (inner_r, inner_r), inner_r)
            sigil_surf.blit(ig, (rc - inner_r, rc - inner_r))

        surface.blit(sigil_surf, (cx - rc, cy - 8))

    def _draw_melee_slash_arc(self, surface, cam_x, cam_y):
        """Giant dark crimson slash arc during boss melee attack."""
        if self._melee_slash_timer <= 0:
            return
        progress = max(0.0, min(1.0, self._melee_slash_timer / 0.22))
        alpha = max(0, min(255, int(210 * progress)))
        arc_r = 44
        start_angle = -math.pi * 0.6
        span = math.pi * 1.2
        if self._melee_slash_dir < 0:
            start_angle = math.pi - (-math.pi * 0.6) - math.pi * 1.2
            span = -math.pi * 1.2

        cx = self.rect.centerx - cam_x + self._melee_slash_dir * arc_r * 0.5
        cy = self.rect.centery - cam_y - 10

        rect_size = arc_r * 2 + 12
        arc_surf = pygame.Surface((rect_size + 12, rect_size + 12), pygame.SRCALPHA)
        for gw, col in [
            (11, (200, 30, 10, max(0, min(255, alpha // 4)))),
            (7,  (255, 70, 20, max(0, min(255, alpha // 2)))),
            (3,  (255, 180, 60, alpha)),
        ]:
            pygame.draw.arc(arc_surf, col,
                            pygame.Rect(6, 6, rect_size, rect_size),
                            start_angle, start_angle + span, gw)
        surface.blit(arc_surf, (cx - rect_size // 2 - 6, cy - rect_size // 2 - 6))

    def _draw_shadow_arrive_flash(self, surface, cam_x, cam_y):
        """Purple lightning burst when shadow-stepping to arrival point."""
        if self._shadow_arrive_flash <= 0:
            return
        t = max(0.0, min(1.0, self._shadow_arrive_flash / 0.28))
        alpha = max(0, min(255, int(220 * t)))
        radius = int(50 * t)
        cx = self.rect.centerx - cam_x
        cy = self.rect.centery - cam_y
        if radius > 0:
            fs = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(fs, (180, 40, 255, alpha), (radius, radius), radius)
            pygame.draw.circle(fs, (255, 200, 255, max(0, min(255, alpha // 2))), (radius, radius), radius // 2)
            surface.blit(fs, (cx - radius, cy - radius))

    def _draw_roar_ring(self, surface, cam_x, cam_y):
        """Expanding shockwave ring on ROAR trigger."""
        if self._roar_ring_timer <= 0:
            return
        t = max(0, self._roar_ring_timer / 0.7)
        alpha = int(180 * t)
        r = int(self._roar_ring_radius)
        if r < 2:
            return
        cx = self.rect.centerx - cam_x
        cy = self.rect.centery - cam_y
        rs = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(rs, (255, 80, 30, alpha), (r + 2, r + 2), r, 4)
        surface.blit(rs, (cx - r - 2, cy - r - 2))

    def _draw_slam_impact(self, surface, cam_x, cam_y):
        """White crater flash immediately after slam landing."""
        if self._slam_impact_timer <= 0:
            self._slam_impact_timer -= 0  # allow negative to be used as guard
            return
        self._slam_impact_timer -= 0  # timer decremented in update via particle system decay
        # Actually just use a separate timer (decremented in update of _draw)
        t = max(0, self._slam_impact_timer / 0.18)
        alpha = int(200 * t)
        r = int(55 * t)
        if r < 2:
            return
        cx = self.rect.centerx - cam_x
        cy = self.rect.bottom - cam_y - 5
        rs = pygame.Surface((r * 2, r * 2 // 2 + 2), pygame.SRCALPHA)
        pygame.draw.ellipse(rs, (255, 200, 100, alpha), (0, 0, r * 2, max(4, r // 2)))
        surface.blit(rs, (cx - r, cy - r // 4))

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        cam_x, cam_y = camera_offset.x, camera_offset.y

        # ── Ground-level VFX (draw before sprite) ────────────────────────
        # Flame sigil
        self._draw_flame_sigil(surface, cam_x, cam_y)

        # Shadow after-images (ghost silhouettes fading out)
        for ai in self._shadow_afterimages:
            t = max(0, ai["timer"] / 0.45)
            ghost = ai["surf"].copy()
            ghost.set_alpha(int(160 * t))
            tinted = ghost.copy()
            tinted.fill((120, 0, 200), special_flags=pygame.BLEND_RGBA_MULT)
            gw, gh = ghost.get_size()
            surface.blit(tinted, (ai["x"] - cam_x - gw // 2, ai["y"] - cam_y - gh))

        # Draw shockwaves
        for sw in self.shockwaves:
            sw.draw(surface, camera_offset)

        # Slam debris particles
        for p in self._slam_debris:
            p.draw(surface, cam_x, cam_y)

        # Shadow vortex particles
        for p in self._shadow_vortex_particles:
            p.draw(surface, cam_x, cam_y)

        # Draw teleport smoke puff
        if self.smoke_active:
            smoke_frame = self.smoke_anim.get_current_frame()
            if smoke_frame:
                s_rect = smoke_frame.get_rect(center=(self.smoke_pos.x - cam_x, self.smoke_pos.y - cam_y))
                surface.blit(smoke_frame, s_rect)

        # Roar ring
        self._draw_roar_ring(surface, cam_x, cam_y)

        # Melee slash arc (behind sprite so arc wraps around)
        self._draw_melee_slash_arc(surface, cam_x, cam_y)

        # ── Main sprite ───────────────────────────────────────────────────
        img = self.anim_manager.get_current_frame()
        img_rect = img.get_rect()
        draw_x = self.rect.centerx - cam_x - img_rect.width / 2
        draw_y = self.rect.bottom - cam_y - img_rect.height
        
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

        # ── Foreground VFX (draw after sprite) ───────────────────────────
        # Poise Shield Barrier Aura
        if self.shield > 0 and not self.is_dead:
            pulse = 0.75 + 0.25 * math.sin(self._time * 4)
            sh_w = int(self.rect.width + 30 + 6 * pulse)
            sh_h = int(self.rect.height + 24 + 6 * pulse)
            sh_surf = pygame.Surface((sh_w, sh_h), pygame.SRCALPHA)
            pygame.draw.ellipse(sh_surf, (80, 210, 255, int(40 * pulse)), (0, 0, sh_w, sh_h))
            pygame.draw.ellipse(sh_surf, (255, 215, 80, int(120 * pulse)), (0, 0, sh_w, sh_h), 2)
            surface.blit(sh_surf, (self.rect.centerx - cam_x - sh_w // 2, self.rect.centery - cam_y - sh_h // 2))

        # Staggered stun stars over head
        if self.state == "STAGGERED" and not self.is_dead:
            stun_frame = self.stun_anim.get_current_frame()
            if stun_frame:
                sf_rect = stun_frame.get_rect(center=(self.rect.centerx - cam_x, self.rect.top - cam_y - 16))
                surface.blit(stun_frame, sf_rect)

        # Slam impact crater flash (draw only while timer > 0)
        if self._slam_impact_timer > 0:
            self._draw_slam_impact(surface, cam_x, cam_y)

        # General particles (flame explosion, roar burst)
        for p in self._particles:
            p.draw(surface, cam_x, cam_y)

        # Enrage flame aura over boss
        for p in self._enrage_flame_particles:
            p.draw(surface, cam_x, cam_y)
