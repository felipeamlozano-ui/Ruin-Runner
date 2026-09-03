import pygame
import os
from engine.scene_manager import Scene
from engine.camera import Camera
from entities.player import Player
from entities.boss import SkeletonBoss
from entities.enemy import Skeleton, MageSkeleton, WildBoar
from ui.hud import HUD
from ui.pause import PauseMenu
from engine.input_manager import INPUT
from config.settings import SETTINGS
from engine.lighting import LightingEngine, LightSource

class BossScene(Scene):
    def __init__(self, scene_manager):
        self.scene_manager = scene_manager
        
        # Backgrounds
        dungeon_bg_path = os.path.join("assets", "sprites", "background", "sprites_dungeon")
        self.bg_imgs = [
            pygame.image.load(os.path.join(dungeon_bg_path, "01_dungeon_left.png")).convert(),
            pygame.image.load(os.path.join(dungeon_bg_path, "02_dungeon_center.png")).convert(),
            pygame.image.load(os.path.join(dungeon_bg_path, "03_dungeon_right.png")).convert()
        ]
        
        # Arena map
        self.map_width = 1536
        self.camera = Camera(self.map_width, 384) 
        
        self.player = Player(180, 200)
        self.hud = HUD(self.player, stage_title="FASE 5: A SALA DO TRONO (CHEFE)")
        self.paused = False
        self.pause_menu = PauseMenu(self.scene_manager, self.unpause)
        self.death_timer = 0.0
        self.victory_timer = 0.0
        self.victory = False
        from ui.death_screen import DeathScreen
        self.death_screen = DeathScreen()
        self.lighting = LightingEngine(theme="dungeon")
        
        # Boss
        self.boss = SkeletonBoss(1000, 200)
        self.hud.active_boss = self.boss
        
        self.enemies = [self.boss]
        self.collectibles = []
        self.traps = []
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
            pygame.FRect(0, 340, self.map_width, 50),
            pygame.FRect(-100, 0, 215, 400),
            pygame.FRect(self.map_width - 120, 0, 200, 400)
        ]
        
        self.player.update(dt, solid_rects)
        self.player.trigger_aoe_damage(self.enemies, self.camera)
        
        # Check if boss dropped healing potions
        while self.boss.potions_to_spawn:
            px, py = self.boss.potions_to_spawn.pop(0)
            from entities.collectible import Collectible
            self.collectibles.append(Collectible(px, py, "potion", is_dropped=True))
            
        # Check if boss wants to spawn minions
        while self.boss.minions_to_spawn:
            m_type, mx = self.boss.minions_to_spawn.pop(0)
            if m_type == "mage":
                self.enemies.append(MageSkeleton(mx, 200))
            elif m_type == "boar":
                self.enemies.append(WildBoar(mx, 200))
            else:
                self.enemies.append(Skeleton(mx, 200))
        
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
            
            # Simple Combat Logic (Melee / Body)
            if not self.player.is_dashing and not self.player.is_casting_ultimate and not e.is_dead:
                attack_hitbox = getattr(e, "get_attack_hitbox", lambda: None)()
                if attack_hitbox and attack_hitbox.colliderect(self.player.rect):
                    self.player.take_damage(1)
                elif e != self.boss and e.rect.colliderect(self.player.rect):
                    self.player.take_damage(1)
                
        # Player attacking enemies (Melee)
        p_hitbox = self.player.get_attack_hitbox()
        if p_hitbox:
            for e in self.enemies:
                if not e.is_dead and p_hitbox.colliderect(e.rect):
                    if getattr(e, "state", "") != "HURT":
                        e.take_damage(2)
                        
        # Update projectiles
        for proj in self.projectiles[:]:
            proj.update(dt, solid_rects)
            if not proj.active:
                self.projectiles.remove(proj)
                continue
                
            if proj.is_enemy:
                if not self.player.is_dashing and not self.player.is_casting_ultimate and proj.rect.colliderect(self.player.rect):
                    self.player.take_damage(proj.damage)
                    proj.explode()
            else:
                for e in self.enemies:
                    if not e.is_dead and proj.rect.colliderect(e.rect):
                        if getattr(e, "state", "") != "HURT":
                            e.take_damage(proj.damage)
                        proj.explode()
                        break
                        
        # Update collectibles (Healing potions dropped by boss)
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
        # Clear screen
        surface.fill((20, 20, 20))
        
        # Draw Clean Dungeon Arena Background
        surface.blit(self.bg_imgs[0], (0 - self.camera.offset.x, 0 - self.camera.offset.y))
        surface.blit(self.bg_imgs[1], (512 - self.camera.offset.x, 0 - self.camera.offset.y))
        surface.blit(self.bg_imgs[2], (1024 - self.camera.offset.x, 0 - self.camera.offset.y))
        
        # Y-Sort entities
        drawables = [self.player] + self.props + [e for e in self.enemies if not (e.is_dead and e.anim_manager.is_finished("dead"))]
        drawables.sort(key=lambda x: x.rect.bottom)
        
        for d in drawables:
            d.draw(surface, self.camera.offset)
            
        # Draw Collectibles (Potions)
        for c in self.collectibles:
            c.draw(surface, self.camera.offset)
            
        for p in self.projectiles:
            p.draw(surface, self.camera.offset)
            
        # Dynamic Point Lights
        lights = []
        for p in self.projectiles:
            if getattr(p, "is_enemy", False):
                if getattr(p, "projectile_type", "") == "mage_fireball":
                    lights.append(LightSource(p.rect.centerx, p.rect.centery, 55, (190, 70, 255), 0.9, True))
                else:
                    lights.append(LightSource(p.rect.centerx, p.rect.centery, 65, (60, 160, 255), 0.9, True))
            else:
                lights.append(LightSource(p.rect.centerx, p.rect.centery, 55, (255, 130, 50), 0.9, True))
                
        # Boss Royal Aura
        if not self.boss.is_dead:
            lights.append(LightSource(self.boss.rect.centerx, self.boss.rect.centery, 95, (60, 150, 255), 0.75, True))
            
        # Player Celestial Aura when 100 MP
        if self.player.mana >= 100 and not self.player.is_dead:
            lights.append(LightSource(self.player.rect.centerx, self.player.rect.centery, 50, (255, 220, 100), 0.40, True))
            
        for c in self.collectibles:
            lights.append(LightSource(c.rect.centerx, c.rect.centery, 35, (255, 80, 80), 0.55, True))
            
        # Render Point Lights, Atmospheric Embers & Vignette
        self.lighting.draw_point_lights(surface, lights, self.camera.offset)
        self.lighting.draw_ambient_particles(surface, self.camera.offset)
        self.lighting.draw_vignette(surface)
            
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
