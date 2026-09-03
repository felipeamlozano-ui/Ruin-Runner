import pygame
from typing import List, Tuple

class AABB:
    """Axis-Aligned Bounding Box for physics and collisions."""
    def __init__(self, x: float, y: float, w: float, h: float):
        self.rect = pygame.FRect(x, y, w, h)
        
    def move(self, dx: float, dy: float):
        self.rect.x += dx
        self.rect.y += dy
        
    def collides_with(self, other: 'AABB') -> bool:
        return self.rect.colliderect(other.rect)

def resolve_collision_x(entity_rect: pygame.FRect, tiles: List[pygame.FRect], velocity_x: float) -> Tuple[float, bool]:
    """Resolves collision on the X axis. Returns new X and if collision occurred."""
    collision = False
    for tile in tiles:
        if entity_rect.colliderect(tile):
            if velocity_x > 0: # Moving right
                entity_rect.right = tile.left
            elif velocity_x < 0: # Moving left
                entity_rect.left = tile.right
            collision = True
            break
    return entity_rect.x, collision

def resolve_collision_y(entity_rect: pygame.FRect, tiles: List[pygame.FRect], velocity_y: float) -> Tuple[float, bool, bool]:
    """Resolves collision on the Y axis. Returns new Y, on_ground, and hit_ceiling."""
    on_ground = False
    hit_ceiling = False
    
    for tile in tiles:
        if entity_rect.colliderect(tile):
            if velocity_y > 0: # Falling
                entity_rect.bottom = tile.top
                on_ground = True
            elif velocity_y < 0: # Jumping
                entity_rect.top = tile.bottom
                hit_ceiling = True
            break
            
    return entity_rect.y, on_ground, hit_ceiling
