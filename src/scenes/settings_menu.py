import pygame
from engine.scene_manager import Scene
from ui.menu import Menu, MenuOption
from engine.input_manager import INPUT
from config.settings import SETTINGS
from config.colors import UI_BACKGROUND, UI_TEXT, UI_HIGHLIGHT, BLACK

class SettingsMenuScene(Scene):
    def __init__(self, scene_manager, previous_scene):
        self.scene_manager = scene_manager
        self.previous_scene = previous_scene
        self.font_title = pygame.font.Font(None, 40)
        self.font_option = pygame.font.Font(None, 24)
        self.font_tip = pygame.font.Font(None, 18)
        
        self.selected_index = 0
        self._update_options_text()
        
    def _update_options_text(self):
        res_w, res_h = SETTINGS.RESOLUTIONS[SETTINGS.RESOLUTION_INDEX]
        res_text = f"{res_w}x{res_h}"
        fs_text = "Tela Cheia" if SETTINGS.FULLSCREEN else "Janela"
        rt_text = "Ativado (Volumétrico)" if SETTINGS.RAYTRACING_ENABLED else "Desativado"
        dl_text = "Ativado (Alta)" if SETTINGS.DYNAMIC_LIGHTS else "Desativado"
        pt_text = "Ativado (Folhas/Brasas)" if SETTINGS.AMBIENT_PARTICLES else "Desativado"
        aa_text = "Ativado (Suave / HD)" if SETTINGS.ANTIALIASING else "Desativado"
        vg_text = "Ativado" if SETTINGS.VIGNETTE_ENABLED else "Desativado"
        tq_text = SETTINGS.TEXTURE_QUALITY
        crt_text = "Ativado" if SETTINGS.SCANLINES_ENABLED else "Desativado (Nítido)"
        stretch_text = "Preencher (Sem Barras)" if SETTINGS.FULLSCREEN_STRETCH else "Proporção 4:3 (Barras)"

        
        self.options = [
            ("Resolução", res_text, self.toggle_resolution),
            ("Modo de Tela", fs_text, self.toggle_fullscreen),
            ("Formato de Tela", stretch_text, self.toggle_stretch),
            ("Iluminação Dinâmica", dl_text, self.toggle_dynamic_lights),
            ("Partículas de Ambiente", pt_text, self.toggle_ambient_particles),
            ("Anti-Aliasing", aa_text, self.toggle_antialiasing),
            ("Vinheta Cinematográfica", vg_text, self.toggle_vignette),
            ("Qualidade Texturas", tq_text, self.toggle_texture_quality),
            ("Linhas CRT (Scanlines)", crt_text, self.toggle_scanlines),
            ("Voltar", "", self.go_back)
        ]


    def toggle_resolution(self, direction: int = 1):
        SETTINGS.RESOLUTION_INDEX = (SETTINGS.RESOLUTION_INDEX + direction) % len(SETTINGS.RESOLUTIONS)
        from engine.game import Game
        if Game.instance:
            Game.instance.apply_display_settings()
        self._update_options_text()

    def toggle_fullscreen(self, direction: int = 1):
        SETTINGS.FULLSCREEN = not SETTINGS.FULLSCREEN
        from engine.game import Game
        if Game.instance:
            Game.instance.apply_display_settings()
        self._update_options_text()

    def toggle_stretch(self, direction: int = 1):
        SETTINGS.FULLSCREEN_STRETCH = not SETTINGS.FULLSCREEN_STRETCH
        self._update_options_text()

        
    def toggle_raytracing(self, direction: int = 1):
        SETTINGS.RAYTRACING_ENABLED = not SETTINGS.RAYTRACING_ENABLED
        self._update_options_text()
        
    def toggle_dynamic_lights(self, direction: int = 1):
        SETTINGS.DYNAMIC_LIGHTS = not SETTINGS.DYNAMIC_LIGHTS
        self._update_options_text()
        
    def toggle_ambient_particles(self, direction: int = 1):
        SETTINGS.AMBIENT_PARTICLES = not SETTINGS.AMBIENT_PARTICLES
        self._update_options_text()
        
    def toggle_vignette(self, direction: int = 1):
        SETTINGS.VIGNETTE_ENABLED = not SETTINGS.VIGNETTE_ENABLED
        self._update_options_text()
        
    def toggle_antialiasing(self, direction: int = 1):
        SETTINGS.ANTIALIASING = not SETTINGS.ANTIALIASING
        self._update_options_text()
        
    def toggle_texture_quality(self, direction: int = 1):
        qualities = ["Alta", "Média", "Pixel-Art"]
        idx = (qualities.index(SETTINGS.TEXTURE_QUALITY) + direction) % len(qualities) if SETTINGS.TEXTURE_QUALITY in qualities else 0
        SETTINGS.TEXTURE_QUALITY = qualities[idx]
        self._update_options_text()
        
    def toggle_scanlines(self, direction: int = 1):
        SETTINGS.SCANLINES_ENABLED = not SETTINGS.SCANLINES_ENABLED
        self._update_options_text()

    def go_back(self, direction: int = 1):
        self.scene_manager.change_scene(self.previous_scene)

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        pass
        
    def update(self, dt: float) -> None:
        if INPUT.is_action_just_pressed("UP"):
            self.selected_index = (self.selected_index - 1) % len(self.options)
        elif INPUT.is_action_just_pressed("DOWN"):
            self.selected_index = (self.selected_index + 1) % len(self.options)
        elif INPUT.is_action_just_pressed("LEFT"):
            self.options[self.selected_index][2](-1)
        elif INPUT.is_action_just_pressed("RIGHT") or INPUT.is_action_just_pressed("JUMP") or INPUT.is_action_just_pressed("ACTION"):
            self.options[self.selected_index][2](1)
        elif INPUT.is_action_just_pressed("PAUSE"):
            self.go_back()
        
    def draw(self, surface: pygame.Surface) -> None:
        # Draw previous scene in background (dimmed)
        if hasattr(self.previous_scene, 'draw'):
            self.previous_scene.draw(surface)
            overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            overlay.fill((10, 12, 18, 225))
            surface.blit(overlay, (0, 0))
        else:
            surface.fill((15, 18, 28))
            
        cx = SETTINGS.GAME_WIDTH // 2
        cy = 28
        
        # Title
        title_surf = self.font_title.render("= CONFIGURAÇÕES GRÁFICAS =", True, (255, 215, 100))
        t_rect = title_surf.get_rect(center=(cx, cy))
        surface.blit(title_surf, t_rect)
        
        # Options List
        start_y = cy + 32
        spacing = 26
        for i, (label, val, _) in enumerate(self.options):
            is_selected = (i == self.selected_index)
            color = (255, 235, 120) if is_selected else (210, 215, 225)
            prefix = "> " if is_selected else "  "
            
            if val:
                line_str = f"{prefix}{label}:  < {val} >"
            else:
                line_str = f"{prefix}{label}"
                
            opt_surf = self.font_option.render(line_str, True, color)
            opt_rect = opt_surf.get_rect(center=(cx, start_y + (i * spacing)))
            
            # Highlight bar behind selected option
            if is_selected:
                bar = pygame.Surface((opt_rect.width + 20, opt_rect.height + 4), pygame.SRCALPHA)
                bar.fill((80, 90, 130, 95))
                surface.blit(bar, (opt_rect.x - 10, opt_rect.y - 2))
                pygame.draw.rect(surface, (200, 170, 70), (opt_rect.x - 10, opt_rect.y - 2, opt_rect.width + 20, opt_rect.height + 4), 1, border_radius=3)
                
            surface.blit(opt_surf, opt_rect)
            
        # Footer Navigation Hint
        tip_surf = self.font_tip.render("[W/S] ou [Setas] Navegar   |   [A/D], [Setas] ou [Espaço] Alterar   |   [ESC] Voltar", True, (160, 170, 190))
        surface.blit(tip_surf, tip_surf.get_rect(center=(cx, SETTINGS.GAME_HEIGHT - 16)))
