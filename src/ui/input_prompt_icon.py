"""
Ruin Engine — Input Prompt Icon System.
Renders authentic pixel-art keyboard and mouse prompt icons from craftpix-net-726651.
Dynamically resolves bindings from InputManager/InputMap with real-time button click feedback.
"""

import os
import pygame
from typing import Dict, Tuple, Optional, Union
from engine.input_manager import INPUT
from config.controls import (
    InputAction,
    P1_DEFAULT_KEYBOARD,
    P2_DEFAULT_KEYBOARD
)

_ICON_SURF_CACHE: Dict[Tuple[str, str, int], Tuple[pygame.Surface, pygame.Surface]] = {}
_BLANK_SHEET: Optional[pygame.Surface] = None
_MOUSE_SHEET: Optional[pygame.Surface] = None
_FONT_KEY: Optional[pygame.font.Font] = None


def _init_icon_assets():
    global _BLANK_SHEET, _MOUSE_SHEET, _FONT_KEY
    if _BLANK_SHEET is not None:
        return

    pygame.font.init()
    try:
        _FONT_KEY = pygame.font.SysFont("Arial", 8, bold=True)
    except Exception:
        _FONT_KEY = pygame.font.Font(None, 12)

    kb_blank_path = os.path.join("assets", "sprites", "tutorial_kb", "PNG", "Kb_blank_buttons_animation_white.png")
    if os.path.exists(kb_blank_path):
        raw_b = pygame.image.load(kb_blank_path)
        disp = pygame.display.get_surface()
        _BLANK_SHEET = raw_b.convert_alpha() if disp else raw_b
    else:
        _BLANK_SHEET = None

    mouse_path = os.path.join("assets", "sprites", "tutorial_kb", "PNG", "Mouse_base.png")
    if os.path.exists(mouse_path):
        raw_m = pygame.image.load(mouse_path)
        disp = pygame.display.get_surface()
        _MOUSE_SHEET = raw_m.convert_alpha() if disp else raw_m
    else:
        _MOUSE_SHEET = None


def _get_key_label_from_code(key_code: int) -> str:
    """Translates pygame keycode into compact badge label."""
    key_map = {
        pygame.K_SPACE: "SP",
        pygame.K_LSHIFT: "SH",
        pygame.K_RSHIFT: "SH",
        pygame.K_RETURN: "RET",
        pygame.K_ESCAPE: "ESC",
        pygame.K_TAB: "TAB",
        pygame.K_UP: "^",
        pygame.K_DOWN: "v",
        pygame.K_LEFT: "<",
        pygame.K_RIGHT: ">",
        pygame.K_KP0: "N0",
        pygame.K_KP1: "N1",
        pygame.K_KP2: "N2",
        pygame.K_KP3: "N3",
        pygame.K_KP4: "N4",
        pygame.K_KP5: "N5",
        pygame.K_KP6: "N6",
        pygame.K_KP7: "N7",
        pygame.K_KP8: "N8",
        pygame.K_KP9: "N9",
    }
    if key_code in key_map:
        return key_map[key_code]
    name = pygame.key.name(key_code).upper()
    if len(name) > 3:
        return name[:3]
    return name


class InputPromptIcon:
    """Reusable dynamic input icon that reflects active key/mouse bindings and live press states."""

    def __init__(self, action: Union[str, InputAction], player_index: int = 0, size: int = 16):
        _init_icon_assets()
        if isinstance(action, InputAction):
            self.action = action.value
        else:
            self.action = str(action).upper()
            
        self.player_index = player_index
        self.size = size
        self.label = ""
        self.is_mouse = False
        self.mouse_button = 1 # 1: LMB, 3: RMB
        
        self.normal_surf, self.pressed_surf = self._resolve_and_bake()

    def _resolve_and_bake(self) -> Tuple[pygame.Surface, pygame.Surface]:
        # 1. Query Player Input bindings
        player_ctrl = INPUT.get_player(self.player_index)
        bound_keys = []
        if player_ctrl and hasattr(player_ctrl, "key_bindings"):
            bound_keys = player_ctrl.key_bindings.get(self.action, [])
            
        if not bound_keys:
            default_map = P2_DEFAULT_KEYBOARD if self.player_index == 1 else P1_DEFAULT_KEYBOARD
            bound_keys = default_map.get(self.action, [])

        primary_key = bound_keys[0] if bound_keys else None
        
        # Check mouse binding conventions
        if self.action in ("MOUSE_LEFT", "LMB"):
            self.is_mouse = True
            self.mouse_button = 1
        elif self.action in ("MOUSE_RIGHT", "RMB"):
            self.is_mouse = True
            self.mouse_button = 3
        elif primary_key is not None:
            self.label = _get_key_label_from_code(primary_key)
        else:
            self.label = self.action[:2]

        cache_key = ("mouse" if self.is_mouse else "key", self.label, self.size)
        if cache_key in _ICON_SURF_CACHE:
            return _ICON_SURF_CACHE[cache_key]

        if self.is_mouse:
            normal, pressed = self._build_mouse_icon()
        else:
            normal, pressed = self._build_key_icon(self.label)

        _ICON_SURF_CACHE[cache_key] = (normal, pressed)
        return normal, pressed

    def _build_key_icon(self, label: str) -> Tuple[pygame.Surface, pygame.Surface]:
        w, h = self.size, self.size
        if _BLANK_SHEET:
            raw_n = _BLANK_SHEET.subsurface((0, 0, 16, 16))
            raw_p = _BLANK_SHEET.subsurface((0, 16, 16, 16))
            surf_n = pygame.transform.scale(raw_n, (w, h)).copy()
            surf_p = pygame.transform.scale(raw_p, (w, h)).copy()
        else:
            surf_n = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(surf_n, (230, 235, 245), (0, 0, w, h), border_radius=2)
            pygame.draw.rect(surf_n, (130, 140, 160), (0, 0, w, h), width=1, border_radius=2)
            
            surf_p = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(surf_p, (180, 190, 205), (0, 1, w, h - 1), border_radius=2)
            pygame.draw.rect(surf_p, (90, 100, 120), (0, 1, w, h - 1), width=1, border_radius=2)

        if _FONT_KEY:
            txt_n = _FONT_KEY.render(label, True, (35, 40, 50))
            surf_n.blit(txt_n, txt_n.get_rect(center=(w // 2, h // 2 - 1)))
            
            txt_p = _FONT_KEY.render(label, True, (15, 20, 30))
            surf_p.blit(txt_p, txt_p.get_rect(center=(w // 2, h // 2)))

        return surf_n, surf_p

    def _build_mouse_icon(self) -> Tuple[pygame.Surface, pygame.Surface]:
        w, h = self.size, int(self.size * 1.15)
        if _MOUSE_SHEET:
            sub_n = _MOUSE_SHEET.subsurface((0, 0, 64, 64))
            sub_p = _MOUSE_SHEET.subsurface((128, 192, 64, 64)) if self.mouse_button == 1 else _MOUSE_SHEET.subsurface((192, 128, 64, 64))
            surf_n = pygame.transform.smoothscale(sub_n, (w, h))
            surf_p = pygame.transform.smoothscale(sub_p, (w, h))
        else:
            surf_n = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.ellipse(surf_n, (230, 235, 245), (0, 0, w, h))
            surf_p = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.ellipse(surf_p, (255, 120, 60), (0, 0, w, h))

        return surf_n, surf_p

    def is_pressed(self) -> bool:
        """Checks real-time if the corresponding action or mouse button is held down."""
        if self.is_mouse:
            buttons = pygame.mouse.get_pressed()
            btn_idx = 0 if self.mouse_button == 1 else 2
            return bool(buttons[btn_idx]) if btn_idx < len(buttons) else False

        player_ctrl = INPUT.get_player(self.player_index)
        if player_ctrl:
            return player_ctrl.is_action_pressed(self.action)
        return False

    def draw(self, surface: pygame.Surface, x: int, y: int):
        """Draws unpressed or depressed prompt sprite with real-time click feedback."""
        if self.is_pressed():
            surface.blit(self.pressed_surf, (x, y + 1))
        else:
            surface.blit(self.normal_surf, (x, y))

    def get_width(self) -> int:
        return self.normal_surf.get_width()

    def get_height(self) -> int:
        return self.normal_surf.get_height()
