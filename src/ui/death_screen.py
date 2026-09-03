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
        
        pygame.font.init()
        self.font_skull = pygame.font.SysFont("Georgia", 32, bold=True)
        self.font_title = pygame.font.SysFont("Georgia", 28, bold=True)
        self.font_sub = pygame.font.SysFont("Arial", 13, italic=True)
        self.font_btn = pygame.font.SysFont("Arial", 14, bold=True)
        self.font_tip = pygame.font.SysFont("Arial", 11)
        
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
            
        gw, gh = SETTINGS.GAME_WIDTH, SETTINGS.GAME_HEIGHT
        cx, cy = gw // 2, gh // 2
        
        # 1. Dark Crimson & Charcoal Vignette Overlay
        overlay = pygame.Surface((gw, gh), pygame.SRCALPHA)
        cur_alpha = int(self.alpha)
        # Deep dark base
        overlay.fill((8, 4, 6, cur_alpha))
        
        # Crimson blood aura pulse from screen center
        pulse = 0.85 + 0.15 * math.sin(self.pulse_timer * 2.5)
        aura_radius = int(gh * 0.7 * pulse)
        aura_surf = pygame.Surface((aura_radius * 2, aura_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(aura_surf, (90, 10, 15, int(70 * (self.alpha / self.target_alpha))), (aura_radius, aura_radius), aura_radius)
        overlay.blit(aura_surf, (cx - aura_radius, cy - aura_radius), special_flags=pygame.BLEND_RGBA_ADD)
        
        # Border vignette shadows
        pygame.draw.rect(overlay, (0, 0, 0, min(255, int(cur_alpha * 1.1))), (0, 0, gw, 30))
        pygame.draw.rect(overlay, (0, 0, 0, min(255, int(cur_alpha * 1.1))), (0, gh - 30, gw, 30))
        
        surface.blit(overlay, (0, 0))
        
        # 2. Draw Floating Ember Particles
        for p in self.particles:
            p.draw(surface)
            
        # 3. Gothic Title: "VOCÊ FOI DERROTADO"
        glow_alpha = int(220 + 35 * math.sin(self.pulse_timer * 3.0))
        title_text = "VOCÊ FOI DERROTADO"
        
        # Outer glow shadow
        shadow_surf = self.font_title.render(title_text, True, (60, 5, 10))
        surface.blit(shadow_surf, (cx - shadow_surf.get_width() // 2 + 2, cy - 60 + 2))
        
        # Main Title (Radiant blood red with gold core)
        title_surf = self.font_title.render(title_text, True, (245, 55, 55))
        surface.blit(title_surf, (cx - title_surf.get_width() // 2, cy - 60))
        
        # Top ornament skulls
        ornament = "— ☠ —"
        orn_surf = self.font_skull.render(ornament, True, (215, 170, 70))
        surface.blit(orn_surf, (cx - orn_surf.get_width() // 2, cy - 95))
        
        # Subtitle
        sub_text = "A escuridão das ruínas consumiu o seu último suspiro..."
        sub_surf = self.font_sub.render(sub_text, True, (200, 190, 195))
        surface.blit(sub_surf, (cx - sub_surf.get_width() // 2, cy - 25))
        
        # Divider Line
        line_w = 260
        pygame.draw.line(surface, (140, 40, 45), (cx - line_w // 2, cy - 8), (cx + line_w // 2, cy - 8), 1)
        pygame.draw.line(surface, (215, 170, 70), (cx - 40, cy - 8), (cx + 40, cy - 8), 2)
        
        # 4. Interactive Action Buttons
        if self.alpha >= 120:
            btn_y = cy + 18
            
            # [R] Tentar Novamente Button Frame
            r_box = pygame.FRect(cx - 150, btn_y, 140, 32)
            bg_box1 = pygame.Surface((int(r_box.width), int(r_box.height)), pygame.SRCALPHA)
            bg_box1.fill((40, 12, 16, 210))
            surface.blit(bg_box1, (r_box.x, r_box.y))
            pygame.draw.rect(surface, (215, 60, 60), r_box, 1, border_radius=4)
            
            r_text = self.font_btn.render("[R] Reiniciar", True, (255, 220, 220))
            surface.blit(r_text, r_text.get_rect(center=r_box.center))
            
            # [ESC] Menu Principal Button Frame
            m_box = pygame.FRect(cx + 10, btn_y, 140, 32)
            bg_box2 = pygame.Surface((int(m_box.width), int(m_box.height)), pygame.SRCALPHA)
            bg_box2.fill((20, 22, 30, 210))
            surface.blit(bg_box2, (m_box.x, m_box.y))
            pygame.draw.rect(surface, (100, 110, 140), m_box, 1, border_radius=4)
            
            m_text = self.font_btn.render("[ESC] Menu", True, (210, 215, 230))
            surface.blit(m_text, m_text.get_rect(center=m_box.center))
            
            # Footer tip
            tip_surf = self.font_tip.render("Pressione [R] para tentar novamente ou [ESC] para sair", True, (160, 150, 160))
            surface.blit(tip_surf, tip_surf.get_rect(center=(cx, gh - 20)))
