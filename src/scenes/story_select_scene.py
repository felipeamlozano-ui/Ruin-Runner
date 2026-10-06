"""
Ruin Engine — Story Mode World Selection Scene.
Seletor de Mundos com planetas 3D pixel-art animados (Deep-Fold),
cenários astrais e integração direta com o StageManager.
Otimizado para resolução nativa 640x360 (16:9).
"""

import math
import random
import pygame
from typing import List, Dict, Any
from engine.scene_manager import Scene
from engine.save_manager import SAVE
from engine.stage_manager import STAGE_MGR
from engine.v3.planets.planet_renderer import PixelPlanetRenderer

WORLDS_INFO = [
    {
        "id": "terrae",
        "name": "TERRAE: O BERÇO DOS HOMENS",
        "first_stage": "terrae_1",
        "stages_count": 3,
        "hazard_name": "Nível I (Normal)",
        "hazard_level": 1,
        "hazard_col": (120, 255, 120),
        "desc": "Florestas ancestrais e pontes fortificadas tomadas por bandos de esqueletos saqueadores.",
        "boss": "O Titã Demoníaco",
        "bg_stars": 60
    },
    {
        "id": "sanguis",
        "name": "SANGUIS: A LUA DE SANGUE",
        "first_stage": "sanguis_1",
        "stages_count": 3,
        "hazard_name": "Nível II (Difícil)",
        "hazard_level": 2,
        "hazard_col": (255, 180, 80),
        "desc": "Um reino de pedras vulcânicas e torres góticas onde os Senhores Vampiros ceifam almas.",
        "boss": "O Empalador Abissal",
        "bg_stars": 45
    },
    {
        "id": "glacies",
        "name": "GLACIES: O DOMÍNIO CONGELADO",
        "first_stage": "glacies_1",
        "stages_count": 3,
        "hazard_name": "Nível III (Pesadelo)",
        "hazard_level": 3,
        "hazard_col": (120, 200, 255),
        "desc": "Montanhas cortantes de gelo eterno e criptas seladas sob o permafrost sombrio.",
        "boss": "O Monstro Quimérico Ancestral",
        "bg_stars": 50
    },
    {
        "id": "aetheria",
        "name": "AETHERIA: O ALTAR CELESTIAL",
        "first_stage": "aetheria_1",
        "stages_count": 3,
        "hazard_name": "Nível IV (Apocalíptico)",
        "hazard_level": 4,
        "hazard_col": (255, 90, 90),
        "desc": "Cidadelas flutuantes entre tempestades de plasma onde reside o núcleo das Ruínas.",
        "boss": "Lorde Samurai Amaldiçoado",
        "bg_stars": 70
    }
]

class StorySelectScene(Scene):
    """World selection carousel with rotating 3D pixel planets and Hollow Knight aesthetic."""
    
    internal_size = (640, 360)
    
    def __init__(self, scene_manager):
        self.scene_manager = scene_manager
        self.width = 640
        self.height = 360
        
        self.world_index = 0
        self.renderers = {
            w["id"]: PixelPlanetRenderer(w["id"], radius=28, target_size=106)
            for w in WORLDS_INFO
        }
        
        from ui.hollow_ui import AtmosphereFX, HollowFonts, HollowCrestRenderer, HollowColors
        self.fx = AtmosphereFX(width=640, height=360, theme="void", particle_count=35)
        self._init_fonts()
        self._init_starfield()

    def _init_fonts(self):
        from ui.hollow_ui import HollowFonts
        self.font_title = HollowFonts.get(18, bold=True)
        self.font_name = HollowFonts.get(14, bold=True)
        self.font_desc = HollowFonts.get(10)
        self.font_hud = HollowFonts.get(11, bold=True)

    def _init_starfield(self):
        self.stars = []
        for _ in range(65):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            size = random.choice([1, 1, 2])
            alpha = random.randint(90, 200)
            self.stars.append((x, y, size, alpha))

    def handle_events(self, events: list[pygame.event.Event]):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    from scenes.main_menu import MainMenuScene
                    self.scene_manager.change_scene(MainMenuScene(self.scene_manager))
                    return
                elif event.key in (pygame.K_a, pygame.K_LEFT):
                    self.world_index = (self.world_index - 1) % len(WORLDS_INFO)
                elif event.key in (pygame.K_d, pygame.K_RIGHT):
                    self.world_index = (self.world_index + 1) % len(WORLDS_INFO)
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self._launch_world()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                btn_box = pygame.Rect(self.width // 2 - 120, 282, 240, 28)
                if btn_box.collidepoint(mx, my):
                    self._launch_world()
                    return
                back_box = pygame.Rect(35, 325, 120, 25)
                if back_box.collidepoint(mx, my):
                    from scenes.main_menu import MainMenuScene
                    self.scene_manager.change_scene(MainMenuScene(self.scene_manager))
                    return

    def _launch_world(self):
        world = WORLDS_INFO[self.world_index]
        stage_cfg = STAGE_MGR.load_stage(world["first_stage"])
        from scenes.level_scene import LevelScene
        if stage_cfg:
            self.scene_manager.change_scene(LevelScene(self.scene_manager, stage=stage_cfg))
        else:
            self.scene_manager.change_scene(LevelScene(self.scene_manager, stage=1))

    def update(self, dt: float):
        self.fx.update(dt)
        for r in self.renderers.values():
            r.update(dt)

    def draw(self, surface: pygame.Surface):
        from ui.hollow_ui import HollowCrestRenderer, HollowColors
        
        # 1. Cosmic Void & Ambient Mist
        self.fx.draw_background(surface)
        
        # Subtle stars in void
        for x, y, size, alpha in self.stars:
            c = (alpha, alpha, alpha)
            if size == 1:
                surface.set_at((x, y), c)
            else:
                pygame.draw.rect(surface, c, (x, y, size, size))

        # 2. Scene Title Header & Section Divider
        title_surf = self.font_title.render("MODO HISTÓRIA — REINOS ANCESTRAIS", True, HollowColors.TEXT_TITLE)
        surface.blit(title_surf, title_surf.get_rect(center=(self.width // 2, 18)))
        HollowCrestRenderer.draw_section_divider(surface, self.width // 2, 36, width=540, alpha=190)
        
        # 3. Planet Centerpiece
        world = WORLDS_INFO[self.world_index]
        cx, cy = self.width // 2, 94
        
        # Atmospheric Orbit Ring with subtle jewel marks
        pygame.draw.ellipse(surface, (45, 55, 78), (cx - 88, cy - 26, 176, 52), width=1)
        pygame.draw.circle(surface, HollowColors.SILVER_CREST, (cx - 88, cy), 2)
        pygame.draw.circle(surface, HollowColors.SILVER_CREST, (cx + 88, cy), 2)
        
        # Render 3D Pixel Planet
        planet_rnd = self.renderers[world["id"]]
        planet_rnd.draw(surface, center=(cx, cy))
        
        # Carousel Chevrons
        arrow_l = self.font_name.render("‹", True, HollowColors.GOLD_CREST)
        arrow_r = self.font_name.render("›", True, HollowColors.GOLD_CREST)
        surface.blit(arrow_l, (cx - 106, cy - 10))
        surface.blit(arrow_r, (cx + 96, cy - 10))

        # 4. World Info Card (Hollow Filigree Frame)
        card_rect = pygame.Rect(35, 160, self.width - 70, 158)
        HollowCrestRenderer.draw_filigree_panel(surface, card_rect, bg_color=(10, 12, 18, 235), border_color=(75, 82, 100), corner_flourish=True)
        
        # World Title in Gold
        w_title = self.font_name.render(f"‹  {world['name']}  ›", True, HollowColors.GOLD_CREST)
        surface.blit(w_title, w_title.get_rect(center=(self.width // 2, 178)))
        
        # Delicate separator inside card
        pygame.draw.line(surface, (45, 52, 68), (55, 194), (self.width - 55, 194), 1)
        
        # Hazard Level & Pips
        hz_text = f"Perigo: {world['hazard_name']} "
        hz_surf = self.font_hud.render(hz_text, True, world["hazard_col"])
        surface.blit(hz_surf, (55, 202))
        
        # Danger diamond pips
        pip_x = 55 + hz_surf.get_width() + 6
        pip_y = 203
        for p in range(4):
            filled = p < world["hazard_level"]
            box_col = world["hazard_col"] if filled else (25, 30, 42)
            pygame.draw.rect(surface, box_col, (pip_x + p * 14, pip_y, 9, 9), border_radius=1)
            pygame.draw.rect(surface, (75, 85, 110), (pip_x + p * 14, pip_y, 9, 9), width=1, border_radius=1)
        
        # Final Boss
        boss_surf = self.font_hud.render(f"Guardião Final: {world['boss']}", True, (245, 150, 150))
        surface.blit(boss_surf, (55, 222))
        
        # Description
        words = world["desc"].split()
        line = ""
        dy = 242
        for w in words:
            test = line + " " + w if line else w
            if self.font_desc.size(test)[0] > (self.width - 120):
                surface.blit(self.font_desc.render(line, True, HollowColors.TEXT_NORMAL), (55, dy))
                dy += 13
                line = w
            else:
                line = test
        if line:
            surface.blit(self.font_desc.render(line, True, HollowColors.TEXT_NORMAL), (55, dy))
            
        # 5. Launch Button inside card
        btn_box = pygame.Rect(self.width // 2 - 120, 282, 240, 26)
        btn_hover = btn_box.collidepoint(pygame.mouse.get_pos())
        HollowCrestRenderer.draw_hollow_button(
            surface,
            btn_box,
            "POUSAR NO MUNDO [ESPAÇO]",
            self.font_hud,
            is_hovered=btn_hover,
            text_color=HollowColors.GOLD_CREST if btn_hover else HollowColors.TEXT_TITLE
        )
        
        # 6. Bottom footer & back button
        back_box = pygame.Rect(35, 325, 120, 25)
        back_hover = back_box.collidepoint(pygame.mouse.get_pos())
        HollowCrestRenderer.draw_hollow_button(surface, back_box, "VOLTAR [ESC]", self.font_desc, is_hovered=back_hover)
        
        esc_txt = self.font_desc.render("[A/D] Selecionar Reino   |   [ENTER] Confirmar", True, HollowColors.TEXT_MUTED)
        surface.blit(esc_txt, (self.width // 2 - esc_txt.get_width() // 2 + 50, 330))
