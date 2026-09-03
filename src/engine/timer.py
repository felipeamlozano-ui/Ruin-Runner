import pygame

class Timer:
    """Frame-independent timing."""
    
    def __init__(self):
        self.clock = pygame.time.Clock()
        self.dt: float = 0.0
        self.time: float = 0.0
        
    def tick(self, fps: int):
        # Limit frame rate and calculate delta time in seconds
        self.dt = self.clock.tick(fps) / 1000.0
        # Prevent spiral of death on lag spikes (cap dt to 0.1s max)
        self.dt = min(self.dt, 0.1)
        self.time += self.dt
        
    def get_fps(self) -> float:
        return self.clock.get_fps()
