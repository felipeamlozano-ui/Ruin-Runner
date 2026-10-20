"""
src/scenes/character_select_scene.py
------------------------------------
AAA Character Selection & Interactive Dojo Scene.
Native 640x360 resolution with zero clipping, full screen coverage (x=10..630, y=6..354).
Features:
- Live Silksong stage atmosphere: Emerald Fortress (terrae_3) parallax + clouds + mist + lighting with autoscroll.
- Soft volumetric light beam on pedestals (no hard polygon triangles).
- Solo mode: Interactive Dojo + 2-Row Compact Grid + Full 390px Dossier with word-wrapped passive and untruncated skill names.
- Co-op mode: Dual symmetrical 304px panels (P1 & P2) with independent pedestals, passive + skills summary,
  real bust thumbnails, and Campaign / Arcade mode selector (< MODO: CAMPANHA NARRATIVA | MODO ARCADE >).
"""

import math
import os
import random
from typing import Optional, Dict
import pygame

from config.settings import SETTINGS
from config.colors import WHITE, GOLD, RED, BLUE, GREEN, GRAY, UI_BACKGROUND
from engine.scene_manager import Scene
from engine.input_manager import INPUT
from entities.player import Player
from entities.character_data import CHARACTER_REGISTRY, CHARACTER_ORDER, get_character_profile
from engine.stage_manager import STAGE_CATALOG, ParallaxRenderer
from engine.v3.weather.clouds import CloudsManager
from engine.v3.weather.mist import MistManager
from engine.lighting import LightingEngine
from engine.text_cache import get_cached_text, render_wrapped_text
from ui.hollow_ui import HollowFonts, HollowCrestRenderer, AtmosphereFX, HollowColors
from ui.selection_helpers import (
    get_hero_thumbnails,
    draw_pedestal_with_beam,
    draw_live_stage_background,
    draw_symmetrical_hero_card
)

class CharacterSelectScene(Scene):
    """
    Character Selection & Interactive Dojo Scene.
    Calibrated for native 640x360 resolution.
    """
    internal_size = (640, 360)

    def __init__(self, scene_manager, previous_scene=None, coop_target: str = "campaign"):
        self.scene_manager = scene_manager
        self.previous_scene = previous_scene
        self.coop_target = coop_target # "campaign" or "arcade"

        self.width = 640
        self.height = 360

        # Load fonts via HollowFonts cache
        pygame.font.init()
        self.font_title = HollowFonts.get(16, bold=True)
        self.font_name = HollowFonts.get(13, bold=True)
        self.font_subtitle = HollowFonts.get(10)
        self.font_body = HollowFonts.get(9)
        self.font_stat = HollowFonts.get(9, bold=True)
        self.font_key = HollowFonts.get(9, bold=True)
        self.font_banner = HollowFonts.get(9)
        self.font_desc = HollowFonts.get(9, italic=True)
        self.font_badge = HollowFonts.get(8, bold=True)

        # Mode detection
        self.coop_mode = getattr(SETTINGS, "COOP_ENABLED", False)

        # 1. Live Emerald Fortress (terrae_3) Stage Atmosphere
        self.cam_x = 0.0
        stage_cfg = STAGE_CATALOG.get("terrae_3")
        self.stage_cfg = stage_cfg
        self.parallax = None
        self.clouds = None
        self.mist = None
        theme = getattr(stage_cfg, "biome_theme", "castle")

        if stage_cfg and stage_cfg.bg_folder and stage_cfg.layer_files:
            self.parallax = ParallaxRenderer(
                stage_cfg.bg_folder,
                stage_cfg.layer_files,
                stage_cfg.layer_speeds,
                screen_h=360,
                initial_offsets=getattr(stage_cfg, "layer_initial_offsets", None)
            )
            cloud_count = getattr(stage_cfg, "cloud_count", 14)
            self.clouds = CloudsManager(
                theme=getattr(stage_cfg, "cloud_theme", "white"),
                map_width=4000,
                cloud_count=cloud_count,
                screen_w=640,
                sky_horizon_y=getattr(stage_cfg, "sky_horizon_y", 65),
                cloud_tint=getattr(stage_cfg, "cloud_tint", None),
                cloud_opacity_scale=getattr(stage_cfg, "cloud_opacity_scale", 0.50)
            )
            self.mist = MistManager(screen_w=640, screen_h=360, floor_y=280, theme=theme)

        self.lighting = LightingEngine(theme=theme, screen_w=640, screen_h=360, floor_y=280)

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
        self.pedestal_pos = pygame.math.Vector2(120, 155)      # Solo left dais
        self.p1_pedestal_pos = pygame.math.Vector2(68, 125)    # Co-op P1 dais
        self.p2_pedestal_pos = pygame.math.Vector2(384, 125)   # Co-op P2 dais

        self.dummy_tiles = [
            pygame.FRect(20, 160, 200, 40)
        ]
        self.coop_dummy_tiles = [
            pygame.FRect(15, 130, 110, 40),
            pygame.FRect(330, 130, 110, 40)
        ]

        # Authentic portraits & skill icons
        self.thumbnails = get_hero_thumbnails()
        self.skill_icons = {}
        self._load_skill_icons()

        # Move tester feedback (Solo mode)
        self.last_tested_action = "DOJO: Pressione [J], [K], [E], [Shift], [Q], [R] para testar!"
        self.banner_timer = 4.0
        self.active_test_key = None
        self.test_key_timer = 0.0

        # Buttons calibrated for full 640x360
        self.btn_left_rect = pygame.FRect(10, 106, 20, 32)
        self.btn_right_rect = pygame.FRect(210, 106, 20, 32)
        self.btn_back_rect = pygame.FRect(10, 334, 110, 22)
        self.btn_play_rect = pygame.FRect(510, 334, 120, 22)

        # Co-op buttons
        self.btn_coop_back_rect = pygame.FRect(10, 334, 110, 22)
        self.btn_coop_start_rect = pygame.FRect(510, 334, 120, 22)
        self.btn_coop_mode_toggle_rect = pygame.FRect(160, 22, 320, 16)

        # Instantiate preview players
        self._spawn_preview_player()
        if self.coop_mode:
            self._spawn_coop_players()

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
        self.selected_index = index % len(CHARACTER_ORDER)
        self._spawn_preview_player()
        self.last_tested_action = f"Personagem: {self.profile.name} ({self.profile.title})"
        self.banner_timer = 2.5

    def _select_p1_character(self, index: int):
        if self.p1_ready:
            return
        self.p1_selected_index = index % len(CHARACTER_ORDER)
        self._spawn_coop_players()

    def _select_p2_character(self, index: int):
        if self.p2_ready:
            return
        self.p2_selected_index = index % len(CHARACTER_ORDER)
        self._spawn_coop_players()

    def _toggle_coop_target(self):
        """Toggles between Campaign and Arcade mode in Co-op."""
        self.coop_target = "arcade" if self.coop_target == "campaign" else "campaign"

    def _confirm_and_play(self):
        """Saves selected character(s) and launches the chosen game mode."""
        from scenes.loading_scene import LoadingScene

        if self.coop_mode:
            p1_cid = CHARACTER_ORDER[self.p1_selected_index]
            p2_cid = CHARACTER_ORDER[self.p2_selected_index]
            SETTINGS.CURRENT_CHARACTER = p1_cid
            SETTINGS.P2_CHARACTER = p2_cid
            SETTINGS.COOP_ENABLED = True

            if self.coop_target == "campaign":
                # Campaign Co-op: Return to StorySelectScene or resume campaign directly
                from scenes.story_select_scene import StorySelectScene
                from engine.save_manager import SAVE
                from engine.stage_manager import STAGE_MGR
                from scenes.level_scene import LevelScene

                # Check if returning to an active story select scene
                if isinstance(self.previous_scene, StorySelectScene):
                    self.previous_scene.coop_heroes_confirmed = True
                    self.previous_scene._launch_world()
                    return

                # Otherwise, launch current resume stage in campaign
                target_stage_id = "terrae_1"
                stage_cfg = STAGE_MGR.load_stage(target_stage_id)
                next_scene = LevelScene(self.scene_manager, stage=stage_cfg) if stage_cfg else LevelScene(self.scene_manager, stage=1)
                loading = LoadingScene(
                    self.scene_manager,
                    next_scene,
                    title="CAMPANHA COOPERATIVA (2 JOGADORES)",
                    tip="Co-op: Trabalhem em equipe! Progresso de fases e Orbes salvos automaticamente."
                )
                self.scene_manager.change_scene(loading)
                return
            else:
                # Arcade Co-op Mode
                from scenes.level_scene import LevelScene
                lvl1 = LevelScene(stage=1, scene_manager=self.scene_manager)
                loading = LoadingScene(
                    self.scene_manager,
                    lvl1,
                    title="MODO ARCADE CO-OP (2 JOGADORES)",
                    tip="Co-op Arcade: Derrotem hordas de inimigos juntos!"
                )
                self.scene_manager.change_scene(loading)
                return
        else:
            # Solo Mode
            cid = CHARACTER_ORDER[self.selected_index]
            SETTINGS.CURRENT_CHARACTER = cid
            SETTINGS.COOP_ENABLED = False

            if SETTINGS.DEV_MODE and SETTINGS.DEV_START_BOSS:
                from scenes.boss_scene import BossScene
                boss_scene = BossScene(self.scene_manager)
                loading = LoadingScene(
                    self.scene_manager,
                    boss_scene,
                    title="SALA DO BOSS: O REI ESQUELETO",
                    tip="Modo Dev Ativo: Confronto direto com o Boss!"
                )
                self.scene_manager.change_scene(loading)
            else:
                from scenes.level_scene import LevelScene
                lvl1 = LevelScene(stage=1, scene_manager=self.scene_manager)
                loading = LoadingScene(
                    self.scene_manager,
                    lvl1,
                    title="FASE 1: AS CATACUMBAS",
                    tip="Solo: Use suas habilidades de combate com sabedoria!"
                )
                self.scene_manager.change_scene(loading)

    def _go_back(self):
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
            for idx in range(len(CHARACTER_ORDER)):
                r = self._get_solo_card_rect(idx)
                if r.collidepoint(mx, my):
                    self._select_character(idx)
                    break

    def _handle_coop_keydown(self, event: pygame.event.Event):
        if event.key == pygame.K_ESCAPE:
            if self.p1_ready or self.p2_ready:
                self.p1_ready = False
                self.p2_ready = False
            else:
                self._go_back()
            return

        # Mode toggle: TAB / Q / E when not both ready
        if event.key in (pygame.K_TAB, pygame.K_q, pygame.K_e) and not (self.p1_ready and self.p2_ready):
            self._toggle_coop_target()
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
            elif event.key in (pygame.K_w, pygame.K_s):
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

        # Player 2 Controls: Arrow Keys + Enter / Num 1 (Ready) + Num 2 / Backspace (Cancel)
        if not self.p2_ready:
            if event.key == pygame.K_LEFT:
                self._select_p2_character(self.p2_selected_index - 1)
            elif event.key == pygame.K_RIGHT:
                self._select_p2_character(self.p2_selected_index + 1)
            elif event.key in (pygame.K_UP, pygame.K_DOWN):
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
        if self.btn_coop_mode_toggle_rect.collidepoint(mx, my) and not (self.p1_ready and self.p2_ready):
            self._toggle_coop_target()
            return
        if self.p1_ready and self.p2_ready and self.btn_coop_start_rect.collidepoint(mx, my):
            self._confirm_and_play()
            return

        # P1 cards click (left half: x < 320)
        if not self.p1_ready:
            for idx in range(len(CHARACTER_ORDER)):
                r = self._get_coop_card_rect(idx, player_idx=0)
                if r.collidepoint(mx, my):
                    self._select_p1_character(idx)
                    break

        # P2 cards click (right half: x >= 320)
        if not self.p2_ready:
            for idx in range(len(CHARACTER_ORDER)):
                r = self._get_coop_card_rect(idx, player_idx=1)
                if r.collidepoint(mx, my):
                    self._select_p2_character(idx)
                    break

    def _get_solo_card_rect(self, index: int) -> pygame.FRect:
        """Returns the bounding rect for index in Solo 2-row grid fitting x in [10, 230]."""
        col = index % 6
        row = index // 6
        x = 10 + col * 37
        y = 230 + row * 46
        return pygame.FRect(x, y, 34, 42)

    def _get_coop_card_rect(self, index: int, player_idx: int) -> pygame.FRect:
        """Returns the bounding rect for card in Co-op mode inside each 304px panel."""
        base_x = 19 if player_idx == 0 else 335
        grid_y = 264
        col = index % 6
        row = index // 6
        cx = base_x + col * 48
        cy = grid_y + row * 33
        return pygame.FRect(cx, cy, 44, 30)

    def _trigger_dojo_move(self, key: str):
        self.active_test_key = key
        self.test_key_timer = 0.35
        self.player.mana = self.player.max_mana
        self.player.stamina = self.player.max_stamina

        if key == "j":
            j_skill = self.profile.skills.get("j")
            self.player.is_attacking = True
            self.player.attack_cooldown = 0.25
            self.player.anim_manager.play("attack", force_reset=True)
            self.last_tested_action = f"[J] {j_skill.name}: {j_skill.damage} Dmg"
            self.banner_timer = 3.5
        elif key == "k":
            k_skill = self.profile.skills.get("k")
            self.player.is_casting_magic = True
            self.player.magic_cast_timer = 0.38
            self.player.anim_manager.play("cast_magic", force_reset=True)
            from entities.projectile import Projectile
            proj_x = self.player.rect.right + 12
            proj_y = self.player.rect.centery - 10
            ptype = k_skill.projectile_type or "arcane_sphere"
            self.player.projectiles.append(Projectile(proj_x, proj_y, True, is_enemy=False, projectile_type=ptype, damage=k_skill.damage))
            self.last_tested_action = f"[K] {k_skill.name}: {k_skill.damage} Dmg ({k_skill.cost_value} MP)"
            self.banner_timer = 3.5
        elif key == "e":
            e_skill = self.profile.skills.get("e")
            self.player.is_casting_aoe = True
            self.player.aoe_timer = 0.85
            self.player.anim_manager.play("whirlwind", force_reset=True)
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
        # Camera slow horizontal autoscroll for live background
        self.cam_x += 12.0 * dt

        if self.clouds:
            self.clouds.update(dt)
        if self.mist:
            self.mist.update(dt)
        if self.lighting:
            self.lighting.update(dt)

        if self.banner_timer > 0:
            self.banner_timer -= dt
        if self.test_key_timer > 0:
            self.test_key_timer -= dt
            if self.test_key_timer <= 0:
                self.active_test_key = None

        if self.coop_mode:
            self.p1_player.update(dt, self.coop_dummy_tiles)
            self.p1_player.pos.x = self.p1_pedestal_pos.x - 16
            self.p1_player.rect.x = self.p1_player.pos.x

            self.p2_player.update(dt, self.coop_dummy_tiles)
            self.p2_player.pos.x = self.p2_pedestal_pos.x - 16
            self.p2_player.rect.x = self.p2_player.pos.x

            if self.p1_ready and self.p2_ready:
                self.both_ready_timer += dt
                if self.both_ready_timer >= 1.2:
                    self._confirm_and_play()
            else:
                self.both_ready_timer = 0.0
        else:
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
        # 1. Live Emerald Fortress background with Silksong Lighting
        draw_live_stage_background(surface, self.parallax, self.cam_x, self.lighting, self.mist, self.clouds)

        if self.coop_mode:
            self._draw_coop_screen(surface)
        else:
            self._draw_solo_screen(surface)

    # =========================================================================
    # SOLO SCREEN RENDERING (640x360 NATIVE)
    # =========================================================================
    def _draw_solo_screen(self, surface: pygame.Surface):
        # Header
        header_surf = get_cached_text(self.font_title, "SALA DOS HERÓIS", HollowColors.TEXT_TITLE)
        surface.blit(header_surf, (14, 6))
        sub_surf = get_cached_text(self.font_subtitle, "SELEÇÃO DE PERSONAGEM & ARENA DE HABILIDADES", HollowColors.TEXT_NORMAL)
        surface.blit(sub_surf, (16, 24))

        HollowCrestRenderer.draw_section_divider(surface, 320, 38, width=620, alpha=210)

        # Left: Dais + Soft Volumetric Beam + Player
        draw_pedestal_with_beam(surface, self.pedestal_pos, self.profile.color_theme, self.lighting)
        self.player.draw(surface, pygame.math.Vector2(0, 0))
        for proj in self.player.projectiles:
            proj.draw(surface, pygame.math.Vector2(0, 0))

        # Carousel controls (< >)
        self._draw_solo_carousel_controls(surface)

        # Dojo move test feedback & keycaps
        self._draw_solo_dojo_test_panel(surface)

        # 2-Row Compact Grid for 11 heroes (x in [10, 230])
        self._draw_solo_grid(surface)

        # Full 390px Character Dossier (x in [240, 630])
        self._draw_character_dossier(surface)

        # Action Buttons in footer
        self._draw_solo_action_buttons(surface)

    def _draw_solo_carousel_controls(self, surface: pygame.Surface):
        col_l = HollowColors.GOLD_CREST if self.btn_left_rect.collidepoint(pygame.mouse.get_pos()) else (150, 160, 180)
        pygame.draw.rect(surface, (14, 16, 24), self.btn_left_rect, border_radius=2)
        pygame.draw.rect(surface, col_l, self.btn_left_rect, 1, border_radius=2)
        arrow_l = get_cached_text(self.font_name, "‹", col_l)
        surface.blit(arrow_l, (self.btn_left_rect.x + 6, self.btn_left_rect.y + 4))

        col_r = HollowColors.GOLD_CREST if self.btn_right_rect.collidepoint(pygame.mouse.get_pos()) else (150, 160, 180)
        pygame.draw.rect(surface, (14, 16, 24), self.btn_right_rect, border_radius=2)
        pygame.draw.rect(surface, col_r, self.btn_right_rect, 1, border_radius=2)
        arrow_r = get_cached_text(self.font_name, "›", col_r)
        surface.blit(arrow_r, (self.btn_right_rect.x + 6, self.btn_right_rect.y + 4))

        badge_text = f"HERÓI {self.selected_index + 1} / {len(CHARACTER_ORDER)}"
        badge_surf = get_cached_text(self.font_key, badge_text, HollowColors.TEXT_TITLE)
        bw = badge_surf.get_width() + 16
        bh = 17
        bx = int(self.pedestal_pos.x - bw // 2)
        by = 44
        pygame.draw.rect(surface, (12, 14, 20), (bx, by, bw, bh), border_radius=3)
        pygame.draw.rect(surface, (70, 78, 98), (bx, by, bw, bh), 1, border_radius=3)
        surface.blit(badge_surf, (bx + 8, by + 1))

    def _draw_solo_dojo_test_panel(self, surface: pygame.Surface):
        banner_rect = pygame.FRect(10, 184, 222, 18)
        HollowCrestRenderer.draw_filigree_panel(surface, pygame.Rect(banner_rect), bg_color=(12, 14, 20, 225), border_color=(55, 62, 78), corner_flourish=False)

        ban_text = get_cached_text(self.font_banner, self.last_tested_action, HollowColors.GOLD_CREST)
        clip_surf = pygame.Surface((int(banner_rect.width - 8), 16), pygame.SRCALPHA)
        clip_surf.blit(ban_text, (0, 0))
        surface.blit(clip_surf, (banner_rect.x + 4, banner_rect.y + 1))

        keycaps = [
            ("j", "J:Atq", 33),
            ("k", "K:Mag", 33),
            ("e", "E:Esp", 33),
            ("shift", "Shift:Def", 46),
            ("q", "Q:Dash", 36),
            ("r", "R:Ult", 30)
        ]
        kx = 10
        ky = 205
        kh = 17
        for k_id, k_label, kw in keycaps:
            is_active = (self.active_test_key == k_id)
            bg_col = self.profile.color_theme if is_active else (18, 20, 28)
            text_col = (10, 10, 15) if is_active else (190, 200, 215)
            k_rect = pygame.FRect(kx, ky, kw, kh)
            pygame.draw.rect(surface, bg_col, k_rect, border_radius=2)
            pygame.draw.rect(surface, (85, 95, 120) if not is_active else WHITE, k_rect, 1, border_radius=2)
            lbl_surf = get_cached_text(self.font_key, k_label, text_col)
            surface.blit(lbl_surf, (k_rect.x + (k_rect.width - lbl_surf.get_width()) // 2, k_rect.y + 1))
            kx += kw + 2

    def _draw_solo_grid(self, surface: pygame.Surface):
        short_names = {
            "shaia": "SHAI", "lunaria": "LUNA", "ignis": "IGNI", "astra": "ASTR",
            "shinobi": "HAYA", "samurai": "KENS", "fighter": "RYUU", "knight": "GALA",
            "wizard": "IGNA", "samurai_archer": "HANZ", "kunoichi": "AYAM"
        }
        for idx, cid in enumerate(CHARACTER_ORDER):
            card_rect = self._get_solo_card_rect(idx)
            is_sel = (idx == self.selected_index)
            c_bg = (24, 28, 40, 240) if is_sel else (12, 14, 20, 220)
            c_border = HollowColors.GOLD_CREST if is_sel else (50, 58, 74)

            HollowCrestRenderer.draw_filigree_panel(surface, pygame.Rect(card_rect), bg_color=c_bg, border_color=c_border, corner_flourish=is_sel)

            t_img = self.thumbnails.get(cid)
            if t_img:
                surface.blit(t_img, (card_rect.x + (card_rect.width - t_img.get_width()) // 2, card_rect.y + 3))

            sn = short_names.get(cid, cid[:4].upper())
            sn_surf = get_cached_text(self.font_badge, sn, HollowColors.GOLD_CREST if is_sel else (150, 160, 180))
            surface.blit(sn_surf, (card_rect.x + (card_rect.width - sn_surf.get_width()) // 2, card_rect.y + 30))

            if is_sel:
                HollowCrestRenderer.draw_selection_marker(surface, card_rect.centerx, card_rect.top - 2, size=3.0)

    def _draw_character_dossier(self, surface: pygame.Surface):
        """Draws full 390px Dossier occupying x=240..630 with word-wrapped passive and full skill names."""
        dx = 240
        dy = 42
        dw = 390
        dh = 286

        dossier_rect = pygame.Rect(dx, dy, dw, dh)
        HollowCrestRenderer.draw_filigree_panel(surface, dossier_rect, bg_color=(10, 12, 18, 240), border_color=(75, 82, 100), corner_flourish=True)

        # Name and Title
        name_surf = get_cached_text(self.font_name, self.profile.name.upper(), HollowColors.TEXT_TITLE)
        surface.blit(name_surf, (dx + 12, dy + 6))
        title_surf = get_cached_text(self.font_desc, self.profile.title, HollowColors.TEXT_NORMAL)
        surface.blit(title_surf, (dx + 12, dy + 22))

        # Archetype badge at top right
        arch_map = {
            "warrior": "VALQUÍRIA", "mage": "MAGA", "shinobi": "SHINOBI", "samurai": "SAMURAI",
            "fighter": "LUTADOR", "healer": "SACERDOTISA", "archer": "ARQUEIRO",
            "support": "ARTÍFICE", "guardian": "GUARDIÃO"
        }
        badge_str = arch_map.get(self.profile.archetype, self.profile.archetype.upper())
        badge_surf = get_cached_text(self.font_key, f"‹ {badge_str} ›", HollowColors.GOLD_CREST)
        surface.blit(badge_surf, (dx + dw - badge_surf.get_width() - 12, dy + 8))

        pygame.draw.line(surface, (45, 52, 68), (dx + 10, dy + 38), (dx + dw - 10, dy + 38), 1)

        # Attributes HP, MP, SP
        stats = [
            ("VIDA", self.profile.hp_max, (225, 60, 60)),
            ("MANA", self.profile.mp_max, (60, 150, 245)),
            ("ESTAMINA", self.profile.sp_max, (45, 200, 95))
        ]
        sy = dy + 42
        for s_label, s_val, s_col in stats:
            lbl = get_cached_text(self.font_stat, s_label, HollowColors.TEXT_NORMAL)
            surface.blit(lbl, (dx + 12, sy))
            bx = dx + 82
            bw = 140
            bh = 6
            pygame.draw.rect(surface, (20, 24, 32), (bx, sy + 2, bw, bh), border_radius=1)
            fill_w = max(4, int(bw * max(0.0, min(1.0, s_val / 165.0))))
            pygame.draw.rect(surface, s_col, (bx, sy + 2, fill_w, bh), border_radius=1)
            pygame.draw.rect(surface, (60, 68, 85), (bx, sy + 2, bw, bh), 1, border_radius=1)
            val_surf = get_cached_text(self.font_key, str(s_val), HollowColors.TEXT_TITLE)
            surface.blit(val_surf, (bx + bw + 8, sy - 1))
            sy += 12

        # Passive Box with Automatic Word-Wrap (Guaranteed inside rect.right)
        px = dx + 10
        py = dy + 82
        pw = dw - 20
        ph = 44
        p_box_rect = pygame.Rect(px, py, pw, ph)
        pygame.draw.rect(surface, (14, 16, 24), p_box_rect, border_radius=2)
        pygame.draw.rect(surface, (55, 62, 78), p_box_rect, 1, border_radius=2)
        pygame.draw.rect(surface, HollowColors.GOLD_CREST, (px, py, 2, ph))

        p_title = f"PASSIVA: {self.profile.passive_name.upper()}"
        p_surf = get_cached_text(self.font_key, p_title, HollowColors.GOLD_CREST)
        surface.blit(p_surf, (px + 8, py + 3))

        # Word wrapped text container
        p_desc_rect = pygame.Rect(px + 8, py + 16, pw - 14, ph - 18)
        render_wrapped_text(surface, self.profile.passive_desc, self.font_desc, HollowColors.TEXT_NORMAL, p_desc_rect, line_height=12)

        pygame.draw.line(surface, (45, 52, 68), (dx + 10, dy + 132), (dx + dw - 10, dy + 132), 1)

        # 5 Combat Skills with FULL UNTRUNCATED NAMES
        sk_title = get_cached_text(self.font_subtitle, "HABILIDADES DE COMBATE:", HollowColors.TEXT_NORMAL)
        surface.blit(sk_title, (dx + 12, dy + 136))

        core_keys = ["j", "k", "e", "shift", "r"]
        sy = dy + 152
        for k in core_keys:
            if k in self.profile.skills:
                sk = self.profile.skills[k]
                is_ult = (k == "r")
                icon_surf = self.skill_icons.get(sk.icon_file, None)
                if icon_surf:
                    surface.blit(icon_surf, (dx + 10, sy))

                hk_name = f"[{'SHIFT' if k == 'shift' else k.upper()}]  {sk.name}"
                hk_surf = get_cached_text(self.font_key, hk_name, HollowColors.GOLD_CREST if is_ult else HollowColors.TEXT_TITLE)
                surface.blit(hk_surf, (dx + 32, sy + 3))

                if k == "j":
                    metric_str = f"{sk.damage} Dano"
                elif k == "k":
                    metric_str = f"{sk.damage} Dano | {sk.cost_value} MP"
                elif k == "e":
                    metric_str = f"{sk.damage} Dano | {sk.cost_value} {sk.cost_type}"
                elif k == "shift":
                    metric_str = f"Bloqueio 100% | {sk.cost_value} {sk.cost_type}"
                elif k == "r":
                    metric_str = f"{sk.damage} Dano | {sk.cost_value} MP"
                else:
                    metric_str = f"{sk.damage} Dano"

                metric_col = HollowColors.GOLD_CREST if is_ult else HollowColors.TEXT_NORMAL
                metric_surf = get_cached_text(self.font_key, metric_str, metric_col)
                surface.blit(metric_surf, (dx + dw - metric_surf.get_width() - 12, sy + 3))
                sy += 24

    def _draw_solo_action_buttons(self, surface: pygame.Surface):
        is_back_hov = self.btn_back_rect.collidepoint(pygame.mouse.get_pos())
        HollowCrestRenderer.draw_hollow_button(surface, pygame.Rect(self.btn_back_rect), "VOLTAR [ESC]", self.font_desc, is_hovered=is_back_hov)

        is_play_hov = self.btn_play_rect.collidepoint(pygame.mouse.get_pos())
        HollowCrestRenderer.draw_hollow_button(
            surface, pygame.Rect(self.btn_play_rect), "JOGAR [ENTER]", self.font_subtitle,
            is_hovered=is_play_hov,
            text_color=HollowColors.GOLD_CREST if is_play_hov else HollowColors.TEXT_TITLE
        )

    # =========================================================================
    # CO-OP SPLIT-SCREEN RENDERING (640x360 NATIVE)
    # =========================================================================
    def _draw_coop_screen(self, surface: pygame.Surface):
        # 1. Header with fixed title (no duplicate text)
        header_surf = get_cached_text(self.font_title, "SALA DOS HERÓIS — CO-OP LOCAL (2 JOGADORES)", HollowColors.TEXT_TITLE)
        surface.blit(header_surf, (self.width // 2 - header_surf.get_width() // 2, 4))

        # Mode Selector Pill in subtitle: < MODO: CAMPANHA NARRATIVA | MODO ARCADE >
        target_name = "CAMPANHA NARRATIVA PERSISTENTE" if self.coop_target == "campaign" else "MODO ARCADE"
        mode_pill_str = f"< MODO: {target_name} >   [TAB / Q / E TROCAR]"
        mode_surf = get_cached_text(self.font_key, mode_pill_str, HollowColors.GOLD_CREST)
        surface.blit(mode_surf, (self.width // 2 - mode_surf.get_width() // 2, 22))

        HollowCrestRenderer.draw_section_divider(surface, self.width // 2, 38, width=620, alpha=180)

        # 2. Player 1 Symmetrical Card (x=10..314, w=304, h=286)
        p1_rect = pygame.Rect(10, 42, 304, 286)
        draw_symmetrical_hero_card(
            surface=surface,
            rect=p1_rect,
            player_idx=0,
            profile=self.p1_profile,
            pedestal_pos=self.p1_pedestal_pos,
            player_entity=self.p1_player,
            is_ready=self.p1_ready,
            tag_name="JOGADOR 1 (P1)",
            tag_col=(140, 210, 255),
            ready_hint="[J/ESPAÇO]",
            cancel_hint="[K]",
            selected_idx=self.p1_selected_index,
            thumbnails=self.thumbnails,
            lighting=self.lighting
        )

        # Center Divider at x = 320
        div_x = 320
        pygame.draw.line(surface, (35, 42, 56), (div_x, 42), (div_x, 328), 1)
        pygame.draw.circle(surface, HollowColors.SILVER_CREST, (div_x, 180), 3)

        # 3. Player 2 Symmetrical Card (x=326..630, w=304, h=286)
        p2_rect = pygame.Rect(326, 42, 304, 286)
        draw_symmetrical_hero_card(
            surface=surface,
            rect=p2_rect,
            player_idx=1,
            profile=self.p2_profile,
            pedestal_pos=self.p2_pedestal_pos,
            player_entity=self.p2_player,
            is_ready=self.p2_ready,
            tag_name="JOGADOR 2 (P2)",
            tag_col=(255, 195, 110),
            ready_hint="[ENTER/NUM1]",
            cancel_hint="[NUM2]",
            selected_idx=self.p2_selected_index,
            thumbnails=self.thumbnails,
            lighting=self.lighting
        )

        # 4. Footer Bar (y=334..356)
        self._draw_coop_bottom_bar(surface)

    def _draw_coop_bottom_bar(self, surface: pygame.Surface):
        # Back button
        is_hov = self.btn_coop_back_rect.collidepoint(pygame.mouse.get_pos())
        HollowCrestRenderer.draw_hollow_button(surface, pygame.Rect(self.btn_coop_back_rect), "VOLTAR [ESC]", self.font_desc, is_hovered=is_hov)

        # Center status or Ready Banner
        if self.p1_ready and self.p2_ready:
            pulse = int(180 + 75 * math.sin(pygame.time.get_ticks() * 0.01))
            pulse_col = (255, min(255, pulse), 80)
            ready_msg = "✣ AMBOS PRONTOS! PRESSIONE [ESPAÇO] OU [ENTER] PARA JOGAR! ✣"
            r_surf = get_cached_text(self.font_subtitle, ready_msg, pulse_col)
            surface.blit(r_surf, (self.width // 2 - r_surf.get_width() // 2, 337))

            is_start_hov = self.btn_coop_start_rect.collidepoint(pygame.mouse.get_pos())
            HollowCrestRenderer.draw_hollow_button(
                surface, pygame.Rect(self.btn_coop_start_rect), "INICIAR CO-OP", self.font_subtitle,
                is_hovered=is_start_hov,
                text_color=HollowColors.GOLD_CREST if is_start_hov else HollowColors.TEXT_TITLE
            )
        else:
            p1_status = "✔ P1 Pronto" if self.p1_ready else "P1 Escolhendo..."
            p2_status = "✔ P2 Pronto" if self.p2_ready else "P2 Escolhendo..."
            status_msg = f"{p1_status}   •   {p2_status}   |   P1: [W/A/S/D] [J]  P2: [Setas] [Enter]"
            s_surf = get_cached_text(self.font_desc, status_msg, HollowColors.TEXT_NORMAL)
            surface.blit(s_surf, (self.width // 2 - s_surf.get_width() // 2, 338))
