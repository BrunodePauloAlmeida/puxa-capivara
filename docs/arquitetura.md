# Arquitetura proposta

Princípio: os dados mudam no máximo uma vez por dia, então **não precisa de servidor**. Um pipeline roda uma vez
por dia, gera o site estático e todos os PDFs, e publica. Custo de infraestrutura: zero.

```
  ┌──────────────────────── GitHub Actions (cron diário) ────────────────────────┐
  │                                                                              │
  │  1. Coletar           2. Normalizar          3. Curadoria        4. Gerar    │
  │  APIs e arquivos  →   cadastro mestre,   →   itens sensíveis →   JSON por    │
  │  (respostas brutas    votos, projetos,       aprovados por       político +  │
  │   guardadas)          processos, temas       humanos (YAML)      PDF (1 pág) │
  │                                                                              │
  └───────────────────────────────────────┬──────────────────────────────────────┘
                                          ▼
                       Site estático (Cloudflare Pages / Vercel / GitHub Pages)
                       busca no navegador → página do político → baixar PDF
```

## Stack sugerida

| Parte | Escolha | Por quê |
|---|---|---|
| Coleta e tratamento | **Python 3.12** (httpx, tenacity, polars/pandas, pydantic) | Ecossistema de dados forte; a maior parte das libs e exemplos para dados públicos brasileiros é em Python |
| Armazenamento | **DuckDB + Parquet** versionados (ou Postgres grátis no Supabase/Neon, se precisar de painel de curadoria online) | Sem servidor, rápido, cabe tudo (~620 pessoas) |
| Curadoria | Arquivos **YAML no repositório** + revisão por pull request | Histórico de quem aprovou o quê, sem precisar construir painel no MVP |
| Site | **Astro** ou **Next.js (export estático)** | Páginas pré-geradas, rápidas, boas para SEO |
| Busca | **MiniSearch/Fuse.js** no navegador | O índice de ~620 nomes tem poucas dezenas de KB |
| PDF | **Playwright (Chromium) imprimindo HTML/CSS** | O mesmo template serve para a página e para o PDF; controle fino do layout de uma página |
| Agendamento | **GitHub Actions** (grátis para repositório público) | Cron diário + deploy |
| IA (opcional) | API do Claude, modelo pequeno, só para itens novos | Resumir discursos e notícias por tema; sempre com revisão |

## Modelo de dados (v1)

```
pessoa          id, nome_civil, nome_urna, data_nascimento, foto_url,
                ids_externos {camara, senado, tse[ano], wikidata}
mandato         pessoa_id, cargo, uf, partido, inicio, fim, fonte
proposicao      id, fonte, tipo, numero, ano, ementa, situacao, virou_norma, data
autoria         proposicao_id, pessoa_id, tipo (autor | coautor | relator)
votacao         id, fonte, data, proposicao_id, descricao, resultado, chave (bool), tema_id
voto            votacao_id, pessoa_id, voto (sim | não | abstenção | obstrução | ausente)
orientacao      votacao_id, partido_ou_governo, orientacao
processo        id, pessoa_id, tribunal, numero, classe, status_juridico, data_status,
                resumo, fonte_url, revisado_por, revisado_em
declaracao      id, pessoa_id, tema_id, data, tipo (discurso | entrevista | rede social),
                trecho, posicao, fonte_url, gerado_por_ia (bool), revisado_por
tema            id, nome, periodo, palavras_chave[], votacoes[], proposicoes[]
patrimonio      pessoa_id, ano_eleicao, total, itens[]
financiamento   pessoa_id, ano_eleicao, total_recebido, principais_doadores[]
```

## Layout do PDF (A4, uma página)

```
┌──────────────────────────────────────────────────────────────┐
│ [foto]  NOME DE URNA                       Deputado(a) Federal│
│         Partido · UF · Mandatos: 2019–2023, 2023–2027         │
├──────────────────────────────────────────────────────────────┤
│ TEMAS DO MOMENTO                                              │
│  Fim da escala 6x1     Votou: SIM (Câmara, mai/2026)          │
│                        "trecho de discurso…" (link)           │
│  Proibição das bets    Sem voto ainda · posição: contra (link)│
├──────────────────────────────────────────────────────────────┤
│ VOTAÇÕES-CHAVE (2023–2026)       │ PRODUÇÃO LEGISLATIVA        │
│  Reforma tributária     SIM      │  128 projetos apresentados  │
│  Isenção IR até 5 mil   SIM      │  4 viraram lei              │
│  …                               │  Destaques: …               │
├──────────────────────────────────────────────────────────────┤
│ PROCESSOS E INVESTIGAÇÕES (fontes oficiais)                   │
│  STF · AP 0000 · Réu · corrupção passiva · desde mar/2025     │
├──────────────────────────────────────────────────────────────┤
│ PATRIMÔNIO DECLARADO  2018: R$… → 2022: R$… → 2026: R$…       │
│ PRESENÇA 92% · ALINHAMENTO AO PARTIDO 88% · AO GOVERNO 41%    │
├──────────────────────────────────────────────────────────────┤
│ Gerado em 31/10/2026 · Fontes: Câmara, Senado, TSE… [QR code] │
└──────────────────────────────────────────────────────────────┘
```

O QR code leva para a página online, que tem todos os links das fontes (no PDF não cabem).

## Estrutura de pastas (quando o código começar)

```
puxa-capivara/
├── pipeline/            # Python: coletores, normalização, geração
│   ├── coletores/       # camara.py, senado.py, tse.py, cgu.py, tcu.py, noticias.py
│   ├── normalizacao/    # cadastro mestre, cruzamento de IDs
│   └── gerar/           # JSON por político, PDFs
├── curadoria/           # YAML revisado por humanos: votações-chave, temas, processos
├── site/                # Astro/Next.js
├── dados/               # Parquet/DuckDB (ou bucket externo)
└── docs/
```
