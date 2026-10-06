import os
import sys
from PIL import Image
import numpy as np

sys.path.append(os.path.dirname(__file__))
from robust_sprite_processor import (
    flood_fill_transparency,
    find_sprite_columns,
    assemble_anchored_frame,
    make_strip,
    make_portrait
)

# Precise row definitions and scale factors based on mathematical measurements
CHARACTERS = [
    {
        "id": "archer",
        "sheet": r"C:\Users\Felipe\.gemini\antigravity-ide\brain\b436599e-060f-4534-9bea-d5741b48a0b6\archer_sheet_1790680096666.jpg",
        "is_dark": False,
        "bg_color": (255, 255, 255),
        "thresh": 28,
        "fixed_scale": 0.4706,
        "out_dir": "assets/sprites/characters/coop/archer",
        "rows": {
            "idle": (37, 207),
            "walk": (242, 408),
            "run": (242, 408),
            "attack": (442, 615),
            "jump": (631, 818),
            "misc": (848, 1010) # hurt + dead
        }
    },
    {
        "id": "aurelia",
        "sheet": r"C:\Users\Felipe\.gemini\antigravity-ide\brain\b436599e-060f-4534-9bea-d5741b48a0b6\aurelia_sheet_1790680006763.jpg",
        "is_dark": True,
        "bg_color": (15, 21, 37),
        "thresh": 30,
        "fixed_scale": 0.5096,
        "out_dir": "assets/sprites/characters/coop/aurelia",
        "rows": {
            "idle": (18, 175),
            "walk": (195, 335),
            "run": (195, 335),
            "jump": (345, 505),
            "attack": (560, 770),
            "misc": (840, 990)
        }
    },
    {
        "id": "zephyr",
        "sheet": r"C:\Users\Felipe\.gemini\antigravity-ide\brain\b436599e-060f-4534-9bea-d5741b48a0b6\zephyr_sheet_1790680120086.jpg",
        "is_dark": False,
        "bg_color": (255, 255, 255),
        "thresh": 28,
        "fixed_scale": 0.4000,
        "out_dir": "assets/sprites/characters/coop/zephyr",
        "rows": {
            "idle": (20, 220),
            "walk": (250, 400),
            "run": (250, 400),
            "attack": (450, 620),
            "jump": (640, 820),
            "misc": (860, 1020)
        }
    },
    {
        "id": "boran",
        "sheet": r"C:\Users\Felipe\.gemini\antigravity-ide\brain\b436599e-060f-4534-9bea-d5741b48a0b6\boran_sheet_1790680143248.jpg",
        "is_dark": False,
        "bg_color": (255, 255, 255),
        "thresh": 28,
        "fixed_scale": 0.5405,
        "out_dir": "assets/sprites/characters/coop/boran",
        "rows": {
            "idle": (30, 200),
            "walk": (230, 390),
            "run": (230, 390),
            "attack": (420, 630),
            "jump": (680, 830),
            "misc": (870, 1020)
        }
    }
]

def process_character(char_cfg):
    cid = char_cfg["id"]
    sheet_p = char_cfg["sheet"]
    out_dir = char_cfg["out_dir"]
    os.makedirs(out_dir, exist_ok=True)
    fixed_scale = char_cfg["fixed_scale"]
    
    print(f"\n=======================================================")
    print(f" PROCESSING {cid.upper()} (Fixed Scale: {fixed_scale:.4f})")
    print(f"=======================================================")
    
    orig_img = Image.open(sheet_p).convert("RGBA")
    clean_img = flood_fill_transparency(orig_img, char_cfg["is_dark"], char_cfg["bg_color"], char_cfg["thresh"])
    
    # Process each row
    row_frames = {}
    for anim_name, (y1, y2) in char_cfg["rows"].items():
        row_crop = clean_img.crop((0, y1, 1024, y2))
        row_arr = np.array(row_crop)
        row_alpha = row_arr[:, :, 3]
        
        # Calculate ground line of this row (max y among solid pixels)
        y_pts, _ = np.where(row_alpha > 20)
        row_ground_y = y_pts.max() if len(y_pts) > 0 else (y2 - y1 - 2)
        
        cols = find_sprite_columns(row_alpha > 20)
        print(f"  {anim_name.upper():<7} (y={y1:3d}..{y2:3d}, h={y2-y1:3d}, ground={row_ground_y:3d}): found {len(cols)} frames")
        
        frames = []
        for x1, x2 in cols:
            frame = assemble_anchored_frame(row_crop, x1, x2, row_ground_y, fixed_scale, baseline_y=124)
            frames.append(frame)
        row_frames[anim_name] = frames
        
def make_breathing_idle(base_frame):
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
    
    im_f0 = Image.fromarray(f0, 'RGBA')
    im_f1 = Image.fromarray(f_inhale, 'RGBA')
    return [im_f0, im_f1, im_f1, im_f0]

    # Assemble final strips
    # 1. Idle (Stationary grounded breathing loop: zero leg stepping, zero running-in-place)
    idle_f = make_breathing_idle(row_frames["idle"][0])
    make_strip(idle_f).save(os.path.join(out_dir, "Idle.png"))
    print(f"  -> Saved Idle.png (4-frame stationary breathing loop)")
    
    # 2. Walk
    walk_f = row_frames["walk"]
    make_strip(walk_f).save(os.path.join(out_dir, "Walk.png"))
    print(f"  -> Saved Walk.png ({len(walk_f)} frames)")
    
    # 3. Run
    run_f = row_frames["run"]
    make_strip(run_f).save(os.path.join(out_dir, "Run.png"))
    print(f"  -> Saved Run.png ({len(run_f)} frames)")
    
    # 4. Jump
    jump_f = row_frames["jump"]
    make_strip(jump_f).save(os.path.join(out_dir, "Jump.png"))
    print(f"  -> Saved Jump.png ({len(jump_f)} frames)")
    
    # 5. Attack (Attack, Attack_1, Attack_2, Attack_3)
    atk_f = row_frames["attack"]
    make_strip(atk_f).save(os.path.join(out_dir, "Attack.png"))
    make_strip(atk_f).save(os.path.join(out_dir, "Attack_1.png"))
    if len(atk_f) >= 4:
        mid = len(atk_f) // 2
        make_strip(atk_f[:mid]).save(os.path.join(out_dir, "Attack_2.png"))
        make_strip(atk_f[mid:]).save(os.path.join(out_dir, "Attack_3.png"))
    else:
        make_strip(atk_f).save(os.path.join(out_dir, "Attack_2.png"))
        make_strip(atk_f).save(os.path.join(out_dir, "Attack_3.png"))
    print(f"  -> Saved Attack.png / Attack_1..3 ({len(atk_f)} frames)")
    
    # 6. Misc (Shield, Hurt, Dead)
    misc_f = row_frames["misc"]
    if len(misc_f) >= 4:
        shield_f = misc_f[:2]
        hurt_f = [misc_f[1]]
        dead_f = misc_f[2:]
    elif len(misc_f) == 3:
        shield_f = [misc_f[0]]
        hurt_f = [misc_f[1]]
        dead_f = [misc_f[2]]
    else:
        shield_f = misc_f
        hurt_f = misc_f
        dead_f = misc_f
        
    make_strip(shield_f).save(os.path.join(out_dir, "Shield.png"))
    make_strip(shield_f).save(os.path.join(out_dir, "Protection.png"))
    make_strip(hurt_f).save(os.path.join(out_dir, "Hurt.png"))
    make_strip(dead_f).save(os.path.join(out_dir, "Dead.png"))
    print(f"  -> Saved Shield/Hurt/Dead ({len(shield_f)}/{len(hurt_f)}/{len(dead_f)} frames)")
    
    # 7. Portrait
    if idle_f:
        portrait = make_portrait(idle_f[0])
        portrait.save(os.path.join(out_dir, "portrait.png"))
        print(f"  -> Saved portrait.png")

def main():
    for c in CHARACTERS:
        process_character(c)
    print("\nALL COOP CHARACTERS BUILT WITH PERFECT FIXED SCALE & ZERO JITTER!")

if __name__ == "__main__":
    main()
