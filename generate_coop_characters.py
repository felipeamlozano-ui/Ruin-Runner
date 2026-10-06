"""
Generates high-detail 128x128 pixel art sprite sheets for the 4 new Co-op characters:
- Aurelia (Sacerdotisa da Luz / Healer)
- Kaelen (Arqueiro do Vento / Archer)
- Zephyr (Mago Eólico & Suporte de Mana / Mana Support)
- Boran (Guardião Sísmico / Crowd Controller Tank)
Conforms strictly to the craftpix 128x128 spritesheet standard.
"""

import os
import math
import pygame
from pathlib import Path

def create_character_sprites():
    pygame.init()
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.display.set_mode((1, 1))

    base_dir = Path("assets") / "sprites" / "characters" / "coop"
    base_dir.mkdir(parents=True, exist_ok=True)

    characters = {
        "aurelia": {
            "name": "Aurelia",
            "body_color": (245, 235, 210),
            "hair_color": (255, 220, 110),
            "outfit_primary": (255, 255, 255),
            "outfit_accent": (240, 195, 60),
            "staff_color": (255, 215, 80),
            "glow_color": (255, 240, 160),
            "weapon_type": "staff"
        },
        "archer": {
            "name": "Kaelen",
            "body_color": (235, 205, 180),
            "hair_color": (90, 60, 40),
            "outfit_primary": (45, 95, 55),
            "outfit_accent": (140, 100, 50),
            "bow_color": (160, 110, 60),
            "glow_color": (140, 255, 160),
            "weapon_type": "bow"
        },
        "zephyr": {
            "name": "Zephyr",
            "body_color": (225, 215, 210),
            "hair_color": (120, 225, 245),
            "outfit_primary": (30, 65, 95),
            "outfit_accent": (80, 200, 230),
            "staff_color": (130, 190, 255),
            "glow_color": (100, 240, 255),
            "weapon_type": "ether_orb"
        },
        "boran": {
            "name": "Boran",
            "body_color": (210, 190, 175),
            "hair_color": (75, 75, 85),
            "outfit_primary": (70, 75, 85),
            "outfit_accent": (210, 140, 50),
            "hammer_color": (100, 105, 115),
            "glow_color": (255, 160, 50),
            "weapon_type": "hammer"
        }
    }

    FW, FH = 128, 128
    CENTER_X = 64
    BASE_Y = 100 # Ground baseline in 128x128 box

    for cid, cfg in characters.items():
        cdir = base_dir / cid
        cdir.mkdir(parents=True, exist_ok=True)
        print(f"Generating pixel art sprite sheets for {cfg['name']} in {cdir}...")

        # 1. IDLE (8 frames = 1024x128)
        idle_sheet = pygame.Surface((FW * 8, FH), pygame.SRCALPHA)
        for f in range(8):
            bob = int(math.sin(f * (math.pi / 4)) * 2)
            fx = f * FW
            _draw_humanoid(idle_sheet, fx + CENTER_X, BASE_Y + bob, cfg, action="idle", frame_idx=f)
        pygame.image.save(idle_sheet, str(cdir / "Idle.png"))

        # 2. WALK / RUN (8 frames = 1024x128)
        walk_sheet = pygame.Surface((FW * 8, FH), pygame.SRCALPHA)
        for f in range(8):
            bob = int(abs(math.sin(f * (math.pi / 2))) * 3)
            fx = f * FW
            _draw_humanoid(walk_sheet, fx + CENTER_X, BASE_Y - bob, cfg, action="walk", frame_idx=f)
        pygame.image.save(walk_sheet, str(cdir / "Walk.png"))

        # 3. ATTACK (8 frames = 1024x128)
        atk_sheet = pygame.Surface((FW * 8, FH), pygame.SRCALPHA)
        for f in range(8):
            fx = f * FW
            _draw_humanoid(atk_sheet, fx + CENTER_X, BASE_Y, cfg, action="attack", frame_idx=f)
        pygame.image.save(atk_sheet, str(cdir / "Attack.png"))

        # 4. PROTECTION / DEFEND (4 frames = 512x128)
        prot_sheet = pygame.Surface((FW * 4, FH), pygame.SRCALPHA)
        for f in range(4):
            fx = f * FW
            _draw_humanoid(prot_sheet, fx + CENTER_X, BASE_Y + 1, cfg, action="protect", frame_idx=f)
        pygame.image.save(prot_sheet, str(cdir / "Protection.png"))

        # 5. JUMP (4 frames = 512x128)
        jump_sheet = pygame.Surface((FW * 4, FH), pygame.SRCALPHA)
        for f in range(4):
            lift = int(f * 3)
            fx = f * FW
            _draw_humanoid(jump_sheet, fx + CENTER_X, BASE_Y - 4 - lift, cfg, action="jump", frame_idx=f)
        pygame.image.save(jump_sheet, str(cdir / "Jump.png"))

        # 6. DEAD (4 frames = 512x128)
        dead_sheet = pygame.Surface((FW * 4, FH), pygame.SRCALPHA)
        for f in range(4):
            fx = f * FW
            _draw_humanoid(dead_sheet, fx + CENTER_X, BASE_Y, cfg, action="dead", frame_idx=f)
        pygame.image.save(dead_sheet, str(cdir / "Dead.png"))

        # 7. HURT (3 frames = 384x128)
        hurt_sheet = pygame.Surface((FW * 3, FH), pygame.SRCALPHA)
        for f in range(3):
            fx = f * FW
            _draw_humanoid(hurt_sheet, fx + CENTER_X - 2, BASE_Y, cfg, action="hurt", frame_idx=f)
        pygame.image.save(hurt_sheet, str(cdir / "Hurt.png"))

        # 8. PORTRAIT (64x64)
        port_surf = pygame.Surface((64, 64), pygame.SRCALPHA)
        _draw_portrait(port_surf, cfg)
        pygame.image.save(port_surf, str(cdir / "portrait.png"))

    print("All Co-op character sprite assets generated successfully!")
    pygame.quit()


def _draw_humanoid(surface: pygame.Surface, cx: int, cy: int, cfg: dict, action: str, frame_idx: int):
    """Draws stylish, expressive 2D pixel art character frame."""
    body_col = cfg["body_color"]
    hair_col = cfg["hair_color"]
    prim_col = cfg["outfit_primary"]
    acc_col = cfg["outfit_accent"]
    glow_col = cfg["glow_color"]
    wtype = cfg["weapon_type"]

    # Shadow on ground
    if action != "dead":
        shadow_w = 26 if action != "jump" else 18
        shadow_surf = pygame.Surface((shadow_w, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (15, 20, 30, 110), (0, 0, shadow_w, 8))
        surface.blit(shadow_surf, (cx - shadow_w // 2, cy + 2))

    if action == "dead":
        # Fallen posture
        tilt_y = cy + 4
        pygame.draw.rect(surface, prim_col, (cx - 18, tilt_y - 8, 28, 12), border_radius=3)
        pygame.draw.circle(surface, body_col, (cx - 24, tilt_y - 4), 7)
        pygame.draw.circle(surface, hair_col, (cx - 25, tilt_y - 6), 7)
        return

    # Legs & Boots
    leg_offset = 0
    if action == "walk":
        leg_offset = int(math.sin(frame_idx * (math.pi / 2)) * 6)
    
    # Left Leg / Boot
    pygame.draw.rect(surface, acc_col, (cx - 7 + leg_offset, cy - 16, 5, 18), border_radius=2)
    # Right Leg / Boot
    pygame.draw.rect(surface, acc_col, (cx + 2 - leg_offset, cy - 16, 5, 18), border_radius=2)

    # Torso / Robe / Armor
    torso_y = cy - 36
    pygame.draw.rect(surface, prim_col, (cx - 9, torso_y, 18, 22), border_radius=3)
    pygame.draw.rect(surface, acc_col, (cx - 5, torso_y + 4, 10, 14), border_radius=2)

    # Belt & Buckle
    pygame.draw.rect(surface, (40, 45, 55), (cx - 9, torso_y + 18, 18, 3))
    pygame.draw.circle(surface, acc_col, (cx, torso_y + 19), 2)

    # Head & Face
    head_y = cy - 48
    pygame.draw.circle(surface, body_col, (cx, head_y), 9)
    # Expressive Anime Eyes
    eye_x = cx + 2
    pygame.draw.rect(surface, (20, 25, 35), (eye_x, head_y - 1, 3, 4))
    pygame.draw.rect(surface, (255, 255, 255), (eye_x, head_y - 1, 2, 2))

    # Hair / Helmet / Hood
    pygame.draw.circle(surface, hair_col, (cx - 2, head_y - 3), 10)
    pygame.draw.polygon(surface, hair_col, [(cx - 10, head_y - 2), (cx - 5, head_y + 6), (cx, head_y)])
    if wtype in ("staff", "ether_orb"):
        # Floating celestial circlet / halo
        halo_surf = pygame.Surface((22, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(halo_surf, (*glow_col, 180), (0, 0, 22, 6), width=1)
        surface.blit(halo_surf, (cx - 11, head_y - 14))

    # Arms & Weapon
    arm_x = cx + 7
    arm_y = torso_y + 6

    if action == "attack":
        # Forward thrust / swing animation
        thrust = int(math.sin(frame_idx * (math.pi / 4)) * 12)
        arm_x += thrust

    if wtype == "staff":
        # Sacred Light Staff
        pygame.draw.line(surface, cfg["staff_color"], (arm_x + 2, arm_y - 18), (arm_x + 6, arm_y + 22), 2)
        # Glowing Crystal head
        pygame.draw.circle(surface, glow_col, (arm_x + 2, arm_y - 18), 4)
        pygame.draw.circle(surface, (255, 255, 255), (arm_x + 2, arm_y - 18), 2)
    elif wtype == "bow":
        # Ranger Composite Bow
        bow_x = arm_x + 6
        pygame.draw.arc(surface, cfg["bow_color"], (bow_x - 6, arm_y - 14, 14, 28), -math.pi/2, math.pi/2, 2)
        pygame.draw.line(surface, (220, 230, 240), (bow_x, arm_y - 14), (bow_x, arm_y + 14), 1)
        if action == "attack":
            # Drawn arrow with glowing tip
            pygame.draw.line(surface, (255, 240, 100), (bow_x - 8, arm_y), (bow_x + 8, arm_y), 2)
            pygame.draw.circle(surface, glow_col, (bow_x + 9, arm_y), 2)
    elif wtype == "ether_orb":
        # Levitating arcane energy sphere
        orbit_a = frame_idx * (math.pi / 4)
        orb_x = arm_x + int(math.cos(orbit_a) * 8)
        orb_y = arm_y + int(math.sin(orbit_a) * 8)
        pygame.draw.circle(surface, glow_col, (orb_x, orb_y), 5)
        pygame.draw.circle(surface, (255, 255, 255), (orb_x, orb_y), 2)
    elif wtype == "hammer":
        # Colossal Stone War Hammer
        ham_x = arm_x + 4
        pygame.draw.line(surface, (140, 110, 70), (ham_x, arm_y - 20), (ham_x + 4, arm_y + 18), 3)
        # Basalt Hammer Head
        pygame.draw.rect(surface, cfg["hammer_color"], (ham_x - 8, arm_y - 26, 18, 12), border_radius=2)
        pygame.draw.rect(surface, glow_col, (ham_x - 4, arm_y - 23, 10, 6))

    # Defensive Guard Aura / Shield
    if action == "protect":
        shield_surf = pygame.Surface((44, 52), pygame.SRCALPHA)
        pygame.draw.ellipse(shield_surf, (*glow_col, 140), (0, 0, 44, 52), width=2)
        pygame.draw.ellipse(shield_surf, (255, 255, 255, 80), (4, 4, 36, 44))
        surface.blit(shield_surf, (cx - 22, torso_y - 10))


def _draw_portrait(surface: pygame.Surface, cfg: dict):
    """Draws sharp 64x64 character UI portrait."""
    surface.fill((16, 22, 32))
    # Border
    pygame.draw.rect(surface, cfg["outfit_accent"], (0, 0, 64, 64), width=2, border_radius=4)
    # Head & Hair
    pygame.draw.circle(surface, cfg["body_color"], (32, 32), 14)
    pygame.draw.circle(surface, cfg["hair_color"], (30, 26), 16)
    # Eye
    pygame.draw.rect(surface, (20, 25, 35), (35, 30, 4, 6))
    pygame.draw.rect(surface, (255, 255, 255), (35, 30, 2, 3))
    # Robe collar
    pygame.draw.polygon(surface, cfg["outfit_primary"], [(16, 64), (32, 46), (48, 64)])
    pygame.draw.polygon(surface, cfg["outfit_accent"], [(24, 64), (32, 50), (40, 64)])

if __name__ == "__main__":
    create_character_sprites()
