# Arquitetura

Hospedagem no **Google Cloud**, no mesmo padrão do Observa Custódia: site Next.js no Cloud Run, Firebase Hosting na
frente para domínio próprio, HTTPS e CDN, deploy pelo GitHub Actions sem chaves de serviço e segredos no
Bitwarden. A diferença é que aqui os dados mudam todo dia, então existe um **pipeline agendado** que coleta,
processa e gera os PDFs.

Tudo em `southamerica-east1` (São Paulo). Além da latência menor, rodar no Brasil reduz o risco de bloqueio ou
limitação que alguns sites públicos brasileiros aplicam a acessos de fora do país.

```
  Cloud Scheduler (diário)
        │
        ▼
  ┌──────────────── Cloud Run Job: pipeline (Python) ────────────────┐
  │ 1. Coletar        2. Normalizar       3. Curadoria     4. Gerar  │
  │ APIs e arquivos → cadastro mestre, → itens aprovados → JSON por  │
  │ (respostas brutas  votos, projetos,   (YAML do repo)   político +│
  │  guardadas)        processos, temas                    PDF 1 pág │
  └───────┬──────────────────────────────────────────────────┬───────┘
          ▼                                                  ▼
  Cloud Storage: bruto/  processado/ (Parquet)        Cloud Storage: site/ (JSON) e pdf/
                                                             │
          ┌──────────────────────────────────────────────────┘
          ▼
  Cloud Run: frontend (Next.js) ◄── Firebase Hosting (domínio, HTTPS, CDN) ◄── visitante
  Cloud Run: backend (FastAPI): formulário de correção e direito de resposta
```

Ao final de cada execução, o pipeline publica uma nova release do Firebase Hosting, que limpa o cache do CDN (o
Observa Custódia faz o mesmo depois de cada deploy do frontend).

## Componentes

| Parte | Escolha | Observações |
|---|---|---|
| Pipeline | **Python 3.13 + uv**, rodando como **Cloud Run Job** acionado pelo **Cloud Scheduler** | httpx, tenacity, polars, pydantic. O mesmo código roda local com `uv run`. Sem limite de 6h por execução e sem depender de runner nos EUA |
| Armazenamento | **Cloud Storage** (respostas brutas, Parquet, JSON do site, PDFs) | DuckDB lê o Parquet direto para as transformações |
| Dados de apoio | **BigQuery** (opcional) | Consultar as tabelas públicas da Base dos Dados (Câmara, Senado, TSE) no mesmo projeto, para carregar o histórico. Grátis até 1 TB de consulta por mês |
| Frontend | **Next.js** (`output: "standalone"`) em Docker no **Cloud Run** | Página por político, busca, página de metodologia. Lê os JSON do bucket com cache |
| Domínio e CDN | **Firebase Hosting** repassando tudo para o Cloud Run | O Cloud Run não aceita domínio próprio em `southamerica-east1` |
| PDFs | Gerados no pipeline com **Playwright (Chromium)** a partir do mesmo HTML/CSS da página; servidos do Cloud Storage | Pré-gerados: o download é instantâneo e não pesa no Cloud Run |
| Backend | **FastAPI** no **Cloud Run**, com limite de requisições (slowapi) e envio de e-mail | Só para o formulário de correção e direito de resposta no MVP. Depois, painel de curadoria |
| Busca | **MiniSearch** no navegador | Índice pequeno (cerca de 1 mil nomes), gerado pelo pipeline |
| CI/CD | **GitHub Actions** + **Workload Identity Federation** + **Artifact Registry** | Testes antes do deploy: pytest, Vitest, Playwright (fumaça e acessibilidade) |
| Segredos | **Bitwarden Secrets Manager** (`bws`) | Chave da API do Portal da Transparência, chave do DataJud, chave da API do Claude, SMTP. Viram variáveis de ambiente do Cloud Run a cada deploy |
| IA | API do Claude, modelo pequeno, só para itens novos | Resumir discursos e notícias por tema; tudo passa por revisão antes de publicar |
| Curadoria | Arquivos **YAML no repositório**, revisados por pull request | Votações-chave, temas do momento, processos confirmados, posições revisadas |

## Custo
Não é mais custo zero, mas fica perto disso: Cloud Run com `min-instances=0`, um job diário e alguns GB no Cloud
Storage cabem no nível gratuito ou ficam em poucos reais por mês. O projeto precisa de faturamento ativado (o
Firebase Hosting com repasse para o Cloud Run exige o plano Blaze). O maior custo variável tende a ser a IA.

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

### Rascunho v1 (implementado em 01/11/2026)

`uv run puxa ficha <id>` gera `dados/site/html/<id>.html` e `dados/site/pdf/<id>.pdf`. Conteúdo: foto, nome,
cargos, temas do momento, votações-chave e produção legislativa. Patrimônio, processos e declarações entram nas
próximas versões. Escolhas da v1:
- Cores dos votos neutras (azul para Sim, terracota para Não), sem verde e vermelho, para não sugerir certo ou errado.
  O voto também aparece por escrito, então a cor não é a única pista.
- "Sem registro" na Câmara = ausente ou sem mandato na data. A ficha não afirma o motivo.
- Nome civil só quando vem do TSE, que respeita o nome social. O nome de registro da Câmara não aparece.
- Nomes do TSE em maiúsculas são formatados ("TARCÍSIO" → "Tarcísio"); siglas sem vogal ficam ("JHC").
- Se o conteúdo não couber em uma página, a ficha usa uma versão compacta. As 862 fichas couberam.
- Fonte Inter. Na imagem de produção, instalar a fonte e o Chromium (`playwright install chromium`). Neste ambiente,
  o pipeline usa o Chromium pré-instalado (variável `PUXA_CHROMIUM` para apontar outro).
- Fotos embutidas no PDF (média de 180 KB por ficha). Reduzir a resolução das fotos é uma otimização pendente.

## Estrutura de pastas (quando o código começar)

```
puxa-capivara/
├── pipeline/            # Python 3.13 + uv; vira a imagem do Cloud Run Job
│   ├── coletores/       # camara.py, senado.py, tse.py, cgu.py, tcu.py, noticias.py
│   ├── normalizacao/    # cadastro mestre, cruzamento de IDs
│   ├── gerar/           # JSON por político, índice de busca, PDFs
│   └── Dockerfile
├── curadoria/           # YAML revisado por humanos: votações-chave, temas, processos
├── frontend/            # Next.js (standalone) + Dockerfile
├── backend/             # FastAPI: formulário de correção + Dockerfile
├── firebase.json        # Firebase Hosting → Cloud Run
├── scripts/             # get-secrets.sh (Bitwarden → .env local)
├── .github/workflows/   # deploy-frontend.yml, deploy-backend.yml, deploy-pipeline.yml
└── docs/
```
