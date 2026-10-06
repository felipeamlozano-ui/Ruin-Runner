"""
Ruin Engine V3.0 — ECS World & Archetype Dispatcher.
High-throughput cache-friendly component queries and lifecycle management.
"""

from typing import Dict, Type, Any, Set, Tuple, List, Optional, TypeVar

T = TypeVar("T")

class ECSWorld:
    """
    Central database of entities and contiguous component stores.
    """
    def __init__(self):
        self._next_entity_id: int = 1
        self._active_entities: Set[int] = set()
        # Storage: { ComponentType: { entity_id: component_instance } }
        self._stores: Dict[Type, Dict[int, Any]] = {}
        self._systems: List[Any] = []

    def create_entity(self) -> int:
        """Instantiates a unique entity ID."""
        entity_id = self._next_entity_id
        self._next_entity_id += 1
        self._active_entities.add(entity_id)
        return entity_id

    def destroy_entity(self, entity_id: int) -> None:
        """Removes an entity and purges all of its associated component stores."""
        if entity_id in self._active_entities:
            self._active_entities.remove(entity_id)
            for store in self._stores.values():
                store.pop(entity_id, None)

    def add_component(self, entity_id: int, component: Any) -> None:
        """Attaches a decoupled component to an entity."""
        comp_type = type(component)
        if comp_type not in self._stores:
            self._stores[comp_type] = {}
        self._stores[comp_type][entity_id] = component

    def get_component(self, entity_id: int, comp_type: Type[T]) -> Optional[T]:
        """Retrieves a specific component for an entity, if attached."""
        store = self._stores.get(comp_type)
        if store:
            return store.get(entity_id)
        return None

    def has_component(self, entity_id: int, comp_type: Type) -> bool:
        """Checks component membership."""
        store = self._stores.get(comp_type)
        return store is not None and entity_id in store

    def remove_component(self, entity_id: int, comp_type: Type) -> None:
        """Detaches a component type from an entity."""
        store = self._stores.get(comp_type)
        if store:
            store.pop(entity_id, None)

    def query(self, *comp_types: Type) -> List[Tuple[int, ...]]:
        """
        Executes intersection query returning tuples of (entity_id, comp1, comp2, ...).
        Sorts queries by smallest component store first for optimal branch efficiency.
        """
        if not comp_types:
            return []

        # Find stores
        active_stores = [self._stores.get(ct, {}) for ct in comp_types]
        if any(len(s) == 0 for s in active_stores):
            return []

        # Find smallest store to iterate
        sorted_indices = sorted(range(len(active_stores)), key=lambda i: len(active_stores[i]))
        lead_index = sorted_indices[0]
        lead_store = active_stores[lead_index]

        results = []
        for entity_id in lead_store:
            # Check if all other stores have this entity
            has_all = True
            for i in range(len(active_stores)):
                if i != lead_index and entity_id not in active_stores[i]:
                    has_all = False
                    break
            if has_all:
                row = [entity_id] + [active_stores[i][entity_id] for i in range(len(comp_types))]
                results.append(tuple(row))

        return results

    def register_system(self, system: Any) -> None:
        """Registers a logic system to be executed on tick."""
        self._systems.append(system)

    def update(self, dt: float) -> None:
        """Executes all registered systems in sequential order."""
        for system in self._systems:
            system.update(self, dt)
