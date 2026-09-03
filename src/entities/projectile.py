import pygame
import os
import math
from engine.animation import Animation, AnimationManager, load_spritesheet, load_animation_folder

# Static animation frame caches (loaded once for 60 FPS zero-lag performance)
_FIREBALL_CACHES = {}
_PURPLE_SPHERE_FLY_FRAMES = None
_PURPLE_SPHERE_HIT_FRAMES = None

def get_fireball_anims(color: str = "red") -> tuple[Animation, Animation]:
    """Returns new Animation instances referencing pre-cached fireball frames for the given color."""
    global _FIREBALL_CACHES
    if color not in _FIREBALL_CACHES:
        if color == "blue":
            sheet_filename = "fireball_blue.png"
            tint = None
        elif color == "purple":
            sheet_filename = "fireball_blue.png"
            tint = (210, 80, 255)
        elif color == "green":
            sheet_filename = "fireball_blue.png"
            tint = (60, 255, 120)
        else: # "red" / default player fireball
            sheet_filename = "fireball.png"
            tint = None

        fb_path = os.path.join("assets", "sprites", "spell_animations", sheet_filename)
        sheet = pygame.image.load(fb_path).convert_alpha()
        fw, fh = 512, 384
        cols = 4
        scale = 0.25
        
        # Flying flame loop (frames 12 to 24)
        fly_frames = []
        for idx in range(12, 25):
            r = idx // cols
            c = idx % cols
            sub = sheet.subsurface((c * fw + 40, r * fh + 110, 320, 150))
            scaled = pygame.transform.smoothscale(sub, (int(320 * scale), int(150 * scale)))
            if tint:
                scaled = scaled.copy()
                scaled.fill(tint, special_flags=pygame.BLEND_RGBA_MULT)
            fly_frames.append(scaled)
            
        # Explosion on hit (frames 28 to 38)
        hit_frames = []
        for idx in range(28, 39):
            r = idx // cols
            c = idx % cols
            sub = sheet.subsurface((c * fw, r * fh, fw, fh))
            scaled = pygame.transform.smoothscale(sub, (int(fw * scale * 0.75), int(fh * scale * 0.75)))
            if tint:
                scaled = scaled.copy()
                scaled.fill(tint, special_flags=pygame.BLEND_RGBA_MULT)
            hit_frames.append(scaled)
            
        _FIREBALL_CACHES[color] = (fly_frames, hit_frames)
        
    fly_f, hit_f = _FIREBALL_CACHES[color]
    return Animation(fly_f, fps=24, loop=True), Animation(hit_f, fps=24, loop=False)

def get_purple_sphere_anims() -> tuple[Animation, Animation]:
    global _PURPLE_SPHERE_FLY_FRAMES, _PURPLE_SPHERE_HIT_FRAMES
    if _PURPLE_SPHERE_FLY_FRAMES is None or _PURPLE_SPHERE_HIT_FRAMES is None:
        purple_path = os.path.join("assets", "sprites", "spell_animations", "sphere_purple.png")
        base_anim = load_spritesheet(purple_path, 128, 128, fps=24, loop=True, scale=0.35, start_frame=8, max_frames=16)
        _PURPLE_SPHERE_FLY_FRAMES = base_anim.frames
        
        hit_path = os.path.join("assets", "sprites", "vfx", "vfx_hit")
        base_hit = load_animation_folder(hit_path, "vfx_hit", fps=24, loop=False, scale=1.3)
        _PURPLE_SPHERE_HIT_FRAMES = base_hit.frames
        
    fly_anim = Animation(_PURPLE_SPHERE_FLY_FRAMES, fps=24, loop=True)
    hit_anim = Animation(_PURPLE_SPHERE_HIT_FRAMES, fps=24, loop=False)
    return fly_anim, hit_anim

_SPHERE_CACHES = {}
_SHURIKEN_FRAMES = None
_WIND_SLASH_FRAMES = None

def get_sphere_projectile_anims(color: str = "blue", scale: float = 0.30) -> tuple[Animation, Animation]:
    global _SPHERE_CACHES
    cache_key = f"{color}_{scale}"
    if cache_key not in _SPHERE_CACHES:
        sheet_name = f"sphere_{color}.png" if color in ("blue", "yellow", "purple") else "sphere_blue.png"
        path = os.path.join("assets", "sprites", "spells", sheet_name)
        if not os.path.exists(path):
            path = os.path.join("assets", "sprites", "spell_animations", sheet_name)
            
        fly_anim = load_spritesheet(path, 128, 128, fps=24, loop=True, scale=scale, start_frame=4, max_frames=20)
        hit_path = os.path.join("assets", "sprites", "vfx", "vfx_hit")
        hit_anim = load_animation_folder(hit_path, "vfx_hit", fps=24, loop=False, scale=1.3)
        _SPHERE_CACHES[cache_key] = (fly_anim.frames, hit_anim.frames)
    
    fly_f, hit_f = _SPHERE_CACHES[cache_key]
    return Animation(fly_f, fps=24, loop=True), Animation(hit_f, fps=24, loop=False)

def get_shuriken_anims() -> tuple[Animation, Animation]:
    global _SHURIKEN_FRAMES
    if _SHURIKEN_FRAMES is None:
        frames = []
        for rot in [0, 45, 90, 135]:
            surf = pygame.Surface((28, 28), pygame.SRCALPHA)
            cx, cy = 14, 14
            pts = [(cx, 2), (cx + 4, cy - 4), (cx + 12, cy), (cx + 4, cy + 4), 
                   (cx, cy + 12), (cx - 4, cy + 4), (cx - 12, cy), (cx - 4, cy - 4)]
            pygame.draw.polygon(surf, (225, 230, 245), pts)
            pygame.draw.polygon(surf, (150, 160, 180), pts, 1)
            pygame.draw.circle(surf, (50, 50, 70), (cx, cy), 3)
            if rot > 0:
                surf = pygame.transform.rotate(surf, rot)
            frames.append(surf)
        _SHURIKEN_FRAMES = frames
        
    hit_path = os.path.join("assets", "sprites", "vfx", "vfx_hit")
    hit_anim = load_animation_folder(hit_path, "vfx_hit", fps=24, loop=False, scale=1.0)
    return Animation(_SHURIKEN_FRAMES, fps=30, loop=True), hit_anim

def get_vacuum_slash_anims() -> tuple[Animation, Animation]:
    global _WIND_SLASH_FRAMES
    if _WIND_SLASH_FRAMES is None:
        frames = []
        for i in range(4):
            surf = pygame.Surface((34, 44), pygame.SRCALPHA)
            alpha_wave = 210 + i * 10
            pygame.draw.arc(surf, (240, 255, 255, alpha_wave), (4, 2, 26, 40), -1.2, 1.2, 4)
            pygame.draw.arc(surf, (140, 220, 255, 160), (2, 0, 30, 44), -1.2, 1.2, 2)
            frames.append(surf)
        _WIND_SLASH_FRAMES = frames
        
    hit_path = os.path.join("assets", "sprites", "vfx", "vfx_hit")
    hit_anim = load_animation_folder(hit_path, "vfx_hit", fps=24, loop=False, scale=1.2)
    return Animation(_WIND_SLASH_FRAMES, fps=20, loop=True), hit_anim

class Projectile:
    def __init__(
        self,
        x: float,
        y: float,
        facing_right: bool,
        is_enemy: bool = False,
        projectile_type: str = None,
        color: str = None
    ):
        self.rect = pygame.FRect(x, y, 28, 28)
        self.active = True
        self.is_enemy = is_enemy
        self.facing_right = facing_right
        self.state = "fly" # "fly" or "hit"
        
        speed = 500
        # Enhanced spell damage and velocity balancing
        if is_enemy:
            if projectile_type in ("boss_fireball", "fireball_blue"):
                self.damage = 2
            else:
                self.damage = 1
        else:
            DAMAGE_MAP = {
                "arcane_bolt": 3,
                "arcane_sphere": 7,
                "fire_spark": 3,
                "fire_sphere": 8,
                "frost_lance": 3,
                "frost_orb": 7,
                "shuriken": 5,
                "vacuum_slash": 6,
                "ki_blast": 6,
                "fireball": 6
            }
            SPEED_MAP = {
                "arcane_bolt": 580,
                "arcane_sphere": 450,
                "fire_spark": 560,
                "fire_sphere": 460,
                "frost_lance": 600,
                "frost_orb": 440,
                "shuriken": 660,
                "vacuum_slash": 540,
                "ki_blast": 480,
                "fireball": 500
            }
            self.damage = DAMAGE_MAP.get(projectile_type, 6)
            speed = SPEED_MAP.get(projectile_type, 500)
            
        self.velocity = pygame.math.Vector2(speed if facing_right else -speed, 0)
        self.anim_manager = AnimationManager()
        
        if projectile_type is None:
            if is_enemy:
                projectile_type = "purple_sphere"
            else:
                projectile_type = "fireball"
                
        self.projectile_type = projectile_type
        chosen_color = None
        if projectile_type in ("boss_fireball", "fireball_blue"):
            chosen_color = color if color else "blue"
            fly_anim, hit_anim = get_fireball_anims(color=chosen_color)
        elif projectile_type in ("mage_fireball", "fireball_purple"):
            chosen_color = color if color else "purple"
            fly_anim, hit_anim = get_fireball_anims(color=chosen_color)
        elif projectile_type == "fireball":
            chosen_color = color if color else "red"
            fly_anim, hit_anim = get_fireball_anims(color=chosen_color)
        elif projectile_type in ("arcane_bolt", "arcane_sphere"):
            chosen_color = "blue"
            fly_anim, hit_anim = get_sphere_projectile_anims(color="blue", scale=0.25 if projectile_type == "arcane_bolt" else 0.38)
        elif projectile_type in ("fire_spark", "fire_sphere", "ki_blast"):
            chosen_color = "yellow"
            fly_anim, hit_anim = get_sphere_projectile_anims(color="yellow", scale=0.24 if projectile_type == "fire_spark" else 0.36)
        elif projectile_type in ("frost_lance", "frost_orb"):
            chosen_color = "blue"
            fly_anim, hit_anim = get_sphere_projectile_anims(color="blue", scale=0.26 if projectile_type == "frost_lance" else 0.38)
        elif projectile_type == "shuriken":
            chosen_color = "purple"
            fly_anim, hit_anim = get_shuriken_anims()
        elif projectile_type == "vacuum_slash":
            chosen_color = "blue"
            fly_anim, hit_anim = get_vacuum_slash_anims()
        else:
            # Default enemy purple sphere
            fly_anim, hit_anim = get_purple_sphere_anims()
            
        self.anim_manager.add_animation("fly", fly_anim)
        self.anim_manager.add_animation("hit", hit_anim)
        
        self.color = chosen_color
        self.anim_manager.play("fly")
        
    def explode(self):
        """Triggers hit explosion state."""
        if self.state != "hit":
            self.state = "hit"
            self.velocity.x = 0
            self.velocity.y = 0
            self.anim_manager.play("hit", force_reset=True)
        
    def update(self, dt: float, tiles: list[pygame.FRect]):
        if not self.active:
            return
            
        self.anim_manager.update(dt)
        
        if self.state == "hit":
            if self.anim_manager.is_finished("hit"):
                self.active = False
            return
            
        self.rect.x += self.velocity.x * dt
        self.rect.y += self.velocity.y * dt
        
        # Check collision with tiles (walls/floor)
        for tile in tiles:
            if self.rect.colliderect(tile):
                self.explode()
                break
                
    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if not self.active:
            return
            
        img = self.anim_manager.get_current_frame()
        if self.state == "fly":
            if not self.facing_right:
                img = pygame.transform.flip(img, True, False)
            if self.velocity.y != 0:
                vx = self.velocity.x if self.facing_right else -self.velocity.x
                angle = -math.degrees(math.atan2(self.velocity.y, abs(vx)))
                img = pygame.transform.rotate(img, angle)
            
        img_rect = img.get_rect()
        draw_x = self.rect.centerx - camera_offset.x - img_rect.width / 2
        draw_y = self.rect.centery - camera_offset.y - img_rect.height / 2
        surface.blit(img, (draw_x, draw_y))
