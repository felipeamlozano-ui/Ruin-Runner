"""
Ruin Runner — Input Action Bindings & Controller Configuration.
Provides default keymaps and button maps for Player 1, Player 2 (same-keyboard co-op),
and Gamepads (Xbox/PlayStation/Generic SDL2 controllers).
"""

import pygame
from enum import Enum, auto
from typing import Dict, List, Union

class InputAction(Enum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    UP = "UP"
    DOWN = "DOWN"
    JUMP = "JUMP"
    ATTACK = "ATTACK"
    SKILL = "SKILL"          # Magic projectile / secondary skill [K]
    SKILL_AOE = "SKILL_AOE"  # AoE Whirlwind / Tempest [E]
    DASH = "DASH"            # Dodge roll / Dash [Q]
    DEFEND = "DEFEND"        # Guard / Shield [Shift]
    ULTIMATE = "ULTIMATE"    # Ultimate skill [R / I]
    INTERACT = "INTERACT"    # Revive teammate / Chest / Lever [F]
    PAUSE = "PAUSE"          # Pause menu [Escape / P]

# Default Player 1 Keyboard Controls (WASD cluster + J/K/E/Q/Shift/R)
P1_DEFAULT_KEYBOARD: Dict[str, List[int]] = {
    InputAction.LEFT.value: [pygame.K_a],
    InputAction.RIGHT.value: [pygame.K_d],
    InputAction.UP.value: [pygame.K_w],
    InputAction.DOWN.value: [pygame.K_s],
    InputAction.JUMP.value: [pygame.K_SPACE, pygame.K_w],
    InputAction.ATTACK.value: [pygame.K_j],
    InputAction.SKILL.value: [pygame.K_k],
    InputAction.SKILL_AOE.value: [pygame.K_e],
    InputAction.DASH.value: [pygame.K_q],
    InputAction.DEFEND.value: [pygame.K_LSHIFT],
    InputAction.ULTIMATE.value: [pygame.K_r, pygame.K_i],
    InputAction.INTERACT.value: [pygame.K_f],
    InputAction.PAUSE.value: [pygame.K_ESCAPE, pygame.K_p],
}

# Default Player 2 Keyboard Controls (Arrow keys + Numpad or Right-hand letters — Zero Key Conflict!)
P2_DEFAULT_KEYBOARD: Dict[str, List[int]] = {
    InputAction.LEFT.value: [pygame.K_LEFT],
    InputAction.RIGHT.value: [pygame.K_RIGHT],
    InputAction.UP.value: [pygame.K_UP],
    InputAction.DOWN.value: [pygame.K_DOWN],
    InputAction.JUMP.value: [pygame.K_UP, pygame.K_KP7, pygame.K_PERIOD],
    InputAction.ATTACK.value: [pygame.K_KP1, pygame.K_m, pygame.K_SLASH],
    InputAction.SKILL.value: [pygame.K_KP2, pygame.K_COMMA, pygame.K_SEMICOLON],
    InputAction.SKILL_AOE.value: [pygame.K_KP4, pygame.K_l, pygame.K_o],
    InputAction.DASH.value: [pygame.K_KP0, pygame.K_k, pygame.K_p],
    InputAction.DEFEND.value: [pygame.K_KP6, pygame.K_RSHIFT, pygame.K_RIGHTBRACKET],
    InputAction.ULTIMATE.value: [pygame.K_KP5, pygame.K_RETURN, pygame.K_u],
    InputAction.INTERACT.value: [pygame.K_KP3, pygame.K_i],
    InputAction.PAUSE.value: [pygame.K_F10],
}

# Standard Gamepad mapping (Xbox / DualShock / Generic standard SDL2)
DEFAULT_GAMEPAD: Dict[str, int] = {
    InputAction.JUMP.value: 0,       # A / Cross
    InputAction.ATTACK.value: 2,     # X / Square
    InputAction.SKILL.value: 3,      # Y / Triangle
    InputAction.DASH.value: 5,       # RB / R1
    InputAction.SKILL_AOE.value: 4,  # LB / L1
    InputAction.ULTIMATE.value: 1,   # B / Circle
    InputAction.DEFEND.value: 9,     # L2 / LT (trigger or button 9)
    InputAction.INTERACT.value: 8,   # Select / Back / R3
    InputAction.PAUSE.value: 7,      # Start / Options
}

# Backwards compatibility dictionaries
KEYBOARD_CONTROLS = {
    'LEFT': [pygame.K_LEFT, pygame.K_a],
    'RIGHT': [pygame.K_RIGHT, pygame.K_d],
    'UP': [pygame.K_UP, pygame.K_w],
    'DOWN': [pygame.K_DOWN, pygame.K_s],
    'JUMP': [pygame.K_SPACE, pygame.K_w, pygame.K_UP],
    'ATTACK': [pygame.K_j, pygame.K_x, pygame.K_z],
    'MAGIC': [pygame.K_k, pygame.K_c],
    'SKILL': [pygame.K_k, pygame.K_c],
    'DASH': [pygame.K_q],
    'SKILL_AOE': [pygame.K_e],
    'ULTIMATE': [pygame.K_r, pygame.K_i],
    'DEFEND': [pygame.K_LSHIFT, pygame.K_RSHIFT],
    'INTERACT': [pygame.K_f],
    'PAUSE': [pygame.K_ESCAPE, pygame.K_p],
}

GAMEPAD_CONTROLS = DEFAULT_GAMEPAD
