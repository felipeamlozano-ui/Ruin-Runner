import pygame
import os
import engine.resource_manager as rm
from typing import Dict, List

class Animation:
    """Handles a single sequence of frames."""
    def __init__(self, frames: List[pygame.Surface], fps: int = 15, loop: bool = True):
        self.frames = frames
        self.fps = fps
        self.loop = loop
        self.frame_duration = 1.0 / fps
        self.current_frame = 0
        self.timer = 0.0
        self.finished = False

    def update(self, dt: float):
        if self.finished:
            return
            
        self.timer += dt
        if self.timer >= self.frame_duration:
            self.timer -= self.frame_duration
            self.current_frame += 1
            
            if self.current_frame >= len(self.frames):
                if self.loop:
                    self.current_frame = 0
                else:
                    self.current_frame = len(self.frames) - 1
                    self.finished = True
                    
    def reset(self):
        self.current_frame = 0
        self.timer = 0.0
        self.finished = False
        
    def is_finished(self, *args, **kwargs) -> bool:
        return self.finished
        
    def get_current_frame(self) -> pygame.Surface:
        if not self.frames:
            # Fallback
            surf = pygame.Surface((16, 32))
            surf.fill((255, 0, 255))
            return surf
        return self.frames[self.current_frame]

class AnimationManager:
    """Manages multiple animations and states for an entity."""
    def __init__(self):
        self.animations: Dict[str, Animation] = {}
        self.current_state = ""
        
    def add_animation(self, state_name: str, anim: Animation):
        self.animations[state_name] = anim
        if not self.current_state:
            self.current_state = state_name
            
    def play(self, state_name: str, force_reset: bool = False):
        if self.current_state != state_name or force_reset:
            self.current_state = state_name
            if state_name in self.animations:
                self.animations[state_name].reset()
                
    def update(self, dt: float):
        if self.current_state in self.animations:
            self.animations[self.current_state].update(dt)
            
    def is_finished(self, state_name: str) -> bool:
        if state_name in self.animations:
            return self.animations[state_name].finished
        return False
            
    def get_current_frame(self) -> pygame.Surface:
        if self.current_state in self.animations:
            return self.animations[self.current_state].get_current_frame()
        # Fallback surface
        surf = pygame.Surface((16, 32))
        surf.fill((255, 0, 255))
        return surf

def load_animation_folder(folder_path: str, prefix: str = "", fps: int = 15, loop: bool = True, scale: float = 1.0) -> Animation:
    """Loads all PNGs in a folder matching the prefix sorted alphabetically, and scales them."""
    frames = []
    if os.path.exists(folder_path):
        files = sorted([f for f in os.listdir(folder_path) if f.endswith('.png') and f.startswith(prefix)])
        for f in files:
            full_path = os.path.join(folder_path, f)
            surf = pygame.image.load(full_path).convert_alpha()
            if scale != 1.0:
                new_size = (int(surf.get_width() * scale), int(surf.get_height() * scale))
                surf = pygame.transform.scale(surf, new_size)
            frames.append(surf)
    return Animation(frames, fps, loop)

_SPRITESHEET_CACHE: Dict[str, List[pygame.Surface]] = {}

def load_spritesheet(
    file_path: str,
    frame_width: int,
    frame_height: int,
    fps: int = 15,
    loop: bool = True,
    scale: float = 1.0,
    start_frame: int = 0,
    max_frames: int = 0
) -> Animation:
    """Loads a spritesheet image, splits it into frames, with caching."""
    cache_key = f"{file_path}_{frame_width}_{frame_height}_{scale}_{start_frame}_{max_frames}"
    if cache_key in _SPRITESHEET_CACHE:
        return Animation(_SPRITESHEET_CACHE[cache_key], fps, loop)

    frames = []
    if os.path.exists(file_path):
        sheet = pygame.image.load(file_path).convert_alpha()
        sheet_width, sheet_height = sheet.get_size()
        
        all_raw_frames = []
        for y in range(0, sheet_height, frame_height):
            for x in range(0, sheet_width, frame_width):
                frame_rect = pygame.Rect(x, y, frame_width, frame_height)
                frame_surf = sheet.subsurface(frame_rect).copy()
                
                # Check if frame is non-empty
                if frame_surf.get_bounding_rect().width > 0:
                    if scale != 1.0:
                        new_size = (int(frame_width * scale), int(frame_height * scale))
                        frame_surf = pygame.transform.scale(frame_surf, new_size)
                    all_raw_frames.append(frame_surf)
                    
        # Apply slice if start_frame / max_frames provided
        if start_frame > 0 or max_frames > 0:
            end_idx = start_frame + max_frames if max_frames > 0 else len(all_raw_frames)
            frames = all_raw_frames[start_frame:end_idx]
        else:
            frames = all_raw_frames
            
    _SPRITESHEET_CACHE[cache_key] = frames
    return Animation(frames, fps, loop)
