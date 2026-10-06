"""
Ruin Engine V3.0 — Spline & Bezier Curve Mesh Renderer.
Generates ribbon strips, sword trail geometry, and smooth parametric paths.
"""

import math
import pygame
from typing import List, Tuple

class SplineRenderer:
    """
    Parametric curve generator and ribbon polygon mesh constructor.
    """
    @staticmethod
    def evaluate_cubic_bezier(
        p0: Tuple[float, float],
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        p3: Tuple[float, float],
        t: float
    ) -> Tuple[float, float]:
        """Evaluates a cubic Bezier curve at parameter t in [0.0, 1.0]."""
        u = 1.0 - t
        tt = t * t
        uu = u * u
        uuu = uu * u
        ttt = tt * t

        x = uuu * p0[0] + 3 * uu * t * p1[0] + 3 * u * tt * p2[0] + ttt * p3[0]
        y = uuu * p0[1] + 3 * uu * t * p1[1] + 3 * u * tt * p2[1] + ttt * p3[1]
        return (x, y)

    @staticmethod
    def generate_catmull_rom_spline(
        points: List[Tuple[float, float]],
        subdivisions: int = 8,
        tension: float = 0.5
    ) -> List[Tuple[float, float]]:
        """
        Interpolates a smooth Catmull-Rom spline passing directly through all control points.
        """
        if len(points) < 2:
            return list(points)
        if len(points) == 2:
            return [points[0], points[1]]

        pts = [points[0]] + list(points) + [points[-1]]
        result = []

        for i in range(1, len(pts) - 2):
            p0 = pts[i - 1]
            p1 = pts[i]
            p2 = pts[i + 1]
            p3 = pts[i + 2]

            for s in range(subdivisions):
                t = s / subdivisions
                tt = t * t
                ttt = tt * t

                # Standard Catmull-Rom basis matrix
                q0 = -ttt + 2.0 * tt - t
                q1 = 3.0 * ttt - 5.0 * tt + 2.0
                q2 = -3.0 * ttt + 4.0 * tt + t
                q3 = ttt - tt

                x = 0.5 * (p0[0] * q0 + p1[0] * q1 + p2[0] * q2 + p3[0] * q3)
                y = 0.5 * (p0[1] * q0 + p1[1] * q1 + p2[1] * q2 + p3[1] * q3)
                result.append((x, y))

        result.append(points[-1])
        return result

    @staticmethod
    def build_ribbon_mesh(
        centerline: List[Tuple[float, float]],
        half_width_start: float = 12.0,
        half_width_end: float = 1.0
    ) -> List[Tuple[float, float]]:
        """
        Constructs a triangulated ribbon strip polygon enclosing the centerline curve.
        """
        if len(centerline) < 2:
            return []

        left_edge = []
        right_edge = []
        n = len(centerline)

        for i in range(n):
            p = centerline[i]
            # Normal calculation
            if i == 0:
                dx = centerline[1][0] - p[0]
                dy = centerline[1][1] - p[1]
            elif i == n - 1:
                dx = p[0] - centerline[n - 2][0]
                dy = p[1] - centerline[n - 2][1]
            else:
                dx = centerline[i + 1][0] - centerline[i - 1][0]
                dy = centerline[i + 1][1] - centerline[i - 1][1]

            length = math.hypot(dx, dy)
            if length > 1e-5:
                nx = -dy / length
                ny = dx / length
            else:
                nx, ny = 0.0, 1.0

            ratio = i / max(1, n - 1)
            hw = half_width_start * (1.0 - ratio) + half_width_end * ratio

            left_edge.append((p[0] + nx * hw, p[1] + ny * hw))
            right_edge.append((p[0] - nx * hw, p[1] - ny * hw))

        # Enclosing polygon: left edge forward, right edge backward
        return left_edge + right_edge[::-1]
