import pygame
from engine.scene_manager import Scene
from config.settings import SETTINGS
from engine.input_manager import INPUT
from ui.hollow_ui import AtmosphereFX, HollowFonts, HollowCrestRenderer, HollowColors

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
        
        # Atmospheric VFX
        self.fx = AtmosphereFX(width=SETTINGS.GAME_WIDTH, height=SETTINGS.GAME_HEIGHT, theme="void", particle_count=30)
        
        # Initialize fonts
        self.font_title = HollowFonts.get(18, bold=True)
        self.font_tip = HollowFonts.get(11, italic=True)
        self.font_percent = HollowFonts.get(10, bold=True)
        
    def handle_events(self, events: list[pygame.event.Event]) -> None:
        pass # Discard events during loading
        
    def update(self, dt: float):
        self.timer += dt
        self.fx.update(dt)
        if self.timer >= self.duration:
            INPUT.clear()
            self.scene_manager.change_scene(self.next_scene)
            
    def draw(self, surface: pygame.Surface):
        gw, gh = surface.get_width(), surface.get_height()
        cx, cy = gw // 2, gh // 2
        
        # 1. Void Atmosphere
        self.fx.draw_background(surface)
        
        # 2. Title with Top Flourish
        HollowCrestRenderer.draw_top_flourish(surface, cx, cy - 75, width=120, alpha=210)
        
        title_surf = self.font_title.render(self.title, True, HollowColors.TEXT_TITLE)
        title_rect = title_surf.get_rect(center=(cx, cy - 46))
        surface.blit(title_surf, title_rect)
        
        HollowCrestRenderer.draw_section_divider(surface, cx, cy - 28, width=380, alpha=180)
        
        # 3. Delicate Filigree Progress Bar
        bar_w = 360
        bar_h = 10
        bar_x = cx - bar_w // 2
        bar_y = cy
        
        # Grooved Background
        bar_rect = pygame.Rect(bar_x, bar_y, bar_w, bar_h)
        HollowCrestRenderer.draw_filigree_panel(surface, bar_rect, bg_color=(10, 12, 18, 240), border_color=(60, 68, 85), corner_flourish=False)
        
        # Progress Fill
        progress = min(1.0, self.timer / self.duration)
        fill_w = int((bar_w - 4) * progress)
        if fill_w > 0:
            fill_rect = pygame.Rect(bar_x + 2, bar_y + 2, fill_w, bar_h - 4)
            pygame.draw.rect(surface, HollowColors.SILVER_CREST, fill_rect)
            pygame.draw.line(surface, (255, 255, 255), (bar_x + 2, bar_y + 2), (bar_x + 2 + fill_w, bar_y + 2), 1)
            
        # Percentage Text
        percent_str = f"{int(progress * 100)}%"
        pct_surf = self.font_percent.render(percent_str, True, HollowColors.TEXT_MUTED)
        pct_rect = pct_surf.get_rect(center=(cx, bar_y + bar_h + 16))
        surface.blit(pct_surf, pct_rect)
        
        # Tip Text
        if self.tip:
            tip_surf = self.font_tip.render(f"‹ {self.tip} ›", True, HollowColors.TEXT_NORMAL)
            tip_rect = tip_surf.get_rect(center=(cx, gh - 35))
            surface.blit(tip_surf, tip_rect)

