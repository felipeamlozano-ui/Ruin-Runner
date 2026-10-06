"""
Ruin Engine V3.0 — 2D Signed Distance Fields (SDF) & Boolean Operators.
Mathematical primitives and constructive solid geometry (CSG) for procedural shapes.
"""

import math
import numpy as np
from engine.v3.core.jit_backend import jit_compile

@jit_compile(fastmath=True)
def sdf_circle(px: float, py: float, cx: float, cy: float, r: float) -> float:
    return math.hypot(px - cx, py - cy) - r

@jit_compile(fastmath=True)
def sdf_box(px: float, py: float, bx: float, by: float, bw: float, bh: float) -> float:
    cx = bx + bw * 0.5
    cy = by + bh * 0.5
    dx = abs(px - cx) - bw * 0.5
    dy = abs(py - cy) - bh * 0.5
    return math.hypot(max(0.0, dx), max(0.0, dy)) + min(max(dx, dy), 0.0)

@jit_compile(fastmath=True)
def sdf_capsule(px: float, py: float, ax: float, ay: float, bx: float, by: float, r: float) -> float:
    pax = px - ax
    pay = py - ay
    bax = bx - ax
    bay = by - ay
    h = max(0.0, min(1.0, (pax * bax + pay * bay) / (bax * bax + bay * bay + 1e-6)))
    return math.hypot(pax - bax * h, pay - bay * h) - r

@jit_compile(fastmath=True)
def op_union(d1: float, d2: float) -> float:
    return min(d1, d2)

@jit_compile(fastmath=True)
def op_subtract(d1: float, d2: float) -> float:
    return max(d1, -d2)

@jit_compile(fastmath=True)
def op_intersect(d1: float, d2: float) -> float:
    return max(d1, d2)

@jit_compile(fastmath=True)
def op_smooth_union(d1: float, d2: float, k: float = 8.0) -> float:
    h = max(0.0, min(1.0, 0.5 + 0.5 * (d2 - d1) / k))
    return (1.0 - h) * d2 + h * d1 - k * h * (1.0 - h)
