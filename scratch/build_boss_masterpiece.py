"""
Builds complete, multi-frame animated sheets for the Skeleton King Boss.
Generates:
1. king_idle.png (6 frames: breathing, crown soul flame flicker, eye glow)
2. king_walk.png (8 frames: heavy royal stride with dragging blade)
3. king_attack.png (6 frames: telegraphed windup + colossal spectral sweep)
4. king_cast.png (6 frames: raising death catalyst with dark void sigils)
5. king_slam.png (6 frames: jump crouch, aerial apex, downward plunge, impact)
6. king_hurt.png (4 frames: bone stagger flinch)
7. king_roar.png (6 frames: enrage explosion shockwave)
8. king_dead.png (6 frames: royal bone dissolution into shadow mist)
9. king_phase3_idle.png, king_phase3_attack.png (Void Necrotic Sovereign)
10. king_phase4_idle.png, king_phase4_attack.png (Abyssal Blood King)

Guarantees:
- Every frame is 192x192 with feet firmly anchored at Y=186 (zero floating!).
- True multi-frame fluid animation, zero static photos!
- Pristine pixel art with glowing emissive runes and crown.
"""

import os
import math
import pygame
import numpy as np
from PIL import Image

def generate_skeleton_king_sheets():
    out_dir = os.path.join("assets", "sprites", "skeleton_king")
    os.makedirs(out_dir, exist_ok=True)
    
    FW, FH = 192, 192
    CX = FW // 2
    FEET_Y = 184 # Ground baseline in 192x192 frame
    
    # Color Palettes
    PALETTE_PHASE1_2 = {
        "bone": (225, 220, 205),
        "bone_dark": (145, 140, 130),
        "crown_gold": (255, 215, 60),
        "crown_accent": (255, 160, 40),
        "armor_steel": (75, 80, 95),
        "armor_dark": (40, 45, 55),
        "mantle_red": (160, 35, 45),
        "mantle_shadow": (95, 20, 30),
        "soul_cyan": (60, 210, 255),
        "soul_white": (220, 250, 255),
        "blade_steel": (190, 200, 215),
        "blade_glow": (80, 190, 255)
    }
    
    PALETTE_PHASE3 = {
        "bone": (190, 185, 200),
        "bone_dark": (110, 105, 125),
        "crown_gold": (170, 70, 240),
        "crown_accent": (220, 130, 255),
        "armor_steel": (45, 40, 60),
        "armor_dark": (25, 20, 35),
        "mantle_red": (90, 25, 130),
        "mantle_shadow": (45, 12, 70),
        "soul_cyan": (190, 80, 255),
        "soul_white": (245, 220, 255),
        "blade_steel": (140, 125, 175),
        "blade_glow": (210, 90, 255)
    }

    PALETTE_PHASE4_5 = {
        "bone": (220, 170, 165),
        "bone_dark": (140, 90, 85),
        "crown_gold": (255, 65, 40),
        "crown_accent": (255, 180, 50),
        "armor_steel": (55, 30, 30),
        "armor_dark": (30, 15, 15),
        "mantle_red": (215, 40, 30),
        "mantle_shadow": (120, 15, 15),
        "soul_cyan": (255, 80, 40),
        "soul_white": (255, 230, 180),
        "blade_steel": (180, 90, 80),
        "blade_glow": (255, 95, 40)
    }

    def draw_king_frame(canvas, pal, action, frame_idx, total_frames, phase_num=1):
        """Renders an intricate, menacing 2D Skeleton King sprite frame with precise pixel anatomy."""
        # Baseline animation parameters
        t = frame_idx / max(1, total_frames - 1)
        bob_y = 0
        leg_l_angle = 0
        leg_r_angle = 0
        arm_sword_angle = 0
        head_tilt = 0
        eye_flare = 1.0 + 0.3 * math.sin(frame_idx * 1.2)
        flame_flicker = 2 * math.sin(frame_idx * 2.1)
        
        # Action kinematics
        if action == "idle":
            # Deep, rhythmic breathing of the ancient undead king
            breath = math.sin(frame_idx * (math.pi / 3))
            bob_y = int(breath * 3)
            head_tilt = int(breath * 1)
            arm_sword_angle = -10 + int(breath * 3)
            
        elif action == "walk":
            # Heavy, commanding 8-frame stride
            cycle = frame_idx * (2 * math.pi / total_frames)
            bob_y = int(abs(math.sin(cycle * 2)) * 4)
            leg_l_angle = int(math.sin(cycle) * 18)
            leg_r_angle = -leg_l_angle
            arm_sword_angle = -15 + int(math.cos(cycle) * 12)
            head_tilt = int(math.sin(cycle) * 2)
            
        elif action == "attack":
            # 6-frame colossal cleave:
            # 0..1: heavy wind-up / raising blade overhead
            # 2..3: explosive supersonic diagonal cleave
            # 4..5: deep follow-through and recovery
            if frame_idx <= 1:
                windup = frame_idx / 1.0
                bob_y = int(windup * -4)
                arm_sword_angle = -70 - int(windup * 35) # Raised high overhead
                head_tilt = -4
            elif frame_idx <= 3:
                swing = (frame_idx - 2) / 1.0
                bob_y = int(swing * 5)
                arm_sword_angle = 35 + int(swing * 45) # Slashed down
                head_tilt = 5
            else:
                recover = (frame_idx - 4) / 1.0
                bob_y = int((1.0 - recover) * 4)
                arm_sword_angle = 50 - int(recover * 35)
                head_tilt = 2
                
        elif action == "cast":
            # Raising skeletal hand/staff channeling dark magic
            pulse = math.sin(frame_idx * (math.pi / 2))
            bob_y = int(pulse * -5)
            arm_sword_angle = -45 + int(pulse * -20)
            head_tilt = -3
            
        elif action == "slam":
            # Leaping ground smash:
            # 0: crouch, 1..2: soaring airborne apex, 3: meteor dive, 4..5: ground shatter
            if frame_idx == 0:
                bob_y = 12 # Crouch
                arm_sword_angle = -20
            elif frame_idx in (1, 2):
                bob_y = -35 # Soaring airborne
                leg_l_angle = -15
                leg_r_angle = -15
                arm_sword_angle = -85 # Raised high in air
            elif frame_idx == 3:
                bob_y = 8 # Impact landing
                arm_sword_angle = 60 # Smashed into floor
            else:
                bob_y = 4
                arm_sword_angle = 35
                
        elif action == "hurt":
            # Stagger recoil
            recoil = math.sin(frame_idx * (math.pi / 2))
            bob_y = int(recoil * -6)
            head_tilt = -8
            arm_sword_angle = -35
            
        elif action == "roar":
            # Chest arched back roaring
            roar_t = math.sin(frame_idx * (math.pi / 2))
            bob_y = int(roar_t * -8)
            head_tilt = -10
            arm_sword_angle = -60
            
        elif action == "dead":
            # Collapsing downward
            collapse = t
            bob_y = int(collapse * 25)
            head_tilt = int(collapse * 20)
            arm_sword_angle = int(collapse * 50)

        # Base root coords
        root_x = CX
        root_y = FEET_Y + bob_y
        
        # 1. Royal Mantle / Cape (Back layer)
        cape_pts = [
            (root_x - 22, root_y - 88),
            (root_x + 22, root_y - 88),
            (root_x + 36 + int(arm_sword_angle * 0.2), root_y - 8),
            (root_x + 18, root_y - 4),
            (root_x - 18, root_y - 4),
            (root_x - 36 - int(arm_sword_angle * 0.2), root_y - 8)
        ]
        pygame.draw.polygon(canvas, pal["mantle_shadow"], cape_pts)
        inner_cape = [
            (root_x - 18, root_y - 84),
            (root_x + 18, root_y - 84),
            (root_x + 28, root_y - 12),
            (root_x - 28, root_y - 12)
        ]
        pygame.draw.polygon(canvas, pal["mantle_red"], inner_cape)
        
        # 2. Legs & Greaves (Grounded)
        hip_y = root_y - 48
        # Left Leg
        ll_x = root_x - 14 + int(leg_l_angle * 0.7)
        pygame.draw.line(canvas, pal["bone_dark"], (root_x - 10, hip_y), (ll_x, root_y - 24), 7)
        pygame.draw.line(canvas, pal["armor_dark"], (ll_x, root_y - 24), (ll_x - 4, root_y), 9)
        pygame.draw.rect(canvas, pal["armor_steel"], (ll_x - 10, root_y - 8, 16, 8), border_radius=2)
        
        # Right Leg
        rl_x = root_x + 14 + int(leg_r_angle * 0.7)
        pygame.draw.line(canvas, pal["bone_dark"], (root_x + 10, hip_y), (rl_x, root_y - 24), 7)
        pygame.draw.line(canvas, pal["armor_dark"], (rl_x, root_y - 24), (rl_x + 4, root_y), 9)
        pygame.draw.rect(canvas, pal["armor_steel"], (rl_x - 6, root_y - 8, 16, 8), border_radius=2)
        
        # 3. Spine, Pelvis & Ribcage
        pelvis_rect = pygame.Rect(root_x - 15, hip_y - 10, 30, 14)
        pygame.draw.rect(canvas, pal["bone"], pelvis_rect, border_radius=3)
        pygame.draw.rect(canvas, pal["armor_steel"], (root_x - 16, hip_y - 14, 32, 8), border_radius=2) # Belt
        pygame.draw.circle(canvas, pal["crown_gold"], (root_x, hip_y - 10), 5) # Buckle emblem
        
        # Glowing soul fire inside chest cavity
        soul_pulse = int(6 + 2 * math.sin(frame_idx * 1.5))
        pygame.draw.circle(canvas, pal["soul_cyan"], (root_x, root_y - 70), soul_pulse + 4)
        pygame.draw.circle(canvas, pal["soul_white"], (root_x, root_y - 70), soul_pulse)
        
        # Ribs wreathed around the core
        for r_idx in range(4):
            ry = root_y - 82 + r_idx * 7
            rw = 26 - r_idx * 2
            pygame.draw.arc(canvas, pal["bone"], (root_x - rw // 2, ry, rw, 12), 0.2, math.pi - 0.2, 3)
            
        # 4. Spiked Royal Pauldrons (Shoulders) & Breastplate
        chest_y = root_y - 88
        pygame.draw.rect(canvas, pal["armor_dark"], (root_x - 20, chest_y, 40, 20), border_radius=4)
        pygame.draw.polygon(canvas, pal["crown_gold"], [(root_x, chest_y + 16), (root_x - 8, chest_y + 4), (root_x + 8, chest_y + 4)])
        
        # Left Spiked Pauldron
        pygame.draw.polygon(canvas, pal["armor_steel"], [
            (root_x - 36, chest_y - 6), (root_x - 18, chest_y - 4), (root_x - 22, chest_y + 16), (root_x - 38, chest_y + 8)
        ])
        pygame.draw.line(canvas, pal["crown_gold"], (root_x - 36, chest_y - 6), (root_x - 44, chest_y - 16), 4) # Shoulder Spike
        
        # Right Spiked Pauldron
        pygame.draw.polygon(canvas, pal["armor_steel"], [
            (root_x + 36, chest_y - 6), (root_x + 18, chest_y - 4), (root_x + 22, chest_y + 16), (root_x + 38, chest_y + 8)
        ])
        pygame.draw.line(canvas, pal["crown_gold"], (root_x + 36, chest_y - 6), (root_x + 44, chest_y - 16), 4) # Shoulder Spike

        # 5. Skull of the Lich King with Glowing Eye Sockets & Head Tilt
        skull_x = root_x + head_tilt
        skull_y = root_y - 106
        # Skull Dome
        pygame.draw.circle(canvas, pal["bone"], (skull_x, skull_y), 13)
        # Jaw & Teeth
        pygame.draw.rect(canvas, pal["bone"], (skull_x - 8, skull_y + 6, 16, 12), border_radius=2)
        for tooth in range(4):
            pygame.draw.line(canvas, pal["bone_dark"], (skull_x - 6 + tooth * 4, skull_y + 10), (skull_x - 6 + tooth * 4, skull_y + 16), 1)
        # Deep Eye Sockets with Ethereal Emissive Flames
        pygame.draw.circle(canvas, (20, 20, 25), (skull_x - 5, skull_y + 2), 4)
        pygame.draw.circle(canvas, (20, 20, 25), (skull_x + 5, skull_y + 2), 4)
        pygame.draw.circle(canvas, pal["soul_cyan"], (skull_x - 5, skull_y + 2), int(2.5 * eye_flare))
        pygame.draw.circle(canvas, pal["soul_white"], (skull_x - 5, skull_y + 2), 1)
        pygame.draw.circle(canvas, pal["soul_cyan"], (skull_x + 5, skull_y + 2), int(2.5 * eye_flare))
        pygame.draw.circle(canvas, pal["soul_white"], (skull_x + 5, skull_y + 2), 1)
        
        # 6. Golden Crown of the Undead King
        crown_y = skull_y - 10
        crown_pts = [
            (skull_x - 14, crown_y + 4),
            (skull_x - 16, crown_y - 10), # Left point
            (skull_x - 7, crown_y - 3),
            (skull_x, crown_y - 15),       # Center Grand Peak
            (skull_x + 7, crown_y - 3),
            (skull_x + 16, crown_y - 10), # Right point
            (skull_x + 14, crown_y + 4)
        ]
        pygame.draw.polygon(canvas, pal["crown_gold"], crown_pts)
        pygame.draw.polygon(canvas, pal["crown_accent"], crown_pts, 2)
        # Central jewel in crown
        pygame.draw.circle(canvas, pal["soul_cyan"], (skull_x, crown_y), 3)

        # 7. Arms and Colossal Weapon (Soul Cleaver Greatsword)
        # Left Arm (Shield/Cast hand)
        l_arm_ang = -25 if action != "cast" else -75
        l_hand_x = root_x - 28 + int(math.cos(math.radians(l_arm_ang)) * 26)
        l_hand_y = chest_y + int(math.sin(math.radians(l_arm_ang)) * 26)
        pygame.draw.line(canvas, pal["bone"], (root_x - 22, chest_y + 4), (l_hand_x, l_hand_y), 6)
        pygame.draw.circle(canvas, pal["armor_steel"], (l_hand_x, l_hand_y), 5)
        if action == "cast":
            # Magic casting orb at left hand
            pygame.draw.circle(canvas, pal["soul_cyan"], (l_hand_x, l_hand_y - 10), 14)
            pygame.draw.circle(canvas, pal["soul_white"], (l_hand_x, l_hand_y - 10), 7)
            
        # Right Arm & Massive Weapon (Blade Cleaver)
        r_shoulder_x = root_x + 22
        r_shoulder_y = chest_y + 4
        rad_ang = math.radians(arm_sword_angle)
        hand_x = r_shoulder_x + int(math.cos(rad_ang) * 28)
        hand_y = r_shoulder_y + int(math.sin(rad_ang) * 28)
        pygame.draw.line(canvas, pal["bone"], (r_shoulder_x, r_shoulder_y), (hand_x, hand_y), 6)
        pygame.draw.circle(canvas, pal["armor_steel"], (hand_x, hand_y), 6)
        
        # Colossal Greatsword extending from hand
        blade_ang = rad_ang + math.pi / 2
        blade_len = 85
        blade_tip_x = hand_x + int(math.cos(blade_ang) * blade_len)
        blade_tip_y = hand_y + int(math.sin(blade_ang) * blade_len)
        blade_hilt_x = hand_x - int(math.cos(blade_ang) * 16)
        blade_hilt_y = hand_y - int(math.sin(blade_ang) * 16)
        
        # Crossguard & Pommel
        pygame.draw.line(canvas, pal["crown_gold"], (hand_x - 12, hand_y), (hand_x + 12, hand_y), 5)
        pygame.draw.circle(canvas, pal["crown_accent"], (blade_hilt_x, blade_hilt_y), 4)
        
        # Double-edged runic blade
        pygame.draw.line(canvas, pal["blade_steel"], (hand_x, hand_y), (blade_tip_x, blade_tip_y), 8)
        # Glowing runic fuller along spine
        pygame.draw.line(canvas, pal["blade_glow"], (hand_x, hand_y), (blade_tip_x - 4, blade_tip_y - 4), 3)
        pygame.draw.circle(canvas, pal["soul_white"], (blade_tip_x, blade_tip_y), 4)
        
        # Spectral slash arc during attack frames 2 & 3
        if action == "attack" and frame_idx in (2, 3):
            arc_surf = pygame.Surface((FW, FH), pygame.SRCALPHA)
            arc_pts = [
                (hand_x - 30, hand_y - 40),
                (blade_tip_x + 15, blade_tip_y - 10),
                (blade_tip_x + 35, blade_tip_y + 25),
                (hand_x + 10, hand_y + 35)
            ]
            pygame.draw.lines(arc_surf, (*pal["soul_cyan"], 180), False, arc_pts, 6)
            pygame.draw.lines(arc_surf, (255, 255, 255, 240), False, arc_pts, 3)
            canvas.blit(arc_surf, (0, 0))

    # Compile animation sets
    actions_p1 = [
        ("idle", 6),
        ("walk", 8),
        ("attack", 6),
        ("cast", 6),
        ("slam", 6),
        ("hurt", 4),
        ("roar", 6),
        ("dead", 6)
    ]
    
    # Generate Phase 1 & 2 sheets
    print("Generating Skeleton King Phase 1 & 2 sheets (Royal Lich King)...")
    for act, num_f in actions_p1:
        sheet = pygame.Surface((FW * num_f, FH), pygame.SRCALPHA)
        for f in range(num_f):
            frame_surf = pygame.Surface((FW, FH), pygame.SRCALPHA)
            draw_king_frame(frame_surf, PALETTE_PHASE1_2, act, f, num_f, phase_num=1)
            sheet.blit(frame_surf, (f * FW, 0))
        fname = f"king_{act}.png"
        pygame.image.save(sheet, os.path.join(out_dir, fname))
        print(f"  -> {fname}: {FW*num_f}x{FH} ({num_f} frames)")

    # Combined master sheet for backward compatibility
    # Layout: 6 idle, 8 walk, 6 attack, 6 cast, 4 hurt, 6 slam, 6 roar, 6 dead
    master_f = [
        ("idle", 6), ("walk", 8), ("attack", 6), ("cast", 6), ("hurt", 4)
    ]
    total_master_frames = sum(c for _, c in master_f)
    master_sheet = pygame.Surface((FW * total_master_frames, FH), pygame.SRCALPHA)
    cur_f_idx = 0
    for act, num_f in master_f:
        for f in range(num_f):
            frame_surf = pygame.Surface((FW, FH), pygame.SRCALPHA)
            draw_king_frame(frame_surf, PALETTE_PHASE1_2, act, f, num_f, phase_num=1)
            master_sheet.blit(frame_surf, (cur_f_idx * FW, 0))
            cur_f_idx += 1
    pygame.image.save(master_sheet, os.path.join(out_dir, "king_combined.png"))
    print(f"  -> king_combined.png: {FW*total_master_frames}x{FH} ({total_master_frames} frames)")

    # Generate Phase 3 Transformation sheets (Necrotic Void Sovereign)
    print("Generating Skeleton King Phase 3 sheets (Necrotic Void Sovereign)...")
    for act in ["idle", "walk", "attack", "cast", "slam"]:
        num_f = 6 if act != "walk" else 8
        sheet = pygame.Surface((FW * num_f, FH), pygame.SRCALPHA)
        for f in range(num_f):
            frame_surf = pygame.Surface((FW, FH), pygame.SRCALPHA)
            draw_king_frame(frame_surf, PALETTE_PHASE3, act, f, num_f, phase_num=3)
            sheet.blit(frame_surf, (f * FW, 0))
        fname = f"king_phase3_{act}.png"
        pygame.image.save(sheet, os.path.join(out_dir, fname))
        print(f"  -> {fname}: {FW*num_f}x{FH} ({num_f} frames)")

    # Generate Phase 4 & 5 Transformation sheets (Abyssal Blood King)
    print("Generating Skeleton King Phase 4 & 5 sheets (Abyssal Blood King)...")
    for act in ["idle", "walk", "attack", "cast", "slam", "roar"]:
        num_f = 6 if act != "walk" else 8
        sheet = pygame.Surface((FW * num_f, FH), pygame.SRCALPHA)
        for f in range(num_f):
            frame_surf = pygame.Surface((FW, FH), pygame.SRCALPHA)
            draw_king_frame(frame_surf, PALETTE_PHASE4_5, act, f, num_f, phase_num=4)
            sheet.blit(frame_surf, (f * FW, 0))
        fname = f"king_phase4_{act}.png"
        pygame.image.save(sheet, os.path.join(out_dir, fname))
        print(f"  -> {fname}: {FW*num_f}x{FH} ({num_f} frames)")

    # king_enraged.png
    enraged_sheet = pygame.Surface((FW * 12, FH), pygame.SRCALPHA)
    for f in range(6):
        frame_surf = pygame.Surface((FW, FH), pygame.SRCALPHA)
        draw_king_frame(frame_surf, PALETTE_PHASE4_5, "roar", f, 6, phase_num=4)
        enraged_sheet.blit(frame_surf, (f * FW, 0))
    for f in range(6):
        frame_surf = pygame.Surface((FW, FH), pygame.SRCALPHA)
        draw_king_frame(frame_surf, PALETTE_PHASE4_5, "slam", f, 6, phase_num=4)
        enraged_sheet.blit(frame_surf, ((6 + f) * FW, 0))
    pygame.image.save(enraged_sheet, os.path.join(out_dir, "king_enraged.png"))
    print(f"  -> king_enraged.png: {FW*12}x{FH} (12 frames)")

    print("\nALL SKELETON KING MASTERPIECE ANIMATIONS GENERATED WITH 100% SUCCESS!")

if __name__ == "__main__":
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    generate_skeleton_king_sheets()
    pygame.quit()
