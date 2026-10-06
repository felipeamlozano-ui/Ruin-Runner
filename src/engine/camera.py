import pygame
import random
from config.settings import SETTINGS
from utils.math_utils import lerp, clamp
from engine.v3.camera.camera_v3 import CameraV3

class Camera(CameraV3):
    """
    Ruin Engine V3.0 Camera implementation.
    Fully backwards-compatible with classic Camera API while providing Look Ahead,
    Trauma Shake, Perlin Noise Rumble, and Dynamic Zoom.
    """
    def __init__(self, width: int, height: int, viewport_w: int = None, viewport_h: int = None):
        vw = viewport_w if viewport_w is not None else SETTINGS.GAME_WIDTH
        vh = viewport_h if viewport_h is not None else SETTINGS.GAME_HEIGHT
        super().__init__(width, height, viewport_w=vw, viewport_h=vh)
        
        # Legacy compatibility attributes
        self.camera_rect = pygame.FRect(0, 0, self.vw, self.vh)
        self.smoothness = 5.0
        self.shake_intensity = 0.0
        self.shake_timer = 0.0
        self.shake_offset = pygame.math.Vector2(0, 0)
        
    def shake(self, intensity: float = 6.0, duration: float = 0.25):
        """Triggers dynamic camera screen shake using trauma model."""
        self.shake_intensity = max(self.shake_intensity, intensity)
        self.shake_timer = max(self.shake_timer, duration)
        self.add_trauma(min(1.0, intensity / 12.0))
        
    def update(self, target: pygame.FRect, dt: float, target_facing: int = 1, target_vx: float = 0.0):
        """Smoothly follow target with Look Ahead, deadzone, and trauma shake."""
        super().update(target, target_facing, target_vx, dt)
        self.camera_rect.x = self.x
        self.camera_rect.y = self.y

    def update_coop(self, p1, p2, dt: float):
        """Smoothly tracks and frames both players in Co-op with dynamic zoom & leash."""
        super().update_coop(p1, p2, dt)
        self.camera_rect.x = self.x
        self.camera_rect.y = self.y

