"""
src/scenes/duel_scene.py
------------------------
1v1 Local Versus Fighting Scene inspired by Mortal Kombat and Hollow Knight: Silksong.
Features:
- Closed fighting arena with boundary walls.
- Fighting HUD: Symmetrical health bars with damage ghosting, posture (SP) and MP bars, 99s timer, round markers.
- Best of 3 Rounds ("ROUND 1", "LUTEM!", "VITÓRIA DE P1/P2", "CAMPEÃO DEFINITIVO").
- Fair 1v1 Combat: Melee hits, projectile collisions, blocking, posture break stun, knockback.
- Silksong visual pipeline integration with active graphics presets (Low/Medium/High/Ultra).
- Manual GC Freeze during active combat.
"""

import math
import random
from typing import List, Tuple, Optional, Any
import pygame

from config.settings import SETTINGS
from config.colors import WHITE, GOLD, RED, BLUE, GREEN, GRAY, UI_BACKGROUND
from engine.scene_manager import Scene
from engine.input_manager import INPUT
from engine.system_optimizer import freeze_gc_for_gameplay, collect_garbage_transition
from engine.game_feel import GAME_FEEL
from engine.lighting import LightingEngine, LightSource
from engine.stage_manager import ParallaxRenderer, STAGE_CATALOG
from engine.v3.weather.clouds import CloudsManager
from engine.v3.weather.mist import MistManager
from entities.player import Player
from ui.hollow_ui import HollowFonts, HollowCrestRenderer

class DuelScene(Scene):
    """Competitive 1v1 Local Fighting Scene."""
    internal_size = (640, 360)

    def __init__(self, scene_manager, p1_char: str = "shaia", p2_char: str = "lunaria", arena_id: str = "terrae_1"):
        self.scene_manager = scene_manager
        self.p1_char = p1_char
        self.p2_char = p2_char
        self.arena_id = arena_id

        # GC Freeze during combat
        freeze_gc_for_gameplay("DuelScene")

        self.width = 640
        self.height = 360
        self.arena_left = 60
        self.arena_right = 580
        self.floor_y = 310

        # Stage setup
        self._init_arena_stage()

        # Players initialization (P1 on Left facing right, P2 on Right facing left)
        self.player1 = Player(150, self.floor_y - 64, character_id=p1_char, player_index=0, input_device="p1")
        self.player2 = Player(490, self.floor_y - 64, character_id=p2_char, player_index=1, input_device="p2")
        self.player2.facing_right = False

        # Hitbox tracking for fair 1v1 melee
        self.p1_attack_connected = False
        self.p2_attack_connected = False

        # Projectiles list
        self.projectiles: List[Any] = []

        # Round System (Best of 3)
        self.round_number = 1
        self.p1_rounds_won = 0
        self.p2_rounds_won = 0
        self.max_rounds_to_win = 2

        self.round_time = 99.0
        self.state = "INTRO"  # "INTRO", "FIGHT", "ROUND_OVER", "MATCH_OVER"
        self.state_timer = 0.0
        self.banner_text = "ROUND 1"
        self.sub_banner_text = "PREPAREM-SE!"
        self.winner_text = ""

        # Damage ghost bars for HUD (smooth health catchup)
        self.p1_ghost_hp = float(self.player1.health)
        self.p2_ghost_hp = float(self.player2.health)

        # Floor collision rect
        self.ground_rect = pygame.Rect(0, self.floor_y, self.width, 50)
        self.tiles = [self.ground_rect]

        self.time_sec = 0.0

    def _init_arena_stage(self):
        """Initializes parallax layers and lighting based on selected arena."""
        stage_cfg = STAGE_CATALOG.get(self.arena_id, STAGE_CATALOG.get("terrae_1"))
        theme = getattr(stage_cfg, "biome_theme", "road")

        self.lighting = LightingEngine(theme=theme, screen_w=self.width, screen_h=self.height, floor_y=self.floor_y)
        self.parallax = None
        if stage_cfg and stage_cfg.bg_folder and stage_cfg.layer_files:
            self.parallax = ParallaxRenderer(
                stage_cfg.bg_folder,
                stage_cfg.layer_files,
                stage_cfg.layer_speeds,
                screen_h=self.height,
                initial_offsets=getattr(stage_cfg, "layer_initial_offsets", None)
            )

        # Clouds and Mist
        cloud_count = getattr(SETTINGS, "CLOUDS_COUNT", 14)
        self.clouds = CloudsManager(cloud_count=cloud_count, screen_w=self.width, sky_horizon_y=80)
        self.mist = MistManager(screen_w=self.width, screen_h=self.height, floor_y=self.floor_y)

    def _reset_round(self):
        """Prepares fighter positions and resets health for the next round."""
        collect_garbage_transition()
        self.round_time = 99.0
        self.player1.health = self.player1.max_health
        self.player1.mana = self.player1.max_mana
        self.player1.stamina = self.player1.max_stamina
        self.player1.is_dead = False
        self.player1.pos.x = 150
        self.player1.pos.y = self.floor_y - 64
        self.player1.velocity.x = 0
        self.player1.velocity.y = 0
        self.player1.facing_right = True

        self.player2.health = self.player2.max_health
        self.player2.mana = self.player2.max_mana
        self.player2.stamina = self.player2.max_stamina
        self.player2.is_dead = False
        self.player2.pos.x = 490
        self.player2.pos.y = self.floor_y - 64
        self.player2.velocity.x = 0
        self.player2.velocity.y = 0
        self.player2.facing_right = False

        self.p1_ghost_hp = float(self.player1.health)
        self.p2_ghost_hp = float(self.player2.health)
        self.projectiles.clear()

        self.state = "INTRO"
        self.state_timer = 0.0
        self.banner_text = f"ROUND {self.round_number}"
        self.sub_banner_text = "PREPAREM-SE!"

    def handle_events(self, events: List[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    from scenes.main_menu import MainMenuScene
                    self.scene_manager.change_scene(MainMenuScene(self.scene_manager))
                    return
                if self.state == "MATCH_OVER" and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    from scenes.duel_character_select_scene import DuelCharacterSelectScene
                    self.scene_manager.change_scene(DuelCharacterSelectScene(self.scene_manager))
                    return

    def update(self, dt: float) -> None:
        self.time_sec += dt
        GAME_FEEL.update(dt)

        if self.clouds:
            self.clouds.update(dt)
        if self.mist:
            self.mist.update(dt)
        self.lighting.update(dt)

        # Smooth HUD health ghost catchup
        self.p1_ghost_hp += (self.player1.health - self.p1_ghost_hp) * min(1.0, dt * 5.0)
        self.p2_ghost_hp += (self.player2.health - self.p2_ghost_hp) * min(1.0, dt * 5.0)

        # State Machine
        if self.state == "INTRO":
            self.state_timer += dt
            if self.state_timer >= 1.0 and self.banner_text != "LUTEM!":
                self.banner_text = "LUTEM!"
                self.sub_banner_text = ""
            if self.state_timer >= 1.8:
                self.state = "FIGHT"
                self.banner_text = ""

        elif self.state == "FIGHT":
            self.round_time = max(0.0, self.round_time - dt)

            # Update Fighters
            self.player1.update(dt, self.tiles)
            self.player2.update(dt, self.tiles)

            # Clamp fighters inside closed arena walls
            self.player1.pos.x = max(self.arena_left, min(self.arena_right - self.player1.rect.width, self.player1.pos.x))
            self.player1.rect.x = int(self.player1.pos.x)
            self.player2.pos.x = max(self.arena_left, min(self.arena_right - self.player2.rect.width, self.player2.pos.x))
            self.player2.rect.x = int(self.player2.pos.x)

            # 1v1 Combat: Melee and Hitboxes
            self._process_1v1_combat(dt)

            # Check Round Winner
            p1_defeated = self.player1.health <= 0 or self.player1.is_dead
            p2_defeated = self.player2.health <= 0 or self.player2.is_dead
            time_up = self.round_time <= 0.0

            if p1_defeated or p2_defeated or time_up:
                self.state = "ROUND_OVER"
                self.state_timer = 0.0
                if p1_defeated and p2_defeated:
                    self.banner_text = "EMPATE DUPLO!"
                elif p1_defeated or (time_up and self.player1.health < self.player2.health):
                    self.p2_rounds_won += 1
                    self.banner_text = f"VITÓRIA DE P2 ({self.p2_char.upper()})!"
                else:
                    self.p1_rounds_won += 1
                    self.banner_text = f"VITÓRIA DE P1 ({self.p1_char.upper()})!"

        elif self.state == "ROUND_OVER":
            self.state_timer += dt
            if self.state_timer >= 2.5:
                if self.p1_rounds_won >= self.max_rounds_to_win:
                    self.state = "MATCH_OVER"
                    self.winner_text = f"CAMPEÃO DEFINITIVO: P1 ({self.p1_char.upper()})!"
                elif self.p2_rounds_won >= self.max_rounds_to_win:
                    self.state = "MATCH_OVER"
                    self.winner_text = f"CAMPEÃO DEFINITIVO: P2 ({self.p2_char.upper()})!"
                else:
                    self.round_number += 1
                    self._reset_round()

        elif self.state == "MATCH_OVER":
            self.state_timer += dt

    def _process_1v1_combat(self, dt: float):
        """Calculates fair reciprocal damage, block parry, posture drain and knockback."""
        p1 = self.player1
        p2 = self.player2

        # P1 Attacks P2
        if p1.is_attacking:
            if not self.p1_attack_connected and p1.rect.inflate(35, 10).colliderect(p2.rect):
                self.p1_attack_connected = True
                damage = 22.0
                if p2.is_defending:
                    # Posture block
                    p2.stamina = max(0.0, p2.stamina - 30.0)
                    GAME_FEEL.emit_dust(p2.rect.centerx, p2.rect.bottom, "footstep")
                    GAME_FEEL.emit_slash_arc(p2.rect.centerx, p2.rect.centery, radius=20, color=(120, 200, 255))
                    p2.velocity.x = 120.0 * (1 if p1.pos.x < p2.pos.x else -1)
                else:
                    # Clean hit
                    p2.health = max(0, p2.health - damage)
                    p2.velocity.x = 240.0 * (1 if p1.pos.x < p2.pos.x else -1)
                    GAME_FEEL.trigger_hit_stop(p2, duration_ms=50.0, shake_px=3.5, direction=1 if p1.pos.x < p2.pos.x else -1)
                    GAME_FEEL.emit_slash_arc(p2.rect.centerx, p2.rect.centery, radius=28, color=(255, 230, 160))
        else:
            self.p1_attack_connected = False

        # P2 Attacks P1
        if p2.is_attacking:
            if not self.p2_attack_connected and p2.rect.inflate(35, 10).colliderect(p1.rect):
                self.p2_attack_connected = True
                damage = 22.0
                if p1.is_defending:
                    # Posture block
                    p1.stamina = max(0.0, p1.stamina - 30.0)
                    GAME_FEEL.emit_dust(p1.rect.centerx, p1.rect.bottom, "footstep")
                    GAME_FEEL.emit_slash_arc(p1.rect.centerx, p1.rect.centery, radius=20, color=(120, 200, 255))
                    p1.velocity.x = 120.0 * (1 if p2.pos.x < p1.pos.x else -1)
                else:
                    # Clean hit
                    p1.health = max(0, p1.health - damage)
                    p1.velocity.x = 240.0 * (1 if p2.pos.x < p1.pos.x else -1)
                    GAME_FEEL.trigger_hit_stop(p1, duration_ms=50.0, shake_px=3.5, direction=1 if p2.pos.x < p1.pos.x else -1)
                    GAME_FEEL.emit_slash_arc(p1.rect.centerx, p1.rect.centery, radius=28, color=(255, 230, 160))
        else:
            self.p2_attack_connected = False

    def draw(self, surface: pygame.Surface) -> None:
        sw, sh = self.width, self.height
        cam_offset = pygame.math.Vector2(0, 0)

        # 1. Background Parallax
        if self.parallax:
            self.parallax.draw(surface, 0, 0)
        else:
            surface.fill((18, 20, 30))

        # 2. Clouds & Weather
        if getattr(SETTINGS, "CLOUDS_COUNT", 0) > 0 and self.clouds:
            self.clouds.draw(surface, (0, 0), sw, sh)

        # 3. Distant Mist
        if getattr(SETTINGS, "MIST_LAYERS", 0) > 0 and self.mist:
            self.mist.draw_distant_fog(surface, 0, 0)

        # 4. Arena Boundary Pillars & Floor
        pygame.draw.rect(surface, (35, 38, 52), (0, self.floor_y, sw, sh - self.floor_y))
        pygame.draw.line(surface, (70, 78, 105), (0, self.floor_y), (sw, self.floor_y), 2)
        # Closed arena boundary pillars
        pygame.draw.rect(surface, (25, 28, 40), (0, 0, self.arena_left, sh))
        pygame.draw.rect(surface, (25, 28, 40), (self.arena_right, 0, sw - self.arena_right, sh))
        pygame.draw.line(surface, (90, 100, 130), (self.arena_left, 0), (self.arena_left, sh), 2)
        pygame.draw.line(surface, (90, 100, 130), (self.arena_right, 0), (self.arena_right, sh), 2)

        # 5. Entity Foot Contact AO
        if getattr(SETTINGS, "CONTACT_AO", True):
            self.lighting.draw_entity_ao(surface, [self.player1, self.player2], cam_offset)

        # 6. Draw Fighters
        self.player1.draw(surface, cam_offset)
        self.player2.draw(surface, cam_offset)

        # 7. Game Feel Effects (Dust & Slash Arcs)
        GAME_FEEL.draw_dust(surface, cam_offset)
        GAME_FEEL.draw_slash_arcs(surface, cam_offset)

        # 8. Ground Mist
        if getattr(SETTINGS, "MIST_LAYERS", 0) > 0 and self.mist:
            self.mist.draw_ground_mist(surface, 0, 0)

        # 9. Dynamic Point Lights & God Rays
        lights = []
        for tx, ty, trad, tcol, tint in GAME_FEEL.get_active_point_lights():
            lights.append(LightSource(tx, ty, int(trad), tcol, tint))
        if getattr(SETTINGS, "DYNAMIC_LIGHTS", True):
            self.lighting.draw_point_lights(surface, lights, cam_offset)

        # 10. Vignette
        if getattr(SETTINGS, "VIGNETTE_ENABLED", True):
            self.lighting.draw_vignette(surface)

        # 11. Symmetrical Fighting HUD
        self._draw_fighting_hud(surface)

        # 12. Banners & Announcements
        self._draw_banners(surface)

    def _draw_fighting_hud(self, surface: pygame.Surface):
        """Draws a professional, symmetrical fighting game HUD with health catchup and round markers."""
        sw = self.width
        cx = sw // 2
        bar_w = 210
        bar_h = 14

        # --- PLAYER 1 HUD (LEFT) ---
        p1_x = 24
        p1_y = 16

        # Background slot
        pygame.draw.rect(surface, (20, 24, 32), (p1_x, p1_y, bar_w, bar_h))
        # Ghost Health (white catchup)
        p1_ghost_pct = max(0.0, min(1.0, self.p1_ghost_hp / max(1, self.player1.max_health)))
        pygame.draw.rect(surface, (240, 240, 240), (p1_x, p1_y, int(bar_w * p1_ghost_pct), bar_h))
        # Current Health (Green -> Red)
        p1_hp_pct = max(0.0, min(1.0, self.player1.health / max(1, self.player1.max_health)))
        hp_col = (70, 225, 90) if p1_hp_pct > 0.3 else (235, 65, 65)
        pygame.draw.rect(surface, hp_col, (p1_x, p1_y, int(bar_w * p1_hp_pct), bar_h))
        pygame.draw.rect(surface, (200, 210, 230), (p1_x, p1_y, bar_w, bar_h), width=2)

        # P1 Stamina / Posture Bar (Cyan)
        p1_sp_pct = max(0.0, min(1.0, self.player1.stamina / max(1, self.player1.max_stamina)))
        pygame.draw.rect(surface, (20, 24, 32), (p1_x, p1_y + 16, 140, 6))
        pygame.draw.rect(surface, (80, 210, 245), (p1_x, p1_y + 16, int(140 * p1_sp_pct), 6))
        pygame.draw.rect(surface, (120, 140, 170), (p1_x, p1_y + 16, 140, 6), width=1)

        # P1 Name & Round Win Orbs
        f_hud = HollowFonts.get(10, bold=True)
        t_p1 = f_hud.render(f"P1: {self.p1_char.upper()}", True, (245, 230, 140))
        surface.blit(t_p1, (p1_x, p1_y - 12))
        for i in range(2):
            won = self.p1_rounds_won > i
            col = (255, 215, 60) if won else (50, 55, 70)
            pygame.draw.circle(surface, col, (p1_x + 155 + i * 14, p1_y + 19), 5)
            pygame.draw.circle(surface, (180, 190, 210), (p1_x + 155 + i * 14, p1_y + 19), 5, width=1)

        # --- PLAYER 2 HUD (RIGHT - MIRRORED) ---
        p2_x = sw - 24 - bar_w
        p2_y = 16

        # Background slot
        pygame.draw.rect(surface, (20, 24, 32), (p2_x, p2_y, bar_w, bar_h))
        # Ghost Health
        p2_ghost_pct = max(0.0, min(1.0, self.p2_ghost_hp / max(1, self.player2.max_health)))
        gw_w = int(bar_w * p2_ghost_pct)
        pygame.draw.rect(surface, (240, 240, 240), (p2_x + (bar_w - gw_w), p2_y, gw_w, bar_h))
        # Current Health
        p2_hp_pct = max(0.0, min(1.0, self.player2.health / max(1, self.player2.max_health)))
        hp2_col = (70, 225, 90) if p2_hp_pct > 0.3 else (235, 65, 65)
        cur_w2 = int(bar_w * p2_hp_pct)
        pygame.draw.rect(surface, hp2_col, (p2_x + (bar_w - cur_w2), p2_y, cur_w2, bar_h))
        pygame.draw.rect(surface, (200, 210, 230), (p2_x, p2_y, bar_w, bar_h), width=2)

        # P2 Stamina / Posture Bar
        p2_sp_pct = max(0.0, min(1.0, self.player2.stamina / max(1, self.player2.max_stamina)))
        sp2_w = int(140 * p2_sp_pct)
        pygame.draw.rect(surface, (20, 24, 32), (p2_x + (bar_w - 140), p2_y + 16, 140, 6))
        pygame.draw.rect(surface, (80, 210, 245), (p2_x + (bar_w - sp2_w), p2_y + 16, sp2_w, 6))
        pygame.draw.rect(surface, (120, 140, 170), (p2_x + (bar_w - 140), p2_y + 16, 140, 6), width=1)

        # P2 Name & Round Win Orbs
        t_p2 = f_hud.render(f"P2: {self.p2_char.upper()}", True, (130, 205, 255))
        surface.blit(t_p2, (p2_x + bar_w - t_p2.get_width(), p2_y - 12))
        for i in range(2):
            won = self.p2_rounds_won > i
            col = (255, 215, 60) if won else (50, 55, 70)
            pygame.draw.circle(surface, col, (p2_x + 35 - i * 14, p2_y + 19), 5)
            pygame.draw.circle(surface, (180, 190, 210), (p2_x + 35 - i * 14, p2_y + 19), 5, width=1)

        # --- CENTER ROUND TIMER ---
        f_timer = HollowFonts.get(22, bold=True)
        time_int = int(math.ceil(self.round_time))
        t_col = (255, 230, 120) if time_int > 10 else (255, 75, 75)
        timer_surf = f_timer.render(f"{time_int:02d}", True, t_col)
        surface.blit(timer_surf, timer_surf.get_rect(center=(cx, p1_y + 10)))

    def _draw_banners(self, surface: pygame.Surface):
        """Draws fighting banners during Intro, Round Over, and Match Over."""
        cx = self.width // 2
        cy = self.height // 2 - 20

        if self.banner_text:
            f_banner = HollowFonts.get(24, bold=True)
            b_surf = f_banner.render(self.banner_text, True, (255, 235, 130))
            # Dark backing banner
            bg_rect = pygame.Rect(0, cy - 18, self.width, 38)
            overlay = pygame.Surface((self.width, 38), pygame.SRCALPHA)
            overlay.fill((10, 12, 18, 190))
            surface.blit(overlay, (0, cy - 18))
            surface.blit(b_surf, b_surf.get_rect(center=(cx, cy)))

            if self.sub_banner_text:
                f_sub = HollowFonts.get(11)
                s_surf = f_sub.render(self.sub_banner_text, True, (200, 215, 235))
                surface.blit(s_surf, s_surf.get_rect(center=(cx, cy + 26)))

        if self.state == "MATCH_OVER" and self.winner_text:
            f_win = HollowFonts.get(20, bold=True)
            w_surf = f_win.render(self.winner_text, True, (255, 220, 90))
            surface.blit(w_surf, w_surf.get_rect(center=(cx, cy)))
            f_hint = HollowFonts.get(10)
            h_surf = f_hint.render("[ENTER] VOLTAR À SELEÇÃO   |   [ESC] MENU PRINCIPAL", True, (180, 195, 220))
            surface.blit(h_surf, h_surf.get_rect(center=(cx, cy + 34)))
