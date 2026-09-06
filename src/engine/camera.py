import pygame
import random
from config.settings import SETTINGS
from utils.math_utils import lerp, clamp

class Camera:
    """Advanced camera with smooth follow, deadzone, boundaries, and screen shake."""
    def __init__(self, width: int, height: int, viewport_w: int = None, viewport_h: int = None):
        self.vw = viewport_w if viewport_w is not None else SETTINGS.GAME_WIDTH
        self.vh = viewport_h if viewport_h is not None else SETTINGS.GAME_HEIGHT
        self.camera_rect = pygame.FRect(0, 0, self.vw, self.vh)
        self.map_width = width
        self.map_height = height
        self.smoothness = 5.0
        self.locked = False
        self.shake_intensity = 0.0
        self.shake_timer = 0.0
        self.shake_offset = pygame.math.Vector2(0, 0)
        
    def shake(self, intensity: float = 6.0, duration: float = 0.25):
        """Triggers dynamic camera screen shake."""
        self.shake_intensity = max(self.shake_intensity, intensity)
        self.shake_timer = max(self.shake_timer, duration)
        
    def apply(self, rect: pygame.FRect) -> pygame.FRect:
        """Applies camera offset to an entity's rect."""
        off = self.offset
        return pygame.FRect(rect.x - off.x, rect.y - off.y, rect.width, rect.height)
        
    def update(self, target: pygame.FRect, dt: float):
        """Smoothly follow the target while clamping to map bounds."""
        if self.shake_timer > 0:
            self.shake_timer -= dt
            decay = max(0.0, self.shake_timer)
            self.shake_offset.x = random.uniform(-self.shake_intensity, self.shake_intensity) * decay
            self.shake_offset.y = random.uniform(-self.shake_intensity, self.shake_intensity) * decay
            if self.shake_timer <= 0:
                self.shake_intensity = 0.0
                self.shake_offset = pygame.math.Vector2(0, 0)
        else:
            self.shake_offset = pygame.math.Vector2(0, 0)

        if self.locked:
            return
            
        target_x = target.centerx - self.vw // 2
        target_y = target.centery - self.vh // 2
        
        # Smooth interpolation
        self.camera_rect.x = lerp(self.camera_rect.x, target_x, self.smoothness * dt)
        self.camera_rect.y = lerp(self.camera_rect.y, target_y, self.smoothness * dt)
        
        # Clamp to bounds
        self.camera_rect.x = clamp(self.camera_rect.x, 0, max(0, self.map_width - self.vw))
        self.camera_rect.y = clamp(self.camera_rect.y, 0, max(0, self.map_height - self.vh))
        
    @property
    def offset(self) -> pygame.math.Vector2:
        return pygame.math.Vector2(self.camera_rect.x + self.shake_offset.x, self.camera_rect.y + self.shake_offset.y)
