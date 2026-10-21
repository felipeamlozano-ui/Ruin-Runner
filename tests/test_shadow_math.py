"""
Mathematical & Geometric Unit Tests for 2D Shadow Projection (shadows.py)
Validates:
- Collinearity: Cross-product (p_proj - p) x (p - l) == 0 within floating point tolerance
- Multi-quadrant positions: Light ABOVE, BELOW, LEFT, RIGHT
- Vertical edge alignment: |p_x - l_x| < 0.5px
- Near-singularity proximity: dist < 2px and dist < 1e-4
- Convexity & Simple Polygon guarantee (No Bowtie self-intersection)
"""

import math
import os
import sys
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(ROOT_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import pygame
from engine.v3.lighting.shadows import ShadowRenderer


def cross_2d(v1, v2):
    return v1[0] * v2[1] - v1[1] * v2[0]


def segments_intersect(p1, p2, p3, p4):
    """Returns True if open segments (p1, p2) and (p3, p4) strictly intersect."""
    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])
    return (ccw(p1, p3, p4) != ccw(p2, p3, p4)) and (ccw(p1, p2, p3) != ccw(p1, p2, p4))


class TestShadowMath(unittest.TestCase):
    def setUp(self):
        self.renderer = ShadowRenderer(shadow_length=120.0)

    def _verify_collinearity(self, p, p_proj, l):
        """Verifies that p_proj lies on the ray passing from l through p."""
        v_light = (p[0] - l[0], p[1] - l[1])
        v_extrude = (p_proj[0] - p[0], p_proj[1] - p[1])
        # Cross product of parallel vectors must be approximately zero
        cross = cross_2d(v_light, v_extrude)
        self.assertAlmostEqual(cross, 0.0, delta=1e-3,
                               msg=f"Extrusion not collinear: cross={cross}, light={l}, p={p}, p_proj={p_proj}")
        # Dot product must be positive (extruded AWAY from light, not towards it)
        dot = v_light[0] * v_extrude[0] + v_light[1] * v_extrude[1]
        self.assertGreater(dot, -1e-4, msg=f"Shadow projected backwards toward light: dot={dot}")

    def _verify_no_bowtie(self, quad):
        """A quad [p1, p2, p2_proj, p1_proj] must not have crossing opposite edges."""
        p1, p2, p2_proj, p1_proj = quad
        # Check if fin 1 (p1 -> p1_proj) intersects fin 2 (p2 -> p2_proj)
        intersects = segments_intersect(p1, p1_proj, p2, p2_proj)
        self.assertFalse(intersects, "Quad has bowtie self-intersection! Opposite fins cross.")

    def test_light_above(self):
        """Light positioned strictly above the obstacle."""
        lx, ly = 100.0, 50.0
        p1 = (80.0, 100.0)
        p2 = (120.0, 100.0)
        quad = self.renderer.project_shadow_polygon(lx, ly, p1, p2)
        self.assertEqual(len(quad), 4)
        self._verify_collinearity(p1, quad[3], (lx, ly))
        self._verify_collinearity(p2, quad[2], (lx, ly))
        self._verify_no_bowtie(quad)

    def test_light_below(self):
        """Light positioned strictly below the obstacle (p_y < l_y)."""
        lx, ly = 100.0, 200.0
        p1 = (80.0, 120.0)
        p2 = (130.0, 120.0)
        quad = self.renderer.project_shadow_polygon(lx, ly, p1, p2)
        self.assertEqual(len(quad), 4)
        self._verify_collinearity(p1, quad[3], (lx, ly))
        self._verify_collinearity(p2, quad[2], (lx, ly))
        self._verify_no_bowtie(quad)
        # Verify shadows project upward away from light (y decreases)
        self.assertLess(quad[3][1], p1[1], "Shadow for light below should project upward away from light")

    def test_light_left(self):
        """Light positioned to the left of a vertical obstacle edge."""
        lx, ly = 40.0, 150.0
        p1 = (100.0, 120.0)
        p2 = (100.0, 180.0)
        quad = self.renderer.project_shadow_polygon(lx, ly, p1, p2)
        self.assertEqual(len(quad), 4)
        self._verify_collinearity(p1, quad[3], (lx, ly))
        self._verify_collinearity(p2, quad[2], (lx, ly))
        self._verify_no_bowtie(quad)
        # Shadow should project to the right (x increases)
        self.assertGreater(quad[3][0], p1[0])

    def test_light_right(self):
        """Light positioned to the right of a vertical obstacle edge."""
        lx, ly = 200.0, 150.0
        p1 = (100.0, 120.0)
        p2 = (100.0, 180.0)
        quad = self.renderer.project_shadow_polygon(lx, ly, p1, p2)
        self.assertEqual(len(quad), 4)
        self._verify_collinearity(p1, quad[3], (lx, ly))
        self._verify_collinearity(p2, quad[2], (lx, ly))
        self._verify_no_bowtie(quad)
        # Shadow should project to the left (x decreases)
        self.assertLess(quad[3][0], p1[0])

    def test_nearly_vertically_aligned_edge(self):
        """Light positioned with |p_x - l_x| < 0.5px relative to vertex."""
        lx, ly = 100.2, 50.0
        p1 = (100.0, 120.0)  # |dx| = 0.2 < 0.5px
        p2 = (150.0, 120.0)
        quad = self.renderer.project_shadow_polygon(lx, ly, p1, p2)
        self.assertEqual(len(quad), 4)
        self._verify_collinearity(p1, quad[3], (lx, ly))
        self._verify_collinearity(p2, quad[2], (lx, ly))
        self._verify_no_bowtie(quad)

    def test_very_close_to_obstacle(self):
        """Light positioned very close to obstacle (dist < 2px)."""
        lx, ly = 99.0, 99.0
        p1 = (100.0, 100.0)  # dist = sqrt(2) approx 1.41px < 2px
        p2 = (140.0, 100.0)
        quad = self.renderer.project_shadow_polygon(lx, ly, p1, p2)
        self.assertEqual(len(quad), 4)
        self._verify_collinearity(p1, quad[3], (lx, ly))
        self._verify_collinearity(p2, quad[2], (lx, ly))
        self._verify_no_bowtie(quad)

    def test_exact_coincidence_singularity(self):
        """Light exactly coinciding with vertex (dist == 0 < 1e-4)."""
        lx, ly = 100.0, 100.0
        p1 = (100.0, 100.0)
        p2 = (140.0, 100.0)
        # Must not crash or raise ZeroDivisionError
        quad = self.renderer.project_shadow_polygon(lx, ly, p1, p2)
        self.assertEqual(len(quad), 4)
        self.assertEqual(quad[0], p1)
        self.assertEqual(quad[1], p2)


if __name__ == "__main__":
    unittest.main()
