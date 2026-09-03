"""
Character Profiles and Data Registry for Ruin Runner.
Defines playable character archetypes, stats, skill configurations,
and animation mappings for Mages, Martial Artists, and Warriors.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List
import os

@dataclass
class SkillData:
    name: str
    key_hint: str
    cost_type: str # "SP", "MP", "FREE"
    cost_value: int
    damage: int
    desc: str
    icon_file: str
    projectile_type: str = ""

    @property
    def description(self) -> str:
        return self.desc

@dataclass
class CharacterProfile:
    id: str
    name: str
    title: str
    archetype: str # "warrior", "mage", "shinobi", "samurai", "fighter"
    gender: str # "female", "male"
    description: str
    color_theme: tuple[int, int, int]
    
    # Base Stats
    hp_max: int = 20
    mp_max: int = 100
    sp_max: int = 100
    mana_regen: float = 2.5
    stamina_regen: float = 14.0
    move_speed: float = 220.0
    dash_speed: float = 750.0
    jump_speed: float = -420.0
    
    # Stat Ratings (1 to 5 stars for UI)
    stats: Dict[str, int] = field(default_factory=lambda: {
        "hp": 3, "mp": 3, "sp": 3, "damage": 3, "speed": 3, "difficulty": 2
    })
    
    # Skills info
    skills: Dict[str, SkillData] = field(default_factory=dict)
    
    # Sprite & Animation setup
    sprite_type: str = "folder" # "folder" for Shaia, "craftpix" for 128x128 sheets
    base_folder: str = ""
    frame_size: tuple[int, int] = (128, 128)
    sprite_scale: float = 0.95
    ground_offset_y: int = 0
    hitbox_size: tuple[int, int] = (32, 80)


CHARACTER_REGISTRY: Dict[str, CharacterProfile] = {
    # 1. SHAIA - Guerreira Valquíria
    "shaia": CharacterProfile(
        id="shaia",
        name="Shaia",
        title="Guerreira Valquíria",
        archetype="warrior",
        gender="female",
        description="Guerreira lendária das ruínas antigas. Especialista em combate corpo a corpo, escudos divinos e cortes fulminantes.",
        color_theme=(255, 215, 80),
        hp_max=20,
        mp_max=100,
        sp_max=100,
        mana_regen=2.5,
        stamina_regen=14.0,
        move_speed=220.0,
        dash_speed=750.0,
        stats={"hp": 5, "mp": 3, "sp": 4, "damage": 4, "speed": 3, "difficulty": 2},
        sprite_type="folder",
        base_folder=os.path.join("assets", "sprites", "shaia"),
        frame_size=(332, 332),
        sprite_scale=0.5,
        ground_offset_y=7,
        skills={
            "j": SkillData("Corte de Espada", "[J]", "SP", 8, 2, "Corte com lâmina afiada.", "human_combat_01.png"),
            "k": SkillData("Bola de Fogo", "[K]", "MP", 50, 6, "Projétil de fogo que perfura defesas.", "demon_magic_01.png", projectile_type="fireball"),
            "e": SkillData("Turbilhão Sagrado", "[E]", "MP", 35, 5, "Giro devastador em 360 graus.", "human_support_02.png"),
            "shift": SkillData("Escudo Divino", "[Shift]", "SP/s", 8, 0, "Bloqueia 100% dos ataques frontais.", "human_defense_07.png"),
            "r": SkillData("Corte Celestial (Ultimate)", "[R]", "MP", 100, 80, "Rasga o espaço em múltiplos cortes com dano massivo.", "demon_combat_12.png")
        }
    ),

    # 2. LUNARIA - Maga Arcana do Grimório (Girl 1)
    "lunaria": CharacterProfile(
        id="lunaria",
        name="Lunaria",
        title="Maga Arcana do Grimório",
        archetype="mage",
        gender="female",
        description="Erudita das artes místicas proibidas. Canaliza runas cósmicas e feitiços astrais diretamente de seu tomo ancestral.",
        color_theme=(130, 180, 255),
        hp_max=16,
        mp_max=160,
        sp_max=80,
        mana_regen=5.5,
        stamina_regen=12.0,
        move_speed=210.0,
        dash_speed=720.0,
        stats={"hp": 3, "mp": 5, "sp": 2, "damage": 5, "speed": 3, "difficulty": 3},
        sprite_type="craftpix",
        base_folder=os.path.join("assets", "sprites", "characters", "mages", "girl_1"),
        frame_size=(128, 128),
        sprite_scale=0.98,
        ground_offset_y=4,
        skills={
            "j": SkillData("Disparo Arcano", "[J]", "MP", 4, 3, "Tiro de energia cósmica rápida à distância.", "arcane_combat_01.png", projectile_type="arcane_bolt"),
            "k": SkillData("Esfera Estelar", "[K]", "MP", 35, 7, "Esfera de pura mana comprimida que explode no alvo.", "arcane_magic_06.png", projectile_type="arcane_sphere"),
            "e": SkillData("Onda Astral", "[E]", "MP", 40, 6, "Canaliza o grimório criando um vórtice estelar.", "arcane_support_08.png"),
            "shift": SkillData("Barreira Rúnica", "[Shift]", "MP/s", 12, 0, "Cúpula de magia pura que dissipa projéteis e golpes.", "arcane_defense_01.png"),
            "r": SkillData("Supernova Arcana (Ultimate)", "[R]", "MP", 160, 95, "Invoca um colapso cósmico limpando a tela inteira.", "arcane_magic_06.png")
        }
    ),

    # 3. IGNIS - Piro-mante das Chamas (Girl 2)
    "ignis": CharacterProfile(
        id="ignis",
        name="Ignis",
        title="Piro-mante do Fogo Sagrado",
        archetype="mage",
        gender="female",
        description="Mestrona da combustão e do fogo elemental. Seus feitiços incendeiam o campo de batalha com dano devastador.",
        color_theme=(255, 120, 40),
        hp_max=18,
        mp_max=140,
        sp_max=85,
        mana_regen=4.8,
        stamina_regen=13.0,
        move_speed=215.0,
        dash_speed=740.0,
        stats={"hp": 3, "mp": 5, "sp": 3, "damage": 5, "speed": 4, "difficulty": 2},
        sprite_type="craftpix",
        base_folder=os.path.join("assets", "sprites", "characters", "mages", "girl_2"),
        frame_size=(128, 128),
        sprite_scale=0.98,
        ground_offset_y=4,
        skills={
            "j": SkillData("Chama Elemental", "[J]", "MP", 4, 3, "Rajada de brasas perfurantes.", "demon_combat_12.png", projectile_type="fire_spark"),
            "k": SkillData("Grande Labareda", "[K]", "MP", 40, 8, "Meteoro ígneo concentrado de alto impacto.", "demon_magic_01.png", projectile_type="fire_sphere"),
            "e": SkillData("Pilar de Chamas", "[E]", "MP", 35, 6, "Erupção de fogo vertical ao redor da conjuradora.", "demon_support_04.png"),
            "shift": SkillData("Manto de Cinzas", "[Shift]", "MP/s", 10, 0, "Escudo incandescente que absorve ataques frontais.", "demon_defense_03.png"),
            "r": SkillData("Inferno Devastador (Ultimate)", "[R]", "MP", 140, 90, "Detona uma tempestade de fogo e magma celestial.", "demon_magic_01.png")
        }
    ),

    # 4. ASTRA - Maga Celeste & Gelo (Girl 3)
    "astra": CharacterProfile(
        id="astra",
        name="Astra",
        title="Sacerdotisa da Luz e Gelo",
        archetype="mage",
        gender="female",
        description="Canalizadora das constelações árticas. Suas magias de gelo e luz cristalina congelam e controlam os inimigos.",
        color_theme=(140, 240, 255),
        hp_max=17,
        mp_max=150,
        sp_max=80,
        mana_regen=5.0,
        stamina_regen=12.0,
        move_speed=215.0,
        dash_speed=730.0,
        stats={"hp": 3, "mp": 5, "sp": 2, "damage": 4, "speed": 4, "difficulty": 3},
        sprite_type="craftpix",
        base_folder=os.path.join("assets", "sprites", "characters", "mages", "girl_3"),
        frame_size=(128, 128),
        sprite_scale=0.98,
        ground_offset_y=4,
        skills={
            "j": SkillData("Projétil de Cristal", "[J]", "MP", 3, 3, "Cristal de gelo perfurante e luminoso.", "elf_combat_10.png", projectile_type="frost_lance"),
            "k": SkillData("Lança Glacial", "[K]", "MP", 35, 7, "Projétil de gelo maciço que congela e desacelera.", "elf_magic_01.png", projectile_type="frost_orb"),
            "e": SkillData("Nevasca Astral", "[E]", "MP", 35, 5, "Anel giratório de lascas de gelo e luz sagrada.", "elf_support_05.png"),
            "shift": SkillData("Domo de Gelo", "[Shift]", "MP/s", 10, 0, "Cúpula de gelo diamantado impenetrável.", "elf_defense_03.png"),
            "r": SkillData("Glaciação Absoluta (Ultimate)", "[R]", "MP", 150, 85, "Congela o fluxo do tempo e estilhaça a escuridão.", "elf_magic_01.png")
        }
    ),

    # 5. HAYATE - Ninja das Sombras (Shinobi)
    "shinobi": CharacterProfile(
        id="shinobi",
        name="Hayate",
        title="Ninja das Sombras",
        archetype="shinobi",
        gender="male",
        description="Assassino mestre do clã das sombras. Possui velocidade impressionante, acrobacias letais e shurikens afiadas.",
        color_theme=(190, 80, 255),
        hp_max=18,
        mp_max=90,
        sp_max=130,
        mana_regen=3.0,
        stamina_regen=18.0,
        move_speed=260.0,
        dash_speed=860.0,
        stats={"hp": 3, "mp": 3, "sp": 5, "damage": 4, "speed": 5, "difficulty": 4},
        sprite_type="craftpix",
        base_folder=os.path.join("assets", "sprites", "characters", "male", "shinobi"),
        frame_size=(128, 128),
        sprite_scale=0.96,
        ground_offset_y=3,
        skills={
            "j": SkillData("Golpe de Ninjato", "[J]", "SP", 6, 2, "Corte rápido e preciso com adaga ninja.", "darkelf_combat_03.png"),
            "k": SkillData("Shuriken das Sombras", "[K]", "MP", 25, 5, "Dispara shurikens velozes em linha reta.", "darkelf_magic_11.png", projectile_type="shuriken"),
            "e": SkillData("Dança das Lâminas", "[E]", "SP", 25, 6, "Sequência acrobática de cortes giratórios.", "darkelf_support_03.png"),
            "shift": SkillData("Técnica de Substituição", "[Shift]", "SP/s", 10, 0, "Guarda evasiva com fumaça e finta corporal.", "darkelf_defense_04.png"),
            "r": SkillData("Tempestade Sombria (Ultimate)", "[R]", "MP", 90, 85, "Desaparece e fatia a tela com dezenas de cortes assassinos.", "darkelf_combat_03.png")
        }
    ),

    # 6. KENSHIN - Mestre Espadachim Ronin (Samurai)
    "samurai": CharacterProfile(
        id="samurai",
        name="Kenshin",
        title="Mestre Espadachim Ronin",
        archetype="samurai",
        gender="male",
        description="Andarilho do caminho da lâmina. Mestre na arte do iaijutsu e cortes de vento, fatiando aço com sua katana.",
        color_theme=(255, 70, 70),
        hp_max=22,
        mp_max=90,
        sp_max=115,
        mana_regen=2.8,
        stamina_regen=15.0,
        move_speed=230.0,
        dash_speed=780.0,
        stats={"hp": 4, "mp": 3, "sp": 4, "damage": 5, "speed": 4, "difficulty": 3},
        sprite_type="craftpix",
        base_folder=os.path.join("assets", "sprites", "characters", "male", "samurai"),
        frame_size=(128, 128),
        sprite_scale=0.96,
        ground_offset_y=3,
        skills={
            "j": SkillData("Combo de Katana", "[J]", "SP", 8, 3, "Tríade de cortes limpos com a lâmina curva.", "human_combat_01.png"),
            "k": SkillData("Corte de Vento", "[K]", "MP", 35, 6, "Dispara um vácuo cortante que corta à distância.", "human_magic_03.png", projectile_type="vacuum_slash"),
            "e": SkillData("Iaijutsu Giratório", "[E]", "SP", 28, 6, "Saque ultrarrápido com repulsão circular.", "human_support_02.png"),
            "shift": SkillData("Postura de Contra-Ataque", "[Shift]", "SP/s", 8, 0, "Defesa perfeita com a lâmina da katana.", "human_defense_07.png"),
            "r": SkillData("Dança da Cerejeira (Ultimate)", "[R]", "MP", 90, 88, "Bainha reluzente e corte supremo que parte o horizonte.", "demon_combat_12.png")
        }
    ),

    # 7. RYUU - Monge Lutador / Brawler (Fighter)
    "fighter": CharacterProfile(
        id="fighter",
        name="Ryuu",
        title="Monge do Punho de Ferro",
        archetype="fighter",
        gender="male",
        description="Guerreiro marcial que domina a energia espiritual Ki. Seus punhos quebram rochas e sua determinação é inabalável.",
        color_theme=(255, 170, 40),
        hp_max=24,
        mp_max=100,
        sp_max=120,
        mana_regen=3.0,
        stamina_regen=16.0,
        move_speed=235.0,
        dash_speed=800.0,
        stats={"hp": 5, "mp": 3, "sp": 4, "damage": 5, "speed": 4, "difficulty": 2},
        sprite_type="craftpix",
        base_folder=os.path.join("assets", "sprites", "characters", "male", "fighter"),
        frame_size=(128, 128),
        sprite_scale=0.96,
        ground_offset_y=3,
        skills={
            "j": SkillData("Golpes Marciais", "[J]", "SP", 7, 3, "Sequência pesada de socos e cotoveladas.", "dwarf_combat_01.png"),
            "k": SkillData("Onda de Ki", "[K]", "MP", 30, 6, "Dispara uma esfera compacta de energia espiritual.", "dwarf_magic_05.png", projectile_type="ki_blast"),
            "e": SkillData("Chute do Dragão", "[E]", "SP", 24, 6, "Chute aéreo giratório com onda de impacto.", "dwarf_support_08.png"),
            "shift": SkillData("Corpo de Ferro", "[Shift]", "SP/s", 8, 0, "Enrijece os músculos bloqueando dano frontal.", "dwarf_defense_10.png"),
            "r": SkillData("Fúria do Dragão (Ultimate)", "[R]", "MP", 100, 85, "Libera todo o Ki espiritual em uma explosão devastadora.", "demon_combat_12.png")
        }
    )
}

# Ordered list for character selection carousel
CHARACTER_ORDER: List[str] = [
    "shaia",
    "lunaria",
    "ignis",
    "astra",
    "shinobi",
    "samurai",
    "fighter"
]

def get_character_profile(char_id: str) -> CharacterProfile:
    """Safely retrieves character profile or defaults to Shaia."""
    return CHARACTER_REGISTRY.get(char_id.lower(), CHARACTER_REGISTRY["shaia"])
