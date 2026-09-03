import pygame
import sys
from config.settings import SETTINGS
from engine.timer import Timer
from engine.scene_manager import SceneManager, Scene
from config.colors import BLACK
import engine.resource_manager as rm
from engine.input_manager import INPUT
from entities.player import Player
from scenes.level_scene import LevelScene

class Game:
    """Main Game Engine class."""
    instance = None
    
    def __init__(self):
        Game.instance = self
        pygame.init()
        pygame.mixer.init()
        INPUT.init()
        
        # Initialize Resource Manager
        rm.RESOURCES = rm.ResourceManager("assets")
        
        # Internal pixel-perfect game buffer
        self.game_surface = pygame.Surface((SETTINGS.GAME_WIDTH, SETTINGS.GAME_HEIGHT))
        
        # Pre-calculate scanlines surface
        self.scanlines = pygame.Surface((SETTINGS.GAME_WIDTH, SETTINGS.GAME_HEIGHT), pygame.SRCALPHA)
        for y in range(0, SETTINGS.GAME_HEIGHT, 2):
            pygame.draw.line(self.scanlines, (0, 0, 0, 70), (0, y), (SETTINGS.GAME_WIDTH, y))
            
        self.apply_display_settings()
        
        self.timer = Timer()
        self.scene_manager = SceneManager()
        self.running = True
        
        # Initial Scene
        from scenes.main_menu import MainMenuScene
        self.scene_manager.change_scene(MainMenuScene(self.scene_manager))
        
    def apply_display_settings(self):
        """Applies resolution, fullscreen, and window flags."""
        flags = 0
        if SETTINGS.FULLSCREEN:
            flags |= pygame.FULLSCREEN
        else:
            flags |= pygame.RESIZABLE
            
        cur_res = SETTINGS.RESOLUTIONS[SETTINGS.RESOLUTION_INDEX]
        SETTINGS.WINDOW_WIDTH, SETTINGS.WINDOW_HEIGHT = cur_res
        
        try:
            if SETTINGS.FULLSCREEN:
                self.screen = pygame.display.set_mode((0, 0), flags)
            else:
                self.screen = pygame.display.set_mode(cur_res, flags)
        except Exception as err:
            print(f"Display mode change notice: {err}")
            self.screen = pygame.display.set_mode(cur_res, pygame.RESIZABLE)
            
        pygame.display.set_caption("Ruin Runner")
        
    def run(self):
        """Main game loop."""
        while self.running:
            self._handle_events()
            self._update()
            self._draw()
            
        pygame.quit()
        sys.exit()
        
    def _handle_events(self):
        INPUT.update()
        events = pygame.event.get()
        for event in events:
            INPUT.process_event(event)
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE:
                if not SETTINGS.FULLSCREEN:
                    SETTINGS.WINDOW_WIDTH, SETTINGS.WINDOW_HEIGHT = event.w, event.h
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    SETTINGS.FULLSCREEN = not SETTINGS.FULLSCREEN
                    self.apply_display_settings()
                    
        self.scene_manager.handle_events(events)
        
    def _update(self):
        self.timer.tick(SETTINGS.FPS)
        self.scene_manager.update(self.timer.dt)
        
    def _draw(self):
        # 1. Render active scene onto internal buffer
        self.scene_manager.draw(self.game_surface)
        
        # 2. Post-processing Scanlines if enabled
        if SETTINGS.SCANLINES_ENABLED:
            self.game_surface.blit(self.scanlines, (0, 0))
            
        # 3. Blit to window screen with Anti-Aliasing (Smoothscale)
        sw, sh = self.screen.get_size()
        gw, gh = SETTINGS.GAME_WIDTH, SETTINGS.GAME_HEIGHT
        
        # Edge-to-edge mode: fill the whole screen (no black bars)
        if SETTINGS.FULLSCREEN_STRETCH:
            target_w, target_h = sw, sh
            target_x, target_y = 0, 0
        else:
            # Maintain 4:3 aspect ratio with letterbox/pillarbox bars
            scale_factor = min(sw / gw, sh / gh)
            target_w = int(gw * scale_factor)
            target_h = int(gh * scale_factor)
            target_x = (sw - target_w) // 2
            target_y = (sh - target_h) // 2
        
        if SETTINGS.ANTIALIASING:
            scaled_buf = pygame.transform.smoothscale(self.game_surface, (target_w, target_h))
        else:
            scaled_buf = pygame.transform.scale(self.game_surface, (target_w, target_h))
            
        self.screen.fill((10, 10, 15)) # Clean letterbox background (only visible when not stretching)
        self.screen.blit(scaled_buf, (target_x, target_y))
        
        pygame.display.flip()

