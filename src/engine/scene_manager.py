from typing import Protocol, Optional
import pygame

class Scene(Protocol):
    def handle_events(self, events: list[pygame.event.Event]) -> None:
        ...
    
    def update(self, dt: float) -> None:
        ...
        
    def draw(self, surface: pygame.Surface) -> None:
        ...

class SceneManager:
    """Manages scene transitions and lifecycle."""
    
    def __init__(self):
        self.current_scene: Optional[Scene] = None
        
    def change_scene(self, scene: Scene):
        from engine.input_manager import INPUT
        INPUT.clear()
        self.current_scene = scene
        
    def handle_events(self, events: list[pygame.event.Event]):
        if self.current_scene:
            self.current_scene.handle_events(events)
            
    def update(self, dt: float):
        if self.current_scene:
            self.current_scene.update(dt)
            
    def draw(self, surface: pygame.Surface):
        if self.current_scene:
            self.current_scene.draw(surface)
