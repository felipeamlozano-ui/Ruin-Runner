"""
Ruin Engine — Retro Story Dialogue System.
Classic 16-bit RPG dialogue box with character portrait, typewriter text reveal,
speaker badge, sound effect support, and intuitive controls (Space/Enter/Click to advance, ESC to skip).
"""

import pygame
import math
from typing import List, Dict, Any, Optional


class DialogueBox:
    """Retro style dialogue box rendered at the top of the screen."""

    def __init__(self, dialogue_lines: List[Dict[str, Any]], on_complete=None):
        """
        dialogue_lines: list of dicts with:
          - "speaker": Name of the character (e.g. "SHAIA", "ARQUIMAGO IGNATIUS", "AYAME", "GALAHAD")
          - "text": Text to be spoken
          - "color": (r, g, b) for speaker badge (optional)
          - "portrait": "shaia", "wizard", "kunoichi", "knight", "archer", "boss", etc. (optional)
        """
        self.on_complete = on_complete
        normalized = []
        for item in (dialogue_lines or []):
            if isinstance(item, dict):
                normalized.append(item)
            elif isinstance(item, (tuple, list)) and len(item) >= 2:
                speaker = str(item[0])
                text = str(item[1])
                sp_lower = speaker.lower()
                if "shaia" in sp_lower:
                    portrait = "shaia"
                    col = (255, 205, 80)
                elif any(k in sp_lower for k in ("ignatius", "wizard", "arquimago", "mago", "vulkan")):
                    portrait = "wizard"
                    col = (80, 200, 255)
                elif any(k in sp_lower for k in ("ayame", "kunoichi", "batedora")):
                    portrait = "kunoichi"
                    col = (255, 140, 180)
                elif any(k in sp_lower for k in ("galahad", "knight", "paladino")):
                    portrait = "knight"
                    col = (240, 220, 110)
                elif any(k in sp_lower for k in ("hanzo", "archer", "arqueiro", "kaelen")):
                    portrait = "archer"
                    col = (140, 230, 160)
                elif "samurai" in sp_lower:
                    portrait = "samurai"
                    col = (255, 175, 60)
                elif "empalador" in sp_lower or "tridente" in sp_lower or "impaler" in sp_lower:
                    portrait = "impaler"
                    col = (255, 120, 50)
                elif "titã" in sp_lower or "slime" in sp_lower or "demon" in sp_lower:
                    portrait = "demon_slime"
                    col = (255, 60, 40)
                elif "quimérico" in sp_lower or "olho" in sp_lower or "beholder" in sp_lower or "monstro" in sp_lower:
                    portrait = "monster_creature"
                    col = (180, 60, 255)
                elif "esqueleto" in sp_lower or "carmesim" in sp_lower or "rei" in sp_lower:
                    portrait = "skeleton_king"
                    col = (230, 70, 70)
                else:
                    portrait = "boss"
                    col = (255, 80, 80)
                normalized.append({
                    "speaker": speaker,
                    "text": text,
                    "portrait": portrait,
                    "color": col
                })
        self.lines = normalized
        self.current_index = 0
        self.char_index = 0
        self.text_timer = 0.0
        self.chars_per_sec = 42.0  # Crisp retro typewriter speed
        self.is_finished = len(self.lines) == 0
        self.blink_timer = 0.0

        # Dimensions & Layout (Top of screen, perfectly clearing floor y=280)
        self.box_x = 30
        self.box_y = 12
        self.box_w = 580
        self.box_h = 76
        self.rect = pygame.FRect(self.box_x, self.box_y, self.box_w, self.box_h)

        self._init_fonts()
        self._load_portraits()

    @property
    def dialogues(self):
        return self.lines

    def advance(self):
        self._advance_or_complete()

    def _init_fonts(self):
        try:
            from ui.hollow_ui import HollowFonts
            self.font_speaker = HollowFonts.get(11, bold=True)
            self.font_text = HollowFonts.get(11)
            self.font_prompt = HollowFonts.get(9)
        except Exception:
            self.font_speaker = pygame.font.Font(None, 16)
            self.font_text = pygame.font.Font(None, 15)
            self.font_prompt = pygame.font.Font(None, 12)

    def _load_portraits(self):
        import os
        self.portraits: Dict[str, pygame.Surface] = {}

        def _make_frame(sub_img: Optional[pygame.Surface], border_color: tuple) -> pygame.Surface:
            p_surf = pygame.Surface((48, 48), pygame.SRCALPHA)
            pygame.draw.rect(p_surf, (15, 18, 28), (0, 0, 48, 48), border_radius=4)
            if sub_img:
                scaled = pygame.transform.smoothscale(sub_img, (40, 40))
                p_surf.blit(scaled, (4, 4))
            pygame.draw.rect(p_surf, border_color, (0, 0, 48, 48), width=2, border_radius=4)
            return p_surf

        # 1. Samurai Boss Portrait
        sam_path = os.path.join("assets", "sprites", "bosses", "samurai", "FREE_Samurai 2D Pixel Art v1.2", "Sprites", "IDLE.png")
        if os.path.exists(sam_path):
            try:
                sheet = pygame.image.load(sam_path).convert_alpha()
                head = sheet.subsurface((36, 45, 22, 22))
                self.portraits["samurai"] = _make_frame(head, (255, 175, 60))
            except Exception:
                pass

        # 2. Skeleton King Boss Portrait
        skel_path = os.path.join("assets", "sprites", "bosses", "skeleton_king", "idle.png")
        if os.path.exists(skel_path):
            try:
                sheet = pygame.image.load(skel_path).convert_alpha()
                head = sheet.subsurface((58, 40, 52, 50))
                self.portraits["skeleton_king"] = _make_frame(head, (230, 70, 70))
                self.portraits["boss"] = self.portraits["skeleton_king"]
            except Exception:
                pass

        # 3. Impaler Boss Portrait
        imp_path = os.path.join("assets", "sprites", "bosses", "impaler", "scaled", "idle", "idle1.png")
        if os.path.exists(imp_path):
            try:
                raw = pygame.image.load(imp_path).convert_alpha()
                head = raw.subsurface((80, 106, 55, 55))
                self.portraits["impaler"] = _make_frame(head, (255, 120, 50))
            except Exception:
                pass

        # 4. Demon Slime Boss Portrait
        slime_path = os.path.join("assets", "sprites", "bosses", "demon_slime", "boss_demon_slime_FREE_v1.0", "spritesheets", "demon_slime_FREE_v1.0_288x160_spritesheet.png")
        if os.path.exists(slime_path):
            try:
                sheet = pygame.image.load(slime_path).convert_alpha()
                head = sheet.subsurface((105, 50, 60, 60))
                self.portraits["demon_slime"] = _make_frame(head, (255, 60, 40))
            except Exception:
                pass

        # 5. Monster Creature Boss Portrait
        mon_path = os.path.join("assets", "sprites", "bosses", "monster_creature", "pixel-0056-900920138.png")
        if os.path.exists(mon_path):
            try:
                raw = pygame.image.load(mon_path).convert_alpha()
                bb = raw.get_bounding_rect()
                head = raw.subsurface(bb)
                self.portraits["monster_creature"] = _make_frame(head, (180, 60, 255))
            except Exception:
                pass

        # 6. Playable & Ally Character Portraits (Shaia, Wizard, Kunoichi, Knight, Archer)
        shaia_path = os.path.join("assets", "sprites", "shaia", "sprites_common", "common_00_idle_stand_A01.png")
        if os.path.exists(shaia_path):
            try:
                s_raw = pygame.image.load(shaia_path).convert_alpha()
                bb = s_raw.get_bounding_rect()
                s_head = s_raw.subsurface((bb.left, bb.top, bb.width, int(bb.height * 0.40)))
                self.portraits["shaia"] = _make_frame(s_head, (255, 205, 80))
            except Exception:
                pass

        # Wizard / Ignatius Mentor Portrait
        wiz_path = os.path.join("assets", "sprites", "characters", "coop", "zephyr", "portrait.png")
        if os.path.exists(wiz_path):
            try:
                z_raw = pygame.image.load(wiz_path).convert_alpha()
                self.portraits["wizard"] = _make_frame(z_raw, (80, 200, 255))
            except Exception:
                pass

        # Kunoichi / Ayame Scout Portrait
        kun_path = os.path.join("assets", "sprites", "characters", "coop", "aurelia", "portrait.png")
        if os.path.exists(kun_path):
            try:
                a_raw = pygame.image.load(kun_path).convert_alpha()
                self.portraits["kunoichi"] = _make_frame(a_raw, (255, 140, 180))
            except Exception:
                pass

        # Knight / Galahad Paladin Portrait
        kni_path = os.path.join("assets", "sprites", "characters", "coop", "boran", "portrait.png")
        if os.path.exists(kni_path):
            try:
                b_raw = pygame.image.load(kni_path).convert_alpha()
                self.portraits["knight"] = _make_frame(b_raw, (240, 220, 110))
            except Exception:
                pass

        # Archer / Hanzo Portrait
        arc_path = os.path.join("assets", "sprites", "characters", "coop", "archer", "portrait.png")
        if os.path.exists(arc_path):
            try:
                ar_raw = pygame.image.load(arc_path).convert_alpha()
                self.portraits["archer"] = _make_frame(ar_raw, (140, 230, 160))
            except Exception:
                pass

        # Fallbacks for any missing key
        default_colors = {
            "shaia": (255, 200, 80),
            "wizard": (80, 200, 255),
            "kunoichi": (255, 140, 180),
            "knight": (240, 220, 110),
            "archer": (140, 230, 160),
            "boss": (255, 60, 60),
            "samurai": (255, 180, 60),
            "impaler": (255, 120, 50),
            "demon_slime": (255, 60, 40),
            "monster_creature": (180, 60, 255),
            "skeleton_king": (230, 70, 70),
        }
        for k, col in default_colors.items():
            if k not in self.portraits:
                self.portraits[k] = _make_frame(None, col)

    def handle_events(self, events: List[pygame.event.Event]) -> bool:
        """Returns True if the dialogue intercepted the event."""
        if self.is_finished:
            return False

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # Skip all remaining dialogue immediately
                    self.is_finished = True
                    if callable(self.on_complete):
                        self.on_complete()
                    return True
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_e, pygame.K_j):
                    self._advance_or_complete()
                    return True
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._advance_or_complete()
                return True
        return True

    def _advance_or_complete(self):
        if self.is_finished:
            return
        cur_line = self.lines[self.current_index]["text"]
        if self.char_index < len(cur_line):
            # Instant reveal current line
            self.char_index = len(cur_line)
        else:
            # Advance to next line
            self.current_index += 1
            if self.current_index >= len(self.lines):
                self.is_finished = True
                if callable(self.on_complete):
                    self.on_complete()
            else:
                self.char_index = 0
                self.text_timer = 0.0

    def update(self, dt: float):
        if self.is_finished:
            return
        self.blink_timer += dt
        cur_line = self.lines[self.current_index]["text"]
        if self.char_index < len(cur_line):
            self.text_timer += dt
            new_chars = int(self.text_timer * self.chars_per_sec)
            if new_chars > 0:
                self.char_index = min(len(cur_line), self.char_index + new_chars)
                self.text_timer -= new_chars / self.chars_per_sec

    def draw(self, surface: pygame.Surface):
        if self.is_finished or self.current_index >= len(self.lines):
            return

        cur = self.lines[self.current_index]
        speaker = cur.get("speaker", "NARRADOR")
        text = cur.get("text", "")
        portrait_key = cur.get("portrait", speaker.lower().split()[0])
        speaker_color = cur.get("color", (245, 215, 90))

        # Dynamic Box Dimensions & Layout adapting to current target surface
        sw, sh = surface.get_size()
        self.box_w = min(580, sw - 32)
        self.box_x = (sw - self.box_w) // 2
        self.box_y = 12
        self.box_h = 76
        self.rect = pygame.FRect(self.box_x, self.box_y, self.box_w, self.box_h)

        # 1. Main Background Box (Obsidian Blue with subtle alpha)
        bg_surf = pygame.Surface((self.box_w, self.box_h), pygame.SRCALPHA)
        bg_surf.fill((12, 16, 26, 235))
        surface.blit(bg_surf, (self.box_x, self.box_y))

        # 2. Ornate Golden Pixel Border
        border_rect = pygame.Rect(self.box_x, self.box_y, self.box_w, self.box_h)
        pygame.draw.rect(surface, (218, 165, 32), border_rect, width=2, border_radius=4)
        inner_rect = border_rect.inflate(-4, -4)
        pygame.draw.rect(surface, (70, 55, 20), inner_rect, width=1, border_radius=3)

        # 3. Portrait Emblem
        p_surf = self.portraits.get(portrait_key)
        if not p_surf:
            p_surf = self.portraits.get("shaia")
        surface.blit(p_surf, (self.box_x + 12, self.box_y + 15))

        # 4. Speaker Badge on top-left
        badge_txt = self.font_speaker.render(f" {speaker.upper()} ", True, speaker_color)
        badge_bg = pygame.Surface((badge_txt.get_width() + 4, badge_txt.get_height() + 2))
        badge_bg.fill((18, 22, 35))
        surface.blit(badge_bg, (self.box_x + 64, self.box_y - 4))
        pygame.draw.rect(surface, speaker_color, (self.box_x + 64, self.box_y - 4, badge_bg.get_width(), badge_bg.get_height()), width=1)
        surface.blit(badge_txt, (self.box_x + 66, self.box_y - 3))

        # 5. Typewriter Text (Wrapped accurately using font metrics with zero character drop)
        text_start_x = self.box_x + 68
        right_margin = 28
        max_line_width = self.box_w - 68 - right_margin

        all_words = text.split(" ")
        full_wrapped_lines = []
        cur_w_list = []
        for w in all_words:
            if self.font_text.size(w)[0] > max_line_width:
                if cur_w_list:
                    full_wrapped_lines.append(" ".join(cur_w_list))
                    cur_w_list = []
                sub_w = ""
                for ch in w:
                    if self.font_text.size(sub_w + ch)[0] > max_line_width:
                        full_wrapped_lines.append(sub_w)
                        sub_w = ch
                    else:
                        sub_w += ch
                if sub_w:
                    cur_w_list.append(sub_w)
                continue

            test_line = " ".join(cur_w_list + [w]) if cur_w_list else w
            if self.font_text.size(test_line)[0] > max_line_width:
                full_wrapped_lines.append(" ".join(cur_w_list))
                cur_w_list = [w]
            else:
                cur_w_list.append(w)
        if cur_w_list:
            full_wrapped_lines.append(" ".join(cur_w_list))

        # Typewriter reveal: guarantee full string integrity when char_index reaches end
        if self.char_index >= len(text):
            lines_to_draw = list(full_wrapped_lines)
        else:
            lines_to_draw = []
            curr_pos = 0
            for full_l in full_wrapped_lines:
                pos = text.find(full_l, curr_pos)
                if pos == -1:
                    pos = curr_pos
                if self.char_index <= pos:
                    break
                take_len = min(len(full_l), self.char_index - pos)
                lines_to_draw.append(full_l[:take_len])
                curr_pos = pos + len(full_l)

        line_y = self.box_y + 19
        line_spacing = 15
        for line in lines_to_draw[:3]:
            txt_surf = self.font_text.render(line, True, (240, 240, 245))
            surface.blit(txt_surf, (text_start_x, line_y))
            line_y += line_spacing

        # 6. Blinking Next Indicator
        if self.char_index >= len(text):
            if int(self.blink_timer * 3) % 2 == 0:
                prompt_txt = self.font_prompt.render("[ESPAÇO] ▼", True, (255, 215, 80))
                surface.blit(prompt_txt, (self.box_x + self.box_w - 75, self.box_y + self.box_h - 14))
        else:
            skip_txt = self.font_prompt.render("[ESC] Pular", True, (130, 140, 160))
            surface.blit(skip_txt, (self.box_x + self.box_w - 75, self.box_y + self.box_h - 14))
