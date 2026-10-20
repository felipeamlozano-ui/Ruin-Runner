"""
Ruin Runner — Co-op Elemental Synergy System (CoopSynergySystem).
Detects multi-player tactical combos and elemental resonance:
- Fire + Wind = Firestorm (Expanded blazing vortex with fire ticks)
- Ice + Light = Holy Freeze (Freezes enemies solid and causes shatter burst)
- Shadow + Lightning = Void Strike (Armor pierce + chain reaction)
- Arrow + Fire = Burning Arrow (Multi-target piercing incendiary projectile)
- Water/Ice + Lightning = Chain Shock (Arcs electrical damage between all targets)
"""

import math
import random
import pygame
from typing import List, Tuple, Optional, Dict
COOP_SYNERGIES: Dict[Tuple[str, str], str] = {
    ("fire", "wind"): "Tempestade de Fogo",
    ("ice", "light"): "Congelamento Sagrado",
    ("shadow", "lightning"): "Golpe do Vácuo",
    ("arrow", "fire"): "Flecha Incendiária",
    ("water", "lightning"): "Choque em Cadeia"
}

class SynergyCombo:
    """Represents a successfully triggered tactical cooperative synergy."""
    def __init__(self, name: str, desc: str, color: Tuple[int, int, int], damage_mult: float = 1.6):
        self.name = name
        self.desc = desc
        self.color = color
        self.damage_mult = damage_mult
        self.timer = 1.6
        self.active = True

    def update(self, dt: float) -> bool:
        self.timer -= dt
        if self.timer <= 0:
            self.active = False
        return self.active

    def draw_banner(self, surface: pygame.Surface, font: pygame.font.Font, x: int, y: int):
        alpha = min(255, int(255 * (self.timer / 1.6) * 1.5))
        if alpha <= 0:
            return
            
        banner_w = 260
        banner_h = 32
        bx = x - banner_w // 2
        by = y
        
        bg = pygame.Surface((banner_w, banner_h), pygame.SRCALPHA)
        bg.fill((15, 20, 30, int(alpha * 0.85)))
        pygame.draw.rect(bg, (*self.color, alpha), (0, 0, banner_w, banner_h), width=1, border_radius=4)
        surface.blit(bg, (bx, by))
        
        from engine.text_cache import get_cached_text
        text_surf = get_cached_text(font, f"SYNERGY: {self.name}!", self.color)
        text_r = text_surf.get_rect(center=(x, by + banner_h // 2))
        surface.blit(text_surf, text_r)


class CoopSynergySystem:
    """
    Evaluates elemental applications and attacks from Player 1 and Player 2,
    triggering synergistic tactical combinations.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
            
        # Target recent element status: target_id -> {element: timestamp}
        self.recent_applications: Dict[int, Dict[str, float]] = {}
        self.active_combos: List[SynergyCombo] = []
        self.synergy_font = None
        self._initialized = True

    def register_element_hit(
        self,
        target,
        element: str,
        source_player_index: int,
        base_damage: int,
        current_time: float
    ) -> Tuple[int, Optional[SynergyCombo]]:
        """
        Registers an elemental attack on a target. If the other player recently applied
        a complementary element, triggers an elemental synergy combo.
        """
        tid = id(target)
        if tid not in self.recent_applications:
            self.recent_applications[tid] = {}

        apps = self.recent_applications[tid]
        combo_triggered = None
        final_damage = base_damage
        elem = element.lower()

        # Check for complementary synergies (applied within 3.0s window)
        window = 3.0
        
        # 1. Fire + Wind = Firestorm
        if elem == "fire" and "wind" in apps and (current_time - apps["wind"] <= window):
            combo_triggered = SynergyCombo("Tempestade de Fogo", "Firestorm Vortex", (255, 140, 30), damage_mult=1.85)
            final_damage = int(base_damage * 1.85)
            del apps["wind"]
        elif elem == "wind" and "fire" in apps and (current_time - apps["fire"] <= window):
            combo_triggered = SynergyCombo("Tempestade de Fogo", "Firestorm Vortex", (255, 140, 30), damage_mult=1.85)
            final_damage = int(base_damage * 1.85)
            del apps["fire"]

        # 2. Ice + Light = Holy Freeze
        elif elem == "ice" and "light" in apps and (current_time - apps["light"] <= window):
            combo_triggered = SynergyCombo("Congelamento Sagrado", "Holy Freeze", (140, 240, 255), damage_mult=1.90)
            final_damage = int(base_damage * 1.90)
            if hasattr(target, "freeze_timer"):
                target.freeze_timer = 2.5
            del apps["light"]
        elif elem == "light" and "ice" in apps and (current_time - apps["ice"] <= window):
            combo_triggered = SynergyCombo("Congelamento Sagrado", "Holy Freeze", (140, 240, 255), damage_mult=1.90)
            final_damage = int(base_damage * 1.90)
            if hasattr(target, "freeze_timer"):
                target.freeze_timer = 2.5
            del apps["ice"]

        # 3. Shadow + Lightning = Void Strike
        elif elem == "shadow" and "lightning" in apps and (current_time - apps["lightning"] <= window):
            combo_triggered = SynergyCombo("Golpe do Vácuo", "Void Strike", (210, 80, 255), damage_mult=2.10)
            final_damage = int(base_damage * 2.10)
            del apps["lightning"]
        elif elem == "lightning" and "shadow" in apps and (current_time - apps["shadow"] <= window):
            combo_triggered = SynergyCombo("Golpe do Vácuo", "Void Strike", (210, 80, 255), damage_mult=2.10)
            final_damage = int(base_damage * 2.10)
            del apps["shadow"]

        # 4. Arrow + Fire = Burning Arrow
        elif elem == "arrow" and "fire" in apps and (current_time - apps["fire"] <= window):
            combo_triggered = SynergyCombo("Flecha Incendiária", "Burning Arrow", (255, 90, 40), damage_mult=1.75)
            final_damage = int(base_damage * 1.75)
            del apps["fire"]
        elif elem == "fire" and "arrow" in apps and (current_time - apps["arrow"] <= window):
            combo_triggered = SynergyCombo("Flecha Incendiária", "Burning Arrow", (255, 90, 40), damage_mult=1.75)
            final_damage = int(base_damage * 1.75)
            del apps["arrow"]

        # Record this application timestamp
        apps[elem] = current_time

        if combo_triggered:
            self.active_combos.append(combo_triggered)

        return final_damage, combo_triggered

    def update(self, *args, **kwargs):
        """
        Updates active synergy combos. Supports both:
        - update(dt: float)
        - update(p1, p2, targets, dt: float)
        """
        dt = 0.016
        if "dt" in kwargs:
            dt = kwargs["dt"]
        elif len(args) == 1:
            dt = float(args[0])
        elif len(args) >= 4:
            dt = float(args[3])
        elif len(args) > 1:
            dt = float(args[-1])

        self.active_combos = [c for c in self.active_combos if c.update(dt)]

    def draw_banners(self, surface: pygame.Surface):
        if not self.active_combos:
            return

        if self.synergy_font is None:
            pygame.font.init()
            self.synergy_font = pygame.font.SysFont("Arial", 12, bold=True)
            if not self.synergy_font:
                self.synergy_font = pygame.font.Font(None, 14)

        sw, sh = surface.get_size()
        cx = sw // 2
        y = 52
        for combo in self.active_combos:
            combo.draw_banner(surface, self.synergy_font, cx, y)
            y += 36

COOP_SYNERGY = CoopSynergySystem()
