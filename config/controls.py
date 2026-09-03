import pygame
from typing import Dict, List

# Keyboard mapping
KEYBOARD_CONTROLS: Dict[str, List[int]] = {
    'LEFT': [pygame.K_LEFT, pygame.K_a],
    'RIGHT': [pygame.K_RIGHT, pygame.K_d],
    'UP': [pygame.K_UP, pygame.K_w],
    'DOWN': [pygame.K_DOWN, pygame.K_s],
    'JUMP': [pygame.K_SPACE, pygame.K_w, pygame.K_UP],
    'ATTACK': [pygame.K_j, pygame.K_x, pygame.K_z],
    'MAGIC': [pygame.K_k, pygame.K_c],
    'DASH': [pygame.K_q],
    'SKILL_AOE': [pygame.K_e],
    'ULTIMATE': [pygame.K_r],
    'DEFEND': [pygame.K_LSHIFT, pygame.K_RSHIFT],
    'PAUSE': [pygame.K_ESCAPE, pygame.K_p],
}

GAMEPAD_CONTROLS: Dict[str, int] = {
    'JUMP': 0,      # A / Cross
    'ATTACK': 2,    # X / Square
    'MAGIC': 3,     # Y / Triangle
    'DASH': 5,      # RB / R1
    'SKILL_AOE': 4, # LB / L1
    'ULTIMATE': 1,  # B / Circle
    'DEFEND': 9,    # L2 / LT
    'PAUSE': 7,     # Start / Options
}
