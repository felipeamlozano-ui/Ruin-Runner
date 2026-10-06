import pygame
from typing import List, Set
from engine.scene_manager import Scene
from engine.camera import Camera
from engine.input_manager import INPUT
from engine.save_manager import SAVE
from entities.player import Player
from entities.rock_obstacle import RockProp
from engine.v3.weather.clouds import CloudsManager
from ui.keyboard_overlay import KeyboardOverlay
from ui.hud import HUD

class TrainingDummy:
    """Boneco de treino resistente para testar combos e habilidades."""
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.max_hp = 9999
        self.hp = 9999
        self.rect = pygame.Rect(int(x - 16), int(y - 54), 32, 54)
        self.hit_flash = 0.0
        self.is_dead = False
        
    def take_damage(self, amount: int, knockback=(0, 0)):
        self.hit_flash = 0.22
        
    def update(self, dt: float):
        if self.hit_flash > 0:
            self.hit_flash -= dt

    def draw(self, surface: pygame.Surface, cam_offset: tuple):
        cam_x, cam_y = cam_offset
        dx = self.rect.x - cam_x
        dy = self.rect.y - cam_y
        
        # Ground contact shadow
        shadow_surf = pygame.Surface((34, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 95), (0, 0, 34, 10))
        surface.blit(shadow_surf, (dx - 1, dy + 48))

        # Draw wooden training post dummy
        color = (255, 230, 230) if self.hit_flash > 0 else (145, 95, 55)
        # Stand base flush on floor
        pygame.draw.rect(surface, (80, 50, 30), (dx + 4, dy + 48, 24, 6))
        # Body
        pygame.draw.rect(surface, color, (dx + 10, dy + 14, 12, 34), border_radius=2)
        # Arms crosspiece
        pygame.draw.rect(surface, color, (dx + 2, dy + 20, 28, 8), border_radius=2)
        # Straw Head
        pygame.draw.circle(surface, (200, 160, 90) if self.hit_flash <= 0 else (255, 255, 255), (dx + 16, dy + 10), 9)
        # Target mark
        pygame.draw.circle(surface, (180, 40, 40), (dx + 16, dy + 24), 4)

class TutorialScene(Scene):
    """Interactive Tutorial Scene with step-by-step guidance."""
    
    internal_size = (640, 360)
    
    def __init__(self, scene_manager, character: str = "knight"):
        self.scene_manager = scene_manager
        self.overlay = KeyboardOverlay()
        
        self.width = 640
        self.height = 360
        self.map_width = 1280
        
        # Standardized floor platform at y = 280
        self.floor_y = 280
        self.floor_rect = pygame.Rect(0, self.floor_y, self.map_width, 100)
        
        # Player setup
        self.player = Player(140, self.floor_y - 70, character_id=character)
        self.player.potions = 3
        self.player.health = 60
        self.dummy = TrainingDummy(380, self.floor_y)
        
        # Full skill HUD with health, mana, stamina & hotbar
        self.hud = HUD(self.player, stage_title="")
        
        # Camera
        self.camera = Camera(self.width, self.height)
        self.camera.world_width = self.map_width
        self.camera.world_height = self.height
        
        # Environment
        self.clouds = CloudsManager(theme="white", map_width=self.map_width, cloud_count=7)
        self.rocks = [
            RockProp(80, self.floor_y, biome="road", variant=1, scale=0.9),
            RockProp(520, self.floor_y, biome="road", variant=2, scale=1.1),
            RockProp(850, self.floor_y, biome="road", variant=3, scale=1.0),
        ]
        
        # Tutorial Steps & Event-driven transition state
        self.step = 1
        self.total_steps = 8
        self.step_timer = 0.0
        self.step_completed = False
        self.transition_timer = 0.0
        self.TRANSITION_DELAY = 0.75
        
        self.hits_landed = 0
        self.swings_count = 0
        self.has_jumped = False
        self.moved_left = False
        self.moved_right = False
        self.skip_hovered = False

    def _get_current_step_info(self) -> tuple:
        """Returns (active_keys_set, title, description)."""
        if self.step == 1:
            return ({"A", "D"}, "ETAPA 1: MOVIMENTAÇÃO BÁSICA", "Pressione [A] para ir à esquerda e [D] para ir à direita.")
        elif self.step == 2:
            return ({"SPACE"}, "ETAPA 2: SALTO & SALTO DUPLO", "Pressione [Espaço] para pular. Pressione no ar para Salto Duplo!")
        elif self.step == 3:
            return ({"J", "MOUSE_L"}, "ETAPA 3: COMBATE BÁSICO & COMBOS", "Aproxime-se do boneco e desfira 3 golpes com [J] ou Botão Esquerdo.")
        elif self.step == 4:
            return ({"K", "MOUSE_R"}, "ETAPA 4: HABILIDADE PRIMÁRIA (MAGIA)", "Dispare sua habilidade primária com [K] ou Botão Direito do Mouse.")
        elif self.step == 5:
            return ({"E"}, "ETAPA 5: GOLPE DE ÁREA (AoE)", "Liberte uma onda destruidora ao redor pressionando [E].")
        elif self.step == 6:
            return ({"SHIFT", "Q"}, "ETAPA 6: ESQUIVA RÁPIDA (DASH)", "Desvie de ataques com invulnerabilidade pressionando [Shift] ou [Q].")
        elif self.step == 7:
            return ({"1"}, "ETAPA 7: POÇÃO DE CURA ALQUÍMICA", "Recupere sua vida tomando uma poção alquímica pressionando [1].")
        elif self.step == 8:
            return ({"R", "Q"}, "ETAPA 8: DESPERTAR DO ULTIMATE", "Com energia arcana acumulada, liberte seu Poder Supremo usando [R]!")
        return (set(), "TREINAMENTO CONCLUÍDO!", "Parabéns! Você dominou todos os fundamentos do combate.")

    def _confirm_step(self):
        """Triggers the transition to the next step with smooth pacing."""
        if not self.step_completed:
            self.step_completed = True
            self.transition_timer = self.TRANSITION_DELAY

    def handle_events(self, events: list[pygame.event.Event]):
        mouse_pos = pygame.mouse.get_pos()
        gw, gh = self.width, self.height
        disp = pygame.display.get_surface()
        if disp:
            sw, sh = disp.get_size()
            scale_x = gw / max(1, sw)
            scale_y = gh / max(1, sh)
            virtual_mouse = (int(mouse_pos[0] * scale_x), int(mouse_pos[1] * scale_y))
        else:
            virtual_mouse = mouse_pos
        
        # Check skip button bounds (top right within banner)
        skip_rect = pygame.Rect(self.width - 144, 14, 126, 22)
        self.skip_hovered = skip_rect.collidepoint(virtual_mouse)

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_f):
                    self._complete_and_exit()
                    return
                
                # Ignore input triggers during transition delay
                if self.step_completed:
                    continue
                    
                # Step 1: Movement
                if self.step == 1:
                    if event.key in (pygame.K_a, pygame.K_LEFT):
                        self.moved_left = True
                    elif event.key in (pygame.K_d, pygame.K_RIGHT):
                        self.moved_right = True
                    if self.moved_left and self.moved_right:
                        self._confirm_step()
                # Step 2: Jump
                elif self.step == 2 and event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                    self._confirm_step()
                # Step 3: Combat [J]
                elif self.step == 3 and event.key in (pygame.K_j,):
                    self.swings_count += 1
                    if self.swings_count >= 3:
                        self._confirm_step()
                # Step 4: Skill [K]
                elif self.step == 4 and event.key in (pygame.K_k,):
                    self._confirm_step()
                # Step 5: AoE [E]
                elif self.step == 5 and event.key in (pygame.K_e,):
                    self._confirm_step()
                # Step 6: Dash [Shift / Q]
                elif self.step == 6 and event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_q):
                    self._confirm_step()
                # Step 7: Potion [1]
                elif self.step == 7 and event.key in (pygame.K_1, pygame.K_KP1):
                    self.player.start_drinking_potion(heal_amount=40)
                    self._confirm_step()
                # Step 8: Ultimate [R / Q / I]
                elif self.step == 8 and event.key in (pygame.K_r, pygame.K_q, pygame.K_i):
                    self.player.mana = self.player.max_mana
                    if hasattr(self.player, "cast_ultimate"):
                        self.player.cast_ultimate()
                    self._confirm_step()
                    
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if self.skip_hovered:
                        self._complete_and_exit()
                        return
                    elif self.step == 3 and not self.step_completed:
                        self.swings_count += 1
                        if self.swings_count >= 3:
                            self._confirm_step()
                elif event.button == 3 and self.step == 4 and not self.step_completed:
                    self._confirm_step()

    def _complete_and_exit(self):
        SAVE.set_tutorial_completed(True)
        if self.scene_manager:
            from scenes.main_menu import MainMenuScene
            self.scene_manager.change_scene(MainMenuScene(self.scene_manager))

    def update(self, dt: float):
        self.overlay.update(dt)
        self.clouds.update(dt)
        self.dummy.update(dt)
        
        self.player.update(dt, [self.floor_rect])
        self.camera.update(self.player.rect, dt)
        
        dummy_rect = self.dummy.rect
        
        # 1. Melee Hit Detection (safe get_attack_hitbox)
        p_atk_rect = self.player.get_attack_hitbox()
        if p_atk_rect and p_atk_rect.colliderect(dummy_rect):
            if self.dummy.hit_flash <= 0:
                dmg = getattr(self.player, "attack_power", 20)
                self.dummy.take_damage(dmg)
                self.hits_landed += 1

        # 2. Projectile Hit Detection
        for proj in self.player.projectiles[:]:
            if proj.rect.colliderect(dummy_rect):
                self.dummy.take_damage(proj.damage)
                self.player.projectiles.remove(proj)
                self.hits_landed += 1

        # 3. Transition Pacing
        if self.step_completed:
            self.transition_timer -= dt
            if self.transition_timer <= 0:
                self._advance_step()
            return

        # 4. Continuous Input & Game State Triggers
        keys = pygame.key.get_pressed()
        
        if self.step == 1:
            if keys[pygame.K_a] or self.player.input.is_action_pressed("LEFT"):
                self.moved_left = True
            if keys[pygame.K_d] or self.player.input.is_action_pressed("RIGHT"):
                self.moved_right = True
            if self.moved_left and self.moved_right:
                self._confirm_step()
                
        elif self.step == 2:
            if not self.player.on_ground or keys[pygame.K_SPACE] or self.player.input.is_action_just_pressed("JUMP"):
                self._confirm_step()
                
        elif self.step == 3:
            if self.hits_landed >= 3 or self.swings_count >= 3:
                self._confirm_step()
                
        elif self.step == 4:
            if keys[pygame.K_k] or self.player.input.is_action_just_pressed("SKILL") or self.player.is_casting_magic or len(self.player.projectiles) > 0:
                self._confirm_step()
                
        elif self.step == 5:
            if keys[pygame.K_e] or self.player.input.is_action_just_pressed("SKILL_AOE") or self.player.is_casting_aoe:
                self._confirm_step()
                
        elif self.step == 6:
            if keys[pygame.K_LSHIFT] or keys[pygame.K_q] or self.player.input.is_action_just_pressed("DASH") or self.player.is_dashing:
                self._confirm_step()
                
        elif self.step == 7:
            if keys[pygame.K_1] or keys[pygame.K_KP1] or self.player.is_drinking_potion or self.player.health > 60:
                self.player.mana = self.player.max_mana
                self._confirm_step()
                
        elif self.step == 8:
            if keys[pygame.K_r] or keys[pygame.K_q] or keys[pygame.K_i] or self.player.input.is_action_just_pressed("ULTIMATE") or self.player.is_casting_ultimate:
                self._confirm_step()

    def _advance_step(self):
        self.step += 1
        self.step_timer = 0.0
        self.step_completed = False
        self.hits_landed = 0
        self.swings_count = 0
        self.moved_left = False
        self.moved_right = False
        self.has_jumped = False
        
        # Replenish stamina & mana for the next tutorial task
        self.player.stamina = self.player.max_stamina
        self.player.mana = self.player.max_mana
        
        if self.step > self.total_steps:
            self._complete_and_exit()

    def draw(self, surface: pygame.Surface):
        # 1. Background gradient sky
        for y in range(0, self.floor_y, 4):
            c_factor = y / float(self.floor_y)
            r = int(30 + c_factor * 25)
            g = int(40 + c_factor * 35)
            b = int(70 + c_factor * 45)
            pygame.draw.rect(surface, (r, g, b), (0, y, self.width, 4))
            
        # 2. Clouds
        self.clouds.draw(surface, self.camera.offset, self.width, self.height)
        
        # 3. Ground / Training Platform
        cam_x, cam_y = self.camera.offset
        fl_y = self.floor_y - cam_y
        pygame.draw.rect(surface, (45, 52, 60), (0, fl_y, self.width, 100))
        pygame.draw.line(surface, (95, 110, 130), (0, fl_y), (self.width, fl_y), 2)
        # Flagstones
        for x in range(0, self.width + 64, 48):
            lx = (x - int(cam_x)) % (self.width + 48)
            pygame.draw.line(surface, (35, 42, 50), (lx, fl_y), (lx, fl_y + 100), 1)

        # 4. Y-Sorted Entities (Rocks, Dummy, Player)
        drawables = [
            *[(r.rect.bottom, r) for r in self.rocks],
            (self.dummy.rect.bottom, self.dummy),
            (self.player.rect.bottom, self.player)
        ]
        drawables.sort(key=lambda item: item[0])
        for _, entity in drawables:
            entity.draw(surface, self.camera.offset)
        
        # 5. Full Hero Skill HUD (Stats panel on top-left, skill hotbar on bottom-left)
        self.hud.draw(surface)
        
        # 6. Interactive Keyboard Overlay (Objective banner on top-right, keyboard on bottom-right)
        active_keys, title, desc = self._get_current_step_info()
        self.overlay.draw_hud(
            surface,
            active_keys,
            title,
            desc,
            self.step,
            self.total_steps,
            skip_hovered=self.skip_hovered,
            with_player_hud=True
        )

        # 7. Smooth Transition Banner when step is confirmed (Hollow Filigree Plaque)
        if self.step_completed:
            from ui.hollow_ui import HollowCrestRenderer, HollowFonts, HollowColors
            bw, bh = 310, 34
            bx = (self.width - bw) // 2
            by = 78
            plaque_rect = pygame.Rect(bx, by, bw, bh)
            HollowCrestRenderer.draw_filigree_panel(surface, plaque_rect, bg_color=(12, 34, 22, 235), border_color=(80, 225, 140), corner_flourish=True)
            
            font_trans = HollowFonts.get(12, bold=True)
            txt = font_trans.render("‹ ETAPA CONCLUÍDA! AVANÇANDO... ›", True, (240, 255, 245))
            surface.blit(txt, txt.get_rect(center=(self.width // 2, by + bh // 2)))
