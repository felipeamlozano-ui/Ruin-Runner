"""
src/scenes/duel_character_select_scene.py
-----------------------------------------
Mortal Kombat style 1v1 Local Versus Character Selection Scene.
Features:
- Dual independent cursors: Red P1 (WASD + J/Space) and Blue P2 (Arrows + Enter/Num1).
- 2x7 Roster Grid with Hero & Boss Portraits and central '?' Random slots.
- Center Matchup area: P1 vs P2 facing each other with metallic gold 'VS' crest.
- Stage / Arena selector (Costa dos Bambus, Catacumbas, Fortaleza Esmeralda).
- Seamless launch into DuelScene when both fighters are Ready.
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
from entities.character_data import CHARACTER_REGISTRY, get_character_profile
from ui.hollow_ui import HollowFonts, HollowCrestRenderer, AtmosphereFX, HollowColors

ROSTER_GRID = [
    ["shaia", "lunaria", "ignis", "random", "astra", "shinobi", "samurai"],
    ["fighter", "knight", "wizard", "skeleton_king", "samurai_archer", "kunoichi", "random"]
]

ROSTER_INFO = {
    "shaia": {"name": "SHAIA", "title": "Espadachim Carmesim", "color": (235, 65, 75)},
    "lunaria": {"name": "LUNARIA", "title": "Valquíria da Lua", "color": (130, 205, 255)},
    "ignis": {"name": "IGNIS", "title": "Mago Piromante", "color": (255, 120, 45)},
    "astra": {"name": "ASTRA", "title": "Feiticeira Cósmica", "color": (195, 130, 255)},
    "shinobi": {"name": "SHINOBI", "title": "Ninja das Sombras", "color": (110, 140, 175)},
    "samurai": {"name": "SAMURAI", "title": "Mestre da Katana", "color": (245, 185, 70)},
    "fighter": {"name": "GUERREIRA", "title": "Bárbara Indomável", "color": (220, 110, 80)},
    "knight": {"name": "CAVALEIRO", "title": "Paladino Sagrado", "color": (240, 225, 140)},
    "wizard": {"name": "MAGO", "title": "Necromante Arcano", "color": (160, 95, 240)},
    "skeleton_king": {"name": "REI ESQUELETO", "title": "Lorde das Catacumbas", "color": (180, 50, 45)},
    "samurai_archer": {"name": "ARQUEIRO", "title": "Arqueiro Imperial", "color": (80, 190, 120)},
    "kunoichi": {"name": "KUNOICHI", "title": "Assassina das Sombras", "color": (225, 80, 160)},
    "random": {"name": "ALEATÓRIO", "title": "Destino Incerto", "color": (180, 190, 205)}
}

ARENAS = [
    {"id": "terrae_1", "name": "COSTA DOS BAMBUS", "theme": "road"},
    {"id": "catacombs", "name": "AS CATACUMBAS", "theme": "dungeon"},
    {"id": "terrae_3", "name": "FORTALEZA ESMERALDA", "theme": "castle"}
]

class DuelCharacterSelectScene(Scene):
    """Mortal Kombat Style 1v1 Local Versus Character Select Scene."""
    internal_size = (640, 360)

    def __init__(self, scene_manager, previous_scene=None):
        self.scene_manager = scene_manager
        self.previous_scene = previous_scene

        self.width = 640
        self.height = 360

        # Atmospheric Ember & Smoke FX
        self.atmosphere = AtmosphereFX(self.width, self.height, theme="ember", particle_count=40)

        # Independent cursors: (row, col)
        self.p1_pos = [0, 0]
        self.p2_pos = [0, 6]
        self.p1_ready = False
        self.p2_ready = False
        self.both_ready_timer = 0.0

        # Arena Selection
        self.selected_arena_idx = 0

        # Cached portraits & preview surfaces
        self.portraits: Dict[str, pygame.Surface] = {}
        self.previews: Dict[str, pygame.Surface] = {}
        self._load_portraits()

        self.time_sec = 0.0

    def _load_portraits(self):
        """Pre-renders or loads pixel-art portraits for each roster fighter."""
        cell_w, cell_h = 44, 44
        for row in ROSTER_GRID:
            for char_id in row:
                if char_id in self.portraits:
                    continue
                info = ROSTER_INFO.get(char_id, ROSTER_INFO["random"])
                surf = pygame.Surface((cell_w, cell_h))
                surf.fill((16, 18, 26))

                # Border with theme color
                c = info["color"]
                pygame.draw.rect(surf, c, (0, 0, cell_w, cell_h), width=2)
                pygame.draw.rect(surf, (30, 34, 46), (2, 2, cell_w - 4, cell_h - 4))

                if char_id == "random":
                    f = HollowFonts.get(22, bold=True)
                    txt = f.render("?", True, (240, 245, 255))
                    surf.blit(txt, txt.get_rect(center=(cell_w // 2, cell_h // 2)))
                else:
                    # Render character emblem/icon
                    f = HollowFonts.get(10, bold=True)
                    short_name = info["name"][:5]
                    txt = f.render(short_name, True, c)
                    surf.blit(txt, txt.get_rect(center=(cell_w // 2, cell_h - 10)))
                    # Small stylized avatar icon in center
                    pygame.draw.circle(surf, c, (cell_w // 2, cell_h // 2 - 4), 10)
                    pygame.draw.circle(surf, (20, 22, 30), (cell_w // 2, cell_h // 2 - 4), 8)
                    pygame.draw.circle(surf, (255, 255, 255), (cell_w // 2, cell_h // 2 - 4), 4)

                self.portraits[char_id] = surf

    def _get_resolved_character(self, pos: List[int]) -> str:
        char_id = ROSTER_GRID[pos[0]][pos[1]]
        if char_id == "random":
            valid = [c for r in ROSTER_GRID for c in r if c != "random"]
            return random.choice(valid)
        return char_id

    def handle_events(self, events: List[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    from scenes.main_menu import MainMenuScene
                    self.scene_manager.change_scene(MainMenuScene(self.scene_manager))
                    return

                # Arena selection toggles [Q / E]
                if event.key == pygame.K_q and not (self.p1_ready and self.p2_ready):
                    self.selected_arena_idx = (self.selected_arena_idx - 1) % len(ARENAS)
                elif event.key == pygame.K_e and not (self.p1_ready and self.p2_ready):
                    self.selected_arena_idx = (self.selected_arena_idx + 1) % len(ARENAS)

                # --- P1 CONTROLS (WASD + J/SPACE) ---
                if not self.p1_ready:
                    if event.key == pygame.K_w:
                        self.p1_pos[0] = (self.p1_pos[0] - 1) % len(ROSTER_GRID)
                    elif event.key == pygame.K_s:
                        self.p1_pos[0] = (self.p1_pos[0] + 1) % len(ROSTER_GRID)
                    elif event.key == pygame.K_a:
                        self.p1_pos[1] = (self.p1_pos[1] - 1) % len(ROSTER_GRID[0])
                    elif event.key == pygame.K_d:
                        self.p1_pos[1] = (self.p1_pos[1] + 1) % len(ROSTER_GRID[0])
                    elif event.key in (pygame.K_j, pygame.K_SPACE):
                        self.p1_ready = True
                else:
                    # Cancel ready with movement or K
                    if event.key in (pygame.K_k, pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d):
                        self.p1_ready = False
                        self.both_ready_timer = 0.0

                # --- P2 CONTROLS (ARROWS + ENTER/NUMPAD1/U) ---
                if not self.p2_ready:
                    if event.key == pygame.K_UP:
                        self.p2_pos[0] = (self.p2_pos[0] - 1) % len(ROSTER_GRID)
                    elif event.key == pygame.K_DOWN:
                        self.p2_pos[0] = (self.p2_pos[0] + 1) % len(ROSTER_GRID)
                    elif event.key == pygame.K_LEFT:
                        self.p2_pos[1] = (self.p2_pos[1] - 1) % len(ROSTER_GRID[0])
                    elif event.key == pygame.K_RIGHT:
                        self.p2_pos[1] = (self.p2_pos[1] + 1) % len(ROSTER_GRID[0])
                    elif event.key in (pygame.K_RETURN, pygame.K_KP1, pygame.K_u):
                        self.p2_ready = True
                else:
                    # Cancel ready with movement or I/Num2
                    if event.key in (pygame.K_i, pygame.K_KP2, pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):
                        self.p2_ready = False
                        self.both_ready_timer = 0.0

    def update(self, dt: float) -> None:
        self.time_sec += dt
        self.atmosphere.update(dt)

        # Transition countdown when both fighters confirm
        if self.p1_ready and self.p2_ready:
            self.both_ready_timer += dt
            if self.both_ready_timer >= 1.0:
                p1_char = self._get_resolved_character(self.p1_pos)
                p2_char = self._get_resolved_character(self.p2_pos)
                arena = ARENAS[self.selected_arena_idx]["id"]
                from scenes.duel_scene import DuelScene
                self.scene_manager.change_scene(DuelScene(self.scene_manager, p1_char, p2_char, arena))

    def draw(self, surface: pygame.Surface) -> None:
        sw, sh = self.width, self.height
        cx = sw // 2

        # 1. Dark Atmosphere Background with Fiery Embers
        self.atmosphere.draw_background(surface, show_rays=False)

        # 2. Header: Title & Flourish
        HollowCrestRenderer.draw_top_flourish(surface, cx, 12, width=160)
        f_title = HollowFonts.get(16, bold=True)
        t_surf = f_title.render("MODO DE DUELO — CONFRONTO 1 VS 1", True, (245, 215, 120))
        surface.blit(t_surf, t_surf.get_rect(center=(cx, 26)))

        # Arena selector pill
        arena_info = ARENAS[self.selected_arena_idx]
        f_arena = HollowFonts.get(9, bold=True)
        a_txt = f_arena.render(f"ARENA:  < {arena_info['name']} >   [Q / E TROCAR]", True, (170, 195, 225))
        surface.blit(a_txt, a_txt.get_rect(center=(cx, 44)))

        # 3. Matchup Center Stage: P1 (Left) vs P2 (Right)
        p1_id = ROSTER_GRID[self.p1_pos[0]][self.p1_pos[1]]
        p2_id = ROSTER_GRID[self.p2_pos[0]][self.p2_pos[1]]
        p1_info = ROSTER_INFO.get(p1_id, ROSTER_INFO["random"])
        p2_info = ROSTER_INFO.get(p2_id, ROSTER_INFO["random"])

        p1_x, p1_y = 120, 140
        p2_x, p2_y = 520, 140

        # Pedestals
        pygame.draw.ellipse(surface, (20, 24, 34), (p1_x - 55, p1_y + 20, 110, 24))
        pygame.draw.ellipse(surface, (235, 65, 75, 80), (p1_x - 55, p1_y + 20, 110, 24), width=2)
        pygame.draw.ellipse(surface, (20, 24, 34), (p2_x - 55, p2_y + 20, 110, 24))
        pygame.draw.ellipse(surface, (65, 145, 245, 80), (p2_x - 55, p2_y + 20, 110, 24), width=2)

        # Draw Fighter Previews / Standees
        self._draw_fighter_standee(surface, p1_id, p1_x, p1_y, facing_right=True, is_ready=self.p1_ready)
        self._draw_fighter_standee(surface, p2_id, p2_x, p2_y, facing_right=False, is_ready=self.p2_ready)

        # Fighter Titles & Statuses
        f_name = HollowFonts.get(12, bold=True)
        f_sub = HollowFonts.get(9)

        # P1 Name Box
        n1 = f_name.render(p1_info["name"], True, p1_info["color"])
        s1 = f_sub.render(p1_info["title"], True, (160, 175, 195))
        surface.blit(n1, n1.get_rect(center=(p1_x, p1_y + 52)))
        surface.blit(s1, s1.get_rect(center=(p1_x, p1_y + 68)))
        if self.p1_ready:
            r1 = f_name.render("PRONTO!", True, (80, 245, 130))
            surface.blit(r1, r1.get_rect(center=(p1_x, p1_y - 45)))

        # P2 Name Box
        n2 = f_name.render(p2_info["name"], True, p2_info["color"])
        s2 = f_sub.render(p2_info["title"], True, (160, 175, 195))
        surface.blit(n2, n2.get_rect(center=(p2_x, p2_y + 52)))
        surface.blit(s2, s2.get_rect(center=(p2_x, p2_y + 68)))
        if self.p2_ready:
            r2 = f_name.render("PRONTO!", True, (80, 245, 130))
            surface.blit(r2, r2.get_rect(center=(p2_x, p2_y - 45)))

        # Central Metallic "VS" Emblem with Radiant Pulse
        pulse = 1.0 + math.sin(self.time_sec * 4.0) * 0.08
        vs_rad = int(32 * pulse)
        vs_surf = pygame.Surface((vs_rad * 2 + 10, vs_rad * 2 + 10), pygame.SRCALPHA)
        vsc = vs_rad + 5
        pygame.draw.circle(vs_surf, (25, 20, 30, 220), (vsc, vsc), vs_rad)
        pygame.draw.circle(vs_surf, (245, 195, 65), (vsc, vsc), vs_rad, width=3)
        pygame.draw.circle(vs_surf, (255, 235, 150), (vsc, vsc), vs_rad - 4, width=1)
        f_vs = HollowFonts.get(int(22 * pulse), bold=True)
        vs_txt = f_vs.render("VS", True, (255, 230, 110))
        vs_surf.blit(vs_txt, vs_txt.get_rect(center=(vsc, vsc)))
        surface.blit(vs_surf, vs_surf.get_rect(center=(cx, 136)), special_flags=pygame.BLEND_RGBA_ADD)

        # 4. Bottom Roster Grid (2 rows x 7 cols)
        grid_start_x = cx - (7 * 48) // 2 + 4
        grid_start_y = 230
        cell_size = 44
        gap = 4

        for r_idx, row in enumerate(ROSTER_GRID):
            for c_idx, char_id in enumerate(row):
                gx = grid_start_x + c_idx * (cell_size + gap)
                gy = grid_start_y + r_idx * (cell_size + gap)
                rect = pygame.Rect(gx, gy, cell_size, cell_size)

                # Draw portrait
                port = self.portraits.get(char_id)
                if port:
                    surface.blit(port, rect)

                # Draw P1 Cursor (Red)
                if self.p1_pos == [r_idx, c_idx]:
                    glow = int(180 + math.sin(self.time_sec * 8.0) * 60)
                    pygame.draw.rect(surface, (255, 50, 60, glow), rect.inflate(6, 6), width=3)
                    p1_badge = HollowFonts.get(8, bold=True).render("P1", True, (255, 255, 255))
                    surface.blit(p1_badge, (rect.left + 2, rect.top + 2))

                # Draw P2 Cursor (Blue)
                if self.p2_pos == [r_idx, c_idx]:
                    glow = int(180 + math.cos(self.time_sec * 8.0) * 60)
                    pygame.draw.rect(surface, (50, 150, 255, glow), rect.inflate(10 if self.p1_pos == [r_idx, c_idx] else 6, 10 if self.p1_pos == [r_idx, c_idx] else 6), width=3)
                    p2_badge = HollowFonts.get(8, bold=True).render("P2", True, (255, 255, 255))
                    surface.blit(p2_badge, (rect.right - 14, rect.top + 2))

        # 5. Bottom Instructions Footer
        f_foot = HollowFonts.get(9)
        foot_txt = f_foot.render("P1: [W/A/S/D] MOVER  [J/ESPAÇO] CONFIRMAR   |   P2: [SETAS] MOVER  [ENTER/NUM1] CONFIRMAR", True, (140, 155, 175))
        surface.blit(foot_txt, foot_txt.get_rect(center=(cx, sh - 14)))

        # Dramatic countdown overlay if both ready
        if self.p1_ready and self.p2_ready:
            rem = max(0.0, 1.0 - self.both_ready_timer)
            cd_surf = f_title.render("COMBATE INICIANDO...", True, (255, 230, 110))
            surface.blit(cd_surf, cd_surf.get_rect(center=(cx, 204)))

    def _draw_fighter_standee(self, surface: pygame.Surface, char_id: str, x: int, y: int, facing_right: bool, is_ready: bool):
        """Draws a standee or placeholder silhouette of the fighter on the pedestal."""
        info = ROSTER_INFO.get(char_id, ROSTER_INFO["random"])
        c = info["color"]

        # Simple pixel standee silhouette (60x70)
        standee = pygame.Surface((60, 70), pygame.SRCALPHA)
        # Cloak / Armor
        pygame.draw.polygon(standee, (*c, 210), [(30, 15), (52, 65), (8, 65)])
        # Head
        pygame.draw.circle(standee, (240, 230, 210), (30, 16), 11)
        # Visor / Mask
        pygame.draw.rect(standee, (20, 20, 25), (24 if facing_right else 20, 14, 14, 5))
        # Weapon glow
        if facing_right:
            pygame.draw.line(standee, (255, 255, 255), (46, 25), (55, 60), 3)
        else:
            pygame.draw.line(standee, (255, 255, 255), (14, 25), (5, 60), 3)

        rect = standee.get_rect(center=(x, y - 5))
        surface.blit(standee, rect)
