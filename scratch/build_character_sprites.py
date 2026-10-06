import os
import sys
from PIL import Image
import numpy as np

from sprite_utils import (
    flood_fill_transparency,
    get_bounding_box,
    fit_to_craftpix_frame,
    make_strip,
    make_portrait
)

SHEETS_DATA = [
    {
        "id": "aurelia",
        "sheet": r"C:\Users\Felipe\.gemini\antigravity-ide\brain\b436599e-060f-4534-9bea-d5741b48a0b6\aurelia_sheet_1790680006763.jpg",
        "is_dark": True,
        "bg_color": (15, 21, 37),
        "thresh": 30,
        "out_dir": r"assets/sprites/characters/coop/aurelia",
        "target_h": 82,
        "anim_rows": {
            "idle": 0,
            "walk": 1,
            "run": 1,
            "attack": 2,
            "shield": (3, [0, 1]),
            "hurt": (3, [2]),
            "dead": (3, [3, 4])
        }
    },
    {
        "id": "archer",
        "sheet": r"C:\Users\Felipe\.gemini\antigravity-ide\brain\b436599e-060f-4534-9bea-d5741b48a0b6\archer_sheet_1790680096666.jpg",
        "is_dark": False,
        "bg_color": (255, 255, 255),
        "thresh": 28,
        "out_dir": r"assets/sprites/characters/coop/archer",
        "target_h": 82,
        "anim_rows": {
            "idle": 0,
            "walk": 1,
            "run": 1,
            "attack": 2,
            "jump": 3,
            "shield": (3, [3, 4]),
            "hurt": (4, [0, 1]),
            "dead": (4, [2, 3, 4])
        }
    },
    {
        "id": "zephyr",
        "sheet": r"C:\Users\Felipe\.gemini\antigravity-ide\brain\b436599e-060f-4534-9bea-d5741b48a0b6\zephyr_sheet_1790680120086.jpg",
        "is_dark": False,
        "bg_color": (255, 255, 255),
        "thresh": 28,
        "out_dir": r"assets/sprites/characters/coop/zephyr",
        "target_h": 82,
        "anim_rows": {
            "idle": 0,
            "walk": 1,
            "run": 1,
            "attack": 2,
            "shield": 3,
            "jump": 1,
            "hurt": (4, [0, 1]),
            "dead": (4, [2, 3, 4])
        }
    },
    {
        "id": "boran",
        "sheet": r"C:\Users\Felipe\.gemini\antigravity-ide\brain\b436599e-060f-4534-9bea-d5741b48a0b6\boran_sheet_1790680143248.jpg",
        "is_dark": False,
        "bg_color": (255, 255, 255),
        "thresh": 28,
        "out_dir": r"assets/sprites/characters/coop/boran",
        "target_h": 80,
        "anim_rows": {
            "idle": 0,
            "walk": 1,
            "run": 1,
            "attack": 2,
            "shield": 3,
            "jump": 1,
            "hurt": (4, [0, 1, 2]),
            "dead": (4, [3, 4, 5])
        }
    }
]

def extract_rows_and_sprites(clean_img):
    arr = np.array(clean_img)
    alpha = arr[:, :, 3]
    h, w = alpha.shape
    
    # Non-empty row profile
    row_counts = np.sum(alpha > 20, axis=1)
    rows = []
    in_r = False
    s = 0
    for y in range(h):
        if row_counts[y] > 40:
            if not in_r: in_r = True; s = y
        elif in_r:
            in_r = False
            if y - s > 35: # Ignore text headers
                rows.append((s, y))
    if in_r and h - s > 35:
        rows.append((s, h))
        
    extracted_rows = []
    for (y1, y2) in rows:
        row_alpha = alpha[y1:y2, :]
        col_c = np.sum(row_alpha > 20, axis=0)
        cols = []
        in_c = False
        cs = 0
        for x in range(w):
            if col_c[x] > 5:
                if not in_c: in_c = True; cs = x
            elif in_c:
                in_c = False
                if x - cs > 18: # min sprite width
                    cols.append((cs, x))
        if in_c and w - cs > 18:
            cols.append((cs, w))
            
        # Crop each sprite in this row
        sprites = []
        for (x1, x2) in cols:
            crop = clean_img.crop((x1, y1, x2, y2))
            bbox = get_bounding_box(crop)
            if bbox:
                # Tight crop to true content
                tight = crop.crop(bbox)
                sprites.append(tight)
        extracted_rows.append(sprites)
    return extracted_rows

def build_all():
    for data in SHEETS_DATA:
        cid = data["id"]
        sheet_path = data["sheet"]
        out_dir = data["out_dir"]
        os.makedirs(out_dir, exist_ok=True)
        print(f"\n=================== Processing {cid.upper()} ===================")
        
        orig = Image.open(sheet_path).convert("RGBA")
        print("Removing background with boundary flood-fill...")
        clean = flood_fill_transparency(orig, data["is_dark"], data["bg_color"], data["thresh"])
        
        rows = extract_rows_and_sprites(clean)
        print(f"Extracted {len(rows)} animation rows.")
        for i, r in enumerate(rows):
            print(f"  Row {i}: {len(r)} sprites")
            
        def get_sprites_for_spec(spec):
            if isinstance(spec, int):
                if spec < len(rows):
                    return rows[spec]
                return rows[0]
            elif isinstance(spec, tuple):
                r_idx, indices = spec
                if r_idx < len(rows):
                    row_sprites = rows[r_idx]
                    return [row_sprites[idx] for idx in indices if idx < len(row_sprites)]
                return rows[0]
            return rows[0]

        target_h = data.get("target_h", 82)
        
        # 1. Idle
        idle_raw = get_sprites_for_spec(data["anim_rows"]["idle"])
        idle_frames = [fit_to_craftpix_frame(s, target_h=target_h) for s in idle_raw]
        idle_strip = make_strip(idle_frames)
        idle_strip.save(os.path.join(out_dir, "Idle.png"))
        print(f"Saved Idle.png ({len(idle_frames)} frames)")
        
        # 2. Walk
        walk_raw = get_sprites_for_spec(data["anim_rows"]["walk"])
        walk_frames = [fit_to_craftpix_frame(s, target_h=target_h) for s in walk_raw]
        walk_strip = make_strip(walk_frames)
        walk_strip.save(os.path.join(out_dir, "Walk.png"))
        print(f"Saved Walk.png ({len(walk_frames)} frames)")
        
        # 3. Run
        run_raw = get_sprites_for_spec(data["anim_rows"]["run"])
        run_frames = [fit_to_craftpix_frame(s, target_h=target_h) for s in run_raw]
        run_strip = make_strip(run_frames)
        run_strip.save(os.path.join(out_dir, "Run.png"))
        print(f"Saved Run.png ({len(run_frames)} frames)")
        
        # 4. Attack / Attack_1 / Attack_2 / Attack_3
        atk_raw = get_sprites_for_spec(data["anim_rows"]["attack"])
        atk_frames = [fit_to_craftpix_frame(s, target_h=target_h) for s in atk_raw]
        atk_strip = make_strip(atk_frames)
        atk_strip.save(os.path.join(out_dir, "Attack.png"))
        atk_strip.save(os.path.join(out_dir, "Attack_1.png"))
        
        # If >= 4 frames, slice attack 2 & 3
        if len(atk_frames) >= 4:
            mid = len(atk_frames) // 2
            make_strip(atk_frames[:mid]).save(os.path.join(out_dir, "Attack_2.png"))
            make_strip(atk_frames[mid:]).save(os.path.join(out_dir, "Attack_3.png"))
        else:
            atk_strip.save(os.path.join(out_dir, "Attack_2.png"))
            atk_strip.save(os.path.join(out_dir, "Attack_3.png"))
        print(f"Saved Attack.png / Attack_1..3 ({len(atk_frames)} frames)")
        
        # 5. Jump
        jump_spec = data["anim_rows"].get("jump", data["anim_rows"]["walk"])
        jump_raw = get_sprites_for_spec(jump_spec)
        jump_frames = [fit_to_craftpix_frame(s, target_h=target_h) for s in jump_raw]
        jump_strip = make_strip(jump_frames)
        jump_strip.save(os.path.join(out_dir, "Jump.png"))
        print(f"Saved Jump.png ({len(jump_frames)} frames)")
        
        # 6. Shield / Protection
        shield_raw = get_sprites_for_spec(data["anim_rows"]["shield"])
        shield_frames = [fit_to_craftpix_frame(s, target_h=target_h) for s in shield_raw]
        shield_strip = make_strip(shield_frames)
        shield_strip.save(os.path.join(out_dir, "Shield.png"))
        shield_strip.save(os.path.join(out_dir, "Protection.png"))
        print(f"Saved Shield.png / Protection.png ({len(shield_frames)} frames)")
        
        # 7. Hurt
        hurt_raw = get_sprites_for_spec(data["anim_rows"]["hurt"])
        hurt_frames = [fit_to_craftpix_frame(s, target_h=target_h) for s in hurt_raw]
        hurt_strip = make_strip(hurt_frames)
        hurt_strip.save(os.path.join(out_dir, "Hurt.png"))
        print(f"Saved Hurt.png ({len(hurt_frames)} frames)")
        
        # 8. Dead
        dead_raw = get_sprites_for_spec(data["anim_rows"]["dead"])
        dead_frames = [fit_to_craftpix_frame(s, target_h=target_h) for s in dead_raw]
        dead_strip = make_strip(dead_frames)
        dead_strip.save(os.path.join(out_dir, "Dead.png"))
        print(f"Saved Dead.png ({len(dead_frames)} frames)")
        
        # 9. Portrait
        if idle_frames:
            portrait = make_portrait(idle_frames[0])
            portrait.save(os.path.join(out_dir, "portrait.png"))
            print("Saved portrait.png (128x128)")

if __name__ == "__main__":
    build_all()
    print("\nAll character sprites built successfully!")
