import pygame
from pathlib import Path
from typing import Dict, Optional

class ResourceManager:
    """Manages all game assets with caching to prevent reloading."""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        
        # Caches
        self._images: Dict[str, pygame.Surface] = {}
        self._fonts: Dict[str, pygame.font.Font] = {}
        self._sounds: Dict[str, pygame.mixer.Sound] = {}
        
    def get_image(self, name: str, folder: str = "sprites", alpha: bool = True) -> pygame.Surface:
        """Loads and caches an image."""
        path_str = f"{folder}/{name}"
        if path_str not in self._images:
            full_path = self.base_path / folder / name
            try:
                img = pygame.image.load(str(full_path))
                self._images[path_str] = img.convert_alpha() if alpha else img.convert()
            except (pygame.error, FileNotFoundError):
                print(f"Warning: Could not load image {full_path}. Creating fallback surface.")
                fallback = pygame.Surface((32, 32))
                fallback.fill((255, 0, 255)) # Magenta = Missing Texture
                self._images[path_str] = fallback
                
        return self._images[path_str]
        
    def get_font(self, name: str, size: int) -> pygame.font.Font:
        """Loads and caches a font. None name loads default font."""
        font_key = f"{name}_{size}"
        if font_key not in self._fonts:
            try:
                full_path = str(self.base_path / "fonts" / name) if name else None
                self._fonts[font_key] = pygame.font.Font(full_path, size)
            except (pygame.error, FileNotFoundError):
                print(f"Warning: Could not load font {name}. Using default.")
                self._fonts[font_key] = pygame.font.Font(None, size)
                
        return self._fonts[font_key]
        
    def get_sound(self, name: str, folder: str = "audio") -> Optional[pygame.mixer.Sound]:
        """Loads and caches sound effects."""
        path_str = f"{folder}/{name}"
        if path_str not in self._sounds:
            full_path = self.base_path / folder / name
            try:
                self._sounds[path_str] = pygame.mixer.Sound(str(full_path))
            except (pygame.error, FileNotFoundError):
                print(f"Warning: Could not load sound {full_path}.")
                self._sounds[path_str] = None
                
        return self._sounds[path_str]
        
    def play_music(self, name: str, loops: int = -1):
        """Streams music (no caching needed for music stream)."""
        full_path = self.base_path / "audio" / name
        try:
            pygame.mixer.music.load(str(full_path))
            pygame.mixer.music.play(loops)
        except (pygame.error, FileNotFoundError):
            print(f"Warning: Could not load music {full_path}.")

    def clear_cache(self):
        """Clears memory for unused assets (can be called between levels)."""
        self._images.clear()
        self._fonts.clear()
        self._sounds.clear()

# Global Resource Manager (Initialized later in game.py)
RESOURCES = None
