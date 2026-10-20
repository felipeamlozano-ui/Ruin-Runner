"""
Ruin Engine — Physical In-World Dialogue Interlocutor (Cinematic NPC).
Enacts real narrative encounters:
- Spawns an official character entity in the same spatial world coordinates as the player.
- Walks onto the screen towards the protagonist using real walking animations.
- Orients directly towards the protagonist (mutual eye contact).
- Holds idle/speaking posture while DialogueBox delivers the conversation.
- Departs naturally by walking off-screen or dissolving in magical particles.
- Completely avoids disembodied dialogues or phantom characters.
"""

import os
import math
import random
import pygame
from typing import Optional, List, Dict, Any

from engine.animation import Animation, AnimationManager, load_animation_folder, load_spritesheet
from entities.character_data import CHARACTER_REGISTRY, get_character_profile

class DialogueActor:
    """An official in-world character that physically enters, dialogues, and departs."""

    def __init__(
        self,
        character_id: str,
        x: float,
        y: float,
        target_x: float,
        exit_x: Optional[float] = None,
        speed: float = 100.0,
        name: str = "INTERLOCUTOR"
    ):
        self.character_id = character_id.lower()
        self.profile = get_character_profile(self.character_id)
        self.name = name or self.profile.name
        self.speed = speed
        self.floor_y = y
        self.x = float(x)
        self.y = float(y)
        self.target_x = float(target_x)
        self.exit_x = float(exit_x) if exit_x is not None else float(x)
        
        self.state = "ENTER"  # "ENTER", "ORIENT", "TALK", "EXIT", "DONE"
        self.facing_right = self.target_x > self.x
        self.active = True
        self.is_finished = False
        self.talk_timer = 0.0
        self.fade_alpha = 255.0
        self.particles: List[Dict[str, Any]] = []

        # Hitbox / Rect footprint (centered at x, bottom grounded at floor_y)
        hw, hh = self.profile.hitbox_size
        self.rect = pygame.FRect(self.x - hw // 2, self.floor_y - hh, hw, hh)

        self.anim_manager = AnimationManager()
        self._load_animations()
        self.anim_manager.play("walk")

    def _load_animations(self):
        """Loads official character animations matching character profile and assets."""
        scale = getattr(self.profile, "sprite_scale", 1.0)
        fw, fh = getattr(self.profile, "frame_size", (128, 128))
        bf = self.profile.base_folder

        if self.profile.sprite_type == "folder" or "shaia" in self.character_id:
            # Shaia folder sprite structure
            idle_dir = os.path.join(bf, "sprites_common")
            walk_dir = os.path.join(bf, "sprites_combat")
            self.anim_manager.add_animation("idle", load_animation_folder(idle_dir, "common_00_idle_stand_A", fps=8, loop=True, scale=scale))
            self.anim_manager.add_animation("walk", load_animation_folder(walk_dir, "combat_00_run", fps=10, loop=True, scale=scale))
        else:
            # Craftpix standard sheet structure
            def _find_sheet(folder: str, *candidates: str) -> str:
                for c in candidates:
                    cp = os.path.join(folder, c)
                    if os.path.exists(cp):
                        return cp
                return os.path.join(folder, candidates[0])

            idle_path = _find_sheet(bf, "Idle.png", "IDLE.png")
            walk_path = _find_sheet(bf, "Walk.png", "WALK.png", "Run.png")

            self.anim_manager.add_animation("idle", load_spritesheet(idle_path, fw, fh, fps=6, loop=True, scale=scale))
            self.anim_manager.add_animation("walk", load_spritesheet(walk_path, fw, fh, fps=9, loop=True, scale=scale))

        if not self.anim_manager.get_current_frame():
            # Robust procedural fallback if assets are missing
            surf = pygame.Surface((32, 64), pygame.SRCALPHA)
            pygame.draw.rect(surf, self.profile.color_theme, (0, 0, 32, 64), border_radius=4)
            self.anim_manager.add_animation("idle", Animation([surf], fps=1, loop=True))
            self.anim_manager.add_animation("walk", Animation([surf], fps=1, loop=True))

    def update(self, dt: float, player=None, player_pos=None):
        if not self.active or self.is_finished:
            return

        self.anim_manager.update(dt)
        self.talk_timer += dt

        target_px = None
        if player is not None:
            target_px = player.rect.centerx if hasattr(player, "rect") else player
        elif player_pos is not None:
            target_px = player_pos[0] if isinstance(player_pos, (tuple, list)) else player_pos

        # Update magical aura particles if teleporting/exiting
        for p in self.particles[:]:
            p["life"] -= dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            if p["life"] <= 0:
                self.particles.remove(p)

        if self.state == "ENTER":
            # Walk towards target_x
            dx = self.target_x - self.x
            dist = abs(dx)
            self.facing_right = dx > 0

            step = self.speed * dt
            if dist <= max(4.0, step):
                self.x = self.target_x
                self.state = "ORIENT"
                self.anim_manager.play("idle")
            else:
                self.x += (1.0 if dx > 0 else -1.0) * step
                self.anim_manager.play("walk")

        elif self.state == "ORIENT":
            # Orient towards the player
            if target_px is not None:
                self.facing_right = target_px > self.x
                if player and hasattr(player, "facing_right") and hasattr(player, "rect"):
                    player.facing_right = self.x > player.rect.centerx
            self.state = "TALK"
            self.anim_manager.play("idle")

        elif self.state == "TALK":
            # Stay grounded in idle while dialogue is active
            if target_px is not None:
                self.facing_right = target_px > self.x
            self.anim_manager.play("idle")

        elif self.state == "EXIT":
            # Walk away towards exit_x
            dx = self.exit_x - self.x
            dist = abs(dx)
            self.facing_right = dx > 0

            step = (self.speed * 1.15) * dt
            if dist <= max(6.0, step):
                self.x = self.exit_x
                self.state = "DONE"
                self.is_finished = True
                self.active = False
            else:
                self.x += (1.0 if dx > 0 else -1.0) * step
                self.anim_manager.play("walk")

        # Keep footprint aligned with floor
        hw = self.rect.width
        hh = self.rect.height
        self.rect.midbottom = (int(self.x), int(self.floor_y))

    def trigger_exit(self):
        """Called when DialogueBox finishes its last line."""
        if self.state != "DONE":
            self.state = "EXIT"
            self.facing_right = self.exit_x > self.x
            self.anim_manager.play("walk")
            # Spawn farewell particle burst
            for _ in range(12):
                self.particles.append({
                    "x": self.x + random.uniform(-16, 16),
                    "y": self.floor_y - random.uniform(10, 50),
                    "vx": random.uniform(-30, 30),
                    "vy": random.uniform(-40, -10),
                    "life": random.uniform(0.4, 0.8),
                    "max_life": 0.8,
                    "color": self.profile.color_theme,
                    "radius": random.uniform(2, 4)
                })

    start_exit = trigger_exit

    def skip(self):
        """Immediately ends the encounter if skipped by player."""
        self.state = "DONE"
        self.is_finished = True
        self.active = False

    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        if not self.active or self.is_finished:
            return

        cam_x, cam_y = camera_offset.x, camera_offset.y
        draw_center_x = self.x - cam_x
        draw_bottom_y = self.floor_y - cam_y

        # 1. Ground Contact Shadow (Soft double-layer grounded ellipse matching props)
        shadow_w = int(self.rect.width * 1.25)
        shadow_h = 8
        shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 105), (0, 0, shadow_w, shadow_h))
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 160), (shadow_w // 4, 1, shadow_w // 2, shadow_h - 2))
        surface.blit(shadow_surf, (draw_center_x - shadow_w // 2, draw_bottom_y - shadow_h // 2 + 1))

        # 2. Draw Sprite Frame
        frame = self.anim_manager.get_current_frame()
        if frame:
            if not self.facing_right:
                frame = pygame.transform.flip(frame, True, False)

            fw, fh = frame.get_size()
            ground_off = getattr(self.profile, "ground_offset_y", 0)
            dest_rect = frame.get_rect(midbottom=(int(draw_center_x), int(draw_bottom_y + ground_off)))

            # Soft rim-light glow for mentor / ally presence
            rim_col = (*self.profile.color_theme, 65)
            rim_surf = pygame.mask.from_surface(frame).to_surface(setcolor=rim_col, unsetcolor=(0, 0, 0, 0))
            for ox, oy in ((-1, 0), (1, 0), (0, -1)):
                surface.blit(rim_surf, (dest_rect.x + ox, dest_rect.y + oy))

            surface.blit(frame, dest_rect)

        # 3. Draw particles
        for p in self.particles:
            alpha = int(255 * (p["life"] / p["max_life"]))
            col = (*p["color"][:3], alpha)
            p_surf = pygame.Surface((int(p["radius"] * 2), int(p["radius"] * 2)), pygame.SRCALPHA)
            pygame.draw.circle(p_surf, col, (int(p["radius"]), int(p["radius"])), int(p["radius"]))
            surface.blit(p_surf, (p["x"] - cam_x - p["radius"], p["y"] - cam_y - p["radius"]))
