# Roadmap: tudo construído até 31/12/2026

Atualizado em 01/11/2026. Todo o desenvolvimento cabe em oito semanas, de 02/11 a 31/12/2026: quatro sprints de duas
semanas e uma semana de fechamento. Depois disso, as eleições de 2028 e 2030 são operação do sistema pronto, não novas
fases de construção.

A versão para patrocinadores, com custos, equipe, governança e riscos, é mantida em documento à parte.

## Já entregue

- [x] Fontes validadas ao vivo (`validacao-fontes.md`)
- [x] Cadastro mestre com 862 pessoas (`puxa cadastro`)
- [x] Votações-chave: 8 temas, 19 votações nominais (`puxa votacoes`)
- [x] Produção legislativa desde 2019 (`puxa producao`)
- [x] Fotos oficiais e ficha em PDF, rascunho v1 (`puxa fotos`, `puxa ficha`)

## Sprint 1: ficha v2 e site no ar (02/11 a 15/11)

- [ ] Ficha v2: um resumo de verdade, lido em 30 segundos (princípios abaixo), testada com 10 eleitores
- [ ] Patrimônio, doadores e trajetória do TSE para as 862 pessoas
- [ ] Presença, alinhamento ao partido e ao governo, cota parlamentar e emendas
- [ ] Projeto no Google Cloud, site público com busca, página por pessoa, PDF e imagem para celular
- [ ] Atualização diária automática; conferência dos 27 governadores; revisão dos resumos das votações-chave
- [ ] Teste do TCU e do GDELT a partir do Google Cloud

**Pronto quando:** o site estiver no ar com as 862 fichas v2.

### Princípios da ficha v2
1. No máximo cerca de 120 palavras na página, além dos nomes.
2. Fato = número + rótulo curto; explicação, data e fonte vão para o site.
3. Cinco blocos fixos, na mesma ordem para qualquer cargo: quem é; em 30 segundos (quatro indicadores); como votou ou
   o que entregou; temas do momento; trajetória e dinheiro.
4. Bloco sem dado não aparece.
5. Votos em grade de ícones, com uma legenda só.
6. Rodapé de uma linha com fontes, data e QR code para a página oficial (verificação da ficha).
7. Dois formatos: A4 e imagem vertical para aplicativos de mensagem.

## Sprint 2: gestão do presidente e dos governadores (16/11 a 29/11)

- [ ] Contas: despesa com pessoal, dívida, investimento e resultado, início e fim do mandato (Tesouro, SICONFI), e
      parecer do tribunal de contas
- [ ] Resultados: educação, saúde, segurança, emprego e renda, início e fim do mandato, ao lado da média nacional
      (IBGE, INEP, DATASUS, Banco Central)
- [ ] Promessas e entregas: plano de governo do TSE resumido por IA com revisão humana
- [ ] Atos: medidas provisórias, vetos, leis e taxa de aprovação dos projetos do governo (presidente); leis e vetos
      onde a assembleia publica dados (governadores)
- [ ] Mandatos anteriores de todos e página pública de metodologia

**Pronto quando:** as 28 fichas executivas tiverem as quatro lentes, revisadas por um editor.

## Sprint 3: todos os eleitos e candidatos pela base do TSE (30/11 a 13/12)

- [ ] Ficha base (identidade, trajetória, patrimônio, doadores, certidões e plano de governo) para os 5.541 prefeitos e
      58.174 vereadores eleitos em 2024, os deputados estaduais e todos os candidatos de 2024 e 2026 (cerca de 485 mil
      candidaturas)
- [ ] Gestão dos prefeitos: contas (SICONFI), indicadores do município e diários oficiais (Querido Diário)
- [ ] Escala: coleta em paralelo por UF (Cloud Run Jobs), BigQuery para as bases grandes, busca no servidor, PDF sob
      demanda com cache

**Pronto quando:** qualquer eleito ou candidato de 2024 e 2026 tiver ficha.

## Sprint 4: processos, declarações e casas legislativas (14/12 a 27/12)

- [ ] Coletores oficiais de processos: certidões criminais do TSE, TCU, CGU (chave no Bitwarden), conselhos de ética
- [ ] Fila de curadoria para STF e STJ; andamento pelo DataJud
- [ ] Discursos e notícias por tema, resumo por IA com revisão; temas do momento configuráveis
- [ ] Votos e projetos das câmaras municipais e assembleias com dados abertos (SAPL e capitais)
- [ ] Canal de correção e direito de resposta (até 48 h)

**Pronto quando:** os blocos de processos e declarações estiverem publicados para quem tem mandato, com parecer jurídico
favorável.

## Fechamento: teste e lançamento (28/12 a 31/12)

- [ ] Teste de carga com volume de campanha, revisão final e lançamento da cobertura completa

**Pronto quando:** em 31/12/2026 o sistema estiver no ar, atualizado todo dia sem intervenção manual.

## Para caber em 2026

- O prazo depende de a equipe e o projeto no Google Cloud estarem prontos no início do sprint 1, e de o desenvolvimento
  seguir o ritmo do protótipo, feito com apoio de IA em dois dias.
- O que depende de terceiros não trava o lançamento: se o parecer jurídico não sair até 27/12, o bloco de processos
  entra em janeiro; câmaras e assembleias sem dados abertos entram ao longo de 2027.
- A curadoria humana (processos de STF e STJ, revisão dos resumos de IA) começa em dezembro e segue permanente.

## Depois de 2026: operação

- **2027:** troca de mandato automática nas posses (05/01, 06/01 e 01/02); câmaras e assembleias sem dados abertos.
- **2028:** registros de candidatura a partir de 15/08 (ingestão a cada hora no período) e ficha em até 48 h; 1º turno
  em 01/10 e 2º turno em 29/10; posse dos eleitos em 01/01/2029.
- **2030:** o mesmo ciclo para as eleições gerais, com 1º turno em 06/10.

## Riscos principais

| Risco | Mitigação |
|---|---|
| Prazo de oito semanas | Escopo fechado por sprint; o que depende de terceiros entra na operação sem travar o lançamento |
| Ação por calúnia ou difamação | Fonte oficial em cada fato, status jurídico exato, revisão humana, correção em até 48 h |
| Percepção de viés | Metodologia pública, conselho plural, mesmos blocos para todos, cores neutras |
| Dados municipais desiguais | Base do TSE igual para todos; cobertura de cada cidade informada na ficha |
| Mudança ou queda de APIs | Cópia das respostas brutas, aviso de serviço depreciado, arquivos em lote |
| Pico de acesso na campanha | Teste de carga em dezembro, CDN, PDF sob demanda com cache |
| Fichas falsas circulando | QR code de verificação em cada PDF |
