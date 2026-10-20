"""
Ruin Engine V3.0 — Interactive Keyboard & Mouse Pixel Art Tutorial Overlay.
Renders pixel-art keycaps and mouse controls with dynamic glowing highlights
for active actions, progress tracking, and instant tutorial skip options.
"""

import math
import os
import pygame
from typing import Set, Tuple, Optional

class KeyboardOverlay:
    """Manages the visual keyboard & mouse overlay for guided tutorials."""
    
    _KEY_SURF_CACHE = {}
    
    def __init__(self):
        self._glow_phase = 0.0
        self._init_fonts()
        self._load_mouse_sprite()
        
    def _init_fonts(self):
        from ui.hollow_ui import HollowFonts
        self.font_key = HollowFonts.get(10, bold=True)
        self.font_hud = HollowFonts.get(11, bold=True)
        self.font_task = HollowFonts.get(12, bold=True)
        self.font_small = HollowFonts.get(9)

    def _load_mouse_sprite(self):
        mouse_path = os.path.join("assets", "sprites", "tutorial_kb", "PNG", "Mouse_base.png")
        if os.path.exists(mouse_path):
            try:
                raw = pygame.image.load(mouse_path).convert_alpha()
                # Downscale to compact pixel art icon (28x36)
                self.mouse_surf = pygame.transform.smoothscale(raw, (28, 36))
            except Exception:
                self.mouse_surf = None
        else:
            self.mouse_surf = None

    def update(self, dt: float):
        self._glow_phase = (self._glow_phase + dt * 4.5) % (2.0 * math.pi)

    def _draw_key(self, surface: pygame.Surface, x: int, y: int, w: int, h: int, label: str, is_active: bool, is_pressed: bool):
        cache_key = (label, w, h, is_active, is_pressed, int(self._glow_phase * 4))
        
        # Draw key base
        rect = pygame.Rect(x, y, w, h)
        
        if is_active:
            # Pulsating gold/cyan aura
            pulse = (math.sin(self._glow_phase) + 1.0) * 0.5 # 0.0 to 1.0
            glow_col = (int(255 * (0.8 + 0.2 * pulse)), int(190 * (0.8 + 0.2 * pulse)), int(50 * (0.8 + 0.2 * pulse)))
            halo_rect = rect.inflate(6, 6)
            halo = pygame.Surface((halo_rect.width, halo_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(halo, (*glow_col, int(90 + 70 * pulse)), halo.get_rect(), border_radius=4)
            surface.blit(halo, halo_rect.topleft)
            
            # Key body
            bg_col = (240, 200, 70) if not is_pressed else (190, 150, 40)
            border_col = (255, 255, 220)
            text_col = (20, 20, 25)
        else:
            bg_col = (45, 48, 60) if not is_pressed else (30, 32, 40)
            border_col = (80, 85, 105)
            text_col = (180, 185, 200)

        # 3D beveled pixel button from authentic craftpix-net-726651 button sheet
        from ui.input_prompt_icon import _BLANK_SHEET, _init_icon_assets
        _init_icon_assets()
        drawn_from_sheet = False
        if _BLANK_SHEET and w <= 32:
            try:
                sheet_y = 16 if is_pressed else 0
                key_sub = _BLANK_SHEET.subsurface((0, sheet_y, 16, 16))
                scaled_key = pygame.transform.scale(key_sub, (w, h))
                if is_active:
                    scaled_key = scaled_key.copy()
                    scaled_key.fill((255, 215, 80), special_flags=pygame.BLEND_RGBA_MULT)
                surface.blit(scaled_key, (rect.x, rect.y))
                drawn_from_sheet = True
            except Exception:
                pass

        if not drawn_from_sheet:
            pygame.draw.rect(surface, (15, 15, 20), (rect.x, rect.y + 2, rect.width, rect.height), border_radius=3)
            pygame.draw.rect(surface, bg_col, rect, border_radius=3)
            pygame.draw.rect(surface, border_col, rect, width=1, border_radius=3)
            pygame.draw.line(surface, (min(255, bg_col[0] + 40), min(255, bg_col[1] + 40), min(255, bg_col[2] + 40)),
                             (rect.left + 2, rect.top + 1), (rect.right - 3, rect.top + 1))
                         
        # Label render
        txt = self.font_key.render(label, True, text_col)
        t_rect = txt.get_rect(center=rect.center)
        if is_pressed:
            t_rect.y += 1
        surface.blit(txt, t_rect)

    def draw_hud(self, surface: pygame.Surface, active_keys: Set[str], task_title: str, task_desc: str, step: int, total_steps: int, skip_hovered: bool = False, with_player_hud: bool = False) -> pygame.Rect:
        """
        Renders top tutorial status card and bottom pixel art keyboard deck.
        Returns the skip button Rect for mouse click handling.
        """
        from ui.hollow_ui import HollowCrestRenderer, HollowColors
        sw, sh = surface.get_size()
        
        # 1. Top Objective Banner
        if with_player_hud:
            top_x = 226
            top_y = 8
            top_w = sw - top_x - 10
            top_h = 62
            banner_rect = pygame.Rect(top_x, top_y, top_w, top_h)
            HollowCrestRenderer.draw_filigree_panel(surface, banner_rect, bg_color=(10, 12, 18, 235), border_color=(75, 82, 100), corner_flourish=True)
            
            prog_txt = self.font_small.render(f"‹ TREINAMENTO DOS HERÓIS [{step}/{total_steps}] ›", True, HollowColors.GOLD_CREST)
            surface.blit(prog_txt, (top_x + 12, top_y + 7))
            
            task_surf = self.font_task.render(task_title, True, HollowColors.TEXT_TITLE)
            surface.blit(task_surf, (top_x + 12, top_y + 22))
            
            desc_surf = self.font_small.render(task_desc, True, HollowColors.TEXT_NORMAL)
            surface.blit(desc_surf, (top_x + 12, top_y + 42))
            
            skip_w, skip_h = 118, 22
            skip_rect = pygame.Rect(top_x + top_w - skip_w - 8, top_y + 8, skip_w, skip_h)
            HollowCrestRenderer.draw_hollow_button(
                surface,
                skip_rect,
                "PULAR [ESC]",
                self.font_small,
                is_hovered=skip_hovered,
                text_color=(255, 200, 200) if skip_hovered else (210, 180, 185)
            )
            
            # Bottom Deck alongside Skill Hotbar
            deck_w = 428
            deck_h = 58
            deck_x = sw - deck_w - 8
            deck_y = sh - deck_h - 6
            deck_rect = pygame.Rect(deck_x, deck_y, deck_w, deck_h)
            HollowCrestRenderer.draw_filigree_panel(surface, deck_rect, bg_color=(10, 12, 18, 235), border_color=(60, 68, 85), corner_flourish=True)
            
            kx, ky = deck_x + 8, deck_y + 6
            self._draw_key(surface, kx + 20, ky, 20, 18, "W", "W" in active_keys, False)
            self._draw_key(surface, kx, ky + 20, 20, 18, "A", "A" in active_keys, False)
            self._draw_key(surface, kx + 20, ky + 20, 20, 18, "S", "S" in active_keys, False)
            self._draw_key(surface, kx + 40, ky + 20, 20, 18, "D", "D" in active_keys, False)
            
            sp_x = kx + 68
            self._draw_key(surface, sp_x, ky + 10, 56, 22, "ESPAÇO", "SPACE" in active_keys, False)
            
            cx = sp_x + 64
            self._draw_key(surface, cx, ky + 10, 22, 22, "J", "J" in active_keys, False)
            lbl_atk = self.font_small.render("ATK", True, HollowColors.GOLD_CREST if "J" in active_keys else HollowColors.TEXT_MUTED)
            surface.blit(lbl_atk, lbl_atk.get_rect(center=(cx + 11, ky + 40)))
            
            self._draw_key(surface, cx + 28, ky + 10, 22, 22, "K", "K" in active_keys, False)
            lbl_sk1 = self.font_small.render("MAG", True, (100, 200, 255) if "K" in active_keys else HollowColors.TEXT_MUTED)
            surface.blit(lbl_sk1, lbl_sk1.get_rect(center=(cx + 28 + 11, ky + 40)))

            self._draw_key(surface, cx + 56, ky + 10, 22, 22, "E", "E" in active_keys, False)
            lbl_sk2 = self.font_small.render("AOE", True, (220, 130, 255) if "E" in active_keys else HollowColors.TEXT_MUTED)
            surface.blit(lbl_sk2, lbl_sk2.get_rect(center=(cx + 56 + 11, ky + 40)))

            self._draw_key(surface, cx + 84, ky + 10, 22, 22, "Q", "Q" in active_keys, False)
            lbl_ult = self.font_small.render("ULT", True, (255, 90, 90) if "Q" in active_keys else HollowColors.TEXT_MUTED)
            surface.blit(lbl_ult, lbl_ult.get_rect(center=(cx + 84 + 11, ky + 40)))
            
            sx = cx + 114
            self._draw_key(surface, sx, ky + 10, 40, 22, "SHIFT", "SHIFT" in active_keys, False)
            lbl_dsh = self.font_small.render("DASH", True, HollowColors.TEXT_MUTED)
            surface.blit(lbl_dsh, lbl_dsh.get_rect(center=(sx + 20, ky + 40)))
            
            self._draw_key(surface, sx + 46, ky + 10, 22, 22, "1", "1" in active_keys, False)
            lbl_pot = self.font_small.render("HEAL", True, (100, 255, 120) if "1" in active_keys else HollowColors.TEXT_MUTED)
            surface.blit(lbl_pot, lbl_pot.get_rect(center=(sx + 46 + 11, ky + 40)))

            mx = sx + 76
            my = ky + 8
            pygame.draw.rect(surface, (25, 28, 38), (mx, my, 18, 24), border_radius=4)
            pygame.draw.rect(surface, (70, 78, 98), (mx, my, 18, 24), width=1, border_radius=4)
            pygame.draw.line(surface, (70, 78, 98), (mx, my + 11), (mx + 17, my + 11), 1)
            pygame.draw.line(surface, (70, 78, 98), (mx + 9, my), (mx + 9, my + 11), 1)
            if "MOUSE_L" in active_keys or "J" in active_keys:
                pygame.draw.rect(surface, (255, 200, 70), (mx + 1, my + 1, 8, 10), border_top_left_radius=3)
            if "MOUSE_R" in active_keys or "K" in active_keys:
                pygame.draw.rect(surface, (100, 200, 255), (mx + 9, my + 1, 8, 10), border_top_right_radius=3)
            lbl_m = self.font_small.render("MOUSE", True, HollowColors.TEXT_MUTED)
            surface.blit(lbl_m, lbl_m.get_rect(center=(mx + 9, ky + 40)))
            
            return skip_rect
        else:
            top_bar = pygame.Surface((sw - 40, 54), pygame.SRCALPHA)
            top_bar.fill((15, 18, 28, 220))
            pygame.draw.rect(top_bar, (80, 110, 160), top_bar.get_rect(), width=1, border_radius=4)
            
            # Progress & Title
            prog_txt = self.font_small.render(f"TREINAMENTO DOS HERÓIS [{step}/{total_steps}]", True, (255, 215, 80))
            top_bar.blit(prog_txt, (14, 8))
            
            task_surf = self.font_task.render(task_title, True, (245, 245, 255))
            top_bar.blit(task_surf, (14, 22))
            
            desc_surf = self.font_small.render(task_desc, True, (170, 185, 215))
            top_bar.blit(desc_surf, (14, 38))
            
            # 2. Skip Tutorial Button (Top Right)
            skip_w, skip_h = 140, 26
            skip_rect = pygame.Rect(sw - 20 - skip_w - 6, 20 + 14, skip_w, skip_h)
            btn_bg = (140, 40, 50) if skip_hovered else (45, 25, 35)
            btn_border = (220, 80, 90) if skip_hovered else (150, 60, 70)
            
            pygame.draw.rect(surface, btn_bg, skip_rect, border_radius=4)
            pygame.draw.rect(surface, btn_border, skip_rect, width=1, border_radius=4)
            skip_txt = self.font_small.render("PULAR TUTORIAL [ESC]", True, (255, 240, 240))
            surface.blit(skip_txt, skip_txt.get_rect(center=skip_rect.center))
            
            surface.blit(top_bar, (20, 20))
            
            # 3. Bottom Keyboard Deck
            deck_w, deck_h = 560, 68
            deck_x = (sw - deck_w) // 2
            deck_y = sh - deck_h - 12
            
            deck_surf = pygame.Surface((deck_w, deck_h), pygame.SRCALPHA)
            deck_surf.fill((12, 14, 22, 215))
            pygame.draw.rect(deck_surf, (55, 65, 85), deck_surf.get_rect(), width=1, border_radius=6)
            surface.blit(deck_surf, (deck_x, deck_y))
            
            # Render Key Groups
            # WASD
            kx, ky = deck_x + 14, deck_y + 12
            self._draw_key(surface, kx + 24, ky, 22, 20, "W", "W" in active_keys, False)
            self._draw_key(surface, kx, ky + 24, 22, 20, "A", "A" in active_keys, False)
            self._draw_key(surface, kx + 24, ky + 24, 22, 20, "S", "S" in active_keys, False)
            self._draw_key(surface, kx + 48, ky + 24, 22, 20, "D", "D" in active_keys, False)
            
            lbl_mov = self.font_small.render("ANDAR", True, (140, 150, 175))
            surface.blit(lbl_mov, (kx + 16, ky + 48))
            
            # SPACE
            sp_x = kx + 85
            self._draw_key(surface, sp_x, ky + 12, 80, 26, "ESPAÇO", "SPACE" in active_keys, False)
            lbl_jmp = self.font_small.render("PULAR / DUPLO", True, (140, 150, 175))
            surface.blit(lbl_jmp, (sp_x + 2, ky + 48))
            
            # COMBAT KEYS [J] [K] [E] [Q]
            cx = sp_x + 92
            self._draw_key(surface, cx, ky + 12, 24, 24, "J", "J" in active_keys, False)
            lbl_atk = self.font_small.render("ATACAR", True, (255, 200, 100) if "J" in active_keys else (140, 150, 175))
            surface.blit(lbl_atk, lbl_atk.get_rect(center=(cx + 12, ky + 45)))
            
            self._draw_key(surface, cx + 38, ky + 12, 24, 24, "K", "K" in active_keys, False)
            lbl_sk1 = self.font_small.render("MAGIA", True, (100, 200, 255) if "K" in active_keys else (140, 150, 175))
            surface.blit(lbl_sk1, lbl_sk1.get_rect(center=(cx + 38 + 12, ky + 45)))

            self._draw_key(surface, cx + 76, ky + 12, 24, 24, "E", "E" in active_keys, False)
            lbl_sk2 = self.font_small.render("ÁREA", True, (220, 130, 255) if "E" in active_keys else (140, 150, 175))
            surface.blit(lbl_sk2, lbl_sk2.get_rect(center=(cx + 76 + 12, ky + 45)))

            self._draw_key(surface, cx + 114, ky + 12, 24, 24, "Q", "Q" in active_keys, False)
            lbl_ult = self.font_small.render("ULTI", True, (255, 90, 90) if "Q" in active_keys else (140, 150, 175))
            surface.blit(lbl_ult, lbl_ult.get_rect(center=(cx + 114 + 12, ky + 45)))
            
            # SURVIVAL [SHIFT] [1]
            sx = cx + 152
            self._draw_key(surface, sx, ky + 12, 44, 24, "SHIFT", "SHIFT" in active_keys, False)
            lbl_dsh = self.font_small.render("DASH", True, (140, 150, 175))
            surface.blit(lbl_dsh, lbl_dsh.get_rect(center=(sx + 22, ky + 45)))
            
            self._draw_key(surface, sx + 52, ky + 12, 24, 24, "1", "1" in active_keys, False)
            lbl_pot = self.font_small.render("CURA", True, (100, 255, 120) if "1" in active_keys else (140, 150, 175))
            surface.blit(lbl_pot, lbl_pot.get_rect(center=(sx + 52 + 12, ky + 45)))

            # Pixel Art Mouse
            mx = sx + 88
            my = ky + 10
            pygame.draw.rect(surface, (45, 48, 60), (mx, my, 20, 28), border_radius=6)
            pygame.draw.rect(surface, (80, 85, 105), (mx, my, 20, 28), width=1, border_radius=6)
            pygame.draw.line(surface, (80, 85, 105), (mx, my + 13), (mx + 19, my + 13), 1)
            pygame.draw.line(surface, (80, 85, 105), (mx + 10, my), (mx + 10, my + 13), 1)
            pygame.draw.rect(surface, (140, 150, 175), (mx + 9, my + 4, 3, 5), border_radius=1)
            if "MOUSE_L" in active_keys or "J" in active_keys:
                pygame.draw.rect(surface, (255, 200, 70), (mx + 1, my + 1, 9, 12), border_top_left_radius=5)
            if "MOUSE_R" in active_keys or "K" in active_keys:
                pygame.draw.rect(surface, (100, 200, 255), (mx + 10, my + 1, 9, 12), border_top_right_radius=5)
            lbl_m = self.font_small.render("MOUSE", True, (140, 150, 175))
            surface.blit(lbl_m, lbl_m.get_rect(center=(mx + 10, ky + 45)))
            
            return skip_rect
