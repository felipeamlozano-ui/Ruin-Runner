"""
Ruin Engine V3.0 — Cinematic Trail & Ribbon Renderer.
Utilizes circular deques with Catmull-Rom spline interpolation for sword slashes, dashes, and projectiles.
"""

from collections import deque
import math
import time
import pygame
from typing import Tuple, List, Optional
from engine.v3.geometry.spline_renderer import SplineRenderer
from engine.v3.core.profiler import PROFILER
from engine.v3.core.surface_pool import SURFACE_POOL

class TrailNode:
    def __init__(self, x: float, y: float, timestamp: float, width: float = 12.0):
        self.x = x
        self.y = y
        self.timestamp = timestamp
        self.width = width

class TrailRenderer:
    """
    Renders tapered, glowing motion ribbons along entity trajectories.
    """
    def __init__(self, max_length: int = 24, lifetime: float = 0.35, color: Tuple[int, int, int] = (160, 220, 255)):
        self.max_length = max_length
        self.lifetime = lifetime
        self.color = color
        self.nodes: deque[TrailNode] = deque(maxlen=max_length)

    def add_point(self, x: float, y: float, width: float = 14.0) -> None:
        """Pushes a new trajectory point into the circular buffer."""
        now = time.perf_counter()
        self.nodes.appendleft(TrailNode(x, y, now, width))

    def update(self) -> None:
        """Evicts expired nodes based on lifetime."""
        now = time.perf_counter()
        while self.nodes and (now - self.nodes[-1].timestamp > self.lifetime):
            self.nodes.pop()

    def clear(self) -> None:
        self.nodes.clear()

    def render(
        self,
        surface: pygame.Surface,
        camera_offset: pygame.math.Vector2,
        additive: bool = True
    ) -> None:
        """
        Builds a smoothed ribbon strip and renders with head-to-tail alpha falloff.
        """
        if len(self.nodes) < 2:
            return

        now = time.perf_counter()
        cam_x, cam_y = camera_offset.x, camera_offset.y

        raw_points = [(node.x - cam_x, node.y - cam_y) for node in self.nodes]
        smooth_points = SplineRenderer.generate_catmull_rom_spline(raw_points, subdivisions=4)

        if len(smooth_points) < 2:
            return

        mesh = SplineRenderer.build_ribbon_mesh(
            smooth_points,
            half_width_start=self.nodes[0].width * 0.5,
            half_width_end=1.0
        )

        if len(mesh) < 3:
            return

        trail_surf = SURFACE_POOL.acquire(surface.get_width(), surface.get_height(), pygame.SRCALPHA)
        trail_surf.fill((0, 0, 0, 0))

        r, g, b = self.color[:3]
        pts = [(int(px), int(py)) for px, py in mesh]
        pygame.draw.polygon(trail_surf, (r, g, b, 190), pts)

        blend = pygame.BLEND_RGBA_ADD if additive else 0
        surface.blit(trail_surf, (0, 0), special_flags=blend)
        SURFACE_POOL.release(trail_surf)
        PROFILER.record_draw_calls(1)
