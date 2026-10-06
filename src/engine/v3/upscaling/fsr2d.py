"""
Ruin Engine V3.0 — FidelityFX Super Resolution 2D (FSR 2D) & Ruin Temporal Reconstruction.
Rebuilt to use the RuinTemporalUpscaler with motion vectors, subpixel jitter,
variance clipping, and contrast-adaptive sharpening (RCAS).
"""

import pygame
from typing import Dict
from engine.v3.upscaling.ruin_upscaler import RuinTemporalUpscaler, TSR_PRESETS

FSR_PRESETS: Dict[str, float] = TSR_PRESETS

class FSR2D:
    """
    State-of-the-art Super Resolution engine combining Temporal Super Resolution (TSR)
    and Robust Contrast-Adaptive Sharpening (RCAS).
    """
    def __init__(self, target_width: int, target_height: int, preset: str = "Balanced"):
        self.tw = target_width
        self.th = target_height
        self.preset = preset
        self.upscaler = RuinTemporalUpscaler(target_width, target_height, preset=preset)
        self.scale_factor = self.upscaler.scale_factor
        self.vw = self.upscaler.internal_w
        self.vh = self.upscaler.internal_h
        self.enabled: bool = True
        self.sharpness: float = 0.32

    def set_preset(self, preset_name: str) -> None:
        self.preset = preset_name
        self.upscaler.set_preset(preset_name)
        self.scale_factor = self.upscaler.scale_factor
        self.vw = self.upscaler.internal_w
        self.vh = self.upscaler.internal_h

    def get_camera_subpixel_jitter(self):
        return self.upscaler.get_camera_subpixel_jitter()

    def mark_reactive_rect(self, rect: pygame.FRect, intensity: int = 255):
        self.upscaler.mark_reactive_rect(rect, intensity)

    def upscale(self, low_res_surface: pygame.Surface, cam_x: float = 0.0, cam_y: float = 0.0) -> pygame.Surface:
        if not self.enabled:
            if low_res_surface.get_size() != (self.tw, self.th):
                return pygame.transform.scale(low_res_surface, (self.tw, self.th))
            return low_res_surface

        self.upscaler.tw = self.tw
        self.upscaler.th = self.th
        self.upscaler.sharpness = self.sharpness
        return self.upscaler.upscale(low_res_surface, cam_x=cam_x, cam_y=cam_y)
