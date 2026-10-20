# Diretrizes de Autonomia e Desempenho do Agente

- O Agente possui autoridade total para investigar, auditar, alterar múltiplos arquivos e rodar todos os testes de regressão do projeto autonomamente.
- O Agente deve priorizar scripts de validação unificados em vez de disparar testes fragmentados linha por linha no terminal.
- Inspeções visuais de imagens (.png) devem ser cirúrgicas: prefira validações automatizadas de superfícies e dimensões via código headless (SDL dummy) para economizar latência de contexto.
