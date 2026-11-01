# Roadmap

Premissas (decididas em 31/10/2026, ver `decisoes.md`): escopo = presidente, governadores, deputados federais e
senadores, **atuais e eleitos em 2026** (cerca de 620 cargos; a união das duas listas fica um pouco maior porque
parte dos eleitos é nova). Deputados estaduais só depois do MVP. IA com revisão humana. Processos com fontes
oficiais + curadoria. Hospedagem no Google Cloud no padrão do Observa Custódia (custo perto de zero).

Durações estimadas para uma pessoa em meio período. Servem para ordenar o trabalho, não são prazo.

---

## Fase 0: Fundação e validação das fontes (1–2 semanas)

Objetivo: ter certeza de que as fontes entregam o que o mapa promete, antes de construir em cima delas.

- [x] Fechar as decisões de escopo em `decisoes.md`
- [x] Criar o repositório no GitHub
- [x] Liberar no ambiente do Claude os domínios da seção 8 de `fontes-de-dados.md`
- [ ] **Google Cloud** (mesmo padrão do Observa Custódia):
  - [ ] Projeto novo com faturamento, região `southamerica-east1`
  - [ ] Artifact Registry, buckets do Cloud Storage (`bruto`, `processado`, `site`, `pdf`)
  - [ ] Service account do CI + Workload Identity Federation ligada a este repositório (sem chave JSON)
  - [ ] Firebase adicionado ao projeto (Hosting) e permissão de release para o CI
  - [ ] Projeto `puxa-capivara` no Bitwarden Secrets Manager + secret `BWS_ACCESS_TOKEN` no GitHub
- [x] Sondagem de cada fonte ao vivo: resultado em `validacao-fontes.md`
- [ ] **Testes críticos:**
  - [x] `/votacoes/{id}/votos` da Câmara traz votos depois de maio/2024? **Sim**
  - [x] Achar as votações da PEC 221/2019 (6x1) na Câmara (maio/2026) e no Senado (14/10/2026) e baixar os votos nominais
  - [x] Senado: quais rotas devolvem headers `Deprecation`/`Sunset` (42 de 157)
  - [x] TSE: `consulta_cand_2026` e `bem_candidato_2026` já publicados com eleitos marcados? **Sim**
  - [ ] TCU: existe exportação em CSV, mas o firewall bloqueou; repetir do GCP
- [ ] **Cadastro mestre de pessoas** (atuais + eleitos em 2026): um ID interno por político, ligado aos IDs da Câmara, do Senado, do TSE (por
  eleição) e do Wikidata. É a base de tudo, porque cada fonte escreve o nome de um jeito.
- [ ] Modelo de dados v1 (ver `arquitetura.md`)
- [ ] Testar Portal da Transparência (chave no Bitwarden), TCU e GDELT a partir do GCP

**Entrega:** relatório de validação + cadastro mestre com os ~620 nomes ligados às fontes.

---

## Fase 1: MVP com Congresso (3–4 semanas)

Objetivo: site no ar com busca e PDF para **deputados federais e senadores**, só com dados objetivos.

- [ ] Coletores: Câmara (deputados, proposições, autorias, votações, votos, discursos) e Senado (idem)
- [ ] Lista curada de **votações-chave** da legislatura 2023–2026, incluindo a PEC da 6x1 (ver `decisoes.md`)
- [ ] Indicadores: projetos apresentados, projetos que viraram lei, presença, alinhamento com o partido e com o governo
- [ ] Blocos do TSE: patrimônio declarado (2018 → 2022 → 2026) e principais doadores
- [ ] Template do PDF de uma página (HTML/CSS → PDF) + página web equivalente
- [ ] Busca por nome (com e sem acento, nome de urna e nome civil)
- [ ] Página de **metodologia e fontes** (como cada número é calculado)
- [ ] Pipeline como Cloud Run Job acionado diariamente pelo Cloud Scheduler
- [ ] Frontend Next.js no Cloud Run + Firebase Hosting; backend FastAPI com o formulário de correção
- [ ] Workflows de deploy no GitHub Actions com testes antes (pytest, Vitest, Playwright)

**Entrega:** site público com cerca de 594 perfis de parlamentares e PDF para download.

---

## Fase 2: Executivo (2 semanas)

- [ ] **Presidente:** MPs editadas, projetos enviados, vetos (e se foram derrubados), leis sancionadas, histórico
  de mandatos, dados do TSE
- [ ] **Governadores:** dados do TSE (patrimônio, doadores, resultado), mandatos anteriores (Câmara/Senado/TSE),
  bloco de temas preenchido por curadoria
- [ ] Ajustar o template do PDF para cargos executivos (sem "votos", com "atos de governo")

---

## Fase 3: Processos e investigações (3–4 semanas)

O bloco mais sensível. Só vai ao ar com regra editorial definida e revisão humana.

- [ ] Coletores automáticos: TSE (situação da candidatura, cassações), CGU (CEIS/CNEP/CEAF), Conselho de Ética
  (representações), TCU (contas irregulares)
- [ ] Extração das certidões criminais do TSE (PDF → texto → lista de processos)
- [ ] Fila de curadoria: itens vindos de notícias e buscas manuais no STF/STJ entram como "pendente" e só são
  publicados depois de alguém confirmar número do processo, tribunal e status
- [ ] Acompanhamento de andamento pelo DataJud (para processos com número conhecido)
- [ ] Canal de **correção e direito de resposta** + registro público de alterações

---

## Fase 4: Declarações e temas do momento (3 semanas)

- [ ] Cadastro de "temas do período" (ex.: Fim da 6x1, Proibição das bets) com palavras-chave e votações ligadas
- [ ] Coleta de discursos (Câmara/Senado) e notícias (GDELT + RSS das agências oficiais)
- [ ] Classificação de posição por tema (a favor / contra / ambíguo / sem manifestação), com trecho citado e link
  - IA faz resumo e classificação; uma pessoa revisa antes de publicar; o PDF mostra o aviso "resumo gerado por IA"
- [ ] Bloco "Temas do momento" no topo do PDF

---

## Fase 5: Escala e evolução (contínuo)

- [ ] Deputados estaduais: começar pelas assembleias com API (SAPL e casas maiores)
- [ ] Histórico de versões do PDF (o que mudou e quando)
- [ ] API pública própria com os dados consolidados
- [ ] Alertas por e-mail quando um político acompanhado vota ou ganha um processo novo
- [ ] Preparação para as eleições de 2028 (municipais) e 2030 (gerais)

---

## Riscos principais

| Risco | Impacto | Mitigação |
|---|---|---|
| Processo por calúnia ou difamação | Alto | Só fontes oficiais, status jurídico exato, revisão humana, direito de resposta |
| Escolha das votações e temas parecer enviesada | Alto | Critério público na página de metodologia; temas de ambos os lados |
| API muda ou sai do ar | Médio | Guardar respostas brutas, alertas de quebra, preferir arquivos em lote |
| Votos recentes da Câmara indisponíveis pela API | Médio | Arquivos anuais `votacoesVotos` |
| Nomes diferentes entre fontes | Médio | Cadastro mestre com IDs cruzados + revisão manual dos casos ambíguos |
| Custo de IA ou do Google Cloud crescer | Baixo | Processar só o que é novo, modelo pequeno, cache; `min-instances=0`; alerta de orçamento no GCP |
| Regras eleitorais em ano de eleição | Médio | Site neutro, sem impulsionamento pago, conteúdo de IA rotulado; consultar advogado eleitoral antes de 2028 |
