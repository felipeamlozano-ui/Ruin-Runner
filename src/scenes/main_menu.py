import pygame
import sys
from engine.scene_manager import Scene
from ui.menu import Menu, MenuOption
from engine.input_manager import INPUT
from config.settings import SETTINGS
from config.colors import UI_BACKGROUND
import engine.resource_manager as rm

class MainMenuScene(Scene):
    def __init__(self, scene_manager):
        self.scene_manager = scene_manager
        
        self.menu = Menu("RUIN RUNNER", [
            MenuOption("Novo Jogo", self.start_game),
            MenuOption("Selecionar Personagem", self.open_character_select),
            MenuOption("Configurações", self.open_settings),
            MenuOption("Sair", self.quit_game)
        ])
        
        # Retro animated background setup (placeholder logic)
        self.bg_timer = 0.0
        
    def start_game(self):
        from scenes.loading_scene import LoadingScene
        if SETTINGS.DEV_MODE and SETTINGS.DEV_START_BOSS:
            from scenes.boss_scene import BossScene
            boss_scene = BossScene(self.scene_manager)
            loading = LoadingScene(
                self.scene_manager,
                boss_scene,
                title="SALA DO BOSS: O REI ESQUELETO",
                tip="Modo Dev Ativo: Iniciando confronto diretamente na sala do Boss!"
            )
            self.scene_manager.change_scene(loading)
        else:
            from scenes.level_scene import LevelScene
            lvl1 = LevelScene(stage=1, scene_manager=self.scene_manager)
            loading = LoadingScene(
                self.scene_manager,
                lvl1,
                title="FASE 1: AS CATACUMBAS",
                tip="Dica: Use [Shift] para erguer o escudo ou barreira e bloquear danos!"
            )
            self.scene_manager.change_scene(loading)
        
    def open_character_select(self):
        from scenes.character_select_scene import CharacterSelectScene
        self.scene_manager.change_scene(CharacterSelectScene(self.scene_manager, self))
        
    def open_settings(self):
        from scenes.settings_menu import SettingsMenuScene
        self.scene_manager.change_scene(SettingsMenuScene(self.scene_manager, self))
        
    def quit_game(self):
        pygame.quit()
        sys.exit()

    def handle_events(self, events: list[pygame.event.Event]) -> None:
        pass # All input handled by INPUT manager in update
        
    def update(self, dt: float) -> None:
        self.menu.handle_input(INPUT)
        self.bg_timer += dt
        
    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(UI_BACKGROUND)
        
        # Simple retro background effect (moving lines)
        offset = int(self.bg_timer * 20) % 20
        for y in range(0, SETTINGS.GAME_HEIGHT, 20):
            pygame.draw.line(surface, (30, 30, 40), (0, y + offset), (SETTINGS.GAME_WIDTH, y + offset))
            
        # Dev mode indicator badge
        if SETTINGS.DEV_MODE:
            dev_font = pygame.font.SysFont("Arial", 11, bold=True)
            dev_surf = dev_font.render("[MODO DEV: INÍCIO NO BOSS ATIVADO]", True, (255, 140, 70))
            dev_rect = dev_surf.get_rect(center=(SETTINGS.GAME_WIDTH // 2, 24))
            surface.blit(dev_surf, dev_rect)
            
        self.menu.draw(surface, SETTINGS.GAME_WIDTH // 2, SETTINGS.GAME_HEIGHT // 2 - 40)
