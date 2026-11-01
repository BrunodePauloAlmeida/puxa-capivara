# puxa-capivara

Busque um político pelo nome e baixe um PDF de uma página com o resumo da vida pública dele: projetos
apresentados e aprovados, votos nos projetos mais importantes, processos e investigações, patrimônio declarado
e o que ele disse sobre os temas do momento.

**Escopo inicial:** presidente, governadores, deputados federais e senadores.
**Princípio:** só dados públicos, de fontes oficiais e gratuitas, com link para a fonte de cada informação.
**Hospedagem:** Google Cloud (Cloud Run, Cloud Storage, Firebase Hosting), região São Paulo.

## Status

Fase 0: fontes validadas ao vivo ([relatório](docs/validacao-fontes.md)) e primeira versão do pipeline (`pipeline/`),
que monta o cadastro mestre de políticos.

## Documentação

- [Mapa de fontes de dados](docs/fontes-de-dados.md): APIs públicas gratuitas, o que cada uma entrega e limitações
- [Roadmap até 2030](docs/roadmap.md): seis fases, da ficha v2 às eleições municipais de 2028 e gerais de 2030
- [Arquitetura](docs/arquitetura.md): stack, modelo de dados e layout do PDF
- [Validação das fontes](docs/validacao-fontes.md): resultado dos testes ao vivo de cada fonte
- [Decisões](docs/decisoes.md): escolhas de escopo e editoriais

## Pipeline

Python 3.13 + [uv](https://docs.astral.sh/uv/).

```bash
cd pipeline
uv sync
uv run pytest -q          # testes (sem rede)
uv run puxa cadastro      # monta o cadastro mestre em dados/processado/cadastro/
uv run puxa votacoes      # votos das votações-chave (curadoria/votacoes_chave.yaml)
uv run puxa producao      # projetos apresentados e que viraram norma, desde 2019
```

Os dados baixados e gerados ficam em `dados/` (fora do Git). Correções manuais ficam em `curadoria/`.

## Licença

MIT
