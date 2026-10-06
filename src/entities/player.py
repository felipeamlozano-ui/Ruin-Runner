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
    def __init__(self, x: float, y: float, character_id: str = None, player_index: int = 0, input_device = None):
        from entities.character_data import get_character_profile
        from config.settings import SETTINGS
        if character_id is None:
            character_id = getattr(SETTINGS, "CURRENT_CHARACTER", "shaia") if player_index == 0 else getattr(SETTINGS, "P2_CHARACTER", "lunaria")
            
        if isinstance(input_device, str):
            self.input = INPUT.get_player(player_index)
            self.input.device = input_device
        elif input_device is not None:
            self.input = input_device
        else:
            self.input = INPUT.get_player(player_index)
        self.profile = get_character_profile(character_id)
        self.character_id = character_id.lower()
        self.archetype = self.profile.archetype
        
        # Position & Physics
        self.pos = pygame.math.Vector2(x, y)
        self.velocity = pygame.math.Vector2(0, 0)
        self.rect = pygame.FRect(x, y, self.profile.hitbox_size[0], self.profile.hitbox_size[1])
        self.ground_y = self.rect.bottom
        
        # Co-op Partner reference & revive state
        self.companion = None
        self.is_downed = False
        self.bleedout_timer = 30.0
        self.revive_progress = 0.0
        self.revive_duration = 2.5 # seconds
        self.reviving_target = None
        self.revive_channel = 0.0
        self.shield_buff_timer = 0.0
        
        # State
        self.on_ground = False
        self.can_double_jump = False
        
        # Stats & Magic Book (Grimoire) Upgrades
        from engine.save_manager import SAVE
        hp_bonus = SAVE.get_skill_level("titan_heart") * 15
        mp_bonus = SAVE.get_skill_level("cosmic_mana") * 15
        blade_lv = SAVE.get_skill_level("blade_sharpness")
        self.blade_damage_mult = 1.0 + (blade_lv * 0.12)
        
        self.max_health = self.profile.hp_max + hp_bonus
        self.health = self.max_health
        self.max_mana = float(self.profile.mp_max) + mp_bonus
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
        self.attack_cooldown = 0.0
        self.attack_hit_enemies: set = set()
        self.is_dashing = False
        self.dash_timer = 0.0
        self.dash_duration = 0.18
        self.dash_cooldown = 0.0
        self.dash_ghost_timer = 0.0
        self.after_images: list[AfterImage] = []
        
        # Asymmetric Survival & Passives
        self.passive_id = getattr(self.profile, "passive_id", "")
        self.stamina_regen_delay = 0.0
        self.is_drinking_potion = False
        self.potion_timer = 0.0
        self.potion_duration = 1.6 # 1.6s Channel
        self.potion_heal_amount = 40
        self.still_timer = 0.0
        self.celestial_barrier_active = (self.passive_id == "astra_celestial_barrier")
        self.celestial_barrier_cooldown = 0.0
        # New character passives & mechanics state
        self.parry_window_timer = 0.0
        self.solar_fusion_stacks = 0
        self.solar_fusion_timer = 0.0
        self.death_mark_hits = {}
        
        # AoE Nova Skill
        self.is_casting_aoe = False
        self.aoe_timer = 0.0
        self.aoe_hit_done = False
        self.aoe_radius = 150.0
        self.aoe_vfx = None
        
        # Magic Projectile [K] Cast State & Animation
        self.is_casting_magic = False
        self.magic_cast_timer = 0.0
        self.magic_sigil_timer = 0.0
        # Dedicated Triple-AAA Ultimate Controller for this specific character
        from entities.ultimate_system import create_ultimate
        self.ultimate_controller = create_ultimate(self.character_id)
        self.is_casting_ultimate = False
        
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
            
            self.anim_manager.add_animation("idle", load_animation_folder(base_path, "common_00_idle_stand_A", 12, True, scale))
            self.anim_manager.add_animation("walk", load_animation_folder(base_path, "common_11_walk", 11, True, scale))
            self.anim_manager.add_animation("jump", load_animation_folder(base_path, "common_21_jump_up", 14, False, scale))
            self.anim_manager.add_animation("fall", load_animation_folder(base_path, "common_21_jump_down", 14, True, scale))
            self.anim_manager.add_animation("attack", load_animation_folder(attack_path, "attack_01_cobination01", 13, False, scale))
            self.anim_manager.add_animation("cast_magic", load_animation_folder(attack_path, "attack_03_cobination03", 20, False, scale))
            self.anim_manager.add_animation("dash", load_animation_folder(append_path, "common_12_guard_dash", 18, False, scale))
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
                jump_p = os.path.join(bf, "Jump.png")
                dead_p = os.path.join(bf, "Dead.png")
                hurt_p = os.path.join(bf, "Hurt.png")
                
                self.anim_manager.add_animation("idle", load_spritesheet(idle_p, fw, fh, 5, True, scale))
                self.anim_manager.add_animation("walk", load_spritesheet(walk_p, fw, fh, 9, True, scale))
                
                # Dedicated Bespoke Jump & Fall for Mages:
                if os.path.exists(jump_p):
                    self.anim_manager.add_animation("jump", load_spritesheet(jump_p, fw, fh, 10, False, scale, start_frame=0, max_frames=3))
                    self.anim_manager.add_animation("fall", load_spritesheet(jump_p, fw, fh, 8, True, scale, start_frame=2, max_frames=2))
                else:
                    self.anim_manager.add_animation("jump", load_spritesheet(atk_p, fw, fh, 11, False, scale, start_frame=0, max_frames=2))
                    self.anim_manager.add_animation("fall", load_spritesheet(atk_p, fw, fh, 9, True, scale, start_frame=1, max_frames=2))
                    
                self.anim_manager.add_animation("attack", load_spritesheet(atk_p, fw, fh, 14, False, scale))
                self.anim_manager.add_animation("cast_magic", load_spritesheet(atk_p, fw, fh, 14, False, scale, start_frame=1, max_frames=4))
                self.anim_manager.add_animation("whirlwind", load_spritesheet(atk_p, fw, fh, 16, False, scale))
                self.anim_manager.add_animation("heavy_slash", load_spritesheet(atk_p, fw, fh, 14, False, scale))
                self.anim_manager.add_animation("jump_attack", load_spritesheet(atk_p, fw, fh, 14, True, scale))
                self.anim_manager.add_animation("landing", load_spritesheet(idle_p, fw, fh, 12, False, scale, start_frame=0, max_frames=2))
                self.anim_manager.add_animation("guard", load_spritesheet(prot_p, fw, fh, 9, True, scale))
                if os.path.exists(dead_p):
                    self.anim_manager.add_animation("dead", load_spritesheet(dead_p, fw, fh, 8, False, scale))
                else:
                    self.anim_manager.add_animation("dead", load_spritesheet(atk_p, fw, fh, 8, False, scale, start_frame=2, max_frames=4))
                if os.path.exists(hurt_p):
                    self.anim_manager.add_animation("hurt", load_spritesheet(hurt_p, fw, fh, 10, False, scale))
                self.anim_manager.add_animation("dash", load_spritesheet(walk_p, fw, fh, 16, False, scale))
            else:
                def _find_sheet(folder, *candidates):
                    for c in candidates:
                        cp = os.path.join(folder, c)
                        if os.path.exists(cp):
                            return cp
                    return os.path.join(folder, candidates[0])

                idle_p = _find_sheet(bf, "Idle.png")
                walk_p = _find_sheet(bf, "Walk.png")
                run_p = _find_sheet(bf, "Run.png", "Walk.png")
                jump_p = _find_sheet(bf, "Jump.png")
                atk1_p = _find_sheet(bf, "Attack_1.png", "Attack 1.png", "Attack.png")
                atk2_p = _find_sheet(bf, "Attack_2.png", "Attack 2.png", "Flame_jet.png", "Shot.png", "Attack.png")
                atk3_p = _find_sheet(bf, "Attack_3.png", "Attack 3.png", "Flame_jet.png", "Shot.png", "Cast.png", "Attack_2.png", "Attack 2.png")
                shield_p = _find_sheet(bf, "Shield.png", "Defend.png", "Protect.png", "Protection.png", "Idle.png")
                dead_p = _find_sheet(bf, "Dead.png", "Hurt.png")
                hurt_p = _find_sheet(bf, "Hurt.png")
                
                self.anim_manager.add_animation("idle", load_spritesheet(idle_p, fw, fh, 6, True, scale))
                self.anim_manager.add_animation("walk", load_spritesheet(walk_p, fw, fh, 9, True, scale))
                
                # Dedicated Bespoke Jump & Fall for characters:
                if self.profile.id in ("fighter",):
                    self.anim_manager.add_animation("jump", load_spritesheet(jump_p, fw, fh, 12, False, scale, start_frame=3, max_frames=3))
                    self.anim_manager.add_animation("fall", load_spritesheet(jump_p, fw, fh, 9, True, scale, start_frame=6, max_frames=2))
                    self.anim_manager.add_animation("landing", load_spritesheet(jump_p, fw, fh, 12, False, scale, start_frame=8, max_frames=2))
                elif self.profile.id in ("samurai",):
                    self.anim_manager.add_animation("jump", load_spritesheet(jump_p, fw, fh, 12, False, scale, start_frame=5, max_frames=3))
                    self.anim_manager.add_animation("fall", load_spritesheet(jump_p, fw, fh, 9, True, scale, start_frame=7, max_frames=2))
                    self.anim_manager.add_animation("landing", load_spritesheet(jump_p, fw, fh, 12, False, scale, start_frame=9, max_frames=3))
                elif self.profile.id in ("shinobi",):
                    self.anim_manager.add_animation("jump", load_spritesheet(jump_p, fw, fh, 12, False, scale, start_frame=4, max_frames=3))
                    self.anim_manager.add_animation("fall", load_spritesheet(jump_p, fw, fh, 9, True, scale, start_frame=6, max_frames=3))
                    self.anim_manager.add_animation("landing", load_spritesheet(jump_p, fw, fh, 12, False, scale, start_frame=9, max_frames=3))
                elif self.profile.id in ("samurai_archer", "archer", "kaelen"):
                    self.anim_manager.add_animation("jump", load_spritesheet(jump_p, fw, fh, 12, False, scale, start_frame=0, max_frames=3))
                    self.anim_manager.add_animation("fall", load_spritesheet(jump_p, fw, fh, 9, True, scale, start_frame=3, max_frames=3))
                    self.anim_manager.add_animation("landing", load_spritesheet(jump_p, fw, fh, 12, False, scale, start_frame=6, max_frames=2))
                elif self.profile.id in ("kunoichi", "ninja", "aurelia"):
                    self.anim_manager.add_animation("jump", load_spritesheet(jump_p, fw, fh, 12, False, scale, start_frame=0, max_frames=3))
                    self.anim_manager.add_animation("fall", load_spritesheet(jump_p, fw, fh, 9, True, scale, start_frame=4, max_frames=3))
                    self.anim_manager.add_animation("landing", load_spritesheet(jump_p, fw, fh, 12, False, scale, start_frame=7, max_frames=2))
                elif self.profile.id in ("wizard", "zephyr"):
                    self.anim_manager.add_animation("jump", load_spritesheet(jump_p, fw, fh, 12, False, scale, start_frame=0, max_frames=3))
                    self.anim_manager.add_animation("fall", load_spritesheet(jump_p, fw, fh, 9, True, scale, start_frame=3, max_frames=3))
                    self.anim_manager.add_animation("landing", load_spritesheet(idle_p, fw, fh, 12, False, scale, start_frame=0, max_frames=2))
                elif self.profile.id in ("knight", "boran"):
                    self.anim_manager.add_animation("jump", load_spritesheet(jump_p, fw, fh, 12, False, scale, start_frame=0, max_frames=3))
                    self.anim_manager.add_animation("fall", load_spritesheet(jump_p, fw, fh, 9, True, scale, start_frame=3, max_frames=2))
                    self.anim_manager.add_animation("landing", load_spritesheet(jump_p, fw, fh, 12, False, scale, start_frame=4, max_frames=2))
                else: # Generic fallback
                    self.anim_manager.add_animation("jump", load_spritesheet(jump_p, fw, fh, 12, False, scale))
                    self.anim_manager.add_animation("fall", load_spritesheet(jump_p, fw, fh, 9, True, scale))
                    self.anim_manager.add_animation("landing", load_spritesheet(idle_p, fw, fh, 12, False, scale, start_frame=0, max_frames=2))
                    
                self.anim_manager.add_animation("attack", load_spritesheet(atk1_p, fw, fh, 14, False, scale))
                self.anim_manager.add_animation("cast_magic", load_spritesheet(atk2_p, fw, fh, 14, False, scale))
                self.anim_manager.add_animation("whirlwind", load_spritesheet(atk3_p, fw, fh, 14, False, scale))
                self.anim_manager.add_animation("heavy_slash", load_spritesheet(atk3_p, fw, fh, 14, False, scale))
                self.anim_manager.add_animation("jump_attack", load_spritesheet(atk1_p, fw, fh, 14, True, scale))
                self.anim_manager.add_animation("guard", load_spritesheet(shield_p, fw, fh, 6, True, scale))
                self.anim_manager.add_animation("dead", load_spritesheet(dead_p, fw, fh, 9, False, scale))
                self.anim_manager.add_animation("dash", load_spritesheet(run_p, fw, fh, 16, False, scale))
                if os.path.exists(hurt_p):
                    self.anim_manager.add_animation("hurt", load_spritesheet(hurt_p, fw, fh, 12, False, scale))
        self.hurt_timer = 0.0
        self.combo_index = 0
        self.combo_timer = 0.0
        self.attack_anim_name = "attack"
        self._pending_shots = []
        self._anchor_cache = {}
        if self.profile.id in self.NEW_HERO_IDS:
            self._load_new_hero_animations()
        self.anim_manager.play("idle")
        self.is_attacking = False
        self.is_dead = False

    NEW_HERO_IDS = ("knight", "wizard", "samurai_archer", "kunoichi")
    # Seconds after the attack/cast animation starts when the projectile is actually released
    NEW_HERO_RELEASE_DELAY = {"knight": 0.12, "wizard": 0.16, "samurai_archer": 0.10, "kunoichi": 0.09}

    def _load_new_hero_animations(self):
        """Bespoke, correctly-sliced animation sets for Galahad, Ignatius, Hanzo and Ayame."""
        bf = self.profile.base_folder
        fw, fh = self.profile.frame_size
        sc = self.profile.sprite_scale

        def L(name, fps, loop=True, start=0, count=0):
            return load_spritesheet(os.path.join(bf, name), fw, fh, fps, loop, sc, start_frame=start, max_frames=count)

        pid = self.profile.id
        if pid == "knight":
            spec = {
                "idle": L("Idle.png", 6), "walk": L("Walk.png", 10), "run": L("Run.png", 14),
                "attack": L("Attack 1.png", 20, False), "attack2": L("Attack 2.png", 18, False),
                "attack3": L("Attack 3.png", 18, False),
                "cast_magic": L("Run+Attack.png", 20, False),
                "whirlwind": L("Attack 2.png", 12, False), "heavy_slash": L("Attack 3.png", 12, False),
                "jump_attack": L("Attack 1.png", 14, True),
                "guard": L("Defend.png", 16, False),
                "jump": L("Jump.png", 12, False, 0, 3), "fall": L("Jump.png", 9, True, 3, 2),
                "landing": L("Jump.png", 14, False, 4, 2),
                "dash": L("Run.png", 22, True),
                "dead": L("Dead.png", 9, False), "hurt": L("Hurt.png", 10, False),
            }
        elif pid == "wizard":
            spec = {
                "idle": L("Idle.png", 7), "walk": L("Walk.png", 9), "run": L("Run.png", 12),
                "attack": L("Attack_1.png", 16, False), "attack2": L("Attack_2.png", 16, False),
                "cast_magic": L("Fireball.png", 22, False, 1, 7),
                "whirlwind": L("Flame_jet.png", 22, False), "heavy_slash": L("Attack_2.png", 12, False),
                "jump_attack": L("Attack_2.png", 14, True),
                "guard": L("Idle.png", 6),
                "jump": L("Jump.png", 12, False, 0, 3), "fall": L("Jump.png", 9, True, 3, 3),
                "landing": L("Jump.png", 16, False, 6, 3),
                "dash": L("Run.png", 20, True),
                "dead": L("Dead.png", 8, False), "hurt": L("Hurt.png", 12, False),
            }
        elif pid == "samurai_archer":
            spec = {
                "idle": L("Idle.png", 8), "walk": L("Walk.png", 10), "run": L("Run.png", 14),
                "attack": L("Shot.png", 36, False, 4, 10), "cast_magic": L("Shot.png", 36, False, 4, 10),
                "whirlwind": L("Shot.png", 22, False), "heavy_slash": L("Attack_3.png", 14, False),
                "jump_attack": L("Attack_1.png", 14, True),
                "guard": L("Idle.png", 6),
                "jump": L("Jump.png", 12, False, 0, 3), "fall": L("Jump.png", 9, True, 3, 3),
                "landing": L("Jump.png", 16, False, 6, 3),
                "dash": L("Run.png", 22, True),
                "dead": L("Dead.png", 8, False), "hurt": L("Hurt.png", 12, False),
            }
        else:  # kunoichi
            spec = {
                "idle": L("Idle.png", 9), "walk": L("Walk.png", 10), "run": L("Run.png", 14),
                "attack": L("Attack_1.png", 18, False), "attack2": L("Attack_2.png", 20, False),
                "cast_magic": L("Cast.png", 20, False),
                "whirlwind": L("Attack_2.png", 22, False), "heavy_slash": L("Attack_2.png", 14, False),
                "jump_attack": L("Attack_1.png", 14, True),
                "guard": L("Idle.png", 6),
                "jump": L("Jump.png", 12, False, 0, 4), "fall": L("Jump.png", 9, True, 4, 3),
                "landing": L("Jump.png", 16, False, 7, 3),
                "dash": L("Run.png", 24, True),
                "dead": L("Dead.png", 8, False), "hurt": L("Hurt.png", 10, False),
            }
        for name, anim in spec.items():
            if anim.frames:
                self.anim_manager.add_animation(name, anim)

    def _anchor_x(self, state: str, img_w: int) -> float:
        """Horizontal body anchor inside the frame. New hero sheets are not centered in their 128px
        frames, so the body (not the frame) must be aligned with the hitbox."""
        if self.profile.id not in self.NEW_HERO_IDS:
            return img_w / 2
        key = state if state in ("walk", "run", "dash") else "idle"
        cached = self._anchor_cache.get(key)
        if cached is not None:
            return cached
        anim = self.anim_manager.animations.get(key)
        centers = []
        if anim:
            for f in anim.frames:
                r = f.get_bounding_rect()
                if r.w:
                    centers.append(r.centerx)
        val = sum(centers) / len(centers) if centers else img_w / 2
        self._anchor_cache[key] = val
        return val

    def _begin_attack_anim(self):
        """Starts the [J] animation, chaining combo variants when the hero has them."""
        names = ["attack"] + [n for n in ("attack2", "attack3") if self.anim_manager.has_animation(n)]
        if self.combo_timer > 0 and len(names) > 1:
            self.combo_index = (self.combo_index + 1) % len(names)
        else:
            self.combo_index = 0
        self.combo_timer = 0.9
        self.attack_anim_name = names[self.combo_index]
        self.anim_manager.play(self.attack_anim_name, force_reset=True)

    def _defer_new_projectiles(self, n_before: int):
        """Delays projectiles spawned this frame until the release frame of the animation."""
        if (self.profile.id in self.NEW_HERO_IDS and len(self.projectiles) > n_before
                and (self.is_attacking or self.is_casting_magic)):
            delay = self.NEW_HERO_RELEASE_DELAY.get(self.profile.id, 0.1)
            new = self.projectiles[n_before:]
            del self.projectiles[n_before:]
            for p in new:
                self._pending_shots.append([delay, p])

    @property
    def ultimate_hit_done(self) -> bool:
        return getattr(self.ultimate_controller, "damage_applied", False)

    @property
    def ultimate_timer(self) -> float:
        return getattr(self.ultimate_controller, "timer", 0.0)

    @property
    def can_dash(self) -> bool:
        dash_cost = 12 if self.passive_id in ("shinobi_shadow_step", "kunoichi_silent_strike") else 25
        return (not self.is_dashing and not self.is_drinking_potion and self.dash_cooldown <= 0 and self.stamina >= dash_cost)
        return (not self.is_dashing and not self.is_drinking_potion and self.dash_cooldown <= 0 and self.stamina >= dash_cost)

    @property
    def can_attack(self) -> bool:
        return (self.attack_cooldown <= 0 and not self.is_attacking and not self.is_blocking and not self.is_drinking_potion and not self.is_dashing)

    def dash(self) -> bool:
        """Executes dash if stamina and cooldown permit."""
        dash_cost = 15 if self.passive_id == "shinobi_shadow_step" else 25
        dash_speed = (self.dash_speed * 1.2) if self.passive_id == "shinobi_shadow_step" else self.dash_speed
        if not self.is_dashing and not self.is_drinking_potion and self.dash_cooldown <= 0 and self.stamina >= dash_cost:
            self.stamina -= dash_cost
            self.stamina_regen_delay = 0.5
            self.is_dashing = True
            self.dash_timer = self.dash_duration
            self.dash_cooldown = 0.45
            self.invulnerable = True
            self.invulnerability_timer = self.dash_duration + 0.1
            self.velocity.y = 0
            self.velocity.x = dash_speed if self.facing_right else -dash_speed
            self.anim_manager.play("dash", force_reset=True)
            
            # Samurai Passive: Foco Perfeito (Perfect Dodge resets basic attack cooldown)
            if self.passive_id == "samurai_perfect_focus":
                self.attack_cooldown = 0.0
            return True
        return False
        
    def start_drinking_potion(self, heal_amount: int = 40):
        """Starts potion drinking channel (slow movement, dodge disabled, heals upon completion)."""
        self.is_drinking_potion = True
        self.potion_timer = self.potion_duration
        self.potion_heal_amount = heal_amount

    def update(self, dt: float, tiles: list[pygame.FRect], enemies=None, camera=None):
        # Co-op Downed State Check
        if self.is_downed:
            self.bleedout_timer -= dt
            self.velocity.x *= FRICTION
            if self.bleedout_timer <= 0:
                self.health = 0
                self.is_dead = True
                self.is_downed = False
                self.anim_manager.play("dead", force_reset=True)
            self._apply_physics(dt, tiles)
            return

        # Co-op Proximity Passive Synergies
        if self.companion and not getattr(self.companion, "is_dead", False) and not getattr(self.companion, "is_downed", False):
            c_dist = math.hypot(self.companion.rect.centerx - self.rect.centerx, self.companion.rect.centery - self.rect.centery)
            if c_dist <= 240.0:
                # Aurelia: Graça da Alvorada (+2 HP/s)
                if self.passive_id == "aurelia_dawn_grace":
                    self.companion.health = min(self.companion.max_health, self.companion.health + 2.0 * dt)
                # Zephyr: Fluxo de Éter (+2.5 MP/s)
                if self.passive_id == "zephyr_ether_stream":
                    self.companion.mana = min(self.companion.max_mana, self.companion.mana + 2.5 * dt)

        # ── Co-op Revive Channeling (Single authoritative system) ──────────────
        # Reviver stands within 75px and holds [F/INTERACT] or [DEFEND] for 2.5s.
        # Only runs when THIS player is alive and companion is downed.
        if self.companion and getattr(self.companion, "is_downed", False) and not self.is_dead:
            c_dist = math.hypot(self.companion.rect.centerx - self.rect.centerx,
                                self.companion.rect.centery - self.rect.centery)
            in_range = c_dist <= 75.0
            holding_revive = (self.input.is_action_pressed("INTERACT") or
                              self.input.is_action_pressed("DEFEND") or
                              (getattr(self, "reviving_target", None) == self.companion))
            if (in_range and holding_revive) or (getattr(self, "reviving_target", None) == self.companion):
                # Aurelia revives 2x faster (passive)
                revive_speed = 2.0 if self.passive_id == "aurelia_dawn_grace" else 1.0
                self.revive_channel += dt * revive_speed
                if self.revive_channel >= 2.5:
                    # REVIVE SUCCESS
                    self.companion.is_downed = False
                    self.companion.is_dead = False
                    self.companion.bleedout_timer = 30.0  # Reset bleedout timer
                    self.companion.health = max(1, int(self.companion.max_health * 0.45))
                    self.companion.invulnerable = True
                    self.companion.invulnerability_timer = 2.0
                    self.companion.revive_channel = 0.0
                    self.companion.anim_manager.play("idle", force_reset=True)
                    self.revive_channel = 0.0
            else:
                # Slowly decay revive progress when not channeling
                self.revive_channel = max(0.0, self.revive_channel - dt * 0.5)

        if self.invulnerable:
            self.invulnerability_timer -= dt
            if self.invulnerability_timer <= 0:
                self.invulnerable = False
                
        if self.dash_cooldown > 0:
            self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        if self.attack_cooldown > 0:
            self.attack_cooldown = max(0.0, self.attack_cooldown - dt)
        if self.hurt_timer > 0:
            self.hurt_timer = max(0.0, self.hurt_timer - dt)
        if self.combo_timer > 0:
            self.combo_timer = max(0.0, self.combo_timer - dt)
        if self._pending_shots:
            for item in self._pending_shots[:]:
                item[0] -= dt
                if item[0] <= 0:
                    self.projectiles.append(item[1])
                    self._pending_shots.remove(item)
        if self.stamina_regen_delay > 0:
            self.stamina_regen_delay = max(0.0, self.stamina_regen_delay - dt)
            
        # Potion Drinking Timer
        if self.is_drinking_potion:
            self.potion_timer -= dt
            if self.potion_timer <= 0:
                self.is_drinking_potion = False
                self.health = min(self.max_health, self.health + self.potion_heal_amount)
                
        # Astra Celestial Barrier Recharge
        if not self.celestial_barrier_active and self.passive_id == "astra_celestial_barrier":
            self.celestial_barrier_cooldown -= dt
            if self.celestial_barrier_cooldown <= 0:
                self.celestial_barrier_active = True
                
        # Lunaria Still Timer
        if self.passive_id == "lunaria_arcane_resonance":
            if abs(self.velocity.x) < 5 and not self.is_attacking and not self.is_casting_magic and self.on_ground:
                self.still_timer += dt
            else:
                self.still_timer = 0.0

        # Knight Parry Window decay
        if self.parry_window_timer > 0:
            self.parry_window_timer = max(0.0, self.parry_window_timer - dt)

        # Wizard Solar Fusion passive: stacks decay after 4s without casting, grants mana regen
        if self.passive_id == "wizard_solar_fusion":
            if self.solar_fusion_stacks > 0:
                self.solar_fusion_timer -= dt
                if self.solar_fusion_timer <= 0:
                    self.solar_fusion_stacks = max(0, self.solar_fusion_stacks - 1)
                    self.solar_fusion_timer = 1.0 if self.solar_fusion_stacks > 0 else 0.0
                # Stacks restore mana: 2.0 MP/s per stack!
                self.mana = min(self.max_mana, self.mana + (self.solar_fusion_stacks * 2.0) * dt)
            
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
                _ax = self._anchor_x(self.anim_manager.current_state, img_rect.width)
                draw_x = self.rect.centerx - (_ax if self.facing_right else img_rect.width - _ax)
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
            if self.aoe_vfx and self.aoe_vfx.active:
                self.aoe_vfx.update(dt)
            if self.anim_manager.is_finished("whirlwind") or self.aoe_timer <= 0:
                self.is_casting_aoe = False
                
        # Check if attack animation finished
        if self.is_attacking and self.anim_manager.is_finished(self.attack_anim_name):
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
                self.anim_manager.play("idle")
                
        # Update Magic Casting State
        if self.is_casting_magic:
            self.magic_cast_timer -= dt
            if self.magic_cast_timer <= 0 or self.anim_manager.is_finished("cast_magic"):
                self.is_casting_magic = False
        if self.magic_sigil_timer > 0:
            self.magic_sigil_timer -= dt

        # Update Dedicated Triple-AAA Ultimate Controller
        if self.is_casting_ultimate:
            self.ultimate_controller.update(dt, self, enemies, camera)
            if not self.ultimate_controller.active:
                self.is_casting_ultimate = False
                self.invulnerable = True
                self.invulnerability_timer = 0.5
                self.anim_manager.play("idle")

        _n_proj = len(self.projectiles)
        self._handle_input(dt)
        self._defer_new_projectiles(_n_proj)
        self._apply_physics(dt, tiles)
        self._update_animation(dt)
        self.anim_manager.update(dt)
        
        # Check if attack animation finished immediately
        if self.is_attacking and self.anim_manager.is_finished(self.attack_anim_name):
            self.is_attacking = False
        
    def get_attack_hitbox(self) -> pygame.FRect:
        """Returns the hitbox for the attack if currently attacking, else None."""
        if self.is_down_attacking:
            return pygame.FRect(self.rect.x - 12, self.rect.bottom - 10, self.rect.width + 24, 38)
            
        # Mages attack exclusively through magic projectiles, no melee sword collision
        if not self.is_attacking or self.archetype == "mage":
            return None
        
        hitbox_width = 72
        hitbox_height = 70
        hitbox_y = self.rect.bottom - hitbox_height
        if self.facing_right:
            return pygame.FRect(self.rect.centerx - 10, hitbox_y, hitbox_width, hitbox_height)
        else:
            return pygame.FRect(self.rect.centerx + 10 - hitbox_width, hitbox_y, hitbox_width, hitbox_height)
            
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
                        e.take_damage(10)
                        e.velocity.y = -260
                        e.velocity.x = 280 if e.rect.centerx > self.rect.centerx else -280
                        
        # 3. Direct mid-air hits while plunging down (Buffed dive damage)
        if self.is_down_attacking:
            down_hitbox = self.get_attack_hitbox()
            if down_hitbox:
                for e in enemies:
                    if not e.is_dead and e not in self.plunge_hit_enemies and down_hitbox.colliderect(e.rect):
                        self.plunge_hit_enemies.add(e)
                        e.take_damage(5)
                        e.velocity.y = -120
                        
    def _update_animation(self, dt: float):
        # Character-specific mana regeneration (Lunaria doubles it when standing still for >= 2.0s)
        # Note: Do not regenerate mana while actively blocking with mana shield
        mana_mult = 2.0 if (self.passive_id == "lunaria_arcane_resonance" and self.still_timer >= 2.0) else 1.0
        if self.mana < self.max_mana and not (self.is_blocking and self.archetype == "mage"):
            self.mana = min(self.max_mana, self.mana + self.mana_regen * mana_mult * dt)
            
        if self.is_dead:
            self.anim_manager.play("dead")
        elif self.is_casting_ultimate:
            ut = getattr(self.ultimate_controller, "timer", 0.0)
            if ut < 0.35:
                self.anim_manager.play("guard")
            elif ut < 0.95:
                if self.anim_manager.has_animation("whirlwind"):
                    self.anim_manager.play("whirlwind")
                else:
                    self.anim_manager.play("attack")
            else:
                self.anim_manager.play("attack")
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
            self.anim_manager.play(self.attack_anim_name)
        elif self.hurt_timer > 0 and self.anim_manager.has_animation("hurt"):
            self.anim_manager.play("hurt")
        elif not self.on_ground:
            if self.velocity.y < 0:
                self.anim_manager.play("jump")
            else:
                self.anim_manager.play("fall")
        elif abs(self.velocity.x) > 10:
            if self.anim_manager.has_animation("run") and abs(self.velocity.x) > self.speed * 0.6:
                self.anim_manager.play("run")
            else:
                self.anim_manager.play("walk")
        else:
            self.anim_manager.play("idle")
            
    def _handle_input(self, dt: float):
        if self.is_dead or self.is_downed:
            self.velocity.x *= FRICTION
            return
            
        if self.is_landing_plunge:
            self.velocity.x = 0
            return
            
        # Co-op Downed Partner: Lock movement to revive area, show progress
        if self.companion and getattr(self.companion, "is_downed", False) and not self.is_dead:
            c_dist = math.hypot(self.companion.rect.centerx - self.rect.centerx,
                                self.companion.rect.centery - self.rect.centery)
            if c_dist <= 75.0 and (self.input.is_action_pressed("INTERACT") or self.input.is_action_pressed("DEFEND")):
                # Freeze in place while channeling revive
                self.velocity.x = 0
                return
            
        # Potion drinking locks out attack, skills, and jumping
        if self.is_drinking_potion:
            axis = self.input.get_axis()
            if axis.x != 0:
                self.velocity.x += axis.x * ACCELERATION * dt
                self.velocity.x = clamp(self.velocity.x, -self.speed * 0.30, self.speed * 0.30)
                self.facing_right = axis.x > 0
            else:
                self.velocity.x *= FRICTION
                if abs(self.velocity.x) < 5:
                    self.velocity.x = 0
            return
            
        if self.is_casting_ultimate:
            self.velocity.x = 0
            return
            
        # Down-Attack (Dive / Plunge Attack with Sword) - Mid-air [S] + [J]
        if not self.on_ground and self.input.is_action_just_pressed("ATTACK") and not self.is_dashing and not self.is_down_attacking and not self.is_blocking:
            axis = self.input.get_axis()
            if axis.y > 0 or self.input.is_action_pressed("DOWN"):
                self.is_down_attacking = True
                self.velocity.y = 520
                self.velocity.x = 0
                self.anim_manager.play("jump_attack", force_reset=True)
                return
                
        # Skill [R] - Ultimate Skill (Costs 100% of maximum Mana)
        if self.input.is_action_just_pressed("ULTIMATE") and not self.is_attacking and not self.is_blocking and not self.is_dashing and not self.is_casting_magic and not self.is_casting_ultimate:
            r_skill = self.profile.skills.get("r", None)
            if r_skill:
                ult_cost = r_skill.cost_value
                if self.mana >= ult_cost:
                    self.mana = 0.0
                    self.is_casting_ultimate = True
                    self.ultimate_controller.trigger(self.rect.centerx, self.rect.bottom, self.facing_right)
                    self.velocity.x = 0
                    self.velocity.y = 0
                    return
                
        # Dash [Q]
        if self.input.is_action_just_pressed("DASH"):
            if self.dash():
                return
            
        if self.is_dashing:
            return
            
        # Skill [E] - AoE Nova / Whirlwind
        if self.input.is_action_just_pressed("SKILL_AOE") and not self.is_casting_aoe and not self.is_attacking and not self.is_blocking and not self.is_drinking_potion:
            e_skill = self.profile.skills.get("e", None)
            if e_skill:
                can_cast = (self.mana >= e_skill.cost_value) if e_skill.cost_type == "MP" else (self.stamina >= e_skill.cost_value)
                if can_cast:
                    if e_skill.cost_type == "MP":
                        self.mana -= e_skill.cost_value
                    else:
                        self.stamina -= e_skill.cost_value
                        self.stamina_regen_delay = 0.5
                    self.is_casting_aoe = True
                    self.aoe_timer = 0.85
                    self.aoe_hit_done = False
                    self.anim_manager.play("whirlwind", force_reset=True)
                    from entities.ultimate_aoe_vfx import UltimateAoE_VFX
                    self.aoe_vfx = UltimateAoE_VFX(self.rect.centerx, self.rect.bottom, self.aoe_radius, self.profile.id)
                    
        # Blocking / Guard / Special Mobility [Shift]
        shift_skill = self.profile.skills.get("shift", None)
        shift_cost = shift_skill.cost_value if shift_skill else 3
        is_mage = (self.archetype in ("mage", "healer", "support"))
        can_block = (self.mana > 0) if is_mage else (self.stamina > 0)

        # Bespoke [Shift] triggers on initial press for mobile archetypes:
        if self.input.is_action_just_pressed("DEFEND") and not self.is_drinking_potion:
            # Wizard: Passo de Cinzas (Blink de Brasas)
            if self.character_id == "wizard" and self.mana >= 12:
                self.mana -= 12
                dir_mult = 1.0 if self.facing_right else -1.0
                self.pos.x += dir_mult * 70.0
                self.rect.x = self.pos.x
                self.invulnerable = True
                self.invulnerability_timer = 0.28
                self.anim_manager.play("dash", force_reset=True)
                return
            # Samurai Archer: Salto Tático com Abrolhos
            elif self.character_id == "samurai_archer" and self.stamina >= 10:
                self.stamina -= 10
                self.stamina_regen_delay = 0.5
                dir_mult = -1.0 if self.facing_right else 1.0
                self.velocity.x = dir_mult * 260.0
                self.velocity.y = -220.0
                self.on_ground = False
                self.invulnerable = True
                self.invulnerability_timer = 0.30
                self.anim_manager.play("jump", force_reset=True)
                return
            # Kunoichi: Kawarimi no Jutsu (Substituição)
            elif self.character_id == "kunoichi" and self.stamina >= 15:
                self.stamina -= 15
                self.stamina_regen_delay = 0.5
                dir_mult = 1.0 if self.facing_right else -1.0
                self.pos.x += dir_mult * 75.0
                self.rect.x = self.pos.x
                self.invulnerable = True
                self.invulnerability_timer = 0.45
                self.anim_manager.play("dash", force_reset=True)
                return
        
        if self.input.is_action_pressed("DEFEND") and can_block and not self.is_drinking_potion:
            if not self.is_blocking:
                self.parry_window_timer = 0.20
            self.is_blocking = True
            if is_mage:
                self.mana = max(0.0, self.mana - shift_cost * dt)
            else:
                self.stamina = max(0.0, self.stamina - shift_cost * dt)
            self.stamina_regen_delay = 0.5
            self.velocity.x = 0
            return
        else:
            self.is_blocking = False
            # Regenerate stamina (only if not blocking and delay expired)
            if self.stamina_regen_delay <= 0:
                self.stamina = min(self.max_stamina, self.stamina + self.stamina_regen * dt)
            
        if self.is_attacking:
            if self.on_ground:
                self.velocity.x *= FRICTION
                if abs(self.velocity.x) < 5:
                    self.velocity.x = 0
            return
            
        # Horizontal Movement (slowed to 30% while drinking potion)
        axis = self.input.get_axis()
        speed_mult = 0.30 if self.is_drinking_potion else 1.0
        
        if axis.x != 0:
            self.velocity.x += axis.x * ACCELERATION * dt
            self.velocity.x = clamp(self.velocity.x, -self.speed * speed_mult, self.speed * speed_mult)
            self.facing_right = axis.x > 0
        else:
            # Apply friction
            self.velocity.x *= FRICTION
            if abs(self.velocity.x) < 5:
                self.velocity.x = 0
                
        # Jumping (Fluid response to dodge attacks with double-jump)
        if self.input.is_action_just_pressed("JUMP") and not self.is_blocking and not self.is_drinking_potion:
            if self.on_ground:
                self.velocity.y = self.jump_speed
                self.on_ground = False
                self.can_double_jump = True
            elif self.can_double_jump:
                self.velocity.y = self.jump_speed * 0.70
                self.can_double_jump = False
                
        # Ground Attack [J] - 0.25s snappy attack cooldown via delta time
        if self.input.is_action_just_pressed("ATTACK") and not self.is_attacking and not self.is_blocking and not self.is_drinking_potion and self.attack_cooldown <= 0:
            j_skill = self.profile.skills.get("j", None)
            if j_skill:
                is_mp = (j_skill.cost_type == "MP")
                can_cast = (self.mana >= j_skill.cost_value) if is_mp else (self.stamina >= j_skill.cost_value)
                if can_cast:
                    if is_mp:
                        self.mana -= j_skill.cost_value
                    else:
                        self.stamina -= j_skill.cost_value
                        self.stamina_regen_delay = 0.5
                    self.is_attacking = True
                    self.attack_hit_enemies.clear()
                    self.attack_cooldown = 0.25
                    self._begin_attack_anim()
                    
                    # Ranged archetypes shoot basic projectile on [J]
                    if self.archetype in ("mage", "healer", "archer", "support", "ninja"):
                        from entities.projectile import Projectile
                        proj_x = self.rect.right + 8 if self.facing_right else self.rect.left - 28
                        proj_y = self.rect.centery - 8
                        ptype = j_skill.projectile_type or ("arrow_fast" if self.archetype == "archer" else "arcane_bolt")
                        self.projectiles.append(Projectile(proj_x, proj_y, self.facing_right, is_enemy=False, projectile_type=ptype, damage=j_skill.damage))
            
        # Skill [K] - Ranged Projectile / Technique
        if self.input.is_action_just_pressed("SKILL") or self.input.is_action_just_pressed("MAGIC"):
            if not self.is_attacking and not self.is_blocking and not self.is_casting_magic and not self.is_casting_ultimate and not self.is_drinking_potion:
                k_skill = self.profile.skills.get("k", None)
                if k_skill and self.mana >= k_skill.cost_value:
                    self.mana -= k_skill.cost_value
                    self.is_casting_magic = True
                    self.magic_cast_timer = 0.32
                    self.magic_sigil_timer = 0.38
                    self.anim_manager.play("cast_magic" if self.anim_manager.has_animation("cast_magic") else "attack", force_reset=True)
                    
                    # Wizard Solar Fusion stack increment on spell cast
                    if self.passive_id == "wizard_solar_fusion":
                        self.solar_fusion_stacks = min(5, self.solar_fusion_stacks + 1)
                        self.solar_fusion_timer = 4.0

                    # Healer [K] Bênção Restauradora: heals self and companion!
                    if self.passive_id == "aurelia_dawn_grace" or self.archetype == "healer":
                        self.health = min(self.max_health, self.health + 45)
                        if self.companion and not getattr(self.companion, "is_dead", False):
                            self.companion.health = min(self.companion.max_health, self.companion.health + 45)

                    # Mana Support [K] Transferência Etérea: grants mana to companion!
                    if self.passive_id == "zephyr_ether_stream" or self.archetype == "support":
                        if self.companion and not getattr(self.companion, "is_dead", False):
                            self.companion.mana = min(self.companion.max_mana, self.companion.mana + 35.0)

                    from entities.projectile import Projectile
                    proj_x = self.rect.right + 8 if self.facing_right else self.rect.left - 28
                    proj_y = self.rect.centery - 8
                    ptype = k_skill.projectile_type or "fireball"
                    is_burn = (self.passive_id == "ignis_smoldering_ashes")
                    damage = k_skill.damage
                    if self.passive_id == "wizard_solar_fusion":
                        damage = int(damage * (1.0 + self.solar_fusion_stacks * 0.06))
                    if ptype == "arrow_scatter":
                        for angle_offset in (-18, 0, 18):
                            p = Projectile(proj_x, proj_y + angle_offset * 0.4, self.facing_right, is_enemy=False, projectile_type="arrow_scatter", damage=damage)
                            p.velocity.y = angle_offset * 5.0
                            self.projectiles.append(p)
                    else:
                        self.projectiles.append(Projectile(proj_x, proj_y, self.facing_right, is_enemy=False, projectile_type=ptype, is_burn=is_burn, damage=damage))

    def dash(self) -> bool:
        """Executes a high-speed directional dash with invulnerability frames and ghost clones."""
        if self.is_dashing or self.dash_cooldown > 0 or self.is_dead or self.is_downed or self.is_drinking_potion:
            return False
        
        stamina_cost = 15.0
        if self.stamina < stamina_cost:
            return False
            
        self.stamina -= stamina_cost
        self.stamina_regen_delay = 0.5
        self.is_dashing = True
        self.dash_timer = self.dash_duration
        self.dash_cooldown = 0.35
        self.invulnerable = True
        self.invulnerability_timer = self.dash_duration + 0.06
        
        if getattr(self, "character_id", "") == "samurai" or getattr(self, "passive_id", "") == "samurai_perfect_focus":
            self.attack_cooldown = 0.0
            
        dir_mult = 1.0 if self.facing_right else -1.0
        self.velocity.x = self.dash_speed * dir_mult
        self.velocity.y = 0.0
        self.anim_manager.play("dash", force_reset=True)
        return True

    def attack(self) -> bool:
        """Triggers basic ground/ranged attack [J]."""
        if self.is_attacking or self.is_blocking or self.is_drinking_potion or self.attack_cooldown > 0:
            return False
        j_skill = self.profile.skills.get("j", None)
        if not j_skill:
            return False
        is_mp = (j_skill.cost_type == "MP")
        can_cast = (self.mana >= j_skill.cost_value) if is_mp else (self.stamina >= j_skill.cost_value)
        if not can_cast:
            return False
        if is_mp:
            self.mana -= j_skill.cost_value
        else:
            self.stamina -= j_skill.cost_value
            self.stamina_regen_delay = 0.5
        self.is_attacking = True
        self.attack_hit_enemies.clear()
        self.attack_cooldown = 0.25
        self._begin_attack_anim()
        if self.archetype in ("mage", "healer", "archer", "support", "ninja"):
            from entities.projectile import Projectile
            proj_x = self.rect.right + 8 if self.facing_right else self.rect.left - 28
            proj_y = self.rect.centery - 8
            ptype = j_skill.projectile_type or ("arrow_fast" if self.archetype == "archer" else "arcane_bolt")
            self.projectiles.append(Projectile(proj_x, proj_y, self.facing_right, is_enemy=False, projectile_type=ptype, damage=j_skill.damage))
        return True

    def cast_skill(self) -> bool:
        """Triggers primary technique / spell [K]."""
        if self.is_attacking or self.is_blocking or self.is_casting_magic or self.is_casting_ultimate or self.is_drinking_potion:
            return False
        k_skill = self.profile.skills.get("k", None)
        if not k_skill or self.mana < k_skill.cost_value:
            return False
        self.mana -= k_skill.cost_value
        self.is_casting_magic = True
        self.magic_cast_timer = 0.32
        self.magic_sigil_timer = 0.38
        self.anim_manager.play("cast_magic" if self.anim_manager.has_animation("cast_magic") else "attack", force_reset=True)
        if self.passive_id == "wizard_solar_fusion":
            self.solar_fusion_stacks = min(5, self.solar_fusion_stacks + 1)
            self.solar_fusion_timer = 4.0
        if self.passive_id == "aurelia_dawn_grace" or self.archetype == "healer":
            self.health = min(self.max_health, self.health + 45)
            if self.companion and not getattr(self.companion, "is_dead", False):
                self.companion.health = min(self.companion.max_health, self.companion.health + 45)
        if self.passive_id == "zephyr_ether_stream" or self.archetype == "support":
            if self.companion and not getattr(self.companion, "is_dead", False):
                self.companion.mana = min(self.companion.max_mana, self.companion.mana + 35.0)
        from entities.projectile import Projectile
        proj_x = self.rect.right + 8 if self.facing_right else self.rect.left - 28
        proj_y = self.rect.centery - 8
        ptype = k_skill.projectile_type or "fireball"
        is_burn = (self.passive_id == "ignis_smoldering_ashes")
        damage = k_skill.damage
        if self.passive_id == "wizard_solar_fusion":
            damage = int(damage * (1.0 + self.solar_fusion_stacks * 0.06))
        if ptype == "arrow_scatter":
            for angle_offset in (-18, 0, 18):
                p = Projectile(proj_x, proj_y + angle_offset * 0.4, self.facing_right, is_enemy=False, projectile_type="arrow_scatter", damage=damage)
                p.velocity.y = angle_offset * 5.0
                self.projectiles.append(p)
        else:
            self.projectiles.append(Projectile(proj_x, proj_y, self.facing_right, is_enemy=False, projectile_type=ptype, is_burn=is_burn, damage=damage))
        return True

    def cast_special(self) -> bool:
        return self.cast_skill()

    def cast_aoe(self) -> bool:
        """Triggers radial AoE skill [E]."""
        if self.is_casting_aoe or self.is_attacking or self.is_blocking or self.is_drinking_potion:
            return False
        e_skill = self.profile.skills.get("e", None)
        if not e_skill:
            return False
        can_cast = (self.mana >= e_skill.cost_value) if e_skill.cost_type == "MP" else (self.stamina >= e_skill.cost_value)
        if not can_cast:
            return False
        if e_skill.cost_type == "MP":
            self.mana -= e_skill.cost_value
        else:
            self.stamina -= e_skill.cost_value
            self.stamina_regen_delay = 0.5
        self.is_casting_aoe = True
        self.aoe_timer = 0.85
        self.aoe_hit_done = False
        self.anim_manager.play("whirlwind", force_reset=True)
        from entities.ultimate_aoe_vfx import UltimateAoE_VFX
        self.aoe_vfx = UltimateAoE_VFX(self.rect.centerx, self.rect.bottom, self.aoe_radius, self.profile.id)
        return True

    def cast_ultimate(self) -> bool:
        """Triggers Triple-AAA Ultimate skill [R / I]."""
        if self.is_attacking or self.is_blocking or self.is_dashing or self.is_casting_magic or self.is_casting_ultimate:
            return False
        r_skill = self.profile.skills.get("r", None)
        if not r_skill or self.mana < r_skill.cost_value:
            return False
        self.mana = 0.0
        self.is_casting_ultimate = True
        self.ultimate_controller.trigger(self.rect.centerx, self.rect.bottom, self.facing_right)
        self.velocity.x = 0
        self.velocity.y = 0
        return True
                
    def _apply_physics(self, dt: float, tiles: list[pygame.FRect]):
        if not self.is_dashing:
            # Apply Gravity — MUST be dt-scaled for frame-rate independence
            # Without * dt, gravity accumulates per-frame: at 9 FPS the player
            # barely decelerates and flies across the entire map.
            self.velocity.y += GRAVITY * dt
            self.velocity.y = min(self.velocity.y, MAX_FALL_SPEED)
            
        # Move X
        self.pos.x += self.velocity.x * dt
        self.rect.x = self.pos.x
        
        # Collide X
        solid_tiles = [t for t in tiles if getattr(t, 'is_oneway', False) is False]
        for tile in solid_tiles:
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
        
        # Collide Y
        self.on_ground = False
        for tile in tiles:
            if self.rect.colliderect(tile):
                is_oneway = getattr(tile, 'is_oneway', False)
                if is_oneway:
                    if self.velocity.y > 0 and self.rect.bottom - (self.velocity.y * dt) <= tile.top + 6:
                        self.rect.bottom = tile.top
                        self.pos.y = self.rect.y
                        self.velocity.y = 0
                        self.on_ground = True
                        if self.is_down_attacking:
                            self.is_down_attacking = False
                            self.is_landing_plunge = True
                            self.plunge_recovery = 0.35
                            self.plunge_impact_pending = True
                            self.anim_manager.play("landing", force_reset=True)
                            self.impact_smokes.append(ImpactSmoke(self.rect.left - 15, self.rect.bottom - 10))
                            self.impact_smokes.append(ImpactSmoke(self.rect.right + 15, self.rect.bottom - 10))
                        break
                    continue
                    
                if self.velocity.y > 0:
                    self.rect.bottom = tile.top
                    self.pos.y = self.rect.y
                    self.on_ground = True
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

        # Track true ground footprint for grounded contact shadow and Y-sort
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
                
    def take_damage(self, amount: int):
        if self.is_dashing or self.is_casting_ultimate:
            return
            
        # 1. Blocking: absorbs 100% damage while holding Shift
        if self.is_blocking:
            # Galahad (Knight) Passive: Paladin Retribution
            if self.passive_id == "knight_paladin_retribution" and self.parry_window_timer > 0:
                self.stamina = min(self.max_stamina, self.stamina + 15.0)
                self.invulnerable = True
                self.invulnerability_timer = 0.45
                from entities.projectile import Projectile
                p_left = Projectile(self.rect.centerx, self.rect.centery, False, is_enemy=False, projectile_type="spear_light", damage=max(25, int(amount * 0.6)))
                p_right = Projectile(self.rect.centerx, self.rect.centery, True, is_enemy=False, projectile_type="spear_light", damage=max(25, int(amount * 0.6)))
                self.projectiles.extend([p_left, p_right])
                return

            self.stamina_regen_delay = 0.5
            return # Block absorbs all damage without taking health or chunking extra resource!
            
        # 2. Astra Passive: Celestial Barrier (absorbs 100% of 1 attack, 20s cooldown)
        if self.celestial_barrier_active:
            self.celestial_barrier_active = False
            self.celestial_barrier_cooldown = 20.0
            self.invulnerable = True
            self.invulnerability_timer = 0.5
            return
            
        if not self.invulnerable:
            # 3. Fighter Passive: Physical Resilience (15% damage reduction if HP < 30%)
            if self.passive_id == "fighter_physical_resilience" and self.health < (self.max_health * 0.30):
                amount = max(1, int(amount * 0.85))
                
            self.health -= amount
            self.hurt_timer = 0.30
            self.invulnerable = True
            self.invulnerability_timer = 0.8
            if self.health <= 0:
                if self.companion and not getattr(self.companion, "is_dead", False) and not getattr(self.companion, "is_downed", False):
                    self.health = 1
                    self.is_downed = True
                    self.bleedout_timer = 25.0
                    self.revive_progress = 0.0
                    self.anim_manager.play("dead", force_reset=True)
                else:
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
            
        # Co-op Downed Indicator & Revive Progress Gauge
        if self.is_downed:
            dx = self.rect.centerx - camera_offset.x
            dy = self.rect.top - camera_offset.y - 14
            # Bleedout warning ring
            b_alpha = int(140 + 90 * math.sin(pygame.time.get_ticks() * 0.01))
            pygame.draw.circle(surface, (255, 60, 60, b_alpha), (int(dx), int(dy)), 14, 2)
            # Revive progress arc / circle
            if self.revive_progress > 0:
                prog = min(1.0, self.revive_progress / self.revive_duration)
                pygame.draw.circle(surface, (0, 255, 180), (int(dx), int(dy)), 10)
                pygame.draw.circle(surface, (255, 255, 255), (int(dx), int(dy)), 10, width=2)
            # Fallen sprite
            img = self.anim_manager.get_current_frame()
            r = img.get_rect(center=(int(self.rect.centerx - camera_offset.x), int(self.rect.bottom - camera_offset.y - 10)))
            surface.blit(img, r)
            return

        # 3. Draw Subtle Celestial Ring when 100 MP (Ultimate Ready) - Perimeter ring only, no filled center
        if self.mana >= 100 and not self.is_dead and not self.is_casting_ultimate:
            pulse_rad = int(30 + 2 * math.sin(pygame.time.get_ticks() * 0.005))
            aura_surf = pygame.Surface((pulse_rad * 2 + 4, pulse_rad * 2 + 4), pygame.SRCALPHA)
            col = getattr(self.profile, "color_theme", (255, 220, 90))
            pygame.draw.circle(aura_surf, (*col, 45), (pulse_rad + 2, pulse_rad + 2), pulse_rad, width=1)
            surface.blit(aura_surf, (self.rect.centerx - camera_offset.x - pulse_rad - 2, self.rect.centery - camera_offset.y - pulse_rad - 2))

        # 0. Contact Drop Shadow under feet (Grounded presence anchored to floor)
        shadow_ground_y = getattr(self, "ground_y", self.rect.bottom)
        air_height = max(0, shadow_ground_y - self.rect.bottom)
        scale = max(0.4, 1.0 - air_height / 250.0)
        shadow_w = int(46 * scale)
        shadow_h = int(12 * scale)
        alpha = int(120 * scale)
        if shadow_w > 2 and shadow_h > 2 and alpha > 0:
            shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_surf, (0, 0, 0, alpha), (0, 0, shadow_w, shadow_h))
            core_w, core_h = max(2, int(shadow_w * 0.62)), max(2, int(shadow_h * 0.62))
            pygame.draw.ellipse(shadow_surf, (0, 0, 0, min(255, int(alpha * 1.35))), ((shadow_w - core_w) // 2, (shadow_h - core_h) // 2, core_w, core_h))
            surface.blit(shadow_surf, (self.rect.centerx - camera_offset.x - shadow_w // 2, shadow_ground_y - camera_offset.y - shadow_h // 2 + 1))

        # 0.1 Astra Celestial Barrier (Soft ambient back-glow drawn BEHIND the character model)
        if self.celestial_barrier_active and not self.is_dead:
            bx = self.rect.centerx - camera_offset.x
            by = self.rect.centery - camera_offset.y
            bg_orb_r = 34
            bg_surf = pygame.Surface((bg_orb_r * 2 + 8, bg_orb_r * 2 + 8), pygame.SRCALPHA)
            # Very subtle soft cosmic backdrop that stays behind her sprite
            pygame.draw.circle(bg_surf, (120, 215, 255, 18), (bg_orb_r + 4, bg_orb_r + 4), bg_orb_r)
            surface.blit(bg_surf, (bx - bg_orb_r - 4, by - bg_orb_r - 4))

        # 4. Triple-AAA Character Ultimate Visual Sequence
        if self.is_casting_ultimate:
            self.ultimate_controller.draw_world(surface, camera_offset)

        img = self.anim_manager.get_current_frame()
        
        # Calculate rendering position
        img_rect = img.get_rect()
        _ax = self._anchor_x(self.anim_manager.current_state, img_rect.width)
        draw_x = self.rect.centerx - camera_offset.x - (_ax if self.facing_right else img_rect.width - _ax)
        ground_off = getattr(self.profile, "ground_offset_y", 7)
        draw_y = self.rect.bottom - camera_offset.y - img_rect.height + ground_off
        
        if not self.facing_right:
            img = pygame.transform.flip(img, True, False)
            
        # Blink when invulnerable (unless dashing/ultimate)
        if self.is_dashing or self.is_casting_ultimate or not self.invulnerable or int(self.invulnerability_timer * 10) % 2 == 0:
            surface.blit(img, (draw_x, draw_y))
            
            # Draw magical barrier or shield effect when blocking
            if self.is_blocking:
                bx = self.rect.centerx - camera_offset.x
                by = self.rect.centery - camera_offset.y
                col = self.profile.color_theme
                
                if self.archetype in ("mage", "healer", "support"):
                    rad = 38
                    bar_surf = pygame.Surface((rad * 2 + 10, rad * 2 + 10), pygame.SRCALPHA)
                    bc = rad + 5
                    pygame.draw.circle(bar_surf, (*col, 50), (bc, bc), rad)
                    pygame.draw.circle(bar_surf, (*col, 160), (bc, bc), rad, 2)
                    pygame.draw.circle(bar_surf, (255, 255, 255, 90), (bc, bc), max(1, rad - 3), 1)
                    t_rot = pygame.time.get_ticks() * 0.005
                    for i in range(6):
                        ang = t_rot + i * (math.pi / 3)
                        px = bc + int(math.cos(ang) * (rad - 4))
                        py = bc + int(math.sin(ang) * (rad - 4))
                        pygame.draw.circle(bar_surf, (255, 255, 255, 160), (px, py), 2)
                    surface.blit(bar_surf, (bx - bc, by - bc))
                elif self.archetype == "shinobi":
                    # Shadow Veil / Replacement technique smoke mist
                    rad = 30
                    v_surf = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
                    pygame.draw.circle(v_surf, (80, 20, 120, 50), (rad, rad), rad)
                    pygame.draw.circle(v_surf, (190, 80, 255, 140), (rad, rad), rad - 2, 2)
                    surface.blit(v_surf, (bx - rad, by - rad))
                elif self.archetype in ("samurai", "archer"):
                    # Parry stance / evasive stance with clean blade glint
                    rad = 28
                    p_surf = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
                    pygame.draw.circle(p_surf, (255, 255, 255, 40), (rad, rad), rad)
                    pygame.draw.circle(p_surf, (*col, 150), (rad, rad), rad, 2)
                    # Deflection blade glint
                    ox = 16 if self.facing_right else -16
                    pygame.draw.line(p_surf, (255, 255, 255, 180), (rad + ox - 4, rad - 12), (rad + ox + 4, rad + 12), 2)
                    surface.blit(p_surf, (bx - rad, by - rad))
                elif self.archetype in ("fighter", "guardian"):
                    # Iron Body Ki barrier aura
                    rad = 38
                    k_surf = pygame.Surface((rad * 2 + 10, rad * 2 + 10), pygame.SRCALPHA)
                    kc = rad + 5
                    pulse = int(2 * math.sin(pygame.time.get_ticks() * 0.008))
                    cur_r = rad + pulse
                    pygame.draw.circle(k_surf, (*col, 55), (kc, kc), cur_r)
                    pygame.draw.circle(k_surf, (255, 215, 80, 150), (kc, kc), cur_r, 2)
                    surface.blit(k_surf, (bx - kc, by - kc))
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

        # 5. Mage Levitation Glow on Jump & Fall
        if not self.on_ground and self.archetype == "mage":
            m_cx = self.rect.centerx - camera_offset.x
            m_fy = self.rect.bottom - camera_offset.y + 2
            m_col = self.profile.color_theme
            disc_w, disc_h = 32, 8
            disc_surf = pygame.Surface((disc_w + 4, disc_h + 4), pygame.SRCALPHA)
            pygame.draw.ellipse(disc_surf, (*m_col, 110), (2, 2, disc_w, disc_h), 2)
            pygame.draw.ellipse(disc_surf, (255, 255, 255, 160), (4, 3, disc_w - 4, disc_h - 2), 1)
            surface.blit(disc_surf, (m_cx - (disc_w + 4) // 2, m_fy - (disc_h + 4) // 2), special_flags=pygame.BLEND_RGBA_ADD)

        # 6. Basic Attack Slash Arc VFX
        if self.is_attacking:
            self._draw_attack_vfx(surface, camera_offset)

        # 7. Magic Conjuration Sigil / Hand Flash (subtle, focused at hand)
        if self.magic_sigil_timer > 0:
            sig_t = self.magic_sigil_timer / 0.38
            flash_alpha = int(140 * sig_t)
            flash_rad = max(4, int(7 + 4 * (1.0 - sig_t)))
            hand_x = self.rect.right + 4 if self.facing_right else self.rect.left - 4
            hx = hand_x - camera_offset.x
            hy = self.rect.centery - camera_offset.y + 2
            sig_surf = pygame.Surface((flash_rad * 2 + 6, flash_rad * 2 + 6), pygame.SRCALPHA)
            sc = flash_rad + 3
            sig_col = getattr(self.profile, "color_theme", (255, 140, 40))
            pygame.draw.circle(sig_surf, (*sig_col, int(flash_alpha * 0.5)), (sc, sc), flash_rad)
            pygame.draw.circle(sig_surf, (255, 255, 255, flash_alpha), (sc, sc), max(2, flash_rad // 3))
            # Subtle small cross star spark at fingertip
            spark_len = flash_rad + 2
            pygame.draw.line(sig_surf, (255, 255, 255, flash_alpha), (sc - spark_len, sc), (sc + spark_len, sc), 1)
            pygame.draw.line(sig_surf, (255, 255, 255, flash_alpha), (sc, sc - spark_len), (sc, sc + spark_len), 1)
            surface.blit(sig_surf, (hx - sc, hy - sc), special_flags=pygame.BLEND_RGBA_ADD)

        # 8. Bespoke AoE Skill [E] Visual Effects
        if self.is_casting_aoe and self.aoe_timer > 0:
            self._draw_aoe_effect(surface, camera_offset)
            
        # 9. Astra Celestial Barrier Foreground Perimeter Ring & Orbiting Star Motes
        # Hollow ring framing the character cleanly without covering or blinding her sprite
        if self.celestial_barrier_active and not self.is_dead:
            bx = self.rect.centerx - camera_offset.x
            by = self.rect.centery - camera_offset.y
            t = pygame.time.get_ticks() * 0.003
            orb_r = 38
            pulse = int(2.0 * math.sin(t * 2))
            cur_r = orb_r + pulse
            orb_surf = pygame.Surface((cur_r * 2 + 16, cur_r * 2 + 16), pygame.SRCALPHA)
            oc = cur_r + 8
            # Crisp perimeter ring (NO solid/additive fill over player body)
            pygame.draw.circle(orb_surf, (140, 225, 255, 180), (oc, oc), cur_r, 2)
            pygame.draw.circle(orb_surf, (255, 255, 255, 230), (oc, oc), cur_r - 2, 1)
            # Orbiting astral star motes along the outer rim
            for i in range(4):
                ang = t + i * (math.pi / 2)
                px = oc + int(math.cos(ang) * cur_r)
                py = oc + int(math.sin(ang) * cur_r)
                pygame.draw.circle(orb_surf, (255, 255, 255, 255), (px, py), 4)
                pygame.draw.circle(orb_surf, (140, 240, 255, 200), (px, py), 7, 1)
            surface.blit(orb_surf, (bx - oc, by - oc), special_flags=pygame.BLEND_RGBA_ADD)
            
        # 10. Potion Drinking Visual Cue
        if self.is_drinking_potion and not self.is_dead:
            px = self.rect.centerx - camera_offset.x
            py = self.rect.top - camera_offset.y - 14
            t_pct = max(0.0, min(1.0, 1.0 - (self.potion_timer / self.potion_duration)))
            # Mini heal progress bar
            bar_w = 26
            bar_h = 4
            pygame.draw.rect(surface, (20, 20, 20), (px - bar_w // 2, py, bar_w, bar_h), border_radius=2)
            pygame.draw.rect(surface, (80, 240, 120), (px - bar_w // 2, py, int(bar_w * t_pct), bar_h), border_radius=2)
            pygame.draw.rect(surface, (200, 255, 220), (px - bar_w // 2, py, bar_w, bar_h), 1, border_radius=2)

    def _draw_attack_vfx(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        """Renders crisp directional weapon slash or magic muzzle flare."""
        cx = self.rect.centerx - camera_offset.x
        cy = self.rect.centery - camera_offset.y - 4
        direction = 1 if self.facing_right else -1
        col = getattr(self.profile, "color_theme", (255, 255, 255))
        
        slash_w, slash_h = 80, 70
        slash_surf = pygame.Surface((slash_w, slash_h), pygame.SRCALPHA)
        scx = slash_w // 2
        scy = slash_h // 2
        
        if self.archetype == "mage":
            # Vivid sparkling elemental hand flare
            flare_rad = 28
            fx, fy = scx + direction * 14, scy
            pygame.draw.circle(slash_surf, (*col, 160), (fx, fy), flare_rad)
            pygame.draw.circle(slash_surf, (*col, 220), (fx, fy), int(flare_rad * 0.65))
            pygame.draw.circle(slash_surf, (255, 255, 255, 255), (fx, fy), int(flare_rad * 0.35))
            for ang in (0, math.pi / 2, math.pi, 3 * math.pi / 2):
                rx = fx + int(math.cos(ang) * (flare_rad + 8))
                ry = fy + int(math.sin(ang) * (flare_rad + 8))
                pygame.draw.line(slash_surf, (255, 255, 255, 230), (fx, fy), (rx, ry), 2)
        elif self.archetype == "shinobi":
            # Violet shadow slash crescent
            points = [(scx, scy - 18), (scx + direction * 22, scy), (scx, scy + 18), (scx + direction * 12, scy)]
            pygame.draw.polygon(slash_surf, (200, 100, 255, 200), points)
            pygame.draw.polygon(slash_surf, (255, 255, 255, 230), points, 1)
        elif self.archetype == "samurai":
            # Razor sharp katana slash crescent
            points = [(scx - direction * 6, scy - 20), (scx + direction * 24, scy - 4), (scx - direction * 6, scy + 16), (scx + direction * 12, scy - 2)]
            pygame.draw.polygon(slash_surf, (255, 80, 80, 210), points)
            pygame.draw.polygon(slash_surf, (255, 255, 255, 240), points, 1)
        elif self.archetype == "fighter":
            # Golden Ki punch shockwave
            fx = scx + direction * 14
            pygame.draw.circle(slash_surf, (255, 170, 40, 150), (fx, scy), 30)
            pygame.draw.circle(slash_surf, (255, 215, 60, 230), (fx, scy), 20, 4)
            pygame.draw.circle(slash_surf, (255, 255, 255, 255), (fx, scy), 10)
        else:
            # Warrior steel slash
            points = [(scx - direction * 8, scy - 22), (scx + direction * 22, scy), (scx - direction * 8, scy + 20), (scx + direction * 8, scy)]
            pygame.draw.polygon(slash_surf, (255, 220, 80, 190), points)
            pygame.draw.polygon(slash_surf, (255, 255, 255, 230), points, 1)
            
        surface.blit(slash_surf, (cx + direction * 18 - scx, cy - scy), special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_aoe_effect(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        """Renders bespoke, spectacular AoE visual effects for all 7 heroes via the polymorphic UltimateAoE_VFX engine."""
        if self.aoe_vfx is None or not self.aoe_vfx.active:
            from entities.ultimate_aoe_vfx import UltimateAoE_VFX
            self.aoe_vfx = UltimateAoE_VFX(self.rect.centerx, self.rect.bottom, self.aoe_radius, self.profile.id)
            if self.aoe_timer > 0:
                self.aoe_vfx.time = max(0.0, self.aoe_vfx.duration - self.aoe_timer)
        
        self.aoe_vfx.draw(surface, camera_offset)


