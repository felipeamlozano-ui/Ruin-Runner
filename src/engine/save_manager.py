"""
Ruin Engine V3.2 — Persistent Save & Campaign Profile Manager.
Manages player profiles, multi-slot campaign saves, persistent narrative progress,
collected Orbs, talent levels, tutorial status, world progression, checkpoints,
and high scores with secure atomic JSON serialization, schema versioning, and corrupt file recovery.
"""

import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Project root determined relative to this file: src/engine/save_manager.py -> root is 2 parents up
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SAVES_DIR = PROJECT_ROOT / "saves"
DEFAULT_GLOBAL_SAVE_FILE = PROJECT_ROOT / "save_data.json"

CURRENT_SAVE_VERSION = 2

DEFAULT_CAMPAIGN_DATA: Dict[str, Any] = {
    "version": CURRENT_SAVE_VERSION,
    "slot_id": 1,
    "created_at": "",
    "updated_at": "",
    "character_id": "shaia",
    "chapter": 1,
    "current_world": "terrae",
    "current_stage": "terrae_1",
    "unlocked_worlds": ["terrae"],
    "unlocked_stages": ["terrae_1"],
    "completed_stages": [],
    "completed_worlds": [],
    "checkpoints": {},
    "narrative_flags": {},
    "completed_events": [],
    "orbs": 120,
    "playtime_sec": 0.0,
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
    "tutorial_completed": False,
    "high_scores": {}
}

DEFAULT_GLOBAL_PROFILE: Dict[str, Any] = {
    "version": CURRENT_SAVE_VERSION,
    "active_slot": 1,
    "orbs": 120,
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
    "selected_character": "shaia"
}


class SaveManager:
    """
    Robust Persistent Save & Profile Manager.
    Supports multi-slot campaign saves, version migrations, atomic disk sync,
    and automatic fallback/recovery from corrupted files.
    """
    _instance: Optional['SaveManager'] = None

    def __init__(self, filepath: Optional[str] = None, saves_dir: Optional[str] = None):
        self.filepath = Path(filepath) if filepath else DEFAULT_GLOBAL_SAVE_FILE
        if saves_dir:
            self.saves_dir = Path(saves_dir)
        elif filepath:
            self.saves_dir = self.filepath.parent / f"{self.filepath.stem}_saves"
        else:
            self.saves_dir = DEFAULT_SAVES_DIR
            
        self.saves_dir.mkdir(parents=True, exist_ok=True)
        
        self.data: Dict[str, Any] = {}
        self.active_slot: int = 1
        self.campaign_data: Dict[str, Any] = {}
        
        self.load()

    @classmethod
    def get_instance(cls) -> 'SaveManager':
        if cls._instance is None:
            cls._instance = SaveManager()
        return cls._instance

    # ─────────────────────────────────────────────────────────────────────────
    # ATOMIC I/O & CORRUPTION SAFEGUARDS
    # ─────────────────────────────────────────────────────────────────────────
    def _atomic_write_json(self, target_path: Path, data: dict) -> bool:
        """Writes JSON data atomically with temp file rename and backup creation."""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = target_path.with_suffix(".tmp")
        bak_path = target_path.with_suffix(".bak")

        try:
            # 1. Write to temporary file
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # 2. If target exists and is valid, backup it first
            if target_path.exists():
                try:
                    shutil.copy2(target_path, bak_path)
                except Exception:
                    pass

            # 3. Replace target with temp file
            os.replace(tmp_path, target_path)
            return True
        except Exception as e:
            print(f"[SaveManager] Error saving data to {target_path}: {e}")
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass
            return False

    def _safe_load_json(self, target_path: Path, default_data: dict) -> dict:
        """Safely loads JSON with schema migration and backup file fallback."""
        if target_path.exists():
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    merged = json.loads(json.dumps(default_data))
                    self._deep_update(merged, loaded)
                    return self._migrate_schema(merged)
            except Exception as e:
                print(f"[SaveManager] Corrupted save {target_path} ({e}). Attempting backup restore...")
                bak_path = target_path.with_suffix(".bak")
                if bak_path.exists():
                    try:
                        with open(bak_path, "r", encoding="utf-8") as fb:
                            loaded_bak = json.load(fb)
                            merged = json.loads(json.dumps(default_data))
                            self._deep_update(merged, loaded_bak)
                            return self._migrate_schema(merged)
                    except Exception as eb:
                        print(f"[SaveManager] Backup {bak_path} also unusable ({eb}).")

        # Fallback to defaults
        fresh = json.loads(json.dumps(default_data))
        fresh["created_at"] = datetime.now().isoformat()
        fresh["updated_at"] = fresh["created_at"]
        return fresh

    def _deep_update(self, target: dict, source: dict):
        """Recursively updates target dict from source dict without wiping keys."""
        for k, v in source.items():
            if isinstance(v, dict) and k in target and isinstance(target[k], dict):
                self._deep_update(target[k], v)
            else:
                target[k] = v

    def _migrate_schema(self, data: dict) -> dict:
        """Migrates older schema versions to current format."""
        v = data.get("version", 1)
        if v < 2:
            data["version"] = 2
            if "unlocked_stages" not in data:
                data["unlocked_stages"] = ["terrae_1"]
            if "completed_stages" not in data:
                data["completed_stages"] = []
            if "completed_events" not in data:
                data["completed_events"] = []
            if "narrative_flags" not in data:
                data["narrative_flags"] = {}
            if "checkpoints" not in data:
                data["checkpoints"] = {}
        return data

    # ─────────────────────────────────────────────────────────────────────────
    # GLOBAL PROFILE & RETRO-COMPATIBILITY
    # ─────────────────────────────────────────────────────────────────────────
    def load(self):
        """Loads global profile and active campaign slot."""
        self.data = self._safe_load_json(self.filepath, DEFAULT_GLOBAL_PROFILE)
        self.active_slot = int(self.data.get("active_slot", 1))
        self.load_slot(self.active_slot)

    def save(self):
        """Saves both the global profile and the active campaign slot."""
        self.data["updated_at"] = datetime.now().isoformat()
        self.data["active_slot"] = self.active_slot
        self._atomic_write_json(self.filepath, self.data)
        if self.campaign_data:
            self._save_active_slot_data()

    # ─────────────────────────────────────────────────────────────────────────
    # MULTI-SLOT CAMPAIGN SYSTEM
    # ─────────────────────────────────────────────────────────────────────────
    def _slot_path(self, slot_id: int) -> Path:
        return self.saves_dir / f"slot_{slot_id}.json"

    def list_slots(self, max_slots: int = 3) -> List[Dict[str, Any]]:
        """Returns metadata summary of each campaign save slot for UI listing."""
        slots = []
        for s_id in range(1, max_slots + 1):
            p = self._slot_path(s_id)
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        s_data = json.load(f)
                    slots.append({
                        "slot_id": s_id,
                        "exists": True,
                        "character_id": s_data.get("character_id", "shaia"),
                        "chapter": s_data.get("chapter", 1),
                        "world": s_data.get("current_world", "terrae"),
                        "stage": s_data.get("current_stage", "terrae_1"),
                        "completed_stages_count": len(s_data.get("completed_stages", [])),
                        "orbs": s_data.get("orbs", 0),
                        "updated_at": s_data.get("updated_at", ""),
                        "playtime_sec": s_data.get("playtime_sec", 0.0)
                    })
                    continue
                except Exception:
                    pass
            slots.append({
                "slot_id": s_id,
                "exists": False,
                "character_id": "shaia",
                "chapter": 1,
                "world": "terrae",
                "stage": "terrae_1",
                "completed_stages_count": 0,
                "orbs": 0,
                "updated_at": "",
                "playtime_sec": 0.0
            })
        return slots

    def load_slot(self, slot_id: int) -> Dict[str, Any]:
        """Loads campaign progress for a specific slot ID."""
        self.active_slot = max(1, slot_id)
        path = self._slot_path(self.active_slot)
        
        # If slot file doesn't exist, check if legacy global file has story progress to import
        if not path.exists() and self.active_slot == 1 and "story_mode" in self.data:
            fresh = json.loads(json.dumps(DEFAULT_CAMPAIGN_DATA))
            fresh["slot_id"] = 1
            fresh["created_at"] = datetime.now().isoformat()
            fresh["updated_at"] = fresh["created_at"]
            fresh["orbs"] = self.data.get("orbs", 120)
            fresh["skills"] = self.data.get("skills", fresh["skills"])
            fresh["tutorial_completed"] = self.data.get("tutorial_completed", False)
            fresh["character_id"] = self.data.get("selected_character", "shaia")
            st_data = self.data.get("story_mode", {})
            fresh["unlocked_worlds"] = st_data.get("unlocked_worlds", ["terrae"])
            fresh["current_world"] = st_data.get("current_world", "terrae")
            self.campaign_data = fresh
            self._save_active_slot_data()
        else:
            defaults = json.loads(json.dumps(DEFAULT_CAMPAIGN_DATA))
            defaults["slot_id"] = self.active_slot
            self.campaign_data = self._safe_load_json(path, defaults)

        # Synchronize global profile
        self.data["active_slot"] = self.active_slot
        self.data["orbs"] = self.campaign_data.get("orbs", self.data.get("orbs", 120))
        self.data["skills"] = self.campaign_data.get("skills", self.data.get("skills", {}))
        self.data["tutorial_completed"] = self.campaign_data.get("tutorial_completed", False)
        self.data["selected_character"] = self.campaign_data.get("character_id", "shaia")
        
        return self.campaign_data

    def _save_active_slot_data(self) -> bool:
        """Flushes active campaign slot data to its file."""
        if not self.campaign_data:
            return False
        self.campaign_data["updated_at"] = datetime.now().isoformat()
        self.campaign_data["slot_id"] = self.active_slot
        path = self._slot_path(self.active_slot)
        return self._atomic_write_json(path, self.campaign_data)

    def new_game(self, slot_id: int, character_id: str = "shaia") -> Dict[str, Any]:
        """Creates a fresh new campaign in the specified slot, resetting progression."""
        self.active_slot = max(1, slot_id)
        now_str = datetime.now().isoformat()
        
        fresh = json.loads(json.dumps(DEFAULT_CAMPAIGN_DATA))
        fresh["slot_id"] = self.active_slot
        fresh["created_at"] = now_str
        fresh["updated_at"] = now_str
        fresh["character_id"] = character_id
        fresh["chapter"] = 1
        fresh["current_world"] = "terrae"
        fresh["current_stage"] = "terrae_1"
        fresh["unlocked_worlds"] = ["terrae"]
        fresh["unlocked_stages"] = ["terrae_1"]
        fresh["completed_stages"] = []
        fresh["completed_worlds"] = []
        fresh["checkpoints"] = {}
        fresh["narrative_flags"] = {}
        fresh["completed_events"] = []
        fresh["orbs"] = 120
        fresh["playtime_sec"] = 0.0
        
        self.campaign_data = fresh
        self._save_active_slot_data()
        
        # Mirror to global profile
        self.data["active_slot"] = self.active_slot
        self.data["selected_character"] = character_id
        self.data["orbs"] = 120
        self.save()
        
        return self.campaign_data

    def delete_slot(self, slot_id: int) -> bool:
        """Deletes a save slot and its backup."""
        p = self._slot_path(slot_id)
        bak = p.with_suffix(".bak")
        deleted = False
        if p.exists():
            try:
                p.unlink()
                deleted = True
            except Exception:
                pass
        if bak.exists():
            try:
                bak.unlink()
            except Exception:
                pass
        if slot_id == self.active_slot:
            self.load_slot(slot_id)
        return deleted

    # ─────────────────────────────────────────────────────────────────────────
    # NARRATIVE & STAGE PROGRESSION API
    # ─────────────────────────────────────────────────────────────────────────
    def get_current_stage(self) -> str:
        return self.campaign_data.get("current_stage", "terrae_1")

    def set_current_stage(self, stage_id: str):
        self.campaign_data["current_stage"] = stage_id
        self.unlock_stage(stage_id)
        self._save_active_slot_data()

    def get_current_world(self) -> str:
        return self.campaign_data.get("current_world", "terrae")

    def set_current_world(self, world_id: str):
        self.campaign_data["current_world"] = world_id
        self.unlock_world(world_id)
        self._save_active_slot_data()

    def get_character_id(self) -> str:
        return self.campaign_data.get("character_id", self.data.get("selected_character", "shaia"))

    def set_character_id(self, character_id: str):
        self.campaign_data["character_id"] = character_id
        self.data["selected_character"] = character_id
        self.save()

    def is_stage_unlocked(self, stage_id: str) -> bool:
        unlocked = self.campaign_data.get("unlocked_stages", ["terrae_1"])
        return stage_id in unlocked

    def unlock_stage(self, stage_id: str):
        if "unlocked_stages" not in self.campaign_data:
            self.campaign_data["unlocked_stages"] = ["terrae_1"]
        if stage_id not in self.campaign_data["unlocked_stages"]:
            self.campaign_data["unlocked_stages"].append(stage_id)
            self._save_active_slot_data()

    def is_world_unlocked(self, world_id: str) -> bool:
        unlocked = self.campaign_data.get("unlocked_worlds", ["terrae"])
        return world_id in unlocked

    def unlock_world(self, world_id: str):
        if "unlocked_worlds" not in self.campaign_data:
            self.campaign_data["unlocked_worlds"] = ["terrae"]
        if world_id not in self.campaign_data["unlocked_worlds"]:
            self.campaign_data["unlocked_worlds"].append(world_id)
            # Unlock the first stage of this world automatically
            self.unlock_stage(f"{world_id}_1")
            self._save_active_slot_data()

    def complete_stage(self, stage_id: str, stars: int = 3, score: int = 0):
        """Marks a stage as completed, unlocking subsequent progression."""
        if "completed_stages" not in self.campaign_data:
            self.campaign_data["completed_stages"] = []
        if stage_id not in self.campaign_data["completed_stages"]:
            self.campaign_data["completed_stages"].append(stage_id)

        # Update chapter if appropriate
        world_prefix = stage_id.split("_")[0] if "_" in stage_id else stage_id
        chapter_map = {"terrae": 1, "sanguis": 2, "glacies": 3, "aetheria": 4}
        if world_prefix in chapter_map:
            self.campaign_data["chapter"] = max(self.campaign_data.get("chapter", 1), chapter_map[world_prefix])

        self._save_active_slot_data()

    def is_stage_completed(self, stage_id: str) -> bool:
        return stage_id in self.campaign_data.get("completed_stages", [])

    def is_event_completed(self, event_id: str) -> bool:
        """Checks if a cinematic dialogue event has already taken place in this campaign."""
        return event_id in self.campaign_data.get("completed_events", [])

    def set_event_completed(self, event_id: str):
        """Persists that a narrative encounter or dialogue has concluded."""
        if "completed_events" not in self.campaign_data:
            self.campaign_data["completed_events"] = []
        if event_id not in self.campaign_data["completed_events"]:
            self.campaign_data["completed_events"].append(event_id)
            self._save_active_slot_data()

    def set_checkpoint(self, stage_id: str, x: float, y: float):
        if "checkpoints" not in self.campaign_data:
            self.campaign_data["checkpoints"] = {}
        self.campaign_data["checkpoints"][stage_id] = [float(x), float(y)]
        self._save_active_slot_data()

    def get_checkpoint(self, stage_id: Optional[str] = None) -> Optional[Tuple[Any, ...]]:
        cps = self.campaign_data.get("checkpoints", {})
        if stage_id:
            if stage_id in cps:
                pt = cps[stage_id]
                return (float(pt[0]), float(pt[1]))
            return None
        if cps:
            last_stg, last_pt = list(cps.items())[-1]
            return (last_stg, float(last_pt[0]), float(last_pt[1]))
        return None

    def add_playtime(self, seconds: float):
        cur = float(self.campaign_data.get("playtime_sec", 0.0))
        self.campaign_data["playtime_sec"] = cur + max(0.0, seconds)

    # ─────────────────────────────────────────────────────────────────────────
    # ORB ECONOMY & SKILL TREE DELEGATIONS
    # ─────────────────────────────────────────────────────────────────────────
    def get_orbs(self) -> int:
        if self.campaign_data and "orbs" in self.campaign_data:
            return int(self.campaign_data["orbs"])
        return int(self.data.get("orbs", 0))

    def add_orbs(self, amount: int) -> int:
        new_total = max(0, self.get_orbs() + amount)
        self.data["orbs"] = new_total
        if self.campaign_data:
            self.campaign_data["orbs"] = new_total
        self.save()
        return new_total

    def spend_orbs(self, amount: int) -> bool:
        if self.get_orbs() >= amount:
            new_total = self.get_orbs() - amount
            self.data["orbs"] = new_total
            if self.campaign_data:
                self.campaign_data["orbs"] = new_total
            self.save()
            return True
        return False

    def get_skill_level(self, skill_id: str) -> int:
        skills = self.campaign_data.get("skills", {}) if self.campaign_data else self.data.get("skills", {})
        return int(skills.get(skill_id, 0))

    def set_skill_level(self, skill_id: str, level: int):
        if "skills" not in self.data:
            self.data["skills"] = {}
        self.data["skills"][skill_id] = level
        if self.campaign_data:
            if "skills" not in self.campaign_data:
                self.campaign_data["skills"] = {}
            self.campaign_data["skills"][skill_id] = level
        self.save()

    def is_tutorial_completed(self) -> bool:
        if self.campaign_data and "tutorial_completed" in self.campaign_data:
            return bool(self.campaign_data["tutorial_completed"])
        return bool(self.data.get("tutorial_completed", False))

    def set_tutorial_completed(self, status: bool = True):
        self.data["tutorial_completed"] = status
        if self.campaign_data:
            self.campaign_data["tutorial_completed"] = status
        self.save()


SAVE = SaveManager.get_instance()
