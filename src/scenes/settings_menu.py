"""
Ruin Engine — Hollow Knight Aesthetic Settings Menu Scene.
Faithfully recreates the clean two-column layout, delicate filigree divider,
floating embers, and serif typography of Hollow Knight Options UI.
"""

import math
import pygame
from typing import List, Tuple, Any
from engine.scene_manager import Scene
from config.settings import SETTINGS
from engine.v3.core.profiler import PROFILER
from ui.hollow_ui import AtmosphereFX, HollowCrestRenderer, HollowFonts

class SettingsMenuScene(Scene):
    """System Settings Scene inspired directly by Hollow Knight Options UI."""
    
    internal_size = (640, 360)
    TABS = ["VÍDEO & TELA", "ÁUDIO & SOM", "GRÁFICOS", "ACESSIBILIDADE"]
    
    def __init__(self, scene_manager, previous_scene):
        self.scene_manager = scene_manager
        self.previous_scene = previous_scene
        
        self.width = 640
        self.height = 360
        
        self.active_tab = 0
        self.selected_index = 0
        self.time_sec = 0.0
        
        # Atmospheric Rising Embers (Image 2 style)
        self.atmosphere = AtmosphereFX(self.width, self.height, theme="ember", particle_count=48)
        
    def _get_tab_options(self) -> List[Tuple[str, str, Any]]:
        """Returns list of tuples (label, current_value_str, handler_func)."""
        if self.active_tab == 0:
            # VIDEO & DISPLAY (Matches reference image directly)
            res = SETTINGS.RESOLUTIONS[SETTINGS.RESOLUTION_INDEX]
            fs = "TELA CHEIA" if SETTINGS.FULLSCREEN else "JANELA"
            st = "PREENCHER TELA" if SETTINGS.FULLSCREEN_STRETCH else "BARRAS 4:3"
            br_str = f"{SETTINGS.BRIGHTNESS:+.2f}" if SETTINGS.BRIGHTNESS != 0 else "PADRÃO"
            ct_str = f"{SETTINGS.CONTRAST:.2f}"
            return [
                ("RESOLUÇÃO DE EXIBIÇÃO", f"{res[0]} x {res[1]}", self._toggle_res),
                ("MODO DE TELA", fs, self._toggle_fullscreen),
                ("PROPORÇÃO DE TELA", st, self._toggle_stretch),
                ("AJUSTE DE BRILHO", br_str, self._adjust_brightness),
                ("AJUSTE DE CONTRASTE", ct_str, self._adjust_contrast),
            ]
        elif self.active_tab == 1:
            # AUDIO
            m_pct = int(SETTINGS.MASTER_VOLUME * 100)
            b_pct = int(SETTINGS.MUSIC_VOLUME * 100)
            s_pct = int(SETTINGS.SFX_VOLUME * 100)
            return [
                ("VOLUME GERAL (MASTER)", f"{m_pct}%", self._adjust_master_vol),
                ("MÚSICA DE FUNDO (BGM)", f"{b_pct}%", self._adjust_music_vol),
                ("EFEITOS SONOROS (SFX)", f"{s_pct}%", self._adjust_sfx_vol),
            ]
        elif self.active_tab == 2:
            # GRAPHICS
            preset = getattr(SETTINGS, "QUALITY_PRESET", "Otimizado").upper()
            vk = "VULKAN GPU" if getattr(SETTINGS, "VULKAN_ENABLED", False) else "SDL HARDWARE"
            blm = "ATIVADO (HDR)" if SETTINGS.BLOOM_ENABLED else "DESATIVADO"
            crt = "ATIVADO" if SETTINGS.SCANLINES_ENABLED else "DESATIVADO"
            vgt = "ATIVADO" if SETTINGS.VIGNETTE_ENABLED else "DESATIVADO"
            return [
                ("PREDEFINIÇÃO DE QUALIDADE", preset, self._toggle_preset),
                ("MOTOR DE RENDERIZAÇÃO", vk, self._toggle_backend),
                ("BLOOM FÍSICO HDR", blm, self._toggle_bloom),
                ("SCANLINES RETRÔ CRT", crt, self._toggle_scanlines),
                ("VINHETA CINEMATOGRÁFICA", vgt, self._toggle_vignette),
            ]
        else:
            # ACCESSIBILITY
            shk_pct = int(SETTINGS.SCREEN_SHAKE * 100)
            photo = "ATIVADO" if SETTINGS.PHOTOSENSITIVITY_MODE else "DESATIVADO"
            outl = "ATIVADO" if SETTINGS.PLAYER_OUTLINE else "DESATIVADO"
            prof = "ATIVADO [F3]" if PROFILER.enabled else "DESATIVADO [F3]"
            return [
                ("TREMOR DE CÂMERA (SHAKE)", f"{shk_pct}%", self._adjust_shake),
                ("MODO FOTOSSENSIBILIDADE", photo, self._toggle_photo),
                ("DESTAQUE DE CONTORNO", outl, self._toggle_outline),
                ("MONITOR DE DESEMPENHO", prof, self._toggle_profiler),
            ]

    @property
    def tabs(self):
        return self.TABS

    @property
    def options(self):
        """Returns all configurable options across all tabs for diagnostic tests."""
        saved_tab = self.active_tab
        all_opts = []
        for t in range(len(self.TABS)):
            self.active_tab = t
            all_opts.extend(self._get_tab_options())
        self.active_tab = saved_tab
        return all_opts

    # Handlers
    def _adjust_master_vol(self, delta: int):
        SETTINGS.MASTER_VOLUME = max(0.0, min(1.0, round(SETTINGS.MASTER_VOLUME + delta * 0.05, 2)))
        pygame.mixer.music.set_volume(SETTINGS.MUSIC_VOLUME * SETTINGS.MASTER_VOLUME)

    def _adjust_music_vol(self, delta: int):
        SETTINGS.MUSIC_VOLUME = max(0.0, min(1.0, round(SETTINGS.MUSIC_VOLUME + delta * 0.05, 2)))
        pygame.mixer.music.set_volume(SETTINGS.MUSIC_VOLUME * SETTINGS.MASTER_VOLUME)

    def _adjust_sfx_vol(self, delta: int):
        SETTINGS.SFX_VOLUME = max(0.0, min(1.0, round(SETTINGS.SFX_VOLUME + delta * 0.05, 2)))

    def _toggle_res(self, delta: int):
        SETTINGS.RESOLUTION_INDEX = (SETTINGS.RESOLUTION_INDEX + delta) % len(SETTINGS.RESOLUTIONS)
        from engine.game import Game
        if Game.instance:
            Game.instance.apply_display_settings()

    def _toggle_fullscreen(self, delta: int):
        SETTINGS.FULLSCREEN = not SETTINGS.FULLSCREEN
        from engine.game import Game
        if Game.instance:
            Game.instance.apply_display_settings()

    def _toggle_stretch(self, delta: int):
        SETTINGS.FULLSCREEN_STRETCH = not SETTINGS.FULLSCREEN_STRETCH

    def _adjust_brightness(self, delta: int):
        SETTINGS.BRIGHTNESS = max(-0.20, min(0.20, round(SETTINGS.BRIGHTNESS + delta * 0.02, 2)))

    def _adjust_contrast(self, delta: int):
        SETTINGS.CONTRAST = max(0.80, min(1.30, round(SETTINGS.CONTRAST + delta * 0.05, 2)))

    def _toggle_preset(self, delta: int):
        cur = getattr(SETTINGS, "QUALITY_PRESET", "Otimizado")
        SETTINGS.QUALITY_PRESET = "Ultra Neo-Retro" if cur == "Otimizado" else "Otimizado"

    def _toggle_backend(self, delta: int):
        SETTINGS.VULKAN_ENABLED = not getattr(SETTINGS, "VULKAN_ENABLED", False)

    def _toggle_bloom(self, delta: int):
        SETTINGS.BLOOM_ENABLED = not SETTINGS.BLOOM_ENABLED

    def _toggle_scanlines(self, delta: int):
        SETTINGS.SCANLINES_ENABLED = not SETTINGS.SCANLINES_ENABLED

    def _toggle_vignette(self, delta: int):
        SETTINGS.VIGNETTE_ENABLED = not SETTINGS.VIGNETTE_ENABLED

    def _adjust_shake(self, delta: int):
        SETTINGS.SCREEN_SHAKE = max(0.0, min(1.0, round(SETTINGS.SCREEN_SHAKE + delta * 0.1, 1)))

    def _toggle_photo(self, delta: int):
        SETTINGS.PHOTOSENSITIVITY_MODE = not SETTINGS.PHOTOSENSITIVITY_MODE

    def _toggle_outline(self, delta: int):
        SETTINGS.PLAYER_OUTLINE = not SETTINGS.PLAYER_OUTLINE

    def _toggle_profiler(self, delta: int):
        PROFILER.toggle()
        SETTINGS.PROFILER_F3 = PROFILER.enabled

    def _reset_defaults(self):
        """Restores default values."""
        SETTINGS.MASTER_VOLUME = 0.8
        SETTINGS.MUSIC_VOLUME = 0.7
        SETTINGS.SFX_VOLUME = 0.9
        SETTINGS.FULLSCREEN = False
        SETTINGS.BLOOM_ENABLED = True
        SETTINGS.SCANLINES_ENABLED = False
        SETTINGS.VIGNETTE_ENABLED = True
        SETTINGS.SCREEN_SHAKE = 1.0

    def handle_events(self, events: list[pygame.event.Event]):
        opts = self._get_tab_options()
        total_items = len(opts) + 2 # options + 'RESTAURAR PADRÕES' + 'VOLTAR'
        
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.scene_manager.change_scene(self.previous_scene)
                    return
                elif event.key in (pygame.K_q, pygame.K_PAGEUP):
                    self.active_tab = (self.active_tab - 1) % len(self.TABS)
                    self.selected_index = 0
                elif event.key in (pygame.K_e, pygame.K_PAGEDOWN, pygame.K_TAB):
                    self.active_tab = (self.active_tab + 1) % len(self.TABS)
                    self.selected_index = 0
                elif event.key in (pygame.K_w, pygame.K_UP):
                    self.selected_index = (self.selected_index - 1) % total_items
                elif event.key in (pygame.K_s, pygame.K_DOWN):
                    self.selected_index = (self.selected_index + 1) % total_items
                elif event.key in (pygame.K_a, pygame.K_LEFT):
                    if self.selected_index < len(opts):
                        opts[self.selected_index][2](-1)
                    else:
                        # Tab switch with left/right on action buttons
                        self.active_tab = (self.active_tab - 1) % len(self.TABS)
                elif event.key in (pygame.K_d, pygame.K_RIGHT):
                    if self.selected_index < len(opts):
                        opts[self.selected_index][2](1)
                    else:
                        self.active_tab = (self.active_tab + 1) % len(self.TABS)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
                    if self.selected_index < len(opts):
                        opts[self.selected_index][2](1)
                    elif self.selected_index == len(opts):
                        self._reset_defaults()
                    elif self.selected_index == len(opts) + 1:
                        self.scene_manager.change_scene(self.previous_scene)

    def update(self, dt: float):
        self.time_sec += dt
        self.atmosphere.update(dt)

    def draw(self, surface: pygame.Surface):
        cx = self.width // 2
        
        # 1. Atmospheric Cavern Background with Rising Embers (Image 2 style)
        self.atmosphere.draw_background(surface, show_rays=False)
        
        # 2. Section Header Title with Tab Carousel
        tab_name = self.TABS[self.active_tab]
        f_title = HollowFonts.get(20, bold=True)
        title_str = f"‹   {tab_name}   ›"
        t_surf = f_title.render(title_str, True, (248, 248, 255))
        surface.blit(t_surf, t_surf.get_rect(center=(cx, 30)))
        
        # Delicate filigree divider below title
        HollowCrestRenderer.draw_section_divider(surface, cx, 54, width=280)
        
        # 3. Two-Column Options List
        opts = self._get_tab_options()
        f_opt = HollowFonts.get(12)
        f_val = HollowFonts.get(12)
        
        y_start = 74
        row_h = 26
        left_x = 80
        right_x = 560
        
        pulse = 0.85 + 0.15 * math.sin(self.time_sec * 5.0)
        marker_alpha = int(230 * pulse)
        
        for idx, (label, val_str, _) in enumerate(opts):
            is_sel = (idx == self.selected_index)
            cur_y = y_start + idx * row_h
            
            col_lbl = (255, 255, 255) if is_sel else (150, 160, 175)
            col_val = (255, 230, 160) if is_sel else (180, 190, 205)
            
            lbl_surf = f_opt.render(label, True, col_lbl)
            val_surf = f_val.render(val_str, True, col_val)
            
            # Drop shadows for crisp contrast
            surface.blit(f_opt.render(label, True, (0, 0, 0)), (left_x + 1, cur_y + 1))
            surface.blit(lbl_surf, (left_x, cur_y))
            
            surface.blit(f_val.render(val_str, True, (0, 0, 0)), (right_x - val_surf.get_width() + 1, cur_y + 1))
            surface.blit(val_surf, (right_x - val_surf.get_width(), cur_y))
            
            if is_sel:
                # Subtle luminous guideline
                hl_line = pygame.Surface((right_x - left_x + 36, 1), pygame.SRCALPHA)
                hl_line.fill((255, 255, 255, 35))
                surface.blit(hl_line, (left_x - 18, cur_y + 18))
                
                # Selection Markers flanking the entire row
                HollowCrestRenderer.draw_selection_marker(surface, left_x - 18, cur_y + 8, size=5.5, is_right=False, alpha=marker_alpha)
                HollowCrestRenderer.draw_selection_marker(surface, right_x + 18, cur_y + 8, size=5.5, is_right=True, alpha=marker_alpha)

        # 4. Bottom Action Buttons (RESET DEFAULTS, BACK)
        actions = ["RESTAURAR PADRÕES", "VOLTAR"]
        y_act = y_start + len(opts) * row_h + 16
        f_act = HollowFonts.get(12)
        
        for a_idx, act_text in enumerate(actions):
            item_global_idx = len(opts) + a_idx
            is_sel = (item_global_idx == self.selected_index)
            
            cur_y = y_act + a_idx * 22
            col = (255, 255, 255) if is_sel else (130, 140, 155)
            
            act_surf = f_act.render(act_text, True, col)
            ax = cx - act_surf.get_width() // 2
            
            surface.blit(f_act.render(act_text, True, (0, 0, 0)), (ax + 1, cur_y + 1))
            surface.blit(act_surf, (ax, cur_y))
            
            if is_sel:
                HollowCrestRenderer.draw_selection_marker(surface, ax - 16, cur_y + 8, size=5.0, is_right=False, alpha=marker_alpha)
                HollowCrestRenderer.draw_selection_marker(surface, ax + act_surf.get_width() + 16, cur_y + 8, size=5.0, is_right=True, alpha=marker_alpha)

        # 5. Bottom Navigation Bar Hint
        f_hint = HollowFonts.get(9)
        hint_str = "[Q/E] ALTERNAR ABAS   •   [W/S] SELECIONAR   •   [A/D] AJUSTAR VALOR   •   [ESC] VOLTAR"
        h_surf = f_hint.render(hint_str, True, (90, 100, 120))
        surface.blit(h_surf, h_surf.get_rect(center=(cx, self.height - 14)))
