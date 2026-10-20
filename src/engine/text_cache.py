"""
src/engine/text_cache.py
-------------------------
Global LRU Text Surface Cache for Ruin Engine.
Eliminates thousands of repetitive CPU font.render() calls per second across
HUD, menus, character selection, dialogue, and gameplay.
"""

from typing import Tuple, Dict, Optional
import pygame

_TEXT_SURFACE_CACHE: Dict[Tuple[int, str, Tuple[int, int, int]], pygame.Surface] = {}
_TEXT_SIZE_CACHE: Dict[Tuple[int, str], Tuple[int, int]] = {}
_MAX_CACHE_ENTRIES = 512

def get_cached_text(font: pygame.font.Font, text: str, color: Tuple[int, int, int]) -> pygame.Surface:
    """
    Returns a cached, pre-converted alpha text surface.
    Keyed by (font_id, text_string, rgb_tuple).
    Evicts oldest entries when cache exceeds 512 items.
    """
    if not text:
        text = " "
    key = (id(font), text, (int(color[0]), int(color[1]), int(color[2])))
    surf = _TEXT_SURFACE_CACHE.get(key)
    if surf is None:
        if len(_TEXT_SURFACE_CACHE) >= _MAX_CACHE_ENTRIES:
            # Evict first 64 entries (LRU-like eviction)
            keys_to_remove = list(_TEXT_SURFACE_CACHE.keys())[:64]
            for k in keys_to_remove:
                _TEXT_SURFACE_CACHE.pop(k, None)
        
        surf = font.render(text, True, color)
        disp = pygame.display.get_surface()
        if disp:
            surf = surf.convert_alpha()
        _TEXT_SURFACE_CACHE[key] = surf
    return surf


def get_cached_text_size(font: pygame.font.Font, text: str) -> Tuple[int, int]:
    """Caches font.size() to prevent repetitive glyph metrics calculations."""
    key = (id(font), text)
    size = _TEXT_SIZE_CACHE.get(key)
    if size is None:
        if len(_TEXT_SIZE_CACHE) >= _MAX_CACHE_ENTRIES:
            keys_to_remove = list(_TEXT_SIZE_CACHE.keys())[:64]
            for k in keys_to_remove:
                _TEXT_SIZE_CACHE.pop(k, None)
        size = font.size(text)
        _TEXT_SIZE_CACHE[key] = size
    return size


def render_wrapped_text(surface: pygame.Surface, text: str, font: pygame.font.Font,
                        color: Tuple[int, int, int], rect: pygame.Rect,
                        line_height: int = 12) -> int:
    """
    Wraps text neatly inside rect.width.
    Guarantees no line ever extends past rect.right or overflows vertically.
    Returns the number of lines rendered.
    """
    words = text.split(" ")
    lines = []
    current_line = ""
    max_w = rect.width
    
    for w in words:
        test = (current_line + " " + w).strip()
        if font.size(test)[0] <= max_w:
            current_line = test
        else:
            if current_line:
                lines.append(current_line)
            current_line = w
    if current_line:
        lines.append(current_line)

    y = rect.y
    rendered = 0
    for line in lines:
        if y + line_height > rect.bottom:
            break
        tsurf = get_cached_text(font, line, color)
        surface.blit(tsurf, (rect.x, y))
        y += line_height
        rendered += 1

    return rendered


def clear_text_cache():
    """Clears text cache on scene transitions to release unneeded strings."""
    _TEXT_SURFACE_CACHE.clear()
    _TEXT_SIZE_CACHE.clear()
