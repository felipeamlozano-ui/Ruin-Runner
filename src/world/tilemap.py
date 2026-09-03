import pygame
from pytmx.util_pygame import load_pygame
import pyscroll
from typing import List

class Tilemap:
    """Wrapper for pytmx and pyscroll integration."""
    def __init__(self, tmx_file: str):
        # Load TMX
        self.tmx_data = load_pygame(tmx_file)
        
        # Create Map Data for pyscroll
        self.map_data = pyscroll.data.TiledMapData(self.tmx_data)
        self.map_layer = pyscroll.orthographic.BufferedRenderer(
            self.map_data, 
            pygame.display.get_surface().get_size(),
            clamp_camera=True
        )
        self.group = pyscroll.PyscrollGroup(map_layer=self.map_layer, default_layer=2)
        
        # Parse collisions
        self.solid_rects: List[pygame.FRect] = []
        self._parse_collisions()
        
    def _parse_collisions(self):
        """Extract collision rects from an object layer named 'collisions'."""
        if 'collisions' in self.tmx_data.layernames:
            layer = self.tmx_data.get_layer_by_name('collisions')
            for obj in layer:
                self.solid_rects.append(pygame.FRect(obj.x, obj.y, obj.width, obj.height))
                
    def get_solid_rects(self) -> List[pygame.FRect]:
        return self.solid_rects
        
    def update_camera(self, camera_rect: pygame.Rect):
        self.group.center(camera_rect.center)
        
    def draw(self, surface: pygame.Surface):
        self.group.draw(surface)
