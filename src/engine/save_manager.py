"""
Ruin Engine V3.0 — Persistent Save & Profile Manager.
Manages player profile, collected Orbs, talent levels, tutorial status,
world progression, and high scores with JSON serialization and robust fallback.
"""

import json
import os
from typing import Dict, Any

SAVE_FILE_PATH = os.path.join("save_data.json")

DEFAULT_SAVE_DATA: Dict[str, Any] = {
    "orbs": 120, # Initial orbs so player can explore the Magic Book
    "tutorial_completed": False,
    "skills": {
        "blade_sharpness": 1,
        "combo_finisher": 0,
        "arcane_mastery": 0,
        "aoe_resonance": 0,
        "shadow_step": 0,
        "ultimate_wrath": 0,
        "alchemist_elixir": 0,
        "titan_heart": 0,
        "cosmic_mana": 0
    },
    "story_mode": {
        "unlocked_worlds": ["terrae"],
        "current_world": "terrae",
        "world_stars": {"terrae": 0, "sanguis": 0, "glacies": 0, "aetheria": 0}
    },
    "high_scores": {},
    "selected_character": "knight"
}

class SaveManager:
    """Singleton-style save data manager."""
    _instance = None
    
    def __init__(self, filepath: str = SAVE_FILE_PATH):
        self.filepath = filepath
        self.data: Dict[str, Any] = {}
        self.load()
        
    @classmethod
    def get_instance(cls) -> 'SaveManager':
        if cls._instance is None:
            cls._instance = SaveManager()
        return cls._instance

    def load(self):
        """Loads save file or initialises default schema."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Merge with default schema to ensure all keys exist
                    self.data = DEFAULT_SAVE_DATA.copy()
                    self._deep_update(self.data, loaded)
                    return
            except Exception as e:
                print(f"Warning: Corrupted save file {self.filepath} ({e}). Rebuilding defaults.")
                
        self.data = json.loads(json.dumps(DEFAULT_SAVE_DATA))
        self.save()

    def _deep_update(self, target: dict, source: dict):
        for k, v in source.items():
            if isinstance(v, dict) and k in target and isinstance(target[k], dict):
                self._deep_update(target[k], v)
            else:
                target[k] = v

    def save(self):
        """Serializes current profile safely to disk."""
        try:
            temp_path = self.filepath + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            if os.path.exists(self.filepath):
                os.replace(temp_path, self.filepath)
            else:
                os.rename(temp_path, self.filepath)
        except Exception as e:
            print(f"Error saving data to {self.filepath}: {e}")

    # Orbs
    def get_orbs(self) -> int:
        return int(self.data.get("orbs", 0))

    def add_orbs(self, amount: int) -> int:
        self.data["orbs"] = max(0, self.get_orbs() + amount)
        self.save()
        return self.data["orbs"]

    def spend_orbs(self, amount: int) -> bool:
        if self.get_orbs() >= amount:
            self.data["orbs"] -= amount
            self.save()
            return True
        return False

    # Skills / Magic Book
    def get_skill_level(self, skill_id: str) -> int:
        return self.data.get("skills", {}).get(skill_id, 0)

    def set_skill_level(self, skill_id: str, level: int):
        if "skills" not in self.data:
            self.data["skills"] = {}
        self.data["skills"][skill_id] = level
        self.save()

    # Tutorial
    def is_tutorial_completed(self) -> bool:
        return bool(self.data.get("tutorial_completed", False))

    def set_tutorial_completed(self, status: bool = True):
        self.data["tutorial_completed"] = status
        self.save()

SAVE = SaveManager.get_instance()
