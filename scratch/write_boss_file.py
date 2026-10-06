import os

boss_code = '''import pygame
import os
import math
import random
import numpy as np
from engine.animation import AnimationManager, load_animation_folder, load_spritesheet
from entities.projectile import Projectile
from engine.v3.ai.neural_ai import NeuralTacticalAI

# ─────────────────────────────────────────────────────────────────────────────
# Lightweight particle for VFX
# ─────────────────────────────────────────────────────────────────────────────
class _BossParticle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "radius", "gravity")
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
    def __init__(self, x: float, y: float, moving_right: bool, speed: float = 240.0, damage: int = 35):
        self.rect = pygame.FRect(x, y - 24, 40, 44)
        self.velocity_x = speed if moving_right else -speed
        self.active = True
        self.damage = damage
        self.moving_right = moving_right
        
        shock_path = os.path.join("assets", "sprites", "vfx", "vfx_ground_shock")
        self.anim = load_animation_folder(shock_path, "vfx_ground_shock", fps=18, loop=True, scale=1.4)
        self.lifetime = 2.4
        
    def update(self, dt: float, tiles: list[pygame.FRect]):
        if not self.active:
            return
        self.anim.update(dt)
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.active = False
            return
            
        self.rect.x += self.velocity_x * dt
        for t in tiles:
            if t.width < 100 and self.rect.colliderect(t):  # collided with wall
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
    """
    Epic Skeleton King Boss with Multi-Phase AI, Dynamic Skills, and SIMD Neural Tactical Brain.
    Divided into 5 distinct phases with visual transformations and adaptive combat mechanics:
    - Phase 1 (15001-20000 HP): Ponderous & predictable, slow windups, no jump or dodge.
    - Phase 2 (10001-15000 HP): Evasive instinct activates, backstep dodges, faster telegraphed skills.
    - Phase 3 (5001-10000 HP): Transformation 1 (Necrotic Void Sovereign). Neural AI online learning,
                                mixed easy and tricky void attacks, shadow step dashes.
    - Phase 4 (2501-5000 HP): Transformation 2 (Abyssal Blood King). Bone shield guard mechanics,
                              aggressive forward pressure, parry reflections, crumbling arena.
    - Phase 5 (< 2500 HP): Climax / Desperation mode. High intensity rhythm combat with fair punish windows.
    """
    def __init__(self, x: float, y: float):
        self.pos = pygame.math.Vector2(x, y)
        self.velocity = pygame.math.Vector2(0, 0)
        self.rect = pygame.FRect(x, y, 64, 110)
        
        self.max_health = 20000  # Epic 20,000 HP boss
        self.health = self.max_health
        self.max_shield = 2000   # 2,000 Poise Shield
        self.shield = self.max_shield
        self.shield_recharge_cooldown = 0.0
        self.attack_damage = 35
        self.touch_damage = 0    # No unfair contact collision damage
        self.is_dead = False
        self.facing_right = False
        self.enraged = False
        self.hit_count = 0
        self.potions_to_spawn = []
        self.potion_dropped_50 = False
        self.slow_timer = 0.0
        self.slow_factor = 1.0
        
        # Ignis Burn passive support
        self.burn_timer = 0.0
        self.burn_dps = 0.0
        self.burn_tick_timer = 0.0
        
        # Boss Combat & AI State
        self.state = "IDLE"  # IDLE, CHASE, ATTACK, FLAME_BURST, JUMP_SLAM, ROAR, STAGGERED, DODGE, GUARD, RECOVERY
        self.state_timer = 0.0
        self.skill_cooldown = 2.0
        self.attack_cooldown = 0.8
        self.has_hit_player = False
        self.current_phase = 1
        self.is_guarding = False
        self.guard_health = 450
        self.guard_timer = 0.0
        self.is_dodging = False
        self.dodge_timer = 0.0
        
        # Minion Summon triggers
        self.summoned_75 = False
        self.summoned_50 = False
        self.summoned_25 = False
        self.minions_to_spawn = []
        
        # Projectiles & Shockwaves
        self.projectiles = []
        self.shockwaves = []
        
        # Smoke VFX for Teleport / Dash
        self.smoke_active = False
        self.smoke_timer = 0.0
        self.smoke_pos = pygame.math.Vector2(0, 0)
        vfx_smoke_path = os.path.join("assets", "sprites", "vfx", "vfx_smoke")
        self.smoke_anim = load_animation_folder(vfx_smoke_path, "vfx_smoke", 22, False, 2.0)
        
        # Stun VFX Animation
        vfx_stun_path = os.path.join("assets", "sprites", "vfx", "vfx_stun")
        self.stun_anim = load_animation_folder(vfx_stun_path, "vfx_stun", 16, True, 1.4)
        
        # Neural Tactical Brain (Item 7)
        self.neural_ai = NeuralTacticalAI(entity_type="boss", difficulty_scale=1.0)
        self.neural_decision_timer = 0.0
        self.last_player_action = "none"
        
        # Animations — Skeleton King Multi-Frame Sheets (192x192, feet anchored at Y=184)
        self.boss_scale = 1.0
        self.feet_anchor_y = 184
        self.anim_manager = AnimationManager()
        self._load_animations()
        self.anim_manager.play("idle")

        # ── VFX state ──────────────────────────────────────────────────────
        self._time = 0.0
        self._particles: list[_BossParticle] = []
        self._flame_charge = 0.0
        self._flame_sigil_angle = 0.0
        self._flame_active = False
        self._slam_impact_timer = 0.0
        self._slam_debris: list[_BossParticle] = []
        self._shadow_afterimages: list[dict] = []
        self._shadow_vortex_particles: list[_BossParticle] = []
        self._shadow_arrive_flash = 0.0
        self._roar_ring_radius = 0.0
        self._roar_ring_timer = 0.0
        self._enrage_flame_particles: list[_BossParticle] = []
        self._melee_slash_timer = 0.0
        self._melee_slash_dir = 1
        self._attack_windup = 0.0
        self._guard_spark_timer = 0.0
        self._phase_announce_text = ""
        self._phase_announce_timer = 0.0

    def _load_animations(self):
        """Loads fluid multi-frame animation strips for Phase 1/2, Phase 3, and Phase 4/5."""
        king_dir = os.path.join("assets", "sprites", "skeleton_king")
        FW, FH = 192, 192
        sc = self.boss_scale
        
        # Default Phase 1 & 2 sheets
        idle_path = os.path.join(king_dir, "king_idle.png")
        walk_path = os.path.join(king_dir, "king_walk.png")
        attack_path = os.path.join(king_dir, "king_attack.png")
        cast_path = os.path.join(king_dir, "king_cast.png")
        slam_path = os.path.join(king_dir, "king_slam.png")
        hurt_path = os.path.join(king_dir, "king_hurt.png")
        roar_path = os.path.join(king_dir, "king_roar.png")
        dead_path = os.path.join(king_dir, "king_dead.png")

        self.anim_manager.add_animation("idle",   load_spritesheet(idle_path, FW, FH, fps=8,  loop=True,  scale=sc))
        self.anim_manager.add_animation("walk",   load_spritesheet(walk_path, FW, FH, fps=10, loop=True,  scale=sc))
        self.anim_manager.add_animation("attack", load_spritesheet(attack_path, FW, FH, fps=10, loop=False, scale=sc))
        self.anim_manager.add_animation("cast",   load_spritesheet(cast_path, FW, FH, fps=10, loop=False, scale=sc))
        self.anim_manager.add_animation("slam",   load_spritesheet(slam_path, FW, FH, fps=12, loop=False, scale=sc))
        self.anim_manager.add_animation("hurt",   load_spritesheet(hurt_path, FW, FH, fps=10, loop=False, scale=sc))
        self.anim_manager.add_animation("roar",   load_spritesheet(roar_path, FW, FH, fps=10, loop=False, scale=sc))
        self.anim_manager.add_animation("dead",   load_spritesheet(dead_path, FW, FH, fps=8,  loop=False, scale=sc))
        self.anim_manager.add_animation("jump",   load_spritesheet(slam_path, FW, FH, fps=12, loop=False, scale=sc, start_frame=1, max_frames=2))

    def switch_phase_visuals(self, phase: int):
        """Swaps active spritesheets when the Boss undergoes form transformations."""
        king_dir = os.path.join("assets", "sprites", "skeleton_king")
        FW, FH = 192, 192
        sc = self.boss_scale
        
        if phase >= 4:
            # Phase 4/5: Abyssal Blood King (Flaming Crimson Armor)
            p_idle = os.path.join(king_dir, "king_phase4_idle.png")
            p_walk = os.path.join(king_dir, "king_phase4_walk.png")
            p_atk  = os.path.join(king_dir, "king_phase4_attack.png")
            p_cast = os.path.join(king_dir, "king_phase4_cast.png")
            p_slam = os.path.join(king_dir, "king_phase4_slam.png")
            p_roar = os.path.join(king_dir, "king_phase4_roar.png")
            if os.path.exists(p_idle):
                self.anim_manager.add_animation("idle",   load_spritesheet(p_idle, FW, FH, fps=10, loop=True, scale=sc))
                self.anim_manager.add_animation("walk",   load_spritesheet(p_walk, FW, FH, fps=12, loop=True, scale=sc))
                self.anim_manager.add_animation("attack", load_spritesheet(p_atk,  FW, FH, fps=12, loop=False, scale=sc))
                self.anim_manager.add_animation("cast",   load_spritesheet(p_cast, FW, FH, fps=12, loop=False, scale=sc))
                self.anim_manager.add_animation("slam",   load_spritesheet(p_slam, FW, FH, fps=14, loop=False, scale=sc))
                self.anim_manager.add_animation("roar",   load_spritesheet(p_roar, FW, FH, fps=12, loop=False, scale=sc))
        elif phase == 3:
            # Phase 3: Necrotic Void Sovereign (Purple Rifts & Cosmic Shadow)
            p_idle = os.path.join(king_dir, "king_phase3_idle.png")
            p_walk = os.path.join(king_dir, "king_phase3_walk.png")
            p_atk  = os.path.join(king_dir, "king_phase3_attack.png")
            p_cast = os.path.join(king_dir, "king_phase3_cast.png")
            p_slam = os.path.join(king_dir, "king_phase3_slam.png")
            if os.path.exists(p_idle):
                self.anim_manager.add_animation("idle",   load_spritesheet(p_idle, FW, FH, fps=9,  loop=True, scale=sc))
                self.anim_manager.add_animation("walk",   load_spritesheet(p_walk, FW, FH, fps=11, loop=True, scale=sc))
                self.anim_manager.add_animation("attack", load_spritesheet(p_atk,  FW, FH, fps=11, loop=False, scale=sc))
                self.anim_manager.add_animation("cast",   load_spritesheet(p_cast, FW, FH, fps=11, loop=False, scale=sc))
                self.anim_manager.add_animation("slam",   load_spritesheet(p_slam, FW, FH, fps=13, loop=False, scale=sc))

    @property
    def poise_shield(self) -> int:
        return self.shield

    @poise_shield.setter
    def poise_shield(self, val: int):
        self.shield = val

    @property
    def is_staggered(self) -> bool:
        return self.state == "STAGGERED"

    def apply_slow(self, duration: float = 2.5, factor: float = 0.35):
        if not self.is_dead:
            self.slow_timer = max(self.slow_timer, duration)
            self.slow_factor = factor

    def apply_burn(self, duration: float = 4.0, dps: float = 3.0):
        if not self.is_dead:
            self.burn_timer = max(self.burn_timer, duration)
            self.burn_dps = dps

    def _determine_phase(self) -> int:
        """Exact phase boundaries matching user specification."""
        if self.health > 15000:
            return 1
        elif self.health > 10000:
            return 2
        elif self.health > 5000:
            return 3
        elif self.health > 2500:
            return 4
        else:
            return 5

    def _on_phase_transition(self, old_phase: int, new_phase: int):
        """Triggers transformation animations, VFX bursts, and arena shifts."""
        self.current_phase = new_phase
        self.switch_phase_visuals(new_phase)
        self.state = "ROAR"
        self.state_timer = 1.2
        self.anim_manager.play("roar", force_reset=True)
        self._roar_ring_radius = 6.0
        self._roar_ring_timer = 0.8
        self._spawn_roar_burst()
        
        # Spawn after-images and void burst for transformations
        if new_phase >= 3:
            self._spawn_shadow_vortex(self.rect.centerx, self.rect.centery, is_arrival=True)
            self._shadow_arrive_flash = 0.35
            
        if new_phase >= 4:
            self.enraged = True
            
        # Neural AI online feedback update
        self.neural_ai.difficulty_scale = 1.0 + (new_phase - 1) * 0.25

    def take_damage(self, amount: int, hit_direction: int = 0):
        if self.is_dead:
            return
            
        self.hit_count += 1
        
        # Dodge check: if in Phase 4/5 or active dodge, negate damage with shadow after-image
        if self.is_dodging:
            self.neural_ai.report_combat_outcome(was_hit=False, dodged_successfully=True, blocked_successfully=False, landed_hit=False)
            return

        # Bone Barrier Guard check (Item 6 & 8: Boss guards in Phase 4/5)
        if self.is_guarding and (hit_direction == 0 or (hit_direction > 0 and not self.facing_right) or (hit_direction < 0 and self.facing_right)):
            # Guard absorbed 80% of damage
            amount = max(1, int(amount * 0.20))
            self._guard_spark_timer = 0.22
            self._spawn_guard_sparks()
            self.guard_health -= amount
            self.neural_ai.report_combat_outcome(was_hit=False, dodged_successfully=False, blocked_successfully=True, landed_hit=False)
            if self.guard_health <= 0:
                self.is_guarding = False
                self.guard_timer = 0.0

        # Poise Shield absorption:
        if self.shield > 0:
            self.shield -= amount
            if self.shield <= 0:
                self.shield = 0
                self.shield_recharge_cooldown = 20.0
                self.state = "STAGGERED"
                self.state_timer = 4.2
                self.velocity.x = 0
                self.anim_manager.play("hurt", force_reset=True)
                self.neural_ai.report_combat_outcome(was_hit=True, dodged_successfully=False, blocked_successfully=False, landed_hit=False)
        else:
            # Direct HP Damage
            self.health -= amount
            self.neural_ai.report_combat_outcome(was_hit=True, dodged_successfully=False, blocked_successfully=False, landed_hit=False)
            if self.health <= 0:
                self.health = 0
                self.is_dead = True
                self.state = "DEAD"
                self.anim_manager.play("dead", force_reset=True)
                self.velocity.x = 0
                self.velocity.y = -120
                return

        # Check Phase Transition
        new_phase = self._determine_phase()
        if new_phase != self.current_phase:
            self._on_phase_transition(self.current_phase, new_phase)

        # Drop healing potion at 50% HP
        if self.health <= self.max_health // 2 and not self.potion_dropped_50:
            self.potion_dropped_50 = True
            self.potions_to_spawn.append((self.rect.centerx, self.rect.centery - 20))
            
        # Minion Reinforcements
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
    def _spawn_guard_sparks(self):
        cx = self.rect.right if self.facing_right else self.rect.left
        cy = self.rect.centery
        for _ in range(12):
            angle = random.uniform(-1.0, 1.0) + (0 if self.facing_right else math.pi)
            spd = random.uniform(80, 180)
            col = random.choice([(255, 215, 80), (255, 240, 150), (200, 220, 255)])
            self._particles.append(_BossParticle(cx, cy, math.cos(angle)*spd, math.sin(angle)*spd,
                                                 random.uniform(0.15, 0.35), col, radius=random.uniform(2, 4), gravity=160))

    def _spawn_roar_burst(self):
        cx, cy = self.rect.centerx, self.rect.centery
        burst_color = (180, 50, 255) if self.current_phase == 3 else ((255, 50, 30) if self.current_phase >= 4 else (80, 190, 255))
        for _ in range(36):
            angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(80, 260)
            color = random.choice([burst_color, (255, 220, 100), (255, 255, 255)])
            self._particles.append(_BossParticle(cx, cy, math.cos(angle)*spd, math.sin(angle)*spd,
                                                 random.uniform(0.4, 0.95), color, radius=random.uniform(3, 7), gravity=160))

    def _spawn_flame_particles(self):
        cx = self.rect.centerx
        base_y = self.rect.bottom
        spread = 160
        for _ in range(4):
            ox = random.uniform(-spread, spread)
            oy = random.uniform(-20, 20)
            px, py = cx + ox, base_y + oy
            hx = cx + (25 if self.facing_right else -25)
            hy = self.rect.centery - 15
            dx, dy = hx - px, hy - py
            dist = max(1, math.hypot(dx, dy))
            spd = random.uniform(90, 180)
            col = (190, 60, 255) if self.current_phase >= 3 else (255, 120, 30)
            self._particles.append(_BossParticle(px, py, (dx/dist)*spd, (dy/dist)*spd,
                                                 random.uniform(0.2, 0.45), col, radius=random.uniform(2, 5), gravity=0))

    def _spawn_flame_burst_explosion(self):
        hx = self.rect.centerx + (30 if self.facing_right else -30)
        hy = self.rect.centery - 15
        for _ in range(24):
            angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(60, 200)
            col = random.choice([(255, 80, 30), (200, 40, 255), (255, 220, 80)]) if self.current_phase < 3 else \
                  random.choice([(180, 40, 255), (220, 80, 255), (255, 255, 255)])
            self._particles.append(_BossParticle(hx, hy, math.cos(angle)*spd, math.sin(angle)*spd,
                                                 random.uniform(0.25, 0.55), col, radius=random.uniform(3, 7), gravity=120))

    def _spawn_slam_debris(self):
        cx, cy = self.rect.centerx, self.rect.bottom
        for _ in range(22):
            angle = random.uniform(-math.pi + 0.2, -0.2)
            spd = random.uniform(110, 320)
            col = random.choice([(220, 210, 190), (160, 140, 110), (120, 40, 40), (255, 80, 20)])
            self._slam_debris.append(_BossParticle(cx, cy, math.cos(angle)*spd, math.sin(angle)*spd,
                                                   random.uniform(0.5, 1.1), col, radius=random.uniform(2, 5), gravity=560))

    def _spawn_shadow_vortex(self, x, y, is_arrival: bool):
        for _ in range(18):
            angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(50, 120)
            inward = -1 if not is_arrival else 1
            col = random.choice([(120, 0, 200), (180, 50, 255), (60, 0, 140)])
            self._shadow_vortex_particles.append(_BossParticle(x, y, math.cos(angle)*spd*inward, math.sin(angle)*spd*inward - 15,
                                                               random.uniform(0.3, 0.6), col, radius=random.uniform(3, 6), gravity=0))

    def _spawn_enrage_flames(self):
        for side in [-18, 18]:
            ox = self.rect.centerx + side
            oy = self.rect.top + 10
            col = random.choice([(255, 60, 20), (255, 30, 20), (220, 30, 180), (255, 140, 30)]) if self.current_phase >= 4 else \
                  random.choice([(160, 40, 240), (200, 70, 255), (100, 20, 200)])
            self._enrage_flame_particles.append(_BossParticle(ox, oy, random.uniform(-20, 20), random.uniform(-70, -150),
                                                              random.uniform(0.25, 0.55), col, radius=random.uniform(2.5, 5), gravity=-50))

    # ── State Machine & Tactical AI Updates ─────────────────────────────────
    def _execute_neural_decision(self, action: str, player, dist: float, dt: float):
        """Translates Neural Tactical AI outputs into fluid gameplay behaviors."""
        if action == "DODGE" and not self.is_dodging and self.skill_cooldown <= 0:
            # Shadow step / backstep away
            self.is_dodging = True
            self.dodge_timer = 0.35
            dodge_dir = -1 if self.facing_right else 1
            self.velocity.x = dodge_dir * 340.0
            self.velocity.y = -120.0
            self.skill_cooldown = 1.8
            # Spawn after-image
            img = self.anim_manager.get_current_frame()
            self._shadow_afterimages.append({"surf": img.copy(), "x": self.rect.centerx, "y": self.rect.centery, "timer": 0.45})
            self._spawn_shadow_vortex(self.rect.centerx, self.rect.centery, is_arrival=False)
            
        elif action == "GUARD" and self.current_phase >= 4 and not self.is_guarding:
            self.is_guarding = True
            self.guard_timer = 1.0
            self.guard_health = 400
            self.velocity.x = 0
            
        elif action == "JUMP" and self.velocity.y == 0 and abs(player.velocity.x) > 50:
            # Tactical jump slam or jump over player
            self.velocity.y = -520.0
            self.velocity.x = 180.0 if self.facing_right else -180.0
            self.state = "JUMP_SLAM"
            self.anim_manager.play("jump", force_reset=True)
            
        elif action == "ADVANCE":
            speed = 130.0 if self.current_phase >= 3 else 90.0
            self.velocity.x = speed if self.facing_right else -speed
            self.anim_manager.play("walk")
            
        elif action == "RETREAT":
            speed = 100.0
            self.velocity.x = -speed if self.facing_right else speed
            self.anim_manager.play("walk")

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
        if self._roar_ring_timer > 0:
            self._roar_ring_timer -= dt
            self._roar_ring_radius += dt * 340

        if self._slam_impact_timer > 0:
            self._slam_impact_timer -= dt

        if self._guard_spark_timer > 0:
            self._guard_spark_timer -= dt

        if self.is_guarding:
            self.guard_timer -= dt
            if self.guard_timer <= 0:
                self.is_guarding = False

        if self.is_dodging:
            self.dodge_timer -= dt
            if self.dodge_timer <= 0:
                self.is_dodging = False

        if (self.enraged or self.current_phase >= 3) and not self.is_dead and random.random() < 0.65:
            self._spawn_enrage_flames()

        if self._flame_active:
            self._flame_charge = min(1.0, self._flame_charge + dt * 1.8)
            self._flame_sigil_angle += dt * 2.8
            if random.random() < 0.6:
                self._spawn_flame_particles()

        if self._melee_slash_timer > 0:
            self._melee_slash_timer -= dt

        if self._shadow_arrive_flash > 0:
            self._shadow_arrive_flash -= dt

        self._particles = [p for p in self._particles if p.update(dt)]
        self._slam_debris = [p for p in self._slam_debris if p.update(dt)]
        self._shadow_vortex_particles = [p for p in self._shadow_vortex_particles if p.update(dt)]
        self._enrage_flame_particles = [p for p in self._enrage_flame_particles if p.update(dt)]
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

        # Burn tick (Ignis passive)
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
                self.shield = self.max_shield
                self.state = "ROAR"
                self.state_timer = 1.0
                self.anim_manager.play("roar", force_reset=True)
                self._roar_ring_radius = 5.0
                self._roar_ring_timer = 0.7
                self._spawn_roar_burst()
            
        if player:
            self.facing_right = player.rect.centerx > self.rect.centerx
            dx = player.rect.centerx - self.rect.centerx
            dist = abs(dx)
            
            # Neural Tactical Brain Evaluation (Active in Phase 3, 4, 5)
            self.neural_decision_timer -= dt
            if self.current_phase >= 3 and self.neural_decision_timer <= 0 and self.state in ("CHASE", "IDLE"):
                self.neural_decision_timer = 0.25
                proj_data = [{"pos": (p.rect.centerx, p.rect.centery), "vx": p.velocity.x} for p in getattr(player, "projectiles", [])]
                features = self.neural_ai.build_feature_vector(
                    self_pos=(self.rect.centerx, self.rect.bottom),
                    target_pos=(player.rect.centerx, player.rect.bottom),
                    target_vel=(player.velocity.x, player.velocity.y),
                    target_is_attacking=getattr(player, "is_attacking", False),
                    target_is_casting=getattr(player, "is_casting_aoe", False) or getattr(player, "is_casting_ultimate", False),
                    target_is_dashing=getattr(player, "is_dashing", False),
                    incoming_projectiles=proj_data,
                    self_cooldown=self.skill_cooldown
                )
                action_name, action_idx, conf = self.neural_ai.decide_action(features, temperature=0.7)
                self._execute_neural_decision(action_name, player, dist, dt)
            
            # Phase-Specific Speed Multipliers
            speed_mult = 0.85 if self.current_phase == 1 else (1.05 if self.current_phase == 2 else (1.25 if self.current_phase == 3 else 1.45))
            
            # ── Main State Machine ─────────────────────────────────────────
            if self.state == "STAGGERED":
                self.velocity.x = 0
                self.state_timer -= dt
                self.anim_manager.play("hurt")
                self.stun_anim.update(effective_dt)
                if self.state_timer <= 0:
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
                    
            elif self.state == "RECOVERY":
                # Fair Dark Souls / Elden Ring punish window after big combos!
                self.anim_manager.play("idle")
                self.velocity.x = 0
                self.state_timer -= dt
                if self.state_timer <= 0:
                    self.state = "CHASE"

            elif self.state == "CHASE":
                self.anim_manager.play("walk")
                self.velocity.x = (85.0 * speed_mult) if self.facing_right else (-85.0 * speed_mult)
                
                # Phase 2 Dodge Heuristic: reacts to player incoming attacks
                if self.current_phase == 2 and getattr(player, "is_attacking", False) and dist < 110 and self.skill_cooldown <= 0:
                    if random.random() < 0.50:
                        self.is_dodging = True
                        self.dodge_timer = 0.32
                        self.velocity.x = -240.0 if self.facing_right else 240.0
                        self.skill_cooldown = 2.2
                
                # Check Melee Attack
                if dist < 80 and self.attack_cooldown <= 0:
                    self.state = "ATTACK"
                    self.has_hit_player = False
                    self.velocity.x = 0
                    self.anim_manager.play("attack", force_reset=True)
                    self._melee_slash_timer = 0.0
                    # Phase 1: slow windup (1.1s); Phase 4/5: tighter windup (0.65s)
                    self._attack_windup = 1.1 if self.current_phase == 1 else (0.85 if self.current_phase == 2 else 0.65)
                    
                # Check Special Skills
                elif self.skill_cooldown <= 0:
                    # In Phase 1: only slow flame burst
                    if self.current_phase == 1:
                        chosen_skill = "FLAME_BURST"
                    else:
                        chosen_skill = random.choice(["FLAME_BURST", "JUMP_SLAM"])
                        
                    self.state = chosen_skill
                    self.state_timer = 0.0
                    self.skill_cooldown = 3.2 if self.current_phase == 1 else (2.4 if self.current_phase == 2 else 1.6)
                    
                    if chosen_skill == "FLAME_BURST":
                        self.velocity.x = 0
                        self.anim_manager.play("cast", force_reset=True)
                        self.state_timer = 1.0 if self.current_phase == 1 else (0.75 if self.current_phase == 2 else 0.5)
                        self._flame_active = True
                        self._flame_charge = 0.0
                        
                    elif chosen_skill == "JUMP_SLAM":
                        # Jump Slam not allowed in Phase 1
                        if self.current_phase > 1:
                            self.velocity.y = -560
                            self.velocity.x = (160.0 * speed_mult) if self.facing_right else (-160.0 * speed_mult)
                            self.anim_manager.play("jump", force_reset=True)
                        else:
                            self.state = "CHASE"
                            
            elif self.state == "ATTACK":
                if self._attack_windup > 0:
                    self._attack_windup -= dt
                    self.velocity.x = 0
                else:
                    self.velocity.x = (150.0 * speed_mult) if self.facing_right else (-150.0 * speed_mult)
                cur_frame = self.anim_manager.animations["attack"].current_frame
                if cur_frame >= 3 and self._melee_slash_timer <= 0:
                    self._melee_slash_timer = 0.22
                    self._melee_slash_dir = 1 if self.facing_right else -1
                if self.anim_manager.is_finished("attack"):
                    # After attack, grant a brief punish recovery window in Phase 5 for fairness!
                    if self.current_phase == 5:
                        self.state = "RECOVERY"
                        self.state_timer = 0.85
                    else:
                        self.state = "IDLE"
                        self.state_timer = 0.5
                    self.attack_cooldown = 2.0 if self.current_phase <= 2 else 1.2
                    
            elif self.state == "FLAME_BURST":
                self.velocity.x = 0
                self.state_timer -= dt
                if self.state_timer <= 0:
                    proj_x = self.rect.right if self.facing_right else self.rect.left - 24
                    proj_y = self.rect.centery - 15
                    
                    # Projectile speed and patterns
                    speed_p = 190.0 if self.current_phase == 1 else (250.0 if self.current_phase == 2 else 320.0)
                    p1 = Projectile(proj_x, proj_y, self.facing_right, is_enemy=True, projectile_type="boss_fireball")
                    p1.velocity.x = speed_p if self.facing_right else -speed_p
                    p2 = Projectile(proj_x, proj_y - 28, self.facing_right, is_enemy=True, projectile_type="boss_fireball")
                    p2.velocity.x = speed_p * 0.95 if self.facing_right else -speed_p * 0.95
                    p3 = Projectile(proj_x, proj_y + 28, self.facing_right, is_enemy=True, projectile_type="boss_fireball")
                    p3.velocity.x = speed_p * 0.95 if self.facing_right else -speed_p * 0.95
                    
                    self.projectiles.extend([p1, p2, p3])
                    self._spawn_flame_burst_explosion()
                    self._flame_active = False
                    self._flame_charge = 0.0
                    
                    if self.current_phase == 5:
                        self.state = "RECOVERY"
                        self.state_timer = 0.85
                    else:
                        self.state = "IDLE"
                        self.state_timer = 0.5
                    
            elif self.state == "JUMP_SLAM":
                pass
                
            elif self.state == "ROAR":
                self.velocity.x = 0
                self.state_timer -= dt
                if self.state_timer <= 0:
                    self.state = "CHASE"
                    
        # Apply physics
        self.velocity.y += 920 * dt
        self.velocity.y = min(self.velocity.y, 820)
        
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
                    
                    if self.state == "JUMP_SLAM":
                        # Post-slam punish window
                        self.state = "RECOVERY" if self.current_phase == 5 else "IDLE"
                        self.state_timer = 0.9 if self.current_phase == 5 else 0.6
                        self.anim_manager.play("slam", force_reset=True)
                        
                        sw_speed = 220.0 if self.current_phase <= 2 else 290.0
                        sw_left = BossShockwave(self.rect.left, self.rect.bottom, moving_right=False, speed=sw_speed)
                        sw_right = BossShockwave(self.rect.right, self.rect.bottom, moving_right=True, speed=sw_speed)
                        self.shockwaves.extend([sw_left, sw_right])
                        
                        if player and abs(player.rect.centerx - self.rect.centerx) < 75 and abs(player.rect.bottom - self.rect.bottom) < 45:
                            player.take_damage(80)
                            
                        self._spawn_slam_debris()
                        self._slam_impact_timer = 0.25
                        
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
            hitbox_w = 70
            hitbox_h = 80
            hitbox_y = self.rect.centery - hitbox_h / 2
            if self.facing_right:
                return pygame.FRect(self.rect.right - 10, hitbox_y, hitbox_w, hitbox_h)
            else:
                return pygame.FRect(self.rect.left - hitbox_w + 10, hitbox_y, hitbox_w, hitbox_h)
        return None

    # ── Draw Helpers ──────────────────────────────────────────────────────
    def _draw_flame_sigil(self, surface, cam_x, cam_y):
        if not self._flame_active or self._flame_charge <= 0:
            return
        t = self._flame_charge
        alpha = max(0, min(255, int(200 * min(1.0, t * 2))))
        radius = int(32 + t * 40)
        cx = self.rect.centerx - cam_x
        cy = self.rect.bottom - cam_y - 4

        sigil_surf = pygame.Surface((radius * 2 + 12, radius * 2 + 12), pygame.SRCALPHA)
        rc = radius + 6
        color_outer = (180, 50, 255) if self.current_phase >= 3 else (255, 100, 30)

        pygame.draw.circle(sigil_surf, (*color_outer, alpha), (rc, rc), radius, 2)
        pygame.draw.circle(sigil_surf, (220, 200, 255, max(0, min(255, alpha // 2))), (rc, rc), radius - 6, 1)

        num_pts = 6
        for i in range(num_pts):
            angle = self._flame_sigil_angle + (i * 2 * math.pi / num_pts)
            angle2 = self._flame_sigil_angle + ((i + 2) * 2 * math.pi / num_pts)
            sx = rc + int(math.cos(angle) * radius)
            sy = rc + int(math.sin(angle) * radius)
            ex = rc + int(math.cos(angle2) * radius)
            ey = rc + int(math.sin(angle2) * radius)
            pygame.draw.line(sigil_surf, (*color_outer, alpha), (sx, sy), (ex, ey), 1)

        surface.blit(sigil_surf, (cx - rc, cy - 8))

    def _draw_melee_slash_arc(self, surface, cam_x, cam_y):
        if self._melee_slash_timer <= 0:
            return
        progress = max(0.0, min(1.0, self._melee_slash_timer / 0.22))
        alpha = max(0, min(255, int(210 * progress)))
        arc_r = 48
        start_angle = -math.pi * 0.6
        span = math.pi * 1.2
        if self._melee_slash_dir < 0:
            start_angle = math.pi - (-math.pi * 0.6) - math.pi * 1.2
            span = -math.pi * 1.2

        cx = self.rect.centerx - cam_x + self._melee_slash_dir * arc_r * 0.5
        cy = self.rect.centery - cam_y - 10

        rect_size = arc_r * 2 + 12
        arc_surf = pygame.Surface((rect_size + 12, rect_size + 12), pygame.SRCALPHA)
        color_arc = (220, 40, 255) if self.current_phase == 3 else ((255, 60, 30) if self.current_phase >= 4 else (80, 190, 255))
        for gw, col in [
            (11, (*color_arc, max(0, min(255, alpha // 4)))),
            (7,  (*color_arc, max(0, min(255, alpha // 2)))),
            (3,  (255, 255, 255, alpha)),
        ]:
            pygame.draw.arc(arc_surf, col, pygame.Rect(6, 6, rect_size, rect_size), start_angle, start_angle + span, gw)
        surface.blit(arc_surf, (cx - rect_size // 2 - 6, cy - rect_size // 2 - 6))

    def _draw_roar_ring(self, surface, cam_x, cam_y):
        if self._roar_ring_timer <= 0:
            return
        t = max(0, self._roar_ring_timer / 0.8)
        alpha = int(200 * t)
        r = int(self._roar_ring_radius)
        if r < 2:
            return
        cx = self.rect.centerx - cam_x
        cy = self.rect.centery - cam_y
        rs = pygame.Surface((r * 2 + 6, r * 2 + 6), pygame.SRCALPHA)
        col = (180, 50, 255) if self.current_phase == 3 else ((255, 60, 30) if self.current_phase >= 4 else (90, 200, 255))
        pygame.draw.circle(rs, (*col, alpha), (r + 3, r + 3), r, 4)
        surface.blit(rs, (cx - r - 3, cy - r - 3))

    def _draw_slam_impact(self, surface, cam_x, cam_y):
        if self._slam_impact_timer <= 0:
            return
        t = max(0, self._slam_impact_timer / 0.25)
        alpha = int(220 * t)
        r = int(60 * t)
        if r < 2:
            return
        cx = self.rect.centerx - cam_x
        cy = self.rect.bottom - cam_y - 4
        rs = pygame.Surface((r * 2, r * 2 // 2 + 4), pygame.SRCALPHA)
        pygame.draw.ellipse(rs, (255, 200, 100, alpha), (0, 0, r * 2, max(4, r // 2)))
        surface.blit(rs, (cx - r, cy - r // 4))

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        cam_x, cam_y = camera_offset.x, camera_offset.y

        # ── 1. Ground contact drop shadow (Permanently anchors feet to floor) ──
        if not self.is_dead:
            sh_w = int(self.rect.width * 1.5)
            sh_h = 14
            contact_sh = pygame.Surface((sh_w, sh_h), pygame.SRCALPHA)
            pygame.draw.ellipse(contact_sh, (0, 0, 0, 130), (0, 0, sh_w, sh_h))
            surface.blit(contact_sh, (self.rect.centerx - cam_x - sh_w // 2, self.rect.bottom - cam_y - sh_h // 2 + 1))

        # ── 2. Ground-level VFX ──────────────────────────────────────────
        self._draw_flame_sigil(surface, cam_x, cam_y)

        # Shadow after-images
        for ai in self._shadow_afterimages:
            t = max(0, ai["timer"] / 0.45)
            ghost = ai["surf"].copy()
            ghost.set_alpha(int(160 * t))
            tinted = ghost.copy()
            tint_col = (140, 30, 220) if self.current_phase == 3 else (220, 40, 40)
            tinted.fill(tint_col, special_flags=pygame.BLEND_RGBA_MULT)
            gw, gh = ghost.get_size()
            surface.blit(tinted, (ai["x"] - cam_x - gw // 2, ai["y"] - cam_y - gh // 2))

        for sw in self.shockwaves:
            sw.draw(surface, camera_offset)

        for p in self._slam_debris:
            p.draw(surface, cam_x, cam_y)

        for p in self._shadow_vortex_particles:
            p.draw(surface, cam_x, cam_y)

        if self.smoke_active:
            smoke_frame = self.smoke_anim.get_current_frame()
            if smoke_frame:
                s_rect = smoke_frame.get_rect(center=(self.smoke_pos.x - cam_x, self.smoke_pos.y - cam_y))
                surface.blit(smoke_frame, s_rect)

        self._draw_roar_ring(surface, cam_x, cam_y)
        self._draw_melee_slash_arc(surface, cam_x, cam_y)

        # ── 3. Main Multi-Frame Sprite (Pristine alignment, zero floating!) ──
        img = self.anim_manager.get_current_frame()
        img_rect = img.get_rect()
        
        # Center horizontally, anchor feet firmly at self.rect.bottom via FEET_Y = 184
        draw_x = self.rect.centerx - cam_x - img_rect.width // 2
        draw_y = self.rect.bottom - cam_y - int(self.feet_anchor_y * self.boss_scale)
        
        if not self.facing_right:
            img = pygame.transform.flip(img, True, False)
            
        # Status Tints
        if self.slow_timer > 0 and not self.is_dead:
            tinted = img.copy()
            tinted.fill((140, 205, 255), special_flags=pygame.BLEND_RGBA_MULT)
            surface.blit(tinted, (draw_x, draw_y))
        elif self.current_phase >= 4 and not self.is_dead:
            # Subtle crimson aura for blood king
            surface.blit(img, (draw_x, draw_y))
        else:
            surface.blit(img, (draw_x, draw_y))

        # ── 4. Foreground VFX & Barriers ─────────────────────────────────
        # Bone Barrier Guard Shield (Phase 4/5)
        if self.is_guarding and not self.is_dead:
            pulse = 0.8 + 0.2 * math.sin(self._time * 8)
            bw = 24
            bh = int(self.rect.height * 0.9)
            bx = (self.rect.right - cam_x + 5) if self.facing_right else (self.rect.left - cam_x - bw - 5)
            by = self.rect.centery - cam_y - bh // 2
            b_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
            pygame.draw.rect(b_surf, (255, 60, 40, int(180 * pulse)), (0, 0, bw, bh), border_radius=6)
            pygame.draw.rect(b_surf, (255, 220, 180, int(240 * pulse)), (0, 0, bw, bh), 2, border_radius=6)
            surface.blit(b_surf, (bx, by))

        # Poise Shield Barrier Aura
        if self.shield > 0 and not self.is_dead:
            pulse = 0.75 + 0.25 * math.sin(self._time * 4)
            sh_w = int(self.rect.width + 36 + 6 * pulse)
            sh_h = int(self.rect.height + 28 + 6 * pulse)
            sh_surf = pygame.Surface((sh_w, sh_h), pygame.SRCALPHA)
            col_shield = (200, 60, 255) if self.current_phase == 3 else ((255, 80, 50) if self.current_phase >= 4 else (80, 210, 255))
            pygame.draw.ellipse(sh_surf, (*col_shield, int(45 * pulse)), (0, 0, sh_w, sh_h))
            pygame.draw.ellipse(sh_surf, (255, 230, 100, int(130 * pulse)), (0, 0, sh_w, sh_h), 2)
            surface.blit(sh_surf, (self.rect.centerx - cam_x - sh_w // 2, self.rect.centery - cam_y - sh_h // 2))

        # Stagger stun stars
        if self.state == "STAGGERED" and not self.is_dead:
            stun_frame = self.stun_anim.get_current_frame()
            if stun_frame:
                sf_rect = stun_frame.get_rect(center=(self.rect.centerx - cam_x, self.rect.top - cam_y - 20))
                surface.blit(stun_frame, sf_rect)

        if self._slam_impact_timer > 0:
            self._draw_slam_impact(surface, cam_x, cam_y)

        for p in self._particles:
            p.draw(surface, cam_x, cam_y)

        for p in self._enrage_flame_particles:
            p.draw(surface, cam_x, cam_y)
'''

with open("src/entities/boss.py", "w", encoding="utf-8") as f:
    f.write(boss_code)
print("src/entities/boss.py updated successfully!")
