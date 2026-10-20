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
    
    # Advanced Graphics Settings (Benchmark Standardized on Vulkan GPU Native)
    VULKAN_ENABLED: bool = True     # Native Vulkan GPU hardware presentation
    GRAPHICS_BACKEND: str = "vulkan" # "vulkan" (padrão definitivo, com fallback direct3d11 / opengl)
    FALLBACK_DRIVERS: List[str] = field(default_factory=lambda: ["direct3d11", "opengl"])
    GRAPHICS_PRESET: str = "high"   # "low", "medium", "high", "ultra"
    ANTIALIASING: bool = True       # Hardware linear filtering in GPU
    TEXTURE_QUALITY: str = "Alta"   # "Alta", "Média", "Pixel-Art"
    SCANLINES_ENABLED: bool = False # Off by default for sharp visual clarity
    CRT_ENABLED: bool = False
    FOG_ENABLED: bool = True        # Atmospheric depth fog
    RAYTRACING_ENABLED: bool = True # Volumetric light shafts / God Rays
    DYNAMIC_LIGHTS: bool = True     # Dynamic point lights on attacks/projectiles
    AMBIENT_PARTICLES: bool = True  # Atmospheric particles active
    AMBIENT_PARTICLES_COUNT: int = 30
    CLOUDS_COUNT: int = 14
    MIST_LAYERS: int = 3
    VIGNETTE_ENABLED: bool = True   # Cinematic border darkening
    GAME_FEEL_REACTIVE: bool = True # Hit-stops, dust, slash arcs, wind sway
    STATIC_AO: bool = True          # Stage ambient occlusion map
    CONTACT_AO: bool = True         # Ground contact occlusion stamps
    FOREGROUND_SILHOUETTE: bool = True # 1.35x foreground parallax layer
    
    # Ruin Engine V3.0 Settings
    RUIN_ENGINE_V3: bool = True
    FSR_ENABLED: bool = False       # Temporal upscaler disabled (native GPU scaling is faster)
    FSR_PRESET: str = "Desativado"  # "Desativado", "Performance", "Balanced", etc.
    BLOOM_ENABLED: bool = True      # Additive bloom pass
    SHADOWS_2D: str = "Blob"        # Soft blob contact shadows
    RAY_TRACING_2D: bool = False
    AA_MODE: str = "Pixel AA (Fast)"
    WEATHER_ENABLED: bool = True
    PROFILER_F3: bool = False
    
    # Gameplay & Character Selection
    CURRENT_CHARACTER: str = "shaia"  # "shaia", "lunaria", "ignis", "astra", "shinobi", "samurai", "fighter", "aurelia", "archer", "zephyr", "boran"
    
    # Co-op & Duel Settings
    COOP_ENABLED: bool = False
    DUEL_MODE: bool = False
    P2_CHARACTER: str = "lunaria"
    P1_INPUT_DEVICE: str = "keyboard"
    P2_INPUT_DEVICE: str = "keyboard"
    FRIENDLY_FIRE: bool = False
    COOP_RESPAWN_MODE: str = "Revive"
    QUALITY_PRESET: str = "High (Cinematográfico)"
    
    # Developer / Debug Mode
    DEV_MODE: bool = False   # True = ao iniciar novo jogo, pula direto para a sala do boss
    DEV_START_BOSS: bool = True

    def apply_graphics_preset(self, preset_key: str):
        """Applies one of the 4 standardized graphics presets: low, medium, high, ultra."""
        preset_key = preset_key.lower().strip()
        if preset_key not in ("low", "medium", "high", "ultra"):
            preset_key = "high"
        self.GRAPHICS_PRESET = preset_key
        
        if preset_key == "low":
            self.CLOUDS_COUNT = 0
            self.MIST_LAYERS = 0
            self.AMBIENT_PARTICLES = False
            self.AMBIENT_PARTICLES_COUNT = 0
            self.RAYTRACING_ENABLED = False
            self.DYNAMIC_LIGHTS = False
            self.BLOOM_ENABLED = False
            self.STATIC_AO = False
            self.CONTACT_AO = False
            self.FOREGROUND_SILHOUETTE = False
            self.VIGNETTE_ENABLED = True
            self.GAME_FEEL_REACTIVE = False
            self.QUALITY_PRESET = "Low (Desempenho Extremo)"
        elif preset_key == "medium":
            self.CLOUDS_COUNT = 8
            self.MIST_LAYERS = 1
            self.AMBIENT_PARTICLES = True
            self.AMBIENT_PARTICLES_COUNT = 15
            self.RAYTRACING_ENABLED = False
            self.DYNAMIC_LIGHTS = False
            self.BLOOM_ENABLED = False
            self.STATIC_AO = True
            self.CONTACT_AO = False
            self.FOREGROUND_SILHOUETTE = True
            self.VIGNETTE_ENABLED = True
            self.GAME_FEEL_REACTIVE = False
            self.QUALITY_PRESET = "Medium (Equilibrado)"
        elif preset_key == "high":
            self.CLOUDS_COUNT = 14
            self.MIST_LAYERS = 3
            self.AMBIENT_PARTICLES = True
            self.AMBIENT_PARTICLES_COUNT = 30
            self.RAYTRACING_ENABLED = True
            self.DYNAMIC_LIGHTS = True
            self.BLOOM_ENABLED = True
            self.STATIC_AO = True
            self.CONTACT_AO = True
            self.FOREGROUND_SILHOUETTE = True
            self.VIGNETTE_ENABLED = True
            self.GAME_FEEL_REACTIVE = True
            self.QUALITY_PRESET = "High (Cinematográfico)"
        elif preset_key == "ultra":
            self.CLOUDS_COUNT = 20
            self.MIST_LAYERS = 3
            self.AMBIENT_PARTICLES = True
            self.AMBIENT_PARTICLES_COUNT = 60
            self.RAYTRACING_ENABLED = True
            self.DYNAMIC_LIGHTS = True
            self.BLOOM_ENABLED = True
            self.STATIC_AO = True
            self.CONTACT_AO = True
            self.FOREGROUND_SILHOUETTE = True
            self.VIGNETTE_ENABLED = True
            self.GAME_FEEL_REACTIVE = True
            self.QUALITY_PRESET = "Ultra (Silksong Max)"

    def save_settings(self, file_path: str = None):
        """Persists configurable settings to disk."""
        import json
        from pathlib import Path
        if file_path is None:
            file_path = Path(__file__).resolve().parent / "game_settings.json"
        data = {
            "GRAPHICS_PRESET": self.GRAPHICS_PRESET,
            "FULLSCREEN": self.FULLSCREEN,
            "FULLSCREEN_STRETCH": self.FULLSCREEN_STRETCH,
            "RESOLUTION_INDEX": self.RESOLUTION_INDEX,
            "MASTER_VOLUME": self.MASTER_VOLUME,
            "MUSIC_VOLUME": self.MUSIC_VOLUME,
            "SFX_VOLUME": self.SFX_VOLUME,
            "BRIGHTNESS": self.BRIGHTNESS,
            "CONTRAST": self.CONTRAST,
            "SCREEN_SHAKE": self.SCREEN_SHAKE,
            "PHOTOSENSITIVITY_MODE": self.PHOTOSENSITIVITY_MODE,
            "PLAYER_OUTLINE": self.PLAYER_OUTLINE,
            "SCANLINES_ENABLED": self.SCANLINES_ENABLED,
            "VIGNETTE_ENABLED": self.VIGNETTE_ENABLED,
            "BLOOM_ENABLED": self.BLOOM_ENABLED,
        }
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def load_settings(self, file_path: str = None):
        """Loads saved settings from disk if available."""
        import json
        from pathlib import Path
        if file_path is None:
            file_path = Path(__file__).resolve().parent / "game_settings.json"
        if not Path(file_path).exists():
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            preset = data.get("GRAPHICS_PRESET", "high")
            self.apply_graphics_preset(preset)
            for k, v in data.items():
                if hasattr(self, k) and k != "GRAPHICS_PRESET":
                    setattr(self, k, v)
        except Exception:
            pass

# Global Settings Instance
SETTINGS = Settings()
SETTINGS.load_settings()

