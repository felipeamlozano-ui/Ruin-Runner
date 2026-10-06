"""
Ruin Engine V3.0 — Marching Squares 2D Isocontour Engine.
Extracts smooth procedural boundaries and terrain meshes from continuous scalar fields.
"""

import numpy as np
from typing import List, Tuple

class MarchingSquares:
    """
    Extracts geometric contour lines from 2D discrete scalar fields.
    """
    @staticmethod
    def extract_contours(
        field: np.ndarray,
        iso_value: float = 0.5,
        cell_size: float = 16.0
    ) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
        """
        Runs marching squares over a 2D numpy scalar field.
        Returns a list of line segments: [((x1, y1), (x2, y2)), ...].
        """
        rows, cols = field.shape
        segments = []

        for r in range(rows - 1):
            for c in range(cols - 1):
                # 4 cell corners
                # 0: TL, 1: TR, 2: BR, 3: BL
                v0 = field[r, c]
                v1 = field[r, c + 1]
                v2 = field[r + 1, c + 1]
                v3 = field[r + 1, c]

                # Binary configuration index (0 to 15)
                idx = 0
                if v0 >= iso_value: idx |= 8
                if v1 >= iso_value: idx |= 4
                if v2 >= iso_value: idx |= 2
                if v3 >= iso_value: idx |= 1

                if idx in (0, 15):
                    continue

                x = c * cell_size
                y = r * cell_size

                # Edge interpolation points
                # Top edge (between 0 and 1)
                t01 = (iso_value - v0) / (v1 - v0 + 1e-6)
                t01 = max(0.0, min(1.0, t01))
                top = (x + t01 * cell_size, y)

                # Right edge (between 1 and 2)
                t12 = (iso_value - v1) / (v2 - v1 + 1e-6)
                t12 = max(0.0, min(1.0, t12))
                right = (x + cell_size, y + t12 * cell_size)

                # Bottom edge (between 3 and 2)
                t32 = (iso_value - v3) / (v2 - v3 + 1e-6)
                t32 = max(0.0, min(1.0, t32))
                bot = (x + t32 * cell_size, y + cell_size)

                # Left edge (between 0 and 3)
                t03 = (iso_value - v0) / (v3 - v0 + 1e-6)
                t03 = max(0.0, min(1.0, t03))
                left = (x, y + t03 * cell_size)

                # Connect according to lookup
                if idx in (1, 14):
                    segments.append((left, bot))
                elif idx in (2, 13):
                    segments.append((bot, right))
                elif idx in (3, 12):
                    segments.append((left, right))
                elif idx in (4, 11):
                    segments.append((top, right))
                elif idx in (5, 10):
                    segments.append((left, top))
                    segments.append((bot, right))
                elif idx in (6, 9):
                    segments.append((top, bot))
                elif idx in (7, 8):
                    segments.append((left, top))

        return segments
