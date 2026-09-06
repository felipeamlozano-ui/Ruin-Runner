import pygame
import os
from engine.scene_manager import Scene
from engine.camera import Camera
from entities.player import Player
from entities.boss import SkeletonBoss
from entities.enemy import Skeleton, MageSkeleton, WildBoar
from entities.prop import Prop
from entities.collectible import Collectible
from ui.hud import HUD
from ui.pause import PauseMenu
from engine.input_manager import INPUT
from config.settings import SETTINGS
from engine.lighting import LightingEngine, LightSource

class BossScene(Scene):
    def __init__(self, scene_manager):
        self.scene_manager = scene_manager
        
        # Virtual Arena Resolution (1.25x Wider FOV camera zoom-out)
        self.arena_w = 640
        self.arena_h = 480
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
        
        # Phase 1 Background: Normal Throne Room
        self.bg_phase1 = pygame.Surface((self.map_width, self.arena_h))
        self.bg_phase1.blit(bg_left, (0, 0))
        self.bg_phase1.blit(bg_center, (512, 0))
        self.bg_phase1.blit(bg_center, (1024, 0))
        self.bg_phase1.blit(bg_center, (1536, 0))
        self.bg_phase1.blit(bg_right, (2048, 0))
        
        # Phase 2 Background: Blood Moon & Magma Fissure Arena
        self.bg_phase2 = self.bg_phase1.copy()
        tint_surf = pygame.Surface((self.map_width, self.arena_h), pygame.SRCALPHA)
        tint_surf.fill((160, 25, 20, 100))
        self.bg_phase2.blit(tint_surf, (0, 0))
        
        # Blood Moon in sky
        moon_cx, moon_cy = 1280, 105
        pygame.draw.circle(self.bg_phase2, (255, 60, 40), (moon_cx, moon_cy), 65)
        pygame.draw.circle(self.bg_phase2, (210, 25, 25), (moon_cx, moon_cy), 56)
        pygame.draw.circle(self.bg_phase2, (255, 120, 80), (moon_cx, moon_cy), 76, 4)
        
        # Magma Floor Fissures along ground level (Y = 422 - 435)
        for fx in range(60, self.map_width - 80, 130):
            pts = [(fx, 423), (fx + 25, 427), (fx + 55, 422), (fx + 85, 428), (fx + 110, 423)]
            pygame.draw.lines(self.bg_phase2, (255, 170, 30), False, pts, 3)
            pygame.draw.lines(self.bg_phase2, (255, 60, 20), False, pts, 5)

        # Dynamic Phase 2 State
        self.phase_transition = 0.0
        self.phase2_triggered = False

        # Player & Entities
        self.player = Player(180, 320)
        self.hud = HUD(self.player, stage_title="FASE 5: A SALA DO TRONO (CHEFE)")
        self.paused = False
        self.pause_menu = PauseMenu(self.scene_manager, self.unpause)
        self.death_timer = 0.0
        self.victory_timer = 0.0
        self.victory = False
        from ui.death_screen import DeathScreen
        self.death_screen = DeathScreen()
        self.lighting = LightingEngine(theme="dungeon")
        
        # Boss (Spawned deep in the 2560px throne arena)
        self.boss = SkeletonBoss(1550, 300)
        self.hud.active_boss = self.boss
        
        self.enemies = [self.boss]
        self.collectibles = []
        self.traps = []
        # No props or barrels on the boss arena floor as requested
        self.props = []
        self.projectiles = []
        
        pygame.font.init()
        self.font_victory = pygame.font.SysFont("Arial", 36, bold=True)
        self.font_sub = pygame.font.SysFont("Arial", 16, bold=True)
        
    def unpause(self):
        self.paused = False
        
    def handle_events(self, events: list[pygame.event.Event]) -> None:
        pass
        
    def update(self, dt: float):
        if INPUT.is_action_just_pressed("PAUSE"):
            self.paused = not self.paused
            
        if self.paused:
            self.pause_menu.update()
            return

        self.lighting.update(dt)

        solid_rects = [
            pygame.FRect(0, 425, self.map_width, 60),       # Floor
            pygame.FRect(-100, 0, 215, 500),                # Left wall
            pygame.FRect(self.map_width - 120, 0, 200, 500) # Right wall
        ]
        
        self.player.update(dt, solid_rects, self.enemies, self.camera)
        self.player.trigger_aoe_damage(self.enemies, self.camera)
        
        # Check Dynamic Phase 2 Trigger at 10,000 HP = 50% (Enraged Arena Shift)
        if self.boss.health <= 10000 and not self.boss.is_dead:
            if not self.phase2_triggered:
                self.phase2_triggered = True
                self.camera.shake(9.5, 1.4)
            self.phase_transition = min(1.0, self.phase_transition + dt / 1.5)

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
            if m_type == "mage":
                self.enemies.append(MageSkeleton(spawn_x, 320))
            elif m_type == "boar":
                self.enemies.append(WildBoar(spawn_x, 320))
            else:
                self.enemies.append(Skeleton(spawn_x, 320))
        
        # Check Victory
        if self.boss.is_dead and self.boss.anim_manager.is_finished("dead"):
            self.victory = True
            self.victory_timer += dt
            if self.victory_timer > 5.0 or INPUT.is_action_just_pressed("ATTACK") or INPUT.is_action_just_pressed("JUMP"):
                from scenes.main_menu import MainMenuScene
                self.scene_manager.change_scene(MainMenuScene(self.scene_manager))
                return
        
        # Grab player projectiles
        while self.player.projectiles:
            self.projectiles.append(self.player.projectiles.pop(0))
            
        for e in self.enemies:
            e.update(dt, solid_rects, self.player)
            if hasattr(e, "projectiles"):
                while e.projectiles:
                    self.projectiles.append(e.projectiles.pop(0))
            
            # Combat Logic (Melee / Body)
            if not self.player.is_dashing and not self.player.is_casting_ultimate and not e.is_dead:
                attack_hitbox = getattr(e, "get_attack_hitbox", lambda: None)()
                if attack_hitbox and attack_hitbox.colliderect(self.player.rect):
                    atk_dmg = getattr(e, "attack_damage", 35 if e == self.boss else 4)
                    self.player.take_damage(atk_dmg)
                elif e.rect.colliderect(self.player.rect):
                    touch_dmg = getattr(e, "touch_damage", 0 if e == self.boss else 2)
                    if touch_dmg > 0:
                        self.player.take_damage(touch_dmg)
                
        # Player attacking enemies (Melee - at most 1 hit per attack swing)
        p_hitbox = self.player.get_attack_hitbox()
        if p_hitbox:
            for e in self.enemies:
                if not e.is_dead and p_hitbox.colliderect(e.rect) and e not in self.player.attack_hit_enemies:
                    self.player.attack_hit_enemies.add(e)
                    atk_dmg = self.player.profile.skills.get("j").damage if hasattr(self.player, "profile") and "j" in self.player.profile.skills else 15
                    e.take_damage(atk_dmg)
                    # Shaia passive: Heal 1 HP and 2 MP on hit
                    if getattr(self.player, "char_id", "") == "shaia":
                        self.player.heal(1)
                        self.player.mana = min(self.player.max_mana, self.player.mana + 2)
            # Player melee hitting destructible props (2 hits to break)
            for prop in self.props:
                if prop.active and p_hitbox.colliderect(prop.rect) and prop not in self.player.attack_hit_enemies:
                    self.player.attack_hit_enemies.add(prop)
                    prop.take_damage(1, is_skill=False)

        # Player AoE skill hitting props (instant break)
        if self.player.is_casting_aoe and not self.player.aoe_hit_done:
            for prop in self.props:
                if prop.active:
                    dist = pygame.math.Vector2(prop.rect.center).distance_to(pygame.math.Vector2(self.player.rect.center))
                    if dist <= self.player.aoe_radius:
                        prop.take_damage(999, is_skill=True)
                        
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
                hit_something = False
                for e in self.enemies:
                    if not e.is_dead and e not in proj.hit_entities and proj.rect.colliderect(e.rect):
                        proj.hit_entities.add(e)
                        e.take_damage(proj.damage)
                        # Ignis burn application
                        if getattr(proj, "is_burn", False) and hasattr(e, "apply_burn"):
                            e.apply_burn(4.0, 3.0)
                        proj.explode()
                        hit_something = True
                        break
                if not hit_something:
                    # Player projectiles hitting props (instant break)
                    for prop in self.props:
                        if prop.active and prop not in proj.hit_entities and proj.rect.colliderect(prop.rect):
                            proj.hit_entities.add(prop)
                            prop.take_damage(999, is_skill=True)
                            proj.explode()
                            break
                        
        # Update collectibles (Healing potions)
        for c in self.collectibles:
            c.update(dt)
            if c.active and self.player.rect.colliderect(c.rect.inflate(-4, -4)):
                c.collect(self.player)
            
        self.camera.update(self.player.rect, dt)
        
        # Death logic with DeathScreen
        if self.player.health <= 0:
            if not self.death_screen.active:
                self.death_screen.start()
            death_action = self.death_screen.update(dt)
            if death_action == "retry":
                self.scene_manager.change_scene(BossScene(self.scene_manager))
                return
            elif death_action == "menu":
                from scenes.main_menu import MainMenuScene
                self.scene_manager.change_scene(MainMenuScene(self.scene_manager))
                return
            
    def draw(self, surface: pygame.Surface):
        # Clear arena virtual surface
        self.arena_surf.fill((20, 20, 20))
        cam_x, cam_y = self.camera.offset.x, self.camera.offset.y
        
        # 1. Draw Phase 1 Dungeon Arena Background
        self.arena_surf.blit(self.bg_phase1, (-cam_x, -cam_y))
        
        # 2. Dynamic Phase 2 Cross-fade (Blood Moon & Magma Fissures)
        if self.phase_transition > 0:
            self.bg_phase2.set_alpha(int(255 * self.phase_transition))
            self.arena_surf.blit(self.bg_phase2, (-cam_x, -cam_y))
        
        # 3. Y-Sort entities (Props, Boss, Minions, Player)
        drawables = [self.player] + self.props + [e for e in self.enemies if not (e.is_dead and e.anim_manager.is_finished("dead"))]
        drawables.sort(key=lambda x: x.rect.bottom)
        
        for d in drawables:
            d.draw(self.arena_surf, self.camera.offset)
            
        # Draw Collectibles (Potions)
        for c in self.collectibles:
            c.draw(self.arena_surf, self.camera.offset)
            
        for p in self.projectiles:
            p.draw(self.arena_surf, self.camera.offset)
            
        # Dynamic Point Lights
        lights = []
        for p in self.projectiles:
            if getattr(p, "is_enemy", False):
                lights.append(LightSource(p.rect.centerx, p.rect.centery, 65, (255, 80, 40), 0.9, True))
            else:
                lights.append(LightSource(p.rect.centerx, p.rect.centery, 55, (255, 140, 50), 0.9, True))
                
        # Boss Royal / Enraged Aura
        if not self.boss.is_dead:
            aura_color = (255, 50, 30) if self.boss.enraged else (80, 180, 255)
            lights.append(LightSource(self.boss.rect.centerx, self.boss.rect.centery, 110, aura_color, 0.8, True))
            
        # Player Aura
        if not self.player.is_dead:
            lights.append(LightSource(self.player.rect.centerx, self.player.rect.centery, 50, (255, 230, 140), 0.45, True))
            
        for c in self.collectibles:
            lights.append(LightSource(c.rect.centerx, c.rect.centery, 35, (255, 80, 80), 0.55, True))
            
        # Render Point Lights, Atmospheric Embers & Vignette onto arena surface
        self.lighting.draw_point_lights(self.arena_surf, lights, self.camera.offset)
        self.lighting.draw_ambient_particles(self.arena_surf, self.camera.offset)
        self.lighting.draw_vignette(self.arena_surf)
            
        # 4. Smoothscale arena surface (640x480) down to native game surface (512x384) for wide FOV zoom-out
        pygame.transform.smoothscale(self.arena_surf, (SETTINGS.GAME_WIDTH, SETTINGS.GAME_HEIGHT), surface)
        
        # 4b. Ultimate Screen-Space overlays (flash, vignette) must be drawn AFTER scale onto game surface
        if self.player.is_casting_ultimate:
            self.player.ultimate_controller.draw_screen(surface)
        
        # 5. Render HUD and Overlays directly onto game surface (unscaled, crisp 512x384 presentation)
        self.hud.draw(surface)
        
        # Victory Overlay
        if self.victory:
            v_overlay = pygame.Surface((SETTINGS.GAME_WIDTH, SETTINGS.GAME_HEIGHT), pygame.SRCALPHA)
            v_overlay.fill((0, 0, 0, 160))
            surface.blit(v_overlay, (0, 0))
            
            v_text = self.font_victory.render("👑 VITÓRIA! O REI FOI DERROTADO! 👑", True, (255, 220, 80))
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
