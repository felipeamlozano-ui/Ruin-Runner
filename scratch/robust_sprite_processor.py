import os
import sys
from PIL import Image, ImageFilter
import numpy as np
from collections import deque

def flood_fill_transparency(img_rgba, is_dark_bg=False, bg_color=None, dist_thresh=30):
    arr = np.array(img_rgba).astype(float)
    h, w, _ = arr.shape
    
    if is_dark_bg:
        d = np.sqrt((arr[:,:,0]-bg_color[0])**2 + (arr[:,:,1]-bg_color[1])**2 + (arr[:,:,2]-bg_color[2])**2)
    else:
        d = np.sqrt((arr[:,:,0]-255)**2 + (arr[:,:,1]-255)**2 + (arr[:,:,2]-255)**2)
        
    is_bg_candidate = d < dist_thresh
    visited = np.zeros((h, w), dtype=bool)
    queue = deque()
    
    for x in range(w):
        if is_bg_candidate[0, x]: queue.append((0, x)); visited[0, x] = True
        if is_bg_candidate[h-1, x]: queue.append((h-1, x)); visited[h-1, x] = True
    for y in range(h):
        if is_bg_candidate[y, 0]: queue.append((y, 0)); visited[y, 0] = True
        if is_bg_candidate[y, w-1]: queue.append((y, w-1)); visited[y, w-1] = True
        
    while queue:
        cy, cx = queue.popleft()
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ny, nx = cy + dy, cx + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and is_bg_candidate[ny, nx]:
                visited[ny, nx] = True
                queue.append((ny, nx))
                
    out_arr = np.array(img_rgba)
    out_arr[visited, 3] = 0
    return Image.fromarray(out_arr)

def find_sprite_columns(row_mask, min_sprite_w=55, max_gap=25):
    """
    Finds sprite column intervals [x1, x2] by analyzing column pixel density,
    ignoring bottom ground shadow to prevent merging adjacent frames.
    """
    h, w = row_mask.shape
    # Exclude bottom 15px (ground line shadow)
    body_h = max(20, h - 15)
    body_mask = row_mask[:body_h, :]
    col_c = np.sum(body_mask, axis=0)
    
    # Moving average smooth
    kernel = 7
    smoothed = np.convolve(col_c, np.ones(kernel)/kernel, mode='same')
    
    # Threshold for content vs gap
    thresh = max(10, np.mean(smoothed) * 0.22)
    
    intervals = []
    in_sprite = False
    start_x = 0
    
    for x in range(w):
        if smoothed[x] >= thresh:
            if not in_sprite:
                in_sprite = True
                start_x = x
        else:
            if in_sprite:
                in_sprite = False
                if x - start_x >= min_sprite_w:
                    intervals.append((start_x, x))
    if in_sprite and w - start_x >= min_sprite_w:
        intervals.append((start_x, w))
        
    # Check if any interval is very wide (e.g. >= 200px), indicating merged sprites
    final_cols = []
    for x1, x2 in intervals:
        width = x2 - x1
        if width > 180:
            # Look for local valley inside this wide interval
            sub = smoothed[x1:x2]
            # Find local minima in the middle 60%
            m_start = int(width * 0.25)
            m_end = int(width * 0.75)
            valley_idx = m_start + np.argmin(sub[m_start:m_end])
            split_x = x1 + valley_idx
            if split_x - x1 >= min_sprite_w and x2 - split_x >= min_sprite_w:
                final_cols.append((x1, split_x - 4))
                final_cols.append((split_x + 4, x2))
                continue
        final_cols.append((x1, x2))
        
    return final_cols

def assemble_anchored_frame(clean_row_img, x1, x2, row_ground_y, fixed_scale, baseline_y=124, frame_w=128, frame_h=128):
    """
    Crops sprite in [x1, x2], resizes by fixed_scale (NEVER varies per frame!),
    anchors character root at X=64 and feet/ground at Y=baseline_y (124).
    """
    row_arr = np.array(clean_row_img)
    sprite_crop = clean_row_img.crop((x1, 0, x2, clean_row_img.height))
    crop_arr = row_arr[:, x1:x2]
    alpha = crop_arr[:, :, 3]
    
    y_idx, x_idx = np.where(alpha > 15)
    if len(y_idx) == 0 or len(x_idx) == 0:
        return Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
        
    sy_min, sy_max = y_idx.min(), y_idx.max()
    sx_min, sx_max = x_idx.min(), x_idx.max()
    
    # Calculate root X (torso/hips center: lower half of the character)
    torso_y_start = sy_min + int((sy_max - sy_min) * 0.35)
    torso_y_end = sy_max
    torso_mask = alpha[torso_y_start:torso_y_end, :]
    ty, tx = np.where(torso_mask > 20)
    if len(tx) > 0:
        root_x_in_crop = np.median(tx)
    else:
        root_x_in_crop = (sx_min + sx_max) * 0.5
        
    # Scale entire crop by FIXED character scale
    cw, ch = sprite_crop.size
    nw = max(1, int(round(cw * fixed_scale)))
    nh = max(1, int(round(ch * fixed_scale)))
    
    resized = sprite_crop.resize((nw, nh), Image.Resampling.LANCZOS)
    
    # Determine paste X so root_x lands exactly at frame_w // 2 (64)
    paste_x = 64 - int(round(root_x_in_crop * fixed_scale))
    
    # Determine paste Y so row_ground_y lands exactly at baseline_y (124)
    # If the character is airborne (sy_max < row_ground_y), they naturally float above baseline_y!
    paste_y = baseline_y - int(round(row_ground_y * fixed_scale))
    
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

def make_portrait(idle_frame_0, frame_size=128):
    alpha = np.array(idle_frame_0)[:, :, 3]
    y_idx, x_idx = np.where(alpha > 15)
    if len(y_idx) == 0:
        return idle_frame_0
    
    y_top = y_idx.min()
    y_bot = y_idx.max()
    char_h = y_bot - y_top
    y_mid = y_top + int(char_h * 0.52)
    
    x_cen = int(np.median(x_idx))
    half_w = int(char_h * 0.32)
    x_min = max(0, x_cen - half_w)
    x_max = min(128, x_cen + half_w)
    
    bust = idle_frame_0.crop((x_min, y_top, x_max, y_mid))
    bw, bh = bust.size
    
    target_bh = 86
    scale = target_bh / float(max(1, bh))
    nbw, nbh = int(round(bw * scale)), int(round(bh * scale))
    resized_bust = bust.resize((nbw, nbh), Image.Resampling.LANCZOS)
    
    port = Image.new("RGBA", (frame_size, frame_size), (0, 0, 0, 0))
    px = (frame_size - nbw) // 2
    py = (frame_size - nbh) // 2 + 4
    port.paste(resized_bust, (px, py), resized_bust)
    return port
