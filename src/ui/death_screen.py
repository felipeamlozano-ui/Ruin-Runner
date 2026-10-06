import pygame
import random
import math
from config.settings import SETTINGS
from engine.input_manager import INPUT

class EmberParticle:
    """Floating ember/blood ash particle drifting upwards."""
    def __init__(self, w: int, h: int):
        self.x = random.uniform(0, w)
        self.y = random.uniform(h * 0.4, h + 20)
        self.speed_y = random.uniform(-25.0, -60.0)
        self.speed_x = random.uniform(-15.0, 15.0)
        self.size = random.uniform(1.5, 3.5)
        self.color = random.choice([
            (255, 60, 50),
            (220, 30, 30),
            (255, 140, 40),
            (180, 20, 20)
        ])
        self.alpha = random.randint(140, 240)
        self.lifetime = random.uniform(1.5, 3.5)
        self.timer = 0.0

    def update(self, dt: float) -> bool:
        self.timer += dt
        self.x += self.speed_x * dt
        self.y += self.speed_y * dt
        return self.timer < self.lifetime

    def draw(self, surface: pygame.Surface):
        progress = self.timer / self.lifetime
        cur_alpha = max(0, int(self.alpha * (1.0 - progress)))
        p_surf = pygame.Surface((int(self.size * 2), int(self.size * 2)), pygame.SRCALPHA)
        pygame.draw.circle(p_surf, (*self.color, cur_alpha), (int(self.size), int(self.size)), int(self.size))
        surface.blit(p_surf, (self.x - self.size, self.y - self.size))

class DeathScreen:
    """Dramatic, dark fantasy Death Screen with blood mist vignette and glowing gothic text."""
    def __init__(self):
        self.alpha = 0.0
        self.target_alpha = 220.0
        self.fade_speed = 120.0 # Reaches max in ~1.8s
        self.active = False
        
        self.pulse_timer = 0.0
        self.particles: list[EmberParticle] = []
        
        from ui.hollow_ui import HollowFonts
        self.font_title = HollowFonts.get(26, bold=True)
        self.font_sub = HollowFonts.get(12, italic=True)
        self.font_btn = HollowFonts.get(12, bold=True)
        self.font_tip = HollowFonts.get(10)
        
    def reset(self):
        self.alpha = 0.0
        self.pulse_timer = 0.0
        self.particles.clear()
        self.active = False
        
    def start(self):
        self.active = True
        
    def update(self, dt: float) -> str:
        """Updates animation and returns 'retry', 'menu', or None."""
        if not self.active:
            return None
            
        # Smooth fade-in
        if self.alpha < self.target_alpha:
            self.alpha = min(self.target_alpha, self.alpha + self.fade_speed * dt)
            
        self.pulse_timer += dt
        
        # Spawn embers
        if len(self.particles) < 35 and random.random() < 0.45:
            self.particles.append(EmberParticle(SETTINGS.GAME_WIDTH, SETTINGS.GAME_HEIGHT))
            
        for p in self.particles[:]:
            if not p.update(dt):
                self.particles.remove(p)
                
        # Handle player action inputs after small initial delay
        if self.alpha >= 100:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_r] or INPUT.is_action_just_pressed("ACTION") or INPUT.is_action_just_pressed("JUMP"):
                return "retry"
            elif keys[pygame.K_ESCAPE] or INPUT.is_action_just_pressed("PAUSE"):
                return "menu"
                
        return None

    def draw(self, surface: pygame.Surface):
        if not self.active or self.alpha <= 0:
            return
            
        from ui.hollow_ui import HollowCrestRenderer, HollowColors
        
        gw, gh = SETTINGS.GAME_WIDTH, SETTINGS.GAME_HEIGHT
        cx, cy = gw // 2, gh // 2
        
        # 1. Dark Crimson & Charcoal Film Atmosphere (zero stepped circular banding)
        for y in range(gh):
            t = y / float(gh)
            edge = abs(t - 0.5) * 2.0 # 0.0 at center, 1.0 at edges
            r = int(14 + edge * 32)
            g = int(5 + edge * 3)
            b = int(7 + edge * 5)
            pygame.draw.line(surface, (r, g, b), (0, y), (gw, y))
            
        # Darkening vignette veil
        overlay = pygame.Surface((gw, gh), pygame.SRCALPHA)
        v_alpha = int(220 * (self.alpha / self.target_alpha))
        overlay.fill((4, 3, 6, 255 - v_alpha))
        surface.blit(overlay, (0, 0))
        
        # 2. Draw Floating Ember Particles
        for p in self.particles:
            p.draw(surface)
            
        # 3. Top Flourish above Title
        HollowCrestRenderer.draw_top_flourish(surface, cx, cy - 85, width=150, alpha=int(self.alpha))
        
        # 4. Hollow Title: "VOCÊ FOI DERROTADO"
        title_text = "VOCÊ FOI DERROTADO"
        
        # Shadow
        shadow_surf = self.font_title.render(title_text, True, (0, 0, 0))
        surface.blit(shadow_surf, (cx - shadow_surf.get_width() // 2 + 1, cy - 65 + 1))
        
        # Core
        title_surf = self.font_title.render(title_text, True, (245, 235, 240))
        surface.blit(title_surf, (cx - title_surf.get_width() // 2, cy - 65))
        
        # Subtitle
        sub_text = "A escuridão das ruínas consumiu o seu último suspiro..."
        sub_surf = self.font_sub.render(sub_text, True, HollowColors.TEXT_NORMAL)
        surface.blit(sub_surf, (cx - sub_surf.get_width() // 2, cy - 25))
        
        # Section Divider
        HollowCrestRenderer.draw_section_divider(surface, cx, cy - 8, width=320, alpha=int(min(220, self.alpha)))
        
        # 5. Interactive Action Buttons
        if self.alpha >= 120:
            btn_y = cy + 18
            mx, my = pygame.mouse.get_pos()
            
            # [R] Reiniciar Button Frame
            r_box = pygame.Rect(cx - 150, btn_y, 140, 32)
            r_hov = r_box.collidepoint(mx, my)
            HollowCrestRenderer.draw_hollow_button(
                surface,
                r_box,
                "REINICIAR [R]",
                self.font_btn,
                is_hovered=r_hov,
                text_color=HollowColors.GOLD_CREST if r_hov else HollowColors.TEXT_TITLE
            )
            
            # [ESC] Menu Principal Button Frame
            m_box = pygame.Rect(cx + 10, btn_y, 140, 32)
            m_hov = m_box.collidepoint(mx, my)
            HollowCrestRenderer.draw_hollow_button(
                surface,
                m_box,
                "MENU [ESC]",
                self.font_btn,
                is_hovered=m_hov,
                text_color=HollowColors.GOLD_CREST if m_hov else HollowColors.TEXT_NORMAL
            )
            
            # Footer tip
            tip_surf = self.font_tip.render("Pressione [R] para desafiar novamente ou [ESC] para o menu principal", True, HollowColors.TEXT_MUTED)
            surface.blit(tip_surf, tip_surf.get_rect(center=(cx, gh - 22)))
