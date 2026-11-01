# Roadmap até 2030

Atualizado em 01/11/2026. Seis fases levam o projeto dos 862 políticos de hoje (presidente, governadores, senadores e
deputados federais, em exercício e eleitos em 2026) a todos os candidatos do país. O calendário eleitoral é o prazo
fixo: registro de candidaturas em 15/08/2028, 1º turno municipal em 01/10/2028 e 1º turno geral em 06/10/2030.

A versão para patrocinadores, com custos, equipe, governança e riscos, é mantida em documento à parte.

## Já entregue (Fase 0 e início da Fase 1)

- [x] Fontes validadas ao vivo (`validacao-fontes.md`)
- [x] Cadastro mestre com 862 pessoas (`puxa cadastro`)
- [x] Votações-chave: 8 temas, 19 votações nominais (`puxa votacoes`)
- [x] Produção legislativa desde 2019 (`puxa producao`)
- [x] Fotos oficiais e ficha em PDF, rascunho v1 (`puxa fotos`, `puxa ficha`)

## Fase 1: ficha v2 e lançamento público (nov/2026 a jan/2027)

- [ ] Ficha v2: um resumo de verdade, lido em 30 segundos (princípios abaixo), testada com 10 eleitores
- [ ] Patrimônio, doadores e trajetória do TSE para as 862 pessoas
- [ ] Presença, alinhamento ao partido e ao governo, cota parlamentar e emendas
- [ ] Projeto no Google Cloud, site público com busca, página por pessoa, PDF e imagem para celular
- [ ] Atualização diária automática e troca de mandato nas posses (05/01, 06/01 e 01/02/2027)
- [ ] Conferência dos 27 governadores em exercício; revisão dos resumos das votações-chave
- [ ] Teste do TCU e do GDELT a partir do Google Cloud

**Pronto quando:** o site estiver no ar com as 862 fichas v2 antes da posse do Congresso (01/02/2027).

### Princípios da ficha v2
1. No máximo cerca de 120 palavras na página, além dos nomes.
2. Fato = número + rótulo curto; explicação, data e fonte vão para o site.
3. Cinco blocos fixos, na mesma ordem para qualquer cargo: quem é; em 30 segundos (quatro indicadores); como votou ou
   o que entregou; temas do momento; trajetória e dinheiro.
4. Bloco sem dado não aparece.
5. Votos em grade de ícones, com uma legenda só.
6. Rodapé de uma linha com fontes, data e QR code para a página oficial (verificação da ficha).
7. Dois formatos: A4 e imagem vertical para aplicativos de mensagem.

## Fase 2: gestão do presidente e dos governadores (fev a abr/2027)

- [ ] Contas: despesa com pessoal, dívida, investimento e resultado, início e fim do mandato (Tesouro, SICONFI), e
      parecer do tribunal de contas
- [ ] Resultados: educação, saúde, segurança, emprego e renda, início e fim do mandato, ao lado da média nacional
      (IBGE, INEP, DATASUS, Banco Central)
- [ ] Promessas e entregas: plano de governo do TSE resumido por IA com revisão humana
- [ ] Atos: medidas provisórias, vetos, leis e taxa de aprovação dos projetos do governo (presidente); leis e vetos
      onde a assembleia publica dados (governadores)
- [ ] Mandatos anteriores de todos (votos e projetos de legislaturas passadas)
- [ ] Página pública de metodologia

**Pronto quando:** as 28 fichas executivas tiverem as quatro lentes, revisadas por um editor.

## Fase 3: processos, investigações e declarações (mai a jul/2027)

- [ ] Coletores oficiais: certidões criminais do TSE, TCU, CGU (chave no Bitwarden), conselhos de ética
- [ ] Fila de curadoria para STF e STJ; andamento pelo DataJud
- [ ] Discursos e notícias por tema, resumo por IA com revisão; temas do momento configuráveis
- [ ] Canal de correção e direito de resposta (até 48 h); conselho editorial

**Pronto quando:** o bloco de processos estiver publicado para as 862 pessoas, com 100% dos itens revisados e parecer
jurídico favorável.

## Fase 4: municípios, prefeitos e vereadores (ago/2027 a mar/2028)

- [ ] Base do TSE de 2024 para os 5.541 prefeitos e 58.174 vereadores eleitos
- [ ] Gestão dos prefeitos: contas (SICONFI), indicadores do município, parecer do TCE, diários oficiais (Querido Diário)
- [ ] Câmaras municipais: conector para o SAPL (Interlegis) e para capitais com dados abertos
- [ ] Escala: coleta em paralelo por UF (Cloud Run Jobs), BigQuery para bases grandes, busca no servidor, PDF sob
      demanda com cache

**Pronto quando:** todos os prefeitos e vereadores eleitos em 2024 tiverem ficha, com votos e projetos onde a câmara
publica dados.

## Fase 5: eleições municipais de 2028 (abr a dez/2028)

- [ ] Ensaio geral até junho com as 463.681 candidaturas de 2024
- [ ] Ingestão dos registros a partir de 15/08/2028 (a cada hora no período de registro); ficha em até 48 h
- [ ] Capacidade para o pico entre 16/08 e 29/10/2028
- [ ] Revisão jurídica eleitoral e plantão de correções na campanha
- [ ] Eleitos de 2028 viram a base dos mandatos 2029–2032 (posse em 01/01/2029)

**Pronto quando:** 95% dos candidatos tiverem ficha em até 48 h do registro e o site aguentar o pico sem queda.

## Fase 6: eleições gerais de 2030 (2029 a out/2030)

- [ ] Deputados estaduais e distritais, começando pelas assembleias com dados abertos
- [ ] Fichas de todos os candidatos de 2030
- [ ] Comparador de candidatos e alertas por e-mail

**Pronto quando:** 100% dos candidatos registrados em 2030 tiverem ficha antes do 1º turno (06/10/2030).

## Riscos principais

| Risco | Mitigação |
|---|---|
| Ação por calúnia ou difamação | Fonte oficial em cada fato, status jurídico exato, revisão humana, correção em até 48 h |
| Percepção de viés | Metodologia pública, conselho plural, mesmos blocos para todos, cores neutras |
| Dados municipais desiguais | Base do TSE igual para todos; cobertura de cada cidade informada na ficha |
| Mudança ou queda de APIs | Cópia das respostas brutas, aviso de serviço depreciado, arquivos em lote |
| Pico de acesso na campanha | Ensaio com 2024, CDN, PDF sob demanda com cache |
| Fichas falsas circulando | QR code de verificação em cada PDF |
