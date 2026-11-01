# puxa-capivara

Busque um político pelo nome e baixe um PDF de uma página com o resumo da vida pública dele: projetos
apresentados e aprovados, votos nos projetos mais importantes, processos e investigações, patrimônio declarado
e o que ele disse sobre os temas do momento.

**Escopo inicial:** presidente, governadores, deputados federais e senadores.
**Princípio:** só dados públicos, de fontes oficiais e gratuitas, com link para a fonte de cada informação.
**Hospedagem:** Google Cloud (Cloud Run, Cloud Storage, Firebase Hosting), região São Paulo.

## Status

Fase 1 em andamento: cadastro mestre, votações-chave, produção legislativa, a ficha em PDF (rascunho v1) e o site
v1 (busca, ficha e PDF) para as 862 pessoas do cadastro. Fontes validadas ao vivo ([relatório](docs/validacao-fontes.md)).

## Documentação

- [Mapa de fontes de dados](docs/fontes-de-dados.md): APIs públicas gratuitas, o que cada uma entrega e limitações
- [Roadmap](docs/roadmap.md): tudo construído até 31/12/2026, em quatro sprints; depois, operação nas eleições de 2028 e 2030
- [Arquitetura](docs/arquitetura.md): stack, modelo de dados e layout do PDF
- [Deploy](docs/deploy.md): configurar o Google Cloud e o GitHub pelo console e publicar o site
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
uv run puxa fotos         # fotos oficiais (Câmara, Senado ou TSE)
uv run puxa ficha erika-hilton lula   # ficha de uma página em dados/site/pdf/ (ou --todos)
uv run puxa site          # dados do site em dados/site/web/ (índice, fichas em JSON, fotos, PDFs)
```

## Site

Next.js 16 (Node 22). Busca por nome, ficha da pessoa e botão de exportar PDF. Lê os dados de `dados/site/web/`
(gerados por `uv run puxa site`) ou, em produção, do Cloud Storage.

```bash
cd site
npm ci
npm run dev               # http://localhost:3000
npm test                  # testes da busca e da leitura do Cloud Storage
```

Os dados baixados e gerados ficam em `dados/` (fora do Git). Correções manuais ficam em `curadoria/`.

## Licença

MIT
