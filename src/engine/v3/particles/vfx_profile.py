"""
Ruin Engine V3.0 — Skill VFX Profiles, Budget Manager, and LOD System.
Ensures every character skill, projectile, and attack has an artisanal visual profile
rather than applying uniform heavy bloom or particle floods.
Implements:
- SkillVFXProfile (particles, trail, light, bloom, shake, flash, afterimage)
- VFXPriority (LOW, MEDIUM, HIGH, CRITICAL)
- VFX_LOD (LOD_0 = 100%, LOD_1 = 70%, LOD_2 = 45%, LOD_3 = 20%)
- VFXBudgetManager (Governs particle, light, and VFX budgets under frame pacing pressure)
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Tuple, Optional, Dict

class VFXPriority(Enum):
    LOW = 0       # Ambient dust, falling leaves, tiny sparks
    MEDIUM = 1    # Basic sword slash, footstep dust, hit impact
    HIGH = 2      # Magic projectile, AoE whirlwind, skill cast
    CRITICAL = 3  # Ultimate skills, boss phase transitions, fatal impacts

class VFX_LOD(Enum):
    LOD_0 = 0 # Ultra / Full Fidelity (100% particles & full trails)
    LOD_1 = 1 # High Fidelity (70% particles, medium trails)
    LOD_2 = 2 # Medium Fidelity (45% particles, reduced lights, no afterimages)
    LOD_3 = 3 # Emergency Performance (20% particles, critical VFX only)

@dataclass
class SkillVFXProfile:
    """Artisanal visual specification per attack / skill / entity event."""
    name: str
    priority: VFXPriority = VFXPriority.MEDIUM
    particles_count: int = 15
    particle_type: str = "spark" # "spark", "fire", "blood", "ice", "arcane", "holy", "wind", "earth"
    trail_enabled: bool = False
    light_radius: int = 0
    light_color: Tuple[int, int, int] = (255, 200, 100)
    light_intensity: float = 0.0
    bloom_category: str = "NO_BLOOM" # "NO_BLOOM", "SUBTLE", "EMISSIVE", "HIGH_EMISSIVE", "CINEMATIC"
    camera_shake_trauma: float = 0.0
    screen_flash: bool = False
    flash_color: Tuple[int, int, int] = (255, 255, 255)
    afterimages: bool = False
    color_grade_tint: Optional[Tuple[int, int, int]] = None

    def get_effective_particle_count(self, lod: VFX_LOD) -> int:
        if self.priority == VFXPriority.CRITICAL:
            return self.particles_count
            
        mults = {
            VFX_LOD.LOD_0: 1.0,
            VFX_LOD.LOD_1: 0.70,
            VFX_LOD.LOD_2: 0.45,
            VFX_LOD.LOD_3: 0.20
        }
        return max(0, int(self.particles_count * mults.get(lod, 1.0)))

    def is_light_permitted(self, lod: VFX_LOD) -> bool:
        if self.priority == VFXPriority.CRITICAL:
            return True
        if lod == VFX_LOD.LOD_3:
            return False
        return self.light_radius > 0


# Registry of Predefined Skill VFX Profiles
VFX_PROFILES: Dict[str, SkillVFXProfile] = {
    # 1. Basic Melee Attacks (Zero bloom, subtle light, clean hit impact)
    "basic_slash": SkillVFXProfile(
        name="Basic Melee Slash",
        priority=VFXPriority.MEDIUM,
        particles_count=8,
        particle_type="spark",
        trail_enabled=True,
        light_radius=0,
        bloom_category="NO_BLOOM",
        camera_shake_trauma=0.08
    ),
    
    # 2. Fire Magic Skills (Emissive bloom, warm light, embers)
    "fireball": SkillVFXProfile(
        name="Fireball Projectile",
        priority=VFXPriority.HIGH,
        particles_count=35,
        particle_type="fire",
        trail_enabled=True,
        light_radius=85,
        light_color=(255, 140, 40),
        light_intensity=0.85,
        bloom_category="EMISSIVE",
        camera_shake_trauma=0.15
    ),

    # 3. Frost / Ice Magic Skills (Subtle crystalline glint, cold cyan light)
    "frost_lance": SkillVFXProfile(
        name="Frost Lance",
        priority=VFXPriority.HIGH,
        particles_count=25,
        particle_type="ice",
        trail_enabled=True,
        light_radius=70,
        light_color=(120, 230, 255),
        light_intensity=0.75,
        bloom_category="SUBTLE",
        camera_shake_trauma=0.12
    ),

    # 4. Holy / Healing Skills (Radiant golden bloom, healing shimmer)
    "holy_heal": SkillVFXProfile(
        name="Holy Blessing & Healing",
        priority=VFXPriority.HIGH,
        particles_count=30,
        particle_type="holy",
        trail_enabled=False,
        light_radius=110,
        light_color=(255, 240, 140),
        light_intensity=0.90,
        bloom_category="EMISSIVE",
        camera_shake_trauma=0.05
    ),

    # 5. Wind / Archer Arrows (Fast, high-velocity streak, low bloom)
    "wind_arrow": SkillVFXProfile(
        name="Wind Arrow Shot",
        priority=VFXPriority.MEDIUM,
        particles_count=12,
        particle_type="wind",
        trail_enabled=True,
        light_radius=40,
        light_color=(160, 240, 180),
        light_intensity=0.45,
        bloom_category="SUBTLE",
        camera_shake_trauma=0.10
    ),

    # 6. Seismic Hammer / Earth Stun (Heavy impact dust, high trauma shake, zero bloom)
    "seismic_slam": SkillVFXProfile(
        name="Seismic Hammer Slam",
        priority=VFXPriority.HIGH,
        particles_count=45,
        particle_type="earth",
        trail_enabled=False,
        light_radius=60,
        light_color=(255, 180, 80),
        light_intensity=0.50,
        bloom_category="NO_BLOOM",
        camera_shake_trauma=0.45
    ),

    # 7. Ultimate Abilities (High Emissive bloom, screen flash, cinematic trauma)
    "ultimate_cinematic": SkillVFXProfile(
        name="Ultimate Dimensional Strike",
        priority=VFXPriority.CRITICAL,
        particles_count=120,
        particle_type="arcane",
        trail_enabled=True,
        light_radius=220,
        light_color=(255, 245, 180),
        light_intensity=1.5,
        bloom_category="HIGH_EMISSIVE",
        camera_shake_trauma=0.75,
        screen_flash=True,
        afterimages=True
    )
}

class VFXBudgetManager:
    """
    Monitors frame time and particle / light counts, dynamically setting VFX_LOD
    to preserve 60 FPS frame pacing on AMD Vega hardware.
    """
    def __init__(self, target_fps: float = 60.0, max_particles: int = 2500):
        self.target_frametime_ms = 1000.0 / target_fps
        self.current_lod = VFX_LOD.LOD_0
        self.max_particles_budget = max_particles
        self.max_dynamic_lights = 8
        self.active_particles = 0
        self.active_lights = 0
        self.current_particle_count = 0

    def get_lod(self, profile: SkillVFXProfile) -> VFX_LOD:
        if profile.priority == VFXPriority.CRITICAL:
            return VFX_LOD.LOD_0
        if self.current_particle_count >= self.max_particles_budget * 0.9:
            return VFX_LOD.LOD_3
        elif self.current_particle_count >= self.max_particles_budget * 0.7:
            return VFX_LOD.LOD_2
        elif self.current_particle_count >= self.max_particles_budget * 0.5:
            return VFX_LOD.LOD_1
        return self.current_lod

    def request_vfx(self, profile: SkillVFXProfile, count: int = 1) -> bool:
        if profile.priority == VFXPriority.CRITICAL:
            return True
        if self.current_particle_count + count > self.max_particles_budget:
            return False
        return True

    def evaluate_frame_pacing(self, frametime_ms: float) -> VFX_LOD:
        """Dynamically adjusts LOD based on frame latency hysteresis."""
        budget = self.target_frametime_ms
        if frametime_ms > budget * 1.15:
            # Over budget: elevate LOD level to reduce load
            if self.current_lod == VFX_LOD.LOD_0:
                self.current_lod = VFX_LOD.LOD_1
            elif self.current_lod == VFX_LOD.LOD_1:
                self.current_lod = VFX_LOD.LOD_2
            elif self.current_lod == VFX_LOD.LOD_2:
                self.current_lod = VFX_LOD.LOD_3
        elif frametime_ms < budget * 0.80:
            # Plentiful headroom: restore higher visual fidelity
            if self.current_lod == VFX_LOD.LOD_3:
                self.current_lod = VFX_LOD.LOD_2
            elif self.current_lod == VFX_LOD.LOD_2:
                self.current_lod = VFX_LOD.LOD_1
            elif self.current_lod == VFX_LOD.LOD_1:
                self.current_lod = VFX_LOD.LOD_0
                
        return self.current_lod

VFX_BUDGET = VFXBudgetManager()
