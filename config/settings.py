from dataclasses import dataclass, field
from typing import List, Tuple

@dataclass
class Settings:
    # Screen & Resolution Settings
    RESOLUTIONS: List[Tuple[int, int]] = field(default_factory=lambda: [(1280, 720), (1600, 900), (1920, 1080)])
    RESOLUTION_INDEX: int = 0
    WINDOW_WIDTH: int = 1280
    WINDOW_HEIGHT: int = 720
    GAME_WIDTH: int = 640   # Internal render buffer (16:9 native)
    GAME_HEIGHT: int = 360
    FPS: int = 60
    VSYNC: int = 0
    FULLSCREEN: bool = False
    FULLSCREEN_STRETCH: bool = True  # Fill screen edge-to-edge (no black pillarbox bars)
    
    # Audio Settings
    MASTER_VOLUME: float = 0.8
    MUSIC_VOLUME: float = 0.6
    SFX_VOLUME: float = 0.85
    
    # Display Color & Calibration (Screen Controls)
    BRIGHTNESS: float = 0.0     # -0.20 to +0.20
    CONTRAST: float = 1.0       # 0.80 to 1.30
    
    # Accessibility Settings
    SCREEN_SHAKE: float = 1.0   # 0.0 to 1.0
    PHOTOSENSITIVITY_MODE: bool = False
    PLAYER_OUTLINE: bool = False
    
    # Advanced Graphics Settings
    VULKAN_ENABLED: bool = False    # Native SDL hardware presentation (Vulkan optional in settings)
    GRAPHICS_BACKEND: str = "Software (SDL 60 FPS)" # "Vulkan (GPU)", "Software (SDL 60 FPS)"
    ANTIALIASING: bool = True       # Bilinear smoothscale filtering for clean, high-res presentation
    TEXTURE_QUALITY: str = "Alta"   # "Alta", "Média", "Pixel-Art"
    SCANLINES_ENABLED: bool = False # Off by default for sharp crystal-clear visual clarity
    CRT_ENABLED: bool = False
    FOG_ENABLED: bool = False       # Disabled for legacy performance
    RAYTRACING_ENABLED: bool = False # Volumetric light shafts / God Rays (Disabled)
    DYNAMIC_LIGHTS: bool = False    # Point lights disabled (uses pre-baked ambient lightmaps)
    AMBIENT_PARTICLES: bool = False # Ambient particles disabled
    VIGNETTE_ENABLED: bool = False  # Cinematic border darkening disabled
    
    # Ruin Engine V3.0 Settings
    RUIN_ENGINE_V3: bool = True
    FSR_ENABLED: bool = False       # Temporal upscaler disabled for Vega iGPU
    FSR_PRESET: str = "Desativado"  # "Desativado", "Performance", "Balanced", etc.
    BLOOM_ENABLED: bool = False     # Heavy HDR physical bloom disabled
    SHADOWS_2D: str = "Desativado"  # Polygonal shadows disabled (uses static blob shadows)
    RAY_TRACING_2D: bool = False    # 2D Visibility Polygons disabled
    AA_MODE: str = "Pixel AA (Fast)"# Fast pixel anti-aliasing
    WEATHER_ENABLED: bool = True
    PROFILER_F3: bool = False
    
    # Gameplay & Character Selection
    CURRENT_CHARACTER: str = "shaia"  # "shaia", "lunaria", "ignis", "astra", "shinobi", "samurai", "fighter", "aurelia", "archer", "zephyr", "boran"
    
    # Co-op Settings
    COOP_ENABLED: bool = False
    P2_CHARACTER: str = "lunaria"
    P1_INPUT_DEVICE: str = "keyboard"
    P2_INPUT_DEVICE: str = "keyboard"
    FRIENDLY_FIRE: bool = False
    COOP_RESPAWN_MODE: str = "Revive"
    QUALITY_PRESET: str = "Legacy / Retro Optimized"
    
    # Developer / Debug Mode
    DEV_MODE: bool = False   # True = ao iniciar novo jogo, pula direto para a sala do boss (configurável nos settings)
    DEV_START_BOSS: bool = True  # Sincronizado com DEV_MODE para início direto no Boss

# Global Settings Instance
SETTINGS = Settings()
