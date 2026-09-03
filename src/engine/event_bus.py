from typing import Callable, Any, Dict, List

class EventBus:
    """Decoupled event communication system."""
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable):
        if event_type in self._subscribers:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)

    def emit(self, event_type: str, **kwargs: Any):
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                callback(**kwargs)

# Global Event Bus Instance
EVENT_BUS = EventBus()
