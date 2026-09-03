import pygame
import os
from pathlib import Path

def generate_placeholders():
    pygame.init()
    # Ensure it's working headlessly
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    screen = pygame.display.set_mode((1, 1))
    
    base = Path("assets")
    
    # 1. Player Sprite (Arani)
    player = pygame.Surface((32, 48), pygame.SRCALPHA)
    player.fill((50, 150, 200)) # Blueish hero
    pygame.draw.rect(player, (255, 200, 150), (8, 4, 16, 12)) # Face
    pygame.image.save(player, str(base / "sprites" / "arani_idle.png"))
    
    # 2. Enemy Sprite (e.g. Wolf/Goblin)
    enemy = pygame.Surface((32, 32), pygame.SRCALPHA)
    enemy.fill((200, 50, 50)) # Red enemy
    pygame.draw.rect(enemy, (0, 0, 0), (8, 8, 16, 8)) # Eyes
    pygame.image.save(enemy, str(base / "sprites" / "enemy_idle.png"))
    
    # 3. Boss (Stone Golem)
    boss = pygame.Surface((128, 128), pygame.SRCALPHA)
    boss.fill((100, 100, 100)) # Grey rock
    pygame.draw.circle(boss, (255, 0, 0), (64, 40), 10) # Glowing eye
    pygame.image.save(boss, str(base / "sprites" / "golem_idle.png"))
    
    # 4. Tileset base
    tileset = pygame.Surface((128, 128))
    tileset.fill((30, 100, 30)) # Grass green
    pygame.draw.rect(tileset, (139, 69, 19), (0, 0, 32, 32)) # Dirt
    pygame.image.save(tileset, str(base / "sprites" / "tileset.png"))
    
    # 5. Items
    health_potion = pygame.Surface((16, 16), pygame.SRCALPHA)
    pygame.draw.circle(health_potion, (255, 50, 50), (8, 8), 8)
    pygame.image.save(health_potion, str(base / "sprites" / "potion.png"))
    
    crystal = pygame.Surface((16, 16), pygame.SRCALPHA)
    pygame.draw.polygon(crystal, (50, 200, 255), [(8, 0), (16, 8), (8, 16), (0, 8)])
    pygame.image.save(crystal, str(base / "sprites" / "crystal.png"))
    
    print("Placeholder assets generated successfully.")
    pygame.quit()

if __name__ == "__main__":
    generate_placeholders()
