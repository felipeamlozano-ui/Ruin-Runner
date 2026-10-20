"""
Ruin Engine — Animated Magic Book Skill Tree Scene (Grimoire of Ascension).
Integrates craftpix-net-809047 animated magic book, turning page transitions, and spell icons.
Jogadores investem Orbes rúnicos em disciplinas marciais e arcanas.
Otimizado para resolução nativa 640x360 (16:9).
"""

import math
import os
import pygame
from typing import Dict, List, Any, Optional
from engine.scene_manager import Scene
from engine.save_manager import SAVE
from engine.input_manager import INPUT

SKILL_TREE_DATA = [
    {
        "page_title": "CAMINHO DA LÂMINA",
        "category": "combate",
        "description": "Domine as técnicas marciais antigas para dilacerar inimigos.",
        "skills": [
            {
                "id": "blade_sharpness",
                "name": "Afiação Rúnica",
                "icon": 1,
                "max_level": 5,
                "costs": [15, 30, 60, 100, 180],
                "desc": "Grava runas na lâmina, aumentando o dano físico em +12% por nível.",
                "bonus_prefix": "+",
                "bonus_suffix": "% Dano Básico",
                "bonus_values": [0, 12, 24, 36, 48, 60]
            },
            {
                "id": "combo_finisher",
                "name": "Finalizador Crítico",
                "icon": 2,
                "max_level": 3,
                "costs": [35, 75, 150],
                "desc": "O golpe final do combo desfere choque com alto dano crítico.",
                "bonus_prefix": "+",
                "bonus_suffix": "% Dano Finisher",
                "bonus_values": [0, 25, 50, 80]
            }
        ]
    },
    {
        "page_title": "MAESTRIA ARCANA",
        "category": "magia",
        "description": "Comande o fluxo elemental de éter e projéteis destruidores.",
        "skills": [
            {
                "id": "arcane_mastery",
                "name": "Eficiência de Éter",
                "icon": 4,
                "max_level": 5,
                "costs": [20, 45, 80, 130, 220],
                "desc": "Reduz o consumo de Mana de projéteis e magias em -10% por nível.",
                "bonus_prefix": "-",
                "bonus_suffix": "% Custo de MP",
                "bonus_values": [0, 10, 20, 30, 40, 50]
            },
            {
                "id": "cosmic_mana",
                "name": "Canalização Cósmica",
                "icon": 12,
                "max_level": 5,
                "costs": [25, 50, 90, 150, 250],
                "desc": "Expande o reservatório arcano de Mana e acelera a regeneração.",
                "bonus_prefix": "+",
                "bonus_suffix": " MP Máximo",
                "bonus_values": [0, 15, 30, 45, 60, 80]
            }
        ]
    },
    {
        "page_title": "CATACLISMO & ÁREA",
        "category": "area",
        "description": "Explosões rúnicas capazes de devastar grupos densos de monstros.",
        "skills": [
            {
                "id": "aoe_resonance",
                "name": "Ressonância de Choque",
                "icon": 6,
                "max_level": 5,
                "costs": [25, 50, 95, 160, 280],
                "desc": "Amplia o raio de alcance da explosão elemental em +15% por nível.",
                "bonus_prefix": "+",
                "bonus_suffix": "% Raio AoE",
                "bonus_values": [0, 15, 30, 45, 60, 75]
            }
        ]
    },
    {
        "page_title": "POSTURA & EVASÃO",
        "category": "defesa",
        "description": "A arte de se mover imperceptivelmente entre os golpes adversários.",
        "skills": [
            {
                "id": "shadow_step",
                "name": "Passo Sombrio (Dash)",
                "icon": 8,
                "max_level": 3,
                "costs": [30, 70, 140],
                "desc": "Aumenta os quadros de invulnerabilidade e reduz a Stamina do Dash.",
                "bonus_prefix": "-",
                "bonus_suffix": "% Custo Stamina",
                "bonus_values": [0, 15, 30, 45]
            }
        ]
    },
    {
        "page_title": "FÚRIA & ALQUIMIA",
        "category": "supremo",
        "description": "O poder absoluto do Ultimate e os segredos da vitalidade.",
        "skills": [
            {
                "id": "ultimate_wrath",
                "name": "Cólera Ancestral",
                "icon": 9,
                "max_level": 3,
                "costs": [50, 120, 240],
                "desc": "Aumenta o dano devastador do Ultimate e concede carga acelerada.",
                "bonus_prefix": "+",
                "bonus_suffix": "% Dano Ultimate",
                "bonus_values": [0, 25, 55, 90]
            },
            {
                "id": "alchemist_elixir",
                "name": "Elixir Puro",
                "icon": 10,
                "max_level": 3,
                "costs": [25, 60, 120],
                "desc": "Refina a fórmula alquímica para curar +20 HP extras por poção.",
                "bonus_prefix": "+",
                "bonus_suffix": " HP por Poção",
                "bonus_values": [0, 20, 40, 65]
            },
            {
                "id": "titan_heart",
                "name": "Coração de Titã",
                "icon": 11,
                "max_level": 5,
                "costs": [20, 45, 85, 140, 220],
                "desc": "Fortalece a constituição física aumentando a barra de Vida Máxima.",
                "bonus_prefix": "+",
                "bonus_suffix": " HP Máximo",
                "bonus_values": [0, 15, 30, 45, 60, 80]
            }
        ]
    }
]


class MagicBookScene(Scene):
    """Grimoire of Ascension UI Scene with animated page transitions and authentic book UI."""
    
    internal_size = (640, 360)
    
    def __init__(self, scene_manager, return_scene=None):
        self.scene_manager = scene_manager
        self.return_scene = return_scene
        
        self.width = 640
        self.height = 360
        
        self.page_index = 0
        self.skill_index = 0
        
        # Animation State Machine: "OPENING", "IDLE", "FLIP_LEFT", "FLIP_RIGHT", "CLOSING"
        self.state = "OPENING"
        self.anim_timer = 0.0
        self.anim_duration = 0.32  # Seconds for opening/closing
        self.flip_duration = 0.22  # Seconds for page flip
        
        self.feedback_msg = ""
        self.feedback_timer = 0.0
        
        self._init_fonts()
        self._load_sprites()
        self._create_ui_elements()

    @property
    def pages(self):
        return SKILL_TREE_DATA

    @property
    def skills(self):
        return SKILL_TREE_DATA[self.page_index]["skills"]

    def _init_fonts(self):
        """Initializes typography with clean system fonts ensuring accurate kerning for Portuguese accents."""
        try:
            self.font_title = pygame.font.SysFont("Georgia", 13, bold=True)
            self.font_page = pygame.font.SysFont("Georgia", 11, bold=True)
            self.font_skill = pygame.font.SysFont("Verdana", 9, bold=True)
            self.font_desc = pygame.font.SysFont("Verdana", 8)
            self.font_orbs = pygame.font.SysFont("Verdana", 10, bold=True)
            self.font_btn = pygame.font.SysFont("Verdana", 9, bold=True)
            self.font_hints = pygame.font.SysFont("Verdana", 8)
        except Exception:
            self.font_title = pygame.font.Font(None, 20)
            self.font_page = pygame.font.Font(None, 16)
            self.font_skill = pygame.font.Font(None, 14)
            self.font_desc = pygame.font.Font(None, 12)
            self.font_orbs = pygame.font.Font(None, 16)
            self.font_btn = pygame.font.Font(None, 14)
            self.font_hints = pygame.font.Font(None, 12)

    def _load_sprites(self):
        base_dir = os.path.join("assets", "sprites", "magic_book", "PNG")
        target_size = (510, 305)
        crop_rect = (13, 84, 246, 183)

        def _load_sheet_frames(fname: str, cols: int, rows: int, max_frames: Optional[int] = None) -> List[pygame.Surface]:
            path = os.path.join(base_dir, fname)
            if not os.path.exists(path):
                return []
            try:
                sheet = pygame.image.load(path)
                disp = pygame.display.get_surface()
                if disp:
                    sheet = sheet.convert_alpha()
                fw = sheet.get_width() // cols
                fh = sheet.get_height() // rows
                total = cols * rows if max_frames is None else max_frames
                frames = []
                cx, cy, cw, ch = crop_rect
                for i in range(total):
                    c = i % cols
                    r = i // cols
                    sub = sheet.subsurface((c * fw + cx, r * fh + cy, cw, ch))
                    frames.append(pygame.transform.scale(sub, target_size))
                return frames
            except Exception:
                return []

        # 1. Opening and Closing Animations (12 frames each)
        self.open_frames = _load_sheet_frames("Open_book.png", 4, 3, 12)
        self.close_frames = _load_sheet_frames("Close_book.png", 4, 3, 12)

        # 2. Page Turning Animations (15 active frames each)
        self.turn_right_frames = _load_sheet_frames("Turning_pages_right.png", 4, 4, 15)
        self.turn_left_frames = _load_sheet_frames("Turning_pages_left.png", 4, 4, 15)

        # 3. Static Book Fallback
        if self.open_frames:
            self.book_surf = self.open_frames[-1]
        else:
            book_path = os.path.join("assets", "sprites", "magic_book", "open_book_full.png")
            if os.path.exists(book_path):
                raw = pygame.image.load(book_path)
                disp = pygame.display.get_surface()
                if disp:
                    raw = raw.convert_alpha()
                self.book_surf = pygame.transform.scale(raw, target_size)
            else:
                self.book_surf = pygame.Surface(target_size, pygame.SRCALPHA)
                self.book_surf.fill((220, 205, 155))

        # 4. Authentic Skill Icons (Icon1_big.png .. Icon20_big.png)
        self.icon_surfs = {}
        icon_dir = os.path.join(base_dir, "Icons")
        for i in range(1, 21):
            ip = os.path.join(icon_dir, f"Icon{i}_big.png")
            if not os.path.exists(ip):
                ip = os.path.join(icon_dir, f"Icon{i}.png")
            if os.path.exists(ip):
                try:
                    img = pygame.image.load(ip)
                    disp = pygame.display.get_surface()
                    if disp:
                        img = img.convert_alpha()
                    # Scale to a 34x34 jewel inside the skill slot
                    self.icon_surfs[i] = pygame.transform.scale(img, (34, 34))
                except Exception:
                    pass

        # 5. Load UI tileset and bookmarks for authentic buttons
        self.info_tileset = None
        self.bookmarks = None
        it_path = os.path.join(base_dir, "info_tileset.png")
        if os.path.exists(it_path):
            self.info_tileset = pygame.image.load(it_path)
        bm_path = os.path.join(base_dir, "bookmarks.png")
        if os.path.exists(bm_path):
            self.bookmarks = pygame.image.load(bm_path)

    def _create_ui_elements(self):
        """Constructs textured buttons from info_tileset.png and bookmarks.png."""
        self.btn_upgrade_surf = self._build_textured_button(184, 28, style="golden")
        self.btn_disabled_surf = self._build_textured_button(184, 28, style="weathered")
        self.btn_max_surf = self._build_textured_button(184, 28, style="emerald")

    def _build_textured_button(self, w: int, h: int, style: str = "golden") -> pygame.Surface:
        """9-slice button with authentic book tileset and bookmark ribbon marker."""
        btn = pygame.Surface((w, h), pygame.SRCALPHA)
        if not self.info_tileset:
            # Fallback procedural button
            col = (195, 145, 55) if style == "golden" else ((160, 150, 135) if style == "weathered" else (100, 150, 85))
            pygame.draw.rect(btn, col, (0, 0, w, h), border_radius=3)
            pygame.draw.rect(btn, (80, 50, 20), (0, 0, w, h), width=1, border_radius=3)
            return btn

        # Select tile slice y-coordinate
        base_y = 48 if style == "golden" else (0 if style == "weathered" else 96)
        base_y = min(base_y, self.info_tileset.get_height() - 32)
        
        # 9-slice construction: corners 8x8, borders stretched
        tl = self.info_tileset.subsurface((0, base_y, 8, 8))
        tr = self.info_tileset.subsurface((24, base_y, 8, 8))
        bl = self.info_tileset.subsurface((0, base_y + 24, 8, 8))
        br = self.info_tileset.subsurface((24, base_y + 24, 8, 8))
        
        top = pygame.transform.scale(self.info_tileset.subsurface((8, base_y, 16, 8)), (w - 16, 8))
        bot = pygame.transform.scale(self.info_tileset.subsurface((8, base_y + 24, 16, 8)), (w - 16, 8))
        left = pygame.transform.scale(self.info_tileset.subsurface((0, base_y + 8, 8, 16)), (8, h - 16))
        right = pygame.transform.scale(self.info_tileset.subsurface((24, base_y + 8, 8, 16)), (8, h - 16))
        center = pygame.transform.scale(self.info_tileset.subsurface((8, base_y + 8, 16, 16)), (w - 16, h - 16))
        
        btn.blit(center, (8, 8))
        btn.blit(top, (8, 0))
        btn.blit(bot, (8, h - 8))
        btn.blit(left, (0, 8))
        btn.blit(right, (w - 8, 8))
        btn.blit(tl, (0, 0))
        btn.blit(tr, (w - 8, 0))
        btn.blit(bl, (0, h - 8))
        btn.blit(br, (w - 8, h - 8))

        return btn

    def handle_events(self, events: list[pygame.event.Event]):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._start_close_book()
                    return
                
                # Ignore navigation inputs during page flipping or book opening/closing
                if self.state != "IDLE":
                    continue

                if event.key in (pygame.K_a, pygame.K_LEFT):
                    self._trigger_page_flip(-1)
                elif event.key in (pygame.K_d, pygame.K_RIGHT):
                    self._trigger_page_flip(1)
                elif event.key in (pygame.K_w, pygame.K_UP):
                    self._change_skill(-1)
                elif event.key in (pygame.K_s, pygame.K_DOWN):
                    self._change_skill(1)
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self._attempt_upgrade()

    def _trigger_page_flip(self, delta: int):
        """Starts animated page turn transition."""
        self.page_index = (self.page_index + delta) % len(SKILL_TREE_DATA)
        self.skill_index = 0
        self.state = "FLIP_RIGHT" if delta > 0 else "FLIP_LEFT"
        self.anim_timer = 0.0

    def _change_page(self, delta: int):
        """Alias for _trigger_page_flip for backward compatibility."""
        self._trigger_page_flip(delta)

    def _change_skill(self, delta: int):
        page = SKILL_TREE_DATA[self.page_index]
        skills = page["skills"]
        self.skill_index = (self.skill_index + delta) % len(skills)

    def _attempt_upgrade(self):
        page = SKILL_TREE_DATA[self.page_index]
        skill = page["skills"][self.skill_index]
        cur_lv = SAVE.get_skill_level(skill["id"])
        
        if cur_lv >= skill["max_level"]:
            self.feedback_msg = "TALENTO MAXIMIZADO!"
            self.feedback_timer = 2.0
            return
            
        cost = skill["costs"][cur_lv]
        if SAVE.get_orbs() >= cost:
            SAVE.spend_orbs(cost)
            SAVE.set_skill_level(skill["id"], cur_lv + 1)
            self.feedback_msg = f"TALENTO APRIMORADO! (Nv. {cur_lv + 1})"
            self.feedback_timer = 2.0
        else:
            self.feedback_msg = f"ORBES INSUFICIENTES! ({cost})"
            self.feedback_timer = 2.0

    def _start_close_book(self):
        if self.close_frames:
            self.state = "CLOSING"
            self.anim_timer = 0.0
        else:
            self._finish_close()

    def _finish_close(self):
        if self.return_scene:
            self.scene_manager.change_scene(self.return_scene)
        else:
            from scenes.main_menu import MainMenuScene
            self.scene_manager.change_scene(MainMenuScene(self.scene_manager))

    def update(self, dt: float):
        if self.feedback_timer > 0:
            self.feedback_timer -= dt

        if self.state == "OPENING":
            self.anim_timer += dt
            if self.anim_timer >= self.anim_duration:
                self.state = "IDLE"
        elif self.state in ("FLIP_LEFT", "FLIP_RIGHT"):
            self.anim_timer += dt
            if self.anim_timer >= self.flip_duration:
                self.state = "IDLE"
        elif self.state == "CLOSING":
            self.anim_timer += dt
            if self.anim_timer >= self.anim_duration:
                self._finish_close()

    def draw(self, surface: pygame.Surface):
        # 1. Mystical background
        surface.fill((8, 10, 16))
        
        # Subtle ambient celestial glow behind book
        center_x = self.width // 2
        center_y = self.height // 2 + 12
        pygame.draw.circle(surface, (18, 22, 36), (center_x, center_y), 190)
        pygame.draw.circle(surface, (28, 38, 62), (center_x, center_y), 190, width=1)
        
        # 2. Header: Title & Orbs Balance
        title_surf = self.font_title.render("GRIMOIRE DE ASCENSÃO", True, (255, 220, 110))
        surface.blit(title_surf, title_surf.get_rect(center=(center_x, 14)))
        
        orbs_txt = f"SEUS ORBES: {SAVE.get_orbs()}"
        orbs_surf = self.font_orbs.render(orbs_txt, True, (160, 225, 255))
        surface.blit(orbs_surf, orbs_surf.get_rect(center=(center_x, 28)))
        
        # 3. Centerpiece Book Rendering
        book_rect = self.book_surf.get_rect(center=(center_x, center_y))

        if self.state == "OPENING" and self.open_frames:
            progress = min(1.0, self.anim_timer / self.anim_duration)
            idx = int(progress * (len(self.open_frames) - 1))
            surface.blit(self.open_frames[idx], book_rect)
            return

        if self.state == "CLOSING" and self.close_frames:
            progress = min(1.0, self.anim_timer / self.anim_duration)
            idx = int(progress * (len(self.close_frames) - 1))
            surface.blit(self.close_frames[idx], book_rect)
            return

        if self.state == "FLIP_RIGHT" and self.turn_right_frames:
            progress = min(1.0, self.anim_timer / self.flip_duration)
            idx = int(progress * (len(self.turn_right_frames) - 1))
            surface.blit(self.turn_right_frames[idx], book_rect)
            return

        if self.state == "FLIP_LEFT" and self.turn_left_frames:
            progress = min(1.0, self.anim_timer / self.flip_duration)
            idx = int(progress * (len(self.turn_left_frames) - 1))
            surface.blit(self.turn_left_frames[idx], book_rect)
            return

        # Render static open book
        surface.blit(self.book_surf, book_rect)

        # 4. Page layout zones (calibrated strictly within the parchment bounds)
        left_page_x = book_rect.left + 38
        left_page_w = 196
        right_page_x = book_rect.centerx + 18
        right_page_w = 196
        content_top = book_rect.top + 32
        
        cur_page = SKILL_TREE_DATA[self.page_index]
        skills = cur_page["skills"]
        
        # 5. Left Page Content: Discipline Header & Skill List
        p_hdr = self.font_page.render(cur_page["page_title"], True, (65, 38, 22))
        surface.blit(p_hdr, p_hdr.get_rect(center=(left_page_x + left_page_w // 2, content_top + 4)))
        
        # Ornate Divider line
        pygame.draw.line(surface, (180, 155, 120), (left_page_x + 10, content_top + 16), (left_page_x + left_page_w - 10, content_top + 16), 1)
        
        # Render skills on left page
        sy = content_top + 24
        for idx, sk in enumerate(skills):
            is_selected = (idx == self.skill_index)
            cur_lv = SAVE.get_skill_level(sk["id"])
            
            # Selection Highlight Box
            box_rect = pygame.Rect(left_page_x, sy, left_page_w, 48)
            if is_selected:
                pygame.draw.rect(surface, (238, 220, 168), box_rect, border_radius=3)
                pygame.draw.rect(surface, (150, 105, 55), box_rect, width=1, border_radius=3)
            else:
                pygame.draw.rect(surface, (222, 206, 156), box_rect, border_radius=3)
                pygame.draw.rect(surface, (190, 172, 130), box_rect, width=1, border_radius=3)
            
            # Skill Icon from magic book pack
            ic_surf = self.icon_surfs.get(sk["icon"])
            if ic_surf:
                surface.blit(ic_surf, (left_page_x + 6, sy + 7))
                
            # Skill Name
            sk_name = self.font_skill.render(sk["name"], True, (45, 25, 15) if is_selected else (75, 50, 35))
            surface.blit(sk_name, (left_page_x + 44, sy + 8))
            
            # Level Pip Boxes
            pip_x = left_page_x + 44
            pip_y = sy + 26
            for p in range(sk["max_level"]):
                filled = p < cur_lv
                col = (195, 125, 25) if filled else (210, 195, 155)
                b_col = (130, 80, 20) if filled else (165, 145, 115)
                pygame.draw.rect(surface, col, (pip_x + p * 11, pip_y, 8, 8), border_radius=1)
                pygame.draw.rect(surface, b_col, (pip_x + p * 11, pip_y, 8, 8), width=1, border_radius=1)
                
            nv_txt = self.font_desc.render(f"Nv. {cur_lv}/{sk['max_level']}", True, (110, 75, 35))
            surface.blit(nv_txt, (pip_x + sk["max_level"] * 11 + 6, pip_y + 1))
            
            sy += 56
            
        # 6. Right Page Content: Selected Skill Details
        sel_skill = skills[self.skill_index]
        sel_lv = SAVE.get_skill_level(sel_skill["id"])
        
        r_title = self.font_page.render("DETALHES DO TALENTO", True, (65, 38, 22))
        surface.blit(r_title, r_title.get_rect(center=(right_page_x + right_page_w // 2, content_top + 4)))
        
        # Divider line
        pygame.draw.line(surface, (180, 155, 120), (right_page_x + 10, content_top + 16), (right_page_x + right_page_w - 10, content_top + 16), 1)
        
        # Full Name & Level Badge
        r_name = self.font_skill.render(f"{sel_skill['name']} [{sel_lv}/{sel_skill['max_level']}]", True, (150, 40, 20))
        surface.blit(r_name, (right_page_x + 6, content_top + 24))
        
        # Word-wrapped description with strict pixel width measurement (zero split words)
        desc_y = content_top + 40
        max_desc_w = right_page_w - 12
        words = sel_skill["desc"].split(" ")
        current_line = ""
        for w in words:
            candidate = f"{current_line} {w}".strip()
            if self.font_desc.size(candidate)[0] <= max_desc_w:
                current_line = candidate
            else:
                if current_line:
                    surface.blit(self.font_desc.render(current_line, True, (80, 60, 45)), (right_page_x + 6, desc_y))
                    desc_y += 12
                current_line = w
        if current_line:
            surface.blit(self.font_desc.render(current_line, True, (80, 60, 45)), (right_page_x + 6, desc_y))
            desc_y += 16
            
        # Current Bonus vs Next Bonus
        cur_bonus = sel_skill["bonus_values"][sel_lv]
        surface.blit(self.font_desc.render(f"Bônus Atual: {sel_skill['bonus_prefix']}{cur_bonus}{sel_skill['bonus_suffix']}", True, (45, 85, 35)), (right_page_x + 6, desc_y))
        desc_y += 13
        
        if sel_lv < sel_skill["max_level"]:
            nxt_bonus = sel_skill["bonus_values"][sel_lv + 1]
            cost = sel_skill["costs"][sel_lv]
            surface.blit(self.font_desc.render(f"Próximo Nv:  {sel_skill['bonus_prefix']}{nxt_bonus}{sel_skill['bonus_suffix']}", True, (120, 80, 25)), (right_page_x + 6, desc_y))
            desc_y += 16
            
            # Cost indicator
            can_afford = SAVE.get_orbs() >= cost
            cost_col = (40, 115, 45) if can_afford else (175, 45, 35)
            cost_str = f"Custo: {cost} Orbes"
            surface.blit(self.font_skill.render(cost_str, True, cost_col), (right_page_x + 6, desc_y))
            desc_y += 18
            
            # Styled Upgrade Button (Authentic Book Tileset & Ribbon Marker)
            btn_surf = self.btn_upgrade_surf if can_afford else self.btn_disabled_surf
            btn_pos = (right_page_x + (right_page_w - btn_surf.get_width()) // 2, desc_y)
            surface.blit(btn_surf, btn_pos)
            
            btn_lbl = self.font_btn.render("[ESPAÇO] APRIMORAR", True, (40, 25, 10) if can_afford else (90, 80, 70))
            surface.blit(btn_lbl, btn_lbl.get_rect(center=(btn_pos[0] + btn_surf.get_width() // 2, btn_pos[1] + btn_surf.get_height() // 2)))
        else:
            desc_y += 20
            max_pos = (right_page_x + (right_page_w - self.btn_max_surf.get_width()) // 2, desc_y)
            surface.blit(self.btn_max_surf, max_pos)
            max_lbl = self.font_btn.render("TALENTO MAXIMIZADO", True, (25, 60, 20))
            surface.blit(max_lbl, max_lbl.get_rect(center=(max_pos[0] + self.btn_max_surf.get_width() // 2 + 6, max_pos[1] + self.btn_max_surf.get_height() // 2)))

        # 7. Feedback Toast Message
        if self.feedback_timer > 0:
            fb_surf = self.font_skill.render(self.feedback_msg, True, (255, 235, 120))
            fb_rect = fb_surf.get_rect(center=(center_x, book_rect.bottom - 14))
            pad = 6
            bg_box = fb_rect.inflate(pad * 2, pad)
            pygame.draw.rect(surface, (30, 20, 15), bg_box, border_radius=3)
            pygame.draw.rect(surface, (160, 120, 40), bg_box, width=1, border_radius=3)
            surface.blit(fb_surf, fb_rect)

        # 8. Bottom Navigation Hints
        hint_surf = self.font_hints.render("[A/D] Folhear Páginas   |   [W/S] Selecionar   |   [ESPAÇO] Aprimorar   |   [ESC] Fechar", True, (140, 155, 175))
        surface.blit(hint_surf, hint_surf.get_rect(center=(center_x, self.height - 12)))
