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
from entities.enemy import Skeleton, MageSkeleton, WildBoar, SkeletonWarrior, SkeletonSpearman, SkeletonArcher
from world.checkpoint import Checkpoint
from entities.portal import Portal
from scenes.loading_scene import LoadingScene
from scenes.boss_scene import BossScene
from engine.lighting import LightingEngine, LightSource
from engine.v3.postfx.bloom import BloomEngine
from engine.v3.core.adaptive_quality import ADAPTIVE_QUALITY
from ui.dialogue_box import DialogueBox

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
            (440, 338, "potion"),
            (1100, 338, "orb"),
            (1750, 338, "chicken"),
            (2400, 338, "orb")
        ],
        "props": [
            (250, 340, "barrel", 1.0),
            (600, 340, "rock", 0.9),
            (1400, 340, "barrel", 1.0),
            (1800, 340, "rock", 0.9),
            (2200, 340, "barrel", 1.0)
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
            ("spearman", 400, 200),
            ("archer", 850, 200),
            ("warrior", 1300, 200),
            ("spearman", 1750, 200),
            ("mage", 2200, 200),
            ("archer", 2650, 200),
            ("warrior", 3050, 200),
        ],
        "collectibles": [
            (380, 338, "potion"),
            (1300, 338, "orb"),
            (2100, 338, "chicken"),
            (2900, 338, "orb")
        ],
        "props": [
            (500, 340, "rock", 0.9),
            (950, 340, "chest", 1.0),
            (1400, 340, "rock", 0.9),
            (2050, 340, "chest", 1.0),
            (2550, 340, "rock", 0.9)
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
            (600, 338, "orb"),
            (1300, 338, "potion"),
            (2000, 338, "orb"),
            (2700, 338, "chicken"),
            (3400, 338, "orb")
        ],
        "props": [
            (200, 340, "barrel", 1.0),
            (900, 340, "rock", 0.9),
            (1450, 340, "barricade", 1.0),
            (2100, 340, "barrel", 1.0),
            (2700, 340, "rock", 0.9),
            (3300, 340, "barricade", 1.0)
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
            ("spearman", 380, 200),
            ("mage", 800, 200),
            ("archer", 1250, 200),
            ("warrior", 1700, 200),
            ("spearman", 2150, 200),
            ("mage", 2600, 200),
            ("warrior", 3050, 200),
            ("archer", 3500, 200),
        ],
        "collectibles": [
            (600, 338, "potion"),
            (1400, 338, "orb"),
            (2200, 338, "golden_potion"),
            (3000, 338, "orb")
        ],
        "props": [
            (200, 340, "rock", 0.9),
            (900, 340, "chest", 1.0),
            (1600, 340, "rock", 0.9),
            (2300, 340, "chest", 1.0),
            (3000, 340, "rock", 0.9)
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
    def __init__(self, *args, **kwargs):
        scene_manager = kwargs.get("scene_manager", None)
        stage = kwargs.get("stage", None)
        for arg in args:
            if hasattr(arg, "change_scene") and scene_manager is None:
                scene_manager = arg
            elif isinstance(arg, int) and stage is None:
                stage = arg
            elif hasattr(arg, "stage_id") and stage is None:
                stage = arg
        self.scene_manager = scene_manager
        self.stage = stage if stage is not None else 1
        
        from engine.stage_manager import ParallaxRenderer, STAGE_CATALOG
        from engine.v3.weather.clouds import CloudsManager
        from engine.v3.weather.mist import MistManager
        from engine.score_system import ScoreSystem

        if isinstance(self.stage, str) and self.stage in STAGE_CATALOG:
            self.stage = STAGE_CATALOG[self.stage]
        stage = self.stage
        
        if hasattr(stage, "stage_id"):
            self.floor_y = getattr(stage, "floor_y", 280)
            cfg = {
                "theme": getattr(stage, "biome_theme", "dungeon"),
                "map_width": stage.map_width,
                "portal_x": stage.portal_x,
                "enemies": [(e[0], e[1], self.floor_y - 80) for e in stage.enemies],
                "collectibles": [(c[0], self.floor_y - 2, c[2]) for c in stage.collectibles],
                "props": [(p[0], self.floor_y, p[2], p[3]) for p in stage.props],
                "traps": [(t[0], self.floor_y - 16) for t in stage.traps],
                "title": stage.title,
                "next_stage": getattr(stage, "next_stage", None),
                "next_title": getattr(stage, "next_title", "PRÓXIMA FASE"),
                "tip": getattr(stage, "tip", "Avance pelo portal das ruínas!"),
                "boss_type": getattr(stage, "boss_type", "skeleton_king")
            }
            self.parallax_renderer = ParallaxRenderer(
                stage.bg_folder,
                stage.layer_files,
                stage.layer_speeds,
                screen_h=360,
                initial_offsets=getattr(stage, "layer_initial_offsets", None)
            )
            self.clouds = CloudsManager(
                theme=getattr(stage, "cloud_theme", "white"),
                map_width=stage.map_width,
                cloud_count=getattr(stage, "cloud_count", 14),
                screen_w=640,
                sky_horizon_y=getattr(stage, "sky_horizon_y", 70),
                cloud_tint=getattr(stage, "cloud_tint", None),
                cloud_opacity_scale=getattr(stage, "cloud_opacity_scale", 1.0)
            )
            self.mist_manager = MistManager(screen_w=640, screen_h=360, floor_y=self.floor_y, theme=getattr(stage, "biome_theme", "road"))
            self.score_system = ScoreSystem(stage_id=stage.stage_id)
            from engine.save_manager import SAVE
            stage_stg_id = getattr(stage, "stage_id", None)
            dialogue_intro = getattr(stage, "dialogue_intro", [])
            intro_already_done = SAVE.is_event_completed(f"{stage_stg_id}_intro") if stage_stg_id else False
            self.dialogue_box = DialogueBox(dialogue_intro) if (dialogue_intro and not intro_already_done) else None
        else:
            self.floor_y = 340
            stage_stg_id = None
            cfg = STAGE_CONFIGS.get(stage, STAGE_CONFIGS[1])
            self.parallax_renderer = None
            self.clouds = None
            self.mist_manager = None
            self.score_system = ScoreSystem(stage_id=f"arcade_{stage}")
            self.dialogue_box = None
            
        self.cfg = cfg
        self.theme = cfg.get("theme", "dungeon")
        self.map_width = cfg["map_width"]
        self.portal_x = cfg["portal_x"]
        
        # Load Theme Background Assets
        if self.parallax_renderer is not None:
            pass # Managed by ParallaxRenderer
        elif self.theme == "forest":
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
        
        self.camera = Camera(self.portal_x + 100, 360)
        spawn_x = 180 if self.theme == "dungeon" else 120
        spawn_y = self.floor_y - 80
        p1_char = getattr(SETTINGS, "CURRENT_CHARACTER", "shaia")
        p1_dev = getattr(SETTINGS, "P1_INPUT_DEVICE", "keyboard")
        self.player = Player(spawn_x, spawn_y, character_id=p1_char, player_index=0, input_device=p1_dev)
        self.hud = HUD(self.player, stage_title=cfg["title"], player_index=0)
        
        # Staged In-World Dialogue Actor (Official Interlocutor entering scene physically)
        self.dialogue_actor = None
        actor_id = getattr(stage, "cinematic_actor", None)
        if actor_id and self.dialogue_box:
            from entities.dialogue_actor import DialogueActor
            actor_start_x = max(20.0, spawn_x - 140.0)
            actor_target_x = spawn_x - 65.0
            self.dialogue_actor = DialogueActor(
                character_id=actor_id,
                x=actor_start_x,
                y=self.floor_y,
                target_x=actor_target_x,
                exit_x=max(0.0, actor_start_x - 40.0),
                speed=115.0
            )
            def _on_actor_dialogue_finish():
                if self.dialogue_actor:
                    self.dialogue_actor.start_exit()
                if stage_stg_id:
                    from engine.save_manager import SAVE
                    SAVE.set_event_completed(f"{stage_stg_id}_intro")
            self.dialogue_box.on_complete = _on_actor_dialogue_finish

        # Co-op Player 2 Setup
        self.coop_enabled = getattr(SETTINGS, "COOP_ENABLED", False)
        self.player2 = None
        self.hud2 = None
        self.synergy_system = None
        if self.coop_enabled:
            p2_char = getattr(SETTINGS, "P2_CHARACTER", "lunaria")
            p2_dev = getattr(SETTINGS, "P2_INPUT_DEVICE", "keyboard")
            self.player2 = Player(spawn_x + 45, spawn_y, character_id=p2_char, player_index=1, input_device=p2_dev)
            self.player.companion = self.player2
            self.player2.companion = self.player
            self.hud2 = HUD(self.player2, stage_title=None, player_index=1)
            from entities.coop_synergy import CoopSynergySystem
            self.synergy_system = CoopSynergySystem()

        self.paused = False
        self.pause_menu = PauseMenu(self.scene_manager, self.unpause)
        self.death_timer = 0.0

        # Freeze GC during active combat to eliminate frame drop micro-stuttering
        from engine.system_optimizer import freeze_gc_for_gameplay
        freeze_gc_for_gameplay("LevelScene")
        from ui.death_screen import DeathScreen
        self.death_screen = DeathScreen()
        self.lighting = LightingEngine(
            theme=self.theme,
            screen_w=SETTINGS.GAME_WIDTH,
            screen_h=SETTINGS.GAME_HEIGHT,
            floor_y=int(self.floor_y)
        )
        self.lighting.configure_stage_ao(self.theme, int(self.floor_y))
        self.bloom_engine = BloomEngine(SETTINGS.GAME_WIDTH, SETTINGS.GAME_HEIGHT)
        
        # Instantiate Props FIRST so collectible and enemy spatial validation has full geometry
        self.props = []
        for px, py, p_type, p_scale in cfg["props"]:
            self.props.append(Prop(px, py, p_type, p_scale))
            
        solid_props = [p for p in self.props if p.prop_type in ("rock", "barrel", "barricade")]

        # Instantiate Enemies from Config with safe spatial validation (never spawned inside rocks)
        self.enemies = []
        for e_type, ex, ey in cfg["enemies"]:
            safe_ex, safe_ey = self.find_safe_spawn_pos(ex, ey, solid_props, self.map_width)
            if e_type == "mage":
                self.enemies.append(MageSkeleton(safe_ex, safe_ey))
            elif e_type == "spearman":
                self.enemies.append(SkeletonSpearman(safe_ex, safe_ey))
            elif e_type == "archer":
                self.enemies.append(SkeletonArcher(safe_ex, safe_ey))
            elif e_type == "warrior":
                self.enemies.append(SkeletonWarrior(safe_ex, safe_ey))
            elif e_type == "boar":
                self.enemies.append(SkeletonWarrior(safe_ex, safe_ey))
            else:
                self.enemies.append(SkeletonWarrior(safe_ex, safe_ey))
                
        # Instantiate Collectibles with safe spatial validation (never inside rocks)
        self.collectibles = []
        for cx, cy, c_item in cfg["collectibles"]:
            safe_x, safe_y = self.find_safe_spawn_pos(cx, cy, solid_props, self.map_width)
            self.collectibles.append(Collectible(safe_x, safe_y, c_item))
            
        # Instantiate Traps
        self.traps = []
        for tx, ty in cfg["traps"]:
            self.traps.append(SpikeTrap(tx, ty))
            
        self.projectiles = []
        
        # Portal to next scene
        self.portal = Portal(self.portal_x, self.floor_y - 64)
        self.checkpoint = Checkpoint(self.portal_x // 2, self.floor_y - 64)

    @staticmethod
    def find_safe_spawn_pos(cx: float, cy: float, obstacles: list, map_width: float, min_x: float = 220.0, max_x: float = None) -> tuple[float, float]:
        """Validates that a collectible or item spawn is NOT inside rocks or solid obstacles."""
        if max_x is None:
            max_x = map_width - 80.0
        
        test_rect = pygame.FRect(cx - 14, cy - 24, 28, 28)
        colliding_obstacle = None
        for obs in obstacles:
            obs_hitbox = getattr(obs, "hitbox", getattr(obs, "rect", None))
            if obs_hitbox and obs_hitbox.colliderect(test_rect.inflate(14, 8)):
                colliding_obstacle = obs_hitbox
                break
                
        if not colliding_obstacle:
            return float(cx), float(cy)
            
        # Obstacle detected! Shift safely outwards
        left_candidate_x = colliding_obstacle.left - 30.0
        right_candidate_x = colliding_obstacle.right + 30.0
        
        for cand_x in (left_candidate_x, right_candidate_x):
            if min_x <= cand_x <= max_x:
                cand_rect = pygame.FRect(cand_x - 14, cy - 24, 28, 28)
                if not any(getattr(o, "hitbox", getattr(o, "rect", None)).colliderect(cand_rect) for o in obstacles):
                    return float(cand_x), float(cy)
                    
        # Multi-step outward scan fallback
        for offset in range(35, 220, 20):
            for sign in (-1, 1):
                cand_x = cx + sign * offset
                if min_x <= cand_x <= max_x:
                    cand_rect = pygame.FRect(cand_x - 14, cy - 24, 28, 28)
                    if not any(getattr(o, "hitbox", getattr(o, "rect", None)).colliderect(cand_rect) for o in obstacles):
                        return float(cand_x), float(cy)
                        
        return float(cx), float(cy)
        
    def unpause(self):
        self.paused = False
        
    def handle_events(self, events: list[pygame.event.Event]) -> None:
        if self.dialogue_box and not self.dialogue_box.is_finished:
            self.dialogue_box.handle_events(events)
        
    def update(self, dt: float) -> None:
        # Update Staged Dialogue Actor & Box
        if getattr(self, "dialogue_actor", None) and self.dialogue_actor.active:
            self.dialogue_actor.update(dt, player=self.player, player_pos=(self.player.rect.centerx, self.player.rect.bottom))
            if self.dialogue_actor.state == "ENTER":
                return # Interlocutor is walking in to position
            if self.dialogue_box and not self.dialogue_box.is_finished:
                self.dialogue_box.update(dt)
                return # Dialogue currently speaking
            if self.dialogue_actor.state == "EXIT":
                return # Interlocutor gracefully walking out
        elif self.dialogue_box and not self.dialogue_box.is_finished:
            self.dialogue_box.update(dt)
            return

        if INPUT.is_action_just_pressed("PAUSE"):
            self.paused = not self.paused
            
        if self.paused:
            self.pause_menu.update()
            return
            
        self.lighting.update(dt)
        if getattr(self, "clouds", None) is not None:
            self.clouds.update(dt)
        if getattr(self, "score_system", None) is not None:
            self.score_system.update(dt)
        
        # Solid boundaries: Left wall stops player properly, right wall stops player right at portal
        left_bound = 215 if self.theme == "dungeon" else 120
        solid_rects = [
            pygame.FRect(0, self.floor_y, self.map_width + 400, 100),     # Solid ground calibrated to floor_y
            pygame.FRect(-100, 0, left_bound, 500),                        # Left boundary wall
            pygame.FRect(self.portal_x + 10, 0, 200, 500)                  # Right boundary wall at portal
        ]
        
        # Add solid obstacle hitboxes for active props
        for p in self.props:
            if p.active and p.prop_type in ["barrel", "rock"]:
                hitbox = pygame.FRect(p.rect.x + 3, p.rect.y + 4, p.rect.width - 6, p.rect.height - 4)
                solid_rects.append(hitbox)
        
        active_players = [p for p in [self.player, self.player2] if p]
        
        # 1. Update Players
        for p in active_players:
            p.update(dt, solid_rects, self.enemies, self.camera)
            p.trigger_aoe_damage(self.enemies, self.camera)
            while p.projectiles:
                self.projectiles.append(p.projectiles.pop(0))

        # 2. Coop Synergies & Auras
        if self.synergy_system and self.player2:
            self.synergy_system.update(self.player, self.player2, self.enemies, dt)

        # 3. Gameplay updates for props & item drops
        for p in self.props[:]:
            p.update(dt, self.player, self.spawn_item)
            if not p.active:
                if hasattr(p, "dropped_item") and p.dropped_item:
                    from entities.collectible import Collectible
                    self.collectibles.append(Collectible(p.dropped_item[0], p.dropped_item[1], "potion", is_dropped=True))
                    p.dropped_item = None
                self.props.remove(p)
            
        # 4. Players attacking props
        for cur_p in active_players:
            p_atk_rect = cur_p.get_attack_hitbox()
            if p_atk_rect:
                for p in self.props:
                    if p.active and p_atk_rect.colliderect(p.rect) and p not in cur_p.attack_hit_enemies:
                        cur_p.attack_hit_enemies.add(p)
                        p.take_damage(1, is_skill=False)
            if cur_p.is_casting_aoe and not cur_p.aoe_hit_done:
                for p in self.props:
                    if p.active:
                        dist = pygame.math.Vector2(p.rect.center).distance_to(pygame.math.Vector2(cur_p.rect.center))
                        if dist <= cur_p.aoe_radius:
                            p.take_damage(999, is_skill=True)

        # 5. Enemies AI & Collision with Players
        for e in self.enemies:
            # Target closest living player
            target = self.player
            if self.player2 and not self.player2.is_dead:
                if self.player.is_dead:
                    target = self.player2
                else:
                    d1 = abs(self.player.rect.centerx - e.rect.centerx)
                    d2 = abs(self.player2.rect.centerx - e.rect.centerx)
                    target = self.player if d1 <= d2 else self.player2

            e.update(dt, solid_rects, target)
            if hasattr(e, "projectiles"):
                while e.projectiles:
                    self.projectiles.append(e.projectiles.pop(0))
                    
            if not e.is_dead:
                # Players attack enemy
                for cur_p in active_players:
                    cur_atk = cur_p.get_attack_hitbox()
                    if cur_atk and cur_atk.colliderect(e.rect) and e not in cur_p.attack_hit_enemies:
                        cur_p.attack_hit_enemies.add(e)
                        atk_dmg = cur_p.profile.skills.get("j").damage if hasattr(cur_p, "profile") and "j" in cur_p.profile.skills else 15
                        e.take_damage(atk_dmg)
                        # Shaia passive: Heal 1 HP and 2 MP on hit
                        if getattr(cur_p, "character_id", "") == "shaia" or getattr(cur_p, "passive_id", "") == "shaia_battle_thirst":
                            cur_p.health = min(cur_p.max_health, cur_p.health + 1)
                            cur_p.mana = min(cur_p.max_mana, cur_p.mana + 2)
                
                # Enemy attack hitbox damage on living players
                hit_any = False
                if hasattr(e, "get_attack_hitbox"):
                    e_atk_rect = e.get_attack_hitbox()
                    if e_atk_rect:
                        for cur_p in active_players:
                            if not cur_p.is_dashing and not cur_p.is_casting_ultimate and not cur_p.is_dead and e_atk_rect.colliderect(cur_p.rect):
                                atk_dmg = getattr(e, "attack_damage", 4)
                                cur_p.take_damage(atk_dmg)
                                hit_any = True
                                
                # Enemy body touch damage
                if not hit_any:
                    for cur_p in active_players:
                        if not cur_p.is_dashing and not cur_p.is_casting_ultimate and not cur_p.is_dead and e.rect.colliderect(cur_p.rect):
                            touch_dmg = getattr(e, "touch_damage", 2)
                            cur_p.take_damage(touch_dmg)
                            
        # Prune fully despawned enemies after death sequence (fade-out + bone particles) completes
        self.enemies = [e for e in self.enemies if not getattr(e, "is_death_complete", False)]
                        
        # 6. Update Projectiles
        friendly_fire = getattr(SETTINGS, "FRIENDLY_FIRE", False)
        for proj in self.projectiles[:]:
            proj.update(dt, solid_rects)
            if not proj.active:
                self.projectiles.remove(proj)
                continue
                
            if not proj.can_deal_damage():
                continue
                
            if proj.is_enemy:
                for cur_p in active_players:
                    if not cur_p.is_dashing and not cur_p.is_casting_ultimate and not cur_p.is_dead and proj.rect.colliderect(cur_p.rect):
                        if cur_p not in proj.hit_entities:
                            proj.hit_entities.add(cur_p)
                            cur_p.take_damage(proj.damage)
                            proj.explode()
                            break
            else:
                hit_target = False
                for e in self.enemies:
                    if not e.is_dead and e not in proj.hit_entities and proj.rect.colliderect(e.rect):
                        proj.hit_entities.add(e)
                        e.take_damage(proj.damage)
                        # Ignis burn application
                        if getattr(proj, "is_burn", False) and hasattr(e, "apply_burn"):
                            e.apply_burn(4.0, 3.0)
                        # Boran earth_spike stun application (1.8s)
                        if getattr(proj, "projectile_type", "") == "earth_spike" and hasattr(e, "apply_slow"):
                            e.apply_slow(1.8, 0.0)
                        # Aurelia heal_orb / Zephyr mana_orb burst
                        if getattr(proj, "projectile_type", "") == "heal_orb":
                            for cur_p in active_players:
                                if not cur_p.is_dead:
                                    cur_p.health = min(cur_p.max_health, cur_p.health + 25)
                        elif getattr(proj, "projectile_type", "") == "mana_orb":
                            for cur_p in active_players:
                                if not cur_p.is_dead:
                                    cur_p.mana = min(cur_p.max_mana, cur_p.mana + 20.0)
                        # Piercing projectiles (holy_ray, wind_blade pierce up to 2 targets)
                        if getattr(proj, "projectile_type", "") in ("holy_ray", "wind_blade") and len(proj.hit_entities) < 2:
                            hit_target = True
                        else:
                            proj.explode()
                            hit_target = True
                            break
                if not hit_target:
                    for p in self.props:
                        if p.active and p not in proj.hit_entities and proj.rect.colliderect(p.rect):
                            proj.hit_entities.add(p)
                            p.take_damage(999, is_skill=True)
                            proj.explode()
                            hit_target = True
                            break
                # Friendly fire
                if not hit_target and friendly_fire and self.player2:
                    for cur_p in active_players:
                        if not cur_p.is_dashing and not cur_p.is_dead and proj.rect.colliderect(cur_p.rect):
                            if cur_p not in proj.hit_entities:
                                proj.hit_entities.add(cur_p)
                                cur_p.take_damage(proj.damage * 0.5)
                                proj.explode()
                                break
                
        # 7. Collectibles
        for c in self.collectibles:
            c.update(dt)
            if c.active:
                for cur_p in active_players:
                    if not cur_p.is_dead and cur_p.rect.colliderect(c.rect.inflate(-4, -4)):
                        c.collect(cur_p)
                        break
                
        # 8. Traps & Checkpoints
        for t in self.traps:
            for cur_p in active_players:
                t.update(cur_p)
            
        self.checkpoint.update(self.player)
        if self.player2:
            self.checkpoint.update(self.player2)
            
        # 9. Camera Update (Coop Bounding Box & Zoom or Single Player)
        if self.player2:
            self.camera.update_coop(self.player, self.player2, dt)
        else:
            self.camera.update(self.player.rect, dt)

        # 9b. Dynamic Sky Weather, Lighting & Ground Mist Updates
        if getattr(self, "clouds", None) is not None:
            self.clouds.update(dt)
        if getattr(self, "mist_manager", None) is not None:
            self.mist_manager.update(dt)
        if getattr(self, "lighting", None) is not None:
            self.lighting.update(dt)

        # Game Feel Manager update
        from engine.game_feel import GAME_FEEL
        GAME_FEEL.update(dt)
        
        # 10. Portal Transition Logic
        self.portal.update(dt)
        portal_reached = self.player.rect.colliderect(self.portal.rect.inflate(30, 20)) or (self.player2 and self.player2.rect.colliderect(self.portal.rect.inflate(30, 20)))
        if portal_reached:
            # Register high score if score system active
            if getattr(self, "score_system", None):
                self.score_system.calculate_final_score()
                
            # Persist story mode stage completion & progression
            from engine.save_manager import SAVE
            current_stg_id = getattr(self.stage, "stage_id", None)
            if current_stg_id:
                SAVE.complete_stage(current_stg_id)
                next_stg_cand = getattr(self.stage, "next_stage", None)
                if next_stg_cand and next_stg_cand != "boss":
                    SAVE.unlock_stage(next_stg_cand)

            next_stg = self.cfg.get("next_stage") if isinstance(self.cfg, dict) else getattr(self.cfg, "next_stage", None)
            boss_t = self.cfg.get("boss_type", "skeleton_king") if isinstance(self.cfg, dict) else getattr(self.cfg, "boss_type", "skeleton_king")
            
            from engine.stage_manager import STAGE_CATALOG
            if next_stg == 5 or next_stg == "boss":
                next_scene = BossScene(self.scene_manager, boss_type=boss_t)
            elif isinstance(next_stg, str) and next_stg in STAGE_CATALOG:
                next_scene = LevelScene(stage=STAGE_CATALOG[next_stg], scene_manager=self.scene_manager)
            elif next_stg is not None and next_stg in STAGE_CONFIGS:
                next_scene = LevelScene(stage=next_stg, scene_manager=self.scene_manager)
            else:
                # Campaign stage cleared! Return to Story Mode
                from scenes.story_select_scene import StorySelectScene
                next_scene = StorySelectScene(self.scene_manager)
                
            loading = LoadingScene(
                self.scene_manager,
                next_scene,
                title=self.cfg.get("next_title", "FASE CONCLUÍDA!"),
                tip=self.cfg.get("tip", "Parabéns por superar os perigos das Ruínas!")
            )
            self.scene_manager.change_scene(loading)
            
        # 11. Death Screen: triggers only when all players are defeated
        all_dead = self.player.is_dead and (self.player2 is None or self.player2.is_dead)
        if all_dead:
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
        solid_props = [p for p in self.props if p.active and p.prop_type in ("rock", "barrel", "barricade")]
        safe_x, safe_y = self.find_safe_spawn_pos(x, y, solid_props, self.map_width)
        self.collectibles.append(Collectible(safe_x, safe_y, actual_type, is_dropped=True))
        
    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(UI_BACKGROUND)
        sw, sh = surface.get_size()
        cam_x, cam_y = self.camera.offset.x, self.camera.offset.y
        vl, vr = cam_x - 32, cam_x + sw + 32
        vt, vb = cam_y - 32, cam_y + sh + 32
        
        # --- SILKSONG 2D DEPTH RENDERING PIPELINE ---
        # 1. Distant Base Sky & Mountains
        if getattr(self, "parallax_renderer", None) is not None:
            if self.parallax_renderer.has_split_layers:
                # 1. Sky Layer (Layer 0)
                self.parallax_renderer.draw_sky_layer(surface, cam_x, cam_y)

                # 2. Silksong Floating Atmospheric Particles (Background batch: behind mountains/towers)
                self.lighting.draw_ambient_particles_background(surface, self.camera.offset)

                # 3. Sky Clouds (Rendered behind fortress towers and mountains, clipped to sky_horizon_y)
                if getattr(self, "clouds", None) is not None:
                    horizon_y = getattr(self.clouds, "sky_horizon_y", 88)
                    surface.set_clip(pygame.Rect(0, 0, sw, horizon_y))
                    self.clouds.draw(surface, (cam_x, cam_y), sw, sh)
                    surface.set_clip(None)

                # 4. Distant Atmospheric Depth Fog (Between distant mountains and fortress towers)
                if getattr(self, "mist_manager", None) is not None:
                    self.mist_manager.draw_distant_fog(surface, cam_x, cam_y)

                # 5. Midground Castle Towers & Walls (Layer 1 - In FRONT of clouds and distant fog)
                self.parallax_renderer.draw_midground_layer(surface, cam_x, cam_y)

                # 6. Foreground Bridge Walkway & Floor (Layer 2)
                self.parallax_renderer.draw_foreground_layer(surface, cam_x, cam_y)

                # 7. Dynamic Ground Mist over bridge floor at feet level (alpha 0.12-0.22, preserving shadows)
                if getattr(self, "mist_manager", None) is not None:
                    self.mist_manager.draw_ground_mist(surface, cam_x, cam_y)
            else:
                self.parallax_renderer.draw(surface, cam_x, cam_y)
                self.lighting.draw_ambient_particles_background(surface, self.camera.offset)
                if getattr(self, "clouds", None) is not None:
                    horizon_y = getattr(self.clouds, "sky_horizon_y", 88)
                    surface.set_clip(pygame.Rect(0, 0, sw, horizon_y))
                    self.clouds.draw(surface, (cam_x, cam_y), sw, sh)
                    surface.set_clip(None)
                if getattr(self, "mist_manager", None) is not None:
                    self.mist_manager.draw_distant_fog(surface, cam_x, cam_y)
                    self.mist_manager.draw_ground_mist(surface, cam_x, cam_y)
        elif self.theme == "forest":
            # 1. Sky Gradient Layer (subtle parallax 0.15) — Culled to visible viewport
            sky_draw_x = -cam_x * 0.15
            start_sky = max(0, int((-sky_draw_x) // self.forest_sky_w))
            end_sky = min((self.map_width // self.forest_sky_w) + 2, int((-sky_draw_x + sw) // self.forest_sky_w) + 1)
            for i in range(start_sky, end_sky + 1):
                surface.blit(self.forest_sky, (sky_draw_x + i * self.forest_sky_w, 0))

            self.lighting.draw_ambient_particles_background(surface, self.camera.offset)
                
            # 2. Forest Canopy & Mountain Layer (parallax 0.45) — Culled to visible viewport
            canopy_draw_x = -cam_x * 0.45
            start_canopy = max(0, int((-canopy_draw_x) // self.forest_canopy_w))
            end_canopy = min((self.map_width // self.forest_canopy_w) + 2, int((-canopy_draw_x + sw) // self.forest_canopy_w) + 1)
            for i in range(start_canopy, end_canopy + 1):
                surface.blit(self.forest_canopy, (canopy_draw_x + i * self.forest_canopy_w, 0))
                
            # 3. Grass Ground Tiles — Aggressively culled to visible camera viewport (11 blits instead of 85!)
            start_grass = max(0, int(cam_x // 48))
            end_grass = min((self.map_width // 48) + 2, int((cam_x + sw) // 48) + 1)
            for i in range(start_grass, end_grass + 1):
                surface.blit(self.grass_tile, (i * 48 - cam_x, 330))
        else:
            # Clean Dungeon Background without internal seams (Aggressive Camera Culling):
            # 1. Left Room Wall at x = 0
            if 0 - cam_x + 512 >= 0:
                surface.blit(self.bg_left, (0 - cam_x, 0 - cam_y))
            # 2. Seamless Center Open Corridor (only visible modules)
            cur_x = max(512, (int(cam_x) // 512) * 512)
            max_x = min(self.map_width - 512, int(cam_x + sw + 512))
            while cur_x < max_x:
                surface.blit(self.bg_center, (cur_x - cam_x, 0 - cam_y))
                cur_x += 512
            # 3. Right Room Wall with Portal Exit at the end
            if self.map_width - 512 - cam_x <= sw:
                surface.blit(self.bg_right, (self.map_width - 512 - cam_x, 0 - cam_y))
                if self.right_overlay:
                    surface.blit(self.right_overlay, (self.map_width - 128 - cam_x, 0 - cam_y))
            self.lighting.draw_ambient_particles_background(surface, self.camera.offset)
            
        # Draw Traps & Checkpoints (Culled)
        if self.checkpoint.rect.right >= vl and self.checkpoint.rect.left <= vr:
            self.checkpoint.draw(surface, self.camera.offset)
        for t in self.traps:
            if t.rect.right >= vl and t.rect.left <= vr:
                t.draw(surface, self.camera.offset)
            
        # Y-Sort entities (Players, Props, Enemies, Dialogue Actor) with 2D Frustum Culling
        living_entities = [p for p in [self.player, self.player2] if p] + self.props + [e for e in self.enemies if not getattr(e, "is_death_complete", False)]
        if getattr(self, "dialogue_actor", None) and self.dialogue_actor.active:
            living_entities.append(self.dialogue_actor)
        living_entities.sort(key=lambda x: getattr(x, "y_sort_pivot", getattr(x, "ground_y", x.rect.bottom)))

        # 8. Silksong Dynamic Entity Foot Contact AO (Soft ground anchoring for living entities & obstacles)
        self.lighting.draw_entity_ao(surface, living_entities, self.camera.offset)

        # 9. Living entities & props
        for d in living_entities:
            r = d.rect
            if r.right >= vl and r.left <= vr and r.bottom >= vt and r.top <= vb:
                d.draw(surface, self.camera.offset)
            
        # Draw Portal
        if self.portal.rect.right >= vl and self.portal.rect.left <= vr:
            self.portal.draw(surface, self.camera.offset)
        
        # Draw Collectibles
        for c in self.collectibles:
            r = c.rect
            if r.right >= vl and r.left <= vr and r.bottom >= vt and r.top <= vb:
                c.draw(surface, self.camera.offset)
            
        # Draw Projectiles
        for p in self.projectiles:
            r = p.rect
            if r.right >= vl and r.left <= vr and r.bottom >= vt and r.top <= vb:
                p.draw(surface, self.camera.offset)

        # 10. Silksong Foreground Silhouette Parallax (1.35x fast parallax dark foliage & chains)
        if getattr(self, "parallax_renderer", None) is not None:
            self.parallax_renderer.draw_foreground_silhouette(surface, cam_x, cam_y)

        # 10b. Silksong Reactive Game Feel VFX: Movement Dust & Combat Slash Arcs
        from engine.game_feel import GAME_FEEL
        GAME_FEEL.draw_dust(surface, self.camera.offset)
        GAME_FEEL.draw_slash_arcs(surface, self.camera.offset)

        # 11. Silksong Foreground Floating Atmospheric Particles (Front batch in front of entities)
        self.lighting.draw_ambient_particles_foreground(surface, self.camera.offset)

        # 12. Foreground Battlement Mist (Band 2: subtle mist sliding near bottom edge)
        if getattr(self, "mist_manager", None) is not None:
            self.mist_manager.draw_foreground_mist(surface, cam_x, cam_y)

        # Dynamic Point Lights with smooth physical photon radiance (Aggressively culled)
        lights = []
        emissives = []
        vl_light, vr_light = cam_x - 80, cam_x + sw + 80
        vt_light, vb_light = cam_y - 80, cam_y + sh + 80

        # Transient point lights from attacks, spells and slash arcs
        for tx, ty, trad, tcol, tint in GAME_FEEL.get_active_point_lights():
            if vl_light <= tx <= vr_light and vt_light <= ty <= vb_light:
                lights.append(LightSource(tx, ty, int(trad), tcol, tint))
        
        for p in self.projectiles:
            px, py = p.rect.centerx, p.rect.centery
            if vl_light <= px <= vr_light and vt_light <= py <= vb_light:
                if getattr(p, "is_enemy", False):
                    ptype = getattr(p, "projectile_type", "")
                    if ptype == "mage_fireball":
                        lights.append(LightSource(px, py, 46, (190, 70, 255), 0.85, True))
                        emissives.append((px, py, 22, (210, 110, 255), 0.35))
                    else:
                        lights.append(LightSource(px, py, 48, (80, 160, 255), 0.85, True))
                        emissives.append((px, py, 24, (120, 190, 255), 0.35))
                else:
                    pal = getattr(p, "palette", None)
                    color = getattr(pal, "inner_glow", (255, 140, 50))
                    lights.append(LightSource(px, py, 46, color, 0.85, True))
                    emissives.append((px, py, 22, color, 0.40))
                    
        # Portal Light & Bloom
        if vl_light <= self.portal.rect.centerx <= vr_light:
            lights.append(LightSource(self.portal.rect.centerx, self.portal.rect.centery, 80, (110, 180, 255), 0.85, True))
            emissives.append((self.portal.rect.centerx, self.portal.rect.centery, 38, (140, 210, 255), 0.45))
        
        for c in self.collectibles:
            if vl_light <= c.rect.centerx <= vr_light:
                if c.item_type == "orb":
                    lights.append(LightSource(c.rect.centerx, c.rect.centery, 32, (100, 210, 255), 0.55, True))
                    emissives.append((c.rect.centerx, c.rect.centery, 16, (150, 235, 255), 0.40))
                elif c.item_type == "potion":
                    emissives.append((c.rect.centerx, c.rect.centery, 14, (255, 100, 120), 0.30))
                
        # Occluder geometries for 2D Soft Shadows (Only visible props to avoid redundant CPU work!)
        occluders = []
        for prop in self.props:
            if not getattr(prop, "destroyed", False):
                pr = prop.rect
                if pr.right >= vl_light and pr.left <= vr_light:
                    occluders.extend([
                        (pr.left, pr.top, pr.right, pr.top),
                        (pr.right, pr.bottom, pr.left, pr.bottom),
                        (pr.left, pr.bottom, pr.left, pr.top),
                        (pr.right, pr.top, pr.right, pr.bottom)
                    ])
                    
        # 13. Silksong Volumetric Diagonal God Rays (Slanted sunbeams / ethereal shafts with BLEND_RGB_ADD)
        self.lighting.draw_god_rays(surface, self.camera.offset)

        # 14. 2D Soft Shadows (if enabled)
        if occluders and lights:
            self.lighting.draw_shadows(surface, lights, occluders, self.camera.offset)

        # 15. Silksong Multiplicative Lightmap Pass (Static Crevice AO + Anamorphic Vignette + Hero Glow + Dynamic Lights)
        hero_pos = (self.player.rect.centerx, self.player.rect.centery) if (self.player and not self.player.is_dead) else None
        self.lighting.draw_point_lights(surface, lights, self.camera.offset, hero_pos=hero_pos)

        # 16. Silksong Additive Bloom Pass for emissive highlights (projectiles, portal, potions)
        if emissives:
            self.lighting.draw_additive_glows(surface, emissives, self.camera.offset)

        # Ruin Engine V3.0 Stage Color Grading & Vignette (Applied to world before UI)
        self.lighting.apply_color_grading(surface, self.theme)
        self.lighting.draw_vignette(surface)
        
        # Co-op Tether & Edge Indicator Overlay
        if self.player2:
            self.camera.draw_coop_overlay(surface, self.player, self.player2)

        # Co-op Synergy Banners
        if self.synergy_system:
            self.synergy_system.draw_banners(surface)
            
        # Ruin Engine V3.0 PostFX: HDR World Bloom (Applied to game world BEFORE HUD/UI)
        if SETTINGS.RUIN_ENGINE_V3 and SETTINGS.BLOOM_ENABLED and ADAPTIVE_QUALITY.profile.bloom_passes > 0:
            self.bloom_engine.apply_bloom(surface, threshold=0.94, intensity=0.06)
            
        # Draw HUDs (P1 on left, P2 on right) - hidden during dialogue intros
        if not (self.dialogue_box and not self.dialogue_box.is_finished):
            self.hud.draw(surface)
            if self.hud2:
                self.hud2.draw(surface)
            
        # Draw Death Screen if player died
        if self.death_screen.active:
            self.death_screen.draw(surface)
            
        # Draw Pause Menu if paused
        if self.paused:
            self.pause_menu.draw(surface)

        # Draw Retro Dialogue Box on top of all HUD/overlays
        if self.dialogue_box and not self.dialogue_box.is_finished:
            self.dialogue_box.draw(surface)


