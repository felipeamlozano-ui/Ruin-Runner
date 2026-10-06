"""
Ruin Engine V3.0 — Temporal Super Resolution (TSR) Engine.
Subpixel jitter accumulation with color-clamping ghost reduction and temporal stability.
"""

import numpy as np
import pygame
from typing import Optional, Tuple
from engine.v3.core.jit_backend import jit_compile
from engine.v3.core.profiler import PROFILER

# 8-sample Halton (2, 3) low-discrepancy subpixel jitter sequence
HALTON_JITTER_8: Tuple[Tuple[float, float], ...] = (
    (-0.25, -0.166),
    (0.25, 0.166),
    (-0.375, 0.5),
    (0.125, -0.5),
    (-0.125, -0.333),
    (0.375, 0.333),
    (-0.437, -0.055),
    (0.062, 0.611)
)

@jit_compile(fastmath=True)
def tsr_accumulate_with_color_clamp_jit(
    curr_frame: np.ndarray,      # (H, W, 3) uint8
    history_frame: np.ndarray,   # (H, W, 3) float32
    blend_weight: float = 0.15   # Alpha weight for current frame
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Accumulates temporal frame history while clamping historical colors to local 3x3 AABB
    to completely eliminate disocclusion ghosting.
    """
    H, W, _ = curr_frame.shape
    out_rgb = np.empty_like(curr_frame)
    next_hist = np.empty_like(history_frame)

    for y in range(H):
        y_min = max(0, y - 1)
        y_max = min(H - 1, y + 1)
        for x in range(W):
            x_min = max(0, x - 1)
            x_max = min(W - 1, x + 1)

            for c in range(3):
                # Compute 3x3 min/max bounding box
                box_min = 255.0
                box_max = 0.0
                for sy in range(y_min, y_max + 1):
                    for sx in range(x_min, x_max + 1):
                        val = float(curr_frame[sy, sx, c])
                        if val < box_min: box_min = val
                        if val > box_max: box_max = val

                # Clamp history sample to local neighborhood box
                hist_val = history_frame[y, x, c]
                clamped_hist = max(box_min, min(box_max, hist_val))

                # Temporal exponential moving average
                curr_val = float(curr_frame[y, x, c])
                accum = clamped_hist * (1.0 - blend_weight) + curr_val * blend_weight

                next_hist[y, x, c] = accum
                out_rgb[y, x, c] = int(max(0.0, min(255.0, accum)))

    return out_rgb, next_hist


class TemporalSuperResolution:
    """
    Accumulates subpixel jittered frames across time to eliminate aliasing and resolve subpixel details.
    """
    def __init__(self, width: int, height: int):
        self.w = width
        self.h = height
        self.jitter_index = 0
        self.history_buf: Optional[np.ndarray] = None
        self.enabled: bool = True

    def get_subpixel_jitter(self) -> Tuple[float, float]:
        """Returns the subpixel offset for the current frame camera jitter."""
        if not self.enabled:
            return (0.0, 0.0)
        jitter = HALTON_JITTER_8[self.jitter_index]
        self.jitter_index = (self.jitter_index + 1) % len(HALTON_JITTER_8)
        return jitter

    def resolve(self, current_surface: pygame.Surface) -> pygame.Surface:
        """
        Resolves the current frame with temporal accumulation and ghost reduction.
        """
        if not self.enabled:
            return current_surface

        curr_arr = np.transpose(pygame.surfarray.array3d(current_surface), (1, 0, 2))

        if self.history_buf is None or self.history_buf.shape != curr_arr.shape:
            self.history_buf = curr_arr.astype(np.float32)
            return current_surface

        out_arr, self.history_buf = tsr_accumulate_with_color_clamp_jit(curr_arr, self.history_buf, blend_weight=0.18)
        resolved_surf = pygame.surfarray.make_surface(np.transpose(out_arr, (1, 0, 2)))
        PROFILER.record_draw_calls(1)
        return resolved_surf
