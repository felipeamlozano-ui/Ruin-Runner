"""
Ruin Engine V3.0 — AAA Score & Combo Multiplier System.
Rewards player technique, speed, and aggressive combos with dynamic multipliers,
No-Hit bonuses, and automatic High Score persistence to save_data.json.
"""

from typing import Dict, Any, Tuple
from engine.save_manager import SAVE

ENEMY_POINT_VALUES = {
    "skeleton": 100,
    "spearman": 180,
    "warrior": 180,
    "mage": 250,
    "archer": 220,
    "boar": 600,
    "boss": 10000,
    "skeleton_king": 10000
}

class ScoreSystem:
    """Manages stage scoring, combo multipliers, and victory ranking."""
    
    def __init__(self, stage_id: str = "stage_1"):
        self.stage_id = stage_id
        self.score = 0
        self.combo_count = 0
        self.combo_multiplier = 1.0
        self.combo_timer = 0.0
        self.combo_max_time = 2.5
        
        self.enemies_defeated = 0
        self.orbs_collected = 0
        self.damage_taken = 0
        self.time_elapsed = 0.0
        self.max_combo = 0
        
    def add_hit(self):
        """Called when player lands an attack."""
        self.combo_count += 1
        if self.combo_count > self.max_combo:
            self.max_combo = self.combo_count
        self.combo_multiplier = min(4.0, 1.0 + (self.combo_count * 0.1))
        self.combo_timer = self.combo_max_time

    def add_kill(self, enemy_type: str = "skeleton"):
        """Called when an enemy is defeated."""
        base_pts = ENEMY_POINT_VALUES.get(enemy_type.lower(), 150)
        awarded = int(base_pts * self.combo_multiplier)
        self.score += awarded
        self.enemies_defeated += 1
        self.add_hit()

    def add_orb(self, value: int = 1):
        self.orbs_collected += value
        self.score += value * 100

    def register_damage(self, amount: int):
        self.damage_taken += amount
        # Break combo on hit
        self.combo_count = 0
        self.combo_multiplier = 1.0
        self.combo_timer = 0.0

    def update(self, dt: float):
        self.time_elapsed += dt
        if self.combo_timer > 0:
            self.combo_timer -= dt
            if self.combo_timer <= 0:
                self.combo_count = 0
                self.combo_multiplier = 1.0

    def calculate_final_score(self) -> Dict[str, Any]:
        """Calculates end-of-stage totals, bonuses, and letter rank."""
        # Time Bonus: 5000 base minus 15 pts per second
        time_bonus = max(0, int(5000 - self.time_elapsed * 15))
        
        # No-Hit Bonus
        no_hit_bonus = 5000 if self.damage_taken == 0 else 0
        
        total = self.score + time_bonus + no_hit_bonus
        
        # Letter Rank: S, A, B, C, D
        if total >= 20000:
            rank = "S"
            rank_title = "MESTRE LENDÁRIO"
            rank_color = (255, 215, 0)
        elif total >= 14000:
            rank = "A"
            rank_title = "CONQUISTADOR EXCEPCIONAL"
            rank_color = (130, 220, 255)
        elif total >= 9000:
            rank = "B"
            rank_title = "GUERREIRO VETERANO"
            rank_color = (120, 255, 120)
        elif total >= 5000:
            rank = "C"
            rank_title = "COMBATENTE REGULAR"
            rank_color = (220, 200, 140)
        else:
            rank = "D"
            rank_title = "APRENDIZ DESTRUTÍVEL"
            rank_color = (180, 180, 180)

        # Save record
        if "high_scores" not in SAVE.data:
            SAVE.data["high_scores"] = {}
        old_high = SAVE.data["high_scores"].get(self.stage_id, 0)
        is_new_record = total > old_high
        if is_new_record:
            SAVE.data["high_scores"][self.stage_id] = total
            SAVE.save()

        return {
            "stage_id": self.stage_id,
            "base_score": self.score,
            "time_bonus": time_bonus,
            "no_hit_bonus": no_hit_bonus,
            "total_score": total,
            "rank": rank,
            "rank_title": rank_title,
            "rank_color": rank_color,
            "enemies_killed": self.enemies_defeated,
            "max_combo": self.max_combo,
            "time_sec": round(self.time_elapsed, 1),
            "is_new_record": is_new_record,
            "best_score": max(old_high, total)
        }
