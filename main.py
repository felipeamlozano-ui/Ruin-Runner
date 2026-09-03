import sys
from pathlib import Path

# Adiciona o diretório src ao PYTHONPATH dinamicamente para imports limpos
sys.path.append(str(Path(__file__).parent / "src"))

from engine.game import Game

def main():
    game = Game()
    game.run()

if __name__ == "__main__":
    main()
