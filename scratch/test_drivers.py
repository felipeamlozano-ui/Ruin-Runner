import os
import sys
import subprocess

drivers = ["direct3d12", "direct3d11", "vulkan", "opengl", "software"]

for d in drivers:
    code = f"""
import os, sys, pygame
os.environ["SDL_RENDER_DRIVER"] = "{d}"
pygame.init()
try:
    s = pygame.display.set_mode((640, 360), pygame.SCALED | pygame.HIDDEN)
    print("{d}: SUCCESS")
except Exception as e:
    print("{d}: ERROR ->", e)
pygame.quit()
"""
    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    out = p.stdout.strip()
    err = p.stderr.strip()
    print(out if out else f"{d} STDERR: {err}")
