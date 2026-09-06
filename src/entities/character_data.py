"""
Character Profiles and Data Registry for Ruin Runner.
Defines playable character archetypes, asymmetric survival stats,
skill configurations, and exclusive passives for Mages, Martial Artists, and Warriors.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List
import os

@dataclass
class SkillData:
    name: str
    key_hint: str
    cost_type: str # "SP", "MP", "FREE", "SP/s", "MP/s"
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
    
    # Asymmetric Survival Stats
    hp_max: int = 130
    mp_max: int = 70
    sp_max: int = 120
    mana_regen: float = 1.5
    stamina_regen: float = 20.0
    move_speed: float = 145.0
    dash_speed: float = 340.0
    jump_speed: float = -350.0
    
    # Exclusive Passive Skill
    passive_id: str = ""
    passive_name: str = ""
    passive_desc: str = ""
    
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
        description="Guerreira lendária das ruínas antigas. Especialista em combate corpo a corpo e sustentação na vanguarda.",
        color_theme=(255, 215, 80),
        hp_max=150,        # Tank pesada: mais HP que todos
        mp_max=70,         # Pouca mana
        sp_max=110,        # Estamina sólida
        mana_regen=1.2,
        stamina_regen=18.0,
        move_speed=140.0,  # Mais lenta, é tanque
        dash_speed=320.0,
        jump_speed=-340.0,
        passive_id="shaia_battle_thirst",
        passive_name="Sede de Batalha",
        passive_desc="Golpes corpo a corpo bem-sucedidos restauram +1 HP e +2 MP.",
        stats={"hp": 5, "mp": 1, "sp": 4, "damage": 4, "speed": 2, "difficulty": 1},
        sprite_type="folder",
        base_folder=os.path.join("assets", "sprites", "shaia"),
        frame_size=(332, 332),
        sprite_scale=0.58,
        ground_offset_y=6,
        skills={
            "j": SkillData("Corte de Espada", "[J]", "SP", 8, 75, "Corte pesado de lâmina afiada.", "human_combat_01.png"),
            "k": SkillData("Bola de Fogo", "[K]", "MP", 35, 1050, "Projétil de fogo concentrado de alto impacto.", "demon_magic_01.png", projectile_type="fireball"),
            "e": SkillData("Turbilhão Sagrado", "[E]", "MP", 40, 1200, "Giro devastador em 360 graus com lâminas sagradas.", "human_support_02.png"),
            "shift": SkillData("Escudo Divino", "[Shift]", "SP/s", 3, 0, "Bloqueia 100% dos ataques frontais (drena 3 SP/s).", "human_defense_07.png"),
            "r": SkillData("Corte Celestial (Ultimate)", "[R]", "MP", 70, 6000, "Rasga o espaço desferindo dano colossal (6.000 Dmg).", "demon_combat_12.png")
        }
    ),

    # 2. LUNARIA - Maga Arcana do Grimório (Glass Cannon Cósmica: Máxima Mana e Dano de Magia)
    "lunaria": CharacterProfile(
        id="lunaria",
        name="Lunaria",
        title="Maga Arcana do Grimório",
        archetype="mage",
        gender="female",
        description="Erudita das artes místicas proibidas. Canaliza feitiços astrais de imenso poder, porém extremamente frágil fisicamente.",
        color_theme=(130, 180, 255),
        hp_max=65,
        mp_max=160,
        sp_max=75,
        mana_regen=4.0,
        stamina_regen=18.0,
        move_speed=135.0,
        dash_speed=325.0,
        jump_speed=-350.0,
        passive_id="lunaria_arcane_resonance",
        passive_name="Ressonância Arcana",
        passive_desc="A regeneração de MP dobra ao ficar 2.0s sem se mover e sem atacar.",
        stats={"hp": 1, "mp": 5, "sp": 2, "damage": 5, "speed": 3, "difficulty": 4},
        sprite_type="craftpix",
        base_folder=os.path.join("assets", "sprites", "characters", "mages", "girl_1"),
        frame_size=(128, 128),
        sprite_scale=1.08,
        ground_offset_y=4,
        skills={
            "j": SkillData("Disparo Arcano", "[J]", "MP", 3, 45, "Tiro de energia cósmica rápida à distância.", "arcane_combat_01.png", projectile_type="arcane_bolt"),
            "k": SkillData("Esfera Estelar", "[K]", "MP", 35, 1500, "Esfera cósmica de pura destruição mágica comprimida.", "arcane_magic_06.png", projectile_type="arcane_sphere"),
            "e": SkillData("Onda Astral", "[E]", "MP", 30, 1050, "Canaliza o grimório criando um vórtice estelar repulsor.", "arcane_support_08.png"),
            "shift": SkillData("Barreira Rúnica", "[Shift]", "MP/s", 3, 0, "Cúpula mágica que dissipa projéteis e golpes (3 MP/s).", "arcane_defense_01.png"),
            "r": SkillData("Supernova Arcana (Ultimate)", "[R]", "MP", 160, 7500, "Invoca um colapso cósmico devastando a tela inteira.", "arcane_magic_06.png")
        }
    ),

    # 3. IGNIS - Piro-mante das Chamas (Maga Ofensiva Rápida: Alta Mobilidade e Agilidade)
    "ignis": CharacterProfile(
        id="ignis",
        name="Ignis",
        title="Piro-mante do Fogo Sagrado",
        archetype="mage",
        gender="female",
        description="Mestrona da combustão elemental. Seus feitiços incendeiam o campo de batalha com dano explosivo e queimadura contínua.",
        color_theme=(255, 120, 40),
        hp_max=75,
        mp_max=130,
        sp_max=90,
        mana_regen=3.2,
        stamina_regen=22.0,
        move_speed=148.0,
        dash_speed=350.0,
        jump_speed=-350.0,
        passive_id="ignis_smoldering_ashes",
        passive_name="Cinzas Fumegantes",
        passive_desc="A Magia [K] aplica queimadura de 3 dano/s durante 4 segundos.",
        stats={"hp": 2, "mp": 4, "sp": 3, "damage": 5, "speed": 4, "difficulty": 3},
        sprite_type="craftpix",
        base_folder=os.path.join("assets", "sprites", "characters", "mages", "girl_2"),
        frame_size=(128, 128),
        sprite_scale=1.08,
        ground_offset_y=4,
        skills={
            "j": SkillData("Chama Elemental", "[J]", "MP", 3, 51, "Rajada de brasas perfurantes rápida.", "demon_combat_12.png", projectile_type="fire_spark"),
            "k": SkillData("Grande Labareda", "[K]", "MP", 35, 900, "Meteoro ígneo concentrado que incendeia inimigos.", "demon_magic_01.png", projectile_type="fire_sphere"),
            "e": SkillData("Pilar de Chamas", "[E]", "MP", 40, 975, "Erupção de fogo vertical maciça ao redor da conjuradora.", "demon_support_04.png"),
            "shift": SkillData("Manto de Cinzas", "[Shift]", "MP/s", 3, 0, "Escudo incandescente de absorção frontal (3 MP/s).", "demon_defense_03.png"),
            "r": SkillData("Inferno Devastador (Ultimate)", "[R]", "MP", 130, 10500, "Detona uma tempestade de fogo e magma celestial.", "demon_magic_01.png")
        }
    ),

    # 4. ASTRA - Sacerdotisa da Luz e Gelo (Maga Protetora Resistente: Maior Vitalidade e Estamina)
    "astra": CharacterProfile(
        id="astra",
        name="Astra",
        title="Sacerdotisa da Luz e Gelo",
        archetype="mage",
        gender="female",
        description="Canalizadora das constelações árticas. Possui proteção estelar defensiva que previne fatalidades imediatas.",
        color_theme=(140, 240, 255),
        hp_max=90,
        mp_max=120,
        sp_max=100,
        mana_regen=3.0,
        stamina_regen=24.0,
        move_speed=142.0,
        dash_speed=335.0,
        jump_speed=-350.0,
        passive_id="astra_celestial_barrier",
        passive_name="Barreira Celestial",
        passive_desc="Escudo automático que anula 100% do dano de 1 ataque a cada 20s.",
        stats={"hp": 3, "mp": 4, "sp": 4, "damage": 4, "speed": 3, "difficulty": 2},
        sprite_type="craftpix",
        base_folder=os.path.join("assets", "sprites", "characters", "mages", "girl_3"),
        frame_size=(128, 128),
        sprite_scale=1.08,
        ground_offset_y=4,
        skills={
            "j": SkillData("Projétil de Cristal", "[J]", "MP", 3, 42, "Cristal de gelo perfurante e luminoso.", "elf_combat_10.png", projectile_type="frost_lance"),
            "k": SkillData("Lança Glacial", "[K]", "MP", 70, 1500, "Projétil de gelo maciço de penetração devastadora.", "elf_magic_01.png", projectile_type="frost_orb"),
            "e": SkillData("Nevasca Astral", "[E]", "MP", 60, 1200, "Anel giratório cortante de lascas de gelo sagrado.", "elf_support_05.png"),
            "shift": SkillData("Domo de Gelo", "[Shift]", "MP/s", 3, 0, "Cúpula de gelo diamantado impenetrável (3 MP/s).", "elf_defense_03.png"),
            "r": SkillData("Glaciação Absoluta (Ultimate)", "[R]", "MP", 120, 9000, "Congela o fluxo do tempo e estilhaça a escuridão.", "elf_magic_01.png")
        }
    ),

    # 5. HAYATE - Ninja das Sombras (Shinobi)
    "shinobi": CharacterProfile(
        id="shinobi",
        name="Hayate",
        title="Ninja das Sombras",
        archetype="shinobi",
        gender="male",
        description="Assassino mestre do clã das sombras. Especialista em esquivas ultrarrápidas de baixo custo e alta mobilidade.",
        color_theme=(190, 80, 255),
        hp_max=100,
        mp_max=90,
        sp_max=140,
        mana_regen=1.8,
        stamina_regen=22.0,
        move_speed=165.0,
        dash_speed=390.0,
        jump_speed=-350.0,
        passive_id="shinobi_shadow_step",
        passive_name="Passos de Sombra",
        passive_desc="A esquiva [Q] consome apenas 15 SP e avança 20% mais longe.",
        stats={"hp": 3, "mp": 3, "sp": 5, "damage": 4, "speed": 5, "difficulty": 4},
        sprite_type="craftpix",
        base_folder=os.path.join("assets", "sprites", "characters", "male", "shinobi"),
        frame_size=(128, 128),
        sprite_scale=1.04,
        ground_offset_y=3,
        skills={
            "j": SkillData("Golpe de Ninjato", "[J]", "SP", 6, 54, "Corte rápido e preciso com adaga ninja.", "darkelf_combat_03.png"),
            "k": SkillData("Shuriken das Sombras", "[K]", "MP", 15, 300, "Dispara shurikens letais perfurantes em alta velocidade.", "darkelf_magic_11.png", projectile_type="shuriken"),
            "e": SkillData("Dança das Lâminas", "[E]", "SP", 30, 210, "Sequência acrobática de cortes giratórios com clones.", "darkelf_support_03.png"),
            "shift": SkillData("Técnica de Substituição", "[Shift]", "SP/s", 3, 0, "Guarda evasiva de fumaça e finta corporal (3 SP/s).", "darkelf_defense_04.png"),
            "r": SkillData("Tempestade Sombria (Ultimate)", "[R]", "MP", 90, 8250, "Desaparece fatiando a tela com dezenas de cortes letais (8.250 Dmg).", "darkelf_combat_03.png")
        }
    ),

    # 6. KENSHIN - Mestre Espadachim Ronin (Samurai)
    "samurai": CharacterProfile(
        id="samurai",
        name="Kenshin",
        title="Mestre Espadachim Ronin",
        archetype="samurai",
        gender="male",
        description="Andarilho do caminho da lâmina. Recompensa esquivas perfeitas com contra-ataques imediatos fulminantes.",
        color_theme=(255, 70, 70),
        hp_max=110,        # Resistente mas não tanque
        mp_max=85,         # Mais mana para técnicas especiais
        sp_max=140,        # Alta estamina para esquivas perfeitas
        mana_regen=2.0,
        stamina_regen=25.0, # Regenera estamina mais rápido
        move_speed=158.0,  # Mais veloz que Shaia
        dash_speed=370.0,  # Dash rápido para Iaijutsu
        jump_speed=-360.0,
        passive_id="samurai_perfect_focus",
        passive_name="Foco Perfeito",
        passive_desc="Esquivar no momento exato de um ataque inimigo zera o cooldown do próximo corte.",
        stats={"hp": 3, "mp": 3, "sp": 5, "damage": 5, "speed": 4, "difficulty": 3},
        sprite_type="craftpix",
        base_folder=os.path.join("assets", "sprites", "characters", "male", "samurai"),
        frame_size=(128, 128),
        sprite_scale=1.04,
        ground_offset_y=3,
        skills={
            "j": SkillData("Combo de Katana", "[J]", "SP", 8, 60, "Tríade de cortes limpos com a lâmina curva.", "human_combat_01.png"),
            "k": SkillData("Corte de Vento", "[K]", "MP", 45, 900, "Dispara um vácuo cortante de alta pressão à distância.", "human_magic_03.png", projectile_type="vacuum_slash"),
            "e": SkillData("Iaijutsu Giratório", "[E]", "SP", 30, 150, "Saque ultrarrápido mortal com repulsão circular.", "human_support_02.png"),
            "shift": SkillData("Postura de Contra-Ataque", "[Shift]", "SP/s", 3, 0, "Defesa perfeita com a lâmina da katana (3 SP/s).", "human_defense_07.png"),
            "r": SkillData("Dança da Cerejeira (Ultimate)", "[R]", "MP", 70, 8850, "Bainha reluzente e corte supremo que parte o horizonte (8.850 Dmg).", "demon_combat_12.png")
        }
    ),

    # 7. RYUU - Monge Lutador / Brawler (Fighter)
    "fighter": CharacterProfile(
        id="fighter",
        name="Ryuu",
        title="Monge do Punho de Ferro",
        archetype="fighter",
        gender="male",
        description="Guerreiro marcial do Ki. Sua resistência corporal endurece conforme sua vida diminui.",
        color_theme=(255, 170, 40),
        hp_max=140,        # Corpo robusto mas menos que Shaia
        mp_max=55,         # Menos mana, foco em estamina
        sp_max=130,        # Boa reserva de estamina marcial
        mana_regen=1.0,    # Regen lenta de mana
        stamina_regen=23.0,
        move_speed=152.0,  # Velocidade intermediária
        dash_speed=355.0,
        jump_speed=-355.0, # Salto levemente mais alto
        passive_id="fighter_physical_resilience",
        passive_name="Resiliência Física",
        passive_desc="Sofre 15% a menos de dano quando o HP estiver abaixo de 30%.",
        stats={"hp": 4, "mp": 1, "sp": 4, "damage": 5, "speed": 3, "difficulty": 2},
        sprite_type="craftpix",
        base_folder=os.path.join("assets", "sprites", "characters", "male", "fighter"),
        frame_size=(128, 128),
        sprite_scale=1.04,
        ground_offset_y=3,
        skills={
            "j": SkillData("Golpes Marciais", "[J]", "SP", 7, 63, "Sequência pesada de socos e cotoveladas de impacto.", "dwarf_combat_01.png"),
            "k": SkillData("Onda de Ki", "[K]", "MP", 30, 750, "Dispara uma esfera compacta de energia espiritual pura.", "dwarf_magic_05.png", projectile_type="ki_blast"),
            "e": SkillData("Chute do Dragão", "[E]", "SP", 50, 960, "Chute aéreo giratório com onda de impacto sísmica.", "dwarf_support_08.png"),
            "shift": SkillData("Corpo de Ferro", "[Shift]", "SP/s", 3, 0, "Enrijece os músculos bloqueando dano frontal (3 SP/s).", "dwarf_defense_10.png"),
            "r": SkillData("Fúria do Dragão (Ultimate)", "[R]", "MP", 70, 6900, "Libera todo o Ki espiritual em uma explosão devastadora (6.900 Dmg).", "demon_combat_12.png")
        }
    )
}

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
