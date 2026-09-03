from config.constants import GameState

class GameStateManager:
    """Manages the high-level state of the game (Menu, Playing, etc.)."""
    
    def __init__(self):
        self._current_state = GameState.MAIN_MENU
        
    @property
    def current_state(self) -> GameState:
        return self._current_state
        
    def change_state(self, new_state: GameState):
        self._current_state = new_state
        # Here we could trigger events via EVENT_BUS if needed
        
# Global State Manager
STATE_MANAGER = GameStateManager()
