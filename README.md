# Ruin Runner ⚔️

Um jogo de ação e aventura em plataforma 2D de ritmo acelerado desenvolvido em **Python 3.14** e **Pygame Community Edition (pygame-ce)**, combinando combate fluido estilo Action-RPG, iluminação volumétrica com Ray Tracing leve, múltiplos cenários e batalha contra chefe em fases dinâmicas.

---

## 🎮 Controles

| Ação | Teclado | Controle (Gamepad) |
|---|---|---|
| **Mover** | `A` / `D` ou `Setas` | Analógico Esquerdo / D-Pad |
| **Pular / Pulo Duplo** | `Espaço` ou `W` | `A` (Cross) |
| **Ataque Básico** (8 SP) | `J` ou `X` | `X` (Square) |
| **Mergulho com Espada (No ar)** | Pular + `J` | Pular + `X` |
| **Projétil Arcano** (50 MP) | `K` ou `C` | `Y` (Triangle) |
| **Dash Esquiva** (12 SP) | `Q` | `RB` / `R1` |
| **Tempestade de Lâminas AoE** (35 MP) | `E` | `LB` / `L1` |
| **Ultimate Devastador** (100 MP) | `R` | `B` (Circle) |
| **Bloqueio / Escudo** (8 SP/s) | `Shift` | `LT` / `L2` |
| **Menu / Pausa** | `ESC` ou `P` | `Start` / `Options` |

---

## ✨ Destaques e Funcionalidades

- **Sistema de Combate Profundo**:
  - Combos terrestres com consumo tático de Stamina.
  - Ataque aéreo descendente (Plunge Attack) cravando a espada no chão com onda de choque e poeira de impacto.
  - Habilidade **Ultimate no [R]**: consome 100% de mana para congelar o tempo num eclipse, desferir cortes supersônicos em 360°, abalar a tela e causar dano massivo em área.
- **Gráficos e Iluminação Cinematográfica (Ray Tracing Leve)**:
  - Feixes volumétricos (God Rays) com passagem de luz dinâmica pelas árvores da floresta e arcadas das masmorras.
  - Iluminação pontual dinâmica projetada por projéteis, portais mágicos e orbes.
  - Partículas atmosféricas (folhas ao vento na floresta e brasas ancestrais nas catacumbas).
  - Vinheta suave e opções de Anti-Aliasing (HD Suave) ou visual retrô Pixel-Art.
- **Inimigos & Batalha de Chefe Épica**:
  - Lacaios esqueletos com ataque de investida e esqueletos magos que lançam bolas de fogo de vácuo púrpura.
  - Javalis selvagens na floresta com charge agressivo.
  - Chefe **Rei Esqueleto**: 450 HP, múltiplas ondas de invocação, enrage a 50% de vida e queda de poções e itens.
- **Menu de Configurações Gráficas Completo**:
  - Resoluções dinâmicas (1280x720, 1600x900, 1920x1080), Modo Tela Cheia, Ray Tracing, Iluminação Dinâmica, Partículas, Vinheta e Scanlines CRT.

---

## 🚀 Como Instalar e Jogar

### Pré-requisitos
- Python 3.10 ou superior instalado.

### Instalação das dependências
```bash
pip install -r requirements.txt
```

### Iniciar o jogo
```bash
python main.py
```

---

## 🧪 Testes Automatizados
O projeto conta com suíte de testes unitários e de integração validando combate, física, balanceamento e renderização:
```bash
python tests/test_new_features.py
```
