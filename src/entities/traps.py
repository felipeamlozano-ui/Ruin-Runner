import pygame

class SpikeTrap:
    def __init__(self, x: float, y: float, width: int = 16, height: int = 16):
        self.rect = pygame.FRect(x, y, width, height)
        self.damage = 5 # Highly punishing floor hazard
        self.damage_cooldown = 0.0
        
    def update(self, player, dt: float = 0.016):
        if self.damage_cooldown > 0:
            self.damage_cooldown -= dt
        if self.damage_cooldown <= 0 and self.rect.colliderect(player.rect):
            player.take_damage(self.damage)
            self.damage_cooldown = 0.5
            
    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        draw_x = self.rect.x - camera_offset.x
        draw_y = self.rect.y - camera_offset.y
        pygame.draw.rect(surface, (255, 50, 50), (draw_x, draw_y, self.rect.width, self.rect.height))
