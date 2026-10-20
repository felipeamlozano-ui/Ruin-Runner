---
name: high-throughput-game-auditor
description: Protocolo de alta velocidade e autonomia máxima para desenvolvimento, auditoria visual, física e execução de testes em jogos Pygame/Python. Use para auditar bugs gráficos, colisões, cenas, UI ou validar regressões completas de jogos de forma rápida.
---

# High-Throughput Game Auditor

O Agente tem autorização plena para auditar, refatorar e executar testes completos de ponta a ponta. Para manter a velocidade máxima sem latência excessiva de contexto:

1. **Auditoria Visual Programática (Headless Harness):**
   - Em vez de inspecionar dezenas de capturas de tela brutas (.png) sequencialmente via multimodal (o que satura a janela de contexto), utilize validação programática usando Pygame headless (`SDL_VIDEODRIVER=dummy` ou `pygame.HIDDEN`).
   - Verifique bounding boxes, overlaps de rects, canais alfa e superfícies analiticamente.
   - Gere imagens de validação e diffs no disco para o desenvolvedor, mas só inspecione no chat se houver ambiguidade visual que o código não consiga validar.

2. **Proibição de Loops Fragmentados no Terminal (`python -c`):**
   - Não execute repetidos comandos inline no shell para tentar adivinhar métricas de fontes, quebras de linhas de diálogo ou offsets.
   - Calcule e implemente a lógica analiticamente na classe ou escreva um script de verificação integrado em `scratch/` que valide todos os casos de uma só vez.

3. **Autonomia Forense Mantida:**
   - O agente pode e deve criar scripts de teste unificados (ex: `verify_all_fixes.py`), rodar suítes existentes (`pytest`, `unittest`) e assegurar 0 regressões antes de entregar a tarefa.
