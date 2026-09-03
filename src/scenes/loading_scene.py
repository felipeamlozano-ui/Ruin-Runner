import pygame
from engine.scene_manager import Scene
from config.settings import SETTINGS
from engine.input_manager import INPUT

class LoadingScene(Scene):
    def __init__(self, scene_manager, next_scene, title: str = "CARREGANDO CENÁRIO...", tip: str = "Dica: Use [Shift] para erguer o escudo e bloquear danos!"):
        self.scene_manager = scene_manager
        self.next_scene = next_scene
        self.title = title
        self.tip = tip
        self.timer = 0.0
        self.duration = 1.8 # 1.8 seconds for smooth loading feeling
        
        # Ensure fresh inputs
        INPUT.clear()
        
        # Initialize fonts
        pygame.font.init()
        self.font_title = pygame.font.SysFont("Arial", 26, bold=True)
        self.font_tip = pygame.font.SysFont("Arial", 14, italic=True)
        self.font_percent = pygame.font.SysFont("Courier New", 14, bold=True)
        
    def handle_events(self, events: list[pygame.event.Event]) -> None:
        pass # Discard events during loading
        
    def update(self, dt: float):
        self.timer += dt
        if self.timer >= self.duration:
            INPUT.clear()
            self.scene_manager.change_scene(self.next_scene)
            
    def draw(self, surface: pygame.Surface):
        surface.fill((10, 12, 18)) # Dark aesthetic background
        
        # Draw Title
        title_surf = self.font_title.render(self.title, True, (255, 215, 110))
        title_rect = title_surf.get_rect(center=(SETTINGS.GAME_WIDTH // 2, SETTINGS.GAME_HEIGHT // 2 - 50))
        surface.blit(title_surf, title_rect)
        
        # Draw Progress Bar
        bar_w = 420
        bar_h = 16
        bar_x = (SETTINGS.GAME_WIDTH - bar_w) // 2
        bar_y = SETTINGS.GAME_HEIGHT // 2
        
        # Bar Container
        pygame.draw.rect(surface, (25, 30, 45), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        
        # Bar Fill
        progress = min(1.0, self.timer / self.duration)
        fill_w = int(bar_w * progress)
        if fill_w > 0:
            pygame.draw.rect(surface, (50, 150, 255), (bar_x, bar_y, fill_w, bar_h), border_radius=4)
            pygame.draw.line(surface, (160, 220, 255), (bar_x + 2, bar_y + 1), (bar_x + fill_w - 2, bar_y + 1))
            
        pygame.draw.rect(surface, (90, 110, 150), (bar_x, bar_y, bar_w, bar_h), 1, border_radius=4)
        
        # Percentage Text
        percent_str = f"{int(progress * 100)}%"
        pct_surf = self.font_percent.render(percent_str, True, (240, 240, 255))
        pct_rect = pct_surf.get_rect(center=(SETTINGS.GAME_WIDTH // 2, bar_y + bar_h + 16))
        surface.blit(pct_surf, pct_rect)
        
        # Tip Text
        if self.tip:
            tip_surf = self.font_tip.render(self.tip, True, (180, 190, 210))
            tip_rect = tip_surf.get_rect(center=(SETTINGS.GAME_WIDTH // 2, SETTINGS.GAME_HEIGHT - 40))
            surface.blit(tip_surf, tip_rect)
