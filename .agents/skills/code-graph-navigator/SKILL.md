---
name: code-graph-navigator
description: Navegação arquitetural rápida e semântica de código usando o grafo de dependências e Graphify. Use para localizar entidades, loops de renderização, colisões e hierarquia de cenas sem greps textuais genéricos.
---

# Code Graph Navigator

1. **Navegação Top-Down por Grafo:**
   - Para bugs de jogo, trace o fluxo de execução a partir do ciclo principal:
     `Main/Game Loop` -> `SceneManager` -> `CurrentScene.update() / draw()` -> `Entities` -> `Components`.
   - Não realize buscas textuais genéricas (como "circle", "light", "update") em todo o projeto. Vá direto na classe proprietária que renderiza na superfície da cena.
2. **Diagnóstico em Lote:**
   - Mapeie todos os arquivos suspeitos em uma única leitura coordenada antes de iniciar as edições.
