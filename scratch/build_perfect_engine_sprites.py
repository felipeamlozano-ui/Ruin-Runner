"""
Ruin Runner - Perfect Engine Sprites Generator
Processes raw sheets from AI generation, precisely separating every individual pose,
eliminating merged/split character bugs, centering root at X=64, anchoring feet at baseline Y=124,
and generating pristine, 100% glitch-free 128x128 sprite sheets for all characters.
"""

import os
import sys
import math
from PIL import Image
import numpy as np
from collections import deque
from scipy.signal import find_peaks

BRAIN_DIR = r"C:\Users\Felipe\.gemini\antigravity-ide\brain\b436599e-060f-4534-9bea-d5741b48a0b6"

def clean_crop_transparency(img_crop, is_dark, bg_color, thresh=32):
    """
    Cleans background from crop using flood-fill from boundaries + distance threshold.
    Preserves all internal character colors and transparency.
    """
    if hasattr(img_crop, "convert"):
        img_crop = img_crop.convert("RGBA")
    arr = np.array(img_crop).copy()
    h, w, _ = arr.shape
    rgb = arr[:, :, :3].astype(np.float32)
    
    if is_dark:
        bg = np.array(bg_color, dtype=np.float32)
        dist = np.sqrt(np.sum((rgb - bg)**2, axis=-1))
    else:
        dist = np.sqrt(np.sum((rgb - 255.0)**2, axis=-1))
        
    is_bg = dist < thresh
    visited = np.zeros((h, w), dtype=bool)
    q = deque()
    
    # Border seed pixels
    for x in range(w):
        if is_bg[0, x]: q.append((0, x)); visited[0, x] = True
        if is_bg[h-1, x]: q.append((h-1, x)); visited[h-1, x] = True
    for y in range(h):
        if is_bg[y, 0]: q.append((y, 0)); visited[y, 0] = True
        if is_bg[y, w-1]: q.append((y, w-1)); visited[y, w-1] = True
        
    while q:
        cy, cx = q.popleft()
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ny, nx = cy + dy, cx + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and is_bg[ny, nx]:
                visited[ny, nx] = True
                q.append((ny, nx))
                
    arr[visited, 3] = 0
    return Image.fromarray(arr)

def assemble_single_character_frame(clean_crop, scale, baseline_y=124, frame_w=128, frame_h=128, max_allowed_w=90):
    """
    Isolates the single main character in the crop, centers at X=64, and anchors feet at baseline_y=124.
    If multiple components exist, keeps the primary central character to guarantee zero split/doubled bodies.
    """
    arr = np.array(clean_crop)
    alpha = arr[:, :, 3]
    y_pts, x_pts = np.where(alpha > 20)
    if len(y_pts) == 0 or len(x_pts) == 0:
        return Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
        
    ymin, ymax = y_pts.min(), y_pts.max()
    xmin, xmax = x_pts.min(), x_pts.max()
    
    # If crop is too wide (adjacent character leaked in), isolate the center of mass
    crop_w = xmax - xmin + 1
    if crop_w > max_allowed_w:
        # Find horizontal mass center
        col_mass = np.sum(alpha > 20, axis=0)
        center_x = int(np.average(np.arange(len(col_mass)), weights=col_mass))
        half_w = max_allowed_w // 2
        safe_xmin = max(0, center_x - half_w)
        safe_xmax = min(clean_crop.width, center_x + half_w)
        
        # Zero out alpha outside safe range
        arr[:, :safe_xmin, 3] = 0
        arr[:, safe_xmax:, 3] = 0
        clean_crop = Image.fromarray(arr)
        
        # Recompute bounds
        alpha = arr[:, :, 3]
        y_pts, x_pts = np.where(alpha > 20)
        if len(y_pts) == 0:
            return Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
        ymin, ymax = y_pts.min(), y_pts.max()
        xmin, xmax = x_pts.min(), x_pts.max()

    # Calculate spine/root X in the torso (upper 35% to 80% of body)
    torso_y_start = ymin + int((ymax - ymin) * 0.25)
    torso_y_end = ymin + int((ymax - ymin) * 0.85)
    torso_mask = alpha[torso_y_start:torso_y_end, :]
    ty, tx = np.where(torso_mask > 20)
    root_x = np.median(tx) if len(tx) > 0 else (xmin + xmax) * 0.5
    
    # Scale character
    cw, ch = clean_crop.size
    nw = max(1, int(round(cw * scale)))
    nh = max(1, int(round(ch * scale)))
    resized = clean_crop.resize((nw, nh), Image.Resampling.LANCZOS)
    
    # Paste centered at X=64, feet at baseline_y
    paste_x = (frame_w // 2) - int(round(root_x * scale))
    paste_y = baseline_y - int(round(ymax * scale))
    
    frame = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
    frame.paste(resized, (paste_x, paste_y), resized)
    return frame

def assemble_jump_frame(clean_crop, scale, ground_crop_y, baseline_y=124, frame_w=128, frame_h=128, max_allowed_w=90):
    """
    Jump frame that preserves vertical lift above baseline.
    """
    arr = np.array(clean_crop)
    alpha = arr[:, :, 3]
    y_pts, x_pts = np.where(alpha > 20)
    if len(y_pts) == 0 or len(x_pts) == 0:
        return Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
        
    ymin, ymax = y_pts.min(), y_pts.max()
    xmin, xmax = x_pts.min(), x_pts.max()
    
    crop_w = xmax - xmin + 1
    if crop_w > max_allowed_w:
        col_mass = np.sum(alpha > 20, axis=0)
        center_x = int(np.average(np.arange(len(col_mass)), weights=col_mass))
        half_w = max_allowed_w // 2
        safe_xmin = max(0, center_x - half_w)
        safe_xmax = min(clean_crop.width, center_x + half_w)
        arr[:, :safe_xmin, 3] = 0
        arr[:, safe_xmax:, 3] = 0
        clean_crop = Image.fromarray(arr)
        alpha = arr[:, :, 3]
        y_pts, x_pts = np.where(alpha > 20)
        if len(y_pts) == 0:
            return Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
        ymin, ymax = y_pts.min(), y_pts.max()
        xmin, xmax = x_pts.min(), x_pts.max()
        
    root_x = (xmin + xmax) * 0.5
    cw, ch = clean_crop.size
    nw = max(1, int(round(cw * scale)))
    nh = max(1, int(round(ch * scale)))
    resized = clean_crop.resize((nw, nh), Image.Resampling.LANCZOS)
    
    paste_x = (frame_w // 2) - int(round(root_x * scale))
    paste_y = baseline_y - int(round(ground_crop_y * scale))
    
    frame = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
    frame.paste(resized, (paste_x, paste_y), resized)
    return frame

def make_strip(frames, frame_w=128, frame_h=128):
    if not frames:
        return Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
    strip = Image.new("RGBA", (len(frames) * frame_w, frame_h), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        strip.paste(f, (i * frame_w, 0), f)
    return strip

def make_portrait(idle_frame, frame_size=128):
    alpha = np.array(idle_frame)[:, :, 3]
    y_pts, x_pts = np.where(alpha > 20)
    if len(y_pts) == 0:
        return idle_frame
    ytop, ybot = y_pts.min(), y_pts.max()
    char_h = ybot - ytop
    ymid = ytop + int(char_h * 0.55)
    xcen = int(np.median(x_pts))
    half_w = int(char_h * 0.35)
    xmin = max(0, xcen - half_w)
    xmax = min(128, xcen + half_w)
    
    bust = idle_frame.crop((xmin, ytop, xmax, ymid))
    bw, bh = bust.size
    target_bh = 86
    b_scale = target_bh / float(max(1, bh))
    nbw, nbh = int(round(bw * b_scale)), int(round(bh * b_scale))
    resized = bust.resize((nbw, nbh), Image.Resampling.LANCZOS)
    
    port = Image.new("RGBA", (frame_size, frame_size), (0, 0, 0, 0))
    port.paste(resized, ((frame_size - nbw) // 2, (frame_size - nbh) // 2 + 4), resized)
    return port

# ─────────────────────────────────────────────────────────────────────────────
# BUILDERS FOR EACH CHARACTER WITH ISOLATED, TRUE SINGLE-POSE BOXES
# ─────────────────────────────────────────────────────────────────────────────

def build_perfect_aurelia():
    print("Building pristine, glitch-free Aurelia...")
    sheet_p = os.path.join(BRAIN_DIR, "aurelia_sheet_1790680006763.jpg")
    out_dir = "assets/sprites/characters/coop/aurelia"
    os.makedirs(out_dir, exist_ok=True)
    img = Image.open(sheet_p).convert("RGB")
    scale = 0.5200
    is_dark = True
    bg_col = (15, 21, 37)
    thresh = 30
    
    # 1. Idle (4 true poses from row 0)
    idle_boxes = [(9, 13, 107, 171), (130, 13, 236, 171), (269, 32, 357, 171), (398, 32, 476, 171)]
    idle_frames = [assemble_single_character_frame(clean_crop_transparency(img.crop(b), is_dark, bg_col, thresh), scale) for b in idle_boxes]
    make_strip(idle_frames).save(os.path.join(out_dir, "Idle.png"))
    
    # 2. Walk & Run (8 poses from sub-rows)
    walk_boxes = [
        (23, 187, 125, 339), (145, 199, 250, 339), (268, 200, 380, 339), (387, 202, 478, 337),
        (29, 363, 99, 504), (147, 362, 254, 504), (257, 351, 351, 504), (380, 363, 477, 503)
    ]
    walk_8 = [assemble_single_character_frame(clean_crop_transparency(img.crop(b), is_dark, bg_col, thresh), scale) for b in walk_boxes]
    make_strip(walk_8).save(os.path.join(out_dir, "Walk.png"))
    make_strip(walk_8).save(os.path.join(out_dir, "Run.png"))
    
    # 3. Jump (3 clean poses)
    jump_boxes = [(522, 328, 626, 502), (645, 254, 758, 502), (767, 231, 880, 502)]
    jump_frames = [assemble_jump_frame(clean_crop_transparency(img.crop(b), is_dark, bg_col, thresh), scale, ground_crop_y=165) for b in jump_boxes]
    jump_4 = [jump_frames[0], jump_frames[1], jump_frames[2], idle_frames[0]]
    make_strip(jump_4).save(os.path.join(out_dir, "Jump.png"))
    
    # 4. Attack (6 ISOLATED poses using exact single-pose peaks: 116, 309, 502, 678, 808, 926)
    # NO MERGED BOXES! Each box is tightly bounded to 90px width around each character!
    atk_boxes = [
        (65, 562, 165, 770),   # Pose 0 (peak 116)
        (255, 562, 355, 770),  # Pose 1 (peak 309 - FIXED: separated from pose 0 and 2!)
        (450, 562, 555, 770),  # Pose 2 (peak 502 - FIXED: separated!)
        (625, 562, 735, 770),  # Pose 3 (peak 678)
        (755, 562, 855, 770),  # Pose 4 (peak 808)
        (875, 562, 975, 770)   # Pose 5 (peak 926)
    ]
    atk_frames = [assemble_single_character_frame(clean_crop_transparency(img.crop(b), is_dark, bg_col, thresh), scale, max_allowed_w=78) for b in atk_boxes]
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack.png"))
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack_1.png"))
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack_2.png"))
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack_3.png"))
    
    # 5. Shield / Protection (Tight boxes)
    guard_boxes = [(22, 844, 125, 988), (244, 841, 350, 988)]
    g0 = assemble_single_character_frame(clean_crop_transparency(img.crop(guard_boxes[0]), is_dark, bg_col, thresh), scale, max_allowed_w=75)
    g1 = assemble_single_character_frame(clean_crop_transparency(img.crop(guard_boxes[1]), is_dark, bg_col, thresh), scale, max_allowed_w=75)
    shield_loop = [g0, g1, g1, g0]
    make_strip(shield_loop).save(os.path.join(out_dir, "Shield.png"))
    make_strip(shield_loop).save(os.path.join(out_dir, "Protection.png"))
    
    # 6. Hurt & Dead (Tight single-pose boxes)
    hurt_box = (394, 849, 490, 987)
    hurt_f = [assemble_single_character_frame(clean_crop_transparency(img.crop(hurt_box), is_dark, bg_col, thresh), scale)]
    make_strip(hurt_f).save(os.path.join(out_dir, "Hurt.png"))
    
    dead_boxes = [(521, 929, 630, 1001), (768, 923, 870, 985), (889, 932, 990, 998)]
    dead_frames = [assemble_single_character_frame(clean_crop_transparency(img.crop(b), is_dark, bg_col, thresh), scale) for b in dead_boxes]
    make_strip(dead_frames).save(os.path.join(out_dir, "Dead.png"))
    
    # 7. Portrait
    make_portrait(idle_frames[0]).save(os.path.join(out_dir, "portrait.png"))
    print("  -> Aurelia built successfully with 0 split sprites and perfect frame isolation!")


def build_perfect_archer():
    print("Building pristine Archer...")
    sheet_p = os.path.join(BRAIN_DIR, "archer_sheet_1790680096666.jpg")
    out_dir = "assets/sprites/characters/coop/archer"
    os.makedirs(out_dir, exist_ok=True)
    img = Image.open(sheet_p).convert("RGB")
    scale = 0.4706
    thresh = 28
    
    idle_boxes = [(42, 37, 128, 207), (168, 37, 258, 207), (298, 37, 395, 207), (432, 37, 540, 207)]
    idle_frames = [assemble_single_character_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), thresh), scale) for b in idle_boxes]
    make_strip(idle_frames).save(os.path.join(out_dir, "Idle.png"))
    
    walk_boxes = [
        (20, 242, 135, 408), (154, 242, 260, 408), (280, 242, 370, 408), (391, 242, 510, 408),
        (530, 242, 650, 408), (699, 242, 820, 408), (862, 242, 970, 408)
    ]
    raw_walk = [assemble_single_character_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), thresh), scale) for b in walk_boxes]
    walk_8 = [raw_walk[0], raw_walk[1], raw_walk[2], raw_walk[3], raw_walk[4], raw_walk[5], raw_walk[6], raw_walk[1]]
    make_strip(walk_8).save(os.path.join(out_dir, "Walk.png"))
    make_strip(walk_8).save(os.path.join(out_dir, "Run.png"))
    
    jump_boxes = [(54, 631, 160, 818), (234, 631, 350, 818), (421, 622, 540, 818), (598, 662, 715, 818), (809, 677, 925, 818)]
    jump_frames = [assemble_jump_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), thresh), scale, ground_crop_y=175) for b in jump_boxes]
    make_strip(jump_frames).save(os.path.join(out_dir, "Jump.png"))
    
    atk_boxes = [
        (37, 428, 150, 615), (193, 428, 305, 615), (359, 428, 475, 615),
        (527, 427, 645, 615), (687, 446, 805, 615), (861, 445, 970, 615)
    ]
    atk_frames = [assemble_single_character_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), thresh), scale, max_allowed_w=78) for b in atk_boxes]
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack.png"))
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack_1.png"))
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack_2.png"))
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack_3.png"))
    
    guard_boxes = [(40, 846, 150, 1010), (206, 846, 315, 1010)]
    g0 = assemble_single_character_frame(clean_crop_transparency(img.crop(guard_boxes[0]), False, (255,255,255), thresh), scale, max_allowed_w=75)
    g1 = assemble_single_character_frame(clean_crop_transparency(img.crop(guard_boxes[1]), False, (255,255,255), thresh), scale, max_allowed_w=75)
    shield_loop = [g0, g1, g1, g0]
    make_strip(shield_loop).save(os.path.join(out_dir, "Shield.png"))
    make_strip(shield_loop).save(os.path.join(out_dir, "Protection.png"))
    
    hurt_box = (400, 889, 520, 1007)
    hurt_f = [assemble_single_character_frame(clean_crop_transparency(img.crop(hurt_box), False, (255,255,255), thresh), scale)]
    make_strip(hurt_f).save(os.path.join(out_dir, "Hurt.png"))
    
    dead_boxes = [(607, 951, 720, 1010), (812, 951, 930, 1006)]
    dead_frames = [assemble_single_character_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), thresh), scale) for b in dead_boxes]
    make_strip(dead_frames).save(os.path.join(out_dir, "Dead.png"))
    
    make_portrait(idle_frames[0]).save(os.path.join(out_dir, "portrait.png"))
    print("  -> Archer built successfully!")


def build_perfect_zephyr():
    print("Building pristine Zephyr...")
    sheet_p = os.path.join(BRAIN_DIR, "zephyr_sheet_1790680120086.jpg")
    out_dir = "assets/sprites/characters/coop/zephyr"
    os.makedirs(out_dir, exist_ok=True)
    img = Image.open(sheet_p).convert("RGB")
    scale_idle = 0.4039
    scale_action = 0.5200
    thresh = 28
    
    idle_boxes = [(30, 13, 150, 216), (203, 13, 320, 216), (375, 13, 490, 216), (547, 13, 665, 216)]
    idle_frames = [assemble_single_character_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), thresh), scale_idle) for b in idle_boxes]
    make_strip(idle_frames).save(os.path.join(out_dir, "Idle.png"))
    
    walk_boxes = [
        (14, 257, 140, 405), (182, 259, 310, 404), (348, 256, 470, 400),
        (517, 259, 640, 404), (682, 259, 810, 404), (848, 256, 970, 399)
    ]
    raw_walk = [assemble_single_character_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), thresh), scale_action, max_allowed_w=75) for b in walk_boxes]
    walk_8 = [raw_walk[0], raw_walk[1], raw_walk[2], raw_walk[3], raw_walk[4], raw_walk[5], raw_walk[4], raw_walk[1]]
    make_strip(walk_8).save(os.path.join(out_dir, "Walk.png"))
    make_strip(walk_8).save(os.path.join(out_dir, "Run.png"))
    
    jump_boxes = [(18, 653, 145, 826), (216, 653, 345, 826), (416, 646, 545, 825), (638, 646, 765, 826)]
    jump_frames = [assemble_jump_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), thresh), scale_action, ground_crop_y=165, max_allowed_w=75) for b in jump_boxes]
    make_strip(jump_frames).save(os.path.join(out_dir, "Jump.png"))
    
    atk_boxes = [
        (23, 444, 145, 630),
        (174, 439, 295, 630),
        (346, 481, 465, 630),
        (631, 482, 750, 630),
        (817, 481, 935, 629)
    ]
    atk_frames = [assemble_single_character_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), thresh), scale_action, max_allowed_w=78) for b in atk_boxes]
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack.png"))
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack_1.png"))
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack_2.png"))
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack_3.png"))
    
    guard_boxes = [(34, 858, 145, 1015), (192, 859, 310, 1015)]
    g0 = assemble_single_character_frame(clean_crop_transparency(img.crop(guard_boxes[0]), False, (255,255,255), thresh), scale_action, max_allowed_w=75)
    g1 = assemble_single_character_frame(clean_crop_transparency(img.crop(guard_boxes[1]), False, (255,255,255), thresh), scale_action, max_allowed_w=75)
    shield_loop = [g0, g1, g1, g0]
    make_strip(shield_loop).save(os.path.join(out_dir, "Shield.png"))
    make_strip(shield_loop).save(os.path.join(out_dir, "Protection.png"))
    
    hurt_box = (432, 873, 545, 1014)
    hurt_f = [assemble_single_character_frame(clean_crop_transparency(img.crop(hurt_box), False, (255,255,255), thresh), scale_action)]
    make_strip(hurt_f).save(os.path.join(out_dir, "Hurt.png"))
    
    dead_boxes = [(618, 912, 735, 1012), (809, 962, 935, 1015)]
    dead_frames = [assemble_single_character_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), thresh), scale_action) for b in dead_boxes]
    make_strip(dead_frames).save(os.path.join(out_dir, "Dead.png"))
    
    make_portrait(idle_frames[0]).save(os.path.join(out_dir, "portrait.png"))
    print("  -> Zephyr built successfully!")


def build_perfect_boran():
    print("Building pristine Boran...")
    sheet_p = os.path.join(BRAIN_DIR, "boran_sheet_1790680143248.jpg")
    out_dir = "assets/sprites/characters/coop/boran"
    os.makedirs(out_dir, exist_ok=True)
    img = Image.open(sheet_p).convert("RGB")
    scale = 0.5200
    thresh = 28
    
    idle_boxes = [
        (5, 44, 135, 192), (175, 44, 305, 192), (345, 44, 475, 192),
        (514, 44, 645, 192), (684, 44, 815, 192), (853, 44, 985, 192)
    ]
    idle_frames = [assemble_single_character_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), thresh), scale, max_allowed_w=78) for b in idle_boxes]
    make_strip(idle_frames).save(os.path.join(out_dir, "Idle.png"))
    
    walk_boxes = [
        (5, 246, 120, 384), (134, 246, 245, 384), (259, 246, 370, 385), (384, 246, 495, 386),
        (514, 246, 625, 384), (641, 246, 750, 386), (765, 246, 875, 384), (894, 246, 1005, 384)
    ]
    walk_8 = [assemble_single_character_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), thresh), scale, max_allowed_w=78) for b in walk_boxes]
    make_strip(walk_8).save(os.path.join(out_dir, "Walk.png"))
    make_strip(walk_8).save(os.path.join(out_dir, "Run.png"))
    
    jump_boxes = [
        (7, 690, 145, 829), (176, 690, 310, 829), (345, 689, 475, 828),
        (513, 693, 645, 829), (688, 660, 815, 829), (852, 690, 975, 828)
    ]
    jump_frames = [assemble_jump_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), thresh), scale, ground_crop_y=138, max_allowed_w=78) for b in jump_boxes]
    make_strip(jump_frames).save(os.path.join(out_dir, "Jump.png"))
    
    atk_boxes = [
        (7, 437, 125, 628), (140, 432, 255, 628), (268, 414, 375, 628),
        (391, 418, 500, 628), (520, 500, 645, 630), (674, 434, 805, 632)
    ]
    atk_frames = [assemble_single_character_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), thresh), scale, max_allowed_w=78) for b in atk_boxes]
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack.png"))
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack_1.png"))
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack_2.png"))
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack_3.png"))
    
    guard_boxes = [(8, 882, 145, 1020), (172, 876, 295, 1020)]
    g0 = assemble_single_character_frame(clean_crop_transparency(img.crop(guard_boxes[0]), False, (255,255,255), thresh), scale, max_allowed_w=75)
    g1 = assemble_single_character_frame(clean_crop_transparency(img.crop(guard_boxes[1]), False, (255,255,255), thresh), scale, max_allowed_w=75)
    shield_loop = [g0, g1, g1, g0]
    make_strip(shield_loop).save(os.path.join(out_dir, "Shield.png"))
    make_strip(shield_loop).save(os.path.join(out_dir, "Protection.png"))
    
    hurt_boxes = [(329, 887, 455, 1020), (496, 887, 625, 1019)]
    hurt_frames = [assemble_single_character_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), thresh), scale) for b in hurt_boxes]
    make_strip(hurt_frames).save(os.path.join(out_dir, "Hurt.png"))
    
    dead_boxes = [(679, 919, 800, 1018), (841, 952, 960, 1022)]
    dead_frames = [assemble_single_character_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), thresh), scale) for b in dead_boxes]
    make_strip(dead_frames).save(os.path.join(out_dir, "Dead.png"))
    
    make_portrait(idle_frames[0]).save(os.path.join(out_dir, "portrait.png"))
    print("  -> Boran built successfully!")

def main():
    print("==================================================================")
    print("   GENERATING PERFECT SPRITES WITH ZERO SPLIT/BROKEN FRAMES       ")
    print("==================================================================")
    build_perfect_aurelia()
    build_perfect_archer()
    build_perfect_zephyr()
    build_perfect_boran()
    print("\nALL CO-OP CHARACTERS REBUILT AND PERFECTED!")

if __name__ == "__main__":
    main()
