import os
import sys
from pathlib import Path
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
pygame.init()
pygame.display.set_mode((640, 360))

# Add project root and src
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from entities.character_data import CHARACTER_ORDER, CHARACTER_REGISTRY

thumbnails = {}
for cid in CHARACTER_ORDER:
    prof = CHARACTER_REGISTRY[cid]
    frame = None
    try:
        # Check folder or craftpix
        if prof.sprite_type == "folder":
            p = os.path.join(prof.base_folder, "common_00_idle_stand_A_000.png")
            if os.path.exists(p):
                frame = pygame.image.load(p).convert_alpha()
        else:
            p = os.path.join(prof.base_folder, "Idle.png")
            if os.path.exists(p):
                raw = pygame.image.load(p).convert_alpha()
                fw, fh = prof.frame_size
                frame = raw.subsurface((0, 0, fw, fh))
        
        if frame is not None:
            bbox = frame.get_bounding_rect()
            print(f"[{cid}] Frame size: {frame.get_size()}, BBox: {bbox}")
            if bbox.width > 0 and bbox.height > 0:
                head_h = max(20, int(bbox.height * 0.45))
                crop_size = max(head_h, int(bbox.width * 0.70))
                crop_x = int(bbox.centerx - crop_size / 2)
                crop_y = int(bbox.top)
                
                # Clamp within frame bounds
                crop_x = max(0, min(frame.get_width() - crop_size, crop_x))
                crop_y = max(0, min(frame.get_height() - crop_size, crop_y))
                crop_size = min(crop_size, frame.get_width() - crop_x, frame.get_height() - crop_y)
                
                sub = frame.subsurface((crop_x, crop_y, crop_size, crop_size))
                scaled = pygame.transform.smoothscale(sub, (32, 32))
                sub_bbox = scaled.get_bounding_rect()
                print(f"  -> Cropped size: {crop_size}x{crop_size} at ({crop_x}, {crop_y}) -> Scaled BBox: {sub_bbox}")
                assert sub_bbox.width >= 10, f"Too empty for {cid}: {sub_bbox}"
                thumbnails[cid] = scaled
    except Exception as e:
        print(f"Error {cid}: {e}")

print(f"Total valid thumbnails: {len(thumbnails)}/{len(CHARACTER_ORDER)}")
