"""
src/scenes/duel_scene.py
------------------------
1v1 Local Versus Fighting Scene inspired by Brawlhalla, Hollow Knight, and fighting game classics.
Features:
- High health pool (multiplied 6x) so fighters never die in a single skill or spell.
- Restricted mana pool and low passive regen: mana must be earned dynamically through attack & defense.
- Core Attack & Defense Mechanics:
  * Active Block (Guard) with posture/stamina drain.
  * Timed Perfect Parry (0.22s window): 100% damage nullified, attacker staggered, resource recovery, and deflection!
  * Guard Break: stamina depletion results in 1.3s daze/stun, leaving the player open to full punishes!
  * Melee Combos & Counter-Hits: catching opponent in swing startup grants bonus damage and points!
  * Blade Clash (Choque de Espadas): simultaneous strikes clash with mid-air sparks and recoil!
  * Brawlhalla-Style Knockback: knockback scales dramatically with missing health!
  * Arena Wall Bounce: high-speed impacts bounce off the arena pillars with heavy screen shake!
- Combat Mastery Scoring System (Pontuação de Maestria):
  * Real-time points for Hits, Combos, Counters, Blocks, Parries, and Guard Breaks.
  * Real-time floating combat badges and comprehensive post-match scoreboard.
- Symmetrical Fighting HUD:
  * Health bars with smooth damage ghosting catchup.
  * Stamina / Posture bars (Cyan -> Red).
  * Mana bars (Violet/Purple) reflecting restricted MP.
  * Round markers, 99s timer, and live combo counters.
"""

import math
import random
from typing import List, Tuple, Optional, Any, Dict
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
from ui.hud import HUD

DUEL_HP_MULTIPLIER = 6.0
DUEL_MAX_MANA_CAP = 80.0
DUEL_START_MANA = 20.0
DUEL_MANA_REGEN_MULT = 0.25

class DuelCamera:
    """Lightweight 1v1 camera with responsive impact screen shake."""
    def __init__(self):
        self.offset = pygame.math.Vector2(0, 0)
        self.shake_intensity = 0.0
        self.shake_duration = 0.0
        self.shake_timer = 0.0

    def shake(self, intensity: float, duration: float):
        self.shake_intensity = max(self.shake_intensity, intensity)
        self.shake_duration = max(self.shake_duration, duration)
        self.shake_timer = self.shake_duration

    def update(self, dt: float):
        if self.shake_timer > 0:
            self.shake_timer -= dt
            progress = self.shake_timer / max(0.001, self.shake_duration)
            mag = self.shake_intensity * progress
            self.offset.x = random.uniform(-mag, mag)
            self.offset.y = random.uniform(-mag * 0.7, mag * 0.7)
        else:
            self.offset.x = 0.0
            self.offset.y = 0.0


class FloatingCombatText:
    """Crisp floating text badge for real-time Duel combat feedback."""
    __slots__ = ("x", "y", "text", "color", "life", "max_life", "vy")
    def __init__(self, x: float, y: float, text: str, color: Tuple[int, int, int], life: float = 0.9):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.life = life
        self.max_life = life
        self.vy = -38.0  # Smooth upward float

    def update(self, dt: float) -> bool:
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface: pygame.Surface, cam_offset: pygame.math.Vector2):
        if self.life <= 0:
            return
        alpha = int(255 * min(1.0, self.life / (self.max_life * 0.35)))
        font = HollowFonts.get(10, bold=True)
        t_surf = font.render(self.text, True, self.color)
        s_surf = font.render(self.text, True, (12, 14, 20))
        if alpha < 255:
            t_surf.set_alpha(alpha)
            s_surf.set_alpha(alpha // 2)
        rx = int(self.x - cam_offset.x - t_surf.get_width() // 2)
        ry = int(self.y - cam_offset.y)
        surface.blit(s_surf, (rx + 1, ry + 1))
        surface.blit(t_surf, (rx, ry))


class DuelScene(Scene):
    """Competitive 1v1 Local Fighting Scene focusing on Attack & Defense Mastery."""
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
        self.camera = DuelCamera()

        # Players initialization (P1 on Left facing right, P2 on Right facing left)
        self.player1 = Player(150, self.floor_y - 64, character_id=p1_char, player_index=0, input_device="p1")
        self.player2 = Player(490, self.floor_y - 64, character_id=p2_char, player_index=1, input_device="p2")
        self.player2.facing_right = False

        # Apply Duel Mode stats (Multiplied Health, Restricted Mana, Stamina)
        self._apply_duel_stats(self.player1)
        self._apply_duel_stats(self.player2)

        # Hitbox tracking for fair 1v1 melee
        self.p1_attack_connected = False
        self.p2_attack_connected = False

        # Beautiful Glassmorphic HUDs identical to adventure and boss modes
        self.hud1 = HUD(self.player1, stage_title=None, player_index=0)
        self.hud2 = HUD(self.player2, stage_title=None, player_index=1)
        self.show_command_map = True

        # Projectiles list
        self.projectiles: List[Any] = []

        # Floating combat badges
        self.floating_texts: List[FloatingCombatText] = []

        # Combat Mastery Scoring System (Pontuação de Maestria de Combate)
        self.p1_score = 0
        self.p2_score = 0
        self.p1_stats: Dict[str, Any] = {
            "score": 0, "hits": 0, "parries": 0, "blocks": 0, "guard_breaks": 0, "counters": 0, "max_combo": 0
        }
        self.p2_stats: Dict[str, Any] = {
            "score": 0, "hits": 0, "parries": 0, "blocks": 0, "guard_breaks": 0, "counters": 0, "max_combo": 0
        }

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

    def _apply_duel_stats(self, p: Player):
        """Applies multiplied health pool and restricted mana configuration for duel."""
        p.is_duel_mode = True
        base_hp = getattr(p.profile, "hp_max", 100)
        p.max_health = max(480, int(base_hp * DUEL_HP_MULTIPLIER))
        p.health = p.max_health

        # Restricted mana pool and low starting mana: players must earn mana through combat
        p.max_mana = min(DUEL_MAX_MANA_CAP, float(getattr(p.profile, "mp_max", 100)))
        p.mana = DUEL_START_MANA
        p.mana_regen = getattr(p.profile, "mana_regen", 6.0) * DUEL_MANA_REGEN_MULT

        p.max_stamina = 100.0
        p.stamina = p.max_stamina
        p.stamina_regen = 26.0

        p.guard_break_timer = 0.0
        p.combo_count = 0
        p.combo_timer = 0.0

    def add_duel_score(self, player_idx: int, points: int, event_name: str, x: float, y: float, color: Tuple[int, int, int]):
        """Awards Combat Mastery score and spawns a floating combat badge."""
        if player_idx == 0:
            self.p1_score += points
            self.p1_stats["score"] = self.p1_score
        else:
            self.p2_score += points
            self.p2_stats["score"] = self.p2_score
        self.floating_texts.append(FloatingCombatText(x, y, f"{event_name} +{points}", color))

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
        """Prepares fighter positions, resets multiplied health and restricted mana for next round."""
        collect_garbage_transition()
        self.round_time = 99.0
        for p, px, facing in [(self.player1, 150, True), (self.player2, 490, False)]:
            p.health = p.max_health
            p.mana = DUEL_START_MANA
            p.stamina = p.max_stamina
            p.guard_break_timer = 0.0
            p.combo_count = 0
            p.combo_timer = 0.0
            p.is_dead = False
            p.is_downed = False
            p.invulnerable = False
            p.is_attacking = False
            p.is_casting_magic = False
            p.is_casting_aoe = False
            p.is_casting_ultimate = False
            p.is_blocking = False
            p.is_dashing = False
            p.pos.x = px
            p.pos.y = self.floor_y - 64
            p.velocity.x = 0
            p.velocity.y = 0
            p.facing_right = facing
            p.attack_hit_enemies.clear()
            p.projectiles.clear()
            if hasattr(p, "_pending_shots"):
                p._pending_shots.clear()
            if hasattr(p, "anim_manager"):
                p.anim_manager.play("idle", force_reset=True)

        self.p1_ghost_hp = float(self.player1.health)
        self.p2_ghost_hp = float(self.player2.health)
        if hasattr(self, "hud1"):
            self.hud1.ghost_hp = float(self.player1.health)
            self.hud1._load_skill_icons()
        if hasattr(self, "hud2"):
            self.hud2.ghost_hp = float(self.player2.health)
            self.hud2._load_skill_icons()
        self.projectiles.clear()
        self.floating_texts.clear()
        self.p1_attack_connected = False
        self.p2_attack_connected = False

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
                if event.key in (pygame.K_TAB, pygame.K_h, pygame.K_F1):
                    self.show_command_map = not self.show_command_map
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

        # Update floating combat text
        self.floating_texts = [ft for ft in self.floating_texts if ft.update(dt)]

        # Combo Timers decay
        for p in (self.player1, self.player2):
            if hasattr(p, "combo_timer") and p.combo_timer > 0:
                p.combo_timer -= dt
                if p.combo_timer <= 0:
                    p.combo_count = 0

        # State Machine
        if self.state == "INTRO":
            self.state_timer += dt
            if self.state_timer >= 1.0 and self.banner_text != "LUTEM!":
                self.banner_text = "LUTEM!"
                self.sub_banner_text = "FOCO EM ATAQUE E DEFESA"
            if self.state_timer >= 1.8:
                self.state = "FIGHT"
                self.banner_text = ""

        elif self.state == "FIGHT":
            self.round_time = max(0.0, self.round_time - dt)
            self.camera.update(dt)

            is_ult_active = (getattr(self.player1, "is_casting_ultimate", False) or 
                             getattr(self.player2, "is_casting_ultimate", False))
            is_time_stopped = is_ult_active and any(
                getattr(p, "ultimate_freeze_timer", 0.0) > 0.0 for p in [self.player1, self.player2] if p
            )

            # Update Fighters with reciprocal target references & camera
            self.player1.update(dt, self.tiles, enemies=[self.player2], camera=self.camera)
            self._handle_aoe_duel(self.player1, self.player2, 0, 1)
            while self.player1.projectiles:
                p = self.player1.projectiles.pop(0)
                setattr(p, "owner", self.player1)
                self.projectiles.append(p)

            self.player2.update(dt, self.tiles, enemies=[self.player1], camera=self.camera)
            self._handle_aoe_duel(self.player2, self.player1, 1, 0)
            while self.player2.projectiles:
                p = self.player2.projectiles.pop(0)
                setattr(p, "owner", self.player2)
                self.projectiles.append(p)

            # Clamp fighters inside arena walls with Brawlhalla Wall Bounce Mechanics!
            self._handle_arena_bounds_and_wall_bounces()

            # 1v1 Melee and Projectiles Combat with Attack & Defense Mastery
            self._process_1v1_combat(dt)
            self._process_projectiles(dt, is_time_stopped)

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
                    self.banner_text = f"VITÓRIA DO ROUND: P2 ({self.p2_char.upper()})!"
                    self.add_duel_score(1, 100, "VITÓRIA DE ROUND", self.player2.rect.centerx, self.player2.rect.top - 20, (255, 215, 60))
                else:
                    self.p1_rounds_won += 1
                    self.banner_text = f"VITÓRIA DO ROUND: P1 ({self.p1_char.upper()})!"
                    self.add_duel_score(0, 100, "VITÓRIA DE ROUND", self.player1.rect.centerx, self.player1.rect.top - 20, (255, 215, 60))

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

    def _handle_arena_bounds_and_wall_bounces(self):
        """Brawlhalla-style boundary containment and high-speed wall rebounds."""
        for p, attacker_idx in [(self.player1, 1), (self.player2, 0)]:
            # Left Wall
            if p.pos.x <= self.arena_left:
                p.pos.x = self.arena_left
                p.rect.x = int(p.pos.x)
                if p.velocity.x < -230.0:
                    self.camera.shake(7.0, 0.22)
                    GAME_FEEL.emit_dust(self.arena_left + 6, p.rect.centery, "landing")
                    GAME_FEEL.emit_slash_arc(self.arena_left + 10, p.rect.centery, radius=26, color=(255, 180, 90))
                    p.velocity.x = -p.velocity.x * 0.40  # Wall rebound
                    self.add_duel_score(attacker_idx, 15, "IMPACTO NA PAREDE", p.rect.centerx, p.rect.centery, (255, 170, 90))
                else:
                    p.velocity.x = max(0.0, p.velocity.x)

            # Right Wall
            elif p.pos.x >= self.arena_right - p.rect.width:
                p.pos.x = self.arena_right - p.rect.width
                p.rect.x = int(p.pos.x)
                if p.velocity.x > 230.0:
                    self.camera.shake(7.0, 0.22)
                    GAME_FEEL.emit_dust(self.arena_right - 6, p.rect.centery, "landing")
                    GAME_FEEL.emit_slash_arc(self.arena_right - 10, p.rect.centery, radius=26, color=(255, 180, 90))
                    p.velocity.x = -p.velocity.x * 0.40  # Wall rebound
                    self.add_duel_score(attacker_idx, 15, "IMPACTO NA PAREDE", p.rect.centerx, p.rect.centery, (255, 170, 90))
                else:
                    p.velocity.x = min(0.0, p.velocity.x)

    def _handle_aoe_duel(self, caster: Player, target: Player, caster_idx: int, target_idx: int):
        """Processes AoE skills with proper defensive interaction (parry, block chip, posture drain)."""
        if caster.is_casting_aoe and not caster.aoe_hit_done:
            caster.aoe_hit_done = True
            raw_dmg = caster.profile.skills["e"].damage if hasattr(caster, "profile") and "e" in caster.profile.skills else 25.0
            dist = pygame.math.Vector2(target.rect.center).distance_to(pygame.math.Vector2(caster.rect.center))
            if dist <= caster.aoe_radius and not target.is_dead:
                # 0. Evasion / Dodge AoE (I-Frames during Dash)
                if getattr(target, "is_dashing", False) or getattr(target, "invulnerable", False):
                    self.add_duel_score(target_idx, 15, "★ ESQUIVA ÁREA!", target.rect.centerx, target.rect.top - 20, (120, 230, 255))
                    return

                # 1. Perfect Parry AoE
                is_parry = (target.is_blocking and target.parry_window_timer > 0) or (hasattr(target, "input") and target.input.is_action_just_pressed("DEFEND"))
                if is_parry:
                    target.stamina = min(target.max_stamina, target.stamina + 25.0)
                    target.mana = min(target.max_mana, target.mana + 15.0)
                    self.add_duel_score(target_idx, 35, "★ PARRY TEMPESTADE!", target.rect.centerx, target.rect.top - 20, (255, 230, 90))
                    GAME_FEEL.emit_slash_arc(target.rect.centerx, target.rect.centery, radius=32, color=(255, 240, 100))
                    self.camera.shake(8.0, 0.28)
                    return

                # 2. Block AoE
                if target.is_blocking:
                    if target.stamina <= 30.0:
                        target.guard_break_timer = 1.3
                        target.stamina = 0.0
                        target.is_blocking = False
                        chip = max(6, int(raw_dmg * 0.40))
                        target.health = max(0, target.health - chip)
                        self.add_duel_score(caster_idx, 50, "QUEBRA DE GUARDA!", caster.rect.centerx, caster.rect.top - 24, (255, 80, 80))
                    else:
                        target.stamina = max(0.0, target.stamina - 30.0)
                        chip = max(2, int(raw_dmg * 0.12))
                        target.health = max(0, target.health - chip)
                        self.add_duel_score(target_idx, 10, "BLOQUEIO", target.rect.centerx, target.rect.top - 14, (100, 215, 255))
                    return

                # 3. Unblocked AoE
                final_dmg = min(40, int(raw_dmg))
                target.health = max(0, target.health - final_dmg)
                missing_hp_pct = max(0.0, 1.0 - (target.health / max(1, target.max_health)))
                kb_dir = 1 if target.rect.centerx > caster.rect.centerx else -1
                target.velocity.x = kb_dir * (220.0 + missing_hp_pct * 200.0)
                target.velocity.y = -(180.0 + missing_hp_pct * 120.0)
                self.add_duel_score(caster_idx, 20, "GOLPE EM ÁREA", caster.rect.centerx, caster.rect.top - 16, (255, 180, 70))

    def _process_projectiles(self, dt: float, is_time_stopped: bool):
        """Updates flying projectiles, checking collisions with perfect parry, defensive blocks, and fighters."""
        for proj in self.projectiles[:]:
            if not is_time_stopped:
                proj.update(dt, self.tiles)
            if not proj.active:
                if proj in self.projectiles:
                    self.projectiles.remove(proj)
                continue

            if not proj.can_deal_damage():
                continue

            owner = getattr(proj, "owner", None)
            target = self.player2 if owner == self.player1 else (self.player1 if owner == self.player2 else None)
            owner_idx = 0 if owner == self.player1 else 1
            target_idx = 1 if owner_idx == 0 else 0

            if target is None:
                if proj.rect.colliderect(self.player1.rect) and proj.rect.colliderect(self.player2.rect):
                    target = self.player2 if self.player1.facing_right else self.player1
                elif proj.rect.colliderect(self.player2.rect):
                    target = self.player2
                elif proj.rect.colliderect(self.player1.rect):
                    target = self.player1

            if target and not target.is_dead and not target.is_casting_ultimate:
                # 0. Evasion / Dodge Projectile
                if getattr(target, "is_dashing", False) or getattr(target, "invulnerable", False):
                    continue

                if target not in proj.hit_entities and proj.rect.colliderect(target.rect):
                    proj.hit_entities.add(target)
                    damage = min(40.0, float(getattr(proj, "damage", 25.0)))

                    # 1. PERFECT PARRY / DEFLECTION
                    is_parry = (target.is_blocking and target.parry_window_timer > 0) or (hasattr(target, "input") and target.input.is_action_just_pressed("DEFEND"))
                    if is_parry:
                        # Deflect projectile back to owner!
                        proj.owner = target
                        proj.hit_entities.clear()
                        if hasattr(proj, "velocity"):
                            proj.velocity.x = -proj.velocity.x * 1.40
                        setattr(proj, "damage", damage * 1.30)

                        target.stamina = min(target.max_stamina, target.stamina + 20.0)
                        target.mana = min(target.max_mana, target.mana + 15.0)

                        GAME_FEEL.emit_slash_arc(target.rect.centerx, target.rect.centery, radius=30, color=(255, 235, 90))
                        self.camera.shake(8.0, 0.25)
                        self.add_duel_score(target_idx, 30, "★ PARRY PROJÉTIL!", target.rect.centerx, target.rect.top - 20, (255, 220, 80))
                        if target_idx == 0:
                            self.p1_stats["parries"] += 1
                        else:
                            self.p2_stats["parries"] += 1
                        continue

                    # 2. ACTIVE BLOCK
                    if target.is_blocking:
                        if target.stamina <= 20.0:
                            # GUARD BREAK!
                            target.guard_break_timer = 1.3
                            target.stamina = 0.0
                            target.is_blocking = False
                            target.health = max(0, target.health - max(4, int(damage * 0.35)))
                            self.add_duel_score(owner_idx, 40, "QUEBRA DE GUARDA!", target.rect.centerx, target.rect.top - 20, (255, 75, 75))
                            if owner_idx == 0:
                                self.p1_stats["guard_breaks"] += 1
                            else:
                                self.p2_stats["guard_breaks"] += 1
                        else:
                            target.stamina = max(0.0, target.stamina - 20.0)
                            target.health = max(0, target.health - max(1, int(damage * 0.10)))
                            target.mana = min(target.max_mana, target.mana + 3.0)
                            target.velocity.x = (80.0 if proj.velocity.x > 0 else -80.0)
                            GAME_FEEL.emit_slash_arc(target.rect.centerx, target.rect.centery, radius=22, color=(120, 210, 255))
                            self.add_duel_score(target_idx, 10, "BLOQUEIO", target.rect.centerx, target.rect.top - 14, (100, 215, 255))
                            if target_idx == 0:
                                self.p1_stats["blocks"] += 1
                            else:
                                self.p2_stats["blocks"] += 1
                    else:
                        # 3. UNBLOCKED HIT
                        target.health = max(0, target.health - int(damage))
                        missing_hp_pct = max(0.0, 1.0 - (target.health / max(1, target.max_health)))
                        target.velocity.x = (180.0 + missing_hp_pct * 180.0) * (1 if proj.velocity.x > 0 else -1)
                        target.velocity.y = -(100.0 + missing_hp_pct * 90.0)
                        GAME_FEEL.trigger_hit_stop(target, duration_ms=45.0, shake_px=3.0, direction=1 if proj.velocity.x > 0 else -1)
                        GAME_FEEL.emit_slash_arc(target.rect.centerx, target.rect.centery, radius=28, color=(255, 230, 160))
                        self.add_duel_score(owner_idx, 12, "TIRO CERTEIRO", target.rect.centerx, target.rect.top - 16, (255, 205, 120))
                        if owner_idx == 0:
                            self.p1_stats["hits"] += 1
                        else:
                            self.p2_stats["hits"] += 1

                    if hasattr(proj, "explode"):
                        proj.explode()
                    else:
                        proj.active = False

    def _process_1v1_combat(self, dt: float):
        """Calculates fair reciprocal damage, blade clash, parry, posture drain, and Brawlhalla knockback."""
        p1 = self.player1
        p2 = self.player2

        # 1. BLADE CLASH: Both players attack simultaneously and hitboxes collide
        p1_swinging = p1.is_attacking
        p2_swinging = p2.is_attacking
        p1_hb = (p1.get_attack_hitbox() or p1.rect.inflate(35, 10)) if p1_swinging else None
        p2_hb = (p2.get_attack_hitbox() or p2.rect.inflate(35, 10)) if p2_swinging else None

        if p1_swinging and p2_swinging and p1_hb and p2_hb and p1_hb.colliderect(p2_hb):
            if not self.p1_attack_connected and not self.p2_attack_connected:
                self.p1_attack_connected = True
                self.p2_attack_connected = True
                mid_x = (p1.rect.centerx + p2.rect.centerx) // 2
                mid_y = (p1.rect.centery + p2.rect.centery) // 2
                GAME_FEEL.emit_slash_arc(mid_x, mid_y, radius=32, color=(255, 255, 230))
                GAME_FEEL.emit_dust(mid_x, mid_y, "footstep")
                self.camera.shake(7.5, 0.26)
                p1.velocity.x = -160.0 * (1 if p1.pos.x < p2.pos.x else -1)
                p2.velocity.x = 160.0 * (1 if p1.pos.x < p2.pos.x else -1)
                self.add_duel_score(0, 10, "CLASH!", mid_x - 22, mid_y - 20, (230, 240, 255))
                self.add_duel_score(1, 10, "CLASH!", mid_x + 22, mid_y - 20, (230, 240, 255))
                return

        # 2. P1 Attacks P2
        if p1_swinging:
            p1_hitbox = p1_hb or p1.rect.inflate(35, 10)
            if not self.p1_attack_connected and p1_hitbox.colliderect(p2.rect):
                self.p1_attack_connected = True
                self._resolve_strike(attacker=p1, defender=p2, attacker_idx=0, defender_idx=1)
        else:
            self.p1_attack_connected = False

        # 3. P2 Attacks P1
        if p2_swinging:
            p2_hitbox = p2_hb or p2.rect.inflate(35, 10)
            if not self.p2_attack_connected and p2_hitbox.colliderect(p1.rect):
                self.p2_attack_connected = True
                self._resolve_strike(attacker=p2, defender=p1, attacker_idx=1, defender_idx=0)
        else:
            self.p2_attack_connected = False

    def _resolve_strike(self, attacker: Player, defender: Player, attacker_idx: int, defender_idx: int):
        """Resolves melee strike evaluating Parry, Active Block, Guard Break, Combos, and Counter-Hits."""
        base_damage = float(attacker.profile.skills.get("j").damage if hasattr(attacker, "profile") and "j" in attacker.profile.skills else 22.0)
        attack_dir = 1 if attacker.pos.x < defender.pos.x else -1

        # Shaia passive: restore HP/MP on hit
        if getattr(attacker, "character_id", "") == "shaia" or getattr(attacker, "passive_id", "") == "shaia_battle_thirst":
            attacker.health = min(attacker.max_health, attacker.health + 3)
            attacker.mana = min(attacker.max_mana, attacker.mana + 4)

        # ─────────────────────────────────────────────────────────────
        # CASE 0: PERFECT EVASION (ESQUIVA / DODGE!)
        # ─────────────────────────────────────────────────────────────
        if getattr(defender, "is_dashing", False) or getattr(defender, "invulnerable", False):
            # 100% damage avoided, attacker whiffed
            mid_x = (attacker.rect.centerx + defender.rect.centerx) // 2
            GAME_FEEL.emit_dust(defender.rect.centerx, defender.rect.bottom, "footstep")
            self.add_duel_score(defender_idx, 20, "★ ESQUIVA PERFEITA!", defender.rect.centerx, defender.rect.top - 20, (120, 230, 255))
            self.floating_texts.append(FloatingCombatText(defender.rect.centerx, defender.rect.top - 15, "ESQUIVA!", (130, 220, 255)))
            defender.velocity.x += 80.0 * (1 if defender.facing_right else -1)
            return

        # ─────────────────────────────────────────────────────────────
        # CASE 1: PERFECT PARRY! (Defender pressed DEFEND within 0.28s)
        # ─────────────────────────────────────────────────────────────
        is_parry = (defender.is_blocking and defender.parry_window_timer > 0) or (hasattr(defender, "input") and defender.input.is_action_just_pressed("DEFEND"))
        if is_parry:
            # 100% damage nullified
            defender.stamina = min(defender.max_stamina, defender.stamina + 25.0)
            defender.mana = min(defender.max_mana, defender.mana + 15.0)
            defender.parry_window_timer = 0.0

            # Attacker is staggered and punished!
            attacker.is_attacking = False
            attacker.attack_cooldown = 0.40
            attacker.hurt_timer = 0.45
            attacker.velocity.x = -220.0 * attack_dir
            attacker.combo_count = 0
            attacker.combo_timer = 0.0

            # VFX & Game Feel
            GAME_FEEL.emit_slash_arc(defender.rect.centerx, defender.rect.centery, radius=36, color=(255, 235, 90))
            GAME_FEEL.trigger_hit_stop(attacker, duration_ms=80.0, shake_px=5.0, direction=-attack_dir)
            self.camera.shake(10.0, 0.32)

            # Scoring
            self.add_duel_score(defender_idx, 35, "★ PARRY!", defender.rect.centerx, defender.rect.top - 20, (255, 220, 70))
            self.floating_texts.append(FloatingCombatText(attacker.rect.centerx, attacker.rect.top - 15, "DESVIADO!", (230, 90, 90)))
            if defender_idx == 0:
                self.p1_stats["parries"] += 1
            else:
                self.p2_stats["parries"] += 1
            return

        # ─────────────────────────────────────────────────────────────
        # CASE 2: ACTIVE BLOCK (GUARD)
        # ─────────────────────────────────────────────────────────────
        if defender.is_blocking:
            stamina_cost = 28.0
            if defender.stamina <= 0 or (defender.stamina - stamina_cost) <= 0:
                # GUARD BREAK!
                defender.stamina = 0.0
                defender.guard_break_timer = 1.3
                defender.is_blocking = False
                defender.hurt_timer = 0.60
                chip_dmg = max(8, int(base_damage * 0.45))
                defender.health = max(0, defender.health - chip_dmg)
                defender.velocity.x = 140.0 * attack_dir

                GAME_FEEL.emit_slash_arc(defender.rect.centerx, defender.rect.centery, radius=38, color=(130, 220, 255))
                GAME_FEEL.emit_dust(defender.rect.centerx, defender.rect.bottom, "landing")
                self.camera.shake(12.0, 0.35)

                self.add_duel_score(attacker_idx, 50, "QUEBRA DE GUARDA!", attacker.rect.centerx, attacker.rect.top - 24, (255, 75, 75))
                self.floating_texts.append(FloatingCombatText(defender.rect.centerx, defender.rect.top - 15, "GUARDA QUEBRADA!", (255, 120, 120)))
                if attacker_idx == 0:
                    self.p1_stats["guard_breaks"] += 1
                else:
                    self.p2_stats["guard_breaks"] += 1
            else:
                # Clean Block
                defender.stamina = max(0.0, defender.stamina - stamina_cost)
                defender.stamina_regen_delay = 0.7
                chip_dmg = max(1, int(base_damage * 0.10))
                defender.health = max(0, defender.health - chip_dmg)
                defender.velocity.x = 100.0 * attack_dir
                defender.mana = min(defender.max_mana, defender.mana + 3.0)

                GAME_FEEL.emit_dust(defender.rect.centerx, defender.rect.bottom, "footstep")
                GAME_FEEL.emit_slash_arc(defender.rect.centerx, defender.rect.centery, radius=20, color=(110, 200, 255))

                self.add_duel_score(defender_idx, 10, "BLOQUEIO", defender.rect.centerx, defender.rect.top - 14, (100, 215, 255))
                if defender_idx == 0:
                    self.p1_stats["blocks"] += 1
                else:
                    self.p2_stats["blocks"] += 1
            return

        # ─────────────────────────────────────────────────────────────
        # CASE 3: UNBLOCKED HIT (CLEAN HIT OR COUNTER-HIT!)
        # ─────────────────────────────────────────────────────────────
        final_damage = base_damage
        is_counter = (defender.is_attacking or defender.is_casting_magic or defender.is_casting_aoe)
        if is_counter:
            final_damage *= 1.25
            self.add_duel_score(attacker_idx, 25, "⚡ CONTRA-GOLPE!", attacker.rect.centerx, attacker.rect.top - 22, (255, 140, 50))
            if attacker_idx == 0:
                self.p1_stats["counters"] += 1
            else:
                self.p2_stats["counters"] += 1
        else:
            if attacker.combo_timer > 0:
                attacker.combo_count += 1
            else:
                attacker.combo_count = 1
            attacker.combo_timer = 1.4

            combo_bonus = min(30, (attacker.combo_count - 1) * 10)
            pts = 10 + combo_bonus
            label = f"{attacker.combo_count}x COMBO!" if attacker.combo_count >= 2 else "GOLPE"
            color = (255, 210, 60) if attacker.combo_count >= 2 else (255, 235, 150)
            self.add_duel_score(attacker_idx, pts, label, attacker.rect.centerx, attacker.rect.top - 18, color)

            if attacker_idx == 0:
                self.p1_stats["hits"] += 1
                self.p1_stats["max_combo"] = max(self.p1_stats["max_combo"], attacker.combo_count)
            else:
                self.p2_stats["hits"] += 1
                self.p2_stats["max_combo"] = max(self.p2_stats["max_combo"], attacker.combo_count)

        # Apply damage & dynamic mana generation through offensive play
        defender.health = max(0, defender.health - int(final_damage))
        defender.hurt_timer = 0.32
        attacker.mana = min(attacker.max_mana, attacker.mana + 6.0)

        # Brawlhalla-Style Knockback scaling based on missing health:
        missing_hp_pct = max(0.0, 1.0 - (defender.health / max(1, defender.max_health)))
        scaled_kb_x = (220.0 + missing_hp_pct * 300.0) * attack_dir
        scaled_kb_y = -(130.0 + missing_hp_pct * 140.0)
        defender.velocity.x = scaled_kb_x
        defender.velocity.y = scaled_kb_y
        defender.on_ground = False

        GAME_FEEL.trigger_hit_stop(defender, duration_ms=55.0 + missing_hp_pct * 35.0, shake_px=4.0, direction=attack_dir)
        GAME_FEEL.emit_slash_arc(defender.rect.centerx, defender.rect.centery, radius=30, color=(255, 230, 160))
        self.camera.shake(7.0 + missing_hp_pct * 8.0, 0.25)

    def draw(self, surface: pygame.Surface) -> None:
        sw, sh = self.width, self.height
        cam_offset = self.camera.offset

        # 1. Background Parallax
        if self.parallax:
            self.parallax.draw(surface, cam_offset.x, cam_offset.y)
        else:
            surface.fill((18, 20, 30))

        # 2. Clouds & Weather
        if getattr(SETTINGS, "CLOUDS_COUNT", 0) > 0 and self.clouds:
            self.clouds.draw(surface, cam_offset, sw, sh)

        # 3. Distant Mist
        if getattr(SETTINGS, "MIST_LAYERS", 0) > 0 and self.mist:
            self.mist.draw_distant_fog(surface, cam_offset.x, cam_offset.y)

        # 4. Arena Boundary Pillars & Floor
        pygame.draw.rect(surface, (35, 38, 52), (0, self.floor_y - cam_offset.y, sw, sh - self.floor_y))
        pygame.draw.line(surface, (70, 78, 105), (0, self.floor_y - cam_offset.y), (sw, self.floor_y - cam_offset.y), 2)
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

        # 6.1 Guard Break / Stun Indicator above fighters
        f_badge = HollowFonts.get(8, bold=True)
        for p, col in [(self.player1, (255, 90, 90)), (self.player2, (255, 90, 90))]:
            if getattr(p, "guard_break_timer", 0.0) > 0:
                t_st = f_badge.render("QUEBRA DE GUARDA!", True, col)
                bx = int(p.rect.centerx - cam_offset.x - t_st.get_width() // 2)
                by = int(p.rect.top - cam_offset.y - 18)
                pygame.draw.rect(surface, (20, 22, 30), (bx - 3, by - 1, t_st.get_width() + 6, 12))
                pygame.draw.rect(surface, (255, 80, 80), (bx - 3, by - 1, t_st.get_width() + 6, 12), width=1)
                surface.blit(t_st, (bx, by))

        # 7. Flying Projectiles
        for proj in self.projectiles:
            proj.draw(surface, cam_offset)

        # 8. Game Feel Effects (Dust & Slash Arcs)
        GAME_FEEL.draw_dust(surface, cam_offset)
        GAME_FEEL.draw_slash_arcs(surface, cam_offset)

        # 8.1 Floating Combat Badges
        for ft in self.floating_texts:
            ft.draw(surface, cam_offset)

        # 9. Ground Mist
        if getattr(SETTINGS, "MIST_LAYERS", 0) > 0 and self.mist:
            self.mist.draw_ground_mist(surface, cam_offset.x, cam_offset.y)

        # 10. Dynamic Point Lights & God Rays
        lights = []
        for tx, ty, trad, tcol, tint in GAME_FEEL.get_active_point_lights():
            lights.append(LightSource(tx, ty, int(trad), tcol, tint))
        if getattr(SETTINGS, "DYNAMIC_LIGHTS", True):
            self.lighting.draw_point_lights(surface, lights, cam_offset)

        # 11. Fullscreen Ultimate Cinematic Passes
        if self.player1.is_casting_ultimate:
            self.player1.ultimate_controller.draw_screen(surface)
        if self.player2.is_casting_ultimate:
            self.player2.ultimate_controller.draw_screen(surface)

        # 12. Vignette
        if getattr(SETTINGS, "VIGNETTE_ENABLED", True):
            self.lighting.draw_vignette(surface)

        # 13. Symmetrical Fighting HUD (Health, Posture, Mana, Mastery Scores)
        self._draw_fighting_hud(surface)

        # 14. Banners & Scoreboards
        self._draw_banners(surface)

    def _draw_fighting_hud(self, surface: pygame.Surface):
        """Draws official glassmorphic HUDs identical to other modes plus central Duel Round Timer, Orbs, and Command Map."""
        sw = self.width
        cx = sw // 2

        # 1. Render Official Polished Glassmorphic HUDs (HP with ghost lag, MP with ready glow, SP with dash pips, and Skill Hotbars)
        self.hud1.draw(surface)
        self.hud2.draw(surface)

        # 2. Central Round Info (Round 99s Timer, Win Orbs, Score readouts)
        f_hud = HollowFonts.get(10, bold=True)
        f_timer = HollowFonts.get(22, bold=True)
        f_sub = HollowFonts.get(8, bold=True)

        # Center Round 99s Timer with dramatic clock styling
        time_int = int(math.ceil(self.round_time))
        t_col = (255, 230, 120) if time_int > 10 else (255, 75, 75)
        timer_box = pygame.Rect(cx - 30, 8, 60, 28)
        pygame.draw.rect(surface, (14, 17, 26, 225), timer_box, border_radius=4)
        pygame.draw.rect(surface, (135, 115, 60), timer_box, 1, border_radius=4)
        timer_surf = f_timer.render(f"{time_int:02d}", True, t_col)
        surface.blit(timer_surf, timer_surf.get_rect(center=(cx, 21)))

        # Round label
        lbl_rnd = f_sub.render(f"ROUND {self.round_number}", True, (215, 220, 235))
        surface.blit(lbl_rnd, lbl_rnd.get_rect(center=(cx, 40)))

        # Round Win Orbs (P1 on left of timer, P2 on right of timer)
        for i in range(2):
            p1_won = self.p1_rounds_won > i
            col1 = (255, 215, 60) if p1_won else (45, 50, 65)
            pygame.draw.circle(surface, col1, (cx - 44 - i * 14, 22), 5)
            pygame.draw.circle(surface, (180, 190, 210), (cx - 44 - i * 14, 22), 5, width=1)

            p2_won = self.p2_rounds_won > i
            col2 = (130, 210, 255) if p2_won else (45, 50, 65)
            pygame.draw.circle(surface, col2, (cx + 44 + i * 14, 22), 5)
            pygame.draw.circle(surface, (180, 190, 210), (cx + 44 + i * 14, 22), 5, width=1)

        # Mastery Points readouts beside timer
        pts_p1 = f_sub.render(f"{self.p1_score} PTS", True, (245, 220, 120))
        surface.blit(pts_p1, pts_p1.get_rect(center=(cx - 96, 22)))

        pts_p2 = f_sub.render(f"{self.p2_score} PTS", True, (130, 210, 255))
        surface.blit(pts_p2, pts_p2.get_rect(center=(cx + 96, 22)))

        # Dynamic Combo Badges
        if getattr(self.player1, "combo_count", 0) >= 2:
            t_combo = f_hud.render(f"{self.player1.combo_count}x COMBO!", True, (255, 215, 60))
            surface.blit(t_combo, (160, 48))

        if getattr(self.player2, "combo_count", 0) >= 2:
            t_combo2 = f_hud.render(f"{self.player2.combo_count}x COMBO!", True, (130, 215, 255))
            surface.blit(t_combo2, (sw - 160 - t_combo2.get_width(), 48))

        # 3. Dedicated Combat Command Map (Mapa de Comandos) at Bottom-Center
        if getattr(self, "show_command_map", True):
            cmd_w = 276
            cmd_h = 42
            cmd_x = (sw - cmd_w) // 2
            cmd_y = self.height - cmd_h - 6
            cmd_rect = pygame.Rect(cmd_x, cmd_y, cmd_w, cmd_h)
            
            # Subtle glass panel
            panel_s = pygame.Surface((cmd_w, cmd_h), pygame.SRCALPHA)
            panel_s.fill((12, 15, 24, 225))
            surface.blit(panel_s, (cmd_x, cmd_y))
            pygame.draw.rect(surface, (70, 80, 105), cmd_rect, width=1, border_radius=4)

            f_key = HollowFonts.get(8, bold=True)
            f_lbl = HollowFonts.get(8)

            # Header / Title
            t_hdr = f_key.render("‹ MAPA DE COMANDOS ›", True, (255, 215, 80))
            surface.blit(t_hdr, t_hdr.get_rect(center=(cx, cmd_y + 8)))

            # P1 Controls Line (Left accent gold)
            t_p1_keys = f_lbl.render("P1: [WASD] Mover/Pulo  [J] Atk  [K] Mag  [Q] Esq  [Shift] Parry", True, (245, 220, 130))
            surface.blit(t_p1_keys, t_p1_keys.get_rect(center=(cx, cmd_y + 20)))

            # P2 Controls Line (Right accent cyan)
            t_p2_keys = f_lbl.render("P2: [Setas] Mover/Pulo [N1] Atk [N2] Mag [N0] Esq [N6] Parry", True, (130, 210, 255))
            surface.blit(t_p2_keys, t_p2_keys.get_rect(center=(cx, cmd_y + 31)))

    def _draw_banners(self, surface: pygame.Surface):
        """Draws fighting banners during Intro, Round Over, and Match Over with Combat Mastery Scorecard."""
        cx = self.width // 2
        cy = self.height // 2 - 20

        if self.banner_text and self.state != "MATCH_OVER":
            f_banner = HollowFonts.get(22, bold=True)
            b_surf = f_banner.render(self.banner_text, True, (255, 235, 130))
            overlay = pygame.Surface((self.width, 42), pygame.SRCALPHA)
            overlay.fill((10, 12, 18, 200))
            surface.blit(overlay, (0, cy - 20))
            pygame.draw.line(surface, (255, 215, 60), (0, cy - 20), (self.width, cy - 20), 1)
            pygame.draw.line(surface, (255, 215, 60), (0, cy + 22), (self.width, cy + 22), 1)
            surface.blit(b_surf, b_surf.get_rect(center=(cx, cy)))

            if self.sub_banner_text:
                f_sub = HollowFonts.get(10)
                s_surf = f_sub.render(self.sub_banner_text, True, (200, 215, 235))
                surface.blit(s_surf, s_surf.get_rect(center=(cx, cy + 28)))

        # Match Over: Complete Combat Mastery Scoreboard!
        if self.state == "MATCH_OVER":
            box_w = 460
            box_h = 230
            box_x = (self.width - box_w) // 2
            box_y = (self.height - box_h) // 2 - 10

            # Dark Slate Card Backing
            card_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
            card_surf.fill((14, 16, 24, 235))
            surface.blit(card_surf, (box_x, box_y))
            pygame.draw.rect(surface, (255, 215, 80), (box_x, box_y, box_w, box_h), width=2)
            pygame.draw.rect(surface, (60, 70, 95), (box_x + 3, box_y + 3, box_w - 6, box_h - 6), width=1)

            # Header: Winner
            f_win = HollowFonts.get(18, bold=True)
            w_surf = f_win.render(self.winner_text, True, (255, 225, 90))
            surface.blit(w_surf, w_surf.get_rect(center=(cx, box_y + 24)))

            # Subheader
            f_sub = HollowFonts.get(10)
            score_header = f"ROUNDS: P1 ({self.p1_rounds_won}) - P2 ({self.p2_rounds_won})   |   PONTOS TOTAIS: P1 ({self.p1_score}) vs P2 ({self.p2_score})"
            sh_surf = f_sub.render(score_header, True, (210, 225, 245))
            surface.blit(sh_surf, sh_surf.get_rect(center=(cx, box_y + 45)))

            pygame.draw.line(surface, (80, 90, 120), (box_x + 15, box_y + 60), (box_x + box_w - 15, box_y + 60), 1)

            # Mastery Stats Table
            f_cat = HollowFonts.get(10, bold=True)
            f_stat = HollowFonts.get(9)

            c_p1_x = box_x + 40
            c_label_x = cx
            c_p2_x = box_x + box_w - 40

            t_h1 = f_cat.render(f"P1: {self.p1_char.upper()}", True, (245, 225, 130))
            t_h2 = f_cat.render(f"P2: {self.p2_char.upper()}", True, (130, 205, 255))
            surface.blit(t_h1, (c_p1_x, box_y + 70))
            surface.blit(t_h2, (c_p2_x - t_h2.get_width(), box_y + 70))

            rows = [
                ("Golpes Conectados", str(self.p1_stats["hits"]), str(self.p2_stats["hits"])),
                ("Parries Perfeitos (★)", str(self.p1_stats["parries"]), str(self.p2_stats["parries"])),
                ("Bloqueios Realizados", str(self.p1_stats["blocks"]), str(self.p2_stats["blocks"])),
                ("Quebras de Guarda", str(self.p1_stats["guard_breaks"]), str(self.p2_stats["guard_breaks"])),
                ("Contra-Golpes", str(self.p1_stats["counters"]), str(self.p2_stats["counters"])),
                ("Maior Combo", f"{self.p1_stats['max_combo']}x", f"{self.p2_stats['max_combo']}x"),
                ("PONTUAÇÃO DE MAESTRIA", f"{self.p1_score} pts", f"{self.p2_score} pts"),
            ]

            start_y = box_y + 92
            for idx, (label, val1, val2) in enumerate(rows):
                ry = start_y + idx * 16
                is_total = (idx == len(rows) - 1)
                col_lbl = (255, 220, 80) if is_total else (180, 195, 220)
                col_val1 = (255, 230, 140) if is_total else (235, 240, 250)
                col_val2 = (140, 215, 255) if is_total else (235, 240, 250)
                font_use = f_cat if is_total else f_stat

                t_lbl = font_use.render(label, True, col_lbl)
                surface.blit(t_lbl, t_lbl.get_rect(center=(c_label_x, ry)))

                t_v1 = font_use.render(val1, True, col_val1)
                surface.blit(t_v1, (c_p1_x, ry))

                t_v2 = font_use.render(val2, True, col_val2)
                surface.blit(t_v2, (c_p2_x - t_v2.get_width(), ry))

            f_hint = HollowFonts.get(9)
            h_surf = f_hint.render("[ENTER / ESPAÇO] VOLTAR À SELEÇÃO   |   [ESC] MENU PRINCIPAL", True, (180, 195, 225))
            surface.blit(h_surf, h_surf.get_rect(center=(cx, box_y + box_h - 14)))
