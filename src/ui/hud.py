import pygame
import os
from config.settings import SETTINGS
from config.colors import RED, BLUE, UI_BACKGROUND, WHITE
from entities.player import Player

class HUD:
    """Heads-Up Display for player stats (Health, Mana, Stamina, Skill Hotbar, and Boss Health)."""
    
    def __init__(self, player: Player, stage_title: str = "FASE 1: AS CATACUMBAS"):
        self.player = player
        self.stage_title = stage_title
        self.active_boss = None
        
        # Initialize fonts
        pygame.font.init()
        self.font_title = pygame.font.SysFont("Arial", 13, bold=True)
        self.font_stat = pygame.font.SysFont("Courier New", 10, bold=True)
        self.font_keys = pygame.font.SysFont("Arial", 10, bold=True)
        self.font_badge = pygame.font.SysFont("Arial", 9, bold=True)
        self.font_cost = pygame.font.SysFont("Arial", 8, bold=True)
        self.font_boss = pygame.font.SysFont("Arial", 14, bold=True)
        
        # Load Skill Icons from skills directory
        skills_dir = os.path.join("assets", "sprites", "icons", "skills")
        if not os.path.exists(skills_dir):
            skills_dir = os.path.join("assets", "sprites", "fantasy_skills", "64x64")
            
        self.skill_icons = {}
        prof = getattr(self.player, "profile", None)
        if prof and hasattr(prof, "skills") and prof.skills:
            j_s = prof.skills.get("j")
            k_s = prof.skills.get("k")
            e_s = prof.skills.get("e")
            sh_s = prof.skills.get("shift")
            r_s = prof.skills.get("r")
            
            icon_map = {
                "attack": (j_s.icon_file if j_s else "human_combat_01.png", "J", f"{j_s.cost_value} {j_s.cost_type}" if j_s else "8 SP"),
                "magic": (k_s.icon_file if k_s else "demon_magic_01.png", "K", f"{k_s.cost_value} {k_s.cost_type}" if k_s else "50 MP"),
                "dash": ("elf_support_05.png", "Q", "12 SP"),
                "aoe": (e_s.icon_file if e_s else "human_support_02.png", "E", f"{e_s.cost_value} {e_s.cost_type}" if e_s else "35 MP"),
                "shield": (sh_s.icon_file if sh_s else "human_defense_07.png", "Shift", f"{sh_s.cost_value} {sh_s.cost_type}" if sh_s else "8 SP/s"),
                "ultimate": (r_s.icon_file if r_s else "demon_combat_12.png", "R", f"{r_s.cost_value} {r_s.cost_type}" if r_s else "100 MP")
            }
        else:
            icon_map = {
                "attack": ("human_combat_01.png", "J", "8 SP"),
                "magic": ("arcane_magic_06.png", "K", "50 MP"),
                "dash": ("elf_support_05.png", "Q", "12 SP"),
                "aoe": ("arcane_combat_01.png", "E", "35 MP"),
                "shield": ("human_defense_07.png", "Shift", "8 SP/s"),
                "ultimate": ("demon_combat_12.png", "R", "100 MP")
            }
        
        slot_size = 28
        for key, (fname, hotkey, cost) in icon_map.items():
            p = os.path.join(skills_dir, fname)
            if not os.path.exists(p):
                p = os.path.join("assets", "sprites", "fantasy_skills", "64x64", fname)
            if os.path.exists(p):
                img = pygame.image.load(p).convert_alpha()
                scaled = pygame.transform.smoothscale(img, (slot_size, slot_size))
                self.skill_icons[key] = (scaled, hotkey, cost)
            else:
                self.skill_icons[key] = (None, hotkey, cost)
        
    def draw_bar(self, surface: pygame.Surface, x: int, y: int, width: int, height: int, ratio: float, fill_color: tuple, highlight_color: tuple, bg_color: tuple, label: str, value_text: str):
        # Background box
        pygame.draw.rect(surface, bg_color, (x, y, width, height), border_radius=3)
        
        # Filled Bar
        fill_w = max(0, int(width * max(0.0, min(1.0, ratio))))
        if fill_w > 0:
            pygame.draw.rect(surface, fill_color, (x, y, fill_w, height), border_radius=3)
            if height > 4:
                pygame.draw.line(surface, highlight_color, (x + 2, y + 1), (x + fill_w - 2, y + 1))
                
        # Outer Border
        pygame.draw.rect(surface, (80, 85, 100), (x, y, width, height), 1, border_radius=3)
        
        # Stat label
        lbl_surf = self.font_stat.render(label, True, (240, 240, 240))
        surface.blit(lbl_surf, (x - 22, y - 1))
        
        # Value text
        val_surf = self.font_stat.render(value_text, True, (255, 255, 255))
        surface.blit(val_surf, (x + width - val_surf.get_width() - 4, y - 1))

    def draw(self, surface: pygame.Surface):
        # 1. Player Status Glassmorphic Panel (Top-Left)
        panel_x, panel_y = 12, 10
        panel_w, panel_h = 210, 62
        
        # Glassmorphic background
        panel_bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_bg.fill((15, 18, 28, 220))
        surface.blit(panel_bg, (panel_x, panel_y))
        
        # Dual-tone frame border
        pygame.draw.rect(surface, (70, 80, 110), (panel_x, panel_y, panel_w, panel_h), 1, border_radius=4)
        pygame.draw.rect(surface, (25, 30, 45), (panel_x + 1, panel_y + 1, panel_w - 2, panel_h - 2), 1, border_radius=3)
        
        # Health Bar (HP)
        hp_ratio = self.player.health / max(1, self.player.max_health)
        hp_text = f"{int(self.player.health)}/{int(self.player.max_health)}"
        self.draw_bar(
            surface, panel_x + 28, panel_y + 8, 120, 12, hp_ratio,
            (215, 35, 35), (255, 110, 110), (50, 12, 15), "HP", hp_text
        )
        
        # Mana Bar (MP)
        mp_ratio = self.player.mana / max(1.0, self.player.max_mana)
        mp_text = f"{int(self.player.mana)}/{int(self.player.max_mana)}"
        self.draw_bar(
            surface, panel_x + 28, panel_y + 25, 120, 11, mp_ratio,
            (35, 120, 235), (120, 195, 255), (12, 25, 50), "MP", mp_text
        )
        
        # Stamina Bar (SP)
        max_sp = float(getattr(self.player, "max_stamina", 100.0))
        sp_ratio = self.player.stamina / max(1.0, max_sp)
        sp_text = f"{int(self.player.stamina)}/{int(max_sp)}"
        self.draw_bar(
            surface, panel_x + 28, panel_y + 42, 120, 11, sp_ratio,
            (35, 190, 70), (120, 245, 140), (12, 45, 20), "SP", sp_text
        )
        
        # 2. Skill Hotbar Frame (Bottom-Left)
        hotbar_x = 12
        hotbar_y = SETTINGS.GAME_HEIGHT - 48
        slot_w, slot_h = 32, 32
        
        skill_keys = ["attack", "magic", "dash", "aoe", "shield", "ultimate"]
        for idx, s_key in enumerate(skill_keys):
            sx = hotbar_x + idx * (slot_w + 8)
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
                pygame.draw.rect(surface, border_col, (sx - 1, sy - 1, slot_w + 2, slot_h + 2), 2, border_radius=4)
            else:
                pygame.draw.rect(surface, (70, 85, 120), (sx, sy, slot_w, slot_h), 1, border_radius=3)
            
            icon_surf, hotkey, cost = self.skill_icons.get(s_key, (None, "", ""))
            if icon_surf:
                if is_ult and not ult_ready:
                    dimmed = icon_surf.copy()
                    dimmed.set_alpha(150)
                    surface.blit(dimmed, (sx + 2, sy + 2))
                else:
                    surface.blit(icon_surf, (sx + 2, sy + 2))
                
            # Key badge
            badge_col = (255, 235, 120) if not ult_ready else (255, 255, 100)
            badge_text = f"[{hotkey}]" if not ult_ready else f"[{hotkey}] READY!"
            badge_surf = self.font_badge.render(badge_text, True, badge_col)
            surface.blit(badge_surf, (sx + 2, sy - 10))
            
            # Cost label
            if cost:
                cost_col = (255, 215, 120) if is_ult else ((160, 220, 255) if "MP" in cost else (140, 255, 160))
                cost_surf = self.font_cost.render(cost, True, cost_col)
                surface.blit(cost_surf, (sx + 2, sy + slot_h + 1))
        
        # 3. Stage Title Badge (Top-Right)
        if self.stage_title:
            stage_surf = self.font_title.render(self.stage_title, True, (255, 215, 100))
            stg_w = stage_surf.get_width() + 16
            stg_h = stage_surf.get_height() + 8
            stg_x = SETTINGS.GAME_WIDTH - stg_w - 12
            stg_y = 10
            
            badge_bg = pygame.Surface((stg_w, stg_h), pygame.SRCALPHA)
            badge_bg.fill((15, 18, 28, 200))
            surface.blit(badge_bg, (stg_x, stg_y))
            pygame.draw.rect(surface, (120, 100, 50), (stg_x, stg_y, stg_w, stg_h), 1, border_radius=3)
            surface.blit(stage_surf, (stg_x + 8, stg_y + 4))

        # 4. Boss Health Bar (Top-Center)
        if self.active_boss and not self.active_boss.is_dead:
            boss_health_ratio = self.active_boss.health / max(1, self.active_boss.max_health)
            bar_width = 340
            bar_height = 14
            bar_x = (SETTINGS.GAME_WIDTH - bar_width) // 2
            bar_y = 28
            
            # Boss Frame
            boss_bg = pygame.Surface((bar_width + 20, bar_height + 26), pygame.SRCALPHA)
            boss_bg.fill((20, 10, 10, 220))
            surface.blit(boss_bg, (bar_x - 10, bar_y - 18))
            pygame.draw.rect(surface, (150, 40, 40), (bar_x - 10, bar_y - 18, bar_width + 20, bar_height + 26), 1, border_radius=4)
            
            # Label
            boss_name = self.font_boss.render("👑 REI ESQUELETO 👑", True, (255, 220, 120))
            surface.blit(boss_name, (bar_x + (bar_width - boss_name.get_width()) // 2, bar_y - 16))
            
            # Boss HP Bar
            pygame.draw.rect(surface, (40, 10, 10), (bar_x, bar_y + 3, bar_width, bar_height), border_radius=3)
            fill_boss_w = int(bar_width * max(0.0, min(1.0, boss_health_ratio)))
            if fill_boss_w > 0:
                # If enraged, glow reddish orange
                hp_bar_col = (240, 60, 20) if self.active_boss.enraged else (200, 20, 20)
                pygame.draw.rect(surface, hp_bar_col, (bar_x, bar_y + 3, fill_boss_w, bar_height), border_radius=3)
                pygame.draw.line(surface, (255, 140, 100), (bar_x + 2, bar_y + 4), (bar_x + fill_boss_w - 2, bar_y + 4))
            pygame.draw.rect(surface, (220, 180, 80), (bar_x, bar_y + 3, bar_width, bar_height), 1, border_radius=3)


