import pygame

class Checkpoint:
    """Saves player position and level state when triggered."""
    def __init__(self, x: float, y: float):
        self.rect = pygame.FRect(x, y, 32, 64)
        self.active = False
        self.triggered = False
        
    def update(self, player):
        if not self.triggered and self.rect.colliderect(player.rect):
            self.triggered = True
            self.active = True
            # Here we would also save the state to SaveManager
            return True # Indicates checkpoint was just hit
        return False
        
    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        # Checkpoint is invisible, it just triggers when walked over.
        pass
