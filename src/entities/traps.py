import pygame

class SpikeTrap:
    def __init__(self, x: float, y: float, width: int = 16, height: int = 16):
        self.rect = pygame.FRect(x, y, width, height)
        self.damage = 1
        
    def update(self, player):
        if self.rect.colliderect(player.rect):
            player.take_damage(self.damage)
            
    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        draw_x = self.rect.x - camera_offset.x
        draw_y = self.rect.y - camera_offset.y
        pygame.draw.rect(surface, (255, 50, 50), (draw_x, draw_y, self.rect.width, self.rect.height))
