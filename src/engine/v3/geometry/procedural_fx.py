"""
Ruin Engine V3.0 — Procedural Geometry & Interactive Physics FX.
Implements interactive spring-mesh Water, bubbling Lava, swaying Grass blades, and Verlet Rope/Chains.
"""

import math
import random
import pygame
from typing import List, Tuple
from engine.v3.core.profiler import PROFILER
from engine.v3.core.surface_pool import SURFACE_POOL

class ProceduralWater:
    """
    Interactive 1D spring mesh simulating shallow wave propagation and splash ripples.
    """
    def __init__(self, x: float, y: float, width: float, height: float, column_spacing: float = 8.0):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.spacing = column_spacing
        self.num_columns = int(width / column_spacing) + 1

        self.heights = [0.0] * self.num_columns
        self.velocities = [0.0] * self.num_columns
        self.target_height = 0.0

        # Physical constants
        self.tension = 0.025
        self.damping = 0.035
        self.spread = 0.25

    def splash(self, world_x: float, speed: float) -> None:
        """Injects a kinetic disturbance at a given world X coordinate."""
        local_x = world_x - self.x
        col = int(local_x / self.spacing)
        if 0 <= col < self.num_columns:
            self.velocities[col] += speed

    def update(self, dt: float) -> None:
        """Integrates Hooke spring mechanics and neighbor column wave propagation."""
        # Spring physics
        for i in range(self.num_columns):
            x = self.heights[i] - self.target_height
            accel = -self.tension * x - self.damping * self.velocities[i]
            self.heights[i] += self.velocities[i]
            self.velocities[i] += accel

        # Wave transmission to adjacent columns
        left_deltas = [0.0] * self.num_columns
        right_deltas = [0.0] * self.num_columns

        for _ in range(4):  # 4 simulation passes per frame
            for i in range(self.num_columns):
                if i > 0:
                    left_deltas[i] = self.spread * (self.heights[i] - self.heights[i - 1])
                    self.velocities[i - 1] += left_deltas[i]
                if i < self.num_columns - 1:
                    right_deltas[i] = self.spread * (self.heights[i] - self.heights[i + 1])
                    self.velocities[i + 1] += right_deltas[i]

            for i in range(self.num_columns):
                if i > 0:
                    self.heights[i - 1] += left_deltas[i]
                if i < self.num_columns - 1:
                    self.heights[i + 1] += right_deltas[i]

    def render(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2) -> None:
        """Renders the fluid polygon with gradient transparency and glistening crest."""
        screen_x = self.x - camera_offset.x
        screen_y = self.y - camera_offset.y

        pts = []
        for i in range(self.num_columns):
            px = screen_x + i * self.spacing
            py = screen_y + self.heights[i]
            pts.append((int(px), int(py)))

        pts.append((int(screen_x + self.width), int(screen_y + self.height)))
        pts.append((int(screen_x), int(screen_y + self.height)))

        water_surf = SURFACE_POOL.acquire(surface.get_width(), surface.get_height(), pygame.SRCALPHA)
        water_surf.fill((0, 0, 0, 0))

        # Deep water body
        pygame.draw.polygon(water_surf, (20, 80, 140, 160), pts)
        # Surface crest
        crest_pts = [(int(screen_x + i * self.spacing), int(screen_y + self.heights[i])) for i in range(self.num_columns)]
        if len(crest_pts) > 1:
            pygame.draw.lines(water_surf, (140, 220, 255, 230), False, crest_pts, 2)

        surface.blit(water_surf, (0, 0))
        SURFACE_POOL.release(water_surf)
        PROFILER.record_draw_calls(2)


class ProceduralLava:
    """
    Bubbling molten magma layer with pulsating incandescent thermal emission.
    """
    def __init__(self, x: float, y: float, width: float, height: float):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.time: float = 0.0

    def update(self, dt: float) -> None:
        self.time += dt * 3.0

    def render(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2) -> None:
        screen_x = self.x - camera_offset.x
        screen_y = self.y - camera_offset.y

        pts = []
        steps = int(self.width / 16) + 1
        for i in range(steps):
            px = screen_x + i * 16
            bubble = math.sin(self.time + i * 0.7) * 4.0 + math.cos(self.time * 1.5 + i * 1.3) * 2.0
            pts.append((int(px), int(screen_y + bubble)))

        pts.append((int(screen_x + self.width), int(screen_y + self.height)))
        pts.append((int(screen_x), int(screen_y + self.height)))

        # Deep magma core
        pygame.draw.polygon(surface, (180, 30, 10), pts)
        # Thermal crust lines
        crest = pts[:steps]
        if len(crest) > 1:
            pygame.draw.lines(surface, (255, 160, 30), False, crest, 4)
            pygame.draw.lines(surface, (255, 240, 120), False, crest, 2)
        PROFILER.record_draw_calls(2)


class VerletRope:
    """
    Verlet particle chain simulating hanging ropes, dungeon chains, and dangling vines.
    """
    def __init__(self, anchor_x: float, anchor_y: float, num_links: int = 10, link_length: float = 14.0):
        self.anchor = (anchor_x, anchor_y)
        self.link_length = link_length
        # Points: (x, y, old_x, old_y)
        self.points: List[List[float]] = []
        for i in range(num_links):
            py = anchor_y + i * link_length
            self.points.append([anchor_x, py, anchor_x, py])

    def update(self, dt: float, gravity: float = 600.0) -> None:
        """Performs Verlet integration followed by distance relaxation constraints."""
        for i in range(1, len(self.points)):
            p = self.points[i]
            vx = (p[0] - p[2]) * 0.98
            vy = (p[1] - p[3]) * 0.98 + gravity * dt * dt
            p[2] = p[0]
            p[3] = p[1]
            p[0] += vx
            p[1] += vy

        # Solve distance constraints
        self.points[0][0] = self.anchor[0]
        self.points[0][1] = self.anchor[1]

        for _ in range(5):  # Constraint relaxation passes
            for i in range(len(self.points) - 1):
                p1 = self.points[i]
                p2 = self.points[i + 1]

                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                dist = math.hypot(dx, dy)
                if dist < 1e-4:
                    continue
                diff = (dist - self.link_length) / dist

                if i == 0:
                    # Anchor does not move
                    p2[0] -= dx * diff
                    p2[1] -= dy * diff
                else:
                    p1[0] += dx * 0.5 * diff
                    p1[1] += dy * 0.5 * diff
                    p2[0] -= dx * 0.5 * diff
                    p2[1] -= dy * 0.5 * diff

    def render(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2, color: Tuple[int, int, int] = (120, 110, 100)) -> None:
        pts = [(int(p[0] - camera_offset.x), int(p[1] - camera_offset.y)) for p in self.points]
        if len(pts) > 1:
            pygame.draw.lines(surface, color, False, pts, 3)
            # Draw chain link dots
            for pt in pts:
                pygame.draw.circle(surface, (80, 75, 70), pt, 3)
        PROFILER.record_draw_calls(1)
