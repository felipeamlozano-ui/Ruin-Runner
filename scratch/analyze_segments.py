import os
from PIL import Image
import numpy as np

def analyze_sheet(name, path, is_dark_bg=False):
    img = Image.open(path).convert("RGBA")
    arr = np.array(img)
    print(f"\n==================== {name} ====================")
    
    # Calculate mask of non-background pixels
    if is_dark_bg:
        # Background is dark blue ~ [15, 21, 37]
        r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
        # Distance to dark blue
        dist = np.sqrt((r - 15)**2 + (g - 21)**2 + (b - 37)**2)
        mask = dist > 35
    else:
        # Background is white / off-white ~ [250-255, 250-255, 250-255]
        r, g, b = arr[..., 0].astype(int), arr[..., 1].astype(int), arr[..., 2].astype(int)
        mask = (r < 240) | (g < 240) | (b < 240)
    
    # Row profile: count non-bg pixels per row
    row_counts = np.sum(mask, axis=1)
    
    # Identify continuous segments of rows with pixels
    rows = []
    in_row = False
    start_y = 0
    for y in range(len(row_counts)):
        if row_counts[y] > 50:
            if not in_row:
                in_row = True
                start_y = y
        else:
            if in_row:
                in_row = False
                if y - start_y > 20: # Minimum row height
                    rows.append((start_y, y))
    if in_row and 1024 - start_y > 20:
        rows.append((start_y, 1024))
        
    print(f"Found {len(rows)} rows:")
    for idx, (y1, y2) in enumerate(rows):
        # In this row, find column segments (sprites)
        row_mask = mask[y1:y2, :]
        col_counts = np.sum(row_mask, axis=0)
        
        sprites = []
        in_col = False
        start_x = 0
        for x in range(len(col_counts)):
            if col_counts[x] > 5:
                if not in_col:
                    in_col = True
                    start_x = x
            else:
                if in_col:
                    in_col = False
                    if x - start_x > 15: # Minimum sprite width
                        sprites.append((start_x, x))
        if in_col and 1024 - start_x > 15:
            sprites.append((start_x, 1024))
            
        print(f"  Row {idx} (y={y1}..{y2}, h={y2-y1}): {len(sprites)} sprites -> {sprites}")

analyze_sheet("aurelia", r"C:\Users\Felipe\.gemini\antigravity-ide\brain\b436599e-060f-4534-9bea-d5741b48a0b6\aurelia_sheet_1790680006763.jpg", is_dark_bg=True)
analyze_sheet("archer", r"C:\Users\Felipe\.gemini\antigravity-ide\brain\b436599e-060f-4534-9bea-d5741b48a0b6\archer_sheet_1790680096666.jpg", is_dark_bg=False)
analyze_sheet("zephyr", r"C:\Users\Felipe\.gemini\antigravity-ide\brain\b436599e-060f-4534-9bea-d5741b48a0b6\zephyr_sheet_1790680120086.jpg", is_dark_bg=False)
analyze_sheet("boran", r"C:\Users\Felipe\.gemini\antigravity-ide\brain\b436599e-060f-4534-9bea-d5741b48a0b6\boran_sheet_1790680143248.jpg", is_dark_bg=False)
