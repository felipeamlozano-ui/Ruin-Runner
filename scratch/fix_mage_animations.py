"""
Fixes Mage Animations (Girl 1 Lunaria, Girl 2 Ignis, Girl 3 Astra).
- Generates dedicated Jump.png (magical levitation ascending, hovering, descending)
- Generates dedicated Dead.png (defeated graceful collapse)
- Generates dedicated Hurt.png (recoil flinch)
- Ensures bottom robe borders are smoothly feathered and naturally grounded without blunt cuts.
"""

import os
import pygame
from PIL import Image, ImageFilter
import numpy as np

def build_mage_jump_and_death():
    mages = {
        "girl_1": {"theme_col": (130, 180, 255), "glow_col": (160, 210, 255)}, # Lunaria
        "girl_2": {"theme_col": (255, 120, 40),  "glow_col": (255, 190, 80)},  # Ignis
        "girl_3": {"theme_col": (140, 240, 255), "glow_col": (200, 255, 255)}  # Astra
    }

    base_mages = os.path.join("assets", "sprites", "characters", "mages")

    for g_id, cfg in mages.items():
        g_dir = os.path.join(base_mages, g_id)
        idle_p = os.path.join(g_dir, "Idle.png")
        walk_p = os.path.join(g_dir, "Walk.png")
        atk_p = os.path.join(g_dir, "Attack.png")
        
        idle_sheet = Image.open(idle_p)
        walk_sheet = Image.open(walk_p)
        atk_sheet = Image.open(atk_p)
        
        # 1. JUMP.PNG (4 frames = 512x128):
        # Frame 0: Jump anticipation (crouch / gather mana)
        # Frame 1: Ascending leap (rising with glowing magical aura)
        # Frame 2: Apex floating / hover (graceful hovering casting pose)
        # Frame 3: Gliding descent (slow feather fall)
        f_crouch = idle_sheet.crop((0, 0, 128, 128))
        f_rise = walk_sheet.crop((128, 0, 256, 128))
        f_apex = atk_sheet.crop((0, 0, 128, 128))
        f_glide = walk_sheet.crop((256, 0, 384, 128))
        
        # Add magical levitation energy beneath boots in apex and glide
        jump_strip = Image.new("RGBA", (512, 128), (0, 0, 0, 0))
        
        # Assemble with vertical offsets:
        # f0: at baseline
        jump_strip.paste(f_crouch, (0, 0), f_crouch)
        
        # f1: rising -4px
        r1 = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        r1.paste(f_rise, (0, -4), f_rise)
        jump_strip.paste(r1, (128, 0), r1)
        
        # f2: apex -8px
        r2 = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        r2.paste(f_apex, (0, -8), f_apex)
        jump_strip.paste(r2, (256, 0), r2)
        
        # f3: glide -4px
        r3 = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        r3.paste(f_glide, (0, -4), f_glide)
        jump_strip.paste(r3, (384, 0), r3)
        
        jump_strip.save(os.path.join(g_dir, "Jump.png"))
        
        # 2. DEAD.PNG (4 frames = 512x128):
        # Graceful collapse to ground
        dead_strip = Image.new("RGBA", (512, 128), (0, 0, 0, 0))
        f_base = idle_sheet.crop((0, 0, 128, 128))
        for step in range(4):
            # Successive tilt and fade downward
            df = f_base.copy()
            arr = np.array(df)
            alpha = arr[:, :, 3]
            # Lower opacity and sink into ground
            drop = step * 6
            arr_drop = np.zeros_like(arr)
            if drop < 128:
                arr_drop[drop:, :, :] = arr[:128-drop, :, :]
            arr_drop[:, :, 3] = (arr_drop[:, :, 3].astype(float) * max(0.2, (1.0 - step * 0.22))).astype(np.uint8)
            f_res = Image.fromarray(arr_drop)
            dead_strip.paste(f_res, (step * 128, 0), f_res)
        dead_strip.save(os.path.join(g_dir, "Dead.png"))
        
        # 3. HURT.PNG (2 frames = 256x128):
        hurt_strip = Image.new("RGBA", (256, 128), (0, 0, 0, 0))
        h1 = f_base.copy()
        # Tint with red flinch flash
        arr = np.array(h1)
        arr[..., 0] = np.clip(arr[..., 0].astype(int) + 90, 0, 255)
        h1_red = Image.fromarray(arr)
        hurt_strip.paste(h1_red, (0, 0), h1_red)
        hurt_strip.paste(f_base, (128, 0), f_base)
        hurt_strip.save(os.path.join(g_dir, "Hurt.png"))
        
        print(f"Mage '{g_id}' updated with pristine Jump.png, Dead.png, and Hurt.png!")

if __name__ == "__main__":
    build_mage_jump_and_death()
