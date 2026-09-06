import pygame
import os
from engine.scene_manager import Scene
from entities.player import Player
from engine.camera import Camera
from config.settings import SETTINGS
from config.colors import UI_BACKGROUND
from ui.hud import HUD
from ui.pause import PauseMenu
from engine.input_manager import INPUT
from entities.collectible import Collectible
from entities.traps import SpikeTrap
from entities.prop import Prop
from entities.enemy import Skeleton, MageSkeleton, WildBoar
from world.checkpoint import Checkpoint
from entities.portal import Portal
from scenes.loading_scene import LoadingScene
from scenes.boss_scene import BossScene
from engine.lighting import LightingEngine, LightSource

STAGE_CONFIGS = {
    1: {
        "title": "CENÁRIO 1: AS CATACUMBAS",
        "theme": "dungeon",
        "map_width": 3072,
        "portal_x": 2880,
        "enemies": [
            ("skeleton", 450, 200),
            ("mage", 850, 200),
            ("skeleton", 1250, 200),
            ("skeleton", 1650, 200),
            ("mage", 2050, 200),
            ("skeleton", 2450, 200),
        ],
        "collectibles": [
            (500, 340, "potion"),
            (1100, 340, "orb"),
            (1750, 340, "chicken"),
            (2400, 340, "orb")
        ],
        "props": [
            (250, 350, "barrel", 0.65),
            (600, 350, "rock", 0.9),
            (1400, 350, "barrel", 0.65),
            (1800, 350, "rock", 0.9),
            (2200, 350, "barrel", 0.65)
        ],
        "traps": [
            (1000, 345),
            (1750, 345)
        ],
        "next_stage": 2,
        "next_title": "CENÁRIO 2: A FLORESTA ANCESTRAL",
        "tip": "Dica: Você está prestes a sair da masmorra para a Floresta Alta!"
    },
    2: {
        "title": "CENÁRIO 2: A FLORESTA ANCESTRAL",
        "theme": "forest",
        "map_width": 3600,
        "portal_x": 3420,
        "enemies": [
            ("boar", 400, 200),
            ("boar", 850, 200),
            ("skeleton", 1300, 200),
            ("boar", 1750, 200),
            ("mage", 2200, 200),
            ("boar", 2650, 200),
            ("skeleton", 3050, 200),
        ],
        "collectibles": [
            (550, 340, "potion"),
            (1300, 340, "orb"),
            (2100, 340, "chicken"),
            (2900, 340, "orb")
        ],
        "props": [
            (500, 350, "rock", 0.9),
            (950, 330, "chest", 0.65),
            (1400, 350, "rock", 0.9),
            (2050, 330, "chest", 0.65),
            (2550, 350, "rock", 0.9)
        ],
        "traps": [
            (750, 345),
            (1650, 345),
            (2300, 345)
        ],
        "next_stage": 3,
        "next_title": "CENÁRIO 3: A CRIPTA DOS MAGOS",
        "tip": "Dica: Pressione [Q] para realizar um DASH que atravessa inimigos e investidas de javalis!"
    },
    3: {
        "title": "CENÁRIO 3: A CRIPTA DOS MAGOS",
        "theme": "dungeon",
        "map_width": 4096,
        "portal_x": 3900,
        "enemies": [
            ("skeleton", 400, 200),
            ("mage", 800, 200),
            ("skeleton", 1250, 200),
            ("mage", 1700, 200),
            ("skeleton", 2150, 200),
            ("mage", 2600, 200),
            ("skeleton", 3050, 200),
            ("mage", 3500, 200),
        ],
        "collectibles": [
            (600, 340, "orb"),
            (1300, 340, "potion"),
            (2000, 340, "orb"),
            (2700, 340, "chicken"),
            (3400, 340, "orb")
        ],
        "props": [
            (200, 350, "barrel", 0.65),
            (900, 350, "rock", 0.9),
            (1450, 350, "barricade", 0.65),
            (2100, 350, "barrel", 0.65),
            (2700, 350, "rock", 0.9),
            (3300, 350, "barricade", 0.65)
        ],
        "traps": [
            (600, 345),
            (1350, 345),
            (2250, 345),
            (3150, 345)
        ],
        "next_stage": 4,
        "next_title": "CENÁRIO 4: A FLORESTA PROIBIDA",
        "tip": "Dica: Use [E] para a Tempestade de Lâminas e [R] com 100 MP para o seu ULTIMATE devastador!"
    },
    4: {
        "title": "CENÁRIO 4: A FLORESTA PROIBIDA",
        "theme": "forest",
        "map_width": 4000,
        "portal_x": 3800,
        "enemies": [
            ("boar", 380, 200),
            ("mage", 800, 200),
            ("boar", 1250, 200),
            ("skeleton", 1700, 200),
            ("boar", 2150, 200),
            ("mage", 2600, 200),
            ("skeleton", 3050, 200),
            ("boar", 3500, 200),
        ],
        "collectibles": [
            (600, 340, "potion"),
            (1400, 340, "orb"),
            (2200, 340, "chicken"),
            (3000, 340, "orb")
        ],
        "props": [
            (200, 350, "rock", 0.9),
            (900, 330, "chest", 0.65),
            (1600, 350, "rock", 0.9),
            (2300, 330, "chest", 0.65),
            (3000, 350, "rock", 0.9)
        ],
        "traps": [
            (550, 345),
            (1400, 345),
            (2200, 345),
            (3200, 345)
        ],
        "next_stage": 5, # Boss
        "next_title": "CENÁRIO 5: A SALA DO TRONO (CHEFE)",
        "tip": "Cuidado! O Rei Esqueleto aguarda no salão principal do trono com golpes devastadores!"
    }
}

class LevelScene(Scene):
    def __init__(self, stage: int = 1, scene_manager = None):
        self.scene_manager = scene_manager
        self.stage = stage
        
        cfg = STAGE_CONFIGS.get(stage, STAGE_CONFIGS[1])
        self.cfg = cfg
        self.theme = cfg.get("theme", "dungeon")
        self.map_width = cfg["map_width"]
        self.portal_x = cfg["portal_x"]
        
        # Load Theme Background Assets
        if self.theme == "forest":
            # 1. Sky Gradient Layer
            sky_path = os.path.join("Legacy-Fantasy - High Forest 2.3", "Background", "Background.png")
            raw_sky = pygame.image.load(sky_path).convert()
            self.forest_sky_w = int(raw_sky.get_width() * 384 / raw_sky.get_height())
            self.forest_sky = pygame.transform.scale(raw_sky, (self.forest_sky_w, 384))
            
            # 2. Forest Canopy & Mountain Layer
            canopy_path = os.path.join("Legacy-Fantasy - High Forest 2.3", "Trees", "Background.png")
            raw_canopy = pygame.image.load(canopy_path).convert_alpha()
            self.forest_canopy_w = int(raw_canopy.get_width() * 384 / raw_canopy.get_height())
            self.forest_canopy = pygame.transform.scale(raw_canopy, (self.forest_canopy_w, 384))
            
            # 3. Grass ground tile (top blades start at y=10 within the tile, so drawing at y=330 matches solid floor y=340)
            tiles_path = os.path.join("Legacy-Fantasy - High Forest 2.3", "Assets", "Tiles.png")
            tiles_img = pygame.image.load(tiles_path).convert_alpha()
            self.grass_tile = tiles_img.subsurface((16, 0, 48, 48))
        else:
            # Dungeon Theme
            dungeon_bg_path = os.path.join("assets", "sprites", "background", "sprites_dungeon")
            self.bg_left = pygame.image.load(os.path.join(dungeon_bg_path, "01_dungeon_left.png")).convert()
            self.bg_center = pygame.image.load(os.path.join(dungeon_bg_path, "02_dungeon_center.png")).convert()
            self.bg_right = pygame.image.load(os.path.join(dungeon_bg_path, "03_dungeon_right.png")).convert()
            
            right_over_path = os.path.join(dungeon_bg_path, "13_dungeon_right_over01.png")
            self.right_overlay = pygame.image.load(right_over_path).convert_alpha() if os.path.exists(right_over_path) else None
        
        self.camera = Camera(self.portal_x + 100, 384)
        spawn_x = 180 if self.theme == "dungeon" else 120
        self.player = Player(spawn_x, 200)
        self.hud = HUD(self.player, stage_title=cfg["title"])
        self.paused = False
        self.pause_menu = PauseMenu(self.scene_manager, self.unpause)
        self.death_timer = 0.0
        from ui.death_screen import DeathScreen
        self.death_screen = DeathScreen()
        self.lighting = LightingEngine(theme=self.theme)
        
        # Instantiate Enemies from Config
        self.enemies = []
        for e_type, ex, ey in cfg["enemies"]:
            if e_type == "mage":
                self.enemies.append(MageSkeleton(ex, ey))
            elif e_type == "boar":
                self.enemies.append(WildBoar(ex, ey))
            else:
                self.enemies.append(Skeleton(ex, ey))
                
        # Instantiate Collectibles
        self.collectibles = []
        for cx, cy, c_item in cfg["collectibles"]:
            self.collectibles.append(Collectible(cx, cy, c_item))
            
        # Instantiate Props
        self.props = []
        for px, py, p_type, p_scale in cfg["props"]:
            self.props.append(Prop(px, py, p_type, p_scale))
            
        # Instantiate Traps
        self.traps = []
        for tx, ty in cfg["traps"]:
            self.traps.append(SpikeTrap(tx, ty))
            
        self.projectiles = []
        
        # Portal to next scene
        self.portal = Portal(self.portal_x, 300)
        self.checkpoint = Checkpoint(self.portal_x // 2, 250)
        
    def unpause(self):
        self.paused = False
        
    def handle_events(self, events: list[pygame.event.Event]) -> None:
        pass
        
    def update(self, dt: float) -> None:
        if INPUT.is_action_just_pressed("PAUSE"):
            self.paused = not self.paused
            
        if self.paused:
            self.pause_menu.update()
            return
            
        self.lighting.update(dt)
        
        # Solid boundaries: Left wall stops player properly, right wall stops player right at portal
        left_bound = 215 if self.theme == "dungeon" else 120
        solid_rects = [
            pygame.FRect(0, 340, self.portal_x + 200, 50),     # Solid ground
            pygame.FRect(-100, 0, left_bound, 400),             # Left boundary wall
            pygame.FRect(self.portal_x + 10, 0, 200, 400)       # Right boundary wall at portal
        ]
        
        # Add solid obstacle hitboxes for active props
        for p in self.props:
            if p.active and p.prop_type in ["barrel", "rock"]:
                hitbox = pygame.FRect(p.rect.x + 8, p.rect.y + 15, p.rect.width - 16, p.rect.height - 15)
                solid_rects.append(hitbox)
        
        self.player.update(dt, solid_rects, self.enemies, self.camera)
        self.player.trigger_aoe_damage(self.enemies, self.camera)
        
        # Gameplay updates for props & item drops
        for p in self.props[:]:
            p.update(dt, self.player, self.spawn_item)
            if not p.active:
                if hasattr(p, "dropped_item") and p.dropped_item:
                    from entities.collectible import Collectible
                    self.collectibles.append(Collectible(p.dropped_item[0], p.dropped_item[1], "potion", is_dropped=True))
                    p.dropped_item = None
                self.props.remove(p)
            
        player_atk_rect = self.player.get_attack_hitbox()

        # Player melee hitting destructible props (2 hits to break)
        if player_atk_rect:
            for p in self.props:
                if p.active and player_atk_rect.colliderect(p.rect) and p not in self.player.attack_hit_enemies:
                    self.player.attack_hit_enemies.add(p)
                    p.take_damage(1, is_skill=False)

        # Player AoE skill hitting destructible props (instant break)
        if self.player.is_casting_aoe and not self.player.aoe_hit_done:
            for p in self.props:
                if p.active:
                    dist = pygame.math.Vector2(p.rect.center).distance_to(pygame.math.Vector2(self.player.rect.center))
                    if dist <= self.player.aoe_radius:
                        p.take_damage(999, is_skill=True)
        
        # Grab player projectiles
        while self.player.projectiles:
            self.projectiles.append(self.player.projectiles.pop(0))
            
        for e in self.enemies:
            e.update(dt, solid_rects, self.player)
            if hasattr(e, "projectiles"):
                while e.projectiles:
                    self.projectiles.append(e.projectiles.pop(0))
                    
            if not e.is_dead:
                # Player attacks enemy with sword (at most 1 hit per attack swing)
                if player_atk_rect and player_atk_rect.colliderect(e.rect) and e not in self.player.attack_hit_enemies:
                    self.player.attack_hit_enemies.add(e)
                    atk_dmg = self.player.profile.skills.get("j").damage if hasattr(self.player, "profile") and "j" in self.player.profile.skills else 15
                    e.take_damage(atk_dmg)
                    # Shaia passive: Heal 1 HP and 2 MP on hit
                    if getattr(self.player, "character_id", "") == "shaia" or getattr(self.player, "passive_id", "") == "shaia_battle_thirst":
                        self.player.health = min(self.player.max_health, self.player.health + 1)
                        self.player.mana = min(self.player.max_mana, self.player.mana + 2)
                
                # Enemy attack hitbox damage (Takes priority over touch)
                hit_player = False
                if hasattr(e, "get_attack_hitbox"):
                    e_atk_rect = e.get_attack_hitbox()
                    if e_atk_rect and not self.player.is_dashing and not self.player.is_casting_ultimate and e_atk_rect.colliderect(self.player.rect):
                        atk_dmg = getattr(e, "attack_damage", 4)
                        self.player.take_damage(atk_dmg)
                        hit_player = True
                        
                # Enemy body collision damage (if not already hit by attack)
                if not hit_player and not self.player.is_dashing and not self.player.is_casting_ultimate and e.rect.colliderect(self.player.rect):
                    touch_dmg = getattr(e, "touch_damage", 2)
                    self.player.take_damage(touch_dmg)
                        
        # Update projectiles
        for proj in self.projectiles[:]:
            proj.update(dt, solid_rects)
            if not proj.active:
                self.projectiles.remove(proj)
                continue
                
            # Skip collision checks if projectile is exploding/has already dealt damage
            if not proj.can_deal_damage():
                continue
                
            if proj.is_enemy:
                if not self.player.is_dashing and not self.player.is_casting_ultimate and proj.rect.colliderect(self.player.rect):
                    if self.player not in proj.hit_entities:
                        proj.hit_entities.add(self.player)
                        self.player.take_damage(proj.damage)
                        proj.explode()
            else:
                hit_target = False
                for e in self.enemies:
                    if not e.is_dead and e not in proj.hit_entities and proj.rect.colliderect(e.rect):
                        proj.hit_entities.add(e)
                        e.take_damage(proj.damage)
                        # Ignis burn application
                        if getattr(proj, "is_burn", False) and hasattr(e, "apply_burn"):
                            e.apply_burn(4.0, 3.0)
                        proj.explode()
                        hit_target = True
                        break
                if not hit_target:
                    # Player projectile hitting destructible props (instant break)
                    for p in self.props:
                        if p.active and p not in proj.hit_entities and proj.rect.colliderect(p.rect):
                            proj.hit_entities.add(p)
                            p.take_damage(999, is_skill=True)
                            proj.explode()
                            break
                
        for c in self.collectibles:
            c.update(dt)
            if c.active and self.player.rect.colliderect(c.rect.inflate(-4, -4)):
                c.collect(self.player)
                
        for t in self.traps:
            t.update(self.player)
            
        if self.checkpoint.update(self.player):
            pass
            
        # Update camera position to follow player smoothly
        self.camera.update(self.player.rect, dt)
        
        # Portal transition logic with LoadingScene
        self.portal.update(dt)
        if self.player.rect.colliderect(self.portal.rect.inflate(30, 20)):
            next_stg = self.cfg["next_stage"]
            if next_stg == 5:
                next_scene = BossScene(self.scene_manager)
            else:
                next_scene = LevelScene(stage=next_stg, scene_manager=self.scene_manager)
                
            loading = LoadingScene(
                self.scene_manager,
                next_scene,
                title=self.cfg["next_title"],
                tip=self.cfg["tip"]
            )
            self.scene_manager.change_scene(loading)
            
        # Death logic with DeathScreen
        if self.player.health <= 0:
            if not self.death_screen.active:
                self.death_screen.start()
            death_action = self.death_screen.update(dt)
            if death_action == "retry":
                self.scene_manager.change_scene(LevelScene(stage=self.stage, scene_manager=self.scene_manager))
                return
            elif death_action == "menu":
                from scenes.main_menu import MainMenuScene
                self.scene_manager.change_scene(MainMenuScene(self.scene_manager))
                return
            
    def spawn_item(self, x: float, y: float, item_type: str = "potion", *args):
        from entities.collectible import Collectible
        # Handles calls with either (x, y, item_type) or (x, y)
        actual_type = item_type if isinstance(item_type, str) else (args[0] if args else "potion")
        self.collectibles.append(Collectible(x, y, actual_type, is_dropped=True))
        
    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(UI_BACKGROUND)
        
        if self.theme == "forest":
            # 1. Sky Gradient Layer (subtle parallax 0.15)
            sky_draw_x = -self.camera.offset.x * 0.15
            num_sky = (self.map_width // self.forest_sky_w) + 2
            for i in range(num_sky):
                surface.blit(self.forest_sky, (sky_draw_x + i * self.forest_sky_w, 0))
                
            # 2. Forest Canopy & Mountain Layer (parallax 0.45)
            canopy_draw_x = -self.camera.offset.x * 0.45
            num_canopy = (self.map_width // self.forest_canopy_w) + 2
            for i in range(num_canopy):
                surface.blit(self.forest_canopy, (canopy_draw_x + i * self.forest_canopy_w, 0))
                
            # 3. Grass Ground Tiles (drawn at y = 330 so top blades align with solid floor y = 340)
            num_grass = (self.map_width // 48) + 2
            for i in range(num_grass):
                surface.blit(self.grass_tile, (i * 48 - self.camera.offset.x, 330))
        else:
            # Clean Dungeon Background without internal seams:
            # 1. Left Room Wall at x = 0
            surface.blit(self.bg_left, (0 - self.camera.offset.x, 0 - self.camera.offset.y))
            # 2. Seamless Center Open Corridor in the middle
            cur_x = 512
            while cur_x < self.map_width - 512:
                surface.blit(self.bg_center, (cur_x - self.camera.offset.x, 0 - self.camera.offset.y))
                cur_x += 512
            # 3. Right Room Wall with Portal Exit at the end
            surface.blit(self.bg_right, (self.map_width - 512 - self.camera.offset.x, 0 - self.camera.offset.y))
            
            # 4. Right Foreground Wall Overlay
            if self.right_overlay:
                surface.blit(self.right_overlay, (self.map_width - 128 - self.camera.offset.x, 0 - self.camera.offset.y))
            
        # Draw Traps & Checkpoints
        self.checkpoint.draw(surface, self.camera.offset)
        for t in self.traps:
            t.draw(surface, self.camera.offset)
            
        # Y-Sort entities (Player, Props, Enemies)
        drawables = [self.player] + self.props + [e for e in self.enemies if not (e.is_dead and e.anim_manager.is_finished("dead"))]
        drawables.sort(key=lambda x: x.rect.bottom)
        
        for d in drawables:
            d.draw(surface, self.camera.offset)
            
        # Draw Portal
        self.portal.draw(surface, self.camera.offset)
        
        # Draw Collectibles
        for c in self.collectibles:
            c.draw(surface, self.camera.offset)
            
        # Draw Projectiles
        for p in self.projectiles:
            p.draw(surface, self.camera.offset)
            
        # Dynamic Point Lights
        lights = []
        for p in self.projectiles:
            if getattr(p, "is_enemy", False):
                if getattr(p, "projectile_type", "") == "mage_fireball":
                    lights.append(LightSource(p.rect.centerx, p.rect.centery, 55, (190, 70, 255), 0.9, True))
                else:
                    lights.append(LightSource(p.rect.centerx, p.rect.centery, 60, (70, 160, 255), 0.9, True))
            else:
                lights.append(LightSource(p.rect.centerx, p.rect.centery, 55, (255, 130, 50), 0.9, True))
                
        # Portal Light
        lights.append(LightSource(self.portal.rect.centerx, self.portal.rect.centery, 85, (110, 180, 255), 0.85, True))
        
        # Player Celestial Aura when 100 MP (Ultimate Ready)
        if self.player.mana >= 100 and not self.player.is_dead:
            lights.append(LightSource(self.player.rect.centerx, self.player.rect.centery, 50, (255, 220, 100), 0.40, True))
            
        for c in self.collectibles:
            if c.item_type == "orb":
                lights.append(LightSource(c.rect.centerx, c.rect.centery, 35, (100, 210, 255), 0.6, True))
                
        # Render Point Lights, Atmospheric Particles & Vignette
        self.lighting.draw_point_lights(surface, lights, self.camera.offset)
        self.lighting.draw_ambient_particles(surface, self.camera.offset)
        self.lighting.draw_vignette(surface)
        
        # Draw HUD
        self.hud.draw(surface)
        
        # Draw Death Screen if player died
        if self.death_screen.active:
            self.death_screen.draw(surface)
            
        # Draw Pause Menu if paused
        if self.paused:
            self.pause_menu.draw(surface)


