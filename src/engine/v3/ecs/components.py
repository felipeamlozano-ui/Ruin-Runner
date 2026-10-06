"""
Ruin Engine V3.0 — Decoupled Entity Component System (ECS) Data Components.
Pure data containers with zero mixed logic, fully type-annotated.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Any, Dict
import pygame

@dataclass
class TransformComponent:
    x: float = 0.0
    y: float = 0.0
    rotation: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0

@dataclass
class PhysicsComponent:
    vx: float = 0.0
    vy: float = 0.0
    ax: float = 0.0
    ay: float = 0.0
    mass: float = 1.0
    friction: float = 0.85
    gravity: float = 980.0
    on_ground: bool = False

@dataclass
class AnimationComponent:
    current_anim: str = "idle"
    frame_index: int = 0
    frame_time: float = 0.0
    frame_duration: float = 0.1
    flip_x: bool = False
    finished: bool = False

@dataclass
class HealthComponent:
    current_hp: float = 100.0
    max_hp: float = 100.0
    invulnerable_timer: float = 0.0

@dataclass
class ManaComponent:
    current_mp: float = 100.0
    max_mp: float = 100.0
    regen_rate: float = 5.0

@dataclass
class StaminaComponent:
    current_stamina: float = 100.0
    max_stamina: float = 100.0
    regen_rate: float = 15.0

@dataclass
class LightSourceComponent:
    radius: int = 60
    color: Tuple[int, int, int] = (255, 200, 100)
    intensity: float = 1.0
    flicker: bool = False
    flicker_speed: float = 6.0
    flicker_phase: float = 0.0

@dataclass
class ShadowCasterComponent:
    occlusion_points: List[Tuple[float, float]] = field(default_factory=list)
    cast_soft_shadow: bool = True
    opacity: float = 0.85

@dataclass
class ParticleEmitterComponent:
    emitter_type: str = "dust"  # dust, blood, sparks, smoke, magic, embers
    rate: float = 10.0          # particles per second
    accumulator: float = 0.0
    active: bool = True
    color: Tuple[int, int, int] = (255, 120, 40)

@dataclass
class HitboxComponent:
    offset_x: float = 0.0
    offset_y: float = 0.0
    width: float = 32.0
    height: float = 32.0
    damage: float = 10.0
    knockback: float = 150.0
    active: bool = False

@dataclass
class HurtboxComponent:
    offset_x: float = 0.0
    offset_y: float = 0.0
    width: float = 32.0
    height: float = 32.0
    is_invulnerable: bool = False

@dataclass
class ColliderComponent:
    offset_x: float = 0.0
    offset_y: float = 0.0
    width: float = 32.0
    height: float = 32.0
    is_solid: bool = True
    is_trigger: bool = False

@dataclass
class CameraTargetComponent:
    priority: int = 10
    weight: float = 1.0
    deadzone_w: float = 40.0
    deadzone_h: float = 30.0

@dataclass
class ProjectileComponent:
    speed: float = 300.0
    direction_x: float = 1.0
    direction_y: float = 0.0
    piercing: bool = False
    lifetime: float = 3.0
    max_range: float = 800.0
    traveled: float = 0.0

@dataclass
class WeaponComponent:
    name: str = "Iron Sword"
    base_damage: float = 25.0
    attack_speed: float = 1.2
    reach: float = 45.0
    weapon_type: str = "slash"

@dataclass
class StateMachineComponent:
    current_state: str = "idle"
    previous_state: str = "none"
    state_timer: float = 0.0

@dataclass
class EnemyAIComponent:
    state: str = "patrol"  # patrol, chase, attack, hurt, dead
    target_entity_id: Optional[int] = None
    aggro_radius: float = 220.0
    patrol_origin_x: float = 0.0
    patrol_distance: float = 150.0
    attack_cooldown: float = 1.5
    current_cooldown: float = 0.0

@dataclass
class LootDropComponent:
    item_type: str = "potion"
    drop_chance: float = 0.75
    collected: bool = False
    value: int = 25
