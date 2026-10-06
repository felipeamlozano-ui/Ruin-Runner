"""
Ruin Engine V3.0 — Dynamic Adaptive Quality Governor.
Automatically adjusts rendering complexity (ray count, particles, blur passes, shadows, volumetric fog)
to sustain target framerate (60 / 90 / 120 FPS) on target Ryzen 5 5500U architecture.
"""

from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class QualityProfile:
    name: str
    ray_multiplier: float
    max_particles: int
    bloom_passes: int
    shadow_softness_rays: int
    volumetric_step: int
    ssao_samples: int
    fsr_scale_factor: float

PRESET_PROFILES: Dict[int, QualityProfile] = {
    0: QualityProfile("Ultra / High-End", ray_multiplier=1.0, max_particles=4000, bloom_passes=3, shadow_softness_rays=8, volumetric_step=4, ssao_samples=16, fsr_scale_factor=1.0),
    1: QualityProfile("Balanced (Ryzen 5500U)", ray_multiplier=0.75, max_particles=2000, bloom_passes=2, shadow_softness_rays=4, volumetric_step=6, ssao_samples=8, fsr_scale_factor=1.0),
    2: QualityProfile("Performance", ray_multiplier=0.5, max_particles=1000, bloom_passes=1, shadow_softness_rays=2, volumetric_step=10, ssao_samples=4, fsr_scale_factor=0.85),
    3: QualityProfile("Ultra Performance", ray_multiplier=0.3, max_particles=500, bloom_passes=1, shadow_softness_rays=1, volumetric_step=16, ssao_samples=2, fsr_scale_factor=0.7)
}

class AdaptiveQualityGovernor:
    """
    Monitors frame budget headroom and dynamically shifts quality profiles without user intervention.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, target_fps: float = 60.0):
        if getattr(self, "_initialized", False):
            return
            
        self.target_fps: float = target_fps
        self.current_tier: int = 1  # Default: Tier 1 (Balanced for Ryzen 5 5500U)
        self.profile: QualityProfile = PRESET_PROFILES[self.current_tier]
        self.auto_tune: bool = True
        
        self.drop_counter: int = 0
        self.recovery_counter: int = 0
        self.hysteresis_threshold: int = 45  # frames below budget before downgrading
        self.recovery_threshold: int = 120   # frames above budget before upgrading
        self._initialized = True

    def update(self, current_fps: float) -> None:
        """Evaluates framerate stability and triggers tier adjustments with hysteresis."""
        if not self.auto_tune:
            return

        fps_ratio = current_fps / max(1.0, self.target_fps)

        if fps_ratio < 0.88:  # Dropping under 53 FPS on a 60 FPS target
            self.drop_counter += 1
            self.recovery_counter = 0
            if self.drop_counter >= self.hysteresis_threshold:
                self.demote_tier()
                self.drop_counter = 0
        elif fps_ratio > 0.98: # Maintaining stable target
            self.recovery_counter += 1
            self.drop_counter = 0
            if self.recovery_counter >= self.recovery_threshold:
                self.promote_tier()
                self.recovery_counter = 0
        else:
            self.drop_counter = max(0, self.drop_counter - 1)
            self.recovery_counter = max(0, self.recovery_counter - 1)

    def demote_tier(self) -> None:
        """Lowers fidelity to protect framerate."""
        if self.current_tier < max(PRESET_PROFILES.keys()):
            self.current_tier += 1
            self.profile = PRESET_PROFILES[self.current_tier]

    def promote_tier(self) -> None:
        """Upgrades fidelity when headroom permits."""
        if self.current_tier > 0:
            self.current_tier -= 1
            self.profile = PRESET_PROFILES[self.current_tier]

    def set_manual_tier(self, tier: int) -> None:
        """Manually sets quality tier and disables auto-tune."""
        self.current_tier = max(0, min(tier, max(PRESET_PROFILES.keys())))
        self.profile = PRESET_PROFILES[self.current_tier]
        self.auto_tune = False

    def get_status(self) -> Dict[str, Any]:
        return {
            "tier": self.current_tier,
            "tier_name": self.profile.name,
            "auto_tune": self.auto_tune,
            "max_particles": self.profile.max_particles,
            "ray_multiplier": self.profile.ray_multiplier,
            "bloom_passes": self.profile.bloom_passes
        }


ADAPTIVE_QUALITY = AdaptiveQualityGovernor()
