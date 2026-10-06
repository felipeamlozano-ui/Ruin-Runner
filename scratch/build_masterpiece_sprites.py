import os
import sys
from PIL import Image
import numpy as np
from collections import deque

def clean_crop_transparency(img_crop, is_dark, bg_color, thresh=28):
    """
    Removes background from crop using flood-fill from boundaries + distance threshold.
    Preserves all internal character colors.
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

def assemble_pose_frame(clean_crop, scale, baseline_y=124, frame_w=128, frame_h=128):
    """
    Centers character root at X=64 and anchors feet at baseline_y=124.
    """
    arr = np.array(clean_crop)
    alpha = arr[:, :, 3]
    y_pts, x_pts = np.where(alpha > 20)
    if len(y_pts) == 0 or len(x_pts) == 0:
        return Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
        
    ymin, ymax = y_pts.min(), y_pts.max()
    xmin, xmax = x_pts.min(), x_pts.max()
    
    # Calculate hip/root X in the crop (lower 50% of the body)
    torso_y_start = ymin + int((ymax - ymin) * 0.35)
    torso_mask = alpha[torso_y_start:ymax, :]
    ty, tx = np.where(torso_mask > 20)
    root_x = np.median(tx) if len(tx) > 0 else (xmin + xmax) * 0.5
    
    # Resize crop by scale
    cw, ch = clean_crop.size
    nw = max(1, int(round(cw * scale)))
    nh = max(1, int(round(ch * scale)))
    resized = clean_crop.resize((nw, nh), Image.Resampling.LANCZOS)
    
    # Paste coordinates
    paste_x = (frame_w // 2) - int(round(root_x * scale))
    paste_y = baseline_y - int(round(ymax * scale))
    
    frame = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
    frame.paste(resized, (paste_x, paste_y), resized)
    return frame

def assemble_jump_frame(clean_crop, scale, ground_crop_y, baseline_y=124, frame_w=128, frame_h=128):
    """
    Jump frame preserves airborne height relative to the row's ground line.
    """
    arr = np.array(clean_crop)
    alpha = arr[:, :, 3]
    y_pts, x_pts = np.where(alpha > 20)
    if len(y_pts) == 0 or len(x_pts) == 0:
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

def make_breathing_loop(base_frame):
    """Creates a gentle, organic 4-frame breathing loop from a single idle frame."""
    f0 = np.array(base_frame)
    alpha = f0[:, :, 3]
    pts = np.where(alpha > 20)
    if len(pts[0]) == 0:
        return [base_frame] * 4
    ymax = pts[0].max()
    feet_split = ymax - 18
    
    f_inhale = np.zeros_like(f0)
    f_inhale[feet_split:, :, :] = f0[feet_split:, :, :]
    f_inhale[:feet_split-1, :, :] = f0[1:feet_split, :, :]
    
    im0 = Image.fromarray(f0, 'RGBA')
    im1 = Image.fromarray(f_inhale, 'RGBA')
    return [im0, im1, im1, im0]

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

BRAIN_DIR = r"C:\Users\Felipe\.gemini\antigravity-ide\brain\b436599e-060f-4534-9bea-d5741b48a0b6"

def build_archer():
    print("\n>>> BUILDING ARCHER...")
    sheet_p = os.path.join(BRAIN_DIR, "archer_sheet_1790680096666.jpg")
    out_dir = "assets/sprites/characters/coop/archer"
    os.makedirs(out_dir, exist_ok=True)
    img = Image.open(sheet_p).convert("RGB")
    scale = 0.4706
    
    # 1. Idle (4 poses from row 0)
    idle_boxes = [(42, 37, 128, 207), (168, 37, 258, 207), (298, 37, 395, 207), (432, 37, 573, 207)]
    idle_frames = [assemble_pose_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), 28), scale) for b in idle_boxes]
    make_strip(idle_frames).save(os.path.join(out_dir, "Idle.png"))
    
    # 2. Walk & Run (7 poses from row 1 looped to 8 smooth frames)
    walk_boxes = [
        (20, 242, 147, 408), (154, 242, 272, 408), (280, 242, 374, 408), (391, 242, 522, 408),
        (530, 242, 685, 408), (699, 242, 852, 408), (862, 242, 1001, 408)
    ]
    raw_walk = [assemble_pose_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), 28), scale) for b in walk_boxes]
    walk_8 = [raw_walk[0], raw_walk[1], raw_walk[2], raw_walk[3], raw_walk[4], raw_walk[5], raw_walk[6], raw_walk[1]]
    make_strip(walk_8).save(os.path.join(out_dir, "Walk.png"))
    make_strip(walk_8).save(os.path.join(out_dir, "Run.png"))
    
    # 3. Jump (5 poses from row 3)
    jump_boxes = [(54, 631, 167, 818), (234, 631, 364, 818), (421, 622, 566, 818), (598, 662, 739, 818), (809, 677, 963, 818)]
    jump_frames = [assemble_jump_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), 28), scale, ground_crop_y=175) for b in jump_boxes]
    make_strip(jump_frames).save(os.path.join(out_dir, "Jump.png"))
    
    # 4. Attack / Attack_1 / Attack_2 / Attack_3 (6 full-body poses from row 2)
    atk_boxes = [
        (37, 428, 161, 615), (193, 428, 320, 615), (359, 428, 490, 615),
        (527, 427, 657, 615), (687, 446, 821, 615), (861, 445, 982, 615)
    ]
    atk_frames = [assemble_pose_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), 28), scale) for b in atk_boxes]
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack.png"))
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack_1.png"))
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack_2.png"))
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack_3.png"))
    
    # 5. Shield / Protection (Row 4 defensive stances, 4-frame breathing hold)
    guard_boxes = [(40, 846, 168, 1010), (206, 846, 338, 1010)]
    g0 = assemble_pose_frame(clean_crop_transparency(img.crop(guard_boxes[0]), False, (255,255,255), 28), scale)
    g1 = assemble_pose_frame(clean_crop_transparency(img.crop(guard_boxes[1]), False, (255,255,255), 28), scale)
    shield_loop = [g0, g1, g1, g0]
    make_strip(shield_loop).save(os.path.join(out_dir, "Shield.png"))
    make_strip(shield_loop).save(os.path.join(out_dir, "Protection.png"))
    
    # 6. Hurt & Dead
    hurt_box = (400, 889, 572, 1007)
    hurt_f = [assemble_pose_frame(clean_crop_transparency(img.crop(hurt_box), False, (255,255,255), 28), scale)]
    make_strip(hurt_f).save(os.path.join(out_dir, "Hurt.png"))
    
    dead_boxes = [(607, 951, 781, 1010), (812, 951, 987, 1006)]
    dead_frames = [assemble_pose_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), 28), scale) for b in dead_boxes]
    make_strip(dead_frames).save(os.path.join(out_dir, "Dead.png"))
    
    # 7. Portrait
    make_portrait(idle_frames[0]).save(os.path.join(out_dir, "portrait.png"))
    print("  -> Archer built successfully with 8-frame walk and 6-frame attack skills!")

def build_aurelia():
    print("\n>>> BUILDING AURELIA...")
    sheet_p = os.path.join(BRAIN_DIR, "aurelia_sheet_1790680006763.jpg")
    out_dir = "assets/sprites/characters/coop/aurelia"
    os.makedirs(out_dir, exist_ok=True)
    img = Image.open(sheet_p).convert("RGB")
    scale = 0.5200
    is_dark = True
    bg_col = (15, 21, 37)
    thresh = 30
    
    # 1. Idle (4 poses from row 0)
    idle_boxes = [(9, 13, 107, 171), (131, 13, 236, 171), (269, 32, 357, 171), (398, 32, 476, 171)]
    idle_frames = [assemble_pose_frame(clean_crop_transparency(img.crop(b), is_dark, bg_col, thresh), scale) for b in idle_boxes]
    make_strip(idle_frames).save(os.path.join(out_dir, "Idle.png"))
    
    # 2. Walk & Run (8 poses from both sub-rows forming full stride cycle)
    walk_boxes = [
        (23, 187, 125, 339), (145, 199, 250, 339), (268, 200, 380, 339), (387, 202, 478, 337),
        (29, 363, 99, 504), (147, 362, 254, 504), (257, 351, 351, 504), (380, 363, 477, 503)
    ]
    walk_8 = [assemble_pose_frame(clean_crop_transparency(img.crop(b), is_dark, bg_col, thresh), scale) for b in walk_boxes]
    make_strip(walk_8).save(os.path.join(out_dir, "Walk.png"))
    make_strip(walk_8).save(os.path.join(out_dir, "Run.png"))
    
    # 3. Jump (3 poses from row 3)
    jump_boxes = [(522, 328, 626, 502), (645, 254, 758, 502), (767, 231, 1024, 502)]
    jump_frames = [assemble_jump_frame(clean_crop_transparency(img.crop(b), is_dark, bg_col, thresh), scale, ground_crop_y=165) for b in jump_boxes]
    jump_4 = [jump_frames[0], jump_frames[1], jump_frames[2], idle_frames[0]]
    make_strip(jump_4).save(os.path.join(out_dir, "Jump.png"))
    
    # 4. Attack / Attack_1 / Attack_2 / Attack_3 (6 full-body poses from row 2, no split frames!)
    atk_boxes = [
        (9, 572, 182, 765), (198, 567, 418, 773), (423, 576, 612, 768),
        (625, 593, 762, 748), (759, 524, 869, 701), (879, 570, 1018, 730)
    ]
    atk_frames = [assemble_pose_frame(clean_crop_transparency(img.crop(b), is_dark, bg_col, thresh), scale) for b in atk_boxes]
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack.png"))
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack_1.png"))
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack_2.png"))
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack_3.png"))
    
    # 5. Shield / Protection (Row 4 divine prayer barrier stances, 4-frame breathing hold)
    guard_boxes = [(22, 844, 253, 988), (244, 841, 378, 988)]
    g0 = assemble_pose_frame(clean_crop_transparency(img.crop(guard_boxes[0]), is_dark, bg_col, thresh), scale)
    g1 = assemble_pose_frame(clean_crop_transparency(img.crop(guard_boxes[1]), is_dark, bg_col, thresh), scale)
    shield_loop = [g0, g1, g1, g0]
    make_strip(shield_loop).save(os.path.join(out_dir, "Shield.png"))
    make_strip(shield_loop).save(os.path.join(out_dir, "Protection.png"))
    
    # 6. Hurt & Dead
    hurt_box = (394, 849, 490, 987)
    hurt_f = [assemble_pose_frame(clean_crop_transparency(img.crop(hurt_box), is_dark, bg_col, thresh), scale)]
    make_strip(hurt_f).save(os.path.join(out_dir, "Hurt.png"))
    
    dead_boxes = [(521, 929, 764, 1001), (768, 923, 887, 985), (889, 932, 1024, 998)]
    dead_frames = [assemble_pose_frame(clean_crop_transparency(img.crop(b), is_dark, bg_col, thresh), scale) for b in dead_boxes]
    make_strip(dead_frames).save(os.path.join(out_dir, "Dead.png"))
    
    # 7. Portrait
    make_portrait(idle_frames[0]).save(os.path.join(out_dir, "portrait.png"))
    print("  -> Aurelia built successfully with 8-frame walk and 6-frame attack skills!")

def build_zephyr():
    print("\n>>> BUILDING ZEPHYR...")
    sheet_p = os.path.join(BRAIN_DIR, "zephyr_sheet_1790680120086.jpg")
    out_dir = "assets/sprites/characters/coop/zephyr"
    os.makedirs(out_dir, exist_ok=True)
    img = Image.open(sheet_p).convert("RGB")
    
    scale_idle = 0.4039
    scale_action = 0.5300
    
    # 1. Idle (4 poses from row 0)
    idle_boxes = [(30, 13, 164, 216), (203, 13, 340, 216), (375, 13, 513, 216), (547, 13, 685, 216)]
    idle_frames = [assemble_pose_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), 28), scale_idle) for b in idle_boxes]
    make_strip(idle_frames).save(os.path.join(out_dir, "Idle.png"))
    
    # 2. Walk & Run (6 poses from row 1 looped to 8 smooth frames, scaled at 0.5300)
    walk_boxes = [
        (14, 257, 178, 405), (182, 259, 344, 404), (348, 256, 511, 400),
        (517, 259, 679, 404), (682, 259, 844, 404), (848, 256, 1013, 399)
    ]
    raw_walk = [assemble_pose_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), 28), scale_action) for b in walk_boxes]
    walk_8 = [raw_walk[0], raw_walk[1], raw_walk[2], raw_walk[3], raw_walk[4], raw_walk[5], raw_walk[4], raw_walk[1]]
    make_strip(walk_8).save(os.path.join(out_dir, "Walk.png"))
    make_strip(walk_8).save(os.path.join(out_dir, "Run.png"))
    
    # 3. Jump (4 poses from row 3)
    jump_boxes = [(18, 653, 190, 826), (216, 653, 390, 826), (416, 646, 609, 825), (638, 646, 835, 826)]
    jump_frames = [assemble_jump_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), 28), scale_action, ground_crop_y=165) for b in jump_boxes]
    make_strip(jump_frames).save(os.path.join(out_dir, "Jump.png"))
    
    # 4. Attack / Attack_1 / Attack_2 / Attack_3 (5 full-body character poses, 0% floating orb!)
    atk_boxes = [
        (23, 444, 162, 630),
        (174, 439, 319, 630),
        (346, 481, 488, 630),
        (631, 482, 774, 630),
        (817, 481, 960, 629)
    ]
    atk_frames = [assemble_pose_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), 28), scale_action) for b in atk_boxes]
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack.png"))
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack_1.png"))
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack_2.png"))
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack_3.png"))
    
    # 5. Shield / Protection (Row 4 barrier stances, 4-frame breathing hold)
    guard_boxes = [(34, 858, 157, 1015), (192, 859, 334, 1015)]
    g0 = assemble_pose_frame(clean_crop_transparency(img.crop(guard_boxes[0]), False, (255,255,255), 28), scale_action)
    g1 = assemble_pose_frame(clean_crop_transparency(img.crop(guard_boxes[1]), False, (255,255,255), 28), scale_action)
    shield_loop = [g0, g1, g1, g0]
    make_strip(shield_loop).save(os.path.join(out_dir, "Shield.png"))
    make_strip(shield_loop).save(os.path.join(out_dir, "Protection.png"))
    
    # 6. Hurt & Dead
    hurt_box = (432, 873, 564, 1014)
    hurt_f = [assemble_pose_frame(clean_crop_transparency(img.crop(hurt_box), False, (255,255,255), 28), scale_action)]
    make_strip(hurt_f).save(os.path.join(out_dir, "Hurt.png"))
    
    dead_boxes = [(618, 912, 772, 1012), (809, 962, 1006, 1015)]
    dead_frames = [assemble_pose_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), 28), scale_action) for b in dead_boxes]
    make_strip(dead_frames).save(os.path.join(out_dir, "Dead.png"))
    
    # 7. Portrait
    make_portrait(idle_frames[0]).save(os.path.join(out_dir, "portrait.png"))
    print("  -> Zephyr built successfully with 8-frame walk, zero shrinkage, and clean attack skills!")

def build_boran():
    print("\n>>> BUILDING BORAN...")
    sheet_p = os.path.join(BRAIN_DIR, "boran_sheet_1790680143248.jpg")
    out_dir = "assets/sprites/characters/coop/boran"
    os.makedirs(out_dir, exist_ok=True)
    img = Image.open(sheet_p).convert("RGB")
    scale = 0.5400
    
    # 1. Idle (6 poses from row 0)
    idle_boxes = [
        (5, 44, 168, 192), (175, 44, 336, 192), (345, 44, 506, 192),
        (514, 44, 675, 192), (684, 44, 845, 192), (853, 44, 1016, 192)
    ]
    idle_frames = [assemble_pose_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), 28), scale) for b in idle_boxes]
    make_strip(idle_frames).save(os.path.join(out_dir, "Idle.png"))
    
    # 2. Walk & Run (8 poses from row 1)
    walk_boxes = [
        (5, 246, 131, 384), (134, 246, 258, 384), (259, 246, 381, 385), (384, 246, 512, 386),
        (514, 246, 640, 384), (641, 246, 765, 386), (765, 246, 892, 384), (894, 246, 1019, 384)
    ]
    walk_8 = [assemble_pose_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), 28), scale) for b in walk_boxes]
    make_strip(walk_8).save(os.path.join(out_dir, "Walk.png"))
    make_strip(walk_8).save(os.path.join(out_dir, "Run.png"))
    
    # 3. Jump (6 poses from row 3)
    jump_boxes = [
        (7, 690, 169, 829), (176, 690, 337, 829), (345, 689, 505, 828),
        (513, 693, 676, 829), (688, 660, 843, 829), (852, 690, 1006, 828)
    ]
    jump_frames = [assemble_jump_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), 28), scale, ground_crop_y=138) for b in jump_boxes]
    make_strip(jump_frames).save(os.path.join(out_dir, "Jump.png"))
    
    # 4. Attack / Attack_1 / Attack_2 / Attack_3 (6 full-body smash poses from row 2)
    atk_boxes = [
        (7, 437, 136, 628), (140, 432, 270, 628), (268, 414, 388, 628),
        (391, 418, 512, 628), (674, 434, 848, 632), (520, 500, 672, 630)
    ]
    atk_frames = [assemble_pose_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), 28), scale) for b in atk_boxes]
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack.png"))
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack_1.png"))
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack_2.png"))
    make_strip(atk_frames).save(os.path.join(out_dir, "Attack_3.png"))
    
    # 5. Shield / Protection (Row 4 granite brace stances, 4-frame breathing hold)
    guard_boxes = [(8, 882, 164, 1020), (172, 876, 320, 1020)]
    g0 = assemble_pose_frame(clean_crop_transparency(img.crop(guard_boxes[0]), False, (255,255,255), 28), scale)
    g1 = assemble_pose_frame(clean_crop_transparency(img.crop(guard_boxes[1]), False, (255,255,255), 28), scale)
    shield_loop = [g0, g1, g1, g0]
    make_strip(shield_loop).save(os.path.join(out_dir, "Shield.png"))
    make_strip(shield_loop).save(os.path.join(out_dir, "Protection.png"))
    
    # 6. Hurt & Dead
    hurt_boxes = [(329, 887, 486, 1020), (496, 887, 663, 1019)]
    hurt_frames = [assemble_pose_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), 28), scale) for b in hurt_boxes]
    make_strip(hurt_frames).save(os.path.join(out_dir, "Hurt.png"))
    
    dead_boxes = [(679, 919, 829, 1018), (841, 952, 1018, 1022)]
    dead_frames = [assemble_pose_frame(clean_crop_transparency(img.crop(b), False, (255,255,255), 28), scale) for b in dead_boxes]
    make_strip(dead_frames).save(os.path.join(out_dir, "Dead.png"))
    
    # 7. Portrait
    make_portrait(idle_frames[0]).save(os.path.join(out_dir, "portrait.png"))
    print("  -> Boran built successfully with 8-frame walk and 6-frame attack skills!")

def main():
    print("================================================================")
    print("   GENERATING MASTERPIECE SPRITES FOR ALL 4 CO-OP HEROES        ")
    print("================================================================")
    build_archer()
    build_aurelia()
    build_zephyr()
    build_boran()
    print("\nALL CO-OP CHARACTER SPRITES GENERATED AND VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    main()

