"""
src/scenes/duel_character_select_scene.py
-----------------------------------------
1v1 Local Versus Character Select Scene.
Unified with Co-op visual architecture:
- Dual symmetrical 304px panels (P1 on Left, P2 on Right) with independent pedestals & animated standees.
- Real bust/head thumbnails for all 11 roster heroes (zero geometric placeholders or target circles).
- Live Arena background rendered in real time with Parallax autoscroll, Mist and Silksong Lighting
  (switches instantly between Costa dos Bambus, As Catacumbas, and Fortaleza Esmeralda via [Q / E]).
- Full character summary: Passive with automatic word-wrap and compact list of 5 Combat Abilities.
- Central metallic gold VS emblem and synchronized match countdown.
"""

import math
import os
import random
from typing import Dict, List, Tuple, Optional
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
from engine.text_cache import get_cached_text
from ui.hollow_ui import HollowFonts, HollowCrestRenderer, HollowColors
from ui.selection_helpers import (
    get_hero_thumbnails,
    draw_pedestal_with_beam,
    draw_live_stage_background,
    draw_symmetrical_hero_card
)

ROSTER_GRID = [
    ["shaia", "lunaria", "ignis", "random", "astra", "shinobi", "samurai"],
    ["fighter", "knight", "wizard", "skeleton_king", "samurai_archer", "kunoichi", "random"]
]

ROSTER_INFO = {
    cid: {"name": CHARACTER_REGISTRY[cid].name.upper(), "title": CHARACTER_REGISTRY[cid].title, "color": CHARACTER_REGISTRY[cid].color_theme}
    for cid in CHARACTER_ORDER
}
ROSTER_INFO["random"] = {"name": "ALEATÓRIO", "title": "Destino Incerto", "color": (180, 190, 205)}
ROSTER_INFO["skeleton_king"] = {"name": "REI ESQUELETO", "title": "Lorde das Catacumbas", "color": (180, 50, 45)}

ARENAS = [
    {"id": "terrae_1", "name": "COSTA DOS BAMBUS", "catalog_id": "terrae_1"},
    {"id": "catacombs", "name": "AS CATACUMBAS", "catalog_id": "sanguis_3"},
    {"id": "terrae_3", "name": "FORTALEZA ESMERALDA", "catalog_id": "terrae_3"}
]

class DuelCharacterSelectScene(Scene):
    """Competitive 1v1 Local Versus Character Select Scene."""
    internal_size = (640, 360)

    def __init__(self, scene_manager, previous_scene=None):
        self.scene_manager = scene_manager
        self.previous_scene = previous_scene

        self.width = 640
        self.height = 360

        pygame.font.init()
        self.font_title = HollowFonts.get(16, bold=True)
        self.font_subtitle = HollowFonts.get(10)
        self.font_key = HollowFonts.get(8, bold=True)
        self.font_desc = HollowFonts.get(9)

        # Arena Selection
        self.selected_arena_idx = 0
        self.cam_x = 0.0

        # Cursors for 11 heroes (P1 at index 0, P2 at index 6)
        self.p1_selected_index = 0
        self.p2_selected_index = 6

        self.p1_ready = False
        self.p2_ready = False
        self.both_ready_timer = 0.0
        self.time_sec = 0.0

        # Pedestal positions inside each 304px card
        self.p1_pedestal_pos = pygame.math.Vector2(68, 125)
        self.p2_pedestal_pos = pygame.math.Vector2(384, 125)

        self.dummy_tiles_p1 = [pygame.FRect(15, 130, 110, 40)]
        self.dummy_tiles_p2 = [pygame.FRect(330, 130, 110, 40)]

        # Authentic portraits & skill icons
        self.thumbnails = get_hero_thumbnails()

        # Buttons
        self.btn_back_rect = pygame.FRect(10, 334, 110, 22)
        self.btn_start_rect = pygame.FRect(510, 334, 120, 22)

        # Load initial live stage background
        self._load_active_arena_background()

        # Instantiate real animated Player previews
        self._spawn_duel_players()

    @property
    def p1_pos(self) -> List[int]:
        row = 0 if self.p1_selected_index < 7 else 1
        col = self.p1_selected_index if row == 0 else (self.p1_selected_index - 7)
        return [row, col]

    @p1_pos.setter
    def p1_pos(self, pos: List[int]) -> None:
        idx = pos[0] * 7 + pos[1]
        self.p1_selected_index = idx % len(CHARACTER_ORDER)

    @property
    def p2_pos(self) -> List[int]:
        row = 0 if self.p2_selected_index < 7 else 1
        col = self.p2_selected_index if row == 0 else (self.p2_selected_index - 7)
        return [row, col]

    @p2_pos.setter
    def p2_pos(self, pos: List[int]) -> None:
        idx = pos[0] * 7 + pos[1]
        self.p2_selected_index = idx % len(CHARACTER_ORDER)

    def _load_active_arena_background(self):
        """Loads live parallax layers, mist, and lighting for the selected arena."""
        arena_info = ARENAS[self.selected_arena_idx]
        cat_id = arena_info["catalog_id"]
        stage_cfg = STAGE_CATALOG.get(cat_id, STAGE_CATALOG.get("terrae_1"))

        theme = getattr(stage_cfg, "biome_theme", "road") if stage_cfg else "road"
        self.parallax = None
        self.clouds = None
        self.mist = None

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
                sky_horizon_y=getattr(stage_cfg, "sky_horizon_y", 70),
                cloud_tint=getattr(stage_cfg, "cloud_tint", None),
                cloud_opacity_scale=getattr(stage_cfg, "cloud_opacity_scale", 0.50)
            )
            self.mist = MistManager(screen_w=640, screen_h=360, floor_y=280, theme=theme)

        self.lighting = LightingEngine(theme=theme, screen_w=640, screen_h=360, floor_y=280)

    def _spawn_duel_players(self):
        """Instantiates real animated Player objects on pedestals."""
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

    def _select_p1_character(self, index: int):
        if self.p1_ready:
            return
        self.p1_selected_index = index % len(CHARACTER_ORDER)
        self._spawn_duel_players()

    def _select_p2_character(self, index: int):
        if self.p2_ready:
            return
        self.p2_selected_index = index % len(CHARACTER_ORDER)
        self._spawn_duel_players()

    def _change_arena(self, delta: int):
        self.selected_arena_idx = (self.selected_arena_idx + delta) % len(ARENAS)
        self._load_active_arena_background()

    def _confirm_and_play(self):
        """Launches the 1v1 Duel Scene with chosen fighters and arena."""
        p1_char = CHARACTER_ORDER[self.p1_selected_index]
        p2_char = CHARACTER_ORDER[self.p2_selected_index]
        arena_id = ARENAS[self.selected_arena_idx]["id"]

        SETTINGS.CURRENT_CHARACTER = p1_char
        SETTINGS.P2_CHARACTER = p2_char
        SETTINGS.DUEL_MODE = True
        SETTINGS.COOP_ENABLED = False

        from scenes.duel_scene import DuelScene
        self.scene_manager.change_scene(DuelScene(self.scene_manager, p1_char, p2_char, arena_id))

    def _go_back(self):
        if self.previous_scene:
            self.scene_manager.change_scene(self.previous_scene)
        else:
            from scenes.main_menu import MainMenuScene
            self.scene_manager.change_scene(MainMenuScene(self.scene_manager))

    def handle_events(self, events: List[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.p1_ready or self.p2_ready:
                        self.p1_ready = False
                        self.p2_ready = False
                        self.both_ready_timer = 0.0
                    else:
                        self._go_back()
                    return

                # Arena selection toggles [Q / E]
                if not (self.p1_ready and self.p2_ready):
                    if event.key == pygame.K_q:
                        self._change_arena(-1)
                        return
                    elif event.key == pygame.K_e:
                        self._change_arena(1)
                        return

                if self.p1_ready and self.p2_ready:
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                        self._confirm_and_play()
                        return

                # --- P1 CONTROLS: WASD + J/SPACE (Ready) + K (Cancel) ---
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
                        self.both_ready_timer = 0.0

                # --- P2 CONTROLS: ARROWS + ENTER/NUM1 (Ready) + NUM2 (Cancel) ---
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
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_KP1):
                        self.p2_ready = True
                else:
                    if event.key in (pygame.K_KP2, pygame.K_BACKSPACE):
                        self.p2_ready = False
                        self.both_ready_timer = 0.0

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if self.btn_back_rect.collidepoint(mx, my):
                    self._go_back()
                    return
                if self.p1_ready and self.p2_ready and self.btn_start_rect.collidepoint(mx, my):
                    self._confirm_and_play()
                    return

                # P1 cards click
                if not self.p1_ready:
                    for idx in range(len(CHARACTER_ORDER)):
                        r = self._get_duel_card_rect(idx, player_idx=0)
                        if r.collidepoint(mx, my):
                            self._select_p1_character(idx)
                            break

                # P2 cards click
                if not self.p2_ready:
                    for idx in range(len(CHARACTER_ORDER)):
                        r = self._get_duel_card_rect(idx, player_idx=1)
                        if r.collidepoint(mx, my):
                            self._select_p2_character(idx)
                            break

    def _get_duel_card_rect(self, index: int, player_idx: int) -> pygame.FRect:
        base_x = 19 if player_idx == 0 else 335
        grid_y = 264
        col = index % 6
        row = index // 6
        cx = base_x + col * 48
        cy = grid_y + row * 31
        return pygame.FRect(cx, cy, 44, 28)

    def update(self, dt: float) -> None:
        self.time_sec += dt
        self.cam_x += 12.0 * dt

        if self.clouds:
            self.clouds.update(dt)
        if self.mist:
            self.mist.update(dt)
        if self.lighting:
            self.lighting.update(dt)

        self.p1_player.update(dt, self.dummy_tiles_p1)
        self.p1_player.pos.x = self.p1_pedestal_pos.x - 16
        self.p1_player.rect.x = self.p1_player.pos.x

        self.p2_player.update(dt, self.dummy_tiles_p2)
        self.p2_player.pos.x = self.p2_pedestal_pos.x - 16
        self.p2_player.rect.x = self.p2_player.pos.x

        # Both ready countdown
        if self.p1_ready and self.p2_ready:
            self.both_ready_timer += dt
            if self.both_ready_timer >= 1.0:
                self._confirm_and_play()
        else:
            self.both_ready_timer = 0.0

    def draw(self, surface: pygame.Surface) -> None:
        # 1. Real Live Stage Background with autoscroll and lighting
        draw_live_stage_background(surface, self.parallax, self.cam_x, self.lighting, self.mist, self.clouds)

        # 2. Header
        header_surf = get_cached_text(self.font_title, "MODO DE DUELO — CONFRONTO 1 VS 1", (245, 215, 120))
        surface.blit(header_surf, (self.width // 2 - header_surf.get_width() // 2, 4))

        arena_info = ARENAS[self.selected_arena_idx]
        arena_str = f"ARENA:  < {arena_info['name']} >   [Q / E TROCAR]"
        arena_surf = get_cached_text(self.font_key, arena_str, (170, 205, 245))
        surface.blit(arena_surf, (self.width // 2 - arena_surf.get_width() // 2, 22))

        HollowCrestRenderer.draw_section_divider(surface, self.width // 2, 38, width=620, alpha=180)

        # 3. Player 1 Symmetrical Card (x=10..314)
        p1_rect = pygame.Rect(10, 42, 304, 286)
        draw_symmetrical_hero_card(
            surface=surface,
            rect=p1_rect,
            player_idx=0,
            profile=self.p1_profile,
            pedestal_pos=self.p1_pedestal_pos,
            player_entity=self.p1_player,
            is_ready=self.p1_ready,
            tag_name="LUTADOR 1 (P1)",
            tag_col=(255, 80, 90),
            ready_hint="[J/ESPAÇO]",
            cancel_hint="[K]",
            selected_idx=self.p1_selected_index,
            thumbnails=self.thumbnails,
            lighting=self.lighting,
            time_sec=self.time_sec
        )

        # Center Divider at x = 320
        div_x = 320
        pygame.draw.line(surface, (45, 52, 68), (div_x, 42), (div_x, 328), 1)

        # 4. Central Metallic Pulsing "VS" Crest
        pulse = 1.0 + math.sin(self.time_sec * 4.0) * 0.08
        vs_rad = int(22 * pulse)
        vs_surf = pygame.Surface((vs_rad * 2 + 10, vs_rad * 2 + 10), pygame.SRCALPHA)
        vsc = vs_rad + 5
        pygame.draw.circle(vs_surf, (25, 20, 30, 220), (vsc, vsc), vs_rad)
        pygame.draw.circle(vs_surf, (245, 195, 65), (vsc, vsc), vs_rad, width=2)
        pygame.draw.circle(vs_surf, (255, 235, 150), (vsc, vsc), vs_rad - 3, width=1)
        f_vs = HollowFonts.get(int(15 * pulse), bold=True)
        vs_txt = f_vs.render("VS", True, (255, 230, 110))
        vs_surf.blit(vs_txt, vs_txt.get_rect(center=(vsc, vsc)))
        surface.blit(vs_surf, vs_surf.get_rect(center=(div_x, 140)), special_flags=pygame.BLEND_RGBA_ADD)

        # 5. Player 2 Symmetrical Card (x=326..630)
        p2_rect = pygame.Rect(326, 42, 304, 286)
        draw_symmetrical_hero_card(
            surface=surface,
            rect=p2_rect,
            player_idx=1,
            profile=self.p2_profile,
            pedestal_pos=self.p2_pedestal_pos,
            player_entity=self.p2_player,
            is_ready=self.p2_ready,
            tag_name="LUTADOR 2 (P2)",
            tag_col=(80, 170, 255),
            ready_hint="[ENTER/NUM1]",
            cancel_hint="[NUM2]",
            selected_idx=self.p2_selected_index,
            thumbnails=self.thumbnails,
            lighting=self.lighting,
            time_sec=self.time_sec
        )

        # 6. Bottom Action / Status Bar
        self._draw_bottom_bar(surface)

    def _draw_bottom_bar(self, surface: pygame.Surface):
        is_hov = self.btn_back_rect.collidepoint(pygame.mouse.get_pos())
        HollowCrestRenderer.draw_hollow_button(surface, pygame.Rect(self.btn_back_rect), "VOLTAR [ESC]", self.font_desc, is_hovered=is_hov)

        if self.p1_ready and self.p2_ready:
            pulse = int(180 + 75 * math.sin(self.time_sec * 10.0))
            pulse_col = (255, min(255, pulse), 80)
            ready_msg = "⚔ COMBATENTES PRONTOS! PRESSIONE [ESPAÇO] OU [ENTER]! ⚔"
            r_surf = get_cached_text(self.font_subtitle, ready_msg, pulse_col)
            surface.blit(r_surf, (self.width // 2 - r_surf.get_width() // 2, 337))

            is_start_hov = self.btn_start_rect.collidepoint(pygame.mouse.get_pos())
            HollowCrestRenderer.draw_hollow_button(
                surface, pygame.Rect(self.btn_start_rect), "INICIAR DUELO", self.font_subtitle,
                is_hovered=is_start_hov,
                text_color=HollowColors.GOLD_CREST if is_start_hov else HollowColors.TEXT_TITLE
            )
        else:
            p1_status = "✔ P1 Pronto" if self.p1_ready else "P1 Escolhendo..."
            p2_status = "✔ P2 Pronto" if self.p2_ready else "P2 Escolhendo..."
            status_msg = f"{p1_status}   •   {p2_status}   |   P1: [W/A/S/D] [J]   P2: [Setas] [Enter]"
            s_surf = get_cached_text(self.font_desc, status_msg, HollowColors.TEXT_NORMAL)
            surface.blit(s_surf, (self.width // 2 - s_surf.get_width() // 2, 338))
