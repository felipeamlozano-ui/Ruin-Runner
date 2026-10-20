"""
Ruin Engine — Boss Selection Scene (Batalha de Chefe / Boss Rush).
Allows the player to directly select and duel any of the 5 game bosses.
Native 640x360 (16:9) layout.
"""

import pygame
import math
from engine.scene_manager import Scene
from config.settings import SETTINGS
from scenes.boss_scene import BossScene


BOSS_ROSTER = [
    {
        "id": "demon_slime",
        "name": "O Titã Demoníaco",
        "title": "SENHOR DO MAGMA ANCESTRAL",
        "world": "Mundo 1: Terrae",
        "desc": "Um colosso colossal forjado no núcleo vulcânico de Terrae. Desfere cortes flamejantes com sua espada abissal e erupções de fogo no solo. Entra em fúria incandescente com menos de 50% de HP.",
        "difficulty": "Normal (Nível I)",
        "color": (255, 100, 40),
    },
    {
        "id": "skeleton_king",
        "name": "O Rei Esqueleto",
        "title": "SOBERANO DAS CATACUMBAS",
        "world": "Mundo 2: Sanguis",
        "desc": "O lendário governante das ruínas ancestrais. Protegido por um escudo de poise impenetrável, desfere combos devastadores de montante, saltos esmagadores e invoca hordas de guerreiros esqueléticos.",
        "difficulty": "Difícil (Nível II)",
        "color": (240, 220, 160),
    },
    {
        "id": "monster_creature",
        "name": "O Monstro Quimérico Ancestral",
        "title": "PREDADOR DO ABISMO GELADO",
        "world": "Mundo 3: Glacies",
        "desc": "Fera descomunal que hibernava nas geleiras profundas de Glacies. Causa tremores violentos com pisões terrestres e cospe jatos de veneno viscoso que desaceleram e desgastam a armadura.",
        "difficulty": "Muito Difícil (Nível III)",
        "color": (90, 200, 255),
    },
    {
        "id": "samurai",
        "name": "Lorde Samurai Amaldiçoado",
        "title": "MESTRE DO CORTE RELÂMPAGO",
        "world": "Mundo 4: Aetheria",
        "desc": "Guerreiro imortal que guardava o templo celestial. Utiliza a técnica suprema de corte desembainhado (Iaido), investidas fantasmas e disparos cortantes de lâminas de ar que cobrem toda a arena.",
        "difficulty": "Extremo (Nível IV)",
        "color": (255, 190, 60),
    },
]


class BossSelectScene(Scene):
    """Scene for directly selecting and fighting any of the 5 bosses."""

    internal_size = (640, 360)

    def __init__(self, scene_manager, return_scene=None):
        self.scene_manager = scene_manager
        self.return_scene = return_scene
        self.width = 640
        self.height = 360
        self.bosses = BOSS_ROSTER
        self.selected_index = 0
        self.time_sec = 0.0

        from ui.hollow_ui import AtmosphereFX, HollowFonts, HollowCrestRenderer, HollowColors
        self.fx = AtmosphereFX(width=640, height=360, theme="ember", particle_count=42)
        self._init_fonts()

    def _init_fonts(self):
        from ui.hollow_ui import HollowFonts
        self.font_title = HollowFonts.get(18, bold=True)
        self.font_item = HollowFonts.get(12, bold=True)
        self.font_name = HollowFonts.get(15, bold=True)
        self.font_sub = HollowFonts.get(10, bold=True)
        self.font_desc = HollowFonts.get(10)
        self.font_hint = HollowFonts.get(11, bold=True)
        self.font_roman = HollowFonts.get(11, bold=True)

    def handle_events(self, events: list[pygame.event.Event]):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._go_back()
                    return
                elif event.key in (pygame.K_UP, pygame.K_w):
                    self.selected_index = (self.selected_index - 1) % len(BOSS_ROSTER)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.selected_index = (self.selected_index + 1) % len(BOSS_ROSTER)
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self._start_boss_fight()
                    return
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                # Check item clicks
                item_y = 50
                for idx in range(len(BOSS_ROSTER)):
                    item_rect = pygame.Rect(20, item_y, 250, 52)
                    if item_rect.collidepoint(mx, my):
                        if self.selected_index == idx:
                            self._start_boss_fight()
                        else:
                            self.selected_index = idx
                        return
                    item_y += 62
                # Check launch button click
                launch_rect = pygame.Rect(290, 290, 325, 34)
                if launch_rect.collidepoint(mx, my):
                    self._start_boss_fight()
                    return
                # Check back button click
                back_rect = pygame.Rect(20, 324, 120, 26)
                if back_rect.collidepoint(mx, my):
                    self._go_back()
                    return

    def _go_back(self):
        if self.return_scene:
            self.scene_manager.change_scene(self.return_scene)
        else:
            from scenes.main_menu import MainMenuScene
            self.scene_manager.change_scene(MainMenuScene(self.scene_manager))

    def _start_boss_fight(self):
        chosen = BOSS_ROSTER[self.selected_index]
        from scenes.loading_scene import LoadingScene
        boss_scene = BossScene(self.scene_manager, boss_type=chosen["id"])
        loading = LoadingScene(
            self.scene_manager,
            boss_scene,
            title=f"CONFRONTO: {chosen['name'].upper()}",
            tip=f"Dica: {chosen['title']} possui ataques devastadores. Use sua esquiva e Ultimate com sabedoria!"
        )
        self.scene_manager.change_scene(loading)

    def update(self, dt: float):
        self.time_sec += dt
        self.fx.update(dt)

    def draw(self, surface: pygame.Surface):
        from ui.hollow_ui import HollowCrestRenderer, HollowColors
        
        # 1. Dark Ember Atmosphere (rising hot sparks and deep vignette)
        self.fx.draw_background(surface)

        # 2. Grand Header with Hollow Knight section divider
        t_surf = self.font_title.render("BATALHA DE CHEFE — PANTEÃO DOS CONFRONTOS", True, HollowColors.TEXT_TITLE)
        surface.blit(t_surf, t_surf.get_rect(center=(self.width // 2, 20)))
        HollowCrestRenderer.draw_section_divider(surface, self.width // 2, 38, width=580, alpha=200)

        # Roman numerals table
        roman_nums = ["I", "II", "III", "IV"]

        # 3. Boss List (Left Column)
        item_y = 50
        for idx, boss in enumerate(BOSS_ROSTER):
            is_selected = (idx == self.selected_index)
            item_rect = pygame.Rect(20, item_y, 250, 52)

            bg_col = (25, 30, 44, 240) if is_selected else (12, 14, 20, 220)
            border_col = HollowColors.GOLD_CREST if is_selected else (50, 58, 74)
            
            HollowCrestRenderer.draw_filigree_panel(surface, item_rect, bg_color=bg_col, border_color=border_col, corner_flourish=is_selected)

            # Boss emblem badge with Roman numeral
            badge_rect = pygame.Rect(item_rect.x + 8, item_rect.y + 10, 32, 32)
            pygame.draw.rect(surface, (10, 12, 18), badge_rect, border_radius=2)
            pygame.draw.rect(surface, boss["color"] if is_selected else (70, 78, 98), badge_rect, 1, border_radius=2)
            
            r_str = roman_nums[idx] if idx < len(roman_nums) else str(idx + 1)
            num_txt = self.font_roman.render(r_str, True, boss["color"] if is_selected else HollowColors.TEXT_NORMAL)
            surface.blit(num_txt, num_txt.get_rect(center=badge_rect.center))

            # Name and World
            name_txt = self.font_item.render(boss["name"], True, HollowColors.TEXT_TITLE if is_selected else HollowColors.TEXT_NORMAL)
            world_txt = self.font_desc.render(boss["world"], True, HollowColors.TEXT_MUTED)
            surface.blit(name_txt, (item_rect.x + 48, item_rect.y + 10))
            surface.blit(world_txt, (item_rect.x + 48, item_rect.y + 29))

            # Left selection fleuron
            if is_selected:
                HollowCrestRenderer.draw_selection_marker(surface, item_rect.left - 4, item_rect.centery, size=4.0)

            item_y += 62

        # 4. Boss Detail Card (Right Column)
        sel_boss = BOSS_ROSTER[self.selected_index]
        card_rect = pygame.Rect(290, 50, 325, 230)
        HollowCrestRenderer.draw_filigree_panel(surface, card_rect, bg_color=(10, 12, 18, 240), border_color=(75, 82, 100), corner_flourish=True)

        # Title & Name
        title_txt = self.font_sub.render(f"‹ {sel_boss['title']} ›", True, sel_boss["color"])
        surface.blit(title_txt, (card_rect.x + 16, card_rect.y + 14))
        name_txt = self.font_name.render(sel_boss["name"], True, HollowColors.TEXT_TITLE)
        surface.blit(name_txt, (card_rect.x + 16, card_rect.y + 30))

        # World & Difficulty
        diff_txt = self.font_desc.render(f"Dificuldade: {sel_boss['difficulty']}", True, HollowColors.GOLD_CREST)
        world_info = self.font_desc.render(f"Origem: {sel_boss['world']}", True, HollowColors.TEXT_NORMAL)
        surface.blit(diff_txt, (card_rect.x + 16, card_rect.y + 54))
        surface.blit(world_info, (card_rect.x + 16, card_rect.y + 70))

        # Filigree divider line inside card
        pygame.draw.line(surface, (45, 52, 68), (card_rect.x + 14, card_rect.y + 88), (card_rect.right - 14, card_rect.y + 88), 1)

        # Description text (wrapped)
        words = sel_boss["desc"].split(" ")
        lines = []
        cur_line = []
        max_w = card_rect.width - 32
        for w in words:
            test = " ".join(cur_line + [w])
            if self.font_desc.size(test)[0] > max_w:
                lines.append(" ".join(cur_line))
                cur_line = [w]
            else:
                cur_line.append(w)
        if cur_line:
            lines.append(" ".join(cur_line))

        dy = card_rect.y + 98
        for line in lines[:8]:
            l_surf = self.font_desc.render(line, True, HollowColors.TEXT_NORMAL)
            surface.blit(l_surf, (card_rect.x + 16, dy))
            dy += 14

        # 5. Launch Button
        btn_rect = pygame.Rect(290, 290, 325, 34)
        btn_hover = btn_rect.collidepoint(pygame.mouse.get_pos())
        HollowCrestRenderer.draw_hollow_button(
            surface,
            btn_rect,
            "INICIAR CONFRONTO [ESPAÇO]",
            self.font_hint,
            is_hovered=btn_hover,
            text_color=HollowColors.GOLD_CREST if btn_hover else HollowColors.TEXT_TITLE
        )

        # 6. Back Button & Hints
        back_rect = pygame.Rect(20, 324, 120, 26)
        back_hover = back_rect.collidepoint(pygame.mouse.get_pos())
        HollowCrestRenderer.draw_hollow_button(surface, back_rect, "VOLTAR [ESC]", self.font_desc, is_hovered=back_hover)

        hint_txt = self.font_desc.render("[W/S] Escolher Chefe   [ENTER] Desafiar", True, HollowColors.TEXT_MUTED)
        surface.blit(hint_txt, (155, 330))
