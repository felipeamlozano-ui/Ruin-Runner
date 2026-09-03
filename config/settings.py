from dataclasses import dataclass, field
from typing import List, Tuple

@dataclass
class Settings:
    # Screen & Resolution Settings
    RESOLUTIONS: List[Tuple[int, int]] = field(default_factory=lambda: [(1280, 720), (1600, 900), (1920, 1080)])
    RESOLUTION_INDEX: int = 0
    WINDOW_WIDTH: int = 1280
    WINDOW_HEIGHT: int = 720
    GAME_WIDTH: int = 512   # Internal render buffer (4:3)
    GAME_HEIGHT: int = 384
    FPS: int = 60
    VSYNC: int = 0
    FULLSCREEN: bool = False
    FULLSCREEN_STRETCH: bool = True  # Fill screen edge-to-edge (no black pillarbox bars)
    
    # Audio Settings
    MASTER_VOLUME: float = 1.0
    MUSIC_VOLUME: float = 1.0
    SFX_VOLUME: float = 1.0
    
    # Advanced Graphics Settings
    ANTIALIASING: bool = True       # Bilinear smoothscale filtering for clean, high-res presentation
    TEXTURE_QUALITY: str = "Alta"   # "Alta", "Média", "Pixel-Art"
    SCANLINES_ENABLED: bool = False # Off by default for sharp crystal-clear visual clarity
    CRT_ENABLED: bool = False
    FOG_ENABLED: bool = True
    RAYTRACING_ENABLED: bool = True # Volumetric light shafts / God Rays
    DYNAMIC_LIGHTS: bool = True     # Point lights on fireballs, portal, and player
    AMBIENT_PARTICLES: bool = True  # Windblown leaves in forest & glowing embers in dungeons
    VIGNETTE_ENABLED: bool = True   # Cinematic border darkening

# Global Settings Instance
SETTINGS = Settings()
