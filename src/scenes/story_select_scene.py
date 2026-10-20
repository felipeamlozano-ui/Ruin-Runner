"""
Ruin Engine — Story Mode World Selection Scene (Deep Refactor).
Features 3D rotating Deep-Fold pixel planets, smooth carousel transitions,
depth-sorted celestial orbits, balanced two-column card layout, and rich animations.
Optimized for native 640x360 (16:9).
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
        "hazard_col": (115, 235, 140),
        "desc": "Florestas ancestrais e pontes fortificadas tomadas por bandos de esqueletos saqueadores.",
        "boss": "O Titã Demoníaco",
        "sat_name": "Luna Antiga",
        "sat_color": (215, 230, 250),
        "theme_accent": (110, 225, 150),
        "theme_glow": (60, 150, 255)
    },
    {
        "id": "sanguis",
        "name": "SANGUIS: A LUA DE SANGUE",
        "first_stage": "sanguis_1",
        "stages_count": 3,
        "hazard_name": "Nível II (Difícil)",
        "hazard_level": 2,
        "hazard_col": (255, 175, 75),
        "desc": "Um reino de pedras vulcânicas e torres góticas onde os Senhores Vampiros ceifam almas.",
        "boss": "O Rei Esqueleto",
        "sat_name": "Fragmento de Lava",
        "sat_color": (255, 160, 60),
        "theme_accent": (255, 120, 85),
        "theme_glow": (255, 50, 40)
    },
    {
        "id": "glacies",
        "name": "GLACIES: O DOMÍNIO CONGELADO",
        "first_stage": "glacies_1",
        "stages_count": 3,
        "hazard_name": "Nível III (Pesadelo)",
        "hazard_level": 3,
        "hazard_col": (120, 220, 255),
        "desc": "Montanhas cortantes de gelo eterno e criptas seladas sob o permafrost sombrio.",
        "boss": "O Monstro Quimérico Ancestral",
        "sat_name": "Cometa Cristalino",
        "sat_color": (160, 245, 255),
        "theme_accent": (110, 225, 255),
        "theme_glow": (80, 210, 255)
    },
    {
        "id": "aetheria",
        "name": "AETHERIA: O ALTAR CELESTIAL",
        "first_stage": "aetheria_1",
        "stages_count": 3,
        "hazard_name": "Nível IV (Apocalíptico)",
        "hazard_level": 4,
        "hazard_col": (255, 95, 95),
        "desc": "Cidadelas flutuantes entre tempestades de plasma onde reside o núcleo das Ruínas.",
        "boss": "Lorde Samurai Amaldiçoado",
        "sat_name": "Prisma Solar",
        "sat_color": (255, 240, 160),
        "theme_accent": (255, 210, 85),
        "theme_glow": (255, 185, 50)
    }
]


class StorySelectScene(Scene):
    """World selection carousel with rotating 3D pixel planets, save slots, and campaign progression."""
    
    internal_size = (640, 360)
    
    def __init__(self, scene_manager):
        self.scene_manager = scene_manager
        self.width = 640
        self.height = 360
        
        self.world_index = 0
        self.carousel_scroll = 0.0
        self.card_fade_alpha = 255.0
        self.card_slide_offset = 0.0
        self.time_sec = 0.0
        
        self.active_slot = SAVE.active_slot
        self.confirming_new_game = False
        self.status_message = ""
        self.status_timer = 0.0
        
        # 3D Pixel Planet Renderers (48 smooth frames, crisp integer 2x: radius 24 -> 96px diameter)
        self.renderers = {
            w["id"]: PixelPlanetRenderer(w["id"], radius=24, target_size=96)
            for w in WORLDS_INFO
        }
        
        from ui.hollow_ui import AtmosphereFX, HollowFonts, HollowCrestRenderer, HollowColors
        self.fx = AtmosphereFX(width=640, height=360, theme="void", particle_count=35)
        self._init_fonts()
        self._init_starfield()

    def _init_fonts(self):
        from ui.hollow_ui import HollowFonts
        self.font_title = HollowFonts.get(15, bold=True)
        self.font_name = HollowFonts.get(13, bold=True)
        self.font_card_title = HollowFonts.get(12, bold=True)
        self.font_sub = HollowFonts.get(10, bold=True)
        self.font_desc = HollowFonts.get(10)
        self.font_hud = HollowFonts.get(11, bold=True)
        self.font_small = HollowFonts.get(9)
        self.font_micro = HollowFonts.get(8, bold=True)

    def _init_starfield(self):
        self.stars = []
        for _ in range(75):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            size = random.choice([1, 1, 1, 2])
            alpha = random.randint(80, 220)
            twinkle_freq = random.uniform(1.5, 4.0)
            twinkle_phase = random.uniform(0.0, 6.28)
            self.stars.append((x, y, size, alpha, twinkle_freq, twinkle_phase))

    def _change_world(self, delta: int):
        new_idx = (self.world_index + delta) % len(WORLDS_INFO)
        if new_idx != self.world_index:
            self.world_index = new_idx
            self.card_fade_alpha = 90.0
            self.card_slide_offset = 5.0

    def _select_slot(self, slot_num: int):
        if slot_num != self.active_slot:
            SAVE.load_slot(slot_num)
            self.active_slot = slot_num
            self.confirming_new_game = False
            self.status_message = f"Slot {slot_num} carregado com sucesso."
            self.status_timer = 2.0

    def _get_resume_stage(self, world_id: str) -> str:
        """Determines the appropriate uncompleted or current checkpoint stage for a world."""
        stages_by_world = {
            "terrae": ["terrae_1", "terrae_2", "terrae_3"],
            "sanguis": ["sanguis_1", "sanguis_2", "sanguis_3"],
            "glacies": ["glacies_1", "glacies_2", "glacies_3"],
            "aetheria": ["aetheria_1", "aetheria_2", "aetheria_3"]
        }
        stages = stages_by_world.get(world_id, [f"{world_id}_1"])
        for stg in stages:
            if not SAVE.is_stage_completed(stg):
                return stg
        return stages[-1]

    def _launch_world(self):
        world = WORLDS_INFO[self.world_index]
        world_id = world["id"]
        
        if not SAVE.is_world_unlocked(world_id):
            self.status_message = "REINO BLOQUEADO! Derrote o guardiao anterior para avancar."
            self.status_timer = 2.5
            return

        target_stage_id = self._get_resume_stage(world_id)
        stage_cfg = STAGE_MGR.load_stage(target_stage_id)
        
        from scenes.level_scene import LevelScene
        from scenes.loading_scene import LoadingScene
        if stage_cfg:
            next_scene = LevelScene(self.scene_manager, stage=stage_cfg)
        else:
            next_scene = LevelScene(self.scene_manager, stage=1)
            
        loading = LoadingScene(
            self.scene_manager,
            next_scene,
            title=f"ENTRANDO EM {world['name']}",
            tip="Preservando seu progresso e decisoes narrativas no save ativo."
        )
        self.scene_manager.change_scene(loading)

    def handle_events(self, events: list[pygame.event.Event]):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.confirming_new_game:
                        self.confirming_new_game = False
                        return
                    from scenes.main_menu import MainMenuScene
                    self.scene_manager.change_scene(MainMenuScene(self.scene_manager))
                    return
                elif event.key in (pygame.K_a, pygame.K_LEFT):
                    self._change_world(-1)
                elif event.key in (pygame.K_d, pygame.K_RIGHT):
                    self._change_world(1)
                elif event.key in (pygame.K_1, pygame.K_KP1):
                    self._select_slot(1)
                elif event.key in (pygame.K_2, pygame.K_KP2):
                    self._select_slot(2)
                elif event.key in (pygame.K_3, pygame.K_KP3):
                    self._select_slot(3)
                elif event.key == pygame.K_TAB:
                    next_s = (self.active_slot % 3) + 1
                    self._select_slot(next_s)
                elif event.key == pygame.K_n:
                    self.confirming_new_game = not self.confirming_new_game
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    if self.confirming_new_game:
                        SAVE.new_game(self.active_slot)
                        self.confirming_new_game = False
                        self.status_message = f"Nova Campanha iniciada no Slot {self.active_slot}!"
                        self.status_timer = 2.5
                    else:
                        self._launch_world()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                
                # Check slot buttons
                slot_w = 70
                start_sx = self.width // 2 - (slot_w * 3 + 16) // 2
                for s_idx in range(1, 4):
                    s_rect = pygame.Rect(start_sx + (s_idx - 1) * (slot_w + 8), 26, slot_w, 17)
                    if s_rect.collidepoint(mx, my):
                        self._select_slot(s_idx)
                        return
                
                # Check New Game button
                ng_box = pygame.Rect(self.width - 150, 26, 115, 17)
                if ng_box.collidepoint(mx, my):
                    self.confirming_new_game = not self.confirming_new_game
                    return

                # Check Chevron arrows
                cx = self.width // 2
                cy = 98
                chevron_l = pygame.Rect(cx - 105, cy - 25, 36, 50)
                chevron_r = pygame.Rect(cx + 69, cy - 25, 36, 50)
                if chevron_l.collidepoint(mx, my):
                    self._change_world(-1)
                    return
                elif chevron_r.collidepoint(mx, my):
                    self._change_world(1)
                    return

                # Check neighboring planet clicks
                if pygame.Rect(cx - 180, cy - 30, 60, 60).collidepoint(mx, my):
                    self._change_world(-1)
                    return
                elif pygame.Rect(cx + 120, cy - 30, 60, 60).collidepoint(mx, my):
                    self._change_world(1)
                    return

                # Check Launch Button
                btn_box = pygame.Rect(self.width // 2 - 130, 286, 260, 26)
                if btn_box.collidepoint(mx, my):
                    if self.confirming_new_game:
                        SAVE.new_game(self.active_slot)
                        self.confirming_new_game = False
                        self.status_message = f"Nova Campanha iniciada no Slot {self.active_slot}!"
                        self.status_timer = 2.5
                    else:
                        self._launch_world()
                    return

                # Back Button
                back_box = pygame.Rect(32, 328, 110, 22)
                if back_box.collidepoint(mx, my):
                    from scenes.main_menu import MainMenuScene
                    self.scene_manager.change_scene(MainMenuScene(self.scene_manager))
                    return

    def update(self, dt: float):
        self.time_sec += dt
        self.fx.update(dt)
        
        # Smooth exponential easing for 3D planetary carousel
        target_scroll = float(self.world_index)
        diff = target_scroll - self.carousel_scroll
        if diff > 2.0:
            self.carousel_scroll += 4.0
        elif diff < -2.0:
            self.carousel_scroll -= 4.0
        self.carousel_scroll += (target_scroll - self.carousel_scroll) * min(1.0, dt * 10.0)
        
        # Smooth card text fade-in and slide recovery
        if self.card_fade_alpha < 255.0:
            self.card_fade_alpha = min(255.0, self.card_fade_alpha + dt * 650.0)
        if self.card_slide_offset > 0.0:
            self.card_slide_offset = max(0.0, self.card_slide_offset - dt * 25.0)

        # Update all 3D planet animators
        for r in self.renderers.values():
            r.update(dt)
            
        if self.status_timer > 0:
            self.status_timer -= dt
            if self.status_timer <= 0:
                self.status_message = ""

    def draw(self, surface: pygame.Surface):
        from ui.hollow_ui import HollowCrestRenderer, HollowColors
        
        # 1. Cosmic Void & Ambient Mist
        self.fx.draw_background(surface)
        
        # Dynamic twinkling stars
        for x, y, size, base_alpha, freq, phase in self.stars:
            twinkle = 0.65 + 0.35 * math.sin(self.time_sec * freq + phase)
            alpha = int(base_alpha * twinkle)
            c = (alpha, alpha, alpha)
            if size == 1:
                surface.set_at((x, y), c)
            else:
                pygame.draw.rect(surface, c, (x, y, size, size))

        # 2. Scene Title Header & Section Divider
        title_surf = self.font_title.render("CAMPANHA NARRATIVA PERSISTENTE", True, HollowColors.TEXT_TITLE)
        surface.blit(title_surf, title_surf.get_rect(center=(self.width // 2, 13)))
        
        # 2.1 Save Slots Bar at Top
        slot_w = 70
        start_sx = self.width // 2 - (slot_w * 3 + 16) // 2
        for s_idx in range(1, 4):
            s_rect = pygame.Rect(start_sx + (s_idx - 1) * (slot_w + 8), 25, slot_w, 17)
            is_active = (s_idx == self.active_slot)
            col_bg = (35, 45, 65, 230) if is_active else (15, 20, 28, 180)
            col_border = HollowColors.GOLD_CREST if is_active else (55, 65, 85)
            pygame.draw.rect(surface, col_bg[:3], s_rect, border_radius=2)
            pygame.draw.rect(surface, col_border, s_rect, width=1, border_radius=2)
            s_text = f"SLOT {s_idx}" + (" *" if is_active else "")
            txt_s = self.font_small.render(s_text, True, HollowColors.GOLD_CREST if is_active else HollowColors.TEXT_MUTED)
            surface.blit(txt_s, txt_s.get_rect(center=s_rect.center))
            
        # New game button at top right
        ng_box = pygame.Rect(self.width - 150, 25, 115, 17)
        col_ng = (180, 50, 50) if self.confirming_new_game else (38, 42, 56)
        pygame.draw.rect(surface, col_ng, ng_box, border_radius=2)
        pygame.draw.rect(surface, HollowColors.SILVER_CREST if not self.confirming_new_game else (255, 120, 120), ng_box, width=1, border_radius=2)
        ng_lbl = "CONFIRMAR? [N]" if self.confirming_new_game else "NOVO JOGO [N]"
        ng_s = self.font_small.render(ng_lbl, True, (255, 220, 220) if self.confirming_new_game else HollowColors.TEXT_NORMAL)
        surface.blit(ng_s, ng_s.get_rect(center=ng_box.center))

        # 3. 3D Planet Centerpiece & Carousel
        world = WORLDS_INFO[self.world_index]
        is_unlocked = SAVE.is_world_unlocked(world["id"])
        theme_glow = world["theme_glow"]
        theme_accent = world["theme_accent"]
        
        # Gentle planetary floating bob
        float_y = math.sin(self.time_sec * 2.2) * 2.8
        cx = self.width // 2
        cy = int(98 + float_y)
        
        # Soft cosmic atmospheric glow behind center planet
        from engine.lighting import LightingEngine
        glow_surf = LightingEngine.get_radial_light_surface(radius=48, color=theme_glow, intensity=0.32)
        surface.blit(glow_surf, (cx - 48, cy - 48), special_flags=pygame.BLEND_RGBA_ADD)

        # Depth-Sorted 3D Orbit Geometry
        rx = 78.0
        ry = 20.0
        sat_angle = (self.time_sec * 1.5) % (2.0 * math.pi)
        sat_x = int(cx + math.cos(sat_angle) * rx)
        sat_y = int(cy + math.sin(sat_angle) * ry)
        sat_behind = math.sin(sat_angle) < 0.0

        # Calculate discrete points along the orbit ellipse
        back_pts = []
        front_pts = []
        steps = 40
        for st in range(steps + 1):
            ang = (st / steps) * 2.0 * math.pi
            pt = (int(cx + math.cos(ang) * rx), int(cy + math.sin(ang) * ry))
            if math.sin(ang) < 0.0:
                back_pts.append(pt)
            else:
                front_pts.append(pt)

        # Draw Back Arc of Orbit Ring (behind planet)
        if len(back_pts) >= 2:
            pygame.draw.lines(surface, (70, 85, 115), False, back_pts, 1)

        # Satellite when behind planet
        if sat_behind:
            pygame.draw.circle(surface, world["sat_color"], (sat_x, sat_y), 3)
            pygame.draw.circle(surface, (255, 255, 255), (sat_x, sat_y), 1)

        # Draw Planets in 3D Carousel (Distant neighbors first, active planet last)
        for i, w_info in enumerate(WORLDS_INFO):
            diff = (i - self.carousel_scroll + 2.0) % 4.0 - 2.0
            if abs(diff) > 1.65:
                continue
            
            px = int(cx + diff * 150.0)
            py = int(cy + abs(diff) * 8.0)
            p_scale = max(0.48, 1.0 - abs(diff) * 0.48)
            p_alpha = int(max(40, 255 * (1.0 - abs(diff) * 0.65)))
            
            p_rnd = self.renderers[w_info["id"]]
            p_rnd.draw(surface, center=(px, py), scale=p_scale, alpha=p_alpha)

        # Draw Front Arc of Orbit Ring (in front of planet)
        if len(front_pts) >= 2:
            pygame.draw.lines(surface, theme_accent, False, front_pts, 1)

        # Orbiting cosmic stardust particles along the ring
        for sp_idx in range(4):
            sp_ang = (self.time_sec * 0.8 + sp_idx * (math.pi / 2.0)) % (2.0 * math.pi)
            sx = int(cx + math.cos(sp_ang) * rx)
            sy = int(cy + math.sin(sp_ang) * ry)
            sp_alpha = int(120 + 75 * math.sin(self.time_sec * 3.0 + sp_idx))
            pygame.draw.circle(surface, (*theme_accent, sp_alpha), (sx, sy), 1)

        # Satellite when in front of planet
        if not sat_behind:
            # Soft drop shadow
            shadow_surf = pygame.Surface((10, 10), pygame.SRCALPHA)
            pygame.draw.circle(shadow_surf, (0, 0, 0, 85), (5, 5), 3)
            surface.blit(shadow_surf, (sat_x - 3, sat_y - 1))
            # Glowing satellite
            pygame.draw.circle(surface, world["sat_color"], (sat_x, sat_y), 3)
            pygame.draw.circle(surface, (255, 255, 255), (sat_x, sat_y), 1)

        # Carousel Chevrons with subtle hover nudge
        mx, my = pygame.mouse.get_pos()
        hover_l = pygame.Rect(cx - 105, cy - 25, 36, 50).collidepoint(mx, my)
        hover_r = pygame.Rect(cx + 69, cy - 25, 36, 50).collidepoint(mx, my)
        
        col_arr_l = HollowColors.GOLD_CREST if hover_l else (165, 175, 195)
        col_arr_r = HollowColors.GOLD_CREST if hover_r else (165, 175, 195)
        
        arrow_l = self.font_name.render("‹", True, col_arr_l)
        arrow_r = self.font_name.render("›", True, col_arr_r)
        surface.blit(arrow_l, (int(cx - 90 - (2 if hover_l else 0)), cy - 10))
        surface.blit(arrow_r, (int(cx + 80 + (2 if hover_r else 0)), cy - 10))

        # 4. Redesigned Balanced World Info Card (Two Columns + Filigree Crest)
        card_rect = pygame.Rect(32, 160, self.width - 64, 162)
        HollowCrestRenderer.draw_filigree_panel(
            surface,
            card_rect,
            bg_color=(10, 13, 20, 240),
            border_color=(65, 72, 90),
            corner_flourish=True
        )
        
        # Smooth alpha card surface for silky cross-fade transitions
        card_surf = pygame.Surface((card_rect.width, card_rect.height), pygame.SRCALPHA)
        c_alpha = int(self.card_fade_alpha)
        dy_slide = int(self.card_slide_offset)
        
        # 4.1 Card Header: Title on Left, Status Badge on Right
        w_title = self.font_name.render(f"‹  {world['name']}  ›", True, theme_accent if is_unlocked else (180, 80, 80))
        card_surf.blit(w_title, (18, 11 + dy_slide))
        
        # Status Pill Badge (Top-Right of card)
        if is_unlocked:
            badge_txt = "DESBLOQUEADO"
            badge_col = (75, 195, 120)
            badge_bg = (18, 42, 28, 200)
        else:
            badge_txt = "BLOQUEADO"
            badge_col = (235, 90, 90)
            badge_bg = (52, 18, 22, 200)
            
        b_surf = self.font_micro.render(badge_txt, True, badge_col)
        b_w, b_h = b_surf.get_width() + 16, 16
        b_rect = pygame.Rect(card_rect.width - b_w - 18, 11 + dy_slide, b_w, b_h)
        pygame.draw.rect(card_surf, badge_bg, b_rect, border_radius=2)
        pygame.draw.rect(card_surf, badge_col, b_rect, width=1, border_radius=2)
        # Small jewel dot in badge
        pygame.draw.circle(card_surf, badge_col, (b_rect.x + 6, b_rect.centery), 2)
        card_surf.blit(b_surf, (b_rect.x + 12, b_rect.y + 2))

        # Filigree Horizontal Separator
        pygame.draw.line(card_surf, (45, 52, 68), (16, 32 + dy_slide), (card_rect.width - 16, 32 + dy_slide), 1)
        pygame.draw.circle(card_surf, HollowColors.GOLD_CREST, (card_rect.width // 2, 32 + dy_slide), 2)

        # 4.2 LEFT COLUMN: Lore & Boss Encounter
        col_l_x = 18
        
        # Lore Header & Text
        lbl_lore = self.font_micro.render("CRÔNICA DO REINO", True, HollowColors.TEXT_MUTED)
        card_surf.blit(lbl_lore, (col_l_x, 39 + dy_slide))
        
        # Wrap Lore description neatly
        desc_words = world["desc"].split()
        desc_line = ""
        desc_y = 51 + dy_slide
        for w in desc_words:
            test = desc_line + " " + w if desc_line else w
            if self.font_desc.size(test)[0] > 310:
                card_surf.blit(self.font_desc.render(desc_line, True, HollowColors.TEXT_NORMAL), (col_l_x, desc_y))
                desc_y += 13
                desc_line = w
            else:
                desc_line = test
        if desc_line:
            card_surf.blit(self.font_desc.render(desc_line, True, HollowColors.TEXT_NORMAL), (col_l_x, desc_y))

        # Boss Pill Cardlet
        boss_box_y = max(desc_y + 14, 82 + dy_slide)
        boss_box = pygame.Rect(col_l_x, boss_box_y, 315, 27)
        pygame.draw.rect(card_surf, (16, 20, 30, 220), boss_box, border_radius=2)
        pygame.draw.rect(card_surf, (55, 65, 85), boss_box, width=1, border_radius=2)
        
        lbl_guard = self.font_micro.render("GUARDIÃO DO REINO", True, HollowColors.TEXT_MUTED)
        card_surf.blit(lbl_guard, (col_l_x + 8, boss_box_y + 3))
        
        boss_title = self.font_sub.render(f"[CHEFE]  {world['boss']}", True, (255, 145, 145))
        card_surf.blit(boss_title, (col_l_x + 8, boss_box_y + 13))

        # Vertical Column Divider
        col_div_x = 348
        pygame.draw.line(card_surf, (40, 46, 60), (col_div_x, 38 + dy_slide), (col_div_x, 115 + dy_slide), 1)

        # 4.3 RIGHT COLUMN: Danger Level, Stage Progress & Orbs
        col_r_x = 362
        
        # Danger Rating & Diamond Pips
        lbl_danger = self.font_micro.render("AMEAÇA & PERIGO", True, HollowColors.TEXT_MUTED)
        card_surf.blit(lbl_danger, (col_r_x, 39 + dy_slide))
        
        hz_name_surf = self.font_sub.render(world["hazard_name"], True, world["hazard_col"])
        card_surf.blit(hz_name_surf, (col_r_x, 50 + dy_slide))
        
        # 4 Glowing Diamond Pips
        pip_start_x = col_r_x + hz_name_surf.get_width() + 10
        pip_y = 52 + dy_slide
        for p in range(4):
            filled = (p < world["hazard_level"])
            px = pip_start_x + p * 13
            d_pts = [(px + 4, pip_y), (px + 8, pip_y + 4), (px + 4, pip_y + 8), (px, pip_y + 4)]
            if filled:
                pygame.draw.polygon(card_surf, world["hazard_col"], d_pts)
            else:
                pygame.draw.polygon(card_surf, (22, 28, 40), d_pts)
            pygame.draw.polygon(card_surf, (80, 92, 115), d_pts, 1)

        # Stage Progress Segmented Bar
        lbl_prog = self.font_micro.render("PROGRESSO DAS FASES", True, HollowColors.TEXT_MUTED)
        card_surf.blit(lbl_prog, (col_r_x, 68 + dy_slide))
        
        completed_in_world = sum(1 for i in range(1, 4) if SAVE.is_stage_completed(f"{world['id']}_{i}"))
        bar_y = 79 + dy_slide
        seg_w = 58
        for stg_i in range(1, 4):
            is_stg_done = SAVE.is_stage_completed(f"{world['id']}_{stg_i}")
            seg_rect = pygame.Rect(col_r_x + (stg_i - 1) * (seg_w + 5), bar_y, seg_w, 7)
            col_seg = (65, 195, 120) if is_stg_done else (24, 30, 42)
            pygame.draw.rect(card_surf, col_seg, seg_rect, border_radius=1)
            pygame.draw.rect(card_surf, (70, 82, 105), seg_rect, width=1, border_radius=1)
            
        txt_stg_count = self.font_micro.render(f"{completed_in_world}/3 Concluídas", True, (170, 215, 255))
        card_surf.blit(txt_stg_count, (col_r_x + 130, 68 + dy_slide))

        # Total Orbs Counter
        lbl_orbs = self.font_micro.render("ORBES ANCESTRAIS:", True, HollowColors.TEXT_MUTED)
        card_surf.blit(lbl_orbs, (col_r_x, 95 + dy_slide))
        
        # Orb icon dot
        pygame.draw.circle(card_surf, (255, 210, 80), (col_r_x + 104, 101 + dy_slide), 3)
        txt_orbs = self.font_sub.render(f"{SAVE.get_orbs()} Coletados", True, (255, 220, 130))
        card_surf.blit(txt_orbs, (col_r_x + 112, 94 + dy_slide))

        # Blit the card surface onto the main buffer with fade alpha
        if c_alpha < 255:
            card_surf.set_alpha(c_alpha)
        surface.blit(card_surf, (card_rect.x, card_rect.y))

        # 5. Launch Button with Ambient Gold Pulse
        btn_box = pygame.Rect(self.width // 2 - 130, 286, 260, 26)
        btn_hover = btn_box.collidepoint(pygame.mouse.get_pos())
        
        if self.confirming_new_game:
            btn_label = f"CONFIRMAR REINÍCIO (SLOT {self.active_slot})"
            btn_col = (255, 110, 110)
        elif is_unlocked:
            btn_label = "CONTINUAR CAMPANHA [ESPAÇO]"
            btn_col = HollowColors.GOLD_CREST if btn_hover else HollowColors.TEXT_TITLE
        else:
            btn_label = "[REINO BLOQUEADO]"
            btn_col = (180, 80, 80)
            
        HollowCrestRenderer.draw_hollow_button(
            surface,
            btn_box,
            btn_label,
            self.font_hud,
            is_hovered=btn_hover and is_unlocked,
            text_color=btn_col
        )
        
        # Sub-hints on sides of launch button
        hint_prev = self.font_micro.render("‹ [A] Anterior", True, HollowColors.TEXT_MUTED)
        hint_next = self.font_micro.render("Próximo [D] ›", True, HollowColors.TEXT_MUTED)
        surface.blit(hint_prev, (card_rect.x + 18, btn_box.centery - 4))
        surface.blit(hint_next, (card_rect.right - hint_next.get_width() - 18, btn_box.centery - 4))

        # Status Toast Message
        if self.status_message:
            toast_s = self.font_small.render(self.status_message, True, (255, 230, 140))
            surface.blit(toast_s, toast_s.get_rect(center=(self.width // 2, 273)))

        # 6. Bottom footer & Back Button
        back_box = pygame.Rect(32, 328, 110, 22)
        back_hover = back_box.collidepoint(pygame.mouse.get_pos())
        HollowCrestRenderer.draw_hollow_button(surface, back_box, "VOLTAR [ESC]", self.font_desc, is_hovered=back_hover)
        
        esc_txt = self.font_desc.render("[A/D] Selecionar   |   [TAB / 1-3] Slots   |   [N] Novo Jogo   |   [ENTER] Confirmar", True, HollowColors.TEXT_MUTED)
        surface.blit(esc_txt, (self.width // 2 - esc_txt.get_width() // 2 + 50, 332))
