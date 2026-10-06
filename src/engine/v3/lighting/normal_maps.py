"""
Ruin Engine V3.0 — 2D Normal Map & Per-Pixel Shading Engine.
Calculates Lambertian Diffuse, Blinn-Phong Specular, Rim Lighting, and Emissive highlights.
Includes procedural Sobel normal map synthesis for legacy sprites without dedicated normal maps.
"""

import math
import numpy as np
import pygame
from typing import Tuple, Optional
from engine.v3.core.jit_backend import jit_compile
from engine.v3.core.profiler import PROFILER

@jit_compile(fastmath=True)
def shade_sprite_pixels_jit(
    diffuse_rgb: np.ndarray,      # shape (H, W, 3), uint8
    normal_rgb: np.ndarray,       # shape (H, W, 3), uint8
    light_dir: np.ndarray,        # shape (3,), float32 normalized (lx, ly, lz)
    light_color: np.ndarray,      # shape (3,), float32 (0-1)
    ambient_color: np.ndarray,    # shape (3,), float32 (0-1)
    specular_power: float,
    rim_strength: float
) -> np.ndarray:
    """
    JIT-accelerated shading kernel computing Lambert, Specular, Rim, and Ambient terms.
    """
    H, W, _ = diffuse_rgb.shape
    out = np.empty((H, W, 3), dtype=np.uint8)

    # Halfway vector with View Vector V=(0, 0, 1)
    hx = light_dir[0]
    hy = light_dir[1]
    hz = light_dir[2] + 1.0
    h_len = math.sqrt(hx * hx + hy * hy + hz * hz)
    if h_len > 1e-6:
        hx /= h_len
        hy /= h_len
        hz /= h_len

    for y in range(H):
        for x in range(W):
            # Unpack normal from [0, 255] to [-1.0, 1.0]
            nx = (normal_rgb[y, x, 0] / 127.5) - 1.0
            ny = (normal_rgb[y, x, 1] / 127.5) - 1.0
            nz = (normal_rgb[y, x, 2] / 127.5) - 1.0

            n_len = math.sqrt(nx * nx + ny * ny + nz * nz)
            if n_len > 1e-6:
                nx /= n_len
                ny /= n_len
                nz /= n_len

            # Lambert Diffuse N . L
            n_dot_l = nx * light_dir[0] + ny * light_dir[1] + nz * light_dir[2]
            diffuse_factor = max(0.0, n_dot_l)

            # Specular N . H
            n_dot_h = max(0.0, nx * hx + ny * hy + nz * hz)
            specular_factor = n_dot_h ** specular_power

            # Rim Light (1 - N . V) with V=(0, 0, 1) -> N . V = nz
            rim_factor = max(0.0, 1.0 - max(0.0, nz)) * rim_strength

            # Combine terms per channel
            for c in range(3):
                base = diffuse_rgb[y, x, c] / 255.0
                ambient = base * ambient_color[c]
                direct = base * light_color[c] * diffuse_factor
                spec = light_color[c] * specular_factor * 0.4
                rim = light_color[c] * rim_factor * 0.3

                final_val = ambient + direct + spec + rim
                clamped = int(min(255.0, max(0.0, final_val * 255.0)))
                out[y, x, c] = clamped

    return out


class NormalMapLighting:
    """
    Shades 2D sprites with simulated depth, normal relief, and specular glints.
    """
    _NORMAL_CACHE: dict[int, pygame.Surface] = {}

    @classmethod
    def generate_procedural_normal_map(cls, sprite: pygame.Surface) -> pygame.Surface:
        """
        Synthesizes a tangent-space normal map from sprite luminance via Sobel convolution.
        Caches result per sprite identity.
        """
        sprite_id = id(sprite)
        if sprite_id in cls._NORMAL_CACHE:
            return cls._NORMAL_CACHE[sprite_id]

        w, h = sprite.get_size()
        arr = pygame.surfarray.array3d(sprite)
        alpha = pygame.surfarray.array_alpha(sprite) if sprite.get_masks()[3] != 0 else np.full((w, h), 255, dtype=np.uint8)

        # Grayscale height approximation
        lum = (0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]) * (alpha / 255.0)

        # Sobel edge detection
        dx = np.zeros_like(lum)
        dy = np.zeros_like(lum)
        dx[1:-1, :] = lum[2:, :] - lum[:-2, :]
        dy[:, 1:-1] = lum[:, 2:] - lum[:, :-2]

        # Normal vector synthesis: N = normalize(-dx, -dy, 1.0)
        scale = 0.08
        nx = -dx * scale
        ny = -dy * scale
        nz = np.ones_like(lum)
        mag = np.sqrt(nx * nx + ny * ny + nz * nz)
        nx /= mag
        ny /= mag
        nz /= mag

        normal_arr = np.empty((w, h, 3), dtype=np.uint8)
        normal_arr[:, :, 0] = ((nx + 1.0) * 127.5).astype(np.uint8)
        normal_arr[:, :, 1] = ((ny + 1.0) * 127.5).astype(np.uint8)
        normal_arr[:, :, 2] = ((nz + 1.0) * 127.5).astype(np.uint8)

        norm_surf = pygame.surfarray.make_surface(normal_arr)
        cls._NORMAL_CACHE[sprite_id] = norm_surf
        return norm_surf

    @classmethod
    def render_shaded_sprite(
        cls,
        sprite: pygame.Surface,
        world_pos: Tuple[float, float],
        light_pos: Tuple[float, float, float],
        normal_map: Optional[pygame.Surface] = None,
        light_color: Tuple[int, int, int] = (255, 230, 180),
        ambient_color: Tuple[int, int, int] = (90, 95, 110)
    ) -> pygame.Surface:
        """
        Produces a shaded sprite surface illuminated by the 3D point light vector.
        """
        if normal_map is None:
            normal_map = cls.generate_procedural_normal_map(sprite)

        sx, sy = world_pos
        lx, ly, lz = light_pos
        dx = lx - sx
        dy = ly - sy
        dz = lz
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)
        if dist < 1e-4:
            dist = 1.0

        light_dir = np.array([dx / dist, dy / dist, dz / dist], dtype=np.float32)
        l_col = np.array([c / 255.0 for c in light_color[:3]], dtype=np.float32)
        a_col = np.array([c / 255.0 for c in ambient_color[:3]], dtype=np.float32)

        diff_arr = np.transpose(pygame.surfarray.array3d(sprite), (1, 0, 2))
        norm_arr = np.transpose(pygame.surfarray.array3d(normal_map), (1, 0, 2))

        shaded = shade_sprite_pixels_jit(diff_arr, norm_arr, light_dir, l_col, a_col, 16.0, 0.5)

        shaded_surf = pygame.surfarray.make_surface(np.transpose(shaded, (1, 0, 2)))
        # Restore alpha
        if sprite.get_masks()[3] != 0:
            alpha = pygame.surfarray.array_alpha(sprite)
            alpha_surf = pygame.surfarray.make_surface(alpha)
            shaded_surf = shaded_surf.convert_alpha()
            pygame.surfarray.pixels_alpha(shaded_surf)[:] = alpha

        PROFILER.record_draw_calls(1)
        return shaded_surf
