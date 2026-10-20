import pygame
import os
import math
import random
from engine.scene_manager import Scene
from engine.camera import Camera
from entities.player import Player
from entities.boss import SkeletonBoss, _BossParticle
from entities.enemy import Skeleton, MageSkeleton, WildBoar, SkeletonWarrior, SkeletonSpearman, SkeletonArcher
from entities.prop import Prop
from entities.collectible import Collectible
from ui.hud import HUD
from ui.pause import PauseMenu
from engine.input_manager import INPUT
from config.settings import SETTINGS
from engine.lighting import LightingEngine, LightSource
from engine.v3.postfx.bloom import BloomEngine
from engine.v3.core.adaptive_quality import ADAPTIVE_QUALITY

class WaterRipple:
    __slots__ = ("x", "y", "radius", "max_radius", "life", "max_life", "color")
    def __init__(self, x: float, y: float, color: tuple = (100, 180, 255)):
        self.x = float(x)
        self.y = float(y)
        self.radius = 2.0
        self.max_radius = random.uniform(14.0, 24.0)
        self.life = self.max_life = 0.55
        self.color = color

    def update(self, dt: float) -> bool:
        self.life -= dt
        self.radius += dt * 32.0
        return self.life > 0

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        t = max(0.0, self.life / self.max_life)
        alpha = int(140 * t)
        rw = int(self.radius * 2)
        rh = max(2, int(self.radius * 0.7))
        s = pygame.Surface((rw + 4, rh + 4), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (*self.color, alpha), (2, 2, rw, rh), 1)
        surface.blit(s, (self.x - cam_x - rw // 2 - 2, self.y - cam_y - rh // 2 - 2))


class WaterDroplet:
    __slots__ = ("x", "y", "vy", "color")
    def __init__(self, x: float, y: float = 0.0, color: tuple = (120, 190, 255)):
        self.x = float(x)
        self.y = float(y)
        self.vy = random.uniform(180.0, 320.0)
        self.color = color

    def update(self, dt: float, floor_y: float = 320.0) -> bool:
        self.y += self.vy * dt
        return self.y < floor_y


BOSS_DIALOGUES = {
    "demon_slime": [
        ("TITÃ DEMONÍACO", "RUAAAGHH! MINHA LAMA CORROSIVA CONSUMIRÁ SUA ALMA!"),
        ("SHAIA", "Permaneçam firmes! Destruam o núcleo sombrio deste titã!")
    ],
    "monster_creature": [
        ("MONSTRO QUIMÉRICO", "GRRRRROAAARR! O GELO ETERNO RECLAMA SEUS OSSOS!"),
        ("SHAIA", "Uma besta colossal dos glaciares... Quebre o selo da corrupção!")
    ],
    "samurai": [
        ("LORDE SAMURAI", "Saquem suas lâminas. Somente o aço mais puro cruzará este altar celeste."),
        ("SHAIA", "Que nossa determinação honre o fio da espada!")
    ],
    "skeleton_king": [
        ("REI ESQUELETO", "Miseráveis invasores... Diante do trono eterno, vocês tombarão!"),
        ("SHAIA", "Seu reinado de ossos termina hoje!")
    ]
}

class BossScene(Scene):
    # Render natively at 16:9 matching the game resolution; zero downscale blur
    internal_size = (640, 360)
    def __init__(self, scene_manager, boss_type: str = "skeleton_king"):
        self.scene_manager = scene_manager
        self.boss_type = boss_type
        
        # Freeze GC during active boss combat
        from engine.system_optimizer import freeze_gc_for_gameplay
        freeze_gc_for_gameplay("BossScene")
        
        from ui.dialogue_box import DialogueBox
        intro_lines = BOSS_DIALOGUES.get(self.boss_type, BOSS_DIALOGUES["skeleton_king"])
        self.dialogue_box = DialogueBox(intro_lines)
        
        # Native 16:9 Arena Resolution
        self.arena_w = 640
        self.arena_h = 360
        self.arena_surf = pygame.Surface((self.arena_w, self.arena_h))
        
        # Arena map bounds (Epic 2560px arena width)
        self.map_width = 2560
        self.camera = Camera(self.map_width, self.arena_h, viewport_w=self.arena_w, viewport_h=self.arena_h)
        
        # Pre-allocate background surfaces for zero-lag 60 FPS transitions
        dungeon_bg_path = os.path.join("assets", "sprites", "background", "sprites_dungeon")
        raw_left = pygame.image.load(os.path.join(dungeon_bg_path, "01_dungeon_left.png")).convert()
        raw_center = pygame.image.load(os.path.join(dungeon_bg_path, "02_dungeon_center.png")).convert()
        raw_right = pygame.image.load(os.path.join(dungeon_bg_path, "03_dungeon_right.png")).convert()
        
        panel_w, panel_h = 512, self.arena_h
        bg_left = pygame.transform.smoothscale(raw_left, (panel_w, panel_h))
        bg_center = pygame.transform.smoothscale(raw_center, (panel_w, panel_h))
        bg_right = pygame.transform.smoothscale(raw_right, (panel_w, panel_h))
        
        # 1. Phase 1 Background: Majestic Royal Throne Room (Blue lanterns & pristine stone)
        self.bg_phase1 = pygame.Surface((self.map_width, self.arena_h))
        self.bg_phase1.blit(bg_left, (0, 0))
        self.bg_phase1.blit(bg_center, (512, 0))
        self.bg_phase1.blit(bg_center, (1024, 0))
        self.bg_phase1.blit(bg_center, (1536, 0))
        self.bg_phase1.blit(bg_right, (2048, 0))
        
        # 2. Phase 2 Background: Ancient Cracked Chamber (Amber torches & stress cracks)
        self.bg_phase2 = self.bg_phase1.copy()
        tint_p2 = pygame.Surface((self.map_width, self.arena_h), pygame.SRCALPHA)
        tint_p2.fill((60, 40, 20, 70))
        self.bg_phase2.blit(tint_p2, (0, 0))
        # Draw structural masonry cracks
        for cx in range(120, self.map_width - 100, 240):
            crack_pts = [(cx, 40), (cx + 12, 85), (cx - 8, 140), (cx + 6, 210)]
            pygame.draw.lines(self.bg_phase2, (20, 15, 10), False, crack_pts, 2)
            pygame.draw.lines(self.bg_phase2, (255, 180, 50, 60), False, crack_pts, 1)

        # 3. Phase 3 Background: Necrotic Void Sovereign Arena (Violet cosmic rifts & void sigils)
        self.bg_phase3 = self.bg_phase1.copy()
        tint_p3 = pygame.Surface((self.map_width, self.arena_h), pygame.SRCALPHA)
        tint_p3.fill((90, 20, 140, 95))
        self.bg_phase3.blit(tint_p3, (0, 0))
        # Void Rifts in walls and sky
        for rx in (480, 1100, 1720, 2280):
            rift_pts = [(rx, 20), (rx + 25, 90), (rx + 10, 160), (rx + 35, 230), (rx, 300)]
            pygame.draw.lines(self.bg_phase3, (180, 50, 255), False, rift_pts, 4)
            pygame.draw.lines(self.bg_phase3, (240, 210, 255), False, rift_pts, 2)
            pygame.draw.circle(self.bg_phase3, (140, 30, 220), (rx + 18, 120), 16)
        
        # 4. Phase 4/5 Background: Cataclysmic Ruin (Blood Moon & Magma Fissures)
        self.bg_phase4 = self.bg_phase1.copy()
        tint_p4 = pygame.Surface((self.map_width, self.arena_h), pygame.SRCALPHA)
        tint_p4.fill((160, 25, 20, 110))
        self.bg_phase4.blit(tint_p4, (0, 0))
        
        # Blood Moon in sky
        moon_cx, moon_cy = 1280, 85
        pygame.draw.circle(self.bg_phase4, (255, 60, 40), (moon_cx, moon_cy), 55)
        pygame.draw.circle(self.bg_phase4, (210, 25, 25), (moon_cx, moon_cy), 48)
        pygame.draw.circle(self.bg_phase4, (255, 120, 80), (moon_cx, moon_cy), 64, 3)
        
        # Magma Floor Fissures along ground level (Y = 318 - 322)
        for fx in range(60, self.map_width - 80, 130):
            pts = [(fx, 318), (fx + 25, 321), (fx + 55, 318), (fx + 85, 322), (fx + 110, 318)]
            pygame.draw.lines(self.bg_phase4, (255, 170, 30), False, pts, 2)
            pygame.draw.lines(self.bg_phase4, (255, 60, 20), False, pts, 4)

        # Walkable Floor Lane
        self.FLOOR_TOP_Y = 240
        self.FLOOR_BOTTOM_Y = 320

        # Arena Pillars & Torches (Anchored to solid masonry columns outside door archway spans)
        self.pillar_x_coords = [416, 928, 1440, 1952, 2464]

        # Environmental Floor Occlusion Rocks: REMOVIDAS do cenário de Boss por completo a pedido
        self.environmental_rocks = []
        
        # Pre-render perspective stone paving without any artificial grid lines
        self._bake_floor_perspective_tiles()

        # Dynamic Scenery Elements (Item 9)
        self.scene_time = 0.0
        self.droplets: list[WaterDroplet] = []
        self.ripples: list[WaterRipple] = []
        self.falling_debris: list[_BossParticle] = []
        self.last_drop_spawn = 0.0
        self.active_arena_phase = 1
        self.phase_transition_alpha = 0.0

        # Player & Entities (Spawned grounded on arena floor, facing boss)
        p1_char = getattr(SETTINGS, "CURRENT_CHARACTER", "shaia")
        p1_dev = getattr(SETTINGS, "P1_INPUT_DEVICE", "keyboard")
        self.player = Player(160, self.FLOOR_BOTTOM_Y - 70, character_id=p1_char, player_index=0, input_device=p1_dev)
        self.player.facing_right = True
        self.hud = HUD(self.player, stage_title="FASE 5: A SALA DO TRONO (CHEFE)", player_index=0)
        
        # Co-op Player 2 Setup
        self.coop_enabled = getattr(SETTINGS, "COOP_ENABLED", False)
        self.player2 = None
        self.hud2 = None
        self.synergy_system = None
        if self.coop_enabled:
            p2_char = getattr(SETTINGS, "P2_CHARACTER", "lunaria")
            p2_dev = getattr(SETTINGS, "P2_INPUT_DEVICE", "keyboard")
            self.player2 = Player(210, self.FLOOR_BOTTOM_Y - 70, character_id=p2_char, player_index=1, input_device=p2_dev)
            self.player2.facing_right = True
            self.player.companion = self.player2
            self.player2.companion = self.player
            self.hud2 = HUD(self.player2, stage_title=None, player_index=1)
            from entities.coop_synergy import CoopSynergySystem
            self.synergy_system = CoopSynergySystem()

        self.paused = False
        self.pause_menu = PauseMenu(self.scene_manager, self.unpause)
        self.death_timer = 0.0
        self.victory_timer = 0.0
        self.victory = False
        from ui.death_screen import DeathScreen
        self.death_screen = DeathScreen()
        self.lighting = LightingEngine(theme="dungeon")
        self.bloom_engine = BloomEngine(self.arena_w, self.arena_h)
        
        # Boss (Spawned grounded on arena floor opposite player, facing player)
        if self.boss_type == "demon_slime":
            from entities.bosses_pack import DemonSlimeBoss
            self.boss = DemonSlimeBoss(470, self.FLOOR_BOTTOM_Y - 145)
            self.hud.stage_title = "CONFRONTO: O TITÃ DEMONÍACO"
        elif self.boss_type == "samurai":
            from entities.bosses_pack import SamuraiBoss
            self.boss = SamuraiBoss(470, self.FLOOR_BOTTOM_Y - 100)
            self.hud.stage_title = "CONFRONTO: LORDE SAMURAI"
        elif self.boss_type == "monster_creature":
            from entities.bosses_pack import MonsterCreatureBoss
            self.boss = MonsterCreatureBoss(470, self.FLOOR_BOTTOM_Y - 140)
            self.hud.stage_title = "CONFRONTO: O MONSTRO QUIMÉRICO"
        else:
            self.boss = SkeletonBoss(470, self.FLOOR_BOTTOM_Y - 100)
            self.hud.stage_title = "FASE 5: A SALA DO TRONO (CHEFE)"
            
        self.boss.facing_right = False
        self.hud.active_boss = self.boss
        if self.hud2:
            self.hud2.active_boss = self.boss
        
        self.enemies = [self.boss]
        self.collectibles = []
        self.traps = []
        self.props = []
        self.projectiles = []
        
        pygame.font.init()
        self.font_victory = pygame.font.SysFont("Arial", 36, bold=True)
        self.font_sub = pygame.font.SysFont("Arial", 16, bold=True)
        
    def _bake_floor_perspective_tiles(self):
        """
        Bakes soft ambient occlusion depth into the wall-floor seam.
        Artifical mesh/grid lines removed to ensure pure visual clarity.
        """
        floor_h = self.FLOOR_BOTTOM_Y - self.FLOOR_TOP_Y
        floor_surf = pygame.Surface((self.map_width, floor_h + 40), pygame.SRCALPHA)

        # Soft base gradient shadow along the wall-floor seam
        for y_off in range(12):
            alpha = int(45 * (1.0 - y_off / 12.0))
            pygame.draw.line(floor_surf, (5, 5, 10, alpha), (0, y_off), (self.map_width, y_off))

        # Blit clean floor shading onto all phase backgrounds
        for bg in (self.bg_phase1, self.bg_phase2, self.bg_phase3, self.bg_phase4):
            bg.blit(floor_surf, (0, self.FLOOR_TOP_Y))

    def unpause(self):
        self.paused = False
        
    def handle_events(self, events: list[pygame.event.Event]) -> None:
        if self.dialogue_box and not self.dialogue_box.is_finished:
            self.dialogue_box.handle_events(events)
        
    def _spawn_ceiling_collapse(self, count: int = 30):
        """Spawns crumbling dust and stone debris when boss transforms or slams ground."""
        for _ in range(count):
            rx = random.uniform(100, self.map_width - 100)
            ry = random.uniform(-10, 60)
            vx = random.uniform(-20, 20)
            vy = random.uniform(120, 380)
            color = random.choice([(140, 135, 125), (100, 95, 90), (180, 175, 160), (220, 90, 40)])
            self.falling_debris.append(_BossParticle(rx, ry, vx, vy, random.uniform(1.0, 2.0), color, radius=random.uniform(2, 5), gravity=450))

    def update(self, dt: float):
        if self.dialogue_box and not self.dialogue_box.is_finished:
            self.dialogue_box.update(dt)
            return

        if INPUT.is_action_just_pressed("PAUSE"):
            self.paused = not self.paused
            
        if self.paused:
            self.pause_menu.update()
            return

        self.scene_time += dt
        self.lighting.update(dt)

        # Arena Lock: Solid floor and lateral screen bounds trapping entities in visible area
        solid_rects = [
            pygame.FRect(-100, self.FLOOR_BOTTOM_Y, self.map_width + 200, 80), # Solid Floor (Y=FLOOR_BOTTOM_Y)
            pygame.FRect(-60, 0, 80, 500),                                     # Left Wall Barrier
            pygame.FRect(self.map_width - 25, 0, 80, 500)                      # Right Wall Barrier
        ]
        
        active_players = [p for p in [self.player, self.player2] if p]
        
        # 1. Update Players with Arena Lock enforcement
        for p in active_players:
            p.update(dt, solid_rects, self.enemies, self.camera)
            # Enforce arena edge bounds across full combat space
            if p.rect.left < 35:
                p.rect.left = 35
                p.pos.x = float(p.rect.x)
                p.velocity.x = 0
            elif p.rect.right > self.map_width - 35:
                p.rect.right = self.map_width - 35
                p.pos.x = float(p.rect.x)
                p.velocity.x = 0
            if p.rect.bottom > self.FLOOR_BOTTOM_Y:
                p.rect.bottom = self.FLOOR_BOTTOM_Y
                p.pos.y = float(p.rect.y)
                p.velocity.y = 0
                p.on_ground = True
            p.trigger_aoe_damage(self.enemies, self.camera)
            while p.projectiles:
                self.projectiles.append(p.projectiles.pop(0))

        # 2. Coop Synergies & Auras
        if self.synergy_system and self.player2:
            self.synergy_system.update(self.player, self.player2, self.enemies, dt)
        
        # 3. Dynamic Arena Phase Transition & Screen Shake (Item 8)
        boss_phase = self.boss.current_phase
        if boss_phase != self.active_arena_phase:
            self.active_arena_phase = boss_phase
            self.camera.shake(11.0, 1.6)
            self._spawn_ceiling_collapse(45)

        # 4. Dynamic Ceiling Droplets & Ripples (Item 9)
        self.last_drop_spawn += dt
        if self.last_drop_spawn >= 0.45:
            self.last_drop_spawn = 0.0
            drop_x = random.uniform(150, self.map_width - 150)
            drop_col = (180, 60, 255) if boss_phase == 3 else ((255, 60, 40) if boss_phase >= 4 else (120, 190, 255))
            self.droplets.append(WaterDroplet(drop_x, y=0.0, color=drop_col))

        for d in self.droplets[:]:
            if not d.update(dt, floor_y=float(self.FLOOR_BOTTOM_Y)):
                self.droplets.remove(d)
                self.ripples.append(WaterRipple(d.x, y=float(self.FLOOR_BOTTOM_Y), color=d.color))

        self.ripples = [r for r in self.ripples if r.update(dt)]
        self.falling_debris = [p for p in self.falling_debris if p.update(dt)]

        # Update props & handle item drops
        for p in self.props[:]:
            p.update(dt)
            if not p.active:
                if hasattr(p, "dropped_item") and p.dropped_item:
                    self.collectibles.append(Collectible(p.dropped_item[0], p.dropped_item[1], "potion", is_dropped=True))
                    p.dropped_item = None
                self.props.remove(p)

        # Check if boss dropped healing potion
        while self.boss.potions_to_spawn:
            px, py = self.boss.potions_to_spawn.pop(0)
            self.collectibles.append(Collectible(px, py, "potion", is_dropped=True))
            
        # Check if boss wants to spawn minions
        while self.boss.minions_to_spawn:
            m_type, mx = self.boss.minions_to_spawn.pop(0)
            spawn_x = max(120, min(self.map_width - 150, mx))
            spawn_y = self.FLOOR_BOTTOM_Y - 45
            if m_type == "mage":
                self.enemies.append(MageSkeleton(spawn_x, spawn_y))
            elif m_type in ("spearman", "boar"):
                self.enemies.append(SkeletonSpearman(spawn_x, spawn_y))
            elif m_type == "archer":
                self.enemies.append(SkeletonArcher(spawn_x, spawn_y))
            else:
                self.enemies.append(SkeletonWarrior(spawn_x, spawn_y))
        
        # Check Victory
        is_anim_done = self.boss.anim_manager.is_finished("dead") or self.boss.anim_manager.is_finished("death") or getattr(self.boss, "state", "") == "DEATH"
        if self.boss.is_dead and is_anim_done:
            self.victory = True
            self.victory_timer += dt
            if self.victory_timer > 5.0 or INPUT.is_action_just_pressed("ATTACK") or INPUT.is_action_just_pressed("JUMP"):
                from scenes.main_menu import MainMenuScene
                self.scene_manager.change_scene(MainMenuScene(self.scene_manager))
                return
            
        for e in self.enemies:
            target = self.player
            if self.player2 and not self.player2.is_dead:
                if self.player.is_dead:
                    target = self.player2
                else:
                    d1 = abs(self.player.rect.centerx - e.rect.centerx)
                    d2 = abs(self.player2.rect.centerx - e.rect.centerx)
                    target = self.player if d1 <= d2 else self.player2

            if e == self.boss:
                e.update(dt, solid_rects, target, self.camera)
                # Enforce Boss arena bounds across full combat arena
                if e.rect.left < 35:
                    e.rect.left = 35
                    if hasattr(e, "pos"):
                        e.pos.x = float(e.rect.x)
                    e.velocity.x = 0
                elif e.rect.right > self.map_width - 35:
                    e.rect.right = self.map_width - 35
                    if hasattr(e, "pos"):
                        e.pos.x = float(e.rect.x)
                    e.velocity.x = 0
                if not getattr(e, "is_floating", False):
                    if e.rect.bottom > self.FLOOR_BOTTOM_Y:
                        e.rect.bottom = self.FLOOR_BOTTOM_Y
                        if hasattr(e, "pos"):
                            e.pos.y = float(e.rect.y)
                        e.velocity.y = 0
                        e.on_ground = True
            else:
                e.update(dt, solid_rects, target)
            if hasattr(e, "projectiles"):
                while e.projectiles:
                    self.projectiles.append(e.projectiles.pop(0))
            
            # Combat Logic (Melee / Body)
            for cur_p in active_players:
                if not cur_p.is_dashing and not cur_p.is_casting_ultimate and not cur_p.is_dead and not e.is_dead:
                    attack_hitbox = getattr(e, "get_attack_hitbox", lambda: None)()
                    if attack_hitbox and attack_hitbox.colliderect(cur_p.rect):
                        atk_dmg = getattr(e, "attack_damage", 35 if e == self.boss else 4)
                        cur_p.take_damage(atk_dmg)
                    elif e.rect.colliderect(cur_p.rect):
                        touch_dmg = getattr(e, "touch_damage", 0 if e == self.boss else 2)
                        if touch_dmg > 0:
                            cur_p.take_damage(touch_dmg)
                
        # Prune fully despawned minions after death sequence (fade-out + bone particles) completes
        self.enemies = [e for e in self.enemies if e == self.boss or not getattr(e, "is_death_complete", False)]

        # Players attacking enemies
        for cur_p in active_players:
            p_hitbox = cur_p.get_attack_hitbox()
            if p_hitbox:
                for e in self.enemies:
                    if not e.is_dead and p_hitbox.colliderect(e.rect) and e not in cur_p.attack_hit_enemies:
                        cur_p.attack_hit_enemies.add(e)
                        atk_dmg = cur_p.profile.skills.get("j").damage if hasattr(cur_p, "profile") and "j" in cur_p.profile.skills else 15
                        hit_dir = 1 if cur_p.rect.centerx < e.rect.centerx else -1
                        if hasattr(e, "take_damage"):
                            try:
                                e.take_damage(atk_dmg, hit_direction=hit_dir)
                            except TypeError:
                                e.take_damage(atk_dmg)
                        # Shaia passive
                        if getattr(cur_p, "char_id", "") == "shaia":
                            cur_p.heal(1)
                            cur_p.mana = min(cur_p.max_mana, cur_p.mana + 2)

        # Update projectiles
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
                hit_something = False
                for e in self.enemies:
                    if not e.is_dead and e not in proj.hit_entities and proj.rect.colliderect(e.rect):
                        proj.hit_entities.add(e)
                        hit_dir = 1 if proj.velocity.x > 0 else -1
                        if hasattr(e, "take_damage"):
                            try:
                                e.take_damage(proj.damage, hit_direction=hit_dir)
                            except TypeError:
                                e.take_damage(proj.damage)
                        if getattr(proj, "is_burn", False) and hasattr(e, "apply_burn"):
                            e.apply_burn(4.0, 3.0)
                        if getattr(proj, "projectile_type", "") == "earth_spike" and hasattr(e, "apply_slow"):
                            e.apply_slow(1.8, 0.4)
                        if getattr(proj, "projectile_type", "") == "heal_orb":
                            for cur_p in active_players:
                                if not cur_p.is_dead:
                                    cur_p.health = min(cur_p.max_health, cur_p.health + 25)
                        elif getattr(proj, "projectile_type", "") == "mana_orb":
                            for cur_p in active_players:
                                if not cur_p.is_dead:
                                    cur_p.mana = min(cur_p.max_mana, cur_p.mana + 20.0)
                        if getattr(proj, "projectile_type", "") in ("holy_ray", "wind_blade") and len(proj.hit_entities) < 2:
                            hit_something = True
                        else:
                            proj.explode()
                            hit_something = True
                            break
                            
        # Update collectibles
        for c in self.collectibles:
            c.update(dt)
            if c.active:
                for cur_p in active_players:
                    if not cur_p.is_dead and cur_p.rect.colliderect(c.rect.inflate(-4, -4)):
                        c.collect(cur_p)
                        break
            
        # Camera Update
        if self.player2:
            self.camera.update_coop(self.player, self.player2, dt)
        else:
            self.camera.update(self.player.rect, dt)
        
        # Boss Defeat / Victory logic
        if getattr(self.boss, "is_dead", False):
            self.victory_timer += dt
            if self.victory_timer >= 2.5 and not self.victory:
                self.victory = True
                from engine.save_manager import SAVE
                SAVE.complete_stage(f"boss_{self.boss_type}")
                if self.boss_type == "demon_slime":
                    SAVE.unlock_world("sanguis")
                    SAVE.unlock_stage("sanguis_1")
                elif self.boss_type == "skeleton_king":
                    SAVE.unlock_world("glacies")
                    SAVE.unlock_stage("glacies_1")
                elif self.boss_type == "monster_creature":
                    SAVE.unlock_world("aetheria")
                    SAVE.unlock_stage("aetheria_1")
                elif self.boss_type == "samurai":
                    SAVE.unlock_world("umbra")
                    SAVE.unlock_stage("umbra_1")
                
                from scenes.story_select_scene import StorySelectScene
                from scenes.loading_scene import LoadingScene
                loading = LoadingScene(
                    self.scene_manager,
                    StorySelectScene(self.scene_manager),
                    title="GUARDIÃO DERROTADO!",
                    tip="O caminho foi aberto para o próximo reino das Ruínas!"
                )
                self.scene_manager.change_scene(loading)
                return

        # Death logic
        all_dead = self.player.is_dead and (self.player2 is None or self.player2.is_dead)
        if all_dead:
            if not self.death_screen.active:
                self.death_screen.start()
            death_action = self.death_screen.update(dt)
            if death_action == "retry":
                self.scene_manager.change_scene(BossScene(self.scene_manager, boss_type=self.boss_type))
                return
            elif death_action == "menu":
                from scenes.main_menu import MainMenuScene
                self.scene_manager.change_scene(MainMenuScene(self.scene_manager))
                return
            
    def _draw_swaying_banners(self, surface: pygame.Surface, cam_x: float, cam_y: float):
        """Draws royal fabric banners hanging from pillars swaying in the dungeon draught."""
        for idx, px in enumerate(self.pillar_x_coords):
            screen_px = px - cam_x
            if -80 <= screen_px <= self.arena_w + 80:
                top_y = 48 - cam_y
                banner_h = 115
                banner_w = 22
                # Sinusoidal cloth physics
                sway = math.sin(self.scene_time * 2.2 + idx * 1.3) * 5.0
                pts = [
                    (screen_px - banner_w // 2, top_y),
                    (screen_px + banner_w // 2, top_y),
                    (screen_px + banner_w // 2 + sway, top_y + banner_h),
                    (screen_px + sway, top_y + banner_h - 12),
                    (screen_px - banner_w // 2 + sway, top_y + banner_h)
                ]
                col_banner = (30, 20, 45) if self.active_arena_phase == 3 else ((120, 25, 25) if self.active_arena_phase >= 4 else (25, 55, 110))
                col_gold = (210, 170, 50)
                pygame.draw.polygon(surface, col_banner, pts)
                pygame.draw.lines(surface, col_gold, True, pts, 1)

    def draw(self, surface: pygame.Surface):
        self.arena_surf.fill((15, 15, 20))
        cam_x, cam_y = self.camera.offset.x, self.camera.offset.y
        
        # 1. Select and blit active Arena Phase Background
        boss_phase = self.boss.current_phase
        if boss_phase == 1:
            self.arena_surf.blit(self.bg_phase1, (-cam_x, -cam_y))
        elif boss_phase == 2:
            self.arena_surf.blit(self.bg_phase2, (-cam_x, -cam_y))
        elif boss_phase == 3:
            self.arena_surf.blit(self.bg_phase3, (-cam_x, -cam_y))
        else:
            self.arena_surf.blit(self.bg_phase4, (-cam_x, -cam_y))

        # 2. Draw Swaying Royal Banners
        self._draw_swaying_banners(self.arena_surf, cam_x, cam_y)

        # 3. Draw Water Ripples on Ground
        for r in self.ripples:
            r.draw(self.arena_surf, cam_x, cam_y)

        # 4. Y-Sort entities (Players, Boss, Minions, Environmental Rocks & Props)
        drawables = [p for p in [self.player, self.player2] if p] + self.props + getattr(self, "environmental_rocks", []) + [e for e in self.enemies if not getattr(e, "is_death_complete", False)]
        drawables.sort(key=lambda x: getattr(x, "y_sort_pivot", getattr(x, "ground_y", x.rect.bottom)))
        
        vl, vr = cam_x - 32, cam_x + self.arena_w + 32
        vt, vb = cam_y - 32, cam_y + self.arena_h + 32

        for d in drawables:
            r = d.rect
            if r.right >= vl and r.left <= vr and r.bottom >= vt and r.top <= vb:
                d.draw(self.arena_surf, self.camera.offset)
            
        # Draw Falling Droplets & Crumbling Debris
        for drop in self.droplets:
            dx = drop.x - cam_x
            dy = drop.y - cam_y
            if 0 <= dx <= self.arena_w and 0 <= dy <= self.arena_h:
                pygame.draw.line(self.arena_surf, drop.color, (dx, dy), (dx, dy + 6), 2)

        for p in self.falling_debris:
            px_scr = p.x - cam_x
            if -32 <= px_scr <= self.arena_w + 32:
                p.draw(self.arena_surf, cam_x, cam_y)

        # Draw Collectibles
        for c in self.collectibles:
            r = c.rect
            if r.right >= vl and r.left <= vr and r.bottom >= vt and r.top <= vb:
                c.draw(self.arena_surf, self.camera.offset)
            
        for p in self.projectiles:
            r = p.rect
            if r.right >= vl and r.left <= vr and r.bottom >= vt and r.top <= vb:
                p.draw(self.arena_surf, self.camera.offset)

            
        # 5. Dynamic Point Lights (Wall Torches, Projectiles, Boss Aura)
        lights = []
        torch_color = (135, 195, 245) if boss_phase == 1 else ((255, 180, 80) if boss_phase == 2 else ((190, 100, 245) if boss_phase == 3 else (255, 80, 40)))
        for px in self.pillar_x_coords:
            flicker = math.sin(self.scene_time * 5.5 + px) * 4.0
            lights.append(LightSource(px, 120, 74 + int(flicker), torch_color, 0.70, True))

        for p in self.projectiles:
            if getattr(p, "is_enemy", False):
                lights.append(LightSource(p.rect.centerx, p.rect.centery, 52, (255, 80, 40), 0.75, True))
            else:
                pal = getattr(p, "palette", None)
                color = getattr(pal, "inner_glow", (255, 140, 50))
                lights.append(LightSource(p.rect.centerx, p.rect.centery, 48, color, 0.75, True))
                
        # Boss Royal Aura Light
        if not self.boss.is_dead:
            aura_color = (255, 50, 30) if boss_phase >= 4 else ((190, 60, 255) if boss_phase == 3 else (100, 175, 235))
            lights.append(LightSource(self.boss.rect.centerx, self.boss.rect.centery, 95, aura_color, 0.70, True))
            
        for c in self.collectibles:
            lights.append(LightSource(c.rect.centerx, c.rect.centery, 34, (255, 80, 80), 0.55, True))

        # 6. Occluder geometries for 2D Soft Shadows (Pillars, Players, Boss, Enemies)
        occluders = []
        # Pillars cast deep architectural shadows
        for px in self.pillar_x_coords:
            occluders.extend([
                (px - 14, 90, px + 14, 90),
                (px + 14, self.FLOOR_BOTTOM_Y, px - 14, self.FLOOR_BOTTOM_Y),
                (px - 14, self.FLOOR_BOTTOM_Y, px - 14, 90),
                (px + 14, 90, px + 14, self.FLOOR_BOTTOM_Y)
            ])
            
        # Entities cast dynamic shadows
        for ent in [self.player, self.player2, self.boss] + [e for e in self.enemies if not e.is_dead]:
            if ent:
                er = ent.rect
                occluders.extend([
                    (er.left, er.top + 20, er.right, er.top + 20),
                    (er.right, er.bottom, er.left, er.bottom),
                    (er.left, er.bottom, er.left, er.top + 20),
                    (er.right, er.top + 20, er.right, er.bottom)
                ])
                
        # Render 2D Soft Shadows & Lighting Pass
        if occluders and lights:
            self.lighting.draw_shadows(self.arena_surf, lights, occluders, self.camera.offset)
        self.lighting.draw_point_lights(self.arena_surf, lights, self.camera.offset)


        self.lighting.draw_ambient_particles(self.arena_surf, self.camera.offset)
        
        # Color Grading
        grade_theme = "blood_moon" if boss_phase >= 4 else ("dungeon" if boss_phase <= 2 else "dungeon")
        self.lighting.apply_color_grading(self.arena_surf, grade_theme)
        self.lighting.draw_vignette(self.arena_surf)
        
        # Co-op Tether
        if self.player2:
            self.camera.draw_coop_overlay(self.arena_surf, self.player, self.player2)

        # Co-op Synergy Banners
        if self.synergy_system:
            self.synergy_system.draw_banners(self.arena_surf)
            
        # Present at native arena resolution (no lossy downscale) when the engine buffer matches
        if surface.get_size() == self.arena_surf.get_size():
            surface.blit(self.arena_surf, (0, 0))
        else:
            pygame.transform.smoothscale(self.arena_surf, surface.get_size(), surface)

        # Screen-space UI reads SETTINGS.GAME_WIDTH/HEIGHT; point it at the actual buffer meanwhile
        _gw, _gh = SETTINGS.GAME_WIDTH, SETTINGS.GAME_HEIGHT
        SETTINGS.GAME_WIDTH, SETTINGS.GAME_HEIGHT = surface.get_size()
        try:
            self._draw_overlays(surface)
        finally:
            SETTINGS.GAME_WIDTH, SETTINGS.GAME_HEIGHT = _gw, _gh

    def _draw_overlays(self, surface: pygame.Surface):
        
        # Ultimate Screen-Space overlays
        if self.player.is_casting_ultimate:
            self.player.ultimate_controller.draw_screen(surface)
        if self.player2 and self.player2.is_casting_ultimate:
            self.player2.ultimate_controller.draw_screen(surface)
        
        # HDR World Bloom
        if SETTINGS.RUIN_ENGINE_V3 and SETTINGS.BLOOM_ENABLED and ADAPTIVE_QUALITY.profile.bloom_passes > 0:
            self.bloom_engine.apply_bloom(surface, threshold=0.94, intensity=0.06)
        
        # Render HUD directly onto game surface (hidden during dialogue intro for cinematic immersion)
        if not (self.dialogue_box and not self.dialogue_box.is_finished):
            self.hud.draw(surface)
            if self.hud2:
                self.hud2.draw(surface)
        
        # Victory Overlay
        if self.victory:
            v_overlay = pygame.Surface((SETTINGS.GAME_WIDTH, SETTINGS.GAME_HEIGHT), pygame.SRCALPHA)
            v_overlay.fill((0, 0, 0, 160))
            surface.blit(v_overlay, (0, 0))
            
            v_text = self.font_victory.render("VITORIA! O CONFRONTO FOI VENCIDO!", True, (255, 220, 80))
            v_rect = v_text.get_rect(center=(SETTINGS.GAME_WIDTH // 2, SETTINGS.GAME_HEIGHT // 2 - 20))
            surface.blit(v_text, v_rect)
            
            sub_text = self.font_sub.render("Pressione qualquer botão para retornar ao menu...", True, (240, 240, 240))
            sub_rect = sub_text.get_rect(center=(SETTINGS.GAME_WIDTH // 2, SETTINGS.GAME_HEIGHT // 2 + 30))
            surface.blit(sub_text, sub_rect)
            
        # Death Screen Overlay
        if self.death_screen.active:
            self.death_screen.draw(surface)
        
        if self.paused:
            self.pause_menu.draw(surface)

        # Draw Retro Dialogue Box on top of HUD & Boss Overlays
        if self.dialogue_box and not self.dialogue_box.is_finished:
            self.dialogue_box.draw(surface)
