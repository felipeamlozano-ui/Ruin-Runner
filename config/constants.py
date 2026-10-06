from enum import Enum, auto

# Physics Constants
# GRAVITY is in px/s² — applied as velocity.y += GRAVITY * dt (frame-rate independent)
# Original: 15.0 per-frame at ~60fps = ~900 px/s². Set to 900 for identical feel,
# but now consistent at any FPS.
GRAVITY = 900.0
MAX_FALL_SPEED = 520.0
FRICTION = 0.85
ACCELERATION = 400.0
MAX_SPEED = 150.0
# JUMP_FORCE is the instant velocity applied on jump.
# Character jump_speed values are around -350 px/s, giving ~0.39s air time at GRAVITY=900.
JUMP_FORCE = -350.0

# Tile Settings
TILE_SIZE = 16

class GameState(Enum):
    MAIN_MENU = auto()
    PLAYING = auto()
    PAUSED = auto()
    GAME_OVER = auto()
    VICTORY = auto()
    LOADING = auto()

class Direction(Enum):
    LEFT = auto()
    RIGHT = auto()
    UP = auto()
    DOWN = auto()
