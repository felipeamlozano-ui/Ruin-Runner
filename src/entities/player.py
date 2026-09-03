import pygame
import os
import math
import random
from config.constants import GRAVITY, MAX_FALL_SPEED, ACCELERATION, MAX_SPEED, JUMP_FORCE, FRICTION
from engine.input_manager import INPUT
import engine.resource_manager as rm
from utils.math_utils import clamp
from engine.animation import AnimationManager, load_animation_folder, load_spritesheet

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
    """Crisp, sharp dimensional anime blade cut slicing across enemies."""
    def __init__(self, start_pos: tuple, end_pos: tuple, color=(255, 235, 120), width=3.5):
        self.start = start_pos
        self.end = end_pos
        self.color = color
        self.max_width = width
        self.life = 0.28 # Snappy anime cut
        self.timer = 0.0
        
    def update(self, dt: float) -> bool:
        self.timer += dt
        return self.timer < self.life
        
    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        t = max(0.0, min(1.0, self.timer / self.life))
        alpha = int(255 * (1.0 - t))
        if alpha <= 0:
            return
            
        p1 = (self.start[0] - camera_offset.x, self.start[1] - camera_offset.y)
        p2 = (self.end[0] - camera_offset.x, self.end[1] - camera_offset.y)
        
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.hypot(dx, dy)
        if length < 6:
            return
            
        nx, ny = -dy / length, dx / length
        mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        
        cur_w = self.max_width * (1.0 - t * 0.35)
        
        gw, gh = surface.get_size()
        slash_surf = pygame.Surface((gw, gh), pygame.SRCALPHA)
        
        # 1. Subtle soft glow edge (thin)
        w_outer = cur_w * 2.0
        pts_outer = [p1, (mx + nx * w_outer, my + ny * w_outer), p2, (mx - nx * w_outer, my - ny * w_outer)]
        pygame.draw.polygon(slash_surf, (*self.color, int(alpha * 0.35)), pts_outer)
        
        # 2. Razor-sharp brilliant core
        w_core = cur_w * 0.65
        pts_core = [p1, (mx + nx * w_core, my + ny * w_core), p2, (mx - nx * w_core, my - ny * w_core)]
        pygame.draw.polygon(slash_surf, (255, 255, 255, alpha), pts_core)
        
        surface.blit(slash_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

def draw_sacred_runic_circle(surface: pygame.Surface, center: tuple[float, float], radius: float, angle: float, alpha: int):
    """Draws a subtle, sleek arcane rune circle on the ground beneath the hero."""
    if alpha <= 0 or radius < 5:
        return
    rc = int(radius) + 4
    circle_surf = pygame.Surface((rc * 2, rc * 2), pygame.SRCALPHA)
    
    # Elegant outer rune ring
    pygame.draw.circle(circle_surf, (255, 220, 90, int(alpha * 0.75)), (rc, rc), int(radius), 1)
    pygame.draw.circle(circle_surf, (120, 220, 255, int(alpha * 0.45)), (rc, rc), int(radius - 4), 1)
    
    # 8 delicate sacred runes
    for i in range(8):
        a = angle + i * (math.pi / 4)
        p_start = (rc + math.cos(a) * (radius - 5), rc + math.sin(a) * (radius - 5))
        p_end = (rc + math.cos(a) * (radius + 2), rc + math.sin(a) * (radius + 2))
        pygame.draw.line(circle_surf, (255, 240, 160, int(alpha * 0.8)), p_start, p_end, 1)
        
    # Inner star
    star_angle = -angle * 1.2
    pts = []
    for i in range(12):
        a = star_angle + i * (math.pi / 6)
        r = (radius * 0.62) if (i % 2 == 0) else (radius * 0.32)
        pts.append((rc + math.cos(a) * r, rc + math.sin(a) * r))
    if len(pts) >= 3:
        pygame.draw.polygon(circle_surf, (255, 215, 80, int(alpha * 0.5)), pts, 1)
        
    surface.blit(circle_surf, (center[0] - rc, center[1] - rc), special_flags=pygame.BLEND_RGBA_ADD)
    
    # 12 Celestial Rune notches on outer ring
    for i in range(12):
        a = angle + i * (math.pi / 6)
        r_in = radius - 7
        r_out = radius + 3
        p_start = (rc + math.cos(a) * r_in, rc + math.sin(a) * r_in)
        p_end = (rc + math.cos(a) * r_out, rc + math.sin(a) * r_out)
        pygame.draw.line(circle_surf, (255, 240, 140, int(alpha * 0.9)), p_start, p_end, 2)
        
    # Counter-rotating Octagram / Sacred Star inside
    star_angle = -angle * 1.3
    pts = []
    num_star = 8
    for i in range(num_star * 2):
        a = star_angle + i * (math.pi / num_star)
        r = (radius * 0.72) if (i % 2 == 0) else (radius * 0.38)
        pts.append((rc + math.cos(a) * r, rc + math.sin(a) * r))
    if len(pts) >= 3:
        pygame.draw.polygon(circle_surf, (255, 215, 80, int(alpha * 0.7)), pts, 2)
        
    # Inner glowing sun disc
    sun_r = int(radius * 0.28)
    if sun_r > 2:
        pygame.draw.circle(circle_surf, (255, 255, 255, int(alpha * 0.6)), (rc, rc), sun_r)
        pygame.draw.circle(circle_surf, (255, 230, 110, int(alpha * 0.9)), (rc, rc), sun_r, 2)
        
    surface.blit(circle_surf, (center[0] - rc, center[1] - rc), special_flags=pygame.BLEND_RGBA_ADD)

class UltimateEnergyParticle:
    """Starlight particle imploding into the sword tip during ultimate windup."""
    def __init__(self, target_pos: tuple[float, float], start_dist: float = 240):
        ang = random.uniform(0, 2 * math.pi)
        dist = start_dist + random.uniform(-30, 60)
        self.x = target_pos[0] + math.cos(ang) * dist
        self.y = target_pos[1] + math.sin(ang) * dist
        self.target = target_pos
        self.speed = random.uniform(550, 900)
        self.color = random.choice([(255, 235, 120), (140, 230, 255), (255, 255, 255), (255, 180, 60)])
        self.size = random.uniform(2.5, 4.5)
        self.active = True
        
    def update(self, dt: float, target_pos: tuple[float, float]) -> bool:
        self.target = target_pos
        dx = self.target[0] - self.x
        dy = self.target[1] - self.y
        dist = math.hypot(dx, dy)
        if dist <= 14:
            self.active = False
            return False
        step = self.speed * dt
        if step >= dist:
            self.active = False
            return False
        self.x += (dx / dist) * step
        self.y += (dy / dist) * step
        return True
        
    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        sx = self.x - camera_offset.x
        sy = self.y - camera_offset.y
        r = int(self.size)
        if r > 0:
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, self.color, (r, r), r)
            surface.blit(s, (sx - r, sy - r), special_flags=pygame.BLEND_RGBA_ADD)

class UltimateShockwaveRing:
    """Expanding chromatic shockwave ring sweeping across the screen."""
    def __init__(self, center: tuple[float, float], max_radius: float = 360, speed: float = 680, color=(255, 230, 130)):
        self.center = center
        self.radius = 12.0
        self.max_radius = max_radius
        self.speed = speed
        self.color = color
        self.active = True
        
    def update(self, dt: float) -> bool:
        self.radius += self.speed * dt
        if self.radius >= self.max_radius:
            self.active = False
            return False
        return True
        
    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        progress = self.radius / self.max_radius
        alpha = int(220 * (1.0 - progress))
        if alpha <= 0:
            return
        cx = int(self.center[0] - camera_offset.x)
        cy = int(self.center[1] - camera_offset.y)
        r = int(self.radius)
        w = max(2, int(8 * (1.0 - progress)))
        ring_surf = pygame.Surface((r * 2 + w * 2, r * 2 + w * 2), pygame.SRCALPHA)
        rc = r + w
        pygame.draw.circle(ring_surf, (*self.color, alpha), (rc, rc), r, w)
        pygame.draw.circle(ring_surf, (255, 255, 255, alpha // 2), (rc, rc), max(1, r - 2), 1)
        surface.blit(ring_surf, (cx - rc, cy - rc), special_flags=pygame.BLEND_RGBA_ADD)

class Player:
    def __init__(self, x: float, y: float, character_id: str = None):
        from entities.character_data import get_character_profile
        from config.settings import SETTINGS
        if character_id is None:
            character_id = getattr(SETTINGS, "CURRENT_CHARACTER", "shaia")
            
        self.profile = get_character_profile(character_id)
        self.character_id = self.profile.id
        self.archetype = self.profile.archetype
        
        # Position & Physics
        self.pos = pygame.math.Vector2(x, y)
        self.velocity = pygame.math.Vector2(0, 0)
        self.rect = pygame.FRect(x, y, self.profile.hitbox_size[0], self.profile.hitbox_size[1])
        
        # State
        self.on_ground = False
        self.can_double_jump = False
        
        # Stats
        self.max_health = self.profile.hp_max
        self.health = self.max_health
        self.max_mana = float(self.profile.mp_max)
        self.mana = self.max_mana
        self.max_stamina = float(self.profile.sp_max)
        self.stamina = self.max_stamina
        self.mana_regen = self.profile.mana_regen
        self.stamina_regen = self.profile.stamina_regen
        self.speed = self.profile.move_speed
        self.dash_speed = self.profile.dash_speed
        self.jump_speed = self.profile.jump_speed
        
        # Combat & Inventory
        self.invulnerable = False
        self.invulnerability_timer = 0.0
        self.is_blocking = False
        self.is_dashing = False
        self.dash_timer = 0.0
        self.dash_duration = 0.22
        self.dash_cooldown = 0.0
        self.dash_ghost_timer = 0.0
        self.after_images: list[AfterImage] = []
        
        # AoE Nova Skill
        self.is_casting_aoe = False
        self.aoe_timer = 0.0
        self.aoe_hit_done = False
        self.aoe_radius = 150.0
        
        # Magic Projectile [K] Cast State & Animation
        self.is_casting_magic = False
        self.magic_cast_timer = 0.0
        self.magic_sigil_timer = 0.0
        
        # AAA Ultimate Skill [R] - Devastating Celestial Cleave with Volumetric Ray Casting
        self.is_casting_ultimate = False
        self.ultimate_timer = 0.0
        self.ultimate_hit_done = False
        self.ultimate_slashes: list[UltimateSlash] = []
        self.ultimate_shockwave_anim = load_animation_folder(os.path.join("assets", "sprites", "vfx", "vfx_ground_shock"), "vfx_ground_shock", 16, False, 1.8)
        self.ultimate_shockwave_active = False
        self.ultimate_shockwave_pos = (0, 0)
        self.ultimate_shockwave_timer = 0.0
        self.ultimate_rune_angle = 0.0
        self.ultimate_particles: list[UltimateEnergyParticle] = []
        self.ultimate_shockwave_rings: list[UltimateShockwaveRing] = []
        self.ultimate_slash_spawn_timer = 0.0
        
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
        self.shield_anim = None
        
        if self.profile.sprite_type == "folder":
            base_path = os.path.join("assets", "sprites", "shaia", "sprites_common")
            attack_path = os.path.join("assets", "sprites", "shaia", "sprites_attack")
            append_path = os.path.join("assets", "sprites", "shaia", "sprites_append")
            scale = self.profile.sprite_scale
            
            self.anim_manager.add_animation("idle", load_animation_folder(base_path, "common_00_idle_stand_A", 15, True, scale))
            self.anim_manager.add_animation("walk", load_animation_folder(base_path, "common_11_walk", 15, True, scale))
            self.anim_manager.add_animation("jump", load_animation_folder(base_path, "common_21_jump_up", 15, False, scale))
            self.anim_manager.add_animation("fall", load_animation_folder(base_path, "common_21_jump_down", 15, True, scale))
            self.anim_manager.add_animation("attack", load_animation_folder(attack_path, "attack_01_cobination01", 14, False, scale))
            self.anim_manager.add_animation("cast_magic", load_animation_folder(attack_path, "attack_03_cobination03", 22, False, scale))
            self.anim_manager.add_animation("dash", load_animation_folder(append_path, "common_12_guard_dash", 24, False, scale))
            self.anim_manager.add_animation("whirlwind", load_animation_folder(attack_path, "attack_04_cobination04", 18, False, scale))
            self.anim_manager.add_animation("heavy_slash", load_animation_folder(attack_path, "attack_03_cobination03", 16, False, scale))
            self.anim_manager.add_animation("jump_attack", load_animation_folder(attack_path, "attack_21_jump_attack", 16, True, scale))
            self.anim_manager.add_animation("landing", load_animation_folder(base_path, "common_22_landing", 14, False, scale))
            
            damage_path = os.path.join("assets", "sprites", "shaia", "sprites_damage")
            self.anim_manager.add_animation("dead", load_animation_folder(damage_path, "damage_11_blow_landing_A", 10, False, scale))
            self.anim_manager.add_animation("guard", load_animation_folder(base_path, "common_31_guard_stand", 10, True, scale))
            
            vfx_guard_path = os.path.join("assets", "sprites", "vfx", "vfx_guard")
            self.shield_anim = load_animation_folder(vfx_guard_path, "vfx_guard", 18, True, 1.3)
        else:
            scale = self.profile.sprite_scale
            bf = self.profile.base_folder
            fw, fh = self.profile.frame_size
            
            if self.profile.archetype == "mage":
                idle_p = os.path.join(bf, "Idle.png")
                walk_p = os.path.join(bf, "Walk.png")
                atk_p = os.path.join(bf, "Attack.png")
                prot_p = os.path.join(bf, "Protection.png")
                dial_p = os.path.join(bf, "Dialogue.png")
                book_p = os.path.join(bf, "Book.png")
                
                self.anim_manager.add_animation("idle", load_spritesheet(idle_p, fw, fh, 10, True, scale))
                self.anim_manager.add_animation("walk", load_spritesheet(walk_p, fw, fh, 12, True, scale))
                self.anim_manager.add_animation("jump", load_spritesheet(walk_p, fw, fh, 12, False, scale, start_frame=1, max_frames=2))
                self.anim_manager.add_animation("fall", load_spritesheet(walk_p, fw, fh, 12, True, scale, start_frame=4, max_frames=2))
                self.anim_manager.add_animation("attack", load_spritesheet(atk_p, fw, fh, 16, False, scale))
                
                # Cast magic
                cast_sheet = book_p if os.path.exists(book_p) else dial_p if os.path.exists(dial_p) else atk_p
                cfw, cfh = (64, 64) if (cast_sheet == book_p) else (fw, fh)
                self.anim_manager.add_animation("cast_magic", load_spritesheet(cast_sheet, cfw, cfh, 16, False, scale))
                self.anim_manager.add_animation("whirlwind", load_spritesheet(atk_p, fw, fh, 20, False, scale))
                self.anim_manager.add_animation("heavy_slash", load_spritesheet(atk_p, fw, fh, 16, False, scale))
                self.anim_manager.add_animation("jump_attack", load_spritesheet(atk_p, fw, fh, 16, True, scale))
                self.anim_manager.add_animation("landing", load_spritesheet(idle_p, fw, fh, 12, False, scale, start_frame=0, max_frames=2))
                self.anim_manager.add_animation("guard", load_spritesheet(prot_p, fw, fh, 10, True, scale))
                self.anim_manager.add_animation("dead", load_spritesheet(atk_p, fw, fh, 8, False, scale, start_frame=2, max_frames=4))
                self.anim_manager.add_animation("dash", load_spritesheet(walk_p, fw, fh, 22, False, scale))
            else:
                idle_p = os.path.join(bf, "Idle.png")
                walk_p = os.path.join(bf, "Walk.png")
                run_p = os.path.join(bf, "Run.png")
                jump_p = os.path.join(bf, "Jump.png")
                atk1_p = os.path.join(bf, "Attack_1.png")
                atk2_p = os.path.join(bf, "Attack_2.png")
                atk3_p = os.path.join(bf, "Attack_3.png")
                shield_p = os.path.join(bf, "Shield.png")
                dead_p = os.path.join(bf, "Dead.png")
                hurt_p = os.path.join(bf, "Hurt.png")
                
                self.anim_manager.add_animation("idle", load_spritesheet(idle_p, fw, fh, 10, True, scale))
                self.anim_manager.add_animation("walk", load_spritesheet(walk_p, fw, fh, 12, True, scale))
                self.anim_manager.add_animation("jump", load_spritesheet(jump_p, fw, fh, 16, False, scale, start_frame=0, max_frames=6))
                self.anim_manager.add_animation("fall", load_spritesheet(jump_p, fw, fh, 14, True, scale, start_frame=6, max_frames=6))
                self.anim_manager.add_animation("attack", load_spritesheet(atk1_p, fw, fh, 16, False, scale))
                self.anim_manager.add_animation("cast_magic", load_spritesheet(atk2_p, fw, fh, 16, False, scale))
                self.anim_manager.add_animation("whirlwind", load_spritesheet(atk3_p, fw, fh, 18, False, scale))
                self.anim_manager.add_animation("heavy_slash", load_spritesheet(atk3_p, fw, fh, 16, False, scale))
                self.anim_manager.add_animation("jump_attack", load_spritesheet(atk1_p, fw, fh, 16, True, scale))
                self.anim_manager.add_animation("landing", load_spritesheet(jump_p, fw, fh, 14, False, scale, start_frame=6, max_frames=2))
                self.anim_manager.add_animation("guard", load_spritesheet(shield_p, fw, fh, 10, True, scale))
                self.anim_manager.add_animation("dead", load_spritesheet(dead_p, fw, fh, 10, False, scale))
                self.anim_manager.add_animation("dash", load_spritesheet(run_p, fw, fh, 20, False, scale))
                if os.path.exists(hurt_p):
                    self.anim_manager.add_animation("hurt", load_spritesheet(hurt_p, fw, fh, 12, False, scale))
        
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

        # Update Magic Casting state
        if self.is_casting_magic:
            self.magic_cast_timer -= dt
            if self.magic_cast_timer <= 0 or self.anim_manager.is_finished("cast_magic"):
                self.is_casting_magic = False
        if self.magic_sigil_timer > 0:
            self.magic_sigil_timer -= dt

        # Update Ultimate Skill State
        if self.is_casting_ultimate:
            self.ultimate_timer += dt
            # Absolute invulnerability while power persists
            self.invulnerable = True
            self.invulnerability_timer = 0.5
            self.velocity.x = 0
            self.velocity.y = min(self.velocity.y, 0)
            
            # Rotate ground rune array
            self.ultimate_rune_angle += dt * 1.6
            
            # Target center for energy implosion: sword tip
            sword_pos = (self.rect.centerx + (16 if self.facing_right else -16), self.rect.centery - 10)
            
            # Spawn a few elegant starlight particles during windup
            if self.ultimate_timer < 0.40:
                if len(self.ultimate_particles) < 18 and random.random() < 0.5:
                    self.ultimate_particles.append(UltimateEnergyParticle(sword_pos, start_dist=random.uniform(120, 220)))
                    
            # Update implosion particles
            self.ultimate_particles = [p for p in self.ultimate_particles if p.update(dt, sword_pos)]
            
            # Detonation at t=0.45s: 1 clean expanding shockwave ring
            if 0.44 <= self.ultimate_timer <= 0.49 and len(self.ultimate_shockwave_rings) == 0:
                self.ultimate_shockwave_rings.append(UltimateShockwaveRing((self.rect.centerx, self.rect.centery), max_radius=250, speed=550, color=(140, 220, 255)))
                
            # Update shockwave rings
            self.ultimate_shockwave_rings = [r for r in self.ultimate_shockwave_rings if r.update(dt)]
            
            # Spawn crisp, clean anime dimensional cuts (1 every 0.14s, total 4-5 slashes)
            self.ultimate_slash_spawn_timer += dt
            if 0.40 <= self.ultimate_timer <= 1.05:
                if self.ultimate_slash_spawn_timer >= 0.14:
                    self.ultimate_slash_spawn_timer = 0.0
                    angle = random.choice([-0.70, 0.70, -1.05, 0.35, -0.30, 0.95]) + random.uniform(-0.08, 0.08)
                    cx = self.rect.centerx + random.uniform(-45, 45)
                    cy = self.rect.centery + random.uniform(-25, 15)
                    length = random.uniform(150, 220)
                    dx = math.cos(angle) * length
                    dy = math.sin(angle) * length
                    slash_col = random.choice([(255, 235, 130), (140, 220, 255), (255, 255, 255)])
                    self.ultimate_slashes.append(UltimateSlash((cx - dx, cy - dy), (cx + dx, cy + dy), color=slash_col, width=3.5))
                
            # Ground shockwave at feet
            if self.ultimate_shockwave_active:
                self.ultimate_shockwave_anim.update(dt)
                self.ultimate_shockwave_timer -= dt
                if self.ultimate_shockwave_timer <= 0 or self.ultimate_shockwave_anim.finished:
                    self.ultimate_shockwave_active = False
                    
            if self.ultimate_timer >= 1.65:
                self.is_casting_ultimate = False
                self.invulnerable = True
                self.invulnerability_timer = 0.5 # Grace period after ultimate ends
                
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
            
        # Mages attack exclusively through magic projectiles, no melee sword collision
        if not self.is_attacking or self.archetype == "mage":
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
        # 1. Whirlwind / Special AoE Skill
        if self.is_casting_aoe and not self.aoe_hit_done:
            self.aoe_hit_done = True
            dmg = self.profile.skills["e"].damage if hasattr(self, "profile") and "e" in self.profile.skills else 5
            for e in enemies:
                if not e.is_dead:
                    dist = pygame.math.Vector2(e.rect.center).distance_to(pygame.math.Vector2(self.rect.center))
                    if dist <= self.aoe_radius:
                        e.take_damage(dmg)
                        # Knockback
                        e.velocity.y = -220
                        e.velocity.x = 260 if e.rect.centerx > self.rect.centerx else -260
                        
        # 2. Downward Plunge Ground Impact Shockwave (Buffed ground slam damage)
        if self.plunge_impact_pending:
            self.plunge_impact_pending = False
            if camera:
                camera.shake(8.5, 0.28)
            for e in enemies:
                if not e.is_dead:
                    dist = pygame.math.Vector2(e.rect.center).distance_to(pygame.math.Vector2(self.rect.centerx, self.rect.bottom))
                    if dist <= 135:
                        e.take_damage(6)
                        e.velocity.y = -260
                        e.velocity.x = 280 if e.rect.centerx > self.rect.centerx else -280
                        
        # 3. Direct mid-air hits while plunging down (Buffed dive damage)
        if self.is_down_attacking:
            down_hitbox = self.get_attack_hitbox()
            if down_hitbox:
                for e in enemies:
                    if not e.is_dead and e not in self.plunge_hit_enemies and down_hitbox.colliderect(e.rect):
                        self.plunge_hit_enemies.add(e)
                        e.take_damage(4)
                        e.velocity.y = -120
                        
        # 4. Ultimate Skill Screen-Clearing Devastation & Continuous Enemy Slow
        if self.is_casting_ultimate:
            for e in enemies:
                if not e.is_dead and hasattr(e, "apply_slow"):
                    e.apply_slow(duration=2.5, factor=0.25)
                    
            if not self.ultimate_hit_done and self.ultimate_timer >= 0.45:
                self.ultimate_hit_done = True
                if camera:
                    camera.shake(20.0, 0.75)
                ult_dmg = self.profile.skills["r"].damage if hasattr(self, "profile") and "r" in self.profile.skills else 80
                for e in enemies:
                    if not e.is_dead:
                        dist = pygame.math.Vector2(e.rect.center).distance_to(pygame.math.Vector2(self.rect.center))
                        if dist <= 460:
                            e.take_damage(ult_dmg)
                            e.velocity.y = -350
                            e.velocity.x = 420 if e.rect.centerx > self.rect.centerx else -420
        
    def _update_animation(self, dt: float):
        # Character-specific mana regeneration
        if self.mana < self.max_mana:
            self.mana = min(self.max_mana, self.mana + self.mana_regen * dt)
            
        if self.is_dead:
            self.anim_manager.play("dead")
        elif self.is_casting_ultimate:
            if self.ultimate_timer < 0.35:
                self.anim_manager.play("guard") # Gathering power
            elif self.ultimate_timer < 0.95:
                self.anim_manager.play("whirlwind") # Blistering slashes / storm
            else:
                self.anim_manager.play("heavy_slash") # Finisher cleave
        elif self.is_casting_magic:
            self.anim_manager.play("cast_magic")
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
            if self.shield_anim:
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
            
        # Lock controls briefly during magic cast strike
        if self.is_casting_magic:
            if self.on_ground:
                self.velocity.x *= FRICTION
                if abs(self.velocity.x) < 5:
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

        # Ultimate Skill [R]
        if INPUT.is_action_just_pressed("ULTIMATE") and not self.is_attacking and not self.is_blocking and not self.is_dashing and not self.is_casting_magic:
            ult_cost = self.profile.skills["r"].cost_value if hasattr(self, "profile") else 100
            if self.mana >= ult_cost:
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
                self.ultimate_particles.clear()
                self.ultimate_shockwave_rings.clear()
                self.ultimate_slashes.clear()
                self.ultimate_flare_timer = 0.0
                return

        # Dash [Q]
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
            
        # Skill [E] - AoE Nova / Whirlwind
        if INPUT.is_action_just_pressed("SKILL_AOE") and not self.is_casting_aoe and not self.is_attacking and not self.is_blocking:
            e_skill = self.profile.skills.get("e", None)
            if e_skill:
                can_cast = (self.mana >= e_skill.cost_value) if e_skill.cost_type == "MP" else (self.stamina >= e_skill.cost_value)
                if can_cast:
                    if e_skill.cost_type == "MP":
                        self.mana -= e_skill.cost_value
                    else:
                        self.stamina -= e_skill.cost_value
                    self.is_casting_aoe = True
                    self.aoe_timer = 0.6
                    self.aoe_hit_done = False
                    self.anim_manager.play("whirlwind", force_reset=True)
                    
        # Blocking / Guard [Shift]
        shift_skill = self.profile.skills.get("shift", None)
        shift_cost = shift_skill.cost_value if shift_skill else 8
        is_mage = (self.archetype == "mage")
        can_block = (self.mana > 1) if is_mage else (self.stamina > 1)
        
        if INPUT.is_action_pressed("DEFEND") and can_block:
            self.is_blocking = True
            if is_mage:
                self.mana = max(0.0, self.mana - shift_cost * dt)
            else:
                self.stamina = max(0.0, self.stamina - shift_cost * dt)
            self.velocity.x = 0
            return
        else:
            self.is_blocking = False
            # Regenerate stamina
            self.stamina = min(self.max_stamina, self.stamina + self.stamina_regen * dt)
            
        if self.is_attacking:
            if self.on_ground:
                self.velocity.x *= FRICTION
                if abs(self.velocity.x) < 5:
                    self.velocity.x = 0
            return
            
        # Horizontal Movement
        axis = INPUT.get_axis()
        
        if axis.x != 0:
            self.velocity.x += axis.x * ACCELERATION * dt
            self.velocity.x = clamp(self.velocity.x, -self.speed, self.speed)
            self.facing_right = axis.x > 0
        else:
            # Apply friction
            self.velocity.x *= FRICTION
            if abs(self.velocity.x) < 5:
                self.velocity.x = 0
                
        # Jumping
        if INPUT.is_action_just_pressed("JUMP") and not self.is_blocking:
            if self.on_ground:
                self.velocity.y = self.jump_speed
                self.on_ground = False
                self.can_double_jump = True
            elif self.can_double_jump:
                self.velocity.y = self.jump_speed * 0.82
                self.can_double_jump = False
                
        # Ground Attack [J]
        if INPUT.is_action_just_pressed("ATTACK") and not self.is_attacking and not self.is_blocking:
            j_skill = self.profile.skills.get("j", None)
            if j_skill:
                is_mp = (j_skill.cost_type == "MP")
                can_cast = (self.mana >= j_skill.cost_value) if is_mp else (self.stamina >= j_skill.cost_value)
                if can_cast:
                    if is_mp:
                        self.mana -= j_skill.cost_value
                    else:
                        self.stamina -= j_skill.cost_value
                    self.is_attacking = True
                    self.anim_manager.play("attack", force_reset=True)
                    
                    # Mages shoot basic projectile on [J]
                    if self.archetype == "mage":
                        from entities.projectile import Projectile
                        proj_x = self.rect.right + 8 if self.facing_right else self.rect.left - 28
                        proj_y = self.rect.centery - 8
                        ptype = j_skill.projectile_type or "arcane_bolt"
                        self.projectiles.append(Projectile(proj_x, proj_y, self.facing_right, is_enemy=False, projectile_type=ptype))
            
        # Skill [K] - Ranged Projectile / Technique
        if INPUT.is_action_just_pressed("MAGIC") and not self.is_attacking and not self.is_blocking and not self.is_casting_magic and not self.is_casting_ultimate:
            k_skill = self.profile.skills.get("k", None)
            if k_skill and self.mana >= k_skill.cost_value:
                self.mana -= k_skill.cost_value
                self.is_casting_magic = True
                self.magic_cast_timer = 0.32
                self.magic_sigil_timer = 0.38
                self.anim_manager.play("cast_magic", force_reset=True)
                
                from entities.projectile import Projectile
                proj_x = self.rect.right + 8 if self.facing_right else self.rect.left - 28
                proj_y = self.rect.centery - 8
                ptype = k_skill.projectile_type or "fireball"
                self.projectiles.append(Projectile(proj_x, proj_y, self.facing_right, is_enemy=False, projectile_type=ptype))
                
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
                    
                    # If was diving with plunge attack, plant weapon in ground with shockwave!
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
            return
            
        if not self.invulnerable:
            self.health -= amount
            self.invulnerable = True
            self.invulnerability_timer = 0.8
            if self.health <= 0:
                self.health = 0
                self.is_dead = True
                self.anim_manager.play("dead", force_reset=True)
                
    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        # 1. Draw Impact Smokes (Plunge VFX)
        for s in self.impact_smokes:
            s.draw(surface, camera_offset)
            
        # 2. Draw Dash After-Images (Ghost trail)
        for ghost in self.after_images:
            ghost.draw(surface, camera_offset)
            
        # 3. Draw Subtle Celestial Ring when 100 MP (Ultimate Ready)
        if self.mana >= 100 and not self.is_dead and not self.is_casting_ultimate:
            pulse_rad = int(32 + 3 * math.sin(pygame.time.get_ticks() * 0.006))
            aura_surf = pygame.Surface((pulse_rad * 2, pulse_rad * 2), pygame.SRCALPHA)
            col = getattr(self.profile, "color_theme", (255, 220, 90))
            pygame.draw.circle(aura_surf, (*col, 20), (pulse_rad, pulse_rad), pulse_rad)
            pygame.draw.circle(aura_surf, (*col, 45), (pulse_rad, pulse_rad), pulse_rad, width=2)
            surface.blit(aura_surf, (self.rect.centerx - camera_offset.x - pulse_rad, self.rect.centery - camera_offset.y - pulse_rad), special_flags=pygame.BLEND_RGBA_ADD)

        # 4. Ultimate Visual Sequence (Subtle cinematic dimming, ground rune & clean shockwaves)
        core_cx = self.rect.centerx - camera_offset.x
        core_cy = self.rect.centery - camera_offset.y - 4
        
        if self.is_casting_ultimate:
            gw, gh = surface.get_size()
            dark_surf = pygame.Surface((gw, gh), pygame.SRCALPHA)
            if self.ultimate_timer < 0.35:
                dark_alpha = int(65 * (self.ultimate_timer / 0.35))
            elif self.ultimate_timer < 1.10:
                dark_alpha = 65
            else:
                dark_alpha = max(0, int(65 * (1.0 - (self.ultimate_timer - 1.10) / 0.40)))
            dark_surf.fill((6, 4, 14, dark_alpha))
            surface.blit(dark_surf, (0, 0))
            
            # Subtle Sacred Runic Circle on the floor (radius 44)
            runic_alpha = int(180 * (min(1.0, self.ultimate_timer / 0.30) if self.ultimate_timer < 1.10 else max(0.0, 1.0 - (self.ultimate_timer - 1.10) / 0.40)))
            runic_cx = self.rect.centerx - camera_offset.x
            runic_cy = self.rect.bottom - camera_offset.y + 6
            draw_sacred_runic_circle(surface, (runic_cx, runic_cy), radius=44, angle=self.ultimate_rune_angle, alpha=runic_alpha)
            
            # Gentle starlight particles
            for p in self.ultimate_particles:
                p.draw(surface, camera_offset)
                
            # Expanding shockwave ripples (thin, clean)
            for ring in self.ultimate_shockwave_rings:
                ring.draw(surface, camera_offset)

        img = self.anim_manager.get_current_frame()
        
        # Calculate rendering position
        img_rect = img.get_rect()
        draw_x = self.rect.centerx - camera_offset.x - img_rect.width / 2
        ground_off = getattr(self.profile, "ground_offset_y", 7)
        draw_y = self.rect.bottom - camera_offset.y - img_rect.height + ground_off
        
        if not self.facing_right:
            img = pygame.transform.flip(img, True, False)
            
        # Blink when invulnerable (unless dashing/ultimate)
        if self.is_dashing or self.is_casting_ultimate or not self.invulnerable or int(self.invulnerability_timer * 10) % 2 == 0:
            surface.blit(img, (draw_x, draw_y))
            
            # Draw magical barrier or shield effect when blocking
            if self.is_blocking:
                if self.archetype == "mage":
                    rad = 36
                    bar_surf = pygame.Surface((rad * 2 + 8, rad * 2 + 8), pygame.SRCALPHA)
                    bc = rad + 4
                    col = self.profile.color_theme
                    pygame.draw.circle(bar_surf, (*col, 55), (bc, bc), rad)
                    pygame.draw.circle(bar_surf, (255, 255, 255, 200), (bc, bc), rad, 2)
                    pygame.draw.circle(bar_surf, (*col, 160), (bc, bc), max(1, rad - 3), 1)
                    t_rot = pygame.time.get_ticks() * 0.005
                    for i in range(6):
                        ang = t_rot + i * (math.pi / 3)
                        px = bc + int(math.cos(ang) * (rad - 5))
                        py = bc + int(math.sin(ang) * (rad - 5))
                        pygame.draw.circle(bar_surf, (255, 255, 255, 220), (px, py), 2)
                    surface.blit(bar_surf, (self.rect.centerx - camera_offset.x - bc, self.rect.centery - camera_offset.y - bc), special_flags=pygame.BLEND_RGBA_ADD)
                elif self.shield_anim:
                    shield_frame = self.shield_anim.get_current_frame()
                    if shield_frame:
                        if not self.facing_right:
                            shield_frame = pygame.transform.flip(shield_frame, True, False)
                        shield_rect = shield_frame.get_rect()
                        s_offset_x = 24 if self.facing_right else -24
                        s_x = self.rect.centerx - camera_offset.x + s_offset_x - shield_rect.width / 2
                        s_y = self.rect.centery - camera_offset.y - shield_rect.height / 2 + 7
                        surface.blit(shield_frame, (s_x, s_y))

        # 5. Magic Conjuration Sigil at hand
        if self.magic_sigil_timer > 0:
            sig_t = self.magic_sigil_timer / 0.38
            sig_alpha = int(220 * sig_t)
            sig_rad = int(14 + 10 * (1.0 - sig_t))
            hand_x = self.rect.right + 10 if self.facing_right else self.rect.left - 10
            hx = hand_x - camera_offset.x
            hy = self.rect.centery - camera_offset.y - 8
            sig_surf = pygame.Surface((sig_rad * 2 + 8, sig_rad * 2 + 8), pygame.SRCALPHA)
            sc = sig_rad + 4
            sig_col = getattr(self.profile, "color_theme", (255, 140, 40))
            pygame.draw.circle(sig_surf, (*sig_col, sig_alpha), (sc, sc), sig_rad, 2)
            pygame.draw.circle(sig_surf, (255, 255, 255, int(sig_alpha * 0.7)), (sc, sc), max(1, sig_rad - 4), 1)
            for i in range(4):
                ang = (1.0 - sig_t) * 3.5 + i * (math.pi / 2)
                sp_x = sc + int(math.cos(ang) * sig_rad)
                sp_y = sc + int(math.sin(ang) * sig_rad)
                ep_x = sc - int(math.cos(ang) * sig_rad)
                ep_y = sc - int(math.sin(ang) * sig_rad)
                pygame.draw.line(sig_surf, (*sig_col, sig_alpha), (sp_x, sp_y), (ep_x, ep_y), 1)
            surface.blit(sig_surf, (hx - sc, hy - sc), special_flags=pygame.BLEND_RGBA_ADD)

        # 6. Crisp Dimensional Blade Cleaves across screen
        for slash in self.ultimate_slashes:
            slash.draw(surface, camera_offset)
