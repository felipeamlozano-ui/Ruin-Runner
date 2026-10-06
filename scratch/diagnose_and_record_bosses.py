import os
import sys
import math
import subprocess
import shutil

# Headless pygame setup
os.environ["SDL_VIDEODRIVER"] = "dummy"

# Add root and src to path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, os.path.join(ROOT_DIR, "src"))

import pygame
pygame.init()
pygame.display.set_mode((640, 480))

from scenes.boss_scene import BossScene

class MockSceneManager:
    def __init__(self):
        self.current_scene = None
    def change_scene(self, scene):
        self.current_scene = scene

BOSS_TYPES = [
    ("skeleton_king", "Rei Esqueleto"),
    ("demon_slime", "Titã Demoníaco"),
    ("monster_creature", "Monstro Quimérico"),
    ("samurai", "Lorde Samurai"),
    ("impaler", "O Empalador Abissal")
]

OUT_DIR = os.path.abspath("scratch/diagnostics")
os.makedirs(OUT_DIR, exist_ok=True)

ARTIFACT_DIR = r"C:\Users\Felipe\.gemini\antigravity-ide\brain\f10221ee-736e-48a6-bbd4-3e2bbfefb28b"

def run_diagnostic_and_record(boss_type, boss_name):
    print(f"\n==================================================")
    print(f"DIAGNÓSTICO & GRAVAÇÃO: {boss_name} ({boss_type})")
    print(f"==================================================")
    
    sm = MockSceneManager()
    scene = BossScene(sm, boss_type=boss_type)
    
    # Complete dialogue immediately to begin combat
    if scene.dialogue_box:
        scene.dialogue_box.is_finished = True
        
    boss = scene.boss
    player = scene.player
    
    # Frame capture setup
    temp_frames_dir = os.path.join(OUT_DIR, f"frames_{boss_type}")
    if os.path.exists(temp_frames_dir):
        shutil.rmtree(temp_frames_dir)
    os.makedirs(temp_frames_dir, exist_ok=True)
    
    dt = 1.0 / 60.0
    total_frames = 180  # 3 full seconds at 60 FPS
    
    anomaly_ceiling_falls = 0
    anomaly_arena_escapes = 0
    anomaly_inverted_attacks = 0
    anomalies_detected = []
    
    print(f"Posição inicial do Boss: x={boss.rect.x:.1f}, y={boss.rect.y:.1f}, bottom={boss.rect.bottom:.1f}")
    print(f"Posição inicial do Player: x={player.rect.x:.1f}, y={player.rect.y:.1f}, bottom={player.rect.bottom:.1f}")
    
    # Render canvas
    canvas = pygame.Surface((640, 480))
    
    for frame_i in range(total_frames):
        # 1. Smoothly patrol player across arena to test dynamic tracking & side changes
        # Frame 0..60: Player patrols around 180 (left of boss)
        # Frame 60..120: Player crosses smoothly to 520 (right of boss)
        # Frame 120..180: Player crosses back to 220 (left of boss)
        if frame_i < 50:
            target_px = 180.0
        elif frame_i < 70:
            prog = (frame_i - 50) / 20.0
            target_px = 180.0 + (520.0 - 180.0) * prog
        elif frame_i < 130:
            target_px = 520.0
        elif frame_i < 150:
            prog = (frame_i - 130) / 20.0
            target_px = 520.0 - (520.0 - 220.0) * prog
        else:
            target_px = 220.0
            
        player.pos.x = target_px
        player.rect.x = int(player.pos.x)
            
        # 2. Update Scene (Physics, AI, State Machines)
        scene.update(dt)
        
        # 3. Check for Ceiling Fall Bug (rect.bottom snapping to < 100 or pos.y < 0 unexpectedly)
        # Note: Impaler intentional dive starts at target.top - 240, but bottom snapping to 0 was the bug.
        if boss.rect.bottom <= 50 and getattr(boss, "state", "") != "DIVE":
            anomaly_ceiling_falls += 1
            anomalies_detected.append(f"Frame {frame_i}: Boss teleported to ceiling (bottom={boss.rect.bottom})")
            
        # 4. Check Arena Escape Bug
        if boss.rect.right < 0 or boss.rect.left > 640:
            anomaly_arena_escapes += 1
            anomalies_detected.append(f"Frame {frame_i}: Boss escaped screen bounds (x={boss.rect.x})")
            
        # 5. Check Orientation / Inverted Attack Bug
        # An inverted attack occurs when the boss is facing a direction (facing_right),
        # but its attack hitbox is generated behind its back (the Impaler bug).
        hitbox = getattr(boss, "get_attack_hitbox", lambda: None)()
        if hitbox:
            b_facing_right = getattr(boss, "facing_right", False)
            if b_facing_right and hitbox.centerx < boss.rect.centerx:
                anomaly_inverted_attacks += 1
                anomalies_detected.append(f"Frame {frame_i}: Attack hitbox INVERTED! Boss faces RIGHT but attack is BEHIND (left).")
            elif not b_facing_right and hitbox.centerx > boss.rect.centerx:
                anomaly_inverted_attacks += 1
                anomalies_detected.append(f"Frame {frame_i}: Attack hitbox INVERTED! Boss faces LEFT but attack is BEHIND (right).")
                
        # 6. Render frame to canvas
        scene.draw(canvas)
        
        # Add visual diagnostic overlay
        font = pygame.font.SysFont("Arial", 14, bold=True)
        txt1 = font.render(f"BOSS: {boss_name.upper()} | State: {getattr(boss, 'state', 'N/A')}", True, (255, 255, 255))
        txt2 = font.render(f"Pos: ({boss.rect.x:.0f}, {boss.rect.y:.0f}) | FacingRight: {getattr(boss, 'facing_right', False)}", True, (255, 220, 100))
        txt3 = font.render(f"Frame: {frame_i+1}/{total_frames} | Target: ({player.rect.centerx}, {player.rect.centery})", True, (150, 255, 150))
        
        # Draw small HUD box
        hud_box = pygame.Surface((340, 60), pygame.SRCALPHA)
        hud_box.fill((0, 0, 0, 180))
        canvas.blit(hud_box, (10, 10))
        canvas.blit(txt1, (15, 12))
        canvas.blit(txt2, (15, 28))
        canvas.blit(txt3, (15, 46))
        
        # Save frame to disk
        frame_file = os.path.join(temp_frames_dir, f"frame_{frame_i:04d}.png")
        pygame.image.save(canvas, frame_file)
        
    print(f"Simulação de {total_frames} frames concluída!")
    print(f"Métricas de Validação:")
    print(f"  - Quedas anômalas do teto: {anomaly_ceiling_falls}")
    print(f"  - Fugas da arena: {anomaly_arena_escapes}")
    print(f"  - Ataques invertidos: {anomaly_inverted_attacks}")
    if anomalies_detected:
        print(f"  - ALERTA DE ANOMALIAS:")
        for a in anomalies_detected[:5]:
            print(f"      {a}")
    else:
        print(f"  - STATUS: 100% APROVADO! NENHUMA ANOMALIA DETECTADA!")
        
    # Generate MP4 video via ffmpeg
    mp4_out = os.path.join(OUT_DIR, f"boss_diagnostic_{boss_type}.mp4")
    artifact_mp4 = os.path.join(ARTIFACT_DIR, f"boss_diagnostic_{boss_type}.mp4")
    
    cmd = [
        "ffmpeg", "-y",
        "-framerate", "60",
        "-i", os.path.join(temp_frames_dir, "frame_%04d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "22",
        mp4_out
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0:
            print(f"Vídeo MP4 gerado com sucesso: {mp4_out}")
            if os.path.exists(ARTIFACT_DIR):
                shutil.copy2(mp4_out, artifact_mp4)
                print(f"Vídeo copiado para Artifacts: {artifact_mp4}")
        else:
            print(f"Erro ao gerar MP4: {res.stderr.decode('utf-8', errors='ignore')[:300]}")
    except Exception as ex:
        print(f"Exceção no ffmpeg: {ex}")
        
    # Generate high quality preview GIF via ffmpeg for instant visual preview
    gif_out = os.path.join(OUT_DIR, f"boss_preview_{boss_type}.gif")
    artifact_gif = os.path.join(ARTIFACT_DIR, f"boss_preview_{boss_type}.gif")
    cmd_gif = [
        "ffmpeg", "-y",
        "-framerate", "30",
        "-i", os.path.join(temp_frames_dir, "frame_%04d.png"),
        "-vf", "fps=20,scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
        gif_out
    ]
    try:
        res_gif = subprocess.run(cmd_gif, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res_gif.returncode == 0:
            print(f"GIF de preview gerado: {gif_out}")
            if os.path.exists(ARTIFACT_DIR):
                shutil.copy2(gif_out, artifact_gif)
                print(f"GIF copiado para Artifacts: {artifact_gif}")
    except Exception as ex:
        print(f"Exceção no gif: {ex}")
        
    # Clean up frames folder to save disk space
    shutil.rmtree(temp_frames_dir, ignore_errors=True)
    
    return {
        "boss_type": boss_type,
        "boss_name": boss_name,
        "ceiling_falls": anomaly_ceiling_falls,
        "escapes": anomaly_arena_escapes,
        "inverted_attacks": anomaly_inverted_attacks,
        "mp4": mp4_out,
        "gif": gif_out,
        "success": (anomaly_ceiling_falls == 0 and anomaly_arena_escapes == 0 and anomaly_inverted_attacks == 0)
    }

def main():
    results = []
    for b_type, b_name in BOSS_TYPES:
        res = run_diagnostic_and_record(b_type, b_name)
        results.append(res)
        
    print("\n" + "="*60)
    print("RESUMO FINAL DA VALIDAÇÃO 1 A 1 DOS 5 BOSSES:")
    print("="*60)
    all_passed = True
    for r in results:
        status_txt = "APROVADO [SEM ERROS]" if r["success"] else "FALHOU"
        print(f"Boss: {r['boss_name']:<25} | Status: {status_txt}")
        print(f"  -> Quedas do teto: {r['ceiling_falls']} | Fugas: {r['escapes']} | Inversões: {r['inverted_attacks']}")
        print(f"  -> Vídeo: {r['mp4']}")
        if not r["success"]:
            all_passed = False
            
    if all_passed:
        print("\nTODOS OS 5 BOSSES FORAM VALIDADOS COM 100% DE SUCESSO!")
    else:
        print("\nATENÇÃO: Foram encontradas falhas em um ou mais bosses.")

if __name__ == "__main__":
    main()
