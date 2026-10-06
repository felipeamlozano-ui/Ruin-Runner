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

# Ruin Engine V3.0 Integration
from engine.v3.core.pipeline import MasterRenderPipeline
from engine.v3.core.profiler import PROFILER
from engine.v3.core.adaptive_quality import ADAPTIVE_QUALITY
from engine.v3.upscaling.fsr2d import FSR2D
from engine.v3.upscaling.antialiasing import AntiAliasingEngine
from engine.v3.postfx.bloom import BloomEngine
from engine.vulkan_backend import VulkanRenderBackend

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
        
        # Low-level Vulkan Render Backend
        self.vulkan_backend = VulkanRenderBackend()
        
        # Internal pixel-perfect game buffer
        self._base_size = (SETTINGS.GAME_WIDTH, SETTINGS.GAME_HEIGHT)
        self.game_surface = pygame.Surface(self._base_size)
        
        # Pre-calculate scanlines surface
        self.scanlines = self._build_scanlines(self._base_size)
            
        self.apply_display_settings()
        
        # Ruin Engine V3.0 Subsystems
        self.pipeline = MasterRenderPipeline(
            internal_w=SETTINGS.GAME_WIDTH,
            internal_h=SETTINGS.GAME_HEIGHT,
            window_w=SETTINGS.WINDOW_WIDTH,
            window_h=SETTINGS.WINDOW_HEIGHT
        )
        self.fsr_engine = FSR2D(SETTINGS.WINDOW_WIDTH, SETTINGS.WINDOW_HEIGHT, preset=SETTINGS.FSR_PRESET)
        self.aa_engine = AntiAliasingEngine(mode=SETTINGS.AA_MODE)
        self.bloom_engine = BloomEngine(SETTINGS.GAME_WIDTH, SETTINGS.GAME_HEIGHT)
        
        self.timer = Timer()
        self.scene_manager = SceneManager()
        self.running = True
        
        # Initial Scene — Sempre inicializa no Menu Principal
        from scenes.main_menu import MainMenuScene
        self.scene_manager.change_scene(MainMenuScene(self.scene_manager))
        
    @staticmethod
    def _build_scanlines(size):
        surf = pygame.Surface(size, pygame.SRCALPHA)
        for y in range(0, size[1], 2):
            pygame.draw.line(surf, (0, 0, 0, 70), (0, y), (size[0], y))
        return surf

    def _sync_internal_resolution(self):
        """Scenes may declare `internal_size` to render natively at a higher resolution."""
        scene = self.scene_manager.current_scene
        want = getattr(scene, "internal_size", None) or self._base_size
        if self.game_surface.get_size() != want:
            self.game_surface = pygame.Surface(want)
            self.scanlines = self._build_scanlines(want)

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
            
        if hasattr(self, "fsr_engine"):
            self.fsr_engine.tw = SETTINGS.WINDOW_WIDTH
            self.fsr_engine.th = SETTINGS.WINDOW_HEIGHT
            self.fsr_engine.set_preset(SETTINGS.FSR_PRESET)
            
        if hasattr(self, "pipeline"):
            self.pipeline.window_w = SETTINGS.WINDOW_WIDTH
            self.pipeline.window_h = SETTINGS.WINDOW_HEIGHT

        # Initialize or resize Vulkan hardware rendering context
        if hasattr(self, "vulkan_backend"):
            if getattr(SETTINGS, "VULKAN_ENABLED", False):
                self.vulkan_backend.initialize(self.screen.get_size())
            else:
                self.vulkan_backend.available = False

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
                    if hasattr(self, "vulkan_backend"):
                        self.vulkan_backend.resize(event.w, event.h)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    SETTINGS.FULLSCREEN = not SETTINGS.FULLSCREEN
                    self.apply_display_settings()
                elif event.key == pygame.K_F3:
                    PROFILER.toggle()
                    SETTINGS.PROFILER_F3 = PROFILER.enabled
                    
        self.scene_manager.handle_events(events)
        
    def _update(self):
        self.timer.tick(SETTINGS.FPS)
        self.scene_manager.update(self.timer.dt)
        
    def _draw(self):
        PROFILER.begin_frame()

        # 1. Render active scene onto internal buffer
        self._sync_internal_resolution()
        self.scene_manager.draw(self.game_surface)
        
        # 2. Post-processing Scanlines if enabled
        if SETTINGS.SCANLINES_ENABLED:
            self.game_surface.blit(self.scanlines, (0, 0))
            
        # 3. Viewport calculation for 4:3 letterbox or edge-to-edge
        sw, sh = self.screen.get_size()
        gw, gh = self.game_surface.get_size()
        
        # Edge-to-edge mode: fill the whole screen (no black bars)
        if SETTINGS.FULLSCREEN_STRETCH:
            target_w, target_h = sw, sh
            target_x, target_y = 0, 0
        else:
            # Maintain aspect ratio with letterbox/pillarbox bars
            scale_factor = min(sw / gw, sh / gh)
            target_w = int(gw * scale_factor)
            target_h = int(gh * scale_factor)
            target_x = (sw - target_w) // 2
            target_y = (sh - target_h) // 2
        
        # 4. Low-Level GPU Hardware Presentation (Vulkan via wgpu)
        vulkan_rendered = False
        if getattr(SETTINGS, "VULKAN_ENABLED", False) and getattr(self, "vulkan_backend", None) and self.vulkan_backend.available:
            if PROFILER.enabled:
                PROFILER.render_overlay(self.game_surface)
            vulkan_rendered = self.vulkan_backend.render_frame(
                self.game_surface,
                (target_x, target_y, target_w, target_h),
                scanlines=getattr(SETTINGS, "SCANLINES_ENABLED", False),
                vignette=SETTINGS.VIGNETTE_ENABLED,
                time_sec=self.timer.time
            )

        # 5. High-Performance Hardware/C Presentation Pipeline (Zero-Lag 60 FPS)
        if not vulkan_rendered:
            src = self.game_surface
            if SETTINGS.ANTIALIASING or (SETTINGS.RUIN_ENGINE_V3 and SETTINGS.AA_MODE != "Off"):
                # Crisp integer pre-scale keeps pixel-art edges sharp before the smooth fractional resize (Dead Cells standard)
                if getattr(SETTINGS, "CRISP_UPSCALE", True) and target_w >= 2 * gw:
                    f = target_w // gw
                    src = pygame.transform.scale(self.game_surface, (gw * f, gh * f))
                scaled_buf = pygame.transform.smoothscale(src, (target_w, target_h))
            else:
                scaled_buf = pygame.transform.scale(self.game_surface, (target_w, target_h))
                
            self.screen.fill((10, 10, 15)) # Clean letterbox background
            self.screen.blit(scaled_buf, (target_x, target_y))
            PROFILER.render_overlay(self.screen)
            pygame.display.flip()

        # 6. Adaptive Quality Governor evaluation
        ADAPTIVE_QUALITY.update(PROFILER.fps)

