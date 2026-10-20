import pygame
import os
import math
from config.settings import SETTINGS
from config.colors import RED, BLUE, UI_BACKGROUND, WHITE
from entities.player import Player
from ui.input_prompt_icon import InputPromptIcon

from engine.text_cache import get_cached_text

def _render_hud_text(font: pygame.font.Font, text: str, color: tuple) -> pygame.Surface:
    """Zero-overhead text caching helper. Avoids 1200+ CPU font.render() calls per second."""
    return get_cached_text(font, text, color)

class HUD:
    """Heads-Up Display for player stats (Health, Mana, Stamina, Skill Hotbar, and Boss Health)."""
    
    def __init__(self, player: Player, stage_title: str = "FASE 1: AS CATACUMBAS", player_index: int = 0):
        self.player = player
        self.stage_title = stage_title
        self.active_boss = None
        self.player_index = player_index
        
        # Pre-allocated glassmorphic panel surface
        self._panel_bg = None
        self._panel_size = None
        
        # Ghost Damage Lag & Tactical Glow
        self.ghost_hp = float(getattr(self.player, "health", 100))
        self.ghost_timer = 0.0
        self.mana_glow_phase = 0.0
        
        # Initialize fonts
        pygame.font.init()
        self.font_title = pygame.font.SysFont("Arial", 13, bold=True)
        self.font_stat = pygame.font.SysFont("Courier New", 10, bold=True)
        self.font_keys = pygame.font.SysFont("Arial", 10, bold=True)
        self.font_badge = pygame.font.SysFont("Arial", 9, bold=True)
        self.font_cost = pygame.font.SysFont("Arial", 8, bold=True)
        self.font_boss = pygame.font.SysFont("Arial", 13, bold=True)
        self.font_boss_val = pygame.font.SysFont("Courier New", 9, bold=True)
        
        # Load Skill Icons from skills directory
        self._load_skill_icons()
        
    def _load_skill_icons(self):
        skills_dir = os.path.join("assets", "sprites", "icons", "skills")
        if not os.path.exists(skills_dir):
            skills_dir = os.path.join("assets", "sprites", "fantasy_skills", "64x64")
            
        self.skill_icons = {}
        prof = getattr(self.player, "profile", None)
        self._cached_char_id = getattr(self.player, "character_id", None)
        
        # Player 1 vs Player 2 hotkey labels
        is_p2 = (self.player_index == 1)
        k_atk = "N1" if is_p2 else "J"
        k_mag = "N2" if is_p2 else "K"
        k_dsh = "N0" if is_p2 else "Q"
        k_aoe = "N4" if is_p2 else "E"
        k_def = "N6" if is_p2 else "Shift"
        k_ult = "N5" if is_p2 else "R"

        if prof and hasattr(prof, "skills") and prof.skills:
            j_s = prof.skills.get("j")
            k_s = prof.skills.get("k")
            e_s = prof.skills.get("e")
            sh_s = prof.skills.get("shift")
            r_s = prof.skills.get("r")
            
            icon_files = {
                "attack": (j_s.icon_file if j_s else "human_combat_01.png", k_atk),
                "magic": (k_s.icon_file if k_s else "demon_magic_01.png", k_mag),
                "dash": ("elf_support_05.png", k_dsh),
                "aoe": (e_s.icon_file if e_s else "human_support_02.png", k_aoe),
                "shield": (sh_s.icon_file if sh_s else "human_defense_07.png", k_def),
                "ultimate": (r_s.icon_file if r_s else "demon_combat_12.png", k_ult)
            }
        else:
            icon_files = {
                "attack": ("human_combat_01.png", k_atk),
                "magic": ("arcane_magic_06.png", k_mag),
                "dash": ("elf_support_05.png", k_dsh),
                "aoe": ("arcane_combat_01.png", k_aoe),
                "shield": ("human_defense_07.png", k_def),
                "ultimate": ("demon_combat_12.png", k_ult)
            }
        
        is_coop = (self.player_index == 1 or getattr(self.player, "companion", None) is not None)
        slot_size = 15 if is_coop else 21
        for key, (fname, hotkey) in icon_files.items():
            p = os.path.join(skills_dir, fname)
            if not os.path.exists(p):
                p = os.path.join("assets", "sprites", "fantasy_skills", "64x64", fname)
            if os.path.exists(p):
                img = pygame.image.load(p).convert_alpha()
                brect = img.get_bounding_rect()
                if brect.width > 0 and brect.height > 0:
                    cropped = img.subsurface(brect)
                    scaled = pygame.transform.smoothscale(cropped, (slot_size, slot_size))
                else:
                    scaled = pygame.transform.smoothscale(img, (slot_size, slot_size))
                self.skill_icons[key] = (scaled, hotkey)
            else:
                self.skill_icons[key] = (None, hotkey)

        # Dynamic Input Prompt Icons (Authentic animated pixel-art buttons)
        self.action_by_skill = {
            "attack": "ATTACK",
            "magic": "SKILL",
            "dash": "DASH",
            "aoe": "SKILL_AOE",
            "shield": "DEFEND",
            "ultimate": "ULTIMATE",
        }
        icon_sz = 14 if is_coop else 16
        self.input_icons = {
            s_key: InputPromptIcon(act, player_index=self.player_index, size=icon_sz)
            for s_key, act in self.action_by_skill.items()
        }

    def get_dynamic_skill_cost(self, s_key: str) -> str:
        """Dynamically retrieves and formats skill cost from player profile and live state."""
        prof = getattr(self.player, "profile", None)
        skills = getattr(prof, "skills", {}) if prof else {}
        is_mage = getattr(self.player, "archetype", "") == "mage"
        
        if s_key == "attack":
            skill = skills.get("j")
            if skill:
                return f"{skill.cost_value} {skill.cost_type}"
            return "3 MP" if is_mage else "8 SP"
            
        elif s_key == "magic":
            skill = skills.get("k")
            if skill:
                return f"{skill.cost_value} {skill.cost_type}"
            return "35 MP" if is_mage else "30 MP"
            
        elif s_key == "dash":
            dash_cost = 15 if getattr(self.player, "passive_id", "") == "shinobi_shadow_step" else 25
            return f"{dash_cost} SP"
            
        elif s_key == "aoe":
            skill = skills.get("e")
            if skill:
                return f"{skill.cost_value} {skill.cost_type}"
            return "30 MP" if is_mage else "30 SP"
            
        elif s_key == "shield":
            skill = skills.get("shift")
            if skill:
                return f"{skill.cost_value} {skill.cost_type}"
            cost_type = "MP/s" if is_mage else "SP/s"
            return f"3 {cost_type}"
            
        elif s_key == "ultimate":
            skill = skills.get("r")
            if skill:
                return f"{skill.cost_value} {skill.cost_type}"
            cost_val = int(getattr(self.player, "max_mana", 100))
            return f"{cost_val} MP"
            
        return ""
        
    def draw_bar(self, surface: pygame.Surface, x: int, y: int, width: int, height: int, ratio: float, fill_color: tuple, highlight_color: tuple, bg_color: tuple, label: str, value_text: str, ghost_ratio: float = None, pips: int = 0, glow: bool = False):
        # Background box
        pygame.draw.rect(surface, bg_color, (x, y, width, height), border_radius=3)
        
        # Ghost Lag Bar (Damage delay trail)
        if ghost_ratio is not None and ghost_ratio > ratio:
            ghost_w = max(0, int(width * max(0.0, min(1.0, ghost_ratio))))
            if ghost_w > 0:
                pygame.draw.rect(surface, (210, 140, 35), (x, y, ghost_w, height), border_radius=3)

        # Filled Bar
        fill_w = max(0, int(width * max(0.0, min(1.0, ratio))))
        if fill_w > 0:
            pygame.draw.rect(surface, fill_color, (x, y, fill_w, height), border_radius=3)
            if height > 4:
                pygame.draw.line(surface, highlight_color, (x + 2, y + 1), (x + fill_w - 2, y + 1))
                
        # Tactical Pips (e.g. Dash intervals)
        if pips > 1:
            for p in range(1, pips):
                pip_x = x + int(width * (p / pips))
                pygame.draw.line(surface, (20, 25, 35), (pip_x, y), (pip_x, y + height - 1), 1)

        # Outer Border & Glow
        border_col = (80, 85, 100)
        if glow:
            pulse = (math.sin(self.mana_glow_phase) + 1.0) * 0.5
            border_col = (int(200 + 55 * pulse), int(170 + 60 * pulse), int(50 + 40 * pulse))
        pygame.draw.rect(surface, border_col, (x, y, width, height), 1, border_radius=3)
        
        # Stat label (Cached zero-overhead)
        lbl_surf = _render_hud_text(self.font_stat, label, (240, 240, 240))
        surface.blit(lbl_surf, (x - 20, y - 1))
        
        # Value text (Cached zero-overhead)
        val_surf = _render_hud_text(self.font_stat, value_text, (255, 255, 255))
        surface.blit(val_surf, (x + width - val_surf.get_width() - 4, y - 1))

    def draw(self, surface: pygame.Surface):
        # Update ghost hp lag and glow
        cur_hp = float(self.player.health)
        if cur_hp < self.ghost_hp:
            self.ghost_timer += 0.016
            if self.ghost_timer >= 0.35:
                self.ghost_hp = max(cur_hp, self.ghost_hp - 1.2)
        else:
            self.ghost_hp = cur_hp
            self.ghost_timer = 0.0

        import math
        self.mana_glow_phase = (self.mana_glow_phase + 0.06) % (2.0 * math.pi)

        # Verify if player profile changed (e.g. character swap)
        if getattr(self.player, "character_id", None) != getattr(self, "_cached_char_id", None):
            self._load_skill_icons()

        is_coop = (self.player_index == 1 or getattr(self.player, "companion", None) is not None)
        
        # 1. Player Status Glassmorphic Panel (Top-Left for P1, Top-Right for P2)
        panel_w, panel_h = (126, 52) if is_coop else (152, 60)
        if self.player_index == 1:
            panel_x, panel_y = surface.get_width() - panel_w - 8, 8
        else:
            panel_x, panel_y = 8, 8
        
        # Reusable Glassmorphic background (0 allocation per frame)
        if self._panel_bg is None or self._panel_size != (panel_w, panel_h):
            self._panel_bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            self._panel_bg.fill((15, 18, 28, 220))
            self._panel_size = (panel_w, panel_h)
        surface.blit(self._panel_bg, (panel_x, panel_y))
        
        # Dual-tone frame border
        border_col = (110, 140, 210) if self.player_index == 1 else (70, 80, 110)
        pygame.draw.rect(surface, border_col, (panel_x, panel_y, panel_w, panel_h), 1, border_radius=4)
        pygame.draw.rect(surface, (25, 30, 45), (panel_x + 1, panel_y + 1, panel_w - 2, panel_h - 2), 1, border_radius=3)
        
        # Player Tag Indicator Tab (Neat badge atop status frame, zero collision with HP)
        p_tag = "P2" if self.player_index == 1 else "P1"
        tag_col = (130, 210, 255) if self.player_index == 1 else (255, 205, 90)
        tag_bg = (20, 32, 55) if self.player_index == 1 else (45, 36, 18)
        tag_border = (80, 140, 220) if self.player_index == 1 else (175, 135, 55)
        pill_w, pill_h = 22, 13
        pill_x = panel_x + 6
        pill_y = panel_y - 6
        pygame.draw.rect(surface, tag_bg, (pill_x, pill_y, pill_w, pill_h), border_radius=3)
        pygame.draw.rect(surface, tag_border, (pill_x, pill_y, pill_w, pill_h), 1, border_radius=3)
        tag_surf = _render_hud_text(self.font_keys, p_tag, tag_col)
        surface.blit(tag_surf, (pill_x + 4, pill_y - 1))
        
        # Bars configuration
        bar_w = 80 if is_coop else 110
        hp_h = 10 if is_coop else 12
        res_h = 9 if is_coop else 11
        bx = panel_x + 26
        
        # Health Bar (HP) with Ghost Damage Lag
        hp_ratio = self.player.health / max(1, self.player.max_health)
        ghost_ratio = self.ghost_hp / max(1, self.player.max_health)
        hp_text = f"{int(self.player.health)}/{int(self.player.max_health)}"
        self.draw_bar(
            surface, bx, panel_y + 6, bar_w, hp_h, hp_ratio,
            (215, 35, 35), (255, 110, 110), (50, 12, 15), "HP", hp_text,
            ghost_ratio=ghost_ratio
        )
        
        # Mana Bar (MP) with Ultimate Ready Glow
        mp_ratio = self.player.mana / max(1.0, self.player.max_mana)
        mp_text = f"{int(self.player.mana)}/{int(self.player.max_mana)}"
        mana_ready = (mp_ratio >= 0.95)
        self.draw_bar(
            surface, bx, panel_y + (19 if is_coop else 25), bar_w, res_h, mp_ratio,
            (35, 120, 235), (120, 195, 255), (12, 25, 50), "MP", mp_text,
            glow=mana_ready
        )
        
        # Stamina Bar (SP) with Tactical Dash Pips
        max_sp = float(getattr(self.player, "max_stamina", 100.0))
        sp_ratio = self.player.stamina / max(1.0, max_sp)
        sp_text = f"{int(self.player.stamina)}/{int(max_sp)}"
        dash_cost = 15 if getattr(self.player, "passive_id", "") == "shinobi_shadow_step" else 25
        num_pips = max(2, int(max_sp // dash_cost))
        self.draw_bar(
            surface, bx, panel_y + (32 if is_coop else 42), bar_w, res_h, sp_ratio,
            (35, 190, 70), (120, 245, 140), (12, 45, 20), "SP", sp_text,
            pips=num_pips
        )
        
        # 2. Skill Hotbar Frame (Bottom-Left for P1, Bottom-Right for P2)
        slot_w, slot_h = (19, 19) if is_coop else (25, 25)
        slot_gap = 3 if is_coop else 5
        dx = slot_w + slot_gap
        skill_keys = ["attack", "magic", "dash", "aoe", "shield", "ultimate"]
        total_hotbar_w = len(skill_keys) * dx - slot_gap
        if self.player_index == 1:
            hotbar_x = surface.get_width() - total_hotbar_w - 8
        else:
            hotbar_x = 8
        hotbar_y = surface.get_height() - (38 if is_coop else 46)
        for idx, s_key in enumerate(skill_keys):
            sx = hotbar_x + idx * dx
            sy = hotbar_y
            
            is_ult = (s_key == "ultimate")
            ult_cost = float(getattr(self.player, "max_mana", 100.0))
            ult_ready = is_ult and (self.player.mana >= ult_cost * 0.95)
            
            # Slot background
            s_bg = pygame.Surface((slot_w, slot_h), pygame.SRCALPHA)
            if ult_ready:
                # Golden radiant background
                s_bg.fill((60, 45, 15, 240))
            else:
                s_bg.fill((20, 25, 38, 220))
            surface.blit(s_bg, (sx, sy))
            
            # Slot border (pulsing gold if ult ready)
            if ult_ready:
                import math
                pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.008)
                border_col = (int(255 * (0.8 + 0.2 * pulse)), int(215 * (0.8 + 0.2 * pulse)), 50)
                pygame.draw.rect(surface, border_col, (sx - 1, sy - 1, slot_w + 2, slot_h + 2), 2, border_radius=3)
            else:
                pygame.draw.rect(surface, (70, 85, 120), (sx, sy, slot_w, slot_h), 1, border_radius=3)
            
            icon_surf, hotkey = self.skill_icons.get(s_key, (None, ""))
            if icon_surf:
                ix = sx + (slot_w - icon_surf.get_width()) // 2
                iy = sy + (slot_h - icon_surf.get_height()) // 2
                if is_ult and not ult_ready:
                    dimmed = icon_surf.copy()
                    dimmed.set_alpha(150)
                    surface.blit(dimmed, (ix, iy))
                else:
                    surface.blit(icon_surf, (ix, iy))
                
            # Dynamic Input Prompt Icon (Authentic animated pixel-art button with live click feedback)
            prompt_icon = self.input_icons.get(s_key)
            if prompt_icon:
                px = sx + (slot_w - prompt_icon.get_width()) // 2
                py = sy - prompt_icon.get_height() - 2
                prompt_icon.draw(surface, px, py)
                if ult_ready:
                    pygame.draw.circle(surface, (255, 220, 80), (px + prompt_icon.get_width() - 1, py + 1), 2)
            
            # Dynamic Cost label (centered horizontally below slot, no bottom cutoff)
            cost = self.get_dynamic_skill_cost(s_key)
            if cost:
                cost_col = (255, 220, 120) if is_ult else ((160, 225, 255) if "MP" in cost else (140, 255, 160))
                cost_surf = _render_hud_text(self.font_cost, cost, cost_col)
                cost_x = sx + (slot_w - cost_surf.get_width()) // 2
                cost_y = sy + slot_h + 2
                surface.blit(cost_surf, (cost_x, cost_y))
        
        # 3. Stage Title Badge (Top-Center) - only display when not in an active boss fight and for player 0
        if self.stage_title and self.player_index == 0 and not (self.active_boss and not self.active_boss.is_dead):
            stage_surf = _render_hud_text(self.font_title, self.stage_title, (255, 215, 100))
            stg_w = stage_surf.get_width() + 16
            stg_h = stage_surf.get_height() + 8
            center_x = (surface.get_width() - stg_w) // 2
            # Maintain safe visual clearance to never overlap P1 status panel or HP numbers
            min_clearance_x = panel_x + panel_w + 14
            stg_x = max(center_x, min_clearance_x) if not is_coop else center_x
            stg_y = 10
            
            if getattr(self, "_stage_badge_bg", None) is None or self._stage_badge_bg.get_size() != (stg_w, stg_h):
                self._stage_badge_bg = pygame.Surface((stg_w, stg_h), pygame.SRCALPHA)
                self._stage_badge_bg.fill((15, 18, 28, 200))
                pygame.draw.rect(self._stage_badge_bg, (120, 100, 50), (0, 0, stg_w, stg_h), 1, border_radius=3)
            surface.blit(self._stage_badge_bg, (stg_x, stg_y))
            surface.blit(stage_surf, (stg_x + 8, stg_y + 4))

        # 4. Dual Boss Bar (Top-Center: 10,000 HP + 2,000 Poise Shield)
        if self.active_boss and not self.active_boss.is_dead:
            boss = self.active_boss
            boss_hp_ratio = boss.health / max(1, boss.max_health)
            boss_shield_max = getattr(boss, "max_shield", 2000)
            boss_shield = getattr(boss, "shield", 0)
            boss_shield_ratio = boss_shield / max(1, boss_shield_max)
            
            bar_width = 240
            hp_h = 10
            shield_h = 6
            bar_x = (surface.get_width() - bar_width) // 2
            bar_y = 16
            
            # Boss Frame Box
            total_h = 52
            boss_bg = pygame.Surface((bar_width + 20, total_h), pygame.SRCALPHA)
            boss_bg.fill((15, 10, 15, 230))
            surface.blit(boss_bg, (bar_x - 10, bar_y - 12))
            pygame.draw.rect(surface, (150, 40, 40), (bar_x - 10, bar_y - 12, bar_width + 20, total_h), 1, border_radius=4)
            
            # Title & Stagger Alert Label
            b_name = getattr(boss, "name", "REI ESQUELETO").upper()
            if getattr(boss, "state", "") == "STAGGERED" or boss_shield <= 0:
                import math
                pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.018)
                lbl_col = (255, int(220 + 35 * pulse), int(40 * pulse))
                boss_name = _render_hud_text(self.font_boss, "[ POSTURA QUEBRADA - VULNERÁVEL! ]", lbl_col)
            elif getattr(boss, "enraged", False):
                boss_name = _render_hud_text(self.font_boss, f"[ FÚRIA ] {b_name}", (255, 110, 50))
            else:
                boss_name = _render_hud_text(self.font_boss, f"— {b_name} —", (255, 220, 120))
            surface.blit(boss_name, (bar_x + (bar_width - boss_name.get_width()) // 2, bar_y - 11))
            
            # 1. HP Bar (Red)
            pygame.draw.rect(surface, (40, 10, 10), (bar_x, bar_y + 6, bar_width, hp_h), border_radius=2)
            fill_hp = int(bar_width * max(0.0, min(1.0, boss_hp_ratio)))
            if fill_hp > 0:
                hp_col = (240, 50, 20) if getattr(boss, "enraged", False) else (210, 25, 25)
                pygame.draw.rect(surface, hp_col, (bar_x, bar_y + 6, fill_hp, hp_h), border_radius=2)
                pygame.draw.line(surface, (255, 150, 120), (bar_x + 1, bar_y + 7), (bar_x + fill_hp - 1, bar_y + 7))
            pygame.draw.rect(surface, (180, 50, 50), (bar_x, bar_y + 6, bar_width, hp_h), 1, border_radius=2)
            
            # HP numeric readout
            hp_txt = _render_hud_text(self.font_boss_val, f"HP: {int(boss.health):,}/{int(boss.max_health):,}".replace(",", "."), (255, 240, 240))
            surface.blit(hp_txt, (bar_x + 5, bar_y + 6))
            
            # Shield numeric readout (positioned cleanly ABOVE the poise shield bar)
            sh_txt = _render_hud_text(self.font_boss_val, f"POSTURA: {int(boss_shield):,}/{int(boss_shield_max):,}".replace(",", "."), (180, 230, 255))
            surface.blit(sh_txt, (bar_x + 5, bar_y + 19))
            
            # 2. Poise Shield Bar (Gold / Cyan) - drawn separated below the posture text
            pygame.draw.rect(surface, (15, 25, 35), (bar_x, bar_y + 31, bar_width, shield_h), border_radius=2)
            fill_sh = int(bar_width * max(0.0, min(1.0, boss_shield_ratio)))
            if fill_sh > 0:
                sh_col = (70, 210, 255)
                pygame.draw.rect(surface, sh_col, (bar_x, bar_y + 31, fill_sh, shield_h), border_radius=2)
                pygame.draw.line(surface, (200, 245, 255), (bar_x + 1, bar_y + 31), (bar_x + fill_sh - 1, bar_y + 31))
            pygame.draw.rect(surface, (100, 180, 220), (bar_x, bar_y + 31, bar_width, shield_h), 1, border_radius=2)


