import pygame

class SpikeTrap:
    def __init__(self, x: float, y: float, width: int = 16, height: int = 16):
        self.rect = pygame.FRect(x, y, width, height)
        self.damage = 5 # Highly punishing floor hazard
        self.damage_cooldown = 0.0
        
    def update(self, player, dt: float = 0.016):
        if self.damage_cooldown > 0:
            self.damage_cooldown -= dt
        if self.damage_cooldown <= 0 and self.rect.colliderect(player.rect):
            player.take_damage(self.damage)
            self.damage_cooldown = 0.5
            
    def draw(self, surface: pygame.Surface, camera_offset: pygame.math.Vector2):
        draw_x = int(self.rect.x - camera_offset.x)
        draw_y = int(self.rect.y - camera_offset.y)
        w, h = int(self.rect.width), int(self.rect.height)
        
        # 1. Base contact shadow embedded into the stone floor
        shadow_surf = pygame.Surface((w + 6, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 110), (0, 0, w + 6, 8))
        surface.blit(shadow_surf, (draw_x - 3, draw_y + h - 4))
        
        # 2. Dark iron base plate embedded in pavement
        base_h = max(4, h // 3)
        pygame.draw.rect(surface, (36, 40, 48), (draw_x, draw_y + h - base_h, w, base_h), border_radius=1)
        pygame.draw.rect(surface, (68, 74, 88), (draw_x, draw_y + h - base_h, w, base_h), 1, border_radius=1)
        
        # Iron corner rivets
        if w >= 12:
            pygame.draw.circle(surface, (140, 150, 168), (draw_x + 2, draw_y + h - base_h + 2), 1)
            pygame.draw.circle(surface, (140, 150, 168), (draw_x + w - 3, draw_y + h - base_h + 2), 1)
            
        # 3. Razor-sharp steel spikes protruding from floor slits
        spike_count = max(2, w // 7)
        spacing = w / (spike_count + 1)
        for i in range(1, spike_count + 1):
            sx = int(draw_x + i * spacing)
            top_y = draw_y + 1
            bot_y = draw_y + h - base_h + 1
            # Left illuminated facet of spike blade
            pygame.draw.polygon(surface, (185, 195, 210), [(sx, top_y), (sx - 3, bot_y), (sx, bot_y)])
            # Right shaded facet of spike blade
            pygame.draw.polygon(surface, (95, 105, 120), [(sx, top_y), (sx, bot_y), (sx + 3, bot_y)])
            # Razor tip glint
            pygame.draw.line(surface, (245, 250, 255), (sx, top_y), (sx, top_y + 3), 1)
