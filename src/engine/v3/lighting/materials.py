"""
Ruin Engine V3.0 — 2D Physical Material System.
Defines physical interaction properties for 2D surfaces, props, characters, and environment:
STONE, WOOD, METAL, MAGIC, FIRE, ICE, FLESH, BONE, WATER, LAVA, EMISSIVE.
Properties:
- roughness: Surface micro-facet roughness (diffuse scattering vs sharp reflection)
- emission: Intrinsic luminous flux emitted by the material
- normal_intensity: Normal map bump extrusion weight
- light_response: Direct photon reflectance
- specular_power: Shininess specular power exponent
- bloom_category: NO_BLOOM, SUBTLE, EMISSIVE, HIGH_EMISSIVE, CINEMATIC
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Tuple, Dict

class MaterialType(Enum):
    STONE = "stone"
    WOOD = "wood"
    METAL = "metal"
    MAGIC = "magic"
    FIRE = "fire"
    ICE = "ice"
    FLESH = "flesh"
    BONE = "bone"
    WATER = "water"
    LAVA = "lava"
    EMISSIVE = "emissive"

@dataclass(frozen=True)
class Material2D:
    name: str
    material_type: MaterialType
    roughness: float = 0.85
    emission: float = 0.0
    normal_intensity: float = 1.0
    light_response: float = 0.70
    specular_power: float = 8.0
    bloom_category: str = "NO_BLOOM"
    bloom_response: float = 0.0
    tint: Tuple[int, int, int] = (255, 255, 255)

MATERIAL_REGISTRY: Dict[MaterialType, Material2D] = {
    MaterialType.STONE: Material2D(
        name="Stone / Ancient Brick",
        material_type=MaterialType.STONE,
        roughness=0.92,
        emission=0.0,
        normal_intensity=1.2,
        light_response=0.60,
        specular_power=4.0,
        bloom_category="NO_BLOOM"
    ),
    MaterialType.WOOD: Material2D(
        name="Weathered Wood",
        material_type=MaterialType.WOOD,
        roughness=0.88,
        emission=0.0,
        normal_intensity=0.8,
        light_response=0.65,
        specular_power=6.0,
        bloom_category="NO_BLOOM"
    ),
    MaterialType.METAL: Material2D(
        name="Tempered Steel / Armor",
        material_type=MaterialType.METAL,
        roughness=0.25,
        emission=0.0,
        normal_intensity=1.1,
        light_response=0.95,
        specular_power=64.0,
        bloom_category="SUBTLE"
    ),
    MaterialType.MAGIC: Material2D(
        name="Arcane Sigil / Ether",
        material_type=MaterialType.MAGIC,
        roughness=0.15,
        emission=1.20,
        normal_intensity=0.4,
        light_response=1.00,
        specular_power=32.0,
        bloom_category="EMISSIVE",
        bloom_response=0.85
    ),
    MaterialType.FIRE: Material2D(
        name="Luminous Combustion / Flame",
        material_type=MaterialType.FIRE,
        roughness=0.10,
        emission=1.60,
        normal_intensity=0.0,
        light_response=1.00,
        specular_power=16.0,
        bloom_category="EMISSIVE",
        bloom_response=0.95
    ),
    MaterialType.ICE: Material2D(
        name="Glacial Crystal",
        material_type=MaterialType.ICE,
        roughness=0.18,
        emission=0.25,
        normal_intensity=1.3,
        light_response=0.92,
        specular_power=48.0,
        bloom_category="SUBTLE"
    ),
    MaterialType.FLESH: Material2D(
        name="Living Flesh / Skin",
        material_type=MaterialType.FLESH,
        roughness=0.80,
        emission=0.0,
        normal_intensity=0.6,
        light_response=0.75,
        specular_power=8.0,
        bloom_category="NO_BLOOM"
    ),
    MaterialType.BONE: Material2D(
        name="Ancient Bone / Skeleton",
        material_type=MaterialType.BONE,
        roughness=0.75,
        emission=0.0,
        normal_intensity=0.9,
        light_response=0.70,
        specular_power=12.0,
        bloom_category="NO_BLOOM"
    ),
    MaterialType.WATER: Material2D(
        name="Dynamic Fluid Water",
        material_type=MaterialType.WATER,
        roughness=0.12,
        emission=0.10,
        normal_intensity=1.4,
        light_response=0.90,
        specular_power=64.0,
        bloom_category="SUBTLE"
    ),
    MaterialType.LAVA: Material2D(
        name="Molten Magma Fissure",
        material_type=MaterialType.LAVA,
        roughness=0.30,
        emission=1.85,
        normal_intensity=0.5,
        light_response=1.00,
        specular_power=20.0,
        bloom_category="HIGH_EMISSIVE"
    ),
    MaterialType.EMISSIVE: Material2D(
        name="High-Luminance Ultimate Burst",
        material_type=MaterialType.EMISSIVE,
        roughness=0.05,
        emission=2.00,
        normal_intensity=0.0,
        light_response=1.00,
        specular_power=128.0,
        bloom_category="HIGH_EMISSIVE"
    )
}

def get_material(mat_type: MaterialType) -> Material2D:
    return MATERIAL_REGISTRY.get(mat_type, MATERIAL_REGISTRY[MaterialType.STONE])
