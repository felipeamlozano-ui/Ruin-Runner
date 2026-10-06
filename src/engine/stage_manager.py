"""
Ruin Engine — Stage Manager & High-Performance Parallax Engine.
Loads multi-layered 4K backgrounds, pre-bakes textures to native resolution (640x360),
and renders with the Zero-Allocation Dual-Slice algorithm to lock 60 FPS.
Includes multi-stage planetary progression and retro RPG story dialogues.
"""

import os
import pygame
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Optional

@dataclass
class StageConfig:
    stage_id: str
    world_id: str
    title: str
    biome_theme: str
    cloud_theme: str
    bg_folder: str
    layer_files: List[str]
    layer_speeds: List[float]
    map_width: int
    enemies: List[Tuple[str, int, int]]
    collectibles: List[Tuple[int, int, str]]
    props: List[Tuple[int, int, str, float]]
    traps: List[Tuple[int, int]]
    portal_x: int
    bgm_track: str = "dungeon"
    is_boss: bool = False
    next_stage: Optional[str] = None
    next_title: str = "PRÓXIMA FASE"
    boss_type: Optional[str] = None
    floor_y: int = 280
    dialogue_intro: List[Dict[str, Any]] = field(default_factory=list)


class ParallaxRenderer:
    """Zero-allocation, seamless multi-layer parallax renderer with continuous boundary synthesis."""
    
    def __init__(self, bg_folder: str, layer_files: List[str], speeds: List[float], screen_h: int = 360):
        self.layers: List[Tuple[pygame.Surface, float, int]] = []
        self._load_and_prebake(bg_folder, layer_files, speeds, screen_h)
        
    def _synthesize_seamless_tile(self, clean_surf: pygame.Surface, target_w: int = 640, blend_w: int = 160) -> pygame.Surface:
        """
        Synthesizes a 100% continuous horizontally tileable surface with ZERO visual cuts.
        Eliminates seam discontinuities using cosine-eased boundary synthesis.
        """
        try:
            import numpy as np
            H = 360
            W = target_w + blend_w
            
            scaled = pygame.transform.smoothscale(clean_surf, (W, H))
            has_alpha = bool(scaled.get_flags() & pygame.SRCALPHA)
            
            arr = pygame.surfarray.pixels3d(scaled)
            alpha = pygame.surfarray.pixels_alpha(scaled) if has_alpha else None
            
            out_rgb = arr[:target_w, :, :].copy()
            
            t = np.linspace(0, 1, blend_w)[:, np.newaxis, np.newaxis]
            w2 = 0.5 - 0.5 * np.cos(np.pi * t)
            w1 = 1.0 - w2
            
            c1 = arr[target_w:target_w + blend_w, :, :].astype(float)
            c2 = arr[:blend_w, :, :].astype(float)
            out_rgb[:blend_w, :, :] = np.clip(c1 * w1 + c2 * w2, 0, 255).astype(np.uint8)
            
            if has_alpha:
                seamless_surf = pygame.Surface((target_w, H), pygame.SRCALPHA, 32)
                p3d = pygame.surfarray.pixels3d(seamless_surf)
                p3d[:] = out_rgb
                del p3d
                if alpha is not None:
                    out_a = alpha[:target_w, :].copy()
                    a1 = alpha[target_w:target_w + blend_w, :].astype(float)
                    a2 = alpha[:blend_w, :].astype(float)
                    out_a[:blend_w, :] = np.clip(a1 * w1[:, :, 0] + a2 * w2[:, :, 0], 0, 255).astype(np.uint8)
                    pa = pygame.surfarray.pixels_alpha(seamless_surf)
                    pa[:] = out_a
                    del pa
            else:
                seamless_surf = pygame.Surface((target_w, H))
                p3d = pygame.surfarray.pixels3d(seamless_surf)
                p3d[:] = out_rgb
                del p3d
                
            disp = pygame.display.get_surface()
            if disp:
                seamless_surf = seamless_surf.convert_alpha() if has_alpha else seamless_surf.convert()
                
            return seamless_surf
        except Exception as err:
            print(f"Warning: Boundary synthesis fallback triggered: {err}")
            return pygame.transform.smoothscale(clean_surf, (target_w, 360))

    def _load_and_prebake(self, folder: str, files: List[str], speeds: List[float], screen_h: int):
        for idx, fname in enumerate(files):
            full_path = os.path.join(folder, fname)
            speed = speeds[idx] if idx < len(speeds) else (0.1 * (idx + 1))
            
            if os.path.exists(full_path):
                try:
                    raw = pygame.image.load(full_path)
                    raw_w, raw_h = raw.get_size()
                    
                    # Trim 2-6px edge artifacts from asset export borders
                    trim_x = min(6, raw_w // 100)
                    if trim_x > 0:
                        clean_raw = raw.subsurface(pygame.Rect(trim_x, 0, raw_w - trim_x * 2, raw_h))
                    else:
                        clean_raw = raw
                        
                    seamless = self._synthesize_seamless_tile(clean_raw, target_w=640, blend_w=160)
                    self._apply_perspective_stone_floor(seamless, fname)
                    self.layers.append((seamless, speed, seamless.get_width()))
                except Exception as err:
                    print(f"Warning: Failed to pre-bake parallax layer {full_path}: {err}")

    def _apply_perspective_stone_floor(self, surface: pygame.Surface, fname: str) -> None:
        """
        Synthesizes a realistic 2.5D perspective stone masonry pavement onto bridge/citadel floors.
        Replaces flat gray slabs with authentic medieval flagstones, perspective mortar joints,
        and chiseled stone bevels with zero per-frame runtime cost (pre-baked).
        """
        fn_lower = fname.lower()
        is_bridge = any(k in fn_lower for k in ("bridge", "sky bridge", "castle bridge", "bamboo bridge", "forest bridge"))
        is_castle = any(k in fn_lower for k in ("castle", "terrace"))
        
        if not (is_bridge or is_castle):
            return

        w, h = surface.get_size()
        y_start = int(128 * (h / 360.0))
        y_end = int(305 * (h / 360.0))
        floor_h = y_end - y_start
        if floor_h <= 10:
            return

        # Perspective row distribution (narrower near horizon, taller in foreground)
        t_steps = [0.0, 0.05, 0.11, 0.18, 0.27, 0.38, 0.50, 0.64, 0.81, 1.0]
        row_ys = [int(y_start + t * floor_h) for t in t_steps]

        overlay = pygame.Surface((w, h), pygame.SRCALPHA)

        # 1. Back wall ambient occlusion drop shadow (soft depth grounding)
        ao_h = int(16 * (h / 360.0))
        for dy in range(ao_h):
            alpha = int(105 * (1.0 - dy / float(ao_h)))
            pygame.draw.line(overlay, (18, 16, 22, alpha), (0, y_start + dy), (w, y_start + dy))

        # 2. Front balustrade contact shadow / crevice
        crevice_h = int(8 * (h / 360.0))
        for dy in range(crevice_h):
            alpha = int(85 * (dy / float(crevice_h)))
            pygame.draw.line(overlay, (14, 12, 18, alpha), (0, y_end - crevice_h + dy), (w, y_end - crevice_h + dy))

        # Stone color base palette
        if "bamboo" in fn_lower:
            base_rgb = (150, 120, 85)
            groove_col = (45, 32, 20)
            highlight_col = (210, 180, 140)
        elif "castle" in fn_lower:
            base_rgb = (115, 110, 120)
            groove_col = (25, 22, 28)
            highlight_col = (195, 190, 205)
        else:
            base_rgb = (142, 137, 131)
            groove_col = (34, 30, 36)
            highlight_col = (220, 215, 205)

        # 3. Draw flagstones row by row
        for r in range(len(row_ys) - 1):
            y_top = row_ys[r]
            y_bot = row_ys[r + 1]
            rh = y_bot - y_top
            if rh <= 0:
                continue

            # Perspective block width grows toward camera
            base_bw = int((40 + r * 5) * (w / 640.0))
            num_blocks = max(4, round(w / float(base_bw)))
            bw = w / float(num_blocks)
            x_offset = (r % 2) * (bw * 0.5)

            for b in range(num_blocks):
                bx = (b * bw + x_offset) % w
                block_w = int(bw)
                
                seed_val = (r * 37 + b * 19) % 100
                shade = (seed_val - 50) * 0.32
                
                bsurf = pygame.Surface((block_w, rh), pygame.SRCALPHA)
                col = (
                    max(0, min(255, int(base_rgb[0] + shade))),
                    max(0, min(255, int(base_rgb[1] + shade))),
                    max(0, min(255, int(base_rgb[2] + shade * 0.8))),
                    38
                )
                bsurf.fill(col)
                
                # Top edge bevel highlight
                pygame.draw.line(bsurf, (*highlight_col, 55), (1, 1), (block_w - 2, 1), 1)
                # Left bevel highlight
                pygame.draw.line(bsurf, (*highlight_col, 35), (1, 1), (1, rh - 2), 1)
                # Right shadow
                pygame.draw.line(bsurf, (groove_col[0], groove_col[1], groove_col[2], 55), (block_w - 1, 1), (block_w - 1, rh - 1), 1)
                # Bottom groove shadow
                pygame.draw.line(bsurf, (groove_col[0], groove_col[1], groove_col[2], 65), (1, rh - 1), (block_w - 1, rh - 1), 1)

                ibx = int(bx)
                overlay.blit(bsurf, (ibx, y_top))
                if ibx + block_w > w:
                    overlay.blit(bsurf, (ibx - w, y_top))

            # Horizontal mortar groove across the entire width
            groove_alpha = min(190, int(85 + r * 11))
            pygame.draw.line(overlay, (*groove_col, groove_alpha), (0, y_bot - 1), (w, y_bot - 1), 1)
            # Sunlight highlight on lower rim of joint
            if y_bot < y_end:
                hl_alpha = min(140, int(50 + r * 9))
                pygame.draw.line(overlay, (*highlight_col, hl_alpha), (0, y_bot), (w, y_bot), 1)

        surface.blit(overlay, (0, 0))

    def draw(self, surface: pygame.Surface, cam_x: float, cam_y: float = 0.0):
        """Dual-slice blit algorithm with 100% seamless continuity."""
        sw = surface.get_width()
        for surf, speed, lw in self.layers:
            offset_x = int(cam_x * speed) % lw
            x1 = -offset_x
            x2 = x1 + lw
            surface.blit(surf, (x1, 0))
            if x2 < sw:
                surface.blit(surf, (x2, 0))
            if x2 + lw < sw:
                surface.blit(surf, (x2 + lw, 0))


STAGE_CATALOG: Dict[str, StageConfig] = {
    # ─────────────────────────────────────────────────────────────────────────
    # MUNDO 1: TERRAE (Costa, Floresta & Fortaleza)
    # ─────────────────────────────────────────────────────────────────────────
    "terrae_1": StageConfig(
        stage_id="terrae_1",
        world_id="terrae",
        title="MUNDO 1-1: COSTA DOS BAMBUS",
        biome_theme="road",
        cloud_theme="white",
        bg_folder=os.path.join("assets", "sprites", "stages", "rpg_battlegrounds", "PNG", "1"),
        layer_files=["bamboo bridge.png"],
        layer_speeds=[0.35],
        map_width=3200,
        floor_y=280,
        enemies=[
            ("warrior", 500, 205),
            ("spearman", 900, 205),
            ("archer", 1400, 205),
            ("warrior", 1850, 205),
            ("spearman", 2300, 205),
            ("mage", 2750, 205),
        ],
        collectibles=[(650, 248, "potion"), (1250, 248, "orb"), (2100, 248, "golden_potion"), (2850, 248, "orb")],
        props=[(120, 240, "rock", 0.8), (350, 248, "barrel", 1.0), (750, 242, "rock", 0.9), (1050, 248, "rock", 1.0), (1450, 242, "rock", 0.85), (1700, 248, "barrel", 1.1), (2100, 240, "rock", 0.9), (2500, 248, "rock", 1.0), (2950, 252, "rock", 0.85)],
        traps=[(850, 266), (1950, 266)],
        portal_x=3050,
        next_stage="terrae_2",
        next_title="MUNDO 1-2: PONTE DA FLORESTA ANCESTRAL",
        dialogue_intro=[
            {"speaker": "ELDER VULKAN", "text": "Shaia, você pousou na Costa dos Bambus. A antiga barreira elemental começou a ruir...", "portrait": "vulkan", "color": (80, 200, 255)},
            {"speaker": "SHAIA", "text": "Posso sentir a corrupção na terra. Os mortos-vivos estão se erguendo das marés!", "portrait": "shaia", "color": (255, 200, 80)},
            {"speaker": "ELDER VULKAN", "text": "Avance pela ponte flutuante. O núcleo da ruína está protegido no coração da floresta!", "portrait": "vulkan", "color": (80, 200, 255)}
        ]
    ),
    "terrae_2": StageConfig(
        stage_id="terrae_2",
        world_id="terrae",
        title="MUNDO 1-2: PONTE DA FLORESTA ANCESTRAL",
        biome_theme="road",
        cloud_theme="white",
        bg_folder=os.path.join("assets", "sprites", "stages", "rpg_battlegrounds", "PNG", "2"),
        layer_files=["forest bridge.png"],
        layer_speeds=[0.35],
        map_width=3600,
        floor_y=280,
        enemies=[
            ("spearman", 450, 205),
            ("mage", 900, 205),
            ("archer", 1400, 205),
            ("warrior", 1900, 205),
            ("spearman", 2350, 205),
            ("mage", 2850, 205),
            ("warrior", 3250, 205)
        ],
        collectibles=[(750, 248, "potion"), (1550, 248, "orb"), (2450, 248, "golden_potion"), (3150, 248, "orb")],
        props=[(150, 240, "rock", 0.85), (300, 248, "barrel", 1.0), (800, 242, "rock", 0.9), (1150, 248, "rock", 1.0), (1600, 240, "rock", 0.85), (2050, 248, "barrel", 1.1), (2550, 242, "rock", 0.9), (2950, 248, "rock", 1.0), (3350, 252, "rock", 0.85)],
        traps=[(850, 266), (1750, 266), (2650, 266)],
        portal_x=3450,
        next_stage="terrae_3",
        next_title="MUNDO 1-3: PORTÃO DA FORTALEZA ESMERALDA",
        dialogue_intro=[
            {"speaker": "SHAIA", "text": "A floresta está infestada de xamãs esqueléticos... A energia de magma abaixo do solo está pulsando.", "portrait": "shaia", "color": (255, 200, 80)},
            {"speaker": "LUNARIA", "text": "Fique atenta aos ataques à distância! Use [Shift] para esquivar e contra-atacar com [E]!", "portrait": "lunaria", "color": (220, 140, 255)}
        ]
    ),
    "terrae_3": StageConfig(
        stage_id="terrae_3",
        world_id="terrae",
        title="MUNDO 1-3: PORTÃO DA FORTALEZA ESMERALDA",
        biome_theme="road",
        cloud_theme="gray",
        bg_folder=os.path.join("assets", "sprites", "stages", "rpg_battlegrounds", "PNG", "4"),
        layer_files=["castle bridge.png"],
        layer_speeds=[0.35],
        map_width=3800,
        floor_y=280,
        enemies=[
            ("warrior", 450, 205),
            ("mage", 900, 205),
            ("spearman", 1450, 205),
            ("archer", 1950, 205),
            ("warrior", 2500, 205),
            ("mage", 3050, 205),
            ("spearman", 3450, 205)
        ],
        collectibles=[(800, 248, "potion"), (1650, 248, "orb"), (2600, 248, "golden_potion"), (3300, 248, "orb")],
        props=[(120, 240, "rock", 0.85), (300, 248, "barrel", 1.0), (750, 242, "rock", 0.9), (1200, 248, "rock", 1.0), (1700, 240, "rock", 0.9), (2200, 248, "barrel", 1.1), (2650, 242, "rock", 0.85), (3000, 248, "rock", 1.0), (3550, 252, "rock", 0.85)],
        traps=[(750, 266), (1700, 266), (2800, 266)],
        portal_x=3650,
        next_stage="boss",
        boss_type="demon_slime",
        next_title="CONFRONTO: O TITÃ DEMONÍACO",
        dialogue_intro=[
            {"speaker": "SHAIA", "text": "O portão ancestral da fortaleza foi arrebentado por dentro... As pedras estão derretendo em lava!", "portrait": "shaia", "color": (255, 200, 80)},
            {"speaker": "O TITÃ DEMONÍACO", "text": "QUEM OUSA PERTURBAR O SONO DO TITÃ DE MAGMA?!", "portrait": "boss", "color": (255, 60, 40)},
            {"speaker": "SHAIA", "text": "O guardião primordial se corrompeu. Devo derrotá-lo para libertar Terrae!", "portrait": "shaia", "color": (255, 200, 80)}
        ]
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # MUNDO 2: SANGUIS (Lua Carmesim, Palácio & Cripta dos Vampiros)
    # ─────────────────────────────────────────────────────────────────────────
    "sanguis_1": StageConfig(
        stage_id="sanguis_1",
        world_id="sanguis",
        title="MUNDO 2-1: O TERRAÇO DO CREPÚSCULO",
        biome_theme="cave",
        cloud_theme="black",
        bg_folder=os.path.join("assets", "sprites", "stages", "vampires", "PNG", "1"),
        layer_files=["terrace.png"],
        layer_speeds=[0.35],
        map_width=3800,
        floor_y=280,
        enemies=[
            ("warrior", 500, 205),
            ("mage", 950, 205),
            ("archer", 1450, 205),
            ("spearman", 1950, 205),
            ("mage", 2450, 205),
            ("warrior", 2950, 205),
            ("archer", 3400, 205)
        ],
        collectibles=[(800, 248, "potion"), (1600, 248, "orb"), (2500, 248, "golden_potion"), (3300, 248, "orb")],
        props=[(140, 240, "rock", 0.9), (350, 248, "rock", 1.0), (800, 242, "rock", 0.85), (1200, 248, "barrel", 1.0), (1650, 240, "rock", 0.9), (2100, 248, "rock", 1.1), (2600, 242, "rock", 0.85), (3000, 248, "barrel", 1.0), (3500, 252, "rock", 0.9)],
        traps=[(900, 266), (1800, 266), (2700, 266)],
        portal_x=3650,
        next_stage="sanguis_2",
        next_title="MUNDO 2-2: O SALÃO DO TRONO CARMESIM",
        dialogue_intro=[
            {"speaker": "CARMILLA", "text": "Mais uma tola ousa pisar no palácio sagrado da Lua de Sangue...", "portrait": "carmilla", "color": (255, 80, 140)},
            {"speaker": "SHAIA", "text": "A praga dos vampiros escravizou este planeta por séculos. Vim libertá-lo!", "portrait": "shaia", "color": (255, 200, 80)},
            {"speaker": "CARMILLA", "text": "Sua carne mortal alimentará nossas bestas antes do amanhecer!", "portrait": "carmilla", "color": (255, 80, 140)}
        ]
    ),
    "sanguis_2": StageConfig(
        stage_id="sanguis_2",
        world_id="sanguis",
        title="MUNDO 2-2: O SALÃO DO TRONO CARMESIM",
        biome_theme="cave",
        cloud_theme="black",
        bg_folder=os.path.join("assets", "sprites", "stages", "vampires", "PNG", "2"),
        layer_files=["throne room.png"],
        layer_speeds=[0.35],
        map_width=4000,
        floor_y=280,
        enemies=[
            ("spearman", 480, 205),
            ("mage", 900, 205),
            ("warrior", 1400, 205),
            ("archer", 1900, 205),
            ("spearman", 2400, 205),
            ("mage", 2900, 205),
            ("warrior", 3400, 205),
            ("archer", 3800, 205)
        ],
        collectibles=[(600, 248, "potion"), (1400, 248, "orb"), (2200, 248, "golden_potion"), (3200, 248, "orb")],
        props=[(150, 240, "rock", 0.85), (200, 248, "barrel", 0.9), (600, 242, "rock", 0.9), (900, 248, "rock", 1.0), (1350, 240, "rock", 0.85), (1700, 248, "barrel", 1.1), (2200, 242, "rock", 0.9), (2600, 248, "rock", 1.0), (3100, 240, "rock", 0.85), (3700, 252, "rock", 0.9)],
        traps=[(550, 266), (1400, 266), (2300, 266), (3200, 266)],
        portal_x=3850,
        next_stage="sanguis_3",
        next_title="MUNDO 2-3: A CRIPTA PROFANADA",
        dialogue_intro=[
            {"speaker": "SHAIA", "text": "O salão está impregnado com a essência do abismo... As sombras conspiram entre as colunas.", "portrait": "shaia", "color": (255, 200, 80)},
            {"speaker": "CARMILLA", "text": "Você não passará pelo meu carrasco blindado... O Empalador já sente seu sangue!", "portrait": "carmilla", "color": (255, 80, 140)}
        ]
    ),
    "sanguis_3": StageConfig(
        stage_id="sanguis_3",
        world_id="sanguis",
        title="MUNDO 2-3: A CRIPTA PROFANADA",
        biome_theme="cave",
        cloud_theme="black",
        bg_folder=os.path.join("assets", "sprites", "stages", "vampires", "PNG", "1"),
        layer_files=["terrace.png"],
        layer_speeds=[0.35],
        map_width=3900,
        floor_y=280,
        enemies=[
            ("warrior", 420, 205),
            ("spearman", 880, 205),
            ("mage", 1350, 205),
            ("archer", 1850, 205),
            ("warrior", 2350, 205),
            ("mage", 2850, 205),
            ("spearman", 3350, 205)
        ],
        collectibles=[(700, 248, "potion"), (1500, 248, "orb"), (2400, 248, "golden_potion"), (3200, 248, "orb")],
        props=[(120, 240, "rock", 0.85), (250, 248, "rock", 1.0), (700, 242, "rock", 0.9), (1100, 248, "barrel", 1.0), (1550, 240, "rock", 0.85), (2000, 248, "rock", 1.1), (2500, 242, "rock", 0.9), (2900, 248, "barrel", 1.0), (3500, 252, "rock", 0.85)],
        traps=[(800, 266), (1700, 266), (2600, 266)],
        portal_x=3700,
        next_stage="boss",
        boss_type="impaler",
        next_title="CONFRONTO: O EMPALADOR ABISSAL",
        dialogue_intro=[
            {"speaker": "SHAIA", "text": "O cheiro de ferro e morte empesteia o ar. Estacas afiadas cobrem as paredes...", "portrait": "shaia", "color": (255, 200, 80)},
            {"speaker": "O EMPALADOR ABISSAL", "text": "INVASORES SERÃO EMPALADOS! NINGUÉM DEIXA O CASTELO VIVO!", "portrait": "boss", "color": (220, 60, 90)},
            {"speaker": "SHAIA", "text": "Sua armadura pode ser pesada, mas minha lâmina é mais rápida!", "portrait": "shaia", "color": (255, 200, 80)}
        ]
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # MUNDO 3: GLACIES (Tundra, Castelo & Floresta Congelada)
    # ─────────────────────────────────────────────────────────────────────────
    "glacies_1": StageConfig(
        stage_id="glacies_1",
        world_id="glacies",
        title="MUNDO 3-1: O CASTELO CONGELADO",
        biome_theme="ice",
        cloud_theme="gray",
        bg_folder=os.path.join("assets", "sprites", "stages", "vampires", "PNG", "3"),
        layer_files=["castle.png"],
        layer_speeds=[0.35],
        map_width=3600,
        floor_y=280,
        enemies=[
            ("warrior", 400, 205),
            ("archer", 900, 205),
            ("spearman", 1400, 205),
            ("mage", 1900, 205),
            ("warrior", 2400, 205),
            ("archer", 2900, 205)
        ],
        collectibles=[(700, 248, "potion"), (1500, 248, "orb"), (2300, 248, "golden_potion"), (3100, 248, "orb")],
        props=[(140, 240, "rock", 0.9), (300, 248, "rock", 1.0), (750, 242, "rock", 0.85), (1200, 248, "barrel", 1.1), (1650, 240, "rock", 0.9), (2100, 248, "rock", 1.0), (2550, 242, "rock", 0.85), (2900, 248, "barrel", 1.0), (3350, 252, "rock", 0.9)],
        traps=[(800, 266), (1800, 266), (2700, 266)],
        portal_x=3450,
        next_stage="glacies_2",
        next_title="MUNDO 3-2: A FLORESTA DOS MORTOS CONGELADOS",
        dialogue_intro=[
            {"speaker": "SHAIA", "text": "O frio deste planeta é sobrenatural... O castelo parece uma tumba de gelo eterno.", "portrait": "shaia", "color": (255, 200, 80)},
            {"speaker": "ESPÍRITO DO GELO", "text": "Fugi, guerreira... A fera quimérica ancestral devorou todos os guardiões.", "portrait": "spirit", "color": (140, 220, 255)},
            {"speaker": "SHAIA", "text": "Não posso recuar. O núcleo congelado deste mundo precisa ser purificado!", "portrait": "shaia", "color": (255, 200, 80)}
        ]
    ),
    "glacies_2": StageConfig(
        stage_id="glacies_2",
        world_id="glacies",
        title="MUNDO 3-2: A FLORESTA DOS MORTOS CONGELADOS",
        biome_theme="snowy",
        cloud_theme="black",
        bg_folder=os.path.join("assets", "sprites", "stages", "vampires", "PNG", "4"),
        layer_files=["dead forest.png"],
        layer_speeds=[0.35],
        map_width=3800,
        floor_y=280,
        enemies=[
            ("spearman", 450, 205),
            ("mage", 950, 205),
            ("warrior", 1500, 205),
            ("archer", 2050, 205),
            ("spearman", 2600, 205),
            ("mage", 3100, 205)
        ],
        collectibles=[(800, 248, "potion"), (1600, 248, "orb"), (2500, 248, "golden_potion"), (3300, 248, "orb")],
        props=[(350, 248, "rock", 1.0), (1250, 248, "barrel", 1.1), (2200, 248, "rock", 1.0), (3000, 248, "barrel", 1.2)],
        traps=[(750, 266), (1650, 266), (2550, 266)],
        portal_x=3650,
        next_stage="glacies_3",
        next_title="MUNDO 3-3: O ABISMO GELADO",
        dialogue_intro=[
            {"speaker": "SHAIA", "text": "Árvores ressequidas sob a neve perpétua... A névoa verde carrega veneno necrosante.", "portrait": "shaia", "color": (255, 200, 80)},
            {"speaker": "ESPÍRITO DO GELO", "text": "Tenha cuidado! A saliva da fera dissolve até as armaduras mais resistentes!", "portrait": "spirit", "color": (140, 220, 255)}
        ]
    ),
    "glacies_3": StageConfig(
        stage_id="glacies_3",
        world_id="glacies",
        title="MUNDO 3-3: O ABISMO GELADO",
        biome_theme="ice",
        cloud_theme="white",
        bg_folder=os.path.join("assets", "sprites", "stages", "vampires", "PNG", "3"),
        layer_files=["castle.png"],
        layer_speeds=[0.35],
        map_width=3900,
        floor_y=280,
        enemies=[
            ("warrior", 400, 205),
            ("spearman", 880, 205),
            ("mage", 1380, 205),
            ("archer", 1900, 205),
            ("warrior", 2420, 205),
            ("mage", 2950, 205),
            ("spearman", 3450, 205)
        ],
        collectibles=[(750, 248, "potion"), (1550, 248, "orb"), (2450, 248, "golden_potion"), (3250, 248, "orb")],
        props=[(280, 248, "rock", 1.0), (1150, 248, "barrel", 1.0), (2050, 248, "rock", 1.1), (2950, 248, "barrel", 1.0)],
        traps=[(800, 266), (1750, 266), (2700, 266)],
        portal_x=3700,
        next_stage="boss",
        boss_type="monster_creature",
        next_title="CONFRONTO: O MONSTRO QUIMÉRICO ANCESTRAL",
        dialogue_intro=[
            {"speaker": "SHAIA", "text": "Pegadas gigantescas no gelo... A quimera ancestral fez deste abismo sua toca!", "portrait": "shaia", "color": (255, 200, 80)},
            {"speaker": "MONSTRO QUIMÉRICO", "text": "ROOOAAAR! (O solo estremece com seu bafo venenoso)", "portrait": "boss", "color": (90, 200, 255)},
            {"speaker": "SHAIA", "text": "Fera maldita... Retorne ao sono eterno do gelo!", "portrait": "shaia", "color": (255, 200, 80)}
        ]
    ),

    # ─────────────────────────────────────────────────────────────────────────
    # MUNDO 4: AETHERIA (Cidadela dos Céus)
    # ─────────────────────────────────────────────────────────────────────────
    "aetheria_1": StageConfig(
        stage_id="aetheria_1",
        world_id="aetheria",
        title="MUNDO 4-1: A CIDADELA DOS CÉUS",
        biome_theme="desert",
        cloud_theme="white",
        bg_folder=os.path.join("assets", "sprites", "stages", "rpg_battlegrounds", "PNG", "3"),
        layer_files=["sky bridge.png"],
        layer_speeds=[0.35],
        map_width=4000,
        floor_y=280,
        enemies=[
            ("mage", 450, 205),
            ("archer", 950, 205),
            ("spearman", 1450, 205),
            ("mage", 1950, 205),
            ("warrior", 2500, 205),
            ("archer", 3050, 205),
            ("spearman", 3550, 205)
        ],
        collectibles=[(750, 248, "potion"), (1600, 248, "orb"), (2450, 248, "golden_potion"), (3350, 248, "orb")],
        props=[(300, 248, "rock", 1.0), (1200, 248, "barrel", 0.9), (2100, 248, "rock", 1.1), (3000, 248, "barrel", 1.0)],
        traps=[(850, 266), (1800, 266), (2800, 266)],
        portal_x=3800,
        next_stage="aetheria_2",
        next_title="MUNDO 4-2: AS TORRES SUSPENSAS",
        dialogue_intro=[
            {"speaker": "LORDE SAMURAI", "text": "Você tem coragem de subir até a Cidadela dos Céus, guerreira.", "portrait": "samurai", "color": (255, 180, 60)},
            {"speaker": "SHAIA", "text": "Lorde Samurai... Sua lâmina jurou proteger Aetheria, mas a escuridão consumiu sua honra!", "portrait": "shaia", "color": (255, 200, 80)},
            {"speaker": "LORDE SAMURAI", "text": "A honra morreu quando os céus caíram. Apenas o corte perfeito permanece.", "portrait": "samurai", "color": (255, 180, 60)}
        ]
    ),
    "aetheria_2": StageConfig(
        stage_id="aetheria_2",
        world_id="aetheria",
        title="MUNDO 4-2: AS TORRES SUSPENSAS",
        biome_theme="desert",
        cloud_theme="white",
        bg_folder=os.path.join("assets", "sprites", "stages", "rpg_battlegrounds", "PNG", "3"),
        layer_files=["sky bridge.png"],
        layer_speeds=[0.35],
        map_width=4100,
        floor_y=280,
        enemies=[
            ("warrior", 420, 205),
            ("mage", 880, 205),
            ("archer", 1380, 205),
            ("spearman", 1900, 205),
            ("warrior", 2420, 205),
            ("mage", 2950, 205),
            ("archer", 3500, 205)
        ],
        collectibles=[(800, 248, "potion"), (1650, 248, "orb"), (2500, 248, "golden_potion"), (3400, 248, "orb")],
        props=[(280, 248, "barrel", 1.0), (1150, 248, "rock", 1.0), (2050, 248, "barrel", 1.1), (2950, 248, "rock", 1.0)],
        traps=[(800, 266), (1750, 266), (2700, 266)],
        portal_x=3900,
        next_stage="aetheria_3",
        next_title="MUNDO 4-3: O ALTAR DA NÉVOA DOURADA",
        dialogue_intro=[
            {"speaker": "SHAIA", "text": "Os guardiões do céu foram todos corrompidos por suas ordens, Samurai!", "portrait": "shaia", "color": (255, 200, 80)},
            {"speaker": "LORDE SAMURAI", "text": "Eles escolheram a espada. Mostre-me se seu aço é tão afiado quanto suas palavras!", "portrait": "samurai", "color": (255, 180, 60)}
        ]
    ),
    "aetheria_3": StageConfig(
        stage_id="aetheria_3",
        world_id="aetheria",
        title="MUNDO 4-3: O ALTAR DA NÉVOA DOURADA",
        biome_theme="desert",
        cloud_theme="white",
        bg_folder=os.path.join("assets", "sprites", "stages", "rpg_battlegrounds", "PNG", "4"),
        layer_files=["castle bridge.png"],
        layer_speeds=[0.35],
        map_width=4200,
        floor_y=280,
        enemies=[
            ("spearman", 400, 205),
            ("mage", 900, 205),
            ("archer", 1450, 205),
            ("warrior", 2000, 205),
            ("spearman", 2550, 205),
            ("mage", 3100, 205),
            ("warrior", 3650, 205)
        ],
        collectibles=[(850, 248, "potion"), (1700, 248, "orb"), (2600, 248, "golden_potion"), (3500, 248, "orb")],
        props=[(300, 248, "rock", 1.0), (1250, 248, "barrel", 1.0), (2200, 248, "rock", 1.1), (3100, 248, "barrel", 1.0)],
        traps=[(850, 266), (1800, 266), (2800, 266)],
        portal_x=4000,
        next_stage="boss",
        boss_type="samurai",
        next_title="CONFRONTO: LORDE SAMURAI AMALDIÇOADO",
        dialogue_intro=[
            {"speaker": "SHAIA", "text": "O topo do templo... O vento parou de soprar. O duelo final está selado.", "portrait": "shaia", "color": (255, 200, 80)},
            {"speaker": "LORDE SAMURAI", "text": "Desembainhe seu aço. Que o vento celestial decida quem é o verdadeiro mestre!", "portrait": "samurai", "color": (255, 180, 60)},
            {"speaker": "SHAIA", "text": "Pelo destino das Ruínas... Eu não recuarei!", "portrait": "shaia", "color": (255, 200, 80)}
        ]
    ),
}

class StageManager:
    """Manages active stage progression and transitions."""
    def __init__(self):
        self.current_stage_id = "terrae_1"
        self.parallax_renderer = None

    def get_stage(self, stage_id: str) -> Optional[StageConfig]:
        return STAGE_CATALOG.get(stage_id)

    def load_stage(self, stage_id: str) -> Optional[StageConfig]:
        cfg = STAGE_CATALOG.get(stage_id)
        if cfg:
            self.current_stage_id = stage_id
            self.parallax_renderer = ParallaxRenderer(
                cfg.bg_folder,
                cfg.layer_files,
                cfg.layer_speeds,
                screen_h=360
            )
        return cfg

    def get_first_stage_for_world(self, world_id: str) -> Optional[StageConfig]:
        return STAGE_CATALOG.get(f"{world_id}_1")

STAGE_MGR = StageManager()
