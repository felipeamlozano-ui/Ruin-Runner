import pygame
import math
import os
import random
from config.settings import SETTINGS
from config.colors import WHITE, GOLD, RED, BLUE, GREEN, GRAY, UI_BACKGROUND
from engine.scene_manager import Scene
from engine.input_manager import INPUT
from entities.player import Player
from entities.character_data import CHARACTER_REGISTRY, CHARACTER_ORDER, get_character_profile
from ui.hollow_ui import HollowFonts, HollowCrestRenderer, AtmosphereFX, HollowColors

class CharacterSelectScene(Scene):
    """
    AAA Character Selection & Interactive Dojo Scene.
    Calibrated for native 512x384 resolution with zero clipping.
    Supports both Solo mode (Interactive Dojo + 2-Row Compact Grid + Full Dossier)
    and Co-op mode (Split-Screen Dual Selector with Independent Pedestals & Synchronized Ready).
    """

    def __init__(self, scene_manager, previous_scene=None):
        self.scene_manager = scene_manager
        self.previous_scene = previous_scene
        
        # Load fonts via HollowFonts cache
        pygame.font.init()
        self.font_title = HollowFonts.get(18, bold=True)
        self.font_name = HollowFonts.get(14, bold=True)
        self.font_subtitle = HollowFonts.get(10)
        self.font_body = HollowFonts.get(9)
        self.font_stat = HollowFonts.get(9, bold=True)
        self.font_key = HollowFonts.get(9, bold=True)
        self.font_banner = HollowFonts.get(9)
        self.font_desc = HollowFonts.get(9, italic=True)
        self.font_badge = HollowFonts.get(8, bold=True)
        
        # Atmospheric VFX
        self.fx = AtmosphereFX(width=512, height=384, theme="void" if not getattr(SETTINGS, "COOP_ENABLED", False) else "ember", particle_count=36)
        
        # Mode detection
        self.coop_mode = getattr(SETTINGS, "COOP_ENABLED", False)
        
        # Solo selection
        cur_id = getattr(SETTINGS, "CURRENT_CHARACTER", "shaia")
        self.selected_index = CHARACTER_ORDER.index(cur_id) if cur_id in CHARACTER_ORDER else 0
        
        # Co-op dual selections
        p2_id = getattr(SETTINGS, "P2_CHARACTER", "lunaria")
        self.p1_selected_index = self.selected_index
        self.p2_selected_index = CHARACTER_ORDER.index(p2_id) if p2_id in CHARACTER_ORDER else 1
        self.p1_ready = False
        self.p2_ready = False
        self.both_ready_timer = 0.0
        
        # Pedestal positions
        self.pedestal_pos = pygame.math.Vector2(126, 175) # Solo left dais
        self.p1_pedestal_pos = pygame.math.Vector2(128, 140) # Co-op P1 dais
        self.p2_pedestal_pos = pygame.math.Vector2(384, 140) # Co-op P2 dais
        
        self.dummy_tiles = [
            pygame.FRect(20, 180, 212, 40)
        ]
        self.coop_dummy_tiles = [
            pygame.FRect(20, 145, 216, 40),
            pygame.FRect(276, 145, 216, 40)
        ]
        
        # Ambient particles
        self.ambient_particles = []
        for _ in range(24):
            self.ambient_particles.append({
                "x": random.uniform(10, 502),
                "y": random.uniform(30, 360),
                "speed": random.uniform(14, 34),
                "size": random.uniform(1.2, 2.8),
                "alpha": random.randint(70, 200)
            })
            
        # Skill Icons cache
        self.skill_icons = {}
        self._load_skill_icons()
        
        # Thumbnail portraits cache
        self.thumbnails = {}
        self._load_thumbnails()
        
        # Move tester feedback (Solo mode)
        self.last_tested_action = "DOJO: Pressione [J], [K], [E], [Shift], [Q], [R] para testar!"
        self.banner_timer = 4.0
        self.active_test_key = None
        self.test_key_timer = 0.0
        
        # Buttons for mouse clicks
        self.btn_left_rect = pygame.FRect(10, 126, 20, 32)
        self.btn_right_rect = pygame.FRect(222, 126, 20, 32)
        self.btn_back_rect = pygame.FRect(250, 332, 108, 30)
        self.btn_play_rect = pygame.FRect(368, 332, 134, 30)
        
        # Co-op buttons
        self.btn_coop_back_rect = pygame.FRect(16, 348, 96, 26)
        self.btn_coop_start_rect = pygame.FRect(380, 348, 116, 26)
        
        # Instantiate preview players
        self._spawn_preview_player()
        if self.coop_mode:
            self._spawn_coop_players()

    def _load_thumbnails(self):
        """Loads and caches authentic 24x24 character portraits with zero distortion."""
        for cid in CHARACTER_ORDER:
            prof = CHARACTER_REGISTRY[cid]
            try:
                # 1. Check if dedicated portrait.png exists
                p_port = os.path.join(prof.base_folder, "portrait.png")
                if os.path.exists(p_port):
                    raw = pygame.image.load(p_port).convert_alpha()
                    self.thumbnails[cid] = pygame.transform.smoothscale(raw, (24, 24))
                    continue
                    
                # 2. Check for craftpix or folder Idle frame
                if prof.sprite_type == "folder":
                    p = os.path.join(prof.base_folder, "common_00_idle_stand_A_000.png")
                    if os.path.exists(p):
                        raw = pygame.image.load(p).convert_alpha()
                        sub = raw.subsurface((raw.get_width() // 2 - 24, 10, 48, 48))
                        self.thumbnails[cid] = pygame.transform.smoothscale(sub, (24, 24))
                else:
                    p = os.path.join(prof.base_folder, "Idle.png")
                    if os.path.exists(p):
                        raw = pygame.image.load(p).convert_alpha()
                        fw, fh = prof.frame_size
                        frame = raw.subsurface((0, 0, fw, fh))
                        sub = frame.subsurface((fw // 2 - 24, 24 if prof.archetype in ("mage", "healer", "support") else 20, 48, 48))
                        self.thumbnails[cid] = pygame.transform.smoothscale(sub, (24, 24))
            except Exception:
                self.thumbnails[cid] = None

    def _load_skill_icons(self):
        """Loads and caches skill icons scaled to 18x18 for preview cards."""
        icons_dir = os.path.join("assets", "sprites", "icons", "skills")
        if not os.path.exists(icons_dir):
            icons_dir = os.path.join("assets", "sprites", "fantasy_skills", "64x64")
            
        for cid in CHARACTER_ORDER:
            prof = CHARACTER_REGISTRY[cid]
            for skey, sdata in prof.skills.items():
                if sdata.icon_file not in self.skill_icons:
                    p = os.path.join(icons_dir, sdata.icon_file)
                    if os.path.exists(p):
                        img = pygame.image.load(p).convert_alpha()
                        self.skill_icons[sdata.icon_file] = pygame.transform.smoothscale(img, (18, 18))
                    else:
                        self.skill_icons[sdata.icon_file] = None

    def _spawn_preview_player(self):
        """Spawns or switches the interactive preview player on the pedestal (Solo mode)."""
        cid = CHARACTER_ORDER[self.selected_index]
        self.profile = get_character_profile(cid)
        self.player = Player(self.pedestal_pos.x - 16, self.pedestal_pos.y - 75, character_id=cid)
        self.player.mana = self.player.max_mana
        self.player.stamina = self.player.max_stamina
        self.player.facing_right = True

    def _spawn_coop_players(self):
        """Spawns or switches both interactive preview players (Co-op mode)."""
        p1_cid = CHARACTER_ORDER[self.p1_selected_index]
        self.p1_profile = get_character_profile(p1_cid)
        self.p1_player = Player(self.p1_pedestal_pos.x - 16, self.p1_pedestal_pos.y - 70, character_id=p1_cid, player_index=0)
        self.p1_player.mana = self.p1_player.max_mana
        self.p1_player.stamina = self.p1_player.max_stamina
        self.p1_player.facing_right = True
        
        p2_cid = CHARACTER_ORDER[self.p2_selected_index]
        self.p2_profile = get_character_profile(p2_cid)
        self.p2_player = Player(self.p2_pedestal_pos.x - 16, self.p2_pedestal_pos.y - 70, character_id=p2_cid, player_index=1)
        self.p2_player.mana = self.p2_player.max_mana
        self.p2_player.stamina = self.p2_player.max_stamina
        self.p2_player.facing_right = False

    def _select_character(self, index: int):
        """Switches the selected character and refreshes preview (Solo mode)."""
        self.selected_index = index % len(CHARACTER_ORDER)
        self._spawn_preview_player()
        self.last_tested_action = f"Personagem: {self.profile.name} ({self.profile.title})"
        self.banner_timer = 2.5

    def _select_p1_character(self, index: int):
        """Moves P1 selection in Co-op mode."""
        if self.p1_ready:
            return
        self.p1_selected_index = index % len(CHARACTER_ORDER)
        self._spawn_coop_players()

    def _select_p2_character(self, index: int):
        """Moves P2 selection in Co-op mode."""
        if self.p2_ready:
            return
        self.p2_selected_index = index % len(CHARACTER_ORDER)
        self._spawn_coop_players()

    def _confirm_and_play(self):
        """Saves selected character(s) to settings and enters the game."""
        if self.coop_mode:
            p1_cid = CHARACTER_ORDER[self.p1_selected_index]
            p2_cid = CHARACTER_ORDER[self.p2_selected_index]
            SETTINGS.CURRENT_CHARACTER = p1_cid
            SETTINGS.P2_CHARACTER = p2_cid
        else:
            cid = CHARACTER_ORDER[self.selected_index]
            SETTINGS.CURRENT_CHARACTER = cid
            
        from scenes.loading_scene import LoadingScene
        if SETTINGS.DEV_MODE and SETTINGS.DEV_START_BOSS:
            from scenes.boss_scene import BossScene
            boss_scene = BossScene(self.scene_manager)
            loading = LoadingScene(
                self.scene_manager,
                boss_scene,
                title="SALA DO BOSS: O REI ESQUELETO",
                tip="Modo Dev Ativo: Iniciando confronto diretamente na sala do Boss!"
            )
            self.scene_manager.change_scene(loading)
        else:
            from scenes.level_scene import LevelScene
            lvl1 = LevelScene(stage=1, scene_manager=self.scene_manager)
            loading = LoadingScene(
                self.scene_manager,
                lvl1,
                title="FASE 1: AS CATACUMBAS",
                tip="Co-op: Trabalhem em equipe! Mantenham-se próximos para bônus de passivas e revives!"
            )
            self.scene_manager.change_scene(loading)

    def _go_back(self):
        """Returns to previous scene or main menu safely."""
        if self.previous_scene:
            self.scene_manager.change_scene(self.previous_scene)
        else:
            from scenes.main_menu import MainMenuScene
            self.scene_manager.change_scene(MainMenuScene(self.scene_manager))

    def handle_events(self, events: list[pygame.event.Event]):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self.coop_mode:
                    self._handle_coop_keydown(event)
                else:
                    self._handle_solo_keydown(event)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if self.coop_mode:
                    self._handle_coop_mouse(mx, my)
                else:
                    self._handle_solo_mouse(mx, my)

    def _handle_solo_keydown(self, event: pygame.event.Event):
        if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self._go_back()
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._confirm_and_play()
        elif event.key in (pygame.K_LEFT, pygame.K_a):
            self._select_character(self.selected_index - 1)
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self._select_character(self.selected_index + 1)
        elif event.key in (pygame.K_UP, pygame.K_w):
            # Jump between row 1 and row 2 (6 items per row)
            if self.selected_index >= 6:
                self._select_character(self.selected_index - 6)
            else:
                target = min(len(CHARACTER_ORDER) - 1, self.selected_index + 6)
                self._select_character(target)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            if self.selected_index < 6:
                target = min(len(CHARACTER_ORDER) - 1, self.selected_index + 6)
                self._select_character(target)
            else:
                self._select_character(self.selected_index - 6)
                
        # Interactive Dojo Keys
        elif event.key == pygame.K_j:
            self._trigger_dojo_move("j")
        elif event.key == pygame.K_k:
            self._trigger_dojo_move("k")
        elif event.key == pygame.K_e:
            self._trigger_dojo_move("e")
        elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
            self._trigger_dojo_move("shift")
        elif event.key == pygame.K_q:
            self._trigger_dojo_move("q")
        elif event.key == pygame.K_r:
            self._trigger_dojo_move("r")
        elif event.key == pygame.K_SPACE:
            self._trigger_dojo_move("space")

    def _handle_solo_mouse(self, mx: int, my: int):
        if self.btn_left_rect.collidepoint(mx, my):
            self._select_character(self.selected_index - 1)
        elif self.btn_right_rect.collidepoint(mx, my):
            self._select_character(self.selected_index + 1)
        elif self.btn_play_rect.collidepoint(mx, my):
            self._confirm_and_play()
        elif self.btn_back_rect.collidepoint(mx, my):
            self._go_back()
        else:
            # Check 2-row compact grid click
            for idx in range(len(CHARACTER_ORDER)):
                r = self._get_solo_card_rect(idx)
                if r.collidepoint(mx, my):
                    self._select_character(idx)
                    break

    def _handle_coop_keydown(self, event: pygame.event.Event):
        # Global Back / Start
        if event.key == pygame.K_ESCAPE:
            if self.p1_ready or self.p2_ready:
                self.p1_ready = False
                self.p2_ready = False
            else:
                self._go_back()
            return
            
        if self.p1_ready and self.p2_ready:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self._confirm_and_play()
                return

        # Player 1 Controls: WASD + J (Ready) + K (Cancel)
        if not self.p1_ready:
            if event.key == pygame.K_a:
                self._select_p1_character(self.p1_selected_index - 1)
            elif event.key == pygame.K_d:
                self._select_p1_character(self.p1_selected_index + 1)
            elif event.key == pygame.K_w or event.key == pygame.K_s:
                if self.p1_selected_index < 6:
                    target = min(len(CHARACTER_ORDER) - 1, self.p1_selected_index + 6)
                else:
                    target = self.p1_selected_index - 6
                self._select_p1_character(target)
            elif event.key in (pygame.K_j, pygame.K_SPACE):
                self.p1_ready = True
        else:
            if event.key in (pygame.K_k, pygame.K_BACKSPACE):
                self.p1_ready = False

        # Player 2 Controls: Arrow Keys + Numpad 1 / Enter (Ready) + Numpad 2 / Backspace (Cancel)
        if not self.p2_ready:
            if event.key == pygame.K_LEFT:
                self._select_p2_character(self.p2_selected_index - 1)
            elif event.key == pygame.K_RIGHT:
                self._select_p2_character(self.p2_selected_index + 1)
            elif event.key == pygame.K_UP or event.key == pygame.K_DOWN:
                if self.p2_selected_index < 6:
                    target = min(len(CHARACTER_ORDER) - 1, self.p2_selected_index + 6)
                else:
                    target = self.p2_selected_index - 6
                self._select_p2_character(target)
            elif event.key in (pygame.K_KP1, pygame.K_KP_ENTER, pygame.K_RETURN):
                self.p2_ready = True
        else:
            if event.key in (pygame.K_KP2, pygame.K_BACKSPACE):
                self.p2_ready = False

    def _handle_coop_mouse(self, mx: int, my: int):
        if self.btn_coop_back_rect.collidepoint(mx, my):
            self._go_back()
            return
        if self.p1_ready and self.p2_ready and self.btn_coop_start_rect.collidepoint(mx, my):
            self._confirm_and_play()
            return
            
        # P1 cards click (left half: x < 256)
        if not self.p1_ready:
            for idx in range(len(CHARACTER_ORDER)):
                r = self._get_coop_p1_card_rect(idx)
                if r.collidepoint(mx, my):
                    self._select_p1_character(idx)
                    break
                    
        # P2 cards click (right half: x >= 256)
        if not self.p2_ready:
            for idx in range(len(CHARACTER_ORDER)):
                r = self._get_coop_p2_card_rect(idx)
                if r.collidepoint(mx, my):
                    self._select_p2_character(idx)
                    break

    def _get_solo_card_rect(self, index: int) -> pygame.FRect:
        """Returns the bounding rect for index in Solo 2-row grid fitting x in [10, 241]."""
        col = index % 6
        row = index // 6
        x = 10 + col * 39
        y = 265 + row * 46
        return pygame.FRect(x, y, 36, 42)

    def _get_coop_p1_card_rect(self, index: int) -> pygame.FRect:
        """Returns the bounding rect for P1 card in Co-op mode (x in [14, 242])."""
        col = index % 6
        row = index // 6
        x = 14 + col * 38
        y = 238 + row * 46
        return pygame.FRect(x, y, 35, 42)

    def _get_coop_p2_card_rect(self, index: int) -> pygame.FRect:
        """Returns the bounding rect for P2 card in Co-op mode (x in [270, 498])."""
        col = index % 6
        row = index // 6
        x = 270 + col * 38
        y = 238 + row * 46
        return pygame.FRect(x, y, 35, 42)

    def _trigger_dojo_move(self, key: str):
        """Simulates real character action in the test arena (Solo mode)."""
        self.active_test_key = key
        self.test_key_timer = 0.35
        
        self.player.mana = self.player.max_mana
        self.player.stamina = self.player.max_stamina
        
        if key == "j":
            j_skill = self.profile.skills.get("j")
            self.player.is_attacking = True
            self.player.attack_cooldown = 0.25
            self.player.anim_manager.play("attack", force_reset=True)
            if self.player.archetype in ("mage", "healer", "support", "archer"):
                from entities.projectile import Projectile
                proj_x = self.player.rect.right + 8
                proj_y = self.player.rect.centery - 8
                ptype = j_skill.projectile_type or "arcane_bolt"
                self.player.projectiles.append(Projectile(proj_x, proj_y, True, is_enemy=False, projectile_type=ptype, damage=j_skill.damage))
                self.last_tested_action = f"[J] {j_skill.name}: {j_skill.damage} Dmg à Distância"
            else:
                self.last_tested_action = f"[J] {j_skill.name}: {j_skill.damage} Dmg Físico"
            self.banner_timer = 3.5
            
        elif key == "k":
            k_skill = self.profile.skills.get("k")
            self.player.is_casting_magic = True
            self.player.magic_cast_timer = 0.38
            self.player.magic_sigil_timer = 0.38
            self.player.anim_manager.play("cast_magic", force_reset=True)
            
            from entities.projectile import Projectile
            proj_x = self.player.rect.right + 12
            proj_y = self.player.rect.centery - 10
            ptype = k_skill.projectile_type or ("fireball" if self.player.archetype == "warrior" else "arcane_sphere")
            is_burn = (self.profile.id == "ignis")
            self.player.projectiles.append(Projectile(proj_x, proj_y, True, is_enemy=False, projectile_type=ptype, is_burn=is_burn, damage=k_skill.damage))
            self.last_tested_action = f"[K] {k_skill.name}: {k_skill.damage} Dmg ({k_skill.cost_value} MP)"
            self.banner_timer = 3.5
            
        elif key == "e":
            e_skill = self.profile.skills.get("e")
            self.player.is_casting_aoe = True
            self.player.aoe_timer = 0.85
            self.player.aoe_hit_done = False
            self.player.anim_manager.play("whirlwind", force_reset=True)
            from entities.ultimate_aoe_vfx import UltimateAoE_VFX
            self.player.aoe_vfx = UltimateAoE_VFX(self.player.rect.centerx, self.player.rect.bottom, self.player.aoe_radius, self.profile.id)
            self.last_tested_action = f"[E] {e_skill.name}: {e_skill.damage} Dmg em Área"
            self.banner_timer = 3.5
            
        elif key == "shift":
            shift_skill = self.profile.skills.get("shift")
            self.player.is_blocking = True
            self.player.anim_manager.play("guard", force_reset=True)
            self.last_tested_action = f"[Shift] {shift_skill.name}: Bloqueio 100%"
            self.banner_timer = 3.5
            
        elif key == "q":
            self.player.is_dashing = True
            self.player.dash_timer = 0.22
            self.player.anim_manager.play("dash", force_reset=True)
            self.last_tested_action = "[Q] DASH: Esquiva Ágil com Invulnerabilidade"
            self.banner_timer = 3.5
            
        elif key == "r":
            r_skill = self.profile.skills.get("r")
            self.player.is_casting_ultimate = True
            self.player.anim_manager.play("guard", force_reset=True)
            self.player.ultimate_controller.trigger(self.player.rect.centerx, self.player.rect.bottom, self.player.facing_right)
            self.last_tested_action = f"[R] ULTIMATE: {r_skill.name.upper()} - {r_skill.damage} DANO"
            self.banner_timer = 4.0
            
        elif key == "space":
            if self.player.on_ground:
                self.player.velocity.y = -360
                self.player.on_ground = False
                self.player.anim_manager.play("jump", force_reset=True)
            self.last_tested_action = "[Espaço] SALTO: Pulo acrobático"
            self.banner_timer = 2.5

    def update(self, dt: float):
        self.fx.update(dt)
        
        if self.banner_timer > 0:
            self.banner_timer -= dt
            
        if self.test_key_timer > 0:
            self.test_key_timer -= dt
            if self.test_key_timer <= 0:
                self.active_test_key = None

        if self.coop_mode:
            # Update P1 and P2 preview players
            self.p1_player.update(dt, self.coop_dummy_tiles)
            self.p1_player.pos.x = self.p1_pedestal_pos.x - 16
            self.p1_player.rect.x = self.p1_player.pos.x
            
            self.p2_player.update(dt, self.coop_dummy_tiles)
            self.p2_player.pos.x = self.p2_pedestal_pos.x - 16
            self.p2_player.rect.x = self.p2_player.pos.x
            
            # Synchronized launch countdown if both ready
            if self.p1_ready and self.p2_ready:
                self.both_ready_timer += dt
                if self.both_ready_timer >= 1.2:
                    self._confirm_and_play()
            else:
                self.both_ready_timer = 0.0
        else:
            # Solo mode preview
            if self.player.is_blocking and self.active_test_key != "shift":
                self.player.is_blocking = False
                
            self.player.update(dt, self.dummy_tiles)
            if not self.player.is_dashing and not self.player.is_casting_ultimate:
                self.player.pos.x = self.pedestal_pos.x - 16
                self.player.rect.x = self.player.pos.x
                
            for p in self.player.projectiles[:]:
                p.update(dt)
                if p.rect.x > 320 or not p.active:
                    if p in self.player.projectiles:
                        self.player.projectiles.remove(p)

    def draw(self, surface: pygame.Surface):
        # 1. Background Atmosphere (Continuous void twilight gradient & ambient spores)
        self.fx.draw_background(surface)

        if self.coop_mode:
            self._draw_coop_split_screen(surface)
        else:
            self._draw_solo_screen(surface)

    # =========================================================================
    # SOLO SCREEN RENDERING (HOLLOW KNIGHT AESTHETICS)
    # =========================================================================
    def _draw_solo_screen(self, surface: pygame.Surface):
        # Grand Sanctuary Header
        header_surf = self.font_title.render("SALA DOS HERÓIS", True, HollowColors.TEXT_TITLE)
        surface.blit(header_surf, (16, 8))
        sub_surf = self.font_subtitle.render("SELEÇÃO DE PERSONAGEM & ARENA DE HABILIDADES", True, HollowColors.TEXT_NORMAL)
        surface.blit(sub_surf, (18, 28))
        
        # Hollow Knight Section Divider with central gem
        HollowCrestRenderer.draw_section_divider(surface, 256, 42, width=480, alpha=210)
        
        # Pedestal & Dais
        self._draw_pedestal_at(surface, self.pedestal_pos, self.profile.color_theme)
        
        # Draw interactive preview player and effects
        camera_offset = pygame.math.Vector2(0, 0)
        self.player.draw(surface, camera_offset)
        
        for proj in self.player.projectiles:
            proj.draw(surface, camera_offset)
            
        # Carousel controls (< > arrows + badge)
        self._draw_solo_carousel_controls(surface)
        
        # Move tester panel
        self._draw_solo_dojo_test_panel(surface)
        
        # 2-Row Compact Grid for 11 heroes (x in [10, 241]) - Zero clipping into dossier!
        self._draw_solo_grid(surface)
        
        # Character Dossier (x in [248, 502])
        self._draw_character_dossier(surface)
        
        # Bottom Navigation & Action Buttons
        self._draw_solo_action_buttons(surface)

    def _draw_pedestal_at(self, surface: pygame.Surface, pos: pygame.math.Vector2, col: tuple[int, int, int]):
        HollowCrestRenderer.draw_ancient_pedestal(surface, pos, col)

    def _draw_solo_carousel_controls(self, surface: pygame.Surface):
        col_l = HollowColors.GOLD_CREST if self.btn_left_rect.collidepoint(pygame.mouse.get_pos()) else (150, 160, 180)
        pygame.draw.rect(surface, (14, 16, 24), self.btn_left_rect, border_radius=2)
        pygame.draw.rect(surface, col_l, self.btn_left_rect, 1, border_radius=2)
        arrow_l = self.font_name.render("‹", True, col_l)
        surface.blit(arrow_l, (self.btn_left_rect.x + 6, self.btn_left_rect.y + 4))
        
        col_r = HollowColors.GOLD_CREST if self.btn_right_rect.collidepoint(pygame.mouse.get_pos()) else (150, 160, 180)
        pygame.draw.rect(surface, (14, 16, 24), self.btn_right_rect, border_radius=2)
        pygame.draw.rect(surface, col_r, self.btn_right_rect, 1, border_radius=2)
        arrow_r = self.font_name.render("›", True, col_r)
        surface.blit(arrow_r, (self.btn_right_rect.x + 6, self.btn_right_rect.y + 4))
        
        badge_text = f"HERÓI {self.selected_index + 1} / {len(CHARACTER_ORDER)}"
        badge_surf = self.font_key.render(badge_text, True, HollowColors.TEXT_TITLE)
        bw = badge_surf.get_width() + 16
        bh = 17
        bx = int(self.pedestal_pos.x - bw // 2)
        by = 50
        pygame.draw.rect(surface, (12, 14, 20), (bx, by, bw, bh), border_radius=3)
        pygame.draw.rect(surface, (70, 78, 98), (bx, by, bw, bh), 1, border_radius=3)
        surface.blit(badge_surf, (bx + 8, by + 2))

    def _draw_solo_dojo_test_panel(self, surface: pygame.Surface):
        banner_rect = pygame.FRect(10, 210, 232, 20)
        HollowCrestRenderer.draw_filigree_panel(surface, pygame.Rect(banner_rect), bg_color=(12, 14, 20, 225), border_color=(55, 62, 78), corner_flourish=False)
        
        ban_text = self.font_banner.render(self.last_tested_action, True, HollowColors.GOLD_CREST)
        clip_surf = pygame.Surface((int(banner_rect.width - 8), 16), pygame.SRCALPHA)
        clip_surf.blit(ban_text, (0, 0))
        surface.blit(clip_surf, (banner_rect.x + 4, banner_rect.y + 2))
        
        keycaps = [
            ("j", "J:Atq", 34),
            ("k", "K:Mag", 35),
            ("e", "E:Esp", 35),
            ("shift", "Shift:Def", 48),
            ("q", "Q:Dash", 38),
            ("r", "R:Ult", 32)
        ]
        kx = 10
        ky = 234
        kh = 18
        for k_id, k_label, kw in keycaps:
            is_active = (self.active_test_key == k_id)
            bg_col = self.profile.color_theme if is_active else (18, 20, 28)
            text_col = (10, 10, 15) if is_active else (190, 200, 215)
            k_rect = pygame.FRect(kx, ky, kw, kh)
            pygame.draw.rect(surface, bg_col, k_rect, border_radius=2)
            pygame.draw.rect(surface, (85, 95, 120) if not is_active else WHITE, k_rect, 1, border_radius=2)
            lbl_surf = self.font_key.render(k_label, True, text_col)
            surface.blit(lbl_surf, (k_rect.x + (k_rect.width - lbl_surf.get_width()) // 2, k_rect.y + 2))
            kx += kw + 2

    def _draw_solo_grid(self, surface: pygame.Surface):
        """Draws 11 character thumbnail cards cleanly arranged in 2 rows with Hollow filigree."""
        for idx, cid in enumerate(CHARACTER_ORDER):
            p = CHARACTER_REGISTRY[cid]
            card_rect = self._get_solo_card_rect(idx)
            is_sel = (idx == self.selected_index)
            
            c_bg = (24, 28, 40, 240) if is_sel else (12, 14, 20, 220)
            c_border = HollowColors.GOLD_CREST if is_sel else (50, 58, 74)
            
            # Filigree frame
            r_int = pygame.Rect(card_rect)
            HollowCrestRenderer.draw_filigree_panel(surface, r_int, bg_color=c_bg, border_color=c_border, corner_flourish=is_sel)
            
            t_img = self.thumbnails.get(cid, None)
            if t_img:
                surface.blit(t_img, (card_rect.x + (card_rect.width - t_img.get_width()) // 2, card_rect.y + 3))
            else:
                pygame.draw.circle(surface, p.color_theme, (card_rect.centerx, card_rect.y + 14), 4)
                
            sn = p.name[:4].upper()
            sn_surf = self.font_badge.render(sn, True, HollowColors.GOLD_CREST if is_sel else (150, 160, 180))
            surface.blit(sn_surf, (card_rect.x + (card_rect.width - sn_surf.get_width()) // 2, card_rect.y + 28))
            
            if is_sel:
                # Top subtle diamond marker
                HollowCrestRenderer.draw_selection_marker(surface, card_rect.centerx, card_rect.top - 2, size=3.0)

    def _draw_character_dossier(self, surface: pygame.Surface):
        dx = 248
        dy = 46
        dw = 254
        dh = 280
        
        # Noble Hollow Filigree Dossier Panel
        dossier_rect = pygame.Rect(dx, dy, dw, dh)
        HollowCrestRenderer.draw_filigree_panel(surface, dossier_rect, bg_color=(10, 12, 18, 240), border_color=(75, 82, 100), corner_flourish=True)
        
        col = self.profile.color_theme
        name_surf = self.font_name.render(self.profile.name.upper(), True, HollowColors.TEXT_TITLE)
        surface.blit(name_surf, (dx + 12, dy + 6))
        
        title_surf = self.font_desc.render(self.profile.title, True, HollowColors.TEXT_NORMAL)
        surface.blit(title_surf, (dx + 12, dy + 23))
        
        arch_map = {
            "warrior": "VALQUÍRIA",
            "mage": "MAGA",
            "shinobi": "SHINOBI",
            "samurai": "SAMURAI",
            "fighter": "LUTADOR",
            "healer": "SACERDOTISA",
            "archer": "ARQUEIRO",
            "support": "ARTÍFICE",
            "guardian": "GUARDIÃO"
        }
        badge_str = arch_map.get(self.profile.archetype, self.profile.archetype.upper())
        badge_surf = self.font_key.render(f"‹ {badge_str} ›", True, HollowColors.GOLD_CREST)
        surface.blit(badge_surf, (dx + dw - badge_surf.get_width() - 10, dy + 8))
        
        # Subtle horizontal divider
        pygame.draw.line(surface, (45, 52, 68), (dx + 10, dy + 37), (dx + dw - 10, dy + 37), 1)
        
        stats = [
            ("VIDA", self.profile.hp_max, (225, 60, 60)),
            ("MANA", self.profile.mp_max, (60, 150, 245)),
            ("ESTAMINA", self.profile.sp_max, (45, 200, 95))
        ]
        sy = dy + 41
        for s_label, s_val, s_col in stats:
            lbl = self.font_stat.render(s_label, True, HollowColors.TEXT_NORMAL)
            surface.blit(lbl, (dx + 12, sy))
            bx = dx + 76
            bw = 92
            bh = 6
            pygame.draw.rect(surface, (20, 24, 32), (bx, sy + 2, bw, bh), border_radius=1)
            fill_w = max(4, int(bw * max(0.0, min(1.0, s_val / 165.0))))
            pygame.draw.rect(surface, s_col, (bx, sy + 2, fill_w, bh), border_radius=1)
            pygame.draw.rect(surface, (60, 68, 85), (bx, sy + 2, bw, bh), 1, border_radius=1)
            val_surf = self.font_key.render(f"{s_val}", True, HollowColors.TEXT_TITLE)
            surface.blit(val_surf, (bx + bw + 6, sy - 1))
            sy += 12
            
        px = dx + 8
        py = dy + 78
        pw = dw - 16
        ph = 42
        pygame.draw.rect(surface, (14, 16, 24), (px, py, pw, ph), border_radius=2)
        pygame.draw.rect(surface, (55, 62, 78), (px, py, pw, ph), 1, border_radius=2)
        pygame.draw.rect(surface, HollowColors.GOLD_CREST, (px, py, 2, ph))
        
        p_title = f"PASSIVA: {self.profile.passive_name.upper()}"
        p_surf = self.font_key.render(p_title, True, HollowColors.GOLD_CREST)
        surface.blit(p_surf, (px + 7, py + 3))
        
        words = self.profile.passive_desc.split(" ")
        l1, l2 = "", ""
        for w in words:
            test_line = (l1 + " " + w).strip()
            if self.font_desc.size(test_line)[0] < (pw - 14):
                l1 = test_line
            else:
                l2 = (l2 + " " + w).strip()
        if l1:
            surface.blit(self.font_desc.render(l1, True, HollowColors.TEXT_TITLE), (px + 7, py + 16))
        if l2:
            surface.blit(self.font_desc.render(l2, True, HollowColors.TEXT_NORMAL), (px + 7, py + 27))
            
        pygame.draw.line(surface, (45, 52, 68), (dx + 10, dy + 124), (dx + dw - 10, dy + 124), 1)
        
        sk_title = self.font_subtitle.render("HABILIDADES DE COMBATE:", True, HollowColors.TEXT_NORMAL)
        surface.blit(sk_title, (dx + 12, dy + 126))
        
        core_keys = ["j", "k", "e", "shift", "r"]
        sy = dy + 140
        for k in core_keys:
            if k in self.profile.skills:
                sk = self.profile.skills[k]
                is_ult = (k == "r")
                icon_surf = self.skill_icons.get(sk.icon_file, None)
                if icon_surf:
                    surface.blit(icon_surf, (dx + 10, sy))
                hk_name = f"[{k.upper()}] {sk.name}"
                if self.font_key.size(hk_name)[0] > (dw - 130):
                    while self.font_key.size(hk_name + "...")[0] > (dw - 130) and len(hk_name) > 6:
                        hk_name = hk_name[:-1]
                    hk_name += "..."
                hk_surf = self.font_key.render(hk_name, True, HollowColors.GOLD_CREST if is_ult else HollowColors.TEXT_TITLE)
                surface.blit(hk_surf, (dx + 32, sy + 3))
                
                if k == "j":
                    metric_str = f"{sk.damage}D|CD"
                elif k == "k":
                    metric_str = f"{sk.damage}D|{sk.cost_value}MP"
                elif k == "e":
                    metric_str = f"{sk.damage}D|{sk.cost_value}{sk.cost_type}"
                elif k == "shift":
                    metric_str = f"Blq|{sk.cost_value}{sk.cost_type}"
                elif k == "r":
                    metric_str = f"{sk.damage}D|{sk.cost_value}MP"
                else:
                    metric_str = f"{sk.damage}D"
                    
                metric_col = HollowColors.GOLD_CREST if is_ult else HollowColors.TEXT_NORMAL
                metric_surf = self.font_key.render(metric_str, True, metric_col)
                surface.blit(metric_surf, (dx + dw - metric_surf.get_width() - 8, sy + 3))
                sy += 21

    def _draw_solo_action_buttons(self, surface: pygame.Surface):
        is_back_hov = self.btn_back_rect.collidepoint(pygame.mouse.get_pos())
        HollowCrestRenderer.draw_hollow_button(surface, pygame.Rect(self.btn_back_rect), "VOLTAR [ESC]", self.font_key, is_hovered=is_back_hov)
        
        is_play_hov = self.btn_play_rect.collidepoint(pygame.mouse.get_pos())
        HollowCrestRenderer.draw_hollow_button(surface, pygame.Rect(self.btn_play_rect), "JOGAR [ENTER]", self.font_subtitle, is_hovered=is_play_hov, text_color=HollowColors.GOLD_CREST if is_play_hov else HollowColors.TEXT_TITLE)

    # =========================================================================
    # CO-OP SPLIT-SCREEN RENDERING
    # =========================================================================
    def _draw_coop_split_screen(self, surface: pygame.Surface):
        # 1. Main Header
        header_surf = self.font_title.render("SALA DOS HERÓIS — CO-OP LOCAL (2 JOGADORES)", True, HollowColors.TEXT_TITLE)
        surface.blit(header_surf, (surface.get_width() // 2 - header_surf.get_width() // 2, 6))
        
        sub_str = "P1: [W/A/S/D] • [J/Espaço] Pronto   |   P2: [Setas] • [Num 1/Enter] Pronto"
        sub_surf = self.font_desc.render(sub_str, True, HollowColors.TEXT_NORMAL)
        surface.blit(sub_surf, (surface.get_width() // 2 - sub_surf.get_width() // 2, 26))
        
        # Horizontal top bar with section divider
        HollowCrestRenderer.draw_section_divider(surface, surface.get_width() // 2, 40, width=490, alpha=180)
        
        # Center Vertical Divider (x = 256)
        div_x = 256
        pygame.draw.line(surface, (35, 42, 56), (div_x, 44), (div_x, 340), 1)
        pygame.draw.line(surface, (75, 88, 115), (div_x, 80), (div_x, 280), 1)
        pygame.draw.circle(surface, HollowColors.SILVER_CREST, (div_x, 180), 3)
        pygame.draw.circle(surface, (255, 255, 255), (div_x, 180), 1)
        
        # 2. Left Side: Player 1 (x in [0, 256])
        self._draw_coop_player_panel(
            surface=surface,
            player_idx=0,
            rect=pygame.FRect(8, 44, 240, 294),
            selected_idx=self.p1_selected_index,
            is_ready=self.p1_ready,
            player_entity=self.p1_player,
            profile=self.p1_profile,
            pedestal_pos=self.p1_pedestal_pos,
            tag_name="JOGADOR 1 (P1)",
            tag_col=(140, 210, 255),
            ready_key_hint="[J / ESPAÇO]",
            cancel_key_hint="[K]",
            card_getter=self._get_coop_p1_card_rect
        )
        
        # 3. Right Side: Player 2 (x in [256, 512])
        self._draw_coop_player_panel(
            surface=surface,
            player_idx=1,
            rect=pygame.FRect(264, 44, 240, 294),
            selected_idx=self.p2_selected_index,
            is_ready=self.p2_ready,
            player_entity=self.p2_player,
            profile=self.p2_profile,
            pedestal_pos=self.p2_pedestal_pos,
            tag_name="JOGADOR 2 (P2)",
            tag_col=(255, 195, 110),
            ready_key_hint="[NUM 1 / ENTER]",
            cancel_key_hint="[NUM 2]",
            card_getter=self._get_coop_p2_card_rect
        )
        
        # 4. Bottom Launch / Status Bar
        self._draw_coop_bottom_bar(surface)

    def _draw_coop_player_panel(self, surface: pygame.Surface, player_idx: int, rect: pygame.FRect,
                                selected_idx: int, is_ready: bool, player_entity: Player,
                                profile, pedestal_pos: pygame.math.Vector2,
                                tag_name: str, tag_col: tuple[int, int, int],
                                ready_key_hint: str, cancel_key_hint: str, card_getter):
        # Panel outline with Hollow Filigree
        border_col = (80, 240, 140) if is_ready else ((65, 80, 110) if player_idx == 0 else (110, 85, 65))
        HollowCrestRenderer.draw_filigree_panel(surface, pygame.Rect(rect), bg_color=(10, 12, 18, 235), border_color=border_col, corner_flourish=True)
        
        # Player Header Badge
        header_y = rect.y + 6
        badge_surf = self.font_subtitle.render(f"‹ {tag_name} ›", True, tag_col)
        surface.blit(badge_surf, (rect.x + 8, header_y))
        
        # Ready status pill
        if is_ready:
            pill_text = f"PRONTO ({cancel_key_hint})"
            pill_bg = (14, 45, 26, 240)
            pill_border = (80, 240, 140)
            pill_text_col = (255, 255, 255)
        else:
            pill_text = f"{ready_key_hint} ESCOLHER"
            pill_bg = (16, 20, 28, 220)
            pill_border = (65, 75, 98)
            pill_text_col = HollowColors.TEXT_NORMAL
            
        ps = self.font_desc.render(pill_text, True, pill_text_col)
        pw = ps.get_width() + 12
        ph = 16
        px = rect.right - pw - 8
        py = header_y
        pill_rect = pygame.Rect(px, py, pw, ph)
        HollowCrestRenderer.draw_filigree_panel(surface, pill_rect, bg_color=pill_bg, border_color=pill_border, corner_flourish=False)
        surface.blit(ps, (px + 6, py + 1))
        
        # Pedestal & Player Preview
        self._draw_pedestal_at(surface, pedestal_pos, profile.color_theme)
        player_entity.draw(surface, pygame.math.Vector2(0, 0))
        
        # Character Name & Archetype Badge
        ny = rect.y + 115
        cname_surf = self.font_name.render(profile.name.upper(), True, HollowColors.TEXT_TITLE)
        surface.blit(cname_surf, (rect.x + 10, ny))
        
        title_surf = self.font_desc.render(profile.title, True, HollowColors.TEXT_NORMAL)
        surface.blit(title_surf, (rect.x + 10, ny + 15))
        
        # Mini Attribute Gauges (HP, MP, SP)
        stats = [
            ("HP", profile.hp_max, (225, 60, 60)),
            ("MP", profile.mp_max, (60, 150, 245)),
            ("SP", profile.sp_max, (45, 200, 95))
        ]
        gx = rect.right - 92
        gy = ny
        for s_lbl, s_val, s_col in stats:
            l_surf = self.font_badge.render(s_lbl, True, (150, 160, 180))
            surface.blit(l_surf, (gx, gy))
            pygame.draw.rect(surface, (18, 22, 30), (gx + 16, gy + 2, 48, 5), border_radius=1)
            fill_w = max(2, int(48 * min(1.0, s_val / 165.0)))
            pygame.draw.rect(surface, s_col, (gx + 16, gy + 2, fill_w, 5), border_radius=1)
            pygame.draw.rect(surface, (55, 62, 78), (gx + 16, gy + 2, 48, 5), 1, border_radius=1)
            gy += 9
            
        # Character Selection Grid (2 rows x 6 cols)
        for idx, cid in enumerate(CHARACTER_ORDER):
            p = CHARACTER_REGISTRY[cid]
            card_r = card_getter(idx)
            is_sel = (idx == selected_idx)
            
            c_bg = (24, 30, 42, 240) if is_sel else (12, 14, 20, 220)
            c_border = tag_col if is_sel else (45, 52, 68)
            
            HollowCrestRenderer.draw_filigree_panel(surface, pygame.Rect(card_r), bg_color=c_bg, border_color=c_border, corner_flourish=is_sel)
            
            t_img = self.thumbnails.get(cid, None)
            if t_img:
                surface.blit(t_img, (card_r.x + (card_r.width - t_img.get_width()) // 2, card_r.y + 3))
            else:
                pygame.draw.circle(surface, p.color_theme, (card_r.centerx, card_r.y + 14), 4)
                
            sn = p.name[:4].upper()
            sn_surf = self.font_badge.render(sn, True, tag_col if is_sel else (135, 145, 165))
            surface.blit(sn_surf, (card_r.x + (card_r.width - sn_surf.get_width()) // 2, card_r.y + 28))
            
            # Cursor indicator badge (P1 / P2)
            if is_sel:
                p_tag = "P1" if player_idx == 0 else "P2"
                pt_surf = self.font_badge.render(p_tag, True, (10, 10, 15))
                tw = pt_surf.get_width() + 4
                th = 10
                pygame.draw.rect(surface, tag_col, (card_r.right - tw - 1, card_r.y + 1, tw, th), border_radius=1)
                surface.blit(pt_surf, (card_r.right - tw + 1, card_r.y))

    def _draw_coop_bottom_bar(self, surface: pygame.Surface):
        by = 344
        HollowCrestRenderer.draw_section_divider(surface, 256, by, width=490, alpha=160)
        
        # Back button
        is_hov = self.btn_coop_back_rect.collidepoint(pygame.mouse.get_pos())
        HollowCrestRenderer.draw_hollow_button(surface, pygame.Rect(self.btn_coop_back_rect), "VOLTAR [ESC]", self.font_desc, is_hovered=is_hov)
        
        # Center status or Ready Banner
        if self.p1_ready and self.p2_ready:
            pulse = int(180 + 75 * math.sin(pygame.time.get_ticks() * 0.01))
            pulse_col = (255, min(255, pulse), 80)
            ready_msg = "✣ AMBOS PRONTOS! PRESSIONE [ESPAÇO] OU [ENTER] PARA JOGAR! ✣"
            r_surf = self.font_subtitle.render(ready_msg, True, pulse_col)
            surface.blit(r_surf, (surface.get_width() // 2 - r_surf.get_width() // 2, by + 9))
            
            # Start button
            is_start_hov = self.btn_coop_start_rect.collidepoint(pygame.mouse.get_pos())
            HollowCrestRenderer.draw_hollow_button(surface, pygame.Rect(self.btn_coop_start_rect), "INICIAR CO-OP", self.font_subtitle, is_hovered=is_start_hov, text_color=HollowColors.GOLD_CREST if is_start_hov else HollowColors.TEXT_TITLE)
        else:
            p1_status = "✔ P1 Pronto" if self.p1_ready else "P1 Escolhendo..."
            p2_status = "✔ P2 Pronto" if self.p2_ready else "P2 Escolhendo..."
            status_msg = f"{p1_status}   •   {p2_status}"
            s_surf = self.font_desc.render(status_msg, True, HollowColors.TEXT_NORMAL)
            surface.blit(s_surf, (surface.get_width() // 2 - s_surf.get_width() // 2, by + 11))
