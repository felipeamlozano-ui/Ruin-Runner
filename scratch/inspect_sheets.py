import os
import sys
from PIL import Image
import numpy as np

SHEETS = {
    "aurelia": r"C:\Users\Felipe\.gemini\antigravity-ide\brain\b436599e-060f-4534-9bea-d5741b48a0b6\aurelia_sheet_1790680006763.jpg",
    "archer": r"C:\Users\Felipe\.gemini\antigravity-ide\brain\b436599e-060f-4534-9bea-d5741b48a0b6\archer_sheet_1790680096666.jpg",
    "zephyr": r"C:\Users\Felipe\.gemini\antigravity-ide\brain\b436599e-060f-4534-9bea-d5741b48a0b6\zephyr_sheet_1790680120086.jpg",
    "boran": r"C:\Users\Felipe\.gemini\antigravity-ide\brain\b436599e-060f-4534-9bea-d5741b48a0b6\boran_sheet_1790680143248.jpg",
}

for name, path in SHEETS.items():
    if not os.path.exists(path):
        print(f"File not found: {path}")
        continue
    img = Image.open(path)
    print(f"\n=== {name} ===")
    print(f"Size: {img.size}, Mode: {img.mode}")
    arr = np.array(img)
    # Check corners for background color
    corners = [
        arr[0, 0], arr[0, -1], arr[-1, 0], arr[-1, -1],
        arr[5, 5], arr[5, -6]
    ]
    print(f"Corners: {corners[0]}, {corners[1]}, {corners[4]}")
