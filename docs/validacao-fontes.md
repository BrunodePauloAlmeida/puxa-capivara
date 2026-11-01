# Validação das fontes (Fase 0)

Testes feitos ao vivo em 01/11/2026, a partir do ambiente de desenvolvimento (fora do Google Cloud). Este documento
corrige o `fontes-de-dados.md` onde a pesquisa inicial estava errada ou incompleta.

## Resumo

| Fonte | Resultado | Observação |
|---|---|---|
| Câmara: API v2 | ✅ Funciona | Votos nominais de 2026 disponíveis (o risco apontado antes **não se confirmou**) |
| Câmara: arquivos anuais | ✅ Funciona | `votacoesVotos-2026.csv` (17,6 MB), atualizados todo dia de madrugada |
| Senado: Dados Abertos | ✅ Funciona, com rotas depreciadas | `/plenario/...` e `/materia/...` com *sunset* em 01/02/2026 (ainda respondem). Usar `/votacao` e `/processo` |
| TSE: Dados Abertos (CKAN + CDN) | ✅ Funciona | 2026 já tem resultado e CPF; certidões criminais publicadas como dados abertos |
| TSE: DivulgaCandContas | ❌ HTTP 403 | Bloqueado para este ambiente. Não faz falta: tudo o que precisamos está nos Dados Abertos |
| TCU: listas de responsáveis | ⚠️ Bloqueado pelo firewall do TCU | A API pública existe (exportação em CSV); testar a partir do GCP em São Paulo |
| Wikidata | ✅ Funciona | Propriedade P7480 = ID de deputado federal |
| GDELT | ⚠️ HTTP 429 | Limite de 1 requisição a cada 5 s; mesmo respeitando, este ambiente foi barrado. Testar do GCP |
| IBGE Localidades | ⚠️ Conexão encerrada | Não é crítico: a lista de UFs pode ficar fixa no código |
| LexML | ✅ Responde | Ainda não explorado |
| Portal da Transparência (CGU) | ⏳ Falta a chave | O token do Bitwarden não estava disponível nesta sessão |
| DataJud (CNJ) | ⏳ Fase 3 | Responde 401 sem chave, como esperado |

## Câmara dos Deputados

- `GET /deputados` devolve os **513 em exercício** numa página só (com `itens=600`). A ficha (`/deputados/{id}`) traz
  `cpf`, `nomeCivil`, `dataNascimento`, `escolaridade` e `ultimoStatus.nomeEleitoral`.
- Legislatura atual: 57 (01/02/2023 a 31/01/2027).
- **PEC 221/2019 (fim da escala 6x1)**: proposição `2233802`. Situação: *Transformado em Norma Jurídica*, a
  **Emenda Constitucional 141/2026** (DOU de 16/10/2026).
  - 1º turno: votação `2233802-424`, 27/05/2026: Sim 472, Não 22, Obstrução 1.
  - 2º turno: votação `2233802-438`, 27/05/2026: Sim 461, Não 19.
  - `/votacoes/{id}/votos` devolve cada voto com o deputado; `/votacoes/{id}/orientacoes` devolve a orientação de
    cada partido, bloco, Governo, Oposição e Minoria.
- Discursos (`/deputados/{id}/discursos`) trazem `sumario`, `keywords` e `transcricao` completa.
- Arquivos anuais disponíveis e atualizados em 31/10/2026: `votacoesVotos`, `votacoes`, `votacoesOrientacoes`,
  `eventosPresencaDeputados`, `proposicoesAutores`.

## Senado Federal

- A especificação OpenAPI está em `/dadosabertos/v3/api-docs` (versão 4.1.3, 157 rotas, **42 depreciadas**).
- Rotas depreciadas respondem com `Deprecation: 18/03/2025`, `Sunset: 01/02/2026` e o sucessor no header `Link`.
  O pipeline registra esses headers e avisa no fim da execução.

| Para | Usar | Não usar (depreciada) |
|---|---|---|
| Votos nominais | `/votacao?dataInicio=&dataFim=` ou `?codigoParlamentar=` ou `?sigla=&numero=&ano=` | `/plenario/lista/votacao/...`, `/senador/{codigo}/votacoes` |
| Matérias e autoria | `/processo?codigoParlamentarAutor=` ou `?sigla=&numero=&ano=` | `/materia/...`, `/senador/{codigo}/autorias` |
| Relatorias | `/processo/relatoria?codigoParlamentar=` | `/senador/{codigo}/relatorias` |
| Orientação de bancada | `/plenario/votacao/orientacaoBancada/{dataInicio}/{dataFim}` | (não depreciada) |
| Discursos | `/senador/{codigo}/discursos` e `/discurso/texto-integral/{codigo}` | (não depreciadas) |
| Senadores | `/senador/lista/atual`, `/senador/{codigo}` (data de nascimento) | (não depreciadas) |

- `/senador/lista/atual`: **81 em exercício**, com indicação de titular ou suplente. Não traz CPF.
- **PEC 221/2019 no Senado**: processo `9056435`, apelido "Fim da escala 6x1", norma gerada EC 141 de 16/10/2026.
  - 1º turno: sessão de votação `7106`, 14/10/2026. 2º turno: `7107`, 14/10/2026.
  - Nos dois turnos: Sim 75, Não 1, presidente da sessão (art. 51) 1, e os códigos `P-NRV` 2, `AP` 1 e `LS` 1
    (siglas do Senado para presença sem voto registrado, afastamentos e licenças; a tabela de siglas precisa entrar
    no tratamento).
  - O voto de cada senador vem na própria resposta de `/votacao`.
- O formato das rotas antigas é o XML convertido para JSON (um item sozinho vira objeto, não lista); as novas usam
  JSON limpo em camelCase.

## TSE

- Catálogo CKAN: `dadosabertos.tse.jus.br/api/3/action/package_show?id=candidatos-2026`. Arquivos no CDN
  `cdn.tse.jus.br/estatistica/sead/odsele/...`, **atualizados em 31/10/2026**.
- `consulta_cand_2026.zip` (3,3 MB): 21.017 candidaturas, **com o resultado final**:

| Cargo | Eleitos |
|---|---|
| Presidente | 1 (Lula, 2º turno) |
| Governador | 27 |
| Senador | 54 |
| Deputado federal | 513 (385 por quociente partidário + 128 por média) |

- O arquivo de 2026 traz **CPF e data de nascimento**. Nos arquivos de **2018 e 2022 o CPF vem mascarado (`-4`)
  e a data de nascimento vem vazia**. Por isso o cruzamento com eleições anteriores é por nome civil + UF.
- **Certidões criminais** estão publicadas como dados abertos (`certidao_criminal_2026_{UF}.zip`), sem precisar
  do DivulgaCandContas. São grandes: SP tem 2,4 GB e BR (presidenciáveis) 69 MB, porque incluem todos os
  candidatos. Na Fase 3, baixar e extrair só as dos políticos do cadastro.
- Também disponíveis: bens (`bem_candidato`), motivo de cassação, redes sociais, propostas de governo, histórico de
  candidaturas e fotos por UF.

## TCU

- A página de dados abertos aponta para listas públicas em `certidoes.apps.tcu.gov.br`: responsáveis com contas
  irregulares, **lista para fins eleitorais**, inabilitados e inidôneos.
- O site usa uma API pública (`certidoes-apf.apps.tcu.gov.br/api/publico/{lista}/exportar-para-csv`).
- A chamada a partir deste ambiente foi **bloqueada pelo firewall de aplicação do TCU**. Próximo passo: testar do
  Google Cloud em São Paulo. Se continuar bloqueado, baixar o CSV pelo site periodicamente (a lista para fins
  eleitorais muda pouco) ou pedir acesso ao TCU.

## Consequências para o projeto

1. Votos nominais das duas casas estão garantidos por API. A PEC da 6x1 já pode entrar no PDF.
2. O coletor do Senado tem de usar só as rotas novas (`/votacao`, `/processo`).
3. O cadastro mestre cruza Câmara e TSE pelo CPF; Senado e TSE pela data de nascimento e pelo nome; governadores
   de 2022 pelo nome civil e UF.
4. Os governadores atuais **não estão em nenhuma API**: o pipeline infere a partir dos eleitos em 2022 e de quem
   disputou outro cargo em 2026, e a curadoria confirma (`curadoria/governadores_em_exercicio.yaml`).
5. TCU e GDELT precisam ser testados a partir do Google Cloud em São Paulo antes de entrar no roadmap como fontes
   automáticas.

## Primeira execução do cadastro mestre (01/11/2026)

`uv run puxa cadastro` juntou **862 pessoas**:

| Cargo | Em exercício | Eleitos em 2026 |
|---|---|---|
| Presidente | 1 | 1 (a mesma pessoa) |
| Governador | 27 | 27 |
| Senador | 81 | 54 |
| Deputado federal | 513 | 513 (303 são reeleições de quem está no cargo) |

- 500 dos 513 deputados em exercício foram ligados à candidatura de 2026; os 13 restantes não aparecem entre os
  candidatos de 2026 (12 conferidos um a um).
- 49 dos 81 senadores em exercício foram ligados ao TSE 2026 (os outros não disputaram; a maioria tem mandato até 2031).
- **Governadores:** 8 trocas inferidas (titular disputou Senado ou Presidência e o vice assumiu): AC, AM, ES, GO, MG,
  MT, PA e PB. No AM o vice também disputou outro cargo, então é preciso conferir quem governa hoje. Afastamentos
  e cassações judiciais não aparecem em nenhuma API e precisam de conferência manual dos 27.
- 31 pendências para revisão, em `dados/processado/cadastro/pendencias.csv`.
- Lições incorporadas ao código: cruzar também com candidaturas a deputado estadual (vários deputados federais
  disputaram vaga estadual), aceitar nome social pelo nome de urna e aproximar grafias (Souza/Sousa,
  Thereza/Tereza).

## Votações-chave (coletadas em 01/11/2026)

Lista curada em `curadoria/votacoes_chave.yaml`; coleta com `uv run puxa votacoes`. O placar calculado a partir
dos votos individuais bate com o placar oficial de cada votação. O desfecho vem do processo no Senado.

| Tema | Câmara (principal) | Senado (principal) | Desfecho |
|---|---|---|---|
| Reforma Tributária (PEC 45/2019) | `2196833-326`, 06/07/2023: 382 a 118 | `6773`, 08/11/2023: 53 a 24 | EC 132/2023 |
| Arcabouço fiscal (PLP 93/2023) | `2357053-47`, 23/05/2023: 372 a 108 | `6714`, 21/06/2023 | LC 200/2023 |
| Marco temporal (PL 490/2007 e PL 2903/2023) | `345311-270`, 30/05/2023: 283 a 155 | `6756`, 27/09/2023 | Lei 14.701/2023, com veto parcial |
| Isenção do IR até R$ 5 mil (PL 1087/2025) | `2487436-169`, 01/10/2025: 493 a 0 | sem votação nominal (aprovado em 05/11/2025) | Lei 15.270/2025 |
| PEC da Blindagem (PEC 3/2021) | `2270800-135`, 16/09/2025: 353 a 134 | rejeitada na CCJ em 24/09/2025 | rejeitada |
| Licenciamento ambiental (PL 2159/2021) | `257161-454`, 17/07/2025: 267 a 116 | `6935`, 21/05/2025 | Lei 15.190/2025, com veto parcial |
| Dosimetria do 8 de janeiro (PL 2162/2023) | `2358548-89`, 10/12/2025: 291 a 148 | `7041`, 17/12/2025: 48 a 25 | Lei 15.402/2026 (situação no Senado: "vetada") |
| Fim da escala 6x1 (PEC 221/2019) | `2233802-424`, 27/05/2026: 472 a 22 | `7106`, 14/10/2026: 75 a 1 | EC 141/2026 |

Observações:
- O total de registros da Câmara inclui quem presidia a sessão ("Artigo 17"), que não vota.
- A Câmara só lista quem registrou voto. Quem não aparece estava ausente ou não tinha mandato na data; o PDF
  precisa dizer "não votou" sem afirmar o motivo.
- O Senado lista os 81 senadores, com o motivo da ausência. As siglas vêm da tabela oficial
  `/plenario/lista/tiposComparecimento`.
- Orientação de bancada (Câmara): resolvida para partidos isolados e federações. Os blocos aparecem abreviados
  ("Bl UniPpPsd...") e ainda ficam sem correspondência.

## Produção legislativa (coletada em 01/11/2026)

Coleta com `uv run puxa producao`. Janela: projetos apresentados desde 01/02/2019. Tipos: PL, PLP, PEC, PDL e
projeto de resolução (PRC na Câmara, PRS no Senado).

| | Câmara (513) | Senado (81) |
|---|---|---|
| Projetos (autoria e coautoria) | 51.638; mediana 66 por deputado | 14.279; mediana 166 por senador |
| Como primeiro autor | mediana 37 | mediana 54 |
| Viraram norma, como primeiro autor | 375 no total; máximo 18 por pessoa | 291 no total; máximo 17 |

Decisões e limitações:
- **O número comparável entre as Casas é "como primeiro autor".** Na Câmara, assinaturas de apoio a PECs (são
  necessárias 171) vêm com `proponente = 0` e **não contam** como autoria. Por isso os totais do pipeline são
  menores que os do filtro `idDeputadoAutor` da API (ex.: Luiz Carlos Motta, PL-SP, 66 contra 94; a diferença é
  exatamente o número de apoios). No Senado, todos os signatários aparecem como autores, sem distinção.
- **Número da lei:** o arquivo da Câmara quase nunca traz a norma gerada (o último despacho só a cita em 30 de
  326 casos em 2023, e `urnFinal` vem vazio). O pipeline busca a norma no processo do Senado para os destaques:
  551 de 565 destaques têm o número; os 14 sem número são resoluções da Câmara (PRC), que não passam pelo Senado.
- **Projetos apensados:** quando um projeto é anexado a outro que vira lei, só o principal aparece como
  "Transformado em Norma Jurídica". O autor do apensado não recebe crédito.
- **Quem mudou de Casa** só tem contada a produção da Casa em que está agora.
- Dois senadores em exercício aparecem com zero projetos no período (suplentes que assumiram recentemente).
