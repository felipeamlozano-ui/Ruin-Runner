from enum import Enum, auto

# Physics Constants
GRAVITY = 15.0
MAX_FALL_SPEED = 400.0
FRICTION = 0.85
ACCELERATION = 400.0
MAX_SPEED = 150.0
JUMP_FORCE = -400.0

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
