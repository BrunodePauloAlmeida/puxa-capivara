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
