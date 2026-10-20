import os
import sys
from pathlib import Path

# Adiciona o diretório src ao PYTHONPATH dinamicamente para imports limpos
sys.path.append(str(Path(__file__).parent / "src"))

# Motor de renderização definitivo: Vulkan GPU Native (maior 1% Low FPS + menor consumo de CPU)
# Fallback automático para direct3d11 ou opengl gerenciado em engine.system_optimizer
os.environ.setdefault("SDL_RENDER_DRIVER", "vulkan")
os.environ["SDL_RENDER_SCALE_QUALITY"] = "1"  # Hardware linear filtering em VRAM

# Inicialização imediata do Otimizador de Baixo Nível (Vulkan GPU Native + Timer Windows 1ms)
import engine.system_optimizer

from engine.game import Game

def main():
    game = Game()
    game.run()

if __name__ == "__main__":
    main()
