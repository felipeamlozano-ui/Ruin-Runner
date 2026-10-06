"""
Hollow Knight Aesthetic UI Design System for Ruin Runner.
Provides procedural crests, filigree frames, atmospheric god rays, floating embers,
selection ornaments, and classic serif typography inspired by Hollow Knight.
"""

import math
import random
import pygame
from typing import List, Tuple, Optional

# ─────────────────────────────────────────────────────────────────────────────
# Color Tokens
# ─────────────────────────────────────────────────────────────────────────────
class HollowColors:
    # Backgrounds
    VOID_BLACK = (8, 9, 13)
    DEEP_CHARCOAL = (14, 16, 22)
    PANEL_FILL = (12, 14, 20, 230)
    
    # Typography
    TEXT_GLOW = (255, 255, 255)
    TEXT_TITLE = (248, 248, 252)
    TEXT_ACTIVE = (255, 255, 255)
    TEXT_NORMAL = (165, 172, 188)
    TEXT_MUTED = (105, 112, 128)
    TEXT_HINT = (130, 138, 155)
    
    # Accents & Metals
    SILVER_CREST = (200, 210, 225)
    GOLD_CREST = (225, 195, 125)
    EMBER_ORANGE = (255, 130, 45)
    EMBER_CORE = (255, 220, 140)
    SOUL_CYAN = (160, 220, 255)
    
    # Selection Highlights
    HIGHLIGHT_BAR = (255, 255, 255, 22)
    HIGHLIGHT_BORDER = (180, 195, 220, 160)
    SUBTLE_BORDER = (45, 52, 68)


# ─────────────────────────────────────────────────────────────────────────────
# Font Cache & Typography Manager
# ─────────────────────────────────────────────────────────────────────────────
class HollowFonts:
    _cache = {}
    
    @classmethod
    def get(cls, size: int, bold: bool = False, italic: bool = False) -> pygame.font.Font:
        key = (size, bold, italic)
        if key not in cls._cache:
            font_candidates = ["georgia", "palatinolinotype", "constantia", "cambria", "timesnewroman"]
            selected_font = None
            for name in font_candidates:
                try:
                    f = pygame.font.SysFont(name, size, bold=bold, italic=italic)
                    # Verify font renders properly
                    if f:
                        selected_font = f
                        break
                except Exception:
                    continue
            if not selected_font:
                selected_font = pygame.font.Font(None, size)
            cls._cache[key] = selected_font
        return cls._cache[key]


# ─────────────────────────────────────────────────────────────────────────────
# Atmospheric Particles & God Rays Engine
# ─────────────────────────────────────────────────────────────────────────────
class AtmosphericParticle:
    __slots__ = ("x", "y", "vx", "vy", "size", "alpha", "max_alpha", "lifetime", "age", "color", "sway_freq", "sway_amp")
    
    def __init__(self, w: int, h: int, theme: str = "void", spawn_bottom: bool = False):
        self.x = random.uniform(0, w)
        self.y = random.uniform(h * 0.8, h + 20) if spawn_bottom else random.uniform(0, h)
        self.size = random.uniform(1.2, 3.2)
        self.lifetime = random.uniform(4.0, 9.0)
        self.age = random.uniform(0, self.lifetime) if not spawn_bottom else 0.0
        self.sway_freq = random.uniform(0.8, 2.2)
        self.sway_amp = random.uniform(6.0, 18.0)
        
        if theme == "ember":
            # Amber / fiery sparks (like the Hollow Knight Options screen)
            self.vy = random.uniform(-25.0, -55.0)
            self.vx = random.uniform(-6.0, 6.0)
            self.max_alpha = random.randint(140, 240)
            self.color = random.choice([
                HollowColors.EMBER_ORANGE,
                HollowColors.EMBER_CORE,
                (255, 90, 30),
                (240, 170, 70)
            ])
        else:
            # Subtle luminous mist / void spores (like the Hollow Knight Main Menu)
            self.vy = random.uniform(-8.0, -18.0)
            self.vx = random.uniform(-3.0, 3.0)
            self.max_alpha = random.randint(70, 160)
            self.color = random.choice([
                (200, 215, 235),
                (170, 190, 220),
                (240, 245, 255),
                (140, 165, 200)
            ])
        self.alpha = self.max_alpha
            
    def update(self, dt: float, w: int, h: int, time_sec: float) -> bool:
        self.age += dt
        if self.age >= self.lifetime or self.y < -10:
            return False
        
        # Sway motion
        self.x += (self.vx + math.sin(time_sec * self.sway_freq + self.y * 0.05) * 4.0) * dt
        self.y += self.vy * dt
        
        # Fade in & out envelope
        prog = self.age / self.lifetime
        if prog < 0.2:
            self.alpha = int(self.max_alpha * (prog / 0.2))
        elif prog > 0.75:
            self.alpha = int(self.max_alpha * ((1.0 - prog) / 0.25))
        else:
            self.alpha = self.max_alpha
            
        return True


class AtmosphereFX:
    def __init__(self, width: int = 640, height: int = 360, theme: str = "void", particle_count: int = 42):
        self.width = width
        self.height = height
        self.theme = theme
        self.max_particles = particle_count
        self.particles: List[AtmosphericParticle] = [
            AtmosphericParticle(width, height, theme, spawn_bottom=False)
            for _ in range(particle_count)
        ]
        self.time_sec = 0.0
        self._vignette_surf: Optional[pygame.Surface] = None
        self._god_rays_surf: Optional[pygame.Surface] = None
        self._create_vignette()

    def _create_vignette(self):
        self._vignette_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        cx, cy = self.width / 2.0, self.height / 2.0
        max_dist = math.hypot(cx, cy)
        
        # Radial gradient vignette
        step_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        for r_step in range(6):
            ratio = (r_step + 1) / 6.0
            r_px = int(max_dist * (0.45 + ratio * 0.55))
            alpha = int(210 * (ratio ** 1.8))
            # Ellipse mask
            ell_rect = pygame.Rect(cx - r_px, cy - int(r_px * 0.75), r_px * 2, int(r_px * 1.5))
            pygame.draw.ellipse(self._vignette_surf, (5, 6, 9, int(alpha * 0.35)), ell_rect, width=int(max_dist * 0.15))
        
        # Direct dark corners
        pygame.draw.rect(self._vignette_surf, (4, 5, 8, 80), (0, 0, self.width, self.height), width=16)

    def update(self, dt: float):
        self.time_sec += dt
        # Update existing
        active = []
        for p in self.particles:
            if p.update(dt, self.width, self.height, self.time_sec):
                active.append(p)
        # Respawn depleted
        while len(active) < self.max_particles:
            active.append(AtmosphericParticle(self.width, self.height, self.theme, spawn_bottom=True))
        self.particles = active

    def draw_background(self, surface: pygame.Surface, show_rays: bool = True):
        h = self.height
        w = self.width
        
        # 1. Ultra-smooth continuous vertical twilight gradient (zero stepped rings)
        if self.theme == "ember":
            # Dark cavern with embers rising from warm hearth at bottom
            for y in range(h):
                t = y / float(h)
                glow = (t ** 2.2) * 0.45
                r = int(10 + glow * 55)
                g = int(11 + glow * 18)
                b = int(16 + glow * 10)
                pygame.draw.line(surface, (r, g, b), (0, y), (w, y))
        else:
            # Celestial void: soft moonlight filtering from above down to deep darkness
            for y in range(h):
                t = y / float(h)
                light = ((1.0 - t) ** 1.6) * 0.38
                r = int(9 + light * 25)
                g = int(12 + light * 34)
                b = int(18 + light * 50)
                pygame.draw.line(surface, (r, g, b), (0, y), (w, y))

        # 2. Floating Atmospheric Particles (spores or fire sparks)
        for p in self.particles:
            if p.alpha > 0:
                s = pygame.Surface((int(p.size * 2 + 2), int(p.size * 2 + 2)), pygame.SRCALPHA)
                col = (*p.color, p.alpha)
                pygame.draw.circle(s, col, (int(p.size + 1), int(p.size + 1)), int(p.size))
                surface.blit(s, (int(p.x - p.size), int(p.y - p.size)), special_flags=pygame.BLEND_RGBA_ADD)

        # 3. Vignette overlay for cinematic depth
        if self._vignette_surf:
            surface.blit(self._vignette_surf, (0, 0))


# ─────────────────────────────────────────────────────────────────────────────
# Procedural Hollow Knight Crest & Filigree Renderer
# ─────────────────────────────────────────────────────────────────────────────
class HollowCrestRenderer:
    @staticmethod
    def draw_selection_marker(surface: pygame.Surface, x: float, y: float, size: float = 6.0, is_right: bool = False, alpha: int = 255):
        """Draws the delicate Hollow Knight selection ornament flanking active menu options."""
        s = pygame.Surface((int(size * 4 + 4), int(size * 4 + 4)), pygame.SRCALPHA)
        cx, cy = size * 2 + 2, size * 2 + 2
        col = (255, 255, 255, alpha)
        gold = (245, 220, 150, alpha)
        
        # Central diamond
        pts_diamond = [
            (cx, cy - size),
            (cx + size * 0.7, cy),
            (cx, cy + size),
            (cx - size * 0.7, cy)
        ]
        pygame.draw.polygon(s, col, pts_diamond)
        pygame.draw.polygon(s, gold, [(cx, cy - size * 0.4), (cx + size * 0.35, cy), (cx, cy + size * 0.4), (cx - size * 0.35, cy)])
        
        # Small outward petal flourish
        dir_mult = 1.0 if not is_right else -1.0
        tip_x = cx - size * 1.5 * dir_mult
        pygame.draw.polygon(s, col, [(cx, cy - size * 0.4), (tip_x, cy), (cx, cy + size * 0.4)])
        
        surface.blit(s, (int(x - cx), int(y - cy)))

    @staticmethod
    def draw_section_divider(surface: pygame.Surface, cx: float, cy: float, width: float = 280.0, alpha: int = 210):
        """Draws the thin filigree divider with central jewel (as seen in Hollow Knight Options)."""
        col = (230, 235, 245, alpha)
        col_fade = (180, 195, 215, int(alpha * 0.45))
        
        half_w = width / 2.0
        # Central gem
        pygame.draw.circle(surface, col, (int(cx), int(cy)), 3)
        pygame.draw.circle(surface, (255, 255, 255, alpha), (int(cx), int(cy)), 1)
        
        # Side flourish loops
        wing_w = 20.0
        pygame.draw.lines(surface, col, False, [(cx - 3, cy), (cx - 10, cy - 3), (cx - wing_w, cy)], 1)
        pygame.draw.lines(surface, col, False, [(cx - 3, cy), (cx - 10, cy + 3), (cx - wing_w, cy)], 1)
        pygame.draw.lines(surface, col, False, [(cx + 3, cy), (cx + 12, cy - 3), (cx + wing_w, cy)], 1)
        pygame.draw.lines(surface, col, False, [(cx + 3, cy), (cx + 12, cy + 3), (cx + wing_w, cy)], 1)
        
        # Tapered lateral lines
        pygame.draw.line(surface, col, (int(cx - wing_w), int(cy)), (int(cx - half_w * 0.65), int(cy)), 1)
        pygame.draw.line(surface, col_fade, (int(cx - half_w * 0.65), int(cy)), (int(cx - half_w), int(cy)), 1)
        pygame.draw.line(surface, col, (int(cx + wing_w), int(cy)), (int(cx + half_w * 0.65), int(cy)), 1)
        pygame.draw.line(surface, col_fade, (int(cx + half_w * 0.65), int(cy)), (int(cx + half_w), int(cy)), 1)

    @staticmethod
    def draw_master_title_crest(surface: pygame.Surface, cx: float, cy: float, width: float = 300.0, alpha: int = 240):
        """
        Draws the Hollow Knight under-title crest:
        Carapace shield at center, with curving baroque wings and scrollwork.
        """
        col = (240, 245, 255, alpha)
        gold = (235, 215, 160, int(alpha * 0.8))
        
        # 1. Central Carapace Emblem
        cw, ch = 22, 28
        carapace_rect = pygame.Rect(cx - cw // 2, cy - ch // 2, cw, ch)
        pygame.draw.ellipse(surface, (12, 14, 20), carapace_rect)
        pygame.draw.ellipse(surface, col, carapace_rect, 2)
        
        # Internal segments
        pygame.draw.line(surface, col, (cx - 8, cy - 5), (cx + 8, cy - 5), 1)
        pygame.draw.line(surface, col, (cx - 9, cy + 3), (cx + 9, cy + 3), 1)
        pygame.draw.line(surface, gold, (cx, cy - 10), (cx, cy + 10), 1)
        
        # Bottom pointed tip
        pygame.draw.lines(surface, col, False, [(cx - 7, cy + 11), (cx, cy + 22), (cx + 7, cy + 11)], 2)
        pygame.draw.circle(surface, col, (int(cx), int(cy + 22)), 2)
        
        # 2. Symmetrical Baroque Scrolls extending horizontally
        half_span = width * 0.46
        for side in (-1, 1):
            # Main sweeping under-arch
            p0 = (cx + side * 12, cy + 4)
            p1 = (cx + side * (half_span * 0.35), cy + 14)
            p2 = (cx + side * (half_span * 0.70), cy + 4)
            p3 = (cx + side * half_span, cy - 8)
            
            # Draw arch segments with thickness 2
            pygame.draw.lines(surface, col, False, [p0, p1, p2, p3], 2)
            
            # Secondary inner spiral
            spiral_cx = cx + side * (half_span * 0.45)
            spiral_cy = cy + 2
            pygame.draw.circle(surface, col, (int(spiral_cx), int(spiral_cy)), 4, 1)
            pygame.draw.circle(surface, gold, (int(spiral_cx), int(spiral_cy)), 1)
            
            # End flourish curl
            pygame.draw.circle(surface, col, (int(p3[0]), int(p3[1])), 4, 2)
            pygame.draw.circle(surface, gold, (int(p3[0]), int(p3[1])), 2)

    @staticmethod
    def draw_top_flourish(surface: pygame.Surface, cx: float, cy: float, width: float = 160.0, alpha: int = 220):
        """Draws the delicate top crown flourish above the main title (seen in Hollow Knight)."""
        col = (230, 235, 245, alpha)
        hw = width / 2.0
        # Central small ring
        pygame.draw.circle(surface, col, (int(cx), int(cy)), 3, 1)
        
        for side in (-1, 1):
            pts = [
                (cx + side * 5, cy),
                (cx + side * (hw * 0.4), cy - 6),
                (cx + side * (hw * 0.75), cy - 2),
                (cx + side * hw, cy - 7)
            ]
            pygame.draw.lines(surface, col, False, pts, 1)
            pygame.draw.circle(surface, col, (int(cx + side * hw), int(cy - 7)), 2)

    @staticmethod
    def draw_filigree_panel(surface: pygame.Surface, rect: pygame.Rect, bg_color: Tuple[int, int, int, int] = (12, 14, 20, 230), border_color: Tuple[int, int, int] = (65, 72, 88), corner_flourish: bool = True):
        """Draws a noble dark panel with fine filigree framing and optional corner fleurons."""
        # 1. Translucent Background
        panel_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        panel_surf.fill(bg_color)
        surface.blit(panel_surf, rect.topleft)
        
        # 2. Main 1px Outer Border
        pygame.draw.rect(surface, border_color, rect, 1)
        
        # 3. Inner Delicate Inset Line
        if rect.width > 16 and rect.height > 16:
            inset_rect = rect.inflate(-6, -6)
            inner_col = (border_color[0] // 2, border_color[1] // 2, border_color[2] // 2)
            pygame.draw.rect(surface, inner_col, inset_rect, 1)
            
            # 4. Corner Diamonds / Fleurons
            if corner_flourish:
                c_pts = [
                    (inset_rect.left, inset_rect.top),
                    (inset_rect.right, inset_rect.top),
                    (inset_rect.left, inset_rect.bottom),
                    (inset_rect.right, inset_rect.bottom)
                ]
                for px, py in c_pts:
                    pygame.draw.circle(surface, border_color, (px, py), 2)
                    pygame.draw.circle(surface, (255, 255, 255), (px, py), 1)

    @staticmethod
    def draw_ancient_pedestal(surface: pygame.Surface, pos: pygame.math.Vector2, col: Tuple[int, int, int]):
        """Draws an ancient carved stone dais with subtle runic illumination and upward mist."""
        px, py = int(pos.x), int(pos.y) + 5
        beam_h = max(24, int(py - 48))
        beam_surf = pygame.Surface((120, beam_h), pygame.SRCALPHA)
        poly = [(42, 0), (78, 0), (120, beam_h), (0, beam_h)]
        beam_alpha = int(18 + 6 * math.sin(pygame.time.get_ticks() * 0.0025))
        pygame.draw.polygon(beam_surf, (*col, beam_alpha), poly)
        surface.blit(beam_surf, (px - 60, 48), special_flags=pygame.BLEND_RGBA_ADD)
        
        # Base Stone Ellipse
        base_w, base_h = 108, 20
        pygame.draw.ellipse(surface, (6, 7, 10), (px - base_w // 2, py - base_h // 2 + 5, base_w, base_h))
        pygame.draw.ellipse(surface, (22, 25, 34), (px - base_w // 2, py - base_h // 2, base_w, base_h))
        pygame.draw.ellipse(surface, (60, 68, 85), (px - base_w // 2, py - base_h // 2, base_w, base_h), 1)
        
        # Inner Rune Ring
        inner_w, inner_h = 76, 12
        pygame.draw.ellipse(surface, (14, 16, 22), (px - inner_w // 2, py - inner_h // 2, inner_w, inner_h))
        pygame.draw.ellipse(surface, (*col, 160), (px - inner_w // 2, py - inner_h // 2, inner_w, inner_h), 1)
        
        # Orbiting Runic Sigil Sparks
        t = pygame.time.get_ticks() * 0.0018
        for i in range(6):
            ang = t + i * (math.pi * 2 / 6)
            gx = px + int(math.cos(ang) * (inner_w // 2 - 3))
            gy = py + int(math.sin(ang) * (inner_h // 2 - 2))
            pygame.draw.circle(surface, (255, 255, 255, 200), (gx, gy), 1)
            pygame.draw.circle(surface, (*col, 180), (gx, gy), 2, 1)

    @staticmethod
    def draw_hollow_button(surface: pygame.Surface, rect: pygame.Rect, text: str, font: pygame.font.Font, is_hovered: bool = False, is_active: bool = False, text_color: Optional[Tuple[int, int, int]] = None) -> None:
        """Draws an authentic Hollow Knight style button with subtle hover line and fleurons."""
        if is_hovered or is_active:
            # Subtle dark glass fill
            b_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            b_surf.fill((255, 255, 255, 14 if is_hovered else 25))
            surface.blit(b_surf, rect.topleft)
            
            # Subtle top and bottom border lines
            pygame.draw.line(surface, (215, 225, 245, 180), (rect.left + 8, rect.top), (rect.right - 8, rect.top), 1)
            pygame.draw.line(surface, (215, 225, 245, 180), (rect.left + 8, rect.bottom), (rect.right - 8, rect.bottom), 1)
            
            # Selection markers on sides
            pulse = math.sin(pygame.time.get_ticks() * 0.005) * 2.0
            mid_y = rect.centery
            HollowCrestRenderer.draw_selection_marker(surface, rect.left - 4 - pulse, mid_y, size=4.5, is_right=False)
            HollowCrestRenderer.draw_selection_marker(surface, rect.right + 4 + pulse, mid_y, size=4.5, is_right=True)
            col = text_color or (255, 255, 255)
        else:
            pygame.draw.rect(surface, (45, 52, 65), rect, 1)
            col = text_color or (170, 180, 195)
            
        txt_surf = font.render(text, True, col)
        surface.blit(txt_surf, txt_surf.get_rect(center=rect.center))



# ─────────────────────────────────────────────────────────────────────────────
# Hollow Knight Title & Typography Renderer
# ─────────────────────────────────────────────────────────────────────────────
class HollowText:
    @staticmethod
    def render_title_with_glow(surface: pygame.Surface, text: str, cx: float, cy: float, size: int = 34, letter_spacing: int = 4):
        """Renders crisp serif title with subtle soft shadow."""
        font = HollowFonts.get(size, bold=True)
        glyphs_shadow = [font.render(c, True, (0, 0, 0)) for c in text]
        glyphs_core = [font.render(c, True, (250, 250, 255)) for c in text]
        
        total_w = sum(g.get_width() for g in glyphs_core) + letter_spacing * (len(text) - 1)
        start_x = cx - total_w / 2.0
        
        # 1. Soft clean drop shadow
        curr_x = start_x + 1
        for g in glyphs_shadow:
            surface.blit(g, (int(curr_x), int(cy - g.get_height() / 2.0 + 2)))
            curr_x += g.get_width() + letter_spacing
            
        # 2. Crisp Core text
        curr_x = start_x
        for g in glyphs_core:
            surface.blit(g, (int(curr_x), int(cy - g.get_height() / 2.0)))
            curr_x += g.get_width() + letter_spacing
