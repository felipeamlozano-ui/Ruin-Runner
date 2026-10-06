import os
from PIL import Image
import numpy as np

def extract_row_sprites(sheet_path, is_dark_bg=False, bg_color=None, dist_thresh=30):
    img = Image.open(sheet_path).convert("RGBA")
    arr = np.array(img).astype(float)
    
    if is_dark_bg:
        d = np.sqrt((arr[:,:,0]-bg_color[0])**2 + (arr[:,:,1]-bg_color[1])**2 + (arr[:,:,2]-bg_color[2])**2)
        mask = d > dist_thresh
    else:
        # Distance to white
        d = np.sqrt((arr[:,:,0]-255)**2 + (arr[:,:,1]-255)**2 + (arr[:,:,2]-255)**2)
        mask = d > dist_thresh
        
    # Find rows
    row_c = np.sum(mask, axis=1)
    rows = []
    in_r = False
    s = 0
    for y, c in enumerate(row_c):
        if c > 40:
            if not in_r: in_r = True; s = y
        elif in_r:
            in_r = False
            if y - s > 35: # Ignore text headers < 35px
                rows.append((s, y))
    if in_r and 1024 - s > 35:
        rows.append((s, 1024))
        
    result = []
    for r_idx, (y1, y2) in enumerate(rows):
        row_mask = mask[y1:y2, :]
        col_c = np.sum(row_mask, axis=0)
        cols = []
        in_c = False
        cs = 0
        for x, c in enumerate(col_c):
            if c > 5:
                if not in_c: in_c = True; cs = x
            elif in_c:
                in_c = False
                if x - cs > 20: # Sprite width
                    cols.append((cs, x))
        if in_c and 1024 - cs > 20:
            cols.append((cs, 1024))
        result.append(((y1, y2), cols))
    return result

print("=== AURELIA ===")
a_rows = extract_row_sprites(r"C:\Users\Felipe\.gemini\antigravity-ide\brain\b436599e-060f-4534-9bea-d5741b48a0b6\aurelia_sheet_1790680006763.jpg", True, (15, 21, 37), 28)
for i, ((y1, y2), cols) in enumerate(a_rows):
    print(f"Row {i} (y={y1}..{y2}): {len(cols)} sprites")

print("\n=== ARCHER ===")
arch_rows = extract_row_sprites(r"C:\Users\Felipe\.gemini\antigravity-ide\brain\b436599e-060f-4534-9bea-d5741b48a0b6\archer_sheet_1790680096666.jpg", False, (255, 255, 255), 25)
for i, ((y1, y2), cols) in enumerate(arch_rows):
    print(f"Row {i} (y={y1}..{y2}): {len(cols)} sprites")

print("\n=== ZEPHYR ===")
z_rows = extract_row_sprites(r"C:\Users\Felipe\.gemini\antigravity-ide\brain\b436599e-060f-4534-9bea-d5741b48a0b6\zephyr_sheet_1790680120086.jpg", False, (255, 255, 255), 25)
for i, ((y1, y2), cols) in enumerate(z_rows):
    print(f"Row {i} (y={y1}..{y2}): {len(cols)} sprites")

print("\n=== BORAN ===")
b_rows = extract_row_sprites(r"C:\Users\Felipe\.gemini\antigravity-ide\brain\b436599e-060f-4534-9bea-d5741b48a0b6\boran_sheet_1790680143248.jpg", False, (255, 255, 255), 25)
for i, ((y1, y2), cols) in enumerate(b_rows):
    print(f"Row {i} (y={y1}..{y2}): {len(cols)} sprites")
