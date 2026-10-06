import os
import sys
from PIL import Image, ImageDraw
import numpy as np
from collections import deque

def flood_fill_transparency(img_rgba, is_dark_bg=False, bg_color=None, dist_thresh=32):
    """
    Flood fills from image boundaries to only remove external background,
    preserving internal whites/highlights.
    """
    arr = np.array(img_rgba).astype(float)
    h, w, _ = arr.shape
    
    if is_dark_bg:
        d = np.sqrt((arr[:,:,0]-bg_color[0])**2 + (arr[:,:,1]-bg_color[1])**2 + (arr[:,:,2]-bg_color[2])**2)
    else:
        d = np.sqrt((arr[:,:,0]-255)**2 + (arr[:,:,1]-255)**2 + (arr[:,:,2]-255)**2)
        
    is_bg_candidate = d < dist_thresh
    
    # BFS from all borders
    visited = np.zeros((h, w), dtype=bool)
    queue = deque()
    
    for x in range(w):
        if is_bg_candidate[0, x]:
            queue.append((0, x))
            visited[0, x] = True
        if is_bg_candidate[h-1, x]:
            queue.append((h-1, x))
            visited[h-1, x] = True
            
    for y in range(h):
        if is_bg_candidate[y, 0]:
            queue.append((y, 0))
            visited[y, 0] = True
        if is_bg_candidate[y, w-1]:
            queue.append((y, w-1))
            visited[y, w-1] = True
            
    while queue:
        cy, cx = queue.popleft()
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ny, nx = cy + dy, cx + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and is_bg_candidate[ny, nx]:
                visited[ny, nx] = True
                queue.append((ny, nx))
                
    # visited is the true background mask!
    out_arr = np.array(img_rgba)
    out_arr[visited, 3] = 0 # set alpha to 0
    
    # Soft feathering at the border of visited
    # For pixels adjacent to visited that have high dist, slight anti-alias
    return Image.fromarray(out_arr)

def get_bounding_box(img_rgba):
    alpha = np.array(img_rgba)[:, :, 3]
    y_idx, x_idx = np.where(alpha > 10)
    if len(y_idx) == 0 or len(x_idx) == 0:
        return None
    return (int(x_idx.min()), int(y_idx.min()), int(x_idx.max()) + 1, int(y_idx.max()) + 1)

def fit_to_craftpix_frame(crop_img, target_h=82, baseline_y=125, frame_w=128, frame_h=128):
    """
    Fits a cropped sprite into a 128x128 frame:
    - Scales height proportionally to target_h (~80-84px)
    - Positions feet at baseline_y (125)
    - Centers horizontally at frame_w // 2 (64)
    """
    cw, ch = crop_img.size
    if cw == 0 or ch == 0:
        return Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
        
    scale = target_h / float(ch)
    # Don't scale up wildly if it's already big
    scale = min(scale, 1.25)
    new_w = max(1, int(round(cw * scale)))
    new_h = max(1, int(round(ch * scale)))
    
    resized = crop_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    frame = Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
    paste_x = (frame_w - new_w) // 2
    paste_y = baseline_y - new_h
    if paste_y < 0:
        paste_y = 0
    frame.paste(resized, (paste_x, paste_y), resized)
    return frame

def make_strip(frames, frame_w=128, frame_h=128):
    """Combines a list of 128x128 frames into a horizontal strip."""
    if not frames:
        return Image.new("RGBA", (frame_w, frame_h), (0, 0, 0, 0))
    strip = Image.new("RGBA", (len(frames) * frame_w, frame_h), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        strip.paste(f, (i * frame_w, 0), f)
    return strip

def make_portrait(idle_frame_0, frame_size=128):
    """Creates a beautiful 128x128 portrait from frame 0."""
    # Crop upper 60% of character and center with slight zoom
    alpha = np.array(idle_frame_0)[:, :, 3]
    y_idx, x_idx = np.where(alpha > 10)
    if len(y_idx) == 0:
        return idle_frame_0
    
    # Upper half of character
    y_top = y_idx.min()
    y_mid = y_top + int((y_idx.max() - y_top) * 0.58)
    x_min = max(0, x_idx.min() - 8)
    x_max = min(128, x_idx.max() + 8)
    
    bust = idle_frame_0.crop((x_min, y_top, x_max, y_mid))
    bw, bh = bust.size
    
    # Scale to ~90px height
    target_bh = 88
    b_scale = target_bh / float(max(1, bh))
    nbw = int(bw * b_scale)
    nbh = int(bh * b_scale)
    bust_scaled = bust.resize((nbw, nbh), Image.Resampling.LANCZOS)
    
    portrait = Image.new("RGBA", (frame_size, frame_size), (0, 0, 0, 0))
    px = (frame_size - nbw) // 2
    py = (frame_size - nbh) // 2 + 6
    portrait.paste(bust_scaled, (px, py), bust_scaled)
    return portrait
