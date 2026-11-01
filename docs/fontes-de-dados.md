# Mapa de fontes de dados

> Pesquisa feita em 31/10/2026 e **validada ao vivo em 01/11/2026**. Os resultados dos testes, com IDs e números
> reais, estão em [`validacao-fontes.md`](validacao-fontes.md), que prevalece sobre este documento onde houver
> diferença.

Legenda de confiança:
- **Alta**: API oficial, estável, usada por projetos ativos em 2025–2026.
- **Média**: existe, mas tem limitações conhecidas ou documentação ruim.
- **Baixa**: não oficial, instável ou sem acesso programático (exige raspagem ou trabalho manual).

---

## 1. Resumo: o que cada bloco do PDF precisa e de onde vem

| Bloco do PDF | Deputado federal | Senador | Presidente | Governador |
|---|---|---|---|---|
| Identificação (foto, partido, UF, mandatos) | Câmara API | Senado API | TSE | TSE |
| Projetos apresentados | Câmara API | Senado API | Câmara/Senado (autor = Poder Executivo), MPs | ❌ sem fonte unificada (27 assembleias) |
| Projetos aprovados | Câmara API (situação / norma gerada) | Senado API | Câmara/Senado + LexML | ❌ idem |
| Votos em projetos importantes | Câmara (arquivos anuais de votos) | Senado API | n/a (sanção/veto via Congresso) | n/a |
| Acusações e investigações | TSE, TCU, CGU, Conselho de Ética, STF (manual) | idem | idem | TSE, TCU, STJ (manual), TCE |
| Declarações sobre temas do momento | Discursos (Câmara API) + notícias | Discursos (Senado API) + notícias | Notícias + discursos do Planalto | Notícias |
| Patrimônio e financiamento de campanha | TSE | TSE | TSE | TSE |
| Gastos com cota parlamentar (opcional) | Câmara API | Senado (CSV) | n/a | n/a |

**Conclusão:** deputados federais e senadores têm boa cobertura por API. Presidente fica razoável. Governadores
e deputados estaduais **não têm fonte unificada**, então o perfil deles vai ser mais curto ou depender de
curadoria manual.

---

## 2. Poder Legislativo federal

### 2.1 Câmara dos Deputados — Dados Abertos (API v2)
- **Base:** `https://dadosabertos.camara.leg.br/api/v2` · documentação Swagger em `/swagger/api.html`
- **Autenticação:** nenhuma. **Formato:** JSON ou XML (via header `Accept`). **Confiança:** Alta.
- **Endpoints principais:**
  - `/deputados` (lista; filtros por legislatura, UF, partido) e `/deputados/{id}` (inclui **CPF**, data de nascimento e foto)
  - `/deputados/{id}/historico`, `/mandatosExternos`, `/ocupacoes`, `/profissoes`, `/orgaos`, `/frentes`
  - `/deputados/{id}/discursos`: discursos em plenário com **sumário, palavras-chave e transcrição**. Base para "declarações".
  - `/deputados/{id}/despesas`: cota parlamentar (CEAP)
  - `/proposicoes?idDeputadoAutor={id}`, `/proposicoes/{id}`, `/autores`, `/tramitacoes`, `/temas`, `/votacoes`
  - `/votacoes`, `/votacoes/{id}`, `/votacoes/{id}/votos`, `/votacoes/{id}/orientacoes` (orientação de cada partido e do governo)
- **Arquivos em lote** (CSV/JSON/XLSX por ano): `https://dadosabertos.camara.leg.br/arquivos/{conjunto}/{formato}/{conjunto}-{ano}.{formato}`
  - Conjuntos úteis: `votacoesVotos`, `votacoesOrientacoes`, `votacoesProposicoes`, `proposicoes`, `proposicoesAutores`,
    `eventosPresencaDeputados` (presença).
- **Riscos conhecidos:**
  - ✅ Um projeto da comunidade relatou (jan/2026) que `/votacoes/{id}/votos` vinha vazio depois de maio/2024.
    **Não se confirmou**: os votos da PEC 221/2019 (maio/2026) vêm completos.
  - Limite de requisições (HTTP 429) em rajadas: usar cache, backoff e preferir arquivos em lote.
- **Bônus para "investigações":** representações no Conselho de Ética são proposições do tipo `REP`, então dá para
  pegar pela mesma API.

### 2.2 Senado Federal — Dados Abertos
- **Base:** `https://legis.senado.leg.br/dadosabertos` · documentação em `/dadosabertos/docs`
- **Autenticação:** nenhuma. **Formato:** XML por padrão; JSON com `Accept: application/json` (ou sufixo `.json`). **Confiança:** Alta.
- **Endpoints principais** (conferidos no código de um cliente aberto atualizado em jun/2026):
  - `/senador/lista/atual`, `/senador/lista/legislatura/{leg}`, `/senador/{codigo}`, `/mandatos`, `/cargos`, `/comissoes`, `/votacoes`
  - `/senador/{codigo}/discursos`: pronunciamentos (com link para o texto integral)
  - `/materia/pesquisa/lista`, `/materia/{codigo}`, `/materia/{codigo}/textos`, `/materia/{codigo}/votacoes`
  - `/processo/{id}` e sub-rotas: estrutura mais nova para matérias
  - `/plenario/lista/votacao/{ano}`, `/plenario/votacao/{codigo}/votos`
- **Riscos conhecidos:** o Senado marca serviços que vão ser desligados com os headers HTTP `Deprecation`, `Sunset`
  e `Link`. **Confirmado:** 42 das 157 rotas estão depreciadas desde 18/03/2025, com desligamento previsto para
  01/02/2026 (ainda respondem), incluindo `/plenario/...`, `/materia/...` e `/senador/{codigo}/votacoes`.
  Usar as sucessoras `/votacao` e `/processo` (tabela em `validacao-fontes.md`). O coletor registra os headers.
- **Cota parlamentar (CEAPS):** CSV anual no portal de transparência do Senado (não é API).
- **Congresso Nacional** (sessões conjuntas, vetos, medidas provisórias): servido pela mesma infraestrutura do Senado.

### 2.3 Atalho opcional: Base dos Dados (BigQuery)
- Tabelas já limpas de Câmara, Senado (18 tabelas), TSE e CGU, prontas para SQL.
- **Grátis** até 1 TB de consulta por mês, mas exige conta Google Cloud. Ótimo para carregar o histórico inicial
  (anos anteriores) sem bater milhares de vezes nas APIs. **Confiança:** Alta.

---

## 3. Justiça Eleitoral (TSE): todos os cargos

### 3.1 Portal de Dados Abertos do TSE
- **Base:** `https://dadosabertos.tse.jus.br` (CKAN: busca por `api/3/action/package_search`)
- **Autenticação:** nenhuma. **Formato:** CSV zipado por eleição. **Confiança:** Alta.
- **Arquivos úteis** (eleições 2018, 2022 e 2026 cobrem o histórico de todos os atuais):
  - `consulta_cand_{ano}`: candidaturas (cargo, partido, situação da candidatura, eleito ou não, ocupação, escolaridade)
  - `bem_candidato_{ano}`: **patrimônio declarado**, item por item (dá para mostrar a evolução 2018 → 2022 → 2026)
  - `prestacao_de_contas_eleitorais_candidatos_{ano}`: receitas (**quem doou**) e despesas de campanha
  - `motivo_cassacao_{ano}`: motivos de cassação/indeferimento
  - `votacao_candidato_munzona_{ano}`: votos recebidos
  - `rede_social_candidato_{ano}`: perfis declarados em redes sociais (útil para monitorar declarações)
- **Atenção:** para 2026, as contas do 2º turno ainda estão sendo entregues (prazo até meados de novembro).
- **Atenção:** só o arquivo da eleição mais recente (2026) traz CPF e data de nascimento. Em 2018 e 2022 esses
  campos vêm mascarados, então o cruzamento com eleições antigas é por nome civil + UF.

### 3.2 DivulgaCandContas
- Site oficial com perfil de cada candidato: foto, bens, propostas de governo e **certidões criminais** em PDF.
- Tem uma API JSON (`divulgacandcontas.tse.jus.br/divulga/rest/v1/...`) usada pelo próprio site, **sem
  documentação oficial**. No teste de 01/11/2026 respondeu **HTTP 403**. **Confiança:** Baixa.
- **Não é necessário:** as **certidões criminais** (Justiça Federal e Estadual, 1º e 2º grau), fotos, propostas de
  governo e redes sociais também estão nos Dados Abertos do TSE, por UF. As certidões exigem extração de texto
  de PDF e os arquivos são grandes (SP: 2,4 GB).

---

## 4. Poder Executivo

### 4.1 Presidente da República
- **Projetos do Executivo, MPs e vetos:** APIs da Câmara e do Senado (autor = "Poder Executivo"). **Confiança:** Alta.
- **Leis e decretos:** LexML (`lexml.gov.br`, busca SRU, gratuita). **Confiança:** Média.
- **Diário Oficial da União:** INLABS da Imprensa Nacional (XML diário, cadastro gratuito). **Confiança:** Média.
- **Discursos e agenda:** páginas do Planalto (gov.br) sem API, só raspagem. O sistema e-Agendas da CGU publica
  agendas de autoridades federais; **falta verificar** se há exportação de dados. **Confiança:** Baixa.

### 4.2 Governadores
- **Não existe fonte unificada** de atos ou projetos dos 27 governos estaduais.
- O que dá para automatizar: TSE (candidaturas, bens, doadores, resultado) e mandatos anteriores (muitos já foram
  deputados, senadores ou prefeitos, e esse histórico está nas APIs da Câmara, do Senado e do TSE).
- Projetos enviados às assembleias e vetos: depende de cada assembleia (ver 4.3).
- **Proposta:** perfil de governador no MVP com TSE + histórico + bloco de temas curado manualmente.

### 4.3 Assembleias Legislativas (deputados estaduais, se entrarem no escopo)
- 26 assembleias + Câmara Legislativa do DF, **cada uma com um sistema diferente**. Um estudo de 2025 que avaliou
  as 27 casas aponta baixa padronização: dados abertos de qualidade são exceção.
- Algumas usam o **SAPL** (sistema do Interlegis/Senado), que expõe uma API REST (`/api/materia/materialegislativa/`
  etc.). Isso permite um conector reaproveitável para várias casas.
- **Confiança:** Baixa no geral. Exige um levantamento estado por estado.

---

## 5. Acusações, investigações e processos

O bloco mais sensível e o com menos API. Nenhuma fonte gratuita permite buscar "todos os processos do político X".
A solução é **combinar fontes oficiais estruturadas com curadoria humana**.

| Fonte | O que traz | Acesso | Confiança |
|---|---|---|---|
| **TSE** (situação da candidatura, `motivo_cassacao`, certidões criminais) | Indeferimentos (Ficha Limpa), cassações, processos criminais declarados | CSV + PDF | Alta / Média |
| **TCU**: contas julgadas irregulares (Cadirreg), lista para fins eleitorais, inabilitados | Gestores condenados pelo TCU | API pública com exportação em CSV (`certidoes-apf.apps.tcu.gov.br`); **o firewall do TCU bloqueou o teste**, repetir a partir do GCP | Média |
| **CGU** (Portal da Transparência): CEIS, CNEP, CEAF | Sanções e expulsões (mais empresas e servidores que políticos) | API gratuita com **chave** (cadastro por e-mail, header `chave-api-dados`) | Alta |
| **Conselho de Ética** (Câmara e Senado) | Representações por quebra de decoro | APIs da Câmara e do Senado (tipo `REP`) | Alta |
| **STF** (foro de deputados, senadores e presidente) | Inquéritos (INQ), ações penais (AP), petições | Busca por parte no portal (sem API); "Corte Aberta" tem CSV agregado | Baixa |
| **STJ** (foro de governadores) | Inquéritos e ações penais | Busca no portal (sem API) | Baixa |
| **DataJud (CNJ)** | Andamento de processos **pelo número** | API gratuita com chave pública. **Não busca por nome de parte** (LGPD) | Média: só serve para acompanhar processos já identificados |
| **CNJ: cadastro de condenados por improbidade (CNCIAI)** | Condenações por improbidade e inelegibilidade | Consulta web, sem API | Baixa |
| **Notícias** (ver seção 6) | Operações da PF, denúncias da PGR | GDELT/RSS + revisão humana | Média |

**Regra editorial proposta** (ver `decisoes.md`): só publicar um item com **número do processo + tribunal + status
jurídico exato** (investigado / denunciado / réu / condenado em 1ª instância / condenado com trânsito em julgado /
absolvido / arquivado), data e link para a fonte. Sem isso, não entra no PDF.

---

## 6. Declarações e temas do momento

### 6.1 Fontes oficiais (grátis)
- **Discursos em plenário:** Câmara (`/deputados/{id}/discursos`, com transcrição) e Senado (`/senador/{codigo}/discursos`).
  Filtrar por palavras-chave do tema (ex.: "6x1", "jornada", "bets", "apostas") e resumir a posição.
- **Votos nominais:** o sinal mais objetivo de posição. Cada tema do momento é ligado a uma ou mais votações.
- **Orientação de bancada e do governo** (Câmara): permite calcular alinhamento e "votou contra o partido".

### 6.2 Notícias (grátis)
- **GDELT DOC 2.0 API** (`api.gdeltproject.org/api/v2/doc/doc`): sem chave, filtra por país (`sourcecountry:BR`)
  e idioma. Limites: janela móvel de cerca de 3 meses e até 250 resultados por consulta. Bom para monitorar daqui
  para frente; não serve para o histórico. **Confiança:** Média.
- **RSS** da Agência Câmara, Agência Senado e Agência Brasil: grátis e oficial.
- **Google News RSS:** grátis, mas sem garantia de termos de uso. Evitar como fonte principal.
- **Wikipedia/Wikidata:** API grátis. Wikidata ajuda a cruzar IDs (Câmara, Senado, TSE) e confirmar dados básicos.

### 6.3 Redes sociais (fora do escopo gratuito)
- X/Twitter: API paga. Instagram/Facebook: sem acesso a perfis de terceiros. YouTube Data API: grátis com cota,
  mas exigiria transcrição. Bluesky: API grátis, pouca adoção entre políticos. **Recomendação:** não usar no MVP.

### 6.4 Temas do momento (contexto em 31/10/2026, segundo a imprensa; confirmar nas fontes oficiais)
- **Fim da escala 6x1 — PEC 221/2019** (jornada de 44h para 40h, sem redução salarial). A Câmara aprovou em maio de
  2026 e o Senado em 14/10/2026, por 75 a 1 nos dois turnos. Segue para promulgação. **Há votos nominais nas
  duas casas.**
- **Proibição das bets.** MP de 25/09/2026 proíbe exploração, oferta e publicidade de apostas de quota fixa (a
  imprensa cita MP 1.394/2026; confirmar). Precisa ser votada pelo Congresso em até 120 dias e já é contestada no
  STF. Também há o PL 2.470/2026 (proíbe publicidade de bets), aprovado na Comissão de Ciência e Tecnologia do
  Senado em 02/09/2026. **Ainda não há votação nominal em plenário**, então por enquanto a posição vem de
  discursos e declarações.
- **Eleições de 2026:** 1º turno em 04/10 e 2º turno em 25/10. Pela imprensa, Lula foi reeleito contra Flávio
  Bolsonaro (resultado final a confirmar no TSE). Posse do presidente em 05/01/2027 e dos governadores em
  06/01/2027 (regra da EC 111/2021). Nova legislatura do Congresso em 01/02/2027.

---

## 7. Apoio

- **IBGE Localidades API** (`servicodados.ibge.gov.br`): nomes e códigos de UF e município. Grátis, sem chave.
- **Fotos oficiais:** Câmara (`urlFoto`), Senado (`UrlFotoParlamentar`), TSE (DivulgaCandContas). Usar com crédito.

---

## 8. Domínios usados (liberados no ambiente do Claude em 01/11/2026)

```
dadosabertos.camara.leg.br
www.camara.leg.br
legis.senado.leg.br
www12.senado.leg.br
dadosabertos.tse.jus.br
cdn.tse.jus.br
divulgacandcontas.tse.jus.br
api.portaldatransparencia.gov.br
portal.tcu.gov.br
contas.tcu.gov.br
api-publica.datajud.cnj.jus.br
api.gdeltproject.org
query.wikidata.org
www.wikidata.org
servicodados.ibge.gov.br
www.lexml.gov.br
sites.tcu.gov.br
certidoes.apps.tcu.gov.br
certidoes-apf.apps.tcu.gov.br
```

---

## Fontes consultadas nesta pesquisa
- [senado-br-mcp: cliente aberto da API do Senado (código, jun/2026)](https://github.com/SidneyBissoli/senado-br-mcp)
- [Base dos Dados: pipeline do Senado, headers de depreciação](https://github.com/basedosdados/pipelines/pull/2254)
- [AgenteCidadaoMCP: limitações da API da Câmara](https://glama.ai/mcp/servers/@gvc2000/AgenteCidadaoMCP/blob/297aa658a904cd3b543a19b2bc88bb929d19cb60/docs/LIMITACOES_API_CAMARA.md)
- [Gist: coleta de discursos via API v2 da Câmara](https://gist.github.com/fernandobarbalho/a256a2b18e71772528d759ac8c06baeb)
- [CamaraBR (R): arquivos anuais votacoesVotos](https://rdrr.io/github/dmarcelinobr/CamaraBR/src/R/loadVotacaoCamara.R)
- [Catálogo gov.br: API do Portal da Transparência](https://www.gov.br/conecta/catalogo/sistemas/controle-e-transparencia)
- [cidadao.ai: integração com o Portal da Transparência](https://huggingface.co/spaces/neural-thinker/cidadao.ai-backend/blob/main/docs/api/PORTAL_TRANSPARENCIA_INTEGRATION.md)
- [TCU: dados abertos](https://portal.tcu.gov.br/carta-de-servicos/transparencia/dados-abertos-do-tcu) · [Certidão de contas irregulares para fins eleitorais](https://portal.tcu.gov.br/carta-de-servicos/certidoes/certidao-de-contas-julgadas-irregulares-para-fins-eleitorais)
- [Termos de uso da API Pública do DataJud](https://formularios.cnj.jus.br/wp-content/uploads/2023/11/Termos-de-uso-api-publica-V1.2.pdf) · [Comparativo DataJud público x privado](https://judit.io/blog/artigos/datajud-cnj-api-publica-x-privada-comparacao/)
- [CNJ: cadastro de improbidade passa a incluir inelegibilidade](https://www.cnj.jus.br/cadastro-de-improbidade-passa-a-incluir-decisoes-que-acarretam-inelegibilidade/)
- [Preprint SciELO (2025): dados abertos das assembleias legislativas](https://preprints.scielo.org/index.php/scielo/preprint/view/12275)
- [SAPL: issue sobre a API REST](https://github.com/interlegis/sapl/issues/2728)
- [GDELT DOC 2.0 API](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/)
- [TSE: onde consultar dados de candidatos (set/2026)](https://www.tse.jus.br/comunicacao/noticias/2026/Setembro/faltam-20-dias-onde-consultar-informacoes-sobre-candidatas-e-candidatos) · [TSE: prestação de contas parcial 2026](https://www.tse.jus.br/comunicacao/noticias/2026/Setembro/tse-disponibiliza-dados-da-prestacao-de-contas-parcial-das-campanhas-eleitorais)
- [Congresso em Foco: Senado aprova PEC da 6x1 por 75 a 1](https://www.congressoemfoco.com.br/noticia/123241/por-75-votos-a-um-senado-aprova-pec-do-fim-da-escala-6x1) · [Como cada senador votou](https://www.congressoemfoco.com.br/noticia/123263/veja-como-cada-senador-votou-na-pec-do-fim-da-escala-6x1) · [Gazeta do Povo](https://www.gazetadopovo.com.br/economia/senado-aprova-pec-do-fim-da-escala-6x1/)
- [O Povo: Lula proíbe bets a partir de 6/10](https://mais.opovo.com.br/jornal/economia/2026/09/26/lula-proibe-operacao-de-bets-no-brasil-a-partir-do-dia-6-de-outubro.html) · [Band: bets recorrem ao STF](https://www.band.com.br/politica/bets-recorrem-ao-stf-contra-mp-de-lula-que-proibiu-apostas-no-pais) · [Jornal do Comércio: CCT aprova PL contra publicidade de bets](https://www.jornaldocomercio.com/economia/2026/09/1262069-cct-do-senado-aprova-projeto-que-proibe-propagandas-e-patrocinios-de-bets.html)
- [SBT News: Flávio Bolsonaro e Lula no 2º turno](https://sbtnews.sbt.com.br/noticia/eleicoes/flavio-bolsonaro-e-lula-vao-disputar-2-turno) · [Tribuna de Jundiaí: 2º turno](https://tribunadejundiai.com.br/politica/eleicoes-2026/lula-segundo-turno-eleicoes-2026/)
- [TSE: Resolução 23.732 (IA em propaganda)](https://www.tse.jus.br/eleicoes/eleicoes-2024-content/normas-e-documentacoes/arquivos/tse-resolucao-no-23-732-propaganda-alteradora)
