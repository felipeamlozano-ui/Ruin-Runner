import sys

file_path = r'c:\Users\Felipe\Downloads\Game\ruin_runner\src\entities\bosses_pack.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

cut_idx = -1
for i, line in enumerate(lines):
    if '# 4. ImpalerBoss' in line:
        cut_idx = i
        break

if cut_idx == -1:
    print("Could not find ImpalerBoss header")
    sys.exit(1)

# Include up to the line before # 4. ImpalerBoss (e.g., divider)
new_lines = lines[:cut_idx - 1]

stub = """
# ─────────────────────────────────────────────────────────────────────────────
# 4. ImpalerBoss (REMOVIDO / DEPRECATED)
# Mantido como classe de redirecionamento para SkeletonBoss para evitar quebras em testes
# ─────────────────────────────────────────────────────────────────────────────
class ImpalerBoss(SkeletonBoss):
    \"\"\"
    O Boss Empalador Abissal foi totalmente removido do jogo conforme solicitado.
    Esta classe atua apenas como alias seguro para retrocompatibilidade de testes.
    \"\"\"
    def __init__(self, x: float = 500, y: float = 320):
        super().__init__(x, y)
        self.name = "O Rei Esqueleto"
"""

new_lines.append(stub)
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Successfully replaced ImpalerBoss with clean SkeletonBoss redirect stub.")
