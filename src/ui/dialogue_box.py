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

    def __init__(self, dialogue_lines: List[Dict[str, Any]]):
        """
        dialogue_lines: list of dicts with:
          - "speaker": Name of the character (e.g. "SHAIA", "ELDER VULKAN")
          - "text": Text to be spoken
          - "color": (r, g, b) for speaker badge (optional)
          - "portrait": "shaia", "vulkan", "lunaria", "boss", etc. (optional)
        """
        normalized = []
        for item in (dialogue_lines or []):
            if isinstance(item, dict):
                normalized.append(item)
            elif isinstance(item, (tuple, list)) and len(item) >= 2:
                speaker = str(item[0])
                text = str(item[1])
                sp_lower = speaker.lower()
                portrait = "shaia" if "shaia" in sp_lower else ("vulkan" if "vulkan" in sp_lower else ("lunaria" if "lunaria" in sp_lower else ("samurai" if "samurai" in sp_lower else ("carmilla" if "carmilla" in sp_lower else "boss"))))
                col = (255, 200, 80) if portrait == "shaia" else ((80, 200, 255) if portrait == "vulkan" else ((220, 140, 255) if portrait == "lunaria" else (255, 60, 60)))
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
        self.box_h = 74
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
            self.font_speaker = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 8)
            self.font_text = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 7)
            self.font_prompt = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 6)
        except Exception:
            self.font_speaker = pygame.font.Font(None, 16)
            self.font_text = pygame.font.Font(None, 15)
            self.font_prompt = pygame.font.Font(None, 12)

    def _load_portraits(self):
        self.portraits: Dict[str, pygame.Surface] = {}
        # Pre-cache or generate stylish retro icon emblems for speakers
        speaker_colors = {
            "shaia": (255, 200, 80),
            "vulkan": (80, 200, 255),
            "lunaria": (220, 140, 255),
            "boss": (255, 60, 60),
            "carmilla": (255, 80, 140),
            "samurai": (255, 180, 60),
            "spirit": (140, 220, 255),
        }
        for key, col in speaker_colors.items():
            p_surf = pygame.Surface((44, 44), pygame.SRCALPHA)
            pygame.draw.rect(p_surf, (20, 25, 38), (0, 0, 44, 44), border_radius=4)
            pygame.draw.rect(p_surf, col, (0, 0, 44, 44), width=2, border_radius=4)
            # Emblem letter inside
            letter = key[0].upper()
            try:
                f = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 14)
            except Exception:
                f = pygame.font.Font(None, 24)
            t = f.render(letter, True, col)
            p_surf.blit(t, t.get_rect(center=(22, 22)))
            self.portraits[key] = p_surf

    def handle_events(self, events: List[pygame.event.Event]) -> bool:
        """Returns True if the dialogue intercepted the event."""
        if self.is_finished:
            return False

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    # Skip all remaining dialogue immediately
                    self.is_finished = True
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

        # 5. Typewriter Text (wrapped nicely to 2-3 lines max)
        visible_text = text[:self.char_index]
        words = visible_text.split(" ")
        lines = []
        cur_line_words = []
        max_line_width = self.box_w - 90

        for w in words:
            test_line = " ".join(cur_line_words + [w])
            if self.font_text.size(test_line)[0] > max_line_width:
                lines.append(" ".join(cur_line_words))
                cur_line_words = [w]
            else:
                cur_line_words.append(w)
        if cur_line_words:
            lines.append(" ".join(cur_line_words))

        line_y = self.box_y + 20
        for line in lines[:3]:
            txt_surf = self.font_text.render(line, True, (240, 240, 245))
            surface.blit(txt_surf, (self.box_x + 66, line_y))
            line_y += 14

        # 6. Blinking Next Indicator
        if self.char_index >= len(text):
            if int(self.blink_timer * 3) % 2 == 0:
                prompt_txt = self.font_prompt.render("[ESPAÇO] ▼", True, (255, 215, 80))
                surface.blit(prompt_txt, (self.box_x + self.box_w - 75, self.box_y + self.box_h - 14))
        else:
            skip_txt = self.font_prompt.render("[ESC] Pular", True, (130, 140, 160))
            surface.blit(skip_txt, (self.box_x + self.box_w - 75, self.box_y + self.box_h - 14))
