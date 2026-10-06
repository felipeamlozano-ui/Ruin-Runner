import pygame
import os
import math
import random
from config.constants import GRAVITY, MAX_FALL_SPEED
from engine.animation import AnimationManager, load_spritesheet
import engine.resource_manager as rm

# ─────────────────────────────────────────────────────────────────────────────
# Visual Debug Toggle
# ─────────────────────────────────────────────────────────────────────────────
DEBUG_BOSS = False

# ─────────────────────────────────────────────────────────────────────────────
# Lightweight particle for VFX
# ─────────────────────────────────────────────────────────────────────────────
class _BossParticle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "radius", "gravity")
    def __init__(self, x: float, y: float, vx: float, vy: float, life: float, color: tuple, radius: float = 3.0, gravity: float = 0.0):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = float(vx), float(vy)
        self.life = self.max_life = float(life)
        self.color = color
        self.radius = float(radius)
        self.gravity = float(gravity)

    def update(self, dt: float) -> bool:
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        t = max(0.0, self.life / self.max_life)
        alpha = int(255 * t)
        r = max(1, int(self.radius * t))
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (r, r), r)
        surface.blit(s, (self.x - cam_x - r, self.y - cam_y - r))


# ─────────────────────────────────────────────────────────────────────────────
class BossShockwave:
    """Ground shockwave traveling along the floor created by Boss attacks."""
    def __init__(self, x: float, y: float, moving_right: bool, speed: float = 200.0, damage: int = 35):
        self.rect = pygame.FRect(x, y - 24, 40, 44)
        self.velocity_x = speed if moving_right else -speed
        self.active = True
        self.damage = damage
        self.moving_right = moving_right
        self.lifetime = 2.4
        
    def update(self, dt: float, tiles: list[pygame.FRect] = None):
        if not self.active:
            return
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.active = False
            return
        self.rect.x += self.velocity_x * dt
        if tiles:
            for t in tiles:
                if t.width < 100 and self.rect.colliderect(t):
                    self.active = False
                    break
                    
    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if self.active:
            s = pygame.Surface((int(self.rect.width), int(self.rect.height)), pygame.SRCALPHA)
            pygame.draw.ellipse(s, (255, 80, 20, 200), (0, 0, int(self.rect.width), int(self.rect.height)))
            surface.blit(s, (self.rect.x - camera_offset.x, self.rect.y - camera_offset.y))


# ─────────────────────────────────────────────────────────────────────────────
# Main Skeleton King Boss Entity
# ─────────────────────────────────────────────────────────────────────────────
class SkeletonBoss:
    """
    Official Skeleton King Boss for Ruin Runner.
    Utilizes exclusively the three official spritesheets provided:
      - SPRITESHEET 1: Idle, Hurt, Death, Walk
      - SPRITESHEET 2: Attack1, Run, Attack2, Special
      - SPRITESHEET 3: Attack3, Attack4, Jump
    
    Features:
      - 1:1 Pixel art preservation with solid background cleanly removed.
      - Mathematical foot-anchor point guaranteeing 0 pixel sliding or bouncing.
      - Full state machine: IDLE, CHASE, WALK, RUN, ATTACK_1, ATTACK_2, ATTACK_3,
        ATTACK_4, SPECIAL, JUMP, HURT, DEATH.
      - 2-Phase combat progression (Phase 1 >50% HP, Phase 2 <=50% HP Enraged).
      - Per-frame synchronized attack hitboxes with startups and recoveries.
      - Trajectory jump physics with landing impact and screen shake.
      - Visual debug overlay with DEBUG_BOSS = True.
    """
    def __init__(self, x: float, y: float):
        self.pos = pygame.math.Vector2(x, y)
        self.velocity = pygame.math.Vector2(0, 0)
        # Hitbox (55, 110) scaled 20% larger than previous (46, 92)
        self.scale = 1.20
        self.rect = pygame.FRect(x, y, 55, 110)
        
        # Health & Poise Shield Balance
        self.max_health = 20000
        self.health = self.max_health
        self.max_shield = 1000
        self.shield = self.max_shield
        self.shield_recharge_cooldown = 0.0
        
        self.name = "Cavaleiro Negro / Espadachim Carmesim"
        self.attack_damage = 35
        self.touch_damage = 0  # No unfair contact damage
        self.is_dead = False
        self.facing_right = False
        self.on_ground = False
        
        # Super Armor / Poise
        self.can_interrupt = True
        self.windup_timer = 0.0
        self.windup_target = ""
        self._afterimages: list[tuple[pygame.Surface, float, float, float]] = []  # (surface, x, y, alpha)
        
        # Two-Phase System
        self.current_phase = 1
        self.enraged = False
        self.potion_dropped_50 = False
        self.potions_to_spawn = []
        self.minions_to_spawn = []
        
        # Status effects
        self.slow_timer = 0.0
        self.slow_factor = 1.0
        self.burn_timer = 0.0
        self.burn_dps = 0.0
        self.burn_tick_timer = 0.0
        self.invulnerable_timer = 0.0
        
        # Speeds & Ranges
        self.walk_speed = 110.0
        self.run_speed_p1 = 210.0
        self.run_speed_p2 = 290.0
        self.dash_speed = 460.0
        self.combo_count = 0
        self.vision_range = 800.0
        self.attack_range_melee = 110.0
        
        # Combat Cooldowns & AI Timers
        self.state = "IDLE"
        self.state_timer = 0.0
        self.attack_cooldown = 0.8
        self.special_cooldown = 4.0
        self.jump_cooldown = 3.0
        self.dash_cooldown = 2.5
        self.decision_timer = 0.2
        self.has_dealt_damage_in_attack = False
        self.camera_shake_triggered = False
        
        # Animation & Anchor configuration
        # Canvas: 192x160 base, scaled 1.20x. Anchor scaled: (90, 180) right, (139, 180) left.
        self.frame_width = 192
        self.frame_height = 160
        self.anchor_x_right = int(75 * self.scale)  # 90
        self.anchor_x_left = int(116 * self.scale)  # 139
        self.anchor_y = int(150 * self.scale)       # 180
        
        self.anim_manager = AnimationManager()
        self._load_all_animations()
        self.anim_manager.play("idle")
        
        # VFX & Sounds
        self._time = 0.0
        self._particles: list[_BossParticle] = []
        self._enrage_particles: list[_BossParticle] = []
        self.projectiles = []
        self.shockwaves = []
        
        # Font for Debug Rendering
        self._debug_font = None
        try:
            self._debug_font = pygame.font.SysFont("Consolas", 13, bold=True)
        except Exception:
            self._debug_font = pygame.font.Font(None, 18)

    def _load_all_animations(self):
        """Loads and caches all 11 official Boss animations from extracted assets scaled 1.20x."""
        boss_dir = os.path.join("assets", "sprites", "bosses", "skeleton_king")
        FW, FH = self.frame_width, self.frame_height
        sc = self.scale
        
        self.anim_manager.add_animation("idle",     load_spritesheet(os.path.join(boss_dir, "idle.png"), FW, FH, fps=8,  loop=True, scale=sc))
        self.anim_manager.add_animation("hurt",     load_spritesheet(os.path.join(boss_dir, "hurt.png"), FW, FH, fps=14, loop=False, scale=sc))
        self.anim_manager.add_animation("dead",     load_spritesheet(os.path.join(boss_dir, "death.png"), FW, FH, fps=7, loop=False, scale=sc))
        self.anim_manager.add_animation("walk",     load_spritesheet(os.path.join(boss_dir, "walk.png"), FW, FH, fps=11, loop=True, scale=sc))
        self.anim_manager.add_animation("run",      load_spritesheet(os.path.join(boss_dir, "run.png"), FW, FH, fps=15, loop=True, scale=sc))
        self.anim_manager.add_animation("attack1",  load_spritesheet(os.path.join(boss_dir, "attack1.png"), FW, FH, fps=15, loop=False, scale=sc))
        self.anim_manager.add_animation("attack2",  load_spritesheet(os.path.join(boss_dir, "attack2.png"), FW, FH, fps=15, loop=False, scale=sc))
        self.anim_manager.add_animation("attack3",  load_spritesheet(os.path.join(boss_dir, "attack3.png"), FW, FH, fps=14, loop=False, scale=sc))
        self.anim_manager.add_animation("attack4",  load_spritesheet(os.path.join(boss_dir, "attack4.png"), FW, FH, fps=14, loop=False, scale=sc))
        self.anim_manager.add_animation("special",  load_spritesheet(os.path.join(boss_dir, "special.png"), FW, FH, fps=10, loop=False, scale=sc))
        self.anim_manager.add_animation("jump",     load_spritesheet(os.path.join(boss_dir, "jump.png"), FW, FH, fps=10, loop=False, scale=sc))

    @property
    def hp(self) -> float:
        return self.health

    @hp.setter
    def hp(self, val: float):
        self.health = val

    @property
    def max_hp(self) -> float:
        return self.max_health

    @property
    def poise_shield(self) -> int:
        return self.shield

    @poise_shield.setter
    def poise_shield(self, val: int):
        self.shield = val

    @property
    def is_staggered(self) -> bool:
        return self.state == "HURT" or self.shield <= 0

    def apply_burn(self, duration: float = 4.0, dps: float = 4.0):
        if not self.is_dead:
            self.burn_timer = max(self.burn_timer, duration)
            self.burn_dps = dps

    def apply_slow(self, duration: float = 2.5, factor: float = 0.35):
        if not self.is_dead:
            self.slow_timer = max(self.slow_timer, duration)
            self.slow_factor = factor

    def take_damage(self, amount: int, hit_direction: int = 0):
        if self.is_dead:
            return
            
        self.invulnerable_timer = 0.12
        
        # Shield absorbs damage first, overflow damages health
        if self.shield > 0:
            self.shield_recharge_cooldown = 4.0
            if amount <= self.shield:
                self.shield -= amount
            else:
                overflow = amount - self.shield
                self.shield = 0
                self.shield_recharge_cooldown = 7.0
                self.health -= overflow
                # Shield break impact
                for _ in range(12):
                    self._particles.append(_BossParticle(
                        self.rect.centerx, self.rect.centery,
                        random.uniform(-140, 140), random.uniform(-180, 50),
                        0.4, (255, 215, 80), radius=3.5, gravity=300
                    ))
        else:
            self.health -= amount
            
        # Spawn hit sparks
        for _ in range(6):
            self._particles.append(_BossParticle(
                self.rect.centerx, self.rect.centery - 20,
                random.uniform(-100, 100), random.uniform(-120, 20),
                0.25, (255, 60, 40), radius=2.5, gravity=250
            ))
            
        # Phase 2 Enrage Trigger at 50% HP
        if self.health <= self.max_health * 0.50 and not self.enraged:
            self._trigger_phase_two_enrage()
            
        # Potion drop at 50% HP
        if self.health <= self.max_health * 0.50 and not self.potion_dropped_50:
            self.potion_dropped_50 = True
            self.potions_to_spawn.append((self.rect.centerx - 40, self.rect.centery))
            self.potions_to_spawn.append((self.rect.centerx + 40, self.rect.centery))
            
        if self.health <= 0:
            self.health = 0
            self.die()
        elif not self.can_interrupt:
            # Super Armor: During heavy attacks and gap closers, normal hits DO NOT interrupt
            pass
        elif self.state not in ("ATTACK_1", "ATTACK_2", "ATTACK_3", "ATTACK_4", "SPECIAL", "JUMP", "DASH", "WINDUP", "DEATH", "HURT"):
            # Only stagger when poise shield is depleted
            if self.shield <= 0:
                self.change_state("HURT")

    def _trigger_phase_two_enrage(self):
        """Enters Phase 2: Increases speed, lowers cooldowns, unlocks Attack3/4/Special."""
        self.enraged = True
        self.current_phase = 2
        self.attack_cooldown = 0.3
        
        # Minion reinforcements
        self.minions_to_spawn.append(("spearman", self.rect.centerx - 180))
        self.minions_to_spawn.append(("archer", self.rect.centerx + 180))
        
        # Massive eruption of flame particles
        for _ in range(30):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(80, 240)
            self._enrage_particles.append(_BossParticle(
                self.rect.centerx, self.rect.centery,
                math.cos(ang) * spd, math.sin(ang) * spd - 60,
                random.uniform(0.4, 0.9), (255, 80, 20), radius=random.uniform(3, 6), gravity=150
            ))

    def die(self):
        if not self.is_dead:
            self.is_dead = True
            self.velocity.x = 0
            self.can_interrupt = True
            self.change_state("DEATH")

    def change_state(self, new_state: str):
        self.state = new_state
        self.state_timer = 0.0
        self.has_dealt_damage_in_attack = False
        self.camera_shake_triggered = False
        
        # Manage attack locking & super armor
        if self.state in ("ATTACK_1", "ATTACK_2", "ATTACK_3", "ATTACK_4", "SPECIAL", "JUMP", "DASH", "WINDUP"):
            self.can_interrupt = False
        else:
            self.can_interrupt = True
        
        if self.state == "IDLE":
            self.velocity.x = 0
            self.anim_manager.play("idle")
            self.state_timer = random.uniform(0.12, 0.30) if not self.enraged else random.uniform(0.05, 0.15)
        elif self.state == "WINDUP":
            # 0.4s Telegraphed wind-up with charging sword gleam
            self.velocity.x = 0
            self.anim_manager.play("idle")
            self.state_timer = 0.40
            for _ in range(8):
                self._particles.append(_BossParticle(
                    self.rect.centerx + (25 if self.facing_right else -25),
                    self.rect.centery - 15,
                    random.uniform(-40, 40), random.uniform(-60, 20),
                    0.35, (255, 230, 90), radius=3.0, gravity=-20
                ))
        elif self.state == "DASH":
            # Gap closer: straight dash leaving shadow trail
            dash_dir = 1.0 if self.facing_right else -1.0
            self.velocity.x = dash_dir * self.dash_speed
            self.anim_manager.play("run", force_reset=True)
            self.state_timer = 0.35
            self.attack_damage = 40
        elif self.state == "WALK":
            self.anim_manager.play("walk")
            self.state_timer = random.uniform(1.0, 2.0)
        elif self.state == "RUN":
            self.anim_manager.play("run")
            self.state_timer = random.uniform(1.2, 2.5)
        elif self.state == "CHASE":
            self.anim_manager.play("run" if self.enraged else "walk")
        elif self.state == "ATTACK_1":
            self.velocity.x = 45.0 if self.facing_right else -45.0
            self.anim_manager.play("attack1", force_reset=True)
            self.attack_damage = 30
        elif self.state == "ATTACK_2":
            self.velocity.x = 65.0 if self.facing_right else -65.0
            self.anim_manager.play("attack2", force_reset=True)
            self.attack_damage = 42
        elif self.state == "ATTACK_3":
            self.velocity.x = 50.0 if self.facing_right else -50.0
            self.anim_manager.play("attack3", force_reset=True)
            self.attack_damage = 50
        elif self.state == "ATTACK_4":
            self.velocity.x = 55.0 if self.facing_right else -55.0
            self.anim_manager.play("attack4", force_reset=True)
            self.attack_damage = 45
        elif self.state == "SPECIAL":
            self.velocity.x = 0
            self.anim_manager.play("special", force_reset=True)
            self.attack_damage = 70
        elif self.state == "JUMP":
            self.anim_manager.play("jump", force_reset=True)
            self.velocity.y = -500.0
            jump_dir = 1 if self.facing_right else -1
            self.velocity.x = jump_dir * (210.0 if self.enraged else 160.0)
            self.on_ground = False
        elif self.state == "HURT":
            self.velocity.x = -40.0 if self.facing_right else 40.0
            self.anim_manager.play("hurt", force_reset=True)
        elif self.state == "DEATH":
            self.velocity.x = 0
            self.anim_manager.play("dead", force_reset=True)

    def get_attack_hitbox(self) -> pygame.FRect:
        """
        Calculates and returns attack hitboxes synchronized strictly to active frames.
        Returns None during startup and recovery frames. Scaled 1.20x for larger boss.
        """
        if self.is_dead or self.has_dealt_damage_in_attack:
            return None
            
        cur_anim = self.anim_manager.animations.get(self.anim_manager.current_state)
        if not cur_anim:
            return None
        cf = cur_anim.current_frame
        cx = self.rect.centerx
        bot = self.rect.bottom
        
        # 0. Dash gap closer hitbox
        if self.state == "DASH":
            hw, hh = 80, 80
            hx = (cx - 10) if self.facing_right else (cx + 10 - hw)
            return pygame.FRect(hx, bot - 95, hw, hh)
            
        # 1. Attack 1: Quick sword thrust (active at frame 4)
        if self.state == "ATTACK_1" and cf == 4:
            hw, hh = 105, 42
            hy = bot - 76
            hx = (cx + 14) if self.facing_right else (cx - 14 - hw)
            return pygame.FRect(hx, hy, hw, hh)
            
        # 2. Attack 2: Heavy piercing thrust (active at frame 4)
        elif self.state == "ATTACK_2" and cf == 4:
            hw, hh = 125, 42
            hy = bot - 76
            hx = (cx + 14) if self.facing_right else (cx - 14 - hw)
            return pygame.FRect(hx, hy, hw, hh)
            
        # 3. Attack 3: Large vertical crimson arc (active at frame 4)
        elif self.state == "ATTACK_3" and cf == 4:
            hw, hh = 120, 142
            hy = bot - 158
            hx = (cx + 10) if self.facing_right else (cx - 10 - hw)
            return pygame.FRect(hx, hy, hw, hh)
            
        # 4. Attack 4: Double crescent slash (active at frame 2 and frame 4)
        elif self.state == "ATTACK_4":
            if cf == 2:
                hw, hh = 108, 95
                hy = bot - 164
                hx = (cx - 6) if self.facing_right else (cx + 6 - hw)
                return pygame.FRect(hx, hy, hw, hh)
            elif cf == 4:
                hw, hh = 120, 142
                hy = bot - 152
                hx = (cx + 10) if self.facing_right else (cx - 10 - hw)
                return pygame.FRect(hx, hy, hw, hh)
                
        # 5. Special: Radial explosive shockwave (active frames 2, 3, 4)
        elif self.state == "SPECIAL" and 2 <= cf <= 4:
            hw, hh = 175, 145
            hy = bot - 148
            hx = cx - hw // 2
            return pygame.FRect(hx, hy, hw, hh)
            
        return None

    def _decide_action(self, abs_dist: float, dist_to_player: float):
        """Intelligent, multi-layered Boss AI with angular deadzone on sprite flip."""
        # Flip deadzone: only flip if player is at least 38px past boss center
        if abs_dist > 38 and self.state in ("IDLE", "WALK", "RUN", "CHASE"):
            self.facing_right = dist_to_player > 0
        
        # 1. Close combat range (< 115px): Telegraph basic combo with 0.4s wind-up
        if abs_dist <= self.attack_range_melee and self.attack_cooldown <= 0:
            if self.enraged:
                chosen = random.choices(
                    ["ATTACK_1", "ATTACK_2", "ATTACK_3", "ATTACK_4", "SPECIAL"],
                    weights=[0.15, 0.20, 0.25, 0.25, 0.15]
                )[0]
                if chosen == "SPECIAL" and self.special_cooldown > 0:
                    chosen = "ATTACK_3"
            else:
                chosen = random.choices(["ATTACK_1", "ATTACK_2", "ATTACK_3"], weights=[0.45, 0.35, 0.20])[0]
                
            # Telegraph basic combo windup (0.4s)
            self.windup_target = chosen
            self.change_state("WINDUP")
            self.attack_cooldown = 0.25 if self.enraged else 0.55
            if chosen == "SPECIAL":
                self.special_cooldown = 3.5
            return

        # 2. Medium distance (115px - 320px): Gap closer Dash or Jump Slam
        if 115 < abs_dist <= 320:
            if self.dash_cooldown <= 0 and random.random() < 0.50:
                # Gap closer straight dash with shadow trail
                self.dash_cooldown = 3.0 if not self.enraged else 1.8
                self.change_state("DASH")
                return
            if self.jump_cooldown <= 0 and self.on_ground and random.random() < 0.45:
                # Ground slam jump
                self.jump_cooldown = 2.5 if not self.enraged else 1.6
                self.change_state("JUMP")
                return
            if self.enraged and self.special_cooldown <= 0 and random.random() < 0.30:
                self.change_state("SPECIAL")
                self.special_cooldown = 3.5
                return
            self.change_state("RUN" if (self.enraged or random.random() < 0.85) else "WALK")
            return

        # 3. Far distance (> 320px): Dash gap closer or aggressive pursuit
        if abs_dist > 320:
            if self.dash_cooldown <= 0 and random.random() < 0.65:
                self.dash_cooldown = 3.0 if not self.enraged else 1.8
                self.change_state("DASH")
                return
            self.change_state("RUN")

    def update(self, dt: float, tiles: list[pygame.FRect], target_player, camera=None):
        self._time += dt
        
        # Cooldown management
        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt
        if self.dash_cooldown > 0:
            self.dash_cooldown -= dt
        if self.special_cooldown > 0:
            self.special_cooldown -= dt
        if self.jump_cooldown > 0:
            self.jump_cooldown -= dt
        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= dt
        if self.shield_recharge_cooldown > 0:
            self.shield_recharge_cooldown -= dt
        elif self.shield < self.max_shield:
            self.shield = min(self.max_shield, self.shield + int(150 * dt))

        # Status effect ticks
        if self.burn_timer > 0 and not self.is_dead:
            self.burn_timer -= dt
            self.burn_tick_timer += dt
            if self.burn_tick_timer >= 1.0:
                self.burn_tick_timer = 0.0
                self.take_damage(int(self.burn_dps))

        # Ambient enrage ember particles in Phase 2
        if self.enraged and not self.is_dead and random.random() < 0.45:
            ex = self.rect.centerx + random.uniform(-25, 25)
            ey = self.rect.centery + random.uniform(-40, 20)
            self._enrage_particles.append(_BossParticle(
                ex, ey, random.uniform(-20, 20), random.uniform(-60, -20),
                random.uniform(0.3, 0.6), (255, 90, 30), radius=random.uniform(2, 4), gravity=-30
            ))

        # Update Afterimages
        new_afterimages = []
        for srf, ax, ay, alpha in self._afterimages:
            alpha -= dt * 650.0
            if alpha > 0:
                new_afterimages.append((srf, ax, ay, alpha))
        self._afterimages = new_afterimages

        # Update Shockwaves
        for sw in self.shockwaves[:]:
            sw.update(dt, tiles)
            if not sw.active:
                self.shockwaves.remove(sw)

        # Core State Machine
        if not self.is_dead:
            self.state_timer -= dt
            dist_to_player = target_player.rect.centerx - self.rect.centerx if target_player else 0
            abs_dist = abs(dist_to_player)
            
            # ── HURT STATE ──
            if self.state == "HURT":
                if self.anim_manager.is_finished("hurt"):
                    self.change_state("IDLE")

            # ── WINDUP (Telegraphed Attack Anticipation 0.4s) ──
            elif self.state == "WINDUP":
                # Maintain stance facing player
                if abs_dist > 38:
                    self.facing_right = dist_to_player > 0
                if self.state_timer <= 0:
                    self.change_state(self.windup_target or "ATTACK_1")

            # ── GAP CLOSER DASH (Straight Dash with Shadow Trail) ──
            elif self.state == "DASH":
                # Spawn shadow afterimage
                frame = self.anim_manager.get_current_frame()
                if frame:
                    offset_x = self.anchor_x_right if self.facing_right else self.anchor_x_left
                    fx = self.rect.centerx - offset_x
                    fy = self.rect.bottom - self.anchor_y
                    self._afterimages.append((frame.copy(), fx, fy, 200.0))
                
                # Check arrival or hit
                if abs_dist <= self.attack_range_melee or self.state_timer <= 0:
                    # Seamless transition directly into heavy piercing thrust
                    self.change_state("ATTACK_2")

            # ── JUMP & SLAM IMPACT ──
            elif self.state == "JUMP":
                # Airborne movement
                cur_anim = self.anim_manager.animations.get("jump")
                if cur_anim:
                    # Sync animation frame to vertical trajectory
                    if self.velocity.y < -150:
                        cur_anim.current_frame = 1
                    elif -150 <= self.velocity.y <= 150:
                        cur_anim.current_frame = 2
                    elif self.velocity.y > 150:
                        cur_anim.current_frame = 3
                        
                # Landing slam trigger
                if self.on_ground and self.velocity.y >= 0:
                    if cur_anim:
                        cur_anim.current_frame = 4
                    if camera and not self.camera_shake_triggered:
                        camera.shake(9.0, 0.35)
                        self.camera_shake_triggered = True
                        
                    # Ground shockwave in both horizontal directions!
                    self.shockwaves.append(BossShockwave(self.rect.centerx - 20, self.rect.bottom, False, speed=260.0, damage=38))
                    self.shockwaves.append(BossShockwave(self.rect.centerx + 20, self.rect.bottom, True, speed=260.0, damage=38))
                    
                    # Landing dust & ground impact VFX
                    for _ in range(16):
                        self._particles.append(_BossParticle(
                            self.rect.centerx + random.uniform(-40, 40), self.rect.bottom - 4,
                            random.uniform(-110, 110), random.uniform(-60, -10),
                            0.40, (180, 160, 130), radius=random.uniform(2, 5), gravity=120
                        ))
                    self.change_state("IDLE")

            # ── ATTACK STATES ──
            elif self.state in ("ATTACK_1", "ATTACK_2", "ATTACK_3", "ATTACK_4", "SPECIAL"):
                self.velocity.x *= 0.88  # Smooth lunge deceleration
                cur_anim_name = self.anim_manager.current_state
                cur_anim = self.anim_manager.animations.get(cur_anim_name)
                
                # Screen shakes on powerful slashes / special
                if camera and not self.camera_shake_triggered:
                    if cur_anim_name == "ATTACK_3" and cur_anim and cur_anim.current_frame == 4:
                        camera.shake(6.0, 0.25)
                        self.camera_shake_triggered = True
                    elif cur_anim_name == "ATTACK_4" and cur_anim and cur_anim.current_frame == 4:
                        camera.shake(8.0, 0.3)
                        self.camera_shake_triggered = True
                    elif cur_anim_name == "SPECIAL" and cur_anim and cur_anim.current_frame == 2:
                        camera.shake(12.0, 0.5)
                        self.camera_shake_triggered = True
                        # Erupt special shockwave particles
                        for _ in range(24):
                            ang = random.uniform(0, math.tau)
                            spd = random.uniform(90, 220)
                            self._particles.append(_BossParticle(
                                self.rect.centerx, self.rect.bottom - 45,
                                math.cos(ang) * spd, math.sin(ang) * spd,
                                0.45, (255, 60, 30), radius=random.uniform(3, 5), gravity=80
                            ))
                            
                if self.anim_manager.is_finished(cur_anim_name):
                    # Chain combos: keep swinging while the player is still in reach
                    max_chain = 3 if self.enraged else 2
                    if (abs_dist <= self.attack_range_melee * 1.25 and self.combo_count < max_chain
                            and random.random() < 0.75 and self.state != "SPECIAL"):
                        self.combo_count += 1
                        self.attack_cooldown = 0.0
                        self._decide_action(min(abs_dist, self.attack_range_melee), dist_to_player)
                    else:
                        self.combo_count = 0
                        self.change_state("IDLE")

            # ── MOVEMENT STATES ──
            elif self.state == "IDLE":
                if self.state_timer <= 0:
                    self._decide_action(abs_dist, dist_to_player)

            elif self.state == "WALK":
                if abs_dist > 38:
                    self.facing_right = dist_to_player > 0
                self.velocity.x = self.walk_speed if self.facing_right else -self.walk_speed
                if abs_dist <= self.attack_range_melee or self.state_timer <= 0:
                    self._decide_action(abs_dist, dist_to_player)

            elif self.state == "RUN":
                if abs_dist > 38:
                    self.facing_right = dist_to_player > 0
                spd = self.run_speed_p2 if self.enraged else self.run_speed_p1
                self.velocity.x = spd if self.facing_right else -spd
                if abs_dist <= self.attack_range_melee or self.state_timer <= 0:
                    self._decide_action(abs_dist, dist_to_player)

            elif self.state == "CHASE":
                self._decide_action(abs_dist, dist_to_player)

        # Apply Physics & Platform Collisions
        self._apply_physics(dt, tiles)
        
        # Advance Animation
        anim_dt = dt * (self.slow_factor if self.slow_timer > 0 else 1.0)
        self.anim_manager.update(anim_dt)
        
        # Update Particles
        self._particles = [p for p in self._particles if p.update(dt)]
        self._enrage_particles = [p for p in self._enrage_particles if p.update(dt)]

    def _apply_physics(self, dt: float, tiles: list[pygame.FRect]):
        # Apply Gravity
        self.velocity.y = min(MAX_FALL_SPEED, self.velocity.y + GRAVITY * dt)
        
        # Horizontal Movement & Collision
        self.rect.x += self.velocity.x * dt
        for t in tiles:
            if self.rect.colliderect(t):
                if self.velocity.x > 0:
                    self.rect.right = t.left
                elif self.velocity.x < 0:
                    self.rect.left = t.right
                self.velocity.x = 0
                
        # Vertical Movement & Collision
        self.rect.y += self.velocity.y * dt
        self.on_ground = False
        for t in tiles:
            if self.rect.colliderect(t):
                # Only land on floors/platforms (t.top > 100), never snap to 0-top walls!
                if self.velocity.y > 0 and t.top > 100:
                    self.rect.bottom = t.top
                    self.velocity.y = 0
                    self.on_ground = True
                elif self.velocity.y < 0 and t.bottom < self.rect.bottom:
                    self.rect.top = t.bottom
                    self.velocity.y = 0

        # Hard floor clamp safety
        if self.rect.bottom > 425:
            self.rect.bottom = 425
            self.velocity.y = 0
            self.on_ground = True

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if self.is_dead and self.anim_manager.is_finished("dead"):
            return

        cam_x, cam_y = camera_offset.x, camera_offset.y

        # ── 1. Ground Contact Shadow (Permanently anchors feet to floor without cutting) ──
        if not self.is_dead:
            sh_w = 104
            sh_h = 20
            shadow_surf = pygame.Surface((sh_w, sh_h), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_surf, (0, 0, 0, 130), (0, 0, sh_w, sh_h))
            core_w, core_h = int(sh_w * 0.65), int(sh_h * 0.65)
            pygame.draw.ellipse(shadow_surf, (0, 0, 0, 190), ((sh_w - core_w) // 2, (sh_h - core_h) // 2, core_w, core_h))
            surface.blit(shadow_surf, (self.rect.centerx - cam_x - sh_w // 2, self.rect.bottom - cam_y - sh_h // 2))

        # ── 1.5 Draw Shadow Trail Afterimages (Gap closer dash) ──
        for aft_surf, ax, ay, alpha in self._afterimages:
            if not self.facing_right:
                aft_surf = pygame.transform.flip(aft_surf, True, False)
            ghost = aft_surf.copy()
            ghost.set_alpha(int(alpha))
            # Tint shadow afterimage dark crimson/purple
            tint_s = pygame.Surface(ghost.get_size(), pygame.SRCALPHA)
            tint_s.fill((140, 20, 40, int(alpha)))
            ghost.blit(tint_s, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(ghost, (ax - cam_x, ay - cam_y))

        # ── 2. Boss Sprite Rendering with Strict Mathematical Foot-Anchor ──
        img = self.anim_manager.get_current_frame()
        if not img:
            return
            
        offset_x = self.anchor_x_right if self.facing_right else self.anchor_x_left
        draw_x = self.rect.centerx - cam_x - offset_x
        draw_y = self.rect.bottom - cam_y - self.anchor_y

        if not self.facing_right:
            img = pygame.transform.flip(img, True, False)

        # Status Tints: Clean alpha preservation without noisy white artifacts!
        if self.slow_timer > 0 and not self.is_dead:
            tinted = img.copy()
            tinted.fill((130, 205, 255, 255), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(tinted, (draw_x, draw_y))
        elif self.invulnerable_timer > 0 and not self.is_dead:
            tinted = img.copy()
            # Clean hurt flash using RGBA mult to protect semi-transparent pixel edges
            flash_overlay = pygame.Surface(img.get_size(), pygame.SRCALPHA)
            flash_overlay.fill((255, 120, 120, 255))
            tinted.blit(flash_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(tinted, (draw_x, draw_y))
        else:
            surface.blit(img, (draw_x, draw_y))

        # ── 3. Poise Shield Subtle Inner Aura (Clean, no yellow gizmo ring) ──
        if self.shield > 0 and not self.is_dead:
            pulse = 0.8 + 0.2 * math.sin(self._time * 4)
            sw, sh = int(self.rect.width + 36), int(self.rect.height + 24)
            sh_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)
            col_shield = (255, 70, 30) if self.enraged else (60, 160, 240)
            pygame.draw.ellipse(sh_surf, (*col_shield, int(25 * pulse)), (0, 0, sw, sh))
            surface.blit(sh_surf, (self.rect.centerx - cam_x - sw // 2, self.rect.centery - cam_y - sh // 2))

        # ── 4. Shockwaves & Particles ──
        for sw in self.shockwaves:
            sw.draw(surface, pygame.math.Vector2(cam_x, cam_y))
        for p in self._particles:
            p.draw(surface, cam_x, cam_y)
        for p in self._enrage_particles:
            p.draw(surface, cam_x, cam_y)

        # ── 5. Visual Debug Mode (Strictly off unless explicitly enabled) ──
        if DEBUG_BOSS:
            self._render_debug_overlay(surface, cam_x, cam_y)

    def _render_debug_overlay(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        """Renders Hurtbox, Hitbox, Attack Range, and state telemetry."""
        # 1. Body Hurtbox (Green)
        hb_screen = pygame.Rect(self.rect.x - cam_x, self.rect.y - cam_y, self.rect.width, self.rect.height)
        pygame.draw.rect(surface, (0, 255, 0), hb_screen, 2)
        
        # 2. Foot Anchor Point (Yellow crosshair)
        foot_x = int(self.rect.centerx - cam_x)
        foot_y = int(self.rect.bottom - cam_y)
        pygame.draw.circle(surface, (255, 255, 0), (foot_x, foot_y), 4)
        pygame.draw.line(surface, (255, 255, 0), (foot_x - 8, foot_y), (foot_x + 8, foot_y), 1)
        pygame.draw.line(surface, (255, 255, 0), (foot_x, foot_y - 8), (foot_x, foot_y + 8), 1)

        # 3. Active Attack Hitbox (Red)
        hitbox = self.get_attack_hitbox()
        if hitbox:
            atk_screen = pygame.Rect(hitbox.x - cam_x, hitbox.y - cam_y, hitbox.width, hitbox.height)
            pygame.draw.rect(surface, (255, 0, 0), atk_screen, 2)
            pygame.draw.rect(surface, (255, 0, 0, 60), atk_screen)

        # 4. Attack Range Circle (Cyan)
        range_cx = int(self.rect.centerx - cam_x)
        range_cy = int(self.rect.centery - cam_y)
        pygame.draw.circle(surface, (0, 220, 255), (range_cx, range_cy), int(self.attack_range_melee), 1)

        # 5. State & Telemetry Text
        if self._debug_font:
            cur_anim_name = self.anim_manager.current_state
            cur_anim = self.anim_manager.animations.get(cur_anim_name)
            cf = cur_anim.current_frame if cur_anim else 0
            tot_f = len(cur_anim.frames) if cur_anim else 0
            
            lines = [
                f"[STATE: {self.state}] [PHASE: {self.current_phase}]",
                f"[ANIM: {cur_anim_name} (Frame: {cf}/{tot_f})]",
                f"[HP: {int(self.health)}/{int(self.max_health)}] [SHIELD: {int(self.shield)}]",
                f"[HITBOX: {'ACTIVE' if hitbox else 'OFF'}]"
            ]
            
            ty = int(self.rect.top - cam_y - 65)
            for line in lines:
                text_surf = self._debug_font.render(line, True, (255, 255, 255))
                bg_rect = text_surf.get_rect(center=(int(self.rect.centerx - cam_x), ty))
                bg_pad = bg_rect.inflate(6, 2)
                pygame.draw.rect(surface, (0, 0, 0, 180), bg_pad)
                surface.blit(text_surf, bg_rect)
                ty += 14

# Re-export new Boss Pack lazily to prevent circular imports
def __getattr__(name):
    if name in ("DemonSlimeBoss", "SamuraiBoss", "ImpalerBoss", "MonsterCreatureBoss"):
        import entities.bosses_pack as bp
        return getattr(bp, name)
    raise AttributeError(f"module {__name__} has no attribute {name}")

