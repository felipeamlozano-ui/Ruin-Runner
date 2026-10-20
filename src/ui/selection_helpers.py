"""
src/ui/selection_helpers.py
---------------------------
Shared Visual Pipeline and Helper Functions for Selection Scenes:
- Solo Hero Selection (character_select_scene.py)
- Co-op Dual Selection (character_select_scene.py)
- 1v1 Local Duel Selection (duel_character_select_scene.py)

Provides:
- Authentic Bounding-Box Head/Bust Thumbnail Generator for all 11 heroes
- Soft Volumetric Light Beam & Pedestal Halo VFX (Silksong aesthetics, zero hard polygons)
- Live Stage Background Renderer (Parallax autoscroll + Mist + Silksong Lighting + AO + God Rays)
- Symmetrical 304px Hero Dossier Panel Renderer (HP/MP/SP gauges, passive with word-wrap, 5 combat skills)
"""

import math
import os
from typing import Dict, Optional, Tuple, List
import pygame

from config.settings import SETTINGS
from entities.character_data import CHARACTER_ORDER, CHARACTER_REGISTRY, CharacterProfile
from engine.lighting import LightingEngine
from engine.stage_manager import ParallaxRenderer, StageConfig
from engine.v3.weather.clouds import CloudsManager
from engine.v3.weather.mist import MistManager
from engine.text_cache import get_cached_text, render_wrapped_text
from ui.hollow_ui import HollowFonts, HollowColors, HollowCrestRenderer

_THUMBNAILS_CACHE: Dict[str, pygame.Surface] = {}
_BEAM_CACHE: Dict[Tuple[int, int, Tuple[int, int, int]], pygame.Surface] = {}

def get_hero_thumbnails() -> Dict[str, pygame.Surface]:
    """
    Loads and caches authentic 28x28 character portraits for all 11 roster heroes.
    Uses frame.get_bounding_rect() to locate visible pixels (alpha > 10) and crops
    the upper head/bust region (top 45% of character height), perfectly centered.
    """
    global _THUMBNAILS_CACHE
    if _THUMBNAILS_CACHE:
        return _THUMBNAILS_CACHE

    for cid in CHARACTER_ORDER:
        prof = CHARACTER_REGISTRY[cid]
        frame = None
        try:
            # 1. Check if dedicated portrait.png exists
            p_port = os.path.join(prof.base_folder, "portrait.png")
            if os.path.exists(p_port):
                raw = pygame.image.load(p_port).convert_alpha()
                _THUMBNAILS_CACHE[cid] = pygame.transform.smoothscale(raw, (28, 28))
                continue

            # 2. Check for folder (Shaia) or craftpix sprite
            if prof.sprite_type == "folder":
                candidates = [
                    os.path.join(prof.base_folder, "sprites_common", "common_00_idle_stand_A01.png"),
                    os.path.join(prof.base_folder, "common_00_idle_stand_A01.png"),
                    os.path.join(prof.base_folder, "sprites_common", "common_00_idle_stand_A_000.png"),
                    os.path.join(prof.base_folder, "common_00_idle_stand_A_000.png"),
                ]
                for c in candidates:
                    if os.path.exists(c):
                        frame = pygame.image.load(c).convert_alpha()
                        break
            else:
                p = os.path.join(prof.base_folder, "Idle.png")
                if os.path.exists(p):
                    raw = pygame.image.load(p).convert_alpha()
                    fw, fh = prof.frame_size
                    frame = raw.subsurface((0, 0, fw, fh))

            if frame is not None:
                bbox = frame.get_bounding_rect()
                if bbox.width > 0 and bbox.height > 0:
                    head_h = max(20, int(bbox.height * 0.45))
                    crop_size = max(head_h, int(bbox.width * 0.70))
                    crop_x = int(bbox.centerx - crop_size / 2)
                    crop_y = int(bbox.top)

                    crop_x = max(0, min(frame.get_width() - crop_size, crop_x))
                    crop_y = max(0, min(frame.get_height() - crop_size, crop_y))
                    crop_size = min(crop_size, frame.get_width() - crop_x, frame.get_height() - crop_y)

                    sub = frame.subsurface((crop_x, crop_y, crop_size, crop_size))
                    thumb = pygame.transform.smoothscale(sub, (28, 28))
                    _THUMBNAILS_CACHE[cid] = thumb
                else:
                    _THUMBNAILS_CACHE[cid] = _create_fallback_icon(prof)
            else:
                _THUMBNAILS_CACHE[cid] = _create_fallback_icon(prof)
        except Exception:
            _THUMBNAILS_CACHE[cid] = _create_fallback_icon(prof)

    return _THUMBNAILS_CACHE


def _create_fallback_icon(prof: CharacterProfile) -> pygame.Surface:
    surf = pygame.Surface((28, 28), pygame.SRCALPHA)
    pygame.draw.circle(surf, prof.color_theme, (14, 14), 11)
    pygame.draw.circle(surf, (20, 24, 32), (14, 14), 9)
    f = HollowFonts.get(10, bold=True)
    t = f.render(prof.name[:1], True, prof.color_theme)
    surf.blit(t, t.get_rect(center=(14, 14)))
    return surf


def get_volumetric_light_beam(width: int = 120, height: int = 210,
                              color: Tuple[int, int, int] = (255, 235, 175)) -> pygame.Surface:
    """
    Returns a smooth volumetric light beam surface with vertical cosine falloff.
    Pre-baked and cached for zero per-frame CPU allocation.
    """
    cr, cg, cb = int(color[0]), int(color[1]), int(color[2])
    key = (width, height, (cr, cg, cb))
    if key in _BEAM_CACHE:
        return _BEAM_CACHE[key]

    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    cx = width / 2.0
    for y in range(height):
        prog = y / float(height)
        # Intensity increases towards floor then soft fades
        alpha_y = math.sin(prog * math.pi * 0.90) * 48.0
        cur_w = 26.0 + prog * (width - 32.0)
        half_w = cur_w / 2.0
        x_start = max(0, int(cx - half_w))
        x_end = min(width, int(cx + half_w))

        for x in range(x_start, x_end):
            dist_norm = abs(x - cx) / half_w
            alpha_x = math.cos(dist_norm * math.pi * 0.5)
            a = int(alpha_y * alpha_x)
            if a > 0:
                surf.set_at((x, y), (cr, cg, cb, min(255, a)))

    _BEAM_CACHE[key] = surf
    return surf


def draw_pedestal_with_beam(surface: pygame.Surface, pedestal_pos: pygame.math.Vector2,
                            color_theme: Tuple[int, int, int], lighting: Optional[LightingEngine] = None):
    """
    Renders an ancient dais with:
    1. Soft vertical God Ray beam (BLEND_RGB_ADD)
    2. Radial Halo glow on pedestal base (BLEND_RGB_ADD)
    3. Ground Contact AO shadow under hero feet
    4. Hollow Knight filigree ancient stone pedestal
    """
    px, py = int(pedestal_pos.x), int(pedestal_pos.y)

    # 1. Soft Volumetric God Ray Light Beam
    beam_w = 120
    beam_h = 200
    beam_surf = get_volumetric_light_beam(beam_w, beam_h, color_theme)
    surface.blit(beam_surf, (px - beam_w // 2, py - beam_h + 10), special_flags=pygame.BLEND_RGB_ADD)

    # 2. Radial Base Halo
    halo_surf = LightingEngine.get_radial_light_surface(radius=38, color=color_theme, intensity=0.45)
    surface.blit(halo_surf, (px - 38, py - 18), special_flags=pygame.BLEND_RGB_ADD)

    # 3. Ground Contact AO Shadow (anchoring hero feet)
    if lighting and hasattr(lighting, "_ao_stamp_med"):
        stamp = lighting._ao_stamp_med
        surface.blit(stamp, (px - stamp.get_width() // 2, py - 4))
    else:
        shadow_surf = pygame.Surface((44, 12), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 150), (0, 0, 44, 12))
        surface.blit(shadow_surf, (px - 22, py - 4))

    # 4. Ancient Pedestal
    HollowCrestRenderer.draw_ancient_pedestal(surface, pedestal_pos, color_theme)


def draw_live_stage_background(surface: pygame.Surface, parallax: Optional[ParallaxRenderer],
                               cam_x: float, lighting: LightingEngine,
                               mist_manager: Optional[MistManager] = None,
                               clouds: Optional[CloudsManager] = None):
    """
    Renders live animated game stage background with full Hollow Knight Silksong atmosphere:
    Parallax depth planes, moving clouds, depth fog, ground mist, God Rays, ambient dust motes,
    and multiplicative static post-mask.
    """
    cam_vec = pygame.math.Vector2(cam_x, 0)
    if parallax is not None:
        if parallax.has_split_layers:
            parallax.draw_sky_layer(surface, cam_x)
            if clouds:
                clouds.draw(surface, cam_vec)
            parallax.draw_midground_layer(surface, cam_x)
            if mist_manager:
                mist_manager.draw_distant_fog(surface, cam_x)
            parallax.draw_foreground_layer(surface, cam_x)
        else:
            parallax.draw(surface, cam_x)
            if mist_manager:
                mist_manager.draw_distant_fog(surface, cam_x)

    # Ground Mist sliding under pedestals
    if mist_manager:
        mist_manager.draw_ground_mist(surface, cam_x)

    # Silksong Volumetric Diagonal God Rays & Floating Spores
    cam_vec = pygame.math.Vector2(cam_x, 0)
    lighting.draw_god_rays(surface, cam_vec)
    lighting.draw_ambient_particles(surface, cam_vec)

    # Multiplicative Static Post-Mask (AO + Vignette + Color Grading)
    post_mask = getattr(lighting, "_unified_post_mask", None) or lighting._static_ao_map
    if post_mask is not None:
        surface.blit(post_mask, (0, 0), special_flags=pygame.BLEND_MULT)


def draw_symmetrical_hero_card(
    surface: pygame.Surface,
    rect: pygame.Rect,
    player_idx: int,
    profile: CharacterProfile,
    pedestal_pos: pygame.math.Vector2,
    player_entity,
    is_ready: bool,
    tag_name: str,
    tag_col: Tuple[int, int, int],
    ready_hint: str,
    cancel_hint: str,
    selected_idx: int,
    thumbnails: Dict[str, pygame.Surface],
    lighting: LightingEngine,
    time_sec: float = 0.0
):
    """
    Draws a symmetrical 304px character selection card for P1 or P2:
    - Upper: Pedestal with light beam and animated player standee (left); Name, Title, HP/MP/SP gauges and Passive (right)
    - Middle: 5 Combat Abilities ([J], [K], [E], [SH], [R]) without truncation
    - Lower: 2-row selection grid with authentic bust portraits
    """
    # 1. Main Filigree Panel
    border_col = (80, 245, 140) if is_ready else tag_col
    HollowCrestRenderer.draw_filigree_panel(
        surface, rect,
        bg_color=(10, 12, 18, 235),
        border_color=border_col,
        corner_flourish=True
    )

    # Header: Tag and Ready Pill
    f_title = HollowFonts.get(10, bold=True)
    f_desc = HollowFonts.get(9)
    f_badge = HollowFonts.get(8, bold=True)
    f_key = HollowFonts.get(8, bold=True)

    header_y = rect.y + 6
    tag_surf = f_title.render(f"‹ {tag_name} ›", True, tag_col)
    surface.blit(tag_surf, (rect.x + 8, header_y))

    # Ready status pill
    if is_ready:
        pill_txt = f"PRONTO! ({cancel_hint})"
        pill_bg = (14, 45, 26, 240)
        pill_border = (80, 245, 140)
        pill_col = (255, 255, 255)
    else:
        pill_txt = f"{ready_hint} ESCOLHER"
        pill_bg = (16, 20, 28, 220)
        pill_border = (65, 75, 98)
        pill_col = HollowColors.TEXT_NORMAL

    ps = f_desc.render(pill_txt, True, pill_col)
    pw = ps.get_width() + 10
    ph = 15
    px = rect.right - pw - 8
    py = header_y
    pygame.draw.rect(surface, pill_bg, (px, py, pw, ph), border_radius=2)
    pygame.draw.rect(surface, pill_border, (px, py, pw, ph), 1, border_radius=2)
    surface.blit(ps, (px + 5, py + 1))

    # 2. Upper Left: Pedestal + Light Beam + Standee
    draw_pedestal_with_beam(surface, pedestal_pos, profile.color_theme, lighting)
    player_entity.draw(surface, pygame.math.Vector2(0, 0))

    # 3. Upper Right: Name, Title, HP/MP/SP and Passive Box
    rx = rect.x + 118
    rw = rect.right - rx - 8
    ry = rect.y + 24

    name_surf = HollowFonts.get(12, bold=True).render(profile.name.upper(), True, HollowColors.TEXT_TITLE)
    surface.blit(name_surf, (rx, ry))

    title_surf = f_desc.render(profile.title, True, HollowColors.TEXT_NORMAL)
    surface.blit(title_surf, (rx, ry + 15))

    # Attribute Gauges (HP, MP, SP)
    stats = [
        ("HP", profile.hp_max, (225, 60, 60)),
        ("MP", profile.mp_max, (60, 150, 245)),
        ("SP", profile.sp_max, (45, 200, 95))
    ]
    gy = ry + 29
    for s_lbl, s_val, s_col in stats:
        l_surf = f_badge.render(s_lbl, True, (160, 175, 195))
        surface.blit(l_surf, (rx, gy))
        bar_x = rx + 18
        bar_w = rw - 50
        pygame.draw.rect(surface, (18, 22, 30), (bar_x, gy + 2, bar_w, 5), border_radius=1)
        fill_w = max(2, int(bar_w * min(1.0, s_val / 165.0)))
        pygame.draw.rect(surface, s_col, (bar_x, gy + 2, fill_w, 5), border_radius=1)
        pygame.draw.rect(surface, (55, 62, 78), (bar_x, gy + 2, bar_w, 5), 1, border_radius=1)
        v_surf = f_badge.render(str(s_val), True, HollowColors.TEXT_TITLE)
        surface.blit(v_surf, (bar_x + bar_w + 4, gy - 1))
        gy += 9

    # Passive Box with Automatic Word-Wrap
    pbox_y = gy + 3
    pbox_h = 36
    pbox_rect = pygame.Rect(rx, pbox_y, rw, pbox_h)
    pygame.draw.rect(surface, (14, 16, 24), pbox_rect, border_radius=2)
    pygame.draw.rect(surface, (55, 62, 78), pbox_rect, 1, border_radius=2)
    pygame.draw.rect(surface, HollowColors.GOLD_CREST, (rx, pbox_y, 2, pbox_h))

    p_header = f"PASSIVA: {profile.passive_name.upper()}"
    p_h_surf = f_badge.render(p_header, True, HollowColors.GOLD_CREST)
    surface.blit(p_h_surf, (rx + 6, pbox_y + 2))

    # Wrapped description inside passive box
    p_text_rect = pygame.Rect(rx + 6, pbox_y + 13, rw - 10, pbox_h - 15)
    render_wrapped_text(surface, profile.passive_desc, f_desc, HollowColors.TEXT_NORMAL, p_text_rect, line_height=10)

    # 4. Middle Section: 5 Combat Abilities (Compact horizontal rows)
    div_y = rect.y + 144
    pygame.draw.line(surface, (45, 52, 68), (rect.x + 8, div_y), (rect.right - 8, div_y), 1)

    skill_keys = ["j", "k", "e", "shift", "r"]
    sy = div_y + 4
    for sk_k in skill_keys:
        if sk_k in profile.skills:
            sk = profile.skills[sk_k]
            is_ult = (sk_k == "r")
            k_tag = f"[{'SH' if sk_k == 'shift' else sk_k.upper()}]"
            tag_s = f_key.render(k_tag, True, HollowColors.GOLD_CREST if is_ult else (180, 205, 245))
            surface.blit(tag_s, (rect.x + 8, sy))

            # Full skill name
            sname = sk.name
            name_s = f_desc.render(sname, True, HollowColors.TEXT_TITLE if not is_ult else HollowColors.GOLD_CREST)
            surface.blit(name_s, (rect.x + 36, sy))

            # Metric: damage / cost
            if sk_k == "j":
                m_str = f"{sk.damage}D"
            elif sk_k == "shift":
                m_str = "Blq 100%"
            else:
                m_str = f"{sk.damage}D|{sk.cost_value}{sk.cost_type}"
            m_s = f_badge.render(m_str, True, (160, 175, 195) if not is_ult else HollowColors.GOLD_CREST)
            surface.blit(m_s, (rect.right - m_s.get_width() - 8, sy))
            sy += 14

    # 5. Lower Section: 2-row Selection Grid (6 cols x 2 rows)
    grid_div_y = rect.y + 218
    pygame.draw.line(surface, (45, 52, 68), (rect.x + 8, grid_div_y), (rect.right - 8, grid_div_y), 1)

    card_w = 44
    card_h = 30
    gap_x = 4
    start_gx = rect.x + 9
    start_gy = grid_div_y + 4

    short_names = {
        "shaia": "SHAI", "lunaria": "LUNA", "ignis": "IGNI", "astra": "ASTR",
        "shinobi": "HAYA", "samurai": "KENS", "fighter": "RYUU", "knight": "GALA",
        "wizard": "IGNA", "samurai_archer": "HANZ", "kunoichi": "AYAM"
    }

    for idx, cid in enumerate(CHARACTER_ORDER):
        row = idx // 6
        col = idx % 6
        cx = start_gx + col * (card_w + gap_x)
        cy = start_gy + row * (card_h + 3)
        c_rect = pygame.Rect(cx, cy, card_w, card_h)

        is_sel = (idx == selected_idx)
        bg = (24, 30, 42, 240) if is_sel else (12, 14, 20, 220)
        border = tag_col if is_sel else (45, 52, 68)

        HollowCrestRenderer.draw_filigree_panel(surface, c_rect, bg_color=bg, border_color=border, corner_flourish=is_sel)

        t_img = thumbnails.get(cid)
        if t_img:
            # Scaled 22x22 inside button
            scaled_t = pygame.transform.smoothscale(t_img, (22, 22))
            surface.blit(scaled_t, (c_rect.x + 2, c_rect.y + (card_h - 22) // 2))

        # Hero short abbreviation
        sname = short_names.get(cid, cid[:4].upper())
        sn_surf = f_badge.render(sname, True, tag_col if is_sel else (135, 145, 165))
        surface.blit(sn_surf, (c_rect.x + 25, c_rect.y + 5))

        # Cursor badge indicator
        if is_sel:
            p_tag = "P1" if player_idx == 0 else "P2"
            pt_surf = f_badge.render(p_tag, True, (10, 10, 15))
            pt_w = pt_surf.get_width() + 4
            pygame.draw.rect(surface, tag_col, (c_rect.right - pt_w - 1, c_rect.bottom - 10, pt_w, 9), border_radius=1)
            surface.blit(pt_surf, (c_rect.right - pt_w + 1, c_rect.bottom - 10))
