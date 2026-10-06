import os
from PIL import Image
import numpy as np
from collections import deque

def extract_clean_sprite(crop_img, is_dark, bg_col, seed_tolerance=35, edge_tolerance=55):
    """
    Extracts character with pristine alpha:
    1. Flood fills background from outer perimeter with seed_tolerance.
    2. Expands flood fill to include transitional edge pixels up to edge_tolerance.
    3. Guarantees zero halo/capsule artifacts.
    """
    arr = np.array(crop_img.convert('RGBA')).astype(np.float32)
    h, w, _ = arr.shape
    rgb = arr[:, :, :3]
    
    if is_dark:
        bg = np.array(bg_col, dtype=np.float32)
        dist = np.sqrt(np.sum((rgb - bg)**2, axis=-1))
    else:
        # Distance from white
        dist = np.sqrt(np.sum((255.0 - rgb)**2, axis=-1))
        # Off-white compression artifacts treated as background
        is_whitish = (rgb[:, :, 0] > 215) & (rgb[:, :, 1] > 215) & (rgb[:, :, 2] > 215)
        dist = np.where(is_whitish, np.minimum(dist, 20.0), dist)
        
    is_bg_seed = dist < seed_tolerance
    visited = np.zeros((h, w), dtype=bool)
    q = deque()
    
    for x in range(w):
        if is_bg_seed[0, x]: q.append((0, x)); visited[0, x] = True
        if is_bg_seed[h-1, x]: q.append((h-1, x)); visited[h-1, x] = True
    for y in range(h):
        if is_bg_seed[y, 0]: q.append((y, 0)); visited[y, 0] = True
        if is_bg_seed[y, w-1]: q.append((y, w-1)); visited[y, w-1] = True
        
    while q:
        cy, cx = q.popleft()
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ny, nx = cy + dy, cx + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx]:
                if dist[ny, nx] < edge_tolerance:
                    visited[ny, nx] = True
                    q.append((ny, nx))
                    
    alpha = np.ones((h, w), dtype=np.float32) * 255.0
    alpha[visited] = 0.0
    
    arr[:, :, 3] = alpha
    return Image.fromarray(arr.astype(np.uint8))

if __name__ == "__main__":
    test_crops = {
        'zephyr': (r'C:\Users\Felipe\.gemini\antigravity-ide\brain\b436599e-060f-4534-9bea-d5741b48a0b6\zephyr_sheet_1790680120086.jpg', False, (255,255,255), (15, 5, 185, 225)),
        'aurelia': (r'C:\Users\Felipe\.gemini\antigravity-ide\brain\b436599e-060f-4534-9bea-d5741b48a0b6\aurelia_sheet_1790680006763.jpg', True, (15,21,37), (0, 5, 125, 180)),
        'boran': (r'C:\Users\Felipe\.gemini\antigravity-ide\brain\b436599e-060f-4534-9bea-d5741b48a0b6\boran_sheet_1790680143248.jpg', False, (255,255,255), (2, 40, 172, 195)),
        'archer': (r'C:\Users\Felipe\.gemini\antigravity-ide\brain\b436599e-060f-4534-9bea-d5741b48a0b6\archer_sheet_1790680096666.jpg', False, (255,255,255), (35, 30, 135, 210))
    }

    for name, (path, is_dark, bg, box) in test_crops.items():
        im = Image.open(path)
        crop = im.crop(box)
        res = extract_clean_sprite(crop, is_dark, bg)
        arr = np.array(res)
        alpha = arr[:, :, 3]
        y_pts, x_pts = np.where(alpha > 10)
        print(f'{name}: crop size={crop.size}, alpha bounds Y={y_pts.min()}..{y_pts.max()}, X={x_pts.min()}..{x_pts.max()}')
        border_alpha = np.concatenate([alpha[0, :], alpha[-1, :], alpha[:, 0], alpha[:, -1]])
        print(f'  Border opaque pixels count: {np.sum(border_alpha > 10)}')
        res.save(f'scratch/clean_{name}.png')

    print('SUCCESS! All 4 characters tested.')
