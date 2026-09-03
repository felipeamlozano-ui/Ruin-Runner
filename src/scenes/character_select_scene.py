import pygame
import math
import os
import random
from config.settings import SETTINGS
from config.colors import WHITE, GOLD, RED, BLUE, GREEN, GRAY, UI_BACKGROUND
from engine.scene_manager import Scene
from engine.input_manager import INPUT
from entities.player import Player
from entities.character_data import CHARACTER_REGISTRY, CHARACTER_ORDER, get_character_profile

class CharacterSelectScene(Scene):
    """
    AAA Character Selection & Interactive Dojo Scene.
    Players can cycle through all 7 characters (Shaia + 3 Mages + 3 Martial Artists),
    inspect their lore, stats, and skills, and interactively test all moves in real-time
    with live combat animations and VFX!
    """

    def __init__(self, scene_manager, previous_scene=None):
        super().__init__(scene_manager)
        self.previous_scene = previous_scene
        
        # Load fonts
        pygame.font.init()
        self.font_title = pygame.font.SysFont("Georgia", 22, bold=True)
        self.font_name = pygame.font.SysFont("Arial", 18, bold=True)
        self.font_subtitle = pygame.font.SysFont("Arial", 12, bold=True)
        self.font_body = pygame.font.SysFont("Arial", 11)
        self.font_stat = pygame.font.SysFont("Courier New", 11, bold=True)
        self.font_key = pygame.font.SysFont("Arial", 10, bold=True)
        self.font_banner = pygame.font.SysFont("Arial", 12, bold=True)
        
        # Determine initial selection
        cur_id = getattr(SETTINGS, "CURRENT_CHARACTER", "shaia")
        if cur_id in CHARACTER_ORDER:
            self.selected_index = CHARACTER_ORDER.index(cur_id)
        else:
            self.selected_index = 0
            
        # Pedestal and arena positioning
        self.pedestal_pos = pygame.math.Vector2(190, 205)
        self.dummy_tiles = [
            pygame.FRect(60, 210, 260, 40)
        ]
        
        # Ambient particles
        self.ambient_particles = []
        for _ in range(25):
            self.ambient_particles.append({
                "x": random.uniform(80, 300),
                "y": random.uniform(80, 230),
                "speed": random.uniform(15, 40),
                "size": random.uniform(1.5, 3.5),
                "alpha": random.randint(100, 220)
            })
            
        # Skill Icons cache
        self.skill_icons = {}
        self._load_skill_icons()
        
        # Thumbnail portraits cache
        self.thumbnails = {}
        for cid in CHARACTER_ORDER:
            prof = CHARACTER_REGISTRY[cid]
            try:
                if prof.sprite_type == "folder":
                    p = os.path.join(prof.base_folder, "common_00_idle_stand_A_000.png")
                    if os.path.exists(p):
                        raw = pygame.image.load(p).convert_alpha()
                        sub = raw.subsurface((raw.get_width() // 2 - 20, 10, 40, 40))
                        self.thumbnails[cid] = pygame.transform.smoothscale(sub, (22, 22))
                else:
                    p = os.path.join(prof.base_folder, "Idle.png")
                    if os.path.exists(p):
                        raw = pygame.image.load(p).convert_alpha()
                        fw, fh = prof.frame_size
                        frame = raw.subsurface((0, 0, fw, fh))
                        sub = frame.subsurface((fw // 2 - 24, 30 if prof.archetype == "mage" else 22, 48, 48))
                        self.thumbnails[cid] = pygame.transform.smoothscale(sub, (22, 22))
            except Exception:
                self.thumbnails[cid] = None
        
        # Move tester feedback
        self.last_tested_action = "ARENA LIVRE: Pressione [J], [K], [E], [Shift], [Q], [R], [Espaço] para testar golpes!"
        self.banner_timer = 4.0
        self.active_test_key = None
        self.test_key_timer = 0.0
        
        # Buttons for mouse clicks
        self.btn_left_rect = pygame.FRect(35, 150, 28, 40)
        self.btn_right_rect = pygame.FRect(315, 150, 28, 40)
        self.btn_play_rect = pygame.FRect(465, 318, 155, 32)
        self.btn_back_rect = pygame.FRect(345, 318, 105, 32)
        
        # Instantiate preview player
        self._spawn_preview_player()

    def _load_skill_icons(self):
        """Loads and caches 64x64 skill icons scaled to 24x24 for preview cards."""
        icons_dir = os.path.join("assets", "sprites", "icons", "skills")
        if not os.path.exists(icons_dir):
            icons_dir = os.path.join("assets", "sprites", "fantasy_skills", "64x64")
            
        for cid in CHARACTER_ORDER:
            prof = CHARACTER_REGISTRY[cid]
            for skey, sdata in prof.skills.items():
                if sdata.icon_file not in self.skill_icons:
                    p = os.path.join(icons_dir, sdata.icon_file)
                    if os.path.exists(p):
                        img = pygame.image.load(p).convert_alpha()
                        self.skill_icons[sdata.icon_file] = pygame.transform.smoothscale(img, (22, 22))
                    else:
                        self.skill_icons[sdata.icon_file] = None

    def _spawn_preview_player(self):
        """Spawns or switches the interactive preview player on the pedestal."""
        cid = CHARACTER_ORDER[self.selected_index]
        self.profile = get_character_profile(cid)
        self.player = Player(self.pedestal_pos.x - 16, self.pedestal_pos.y - 75, character_id=cid)
        self.player.mana = self.player.max_mana
        self.player.stamina = self.player.max_stamina
        self.player.facing_right = True

    def _select_character(self, index: int):
        """Switches the selected character and refreshes preview."""
        self.selected_index = index % len(CHARACTER_ORDER)
        self._spawn_preview_player()
        self.last_tested_action = f"Personagem selecionado: {self.profile.name} ({self.profile.title})"
        self.banner_timer = 2.5

    def _confirm_and_play(self):
        """Saves selected character to settings and enters the game."""
        cid = CHARACTER_ORDER[self.selected_index]
        SETTINGS.CURRENT_CHARACTER = cid
        from scenes.level_scene import LevelScene
        self.scene_manager.change_scene(LevelScene(stage=1, scene_manager=self.scene_manager))

    def _go_back(self):
        """Returns to previous scene or main menu."""
        if self.previous_scene:
            self.scene_manager.change_scene(self.previous_scene)
        else:
            from scenes.main_menu import MainMenuScene
            self.scene_manager.change_scene(MainMenuScene(self.scene_manager))

    def handle_events(self, events: list[pygame.event.Event]):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                    self._go_back()
                    return
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._confirm_and_play()
                    return
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    self._select_character(self.selected_index - 1)
                    return
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self._select_character(self.selected_index + 1)
                    return
                    
                # Interactive Dojo Keys
                elif event.key == pygame.K_j:
                    self._trigger_dojo_move("j")
                elif event.key == pygame.K_k:
                    self._trigger_dojo_move("k")
                elif event.key == pygame.K_e:
                    self._trigger_dojo_move("e")
                elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    self._trigger_dojo_move("shift")
                elif event.key == pygame.K_q:
                    self._trigger_dojo_move("q")
                elif event.key == pygame.K_r:
                    self._trigger_dojo_move("r")
                elif event.key == pygame.K_SPACE:
                    self._trigger_dojo_move("space")
                    
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if self.btn_left_rect.collidepoint(mx, my):
                    self._select_character(self.selected_index - 1)
                elif self.btn_right_rect.collidepoint(mx, my):
                    self._select_character(self.selected_index + 1)
                elif self.btn_play_rect.collidepoint(mx, my):
                    self._confirm_and_play()
                elif self.btn_back_rect.collidepoint(mx, my):
                    self._go_back()
                else:
                    # Check carousel thumbnails click
                    cy = 318
                    cw, ch = 38, 32
                    for i in range(len(CHARACTER_ORDER)):
                        cx = 36 + i * 44
                        if pygame.FRect(cx, cy, cw, ch).collidepoint(mx, my):
                            self._select_character(i)

    def _trigger_dojo_move(self, key: str):
        """Simulates real character action in the test arena."""
        self.active_test_key = key
        self.test_key_timer = 0.35
        
        # Replenish stats in preview mode
        self.player.mana = self.player.max_mana
        self.player.stamina = self.player.max_stamina
        
        if key == "j":
            j_skill = self.profile.skills.get("j")
            self.player.is_attacking = True
            self.player.anim_manager.play("attack", force_reset=True)
            if self.player.archetype == "mage":
                from entities.projectile import Projectile
                proj_x = self.player.rect.right + 8
                proj_y = self.player.rect.centery - 8
                ptype = j_skill.projectile_type or "arcane_bolt"
                self.player.projectiles.append(Projectile(proj_x, proj_y, True, is_enemy=False, projectile_type=ptype))
            self.last_tested_action = f"[J] {j_skill.name}: {j_skill.description}"
            self.banner_timer = 3.2
            
        elif key == "k":
            k_skill = self.profile.skills.get("k")
            self.player.is_casting_magic = True
            self.player.magic_cast_timer = 0.35
            self.player.magic_sigil_timer = 0.40
            self.player.anim_manager.play("cast_magic", force_reset=True)
            from entities.projectile import Projectile
            proj_x = self.player.rect.right + 8
            proj_y = self.player.rect.centery - 8
            ptype = k_skill.projectile_type or "fireball"
            self.player.projectiles.append(Projectile(proj_x, proj_y, True, is_enemy=False, projectile_type=ptype))
            self.last_tested_action = f"[K] {k_skill.name}: {k_skill.description}"
            self.banner_timer = 3.2
            
        elif key == "e":
            e_skill = self.profile.skills.get("e")
            self.player.is_casting_aoe = True
            self.player.aoe_timer = 0.7
            self.player.aoe_hit_done = False
            self.player.anim_manager.play("whirlwind", force_reset=True)
            self.last_tested_action = f"[E] {e_skill.name}: {e_skill.description}"
            self.banner_timer = 3.2
            
        elif key == "shift":
            sh_skill = self.profile.skills.get("shift")
            self.player.is_blocking = True
            self.player.anim_manager.play("guard", force_reset=True)
            self.last_tested_action = f"[Shift] {sh_skill.name}: {sh_skill.description}"
            self.banner_timer = 3.2
            
        elif key == "q":
            self.player.is_dashing = True
            self.player.dash_timer = 0.25
            self.player.dash_cooldown = 0.4
            self.player.velocity.x = 280
            self.player.anim_manager.play("dash", force_reset=True)
            self.last_tested_action = "[Q] DASH / ESQUIVA: Impulso acrobático de esquiva veloz com frames de invulnerabilidade"
            self.banner_timer = 3.2
            
        elif key == "r":
            r_skill = self.profile.skills.get("r")
            self.player.is_casting_ultimate = True
            self.player.ultimate_timer = 0.0
            self.player.ultimate_hit_done = False
            self.player.anim_manager.play("guard", force_reset=True)
            self.player.ultimate_shockwave_active = True
            self.player.ultimate_shockwave_pos = (self.player.rect.centerx, self.player.rect.bottom)
            self.player.ultimate_shockwave_timer = 0.8
            self.player.ultimate_shockwave_anim.reset()
            self.player.ultimate_particles.clear()
            self.player.ultimate_shockwave_rings.clear()
            self.player.ultimate_slashes.clear()
            self.last_tested_action = f"[R] ULTIMATE {r_skill.name.upper()}: {r_skill.description}"
            self.banner_timer = 4.0
            
        elif key == "space":
            if self.player.on_ground:
                self.player.velocity.y = -360
                self.player.on_ground = False
                self.player.anim_manager.play("jump", force_reset=True)
            self.last_tested_action = "[Espaço] SALTO: Pulo ágil e acrobático com suporte a salto duplo"
            self.banner_timer = 2.5

    def update(self, dt: float):
        # Update banner timer
        if self.banner_timer > 0:
            self.banner_timer -= dt
            if self.banner_timer <= 0:
                self.last_tested_action = "ARENA LIVRE: Pressione [J], [K], [E], [Shift], [Q], [R], [Espaço] para testar golpes!"
                
        if self.test_key_timer > 0:
            self.test_key_timer -= dt
            if self.test_key_timer <= 0:
                self.active_test_key = None
                
        # Keep player on pedestal arena
        self.player.update(dt, self.dummy_tiles)
        
        # If player drifted off pedestal during dash, tether back gently
        if not self.player.is_dashing:
            if abs(self.player.pos.x - (self.pedestal_pos.x - 16)) > 40:
                self.player.pos.x += ((self.pedestal_pos.x - 16) - self.player.pos.x) * dt * 4.0
                self.player.rect.x = self.player.pos.x
                
        # Update projectiles
        camera_offset = pygame.math.Vector2(0, 0)
        for p in self.player.projectiles[:]:
            p.update(dt, [])
            # Dissipate if out of arena frame
            if p.rect.x > 330 or p.rect.x < 50 or not p.active:
                if p in self.player.projectiles:
                    self.player.projectiles.remove(p)
                    
        # Update ambient particles
        col = self.profile.color_theme
        for p in self.ambient_particles:
            p["y"] -= p["speed"] * dt
            if p["y"] < 80:
                p["y"] = 230
                p["x"] = random.uniform(80, 300)

    def draw(self, surface: pygame.Surface):
        # 1. Dark Atmospheric Background
        surface.fill((10, 11, 18))
        col = self.profile.color_theme
        
        # Draw floating motes
        for p in self.ambient_particles:
            p_surf = pygame.Surface((int(p["size"] * 2), int(p["size"] * 2)), pygame.SRCALPHA)
            pygame.draw.circle(p_surf, (*col, p["alpha"]), (int(p["size"]), int(p["size"])), int(p["size"]))
            surface.blit(p_surf, (int(p["x"]), int(p["y"])), special_flags=pygame.BLEND_RGBA_ADD)
            
        # 2. Grand Sanctuary Header
        header_surf = self.font_title.render("SALA DOS HERÓIS", True, GOLD)
        surface.blit(header_surf, (28, 12))
        sub_surf = self.font_subtitle.render("SELEÇÃO DE PERSONAGEM & ARENA DE HABILIDADES", True, (160, 175, 200))
        surface.blit(sub_surf, (30, 38))
        
        # Horizontal golden rule
        pygame.draw.line(surface, (85, 75, 45), (28, 54), (612, 54), 1)
        pygame.draw.line(surface, (180, 155, 75), (28, 54), (220, 54), 2)
        
        # 3. Pedestal & Champion Dais (Left side)
        self._draw_pedestal(surface)
        
        # Draw interactive preview player and effects
        camera_offset = pygame.math.Vector2(0, 0)
        self.player.draw(surface, camera_offset)
        
        # Draw player projectiles
        for proj in self.player.projectiles:
            proj.draw(surface, camera_offset)
            
        # 4. Carousel arrows for changing character
        self._draw_carousel_controls(surface)
        
        # 5. Live Move Tester Controls & Feedback Banner
        self._draw_dojo_test_panel(surface)
        
        # 6. Character Dossier & Stats Panel (Right side)
        self._draw_character_dossier(surface)
        
        # 7. Bottom Navigation & Action Buttons
        self._draw_action_buttons(surface)

    def _draw_pedestal(self, surface: pygame.Surface):
        """Draws a grand glowing dais with rotating runic arcs."""
        px, py = int(self.pedestal_pos.x), int(self.pedestal_pos.y) + 5
        col = self.profile.color_theme
        
        # Spotlight shaft from below header bar
        beam_h = max(20, int(py - 56))
        beam_surf = pygame.Surface((120, beam_h), pygame.SRCALPHA)
        poly = [(42, 0), (78, 0), (120, beam_h), (0, beam_h)]
        beam_alpha = int(15 + 5 * math.sin(pygame.time.get_ticks() * 0.003))
        pygame.draw.polygon(beam_surf, (*col, beam_alpha), poly)
        surface.blit(beam_surf, (px - 60, 56), special_flags=pygame.BLEND_RGBA_ADD)
        
        # Stone Dais base (3D ellipse)
        base_w, base_h = 130, 26
        # Shadow / lower depth
        pygame.draw.ellipse(surface, (20, 24, 34), (px - base_w // 2, py - base_h // 2 + 6, base_w, base_h))
        pygame.draw.ellipse(surface, (40, 48, 65), (px - base_w // 2, py - base_h // 2, base_w, base_h))
        pygame.draw.ellipse(surface, (*col, 180), (px - base_w // 2, py - base_h // 2, base_w, base_h), 2)
        
        # Inner runic ring
        inner_w, inner_h = 96, 18
        pygame.draw.ellipse(surface, (25, 30, 42), (px - inner_w // 2, py - inner_h // 2, inner_w, inner_h))
        pygame.draw.ellipse(surface, (255, 255, 255, 120), (px - inner_w // 2, py - inner_h // 2, inner_w, inner_h), 1)
        
        # Orbiting glyph dots on dais
        t = pygame.time.get_ticks() * 0.002
        for i in range(5):
            ang = t + i * (math.pi * 2 / 5)
            gx = px + int(math.cos(ang) * (inner_w // 2 - 4))
            gy = py + int(math.sin(ang) * (inner_h // 2 - 2))
            pygame.draw.circle(surface, (*col, 220), (gx, gy), 2)

    def _draw_carousel_controls(self, surface: pygame.Surface):
        """Draws left/right switch buttons and active index indicator."""
        # Left Arrow
        col_l = GOLD if self.btn_left_rect.collidepoint(pygame.mouse.get_pos()) else (140, 150, 175)
        pygame.draw.rect(surface, (22, 26, 38), self.btn_left_rect, border_radius=4)
        pygame.draw.rect(surface, col_l, self.btn_left_rect, 1, border_radius=4)
        arrow_l = self.font_name.render("<", True, col_l)
        surface.blit(arrow_l, (self.btn_left_rect.x + 8, self.btn_left_rect.y + 7))
        
        # Right Arrow
        col_r = GOLD if self.btn_right_rect.collidepoint(pygame.mouse.get_pos()) else (140, 150, 175)
        pygame.draw.rect(surface, (22, 26, 38), self.btn_right_rect, border_radius=4)
        pygame.draw.rect(surface, col_r, self.btn_right_rect, 1, border_radius=4)
        arrow_r = self.font_name.render(">", True, col_r)
        surface.blit(arrow_r, (self.btn_right_rect.x + 8, self.btn_right_rect.y + 7))
        
        # Character Counter Badge pill
        badge_text = f"HERÓI {self.selected_index + 1} / {len(CHARACTER_ORDER)}"
        badge_surf = self.font_key.render(badge_text, True, (215, 225, 240))
        bw = badge_surf.get_width() + 14
        bh = 17
        bx = int(self.pedestal_pos.x - bw // 2)
        by = 64
        pygame.draw.rect(surface, (18, 22, 34), (bx, by, bw, bh), border_radius=8)
        pygame.draw.rect(surface, (60, 75, 105), (bx, by, bw, bh), 1, border_radius=8)
        surface.blit(badge_surf, (bx + 7, by + 2))

    def _draw_dojo_test_panel(self, surface: pygame.Surface):
        """Draws interactive move-tester keycaps and action feedback banner."""
        # Feedback banner
        banner_rect = pygame.FRect(35, 236, 305, 24)
        pygame.draw.rect(surface, (18, 22, 34), banner_rect, border_radius=4)
        pygame.draw.rect(surface, (50, 60, 85), banner_rect, 1, border_radius=4)
        
        ban_text = self.font_banner.render(self.last_tested_action, True, (235, 225, 180))
        clip_surf = pygame.Surface((banner_rect.width - 10, 20), pygame.SRCALPHA)
        clip_surf.blit(ban_text, (0, 2))
        surface.blit(clip_surf, (banner_rect.x + 6, banner_rect.y + 2))
        
        # Fitted keycaps row
        keycaps = [
            ("j", "J: Atq", 44),
            ("k", "K: Mag", 44),
            ("e", "E: Esp", 44),
            ("shift", "Shift: Def", 58),
            ("q", "Q: Dash", 44),
            ("r", "R: Ult", 42)
        ]
        
        kx = 35
        ky = 265
        kh = 22
        
        for k_id, k_label, kw in keycaps:
            is_active = (self.active_test_key == k_id)
            bg_col = self.profile.color_theme if is_active else (25, 30, 44)
            text_col = (10, 10, 15) if is_active else (200, 210, 230)
            
            k_rect = pygame.FRect(kx, ky, kw, kh)
            pygame.draw.rect(surface, bg_col, k_rect, border_radius=3)
            pygame.draw.rect(surface, (90, 105, 140) if not is_active else WHITE, k_rect, 1, border_radius=3)
            
            lbl_surf = self.font_key.render(k_label, True, text_col)
            surface.blit(lbl_surf, (k_rect.x + (k_rect.width - lbl_surf.get_width()) // 2, k_rect.y + 4))
            kx += kw + 4

    def _draw_character_dossier(self, surface: pygame.Surface):
        """Draws character name, archetype, lore, and 5 skill cards on the right side."""
        dx = 355
        dy = 60
        dw = 258
        dh = 250
        
        # Glassmorphic dossier panel
        panel_bg = pygame.Surface((dw, dh), pygame.SRCALPHA)
        panel_bg.fill((16, 20, 30, 235))
        surface.blit(panel_bg, (dx, dy))
        
        col = self.profile.color_theme
        pygame.draw.rect(surface, (60, 70, 95), (dx, dy, dw, dh), 1, border_radius=4)
        pygame.draw.line(surface, col, (dx + 2, dy + 2), (dx + dw - 2, dy + 2), 2)
        
        # Name and Title
        name_surf = self.font_name.render(self.profile.name.upper(), True, col)
        surface.blit(name_surf, (dx + 12, dy + 8))
        
        title_surf = self.font_subtitle.render(self.profile.title, True, (215, 225, 240))
        surface.blit(title_surf, (dx + 12, dy + 28))
        
        # Archetype Tag Badge
        arch_map = {
            "warrior": "GUERREIRA VALQUÍRIA",
            "mage": "MAGA ELEMENTAL",
            "shinobi": "NINJA DAS SOMBRAS",
            "samurai": "MESTRE ESPADACHIM",
            "fighter": "MONGE ARTISTA MARCIAL"
        }
        badge_str = arch_map.get(self.profile.archetype, self.profile.archetype.upper())
        badge_surf = self.font_key.render(f"[ {badge_str} ]", True, GOLD)
        surface.blit(badge_surf, (dx + dw - badge_surf.get_width() - 10, dy + 10))
        
        # Divider
        pygame.draw.line(surface, (45, 52, 70), (dx + 10, dy + 45), (dx + dw - 10, dy + 45), 1)
        
        # Attribute Bars (HP, MP, SP, Dano, Vel)
        stats = [
            ("VIDA", f"{self.profile.hp_max}", self.profile.hp_max / 25.0, (215, 45, 45)),
            ("MANA", f"{self.profile.mp_max}", self.profile.mp_max / 170.0, (45, 130, 240)),
            ("ESTAMINA", f"{self.profile.sp_max}", self.profile.sp_max / 130.0, (40, 190, 80)),
            ("DANO", f"{self.profile.stats.get('dano', 8)} / 10", self.profile.stats.get("dano", 8) / 10.0, (235, 170, 30)),
            ("VELOCIDADE", f"{self.profile.stats.get('agilidade', 8)} / 10", self.profile.stats.get("agilidade", 8) / 10.0, (170, 90, 240))
        ]
        
        sy = dy + 52
        for s_label, s_val, s_ratio, s_col in stats:
            lbl = self.font_stat.render(s_label, True, (175, 185, 205))
            surface.blit(lbl, (dx + 12, sy))
            
            # Bar box
            bx = dx + 88
            bw = 100
            bh = 7
            pygame.draw.rect(surface, (30, 35, 50), (bx, sy + 3, bw, bh), border_radius=2)
            fill_w = max(4, int(bw * max(0.0, min(1.0, s_ratio))))
            pygame.draw.rect(surface, s_col, (bx, sy + 3, fill_w, bh), border_radius=2)
            
            val_surf = self.font_key.render(s_val, True, (240, 240, 240))
            surface.blit(val_surf, (bx + bw + 6, sy - 1))
            sy += 16
            
        # Divider
        pygame.draw.line(surface, (45, 52, 70), (dx + 10, sy + 2), (dx + dw - 10, sy + 2), 1)
        sy += 6
        
        # Skill List header
        sk_title = self.font_subtitle.render("HABILIDADES DE COMBATE:", True, (200, 210, 230))
        surface.blit(sk_title, (dx + 12, sy))
        sy += 16
        
        # Display 5 core skills (J, K, E, Shift, R)
        core_keys = ["j", "k", "e", "shift", "r"]
        for k in core_keys:
            if k in self.profile.skills:
                sk = self.profile.skills[k]
                
                # Icon
                icon_surf = self.skill_icons.get(sk.icon_file, None)
                if icon_surf:
                    surface.blit(icon_surf, (dx + 12, sy - 1))
                    
                # Name and hotkey
                hk_name = f"[{k.upper()}] {sk.name}"
                hk_surf = self.font_key.render(hk_name, True, GOLD if k == "r" else (225, 235, 250))
                surface.blit(hk_surf, (dx + 38, sy))
                
                # Cost
                cost_str = f"{sk.cost_value} {sk.cost_type}"
                cost_surf = self.font_key.render(cost_str, True, (130, 145, 175))
                surface.blit(cost_surf, (dx + dw - cost_surf.get_width() - 10, sy))
                sy += 18

    def _draw_action_buttons(self, surface: pygame.Surface):
        """Draws carousel thumbnail slots and Play / Back buttons."""
        # Carousel Thumbnails (7 mini character cards)
        cy = 300
        cw, ch = 38, 44
        
        for idx, cid in enumerate(CHARACTER_ORDER):
            p = CHARACTER_REGISTRY[cid]
            cx = 36 + idx * 43
            thumb_rect = pygame.FRect(cx, cy, cw, ch)
            
            is_sel = (idx == self.selected_index)
            bg_col = (40, 48, 70) if is_sel else (20, 24, 34)
            border_col = p.color_theme if is_sel else (55, 65, 85)
            
            pygame.draw.rect(surface, bg_col, thumb_rect, border_radius=3)
            pygame.draw.rect(surface, border_col, thumb_rect, 2 if is_sel else 1, border_radius=3)
            
            # Portrait thumbnail
            t_img = self.thumbnails.get(cid, None)
            if t_img:
                surface.blit(t_img, (cx + (cw - t_img.get_width()) // 2, cy + 3))
            else:
                pygame.draw.circle(surface, p.color_theme, (cx + cw // 2, cy + 14), 4 if is_sel else 3)
            
            # Short Name label
            sn = p.name[:4].upper()
            sn_surf = self.font_key.render(sn, True, p.color_theme if is_sel else (150, 160, 180))
            surface.blit(sn_surf, (cx + (cw - sn_surf.get_width()) // 2, cy + 28))
            
        # Action Buttons
        # Back Button [ESC]
        is_back_hov = self.btn_back_rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surface, (30, 36, 52) if is_back_hov else (20, 24, 36), self.btn_back_rect, border_radius=4)
        pygame.draw.rect(surface, (120, 130, 160) if is_back_hov else (60, 70, 95), self.btn_back_rect, 1, border_radius=4)
        back_text = self.font_key.render("VOLTAR [ESC]", True, WHITE)
        surface.blit(back_text, (self.btn_back_rect.x + (self.btn_back_rect.width - back_text.get_width()) // 2, self.btn_back_rect.y + 10))
        
        # Play Button [ENTER]
        is_play_hov = self.btn_play_rect.collidepoint(pygame.mouse.get_pos())
        play_bg = (180, 140, 40) if is_play_hov else (140, 110, 30)
        pygame.draw.rect(surface, play_bg, self.btn_play_rect, border_radius=4)
        pygame.draw.rect(surface, GOLD, self.btn_play_rect, 1, border_radius=4)
        play_text = self.font_name.render("JOGAR [ENTER]", True, (10, 10, 15))
        surface.blit(play_text, (self.btn_play_rect.x + (self.btn_play_rect.width - play_text.get_width()) // 2, self.btn_play_rect.y + 6))
