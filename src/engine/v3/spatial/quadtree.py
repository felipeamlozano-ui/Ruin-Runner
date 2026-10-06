"""
Ruin Engine V3.0 — Dynamic QuadTree & Spatial Partitioning.
Accelerates collision queries, light occlusion lookups, and AI entity awareness.
"""

from typing import List, Tuple, Any, Optional

class QuadTree:
    """
    Hierarchical 2D spatial partitioner for high-performance range queries.
    """
    def __init__(self, x: float, y: float, width: float, height: float, max_objects: int = 8, max_depth: int = 5, depth: int = 0):
        self.bounds = (x, y, width, height)
        self.max_objects = max_objects
        self.max_depth = max_depth
        self.depth = depth
        
        # Stored items: list of (item_ref, (rx, ry, rw, rh))
        self.items: List[Tuple[Any, Tuple[float, float, float, float]]] = []
        self.children: Optional[List['QuadTree']] = None

    def _subdivide(self) -> None:
        x, y, w, h = self.bounds
        hw, hh = w / 2.0, h / 2.0
        self.children = [
            QuadTree(x, y, hw, hh, self.max_objects, self.max_depth, self.depth + 1),         # NW
            QuadTree(x + hw, y, hw, hh, self.max_objects, self.max_depth, self.depth + 1),    # NE
            QuadTree(x, y + hh, hw, hh, self.max_objects, self.max_depth, self.depth + 1),    # SW
            QuadTree(x + hw, y + hh, hw, hh, self.max_objects, self.max_depth, self.depth + 1) # SE
        ]

    def _intersects(self, r1: Tuple[float, float, float, float], r2: Tuple[float, float, float, float]) -> bool:
        return not (r1[0] + r1[2] < r2[0] or
                    r1[0] > r2[0] + r2[2] or
                    r1[1] + r1[3] < r2[1] or
                    r1[1] > r2[1] + r2[3])

    def insert(self, item: Any, rect: Tuple[float, float, float, float]) -> bool:
        """Inserts an item and its bounding rectangle into the QuadTree."""
        if not self._intersects(self.bounds, rect):
            return False

        if self.children is not None:
            for child in self.children:
                child.insert(item, rect)
            return True

        self.items.append((item, rect))

        if len(self.items) > self.max_objects and self.depth < self.max_depth:
            if self.children is None:
                self._subdivide()
            # Push existing items down to children
            for it, it_rect in self.items:
                for child in self.children:
                    child.insert(it, it_rect)
            self.items.clear()

        return True

    def query_range(self, query_rect: Tuple[float, float, float, float], results: Optional[set] = None) -> List[Any]:
        """Queries all items whose bounding box intersects query_rect."""
        if results is None:
            results = set()

        if not self._intersects(self.bounds, query_rect):
            return list(results)

        for item, rect in self.items:
            if self._intersects(rect, query_rect):
                results.add(item)

        if self.children is not None:
            for child in self.children:
                child.query_range(query_rect, results)

        return list(results)

    def clear(self) -> None:
        """Resets the QuadTree hierarchy."""
        self.items.clear()
        if self.children is not None:
            for child in self.children:
                child.clear()
            self.children = None


class SpatialChunkCache:
    """
    Grid-based hash cache mapping 2D world coordinates to spatial buckets.
    """
    def __init__(self, cell_size: int = 128):
        self.cell_size = cell_size
        self.grid: dict[Tuple[int, int], list[Any]] = {}

    def get_cell(self, x: float, y: float) -> Tuple[int, int]:
        return int(x // self.cell_size), int(y // self.cell_size)

    def insert(self, item: Any, x: float, y: float) -> None:
        cell = self.get_cell(x, y)
        self.grid.setdefault(cell, []).append(item)

    def query_radius(self, x: float, y: float, radius: float) -> list[Any]:
        min_cx, min_cy = self.get_cell(x - radius, y - radius)
        max_cx, max_cy = self.get_cell(x + radius, y + radius)
        found = []
        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                found.extend(self.grid.get((cx, cy), []))
        return found

    def clear(self) -> None:
        self.grid.clear()
