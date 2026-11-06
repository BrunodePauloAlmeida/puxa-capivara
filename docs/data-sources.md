# Data source map

> Research done on October 31, 2026 and **validated live on November 1, 2026**. The test results, with real IDs
> and numbers, are in [`source-validation.md`](source-validation.md), which takes precedence over this document
> wherever they differ.

Confidence legend:
- **High**: official, stable API, used by active projects in 2025–2026.
- **Medium**: exists, but has known limitations or poor documentation.
- **Low**: unofficial, unstable or without programmatic access (requires scraping or manual work).

---

## 1. Summary: what each PDF block needs and where it comes from

| PDF block | Federal deputy | Senator | President | Governor |
|---|---|---|---|---|
| Identification (photo, party, state, terms) | Chamber API | Senate API | TSE | TSE |
| Bills introduced | Chamber API | Senate API | Chamber/Senate (author = Poder Executivo), MPs | ❌ no unified source (27 assemblies) |
| Bills passed | Chamber API (status / resulting law) | Senate API | Chamber/Senate + LexML | ❌ same |
| Votes on important bills | Chamber (annual vote files) | Senate API | n/a (signing/veto via Congress) | n/a |
| Accusations and investigations | TSE, TCU, CGU, Ethics Council, STF (manual) | same | same | TSE, TCU, STJ (manual), TCE |
| Statements on hot topics | Speeches (Chamber API) + news | Speeches (Senate API) + news | News + Planalto speeches | News |
| Assets and campaign funding | TSE | TSE | TSE | TSE |
| Parliamentary allowance spending (optional) | Chamber API | Senate (CSV) | n/a | n/a |

Abbreviations: MP = medida provisória (provisional measure), TCU = Tribunal de Contas da União (federal audit
court), CGU = Controladoria-Geral da União (comptroller general), STF = Supremo Tribunal Federal (supreme court),
STJ = Superior Tribunal de Justiça (superior court of justice), TCE = state audit court.

**Conclusion:** federal deputies and senators have good API coverage. The president is reasonable. Governors and
state deputies **have no unified source**, so their profiles will be shorter or depend on manual curation.

---

## 2. Federal legislature

### 2.1 Câmara dos Deputados (Chamber of Deputies): Dados Abertos (API v2)
- **Base:** `https://dadosabertos.camara.leg.br/api/v2` · Swagger documentation at `/swagger/api.html`
- **Authentication:** none. **Format:** JSON or XML (via the `Accept` header). **Confidence:** High.
- **Main endpoints:**
  - `/deputados` (list; filters by legislature, state, party) and `/deputados/{id}` (includes **CPF**, birth date and photo)
  - `/deputados/{id}/historico`, `/mandatosExternos`, `/ocupacoes`, `/profissoes`, `/orgaos`, `/frentes`
  - `/deputados/{id}/discursos`: floor speeches with **summary, keywords and transcript**. The basis for "statements".
  - `/deputados/{id}/despesas`: parliamentary allowance (CEAP)
  - `/proposicoes?idDeputadoAutor={id}`, `/proposicoes/{id}`, `/autores`, `/tramitacoes`, `/temas`, `/votacoes`
  - `/votacoes`, `/votacoes/{id}`, `/votacoes/{id}/votos`, `/votacoes/{id}/orientacoes` (guidance from each party and the government)
- **Bulk files** (CSV/JSON/XLSX per year): `https://dadosabertos.camara.leg.br/arquivos/{conjunto}/{formato}/{conjunto}-{ano}.{formato}`
  - Useful datasets: `votacoesVotos`, `votacoesOrientacoes`, `votacoesProposicoes`, `proposicoes`, `proposicoesAutores`,
    `eventosPresencaDeputados` (attendance).
- **Known risks:**
  - ✅ A community project reported (January 2026) that `/votacoes/{id}/votos` came back empty after May 2024.
    **Not confirmed**: the votes on PEC 221/2019 (May 2026) come back complete.
  - Rate limiting (HTTP 429) on bursts: use caching, backoff, and prefer the bulk files.
- **Bonus for "investigations":** complaints to the Ethics Council are bills of type `REP`, so they can be fetched
  from the same API.

### 2.2 Senado Federal (Federal Senate): Dados Abertos
- **Base:** `https://legis.senado.leg.br/dadosabertos` · documentation at `/dadosabertos/docs`
- **Authentication:** none. **Format:** XML by default; JSON with `Accept: application/json` (or the `.json` suffix). **Confidence:** High.
- **Main endpoints** (checked against the code of an open-source client updated in June 2026):
  - `/senador/lista/atual`, `/senador/lista/legislatura/{leg}`, `/senador/{codigo}`, `/mandatos`, `/cargos`, `/comissoes`, `/votacoes`
  - `/senador/{codigo}/discursos`: speeches (with a link to the full text)
  - `/materia/pesquisa/lista`, `/materia/{codigo}`, `/materia/{codigo}/textos`, `/materia/{codigo}/votacoes`
  - `/processo/{id}` and sub-routes: newer structure for bills
  - `/plenario/lista/votacao/{ano}`, `/plenario/votacao/{codigo}/votos`
- **Known risks:** the Senate flags services that will be shut down with the HTTP headers `Deprecation`, `Sunset`
  and `Link`. **Confirmed:** 42 of the 157 routes have been deprecated since March 18, 2025, with shutdown planned
  for February 1, 2026 (they still respond), including `/plenario/...`, `/materia/...` and
  `/senador/{codigo}/votacoes`. Use the successors `/votacao` and `/processo` (table in `source-validation.md`).
  The collector logs the headers.
- **Parliamentary allowance (CEAPS):** annual CSV on the Senate's transparency portal (not an API).
- **Congresso Nacional** (joint sessions, vetoes, provisional measures): served by the same infrastructure as the
  Senate.

### 2.3 Optional shortcut: Base dos Dados (BigQuery)
- Already-cleaned tables for the Chamber, the Senate (18 tables), TSE and CGU, ready for SQL.
- **Free** up to 1 TB of queries per month, but requires a Google Cloud account. Great for loading the initial
  history (earlier years) without hitting the APIs thousands of times. **Confidence:** High.

---

## 3. Electoral courts (TSE): all offices

### 3.1 TSE (Tribunal Superior Eleitoral, the Superior Electoral Court) open data portal
- **Base:** `https://dadosabertos.tse.jus.br` (CKAN: search via `api/3/action/package_search`)
- **Authentication:** none. **Format:** zipped CSV per election. **Confidence:** High.
- **Useful files** (the 2018, 2022 and 2026 elections cover the history of everyone currently in office):
  - `consulta_cand_{ano}`: candidacies (office, party, candidacy status, elected or not, occupation, education)
  - `bem_candidato_{ano}`: **declared assets**, item by item (lets us show the evolution 2018 → 2022 → 2026)
  - `prestacao_de_contas_eleitorais_candidatos_{ano}`: campaign revenue (**who donated**) and expenses
  - `motivo_cassacao_{ano}`: reasons for removal or rejection of a candidacy
  - `votacao_candidato_munzona_{ano}`: votes received
  - `rede_social_candidato_{ano}`: declared social media profiles (useful for monitoring statements)
- **Note:** for 2026, the runoff campaign accounts are still being filed (deadline in mid-November).
- **Note:** only the file for the most recent election (2026) includes CPF and birth date. In 2018 and 2022 those
  fields are masked, so matching with older elections is by civil name + state.

### 3.2 DivulgaCandContas
- Official site with a profile for each candidate: photo, assets, government proposals and **criminal record
  certificates** as PDFs.
- It has a JSON API (`divulgacandcontas.tse.jus.br/divulga/rest/v1/...`) used by the site itself, **with no
  official documentation**. In the November 1, 2026 test it returned **HTTP 403**. **Confidence:** Low.
- **Not needed:** the **criminal record certificates** (federal and state courts, first and second instance),
  photos, government proposals and social media are also in the TSE open data, per state. The certificates require
  extracting text from PDFs and the files are large (SP: 2.4 GB).

---

## 4. Executive branch

### 4.1 Presidente da República (President)
- **Executive bills, provisional measures and vetoes:** Chamber and Senate APIs (author = "Poder Executivo").
  **Confidence:** High.
- **Laws and decrees:** LexML (`lexml.gov.br`, SRU search, free). **Confidence:** Medium.
- **Diário Oficial da União (federal official gazette):** INLABS from Imprensa Nacional (daily XML, free sign-up).
  **Confidence:** Medium.
- **Speeches and schedule:** Planalto pages (gov.br) with no API, scraping only. CGU's e-Agendas system publishes
  the schedules of federal officials; **still to check** whether it offers a data export. **Confidence:** Low.

### 4.2 Governors
- **There is no unified source** for acts or bills of the 27 state governments.
- What can be automated: TSE (candidacies, assets, donors, results) and previous terms (many were deputies,
  senators or mayors before, and that history is in the Chamber, Senate and TSE APIs).
- Bills sent to the assemblies and vetoes: depends on each assembly (see 4.3).
- **Proposal:** governor profiles in the MVP with TSE + history + a manually curated topics block.

### 4.3 Assembleias Legislativas (state assemblies; state deputies, if they enter the scope)
- 26 assemblies + the Câmara Legislativa do DF, **each with a different system**. A 2025 study that assessed the
  27 houses points to little standardization: good-quality open data is the exception.
- Some use **SAPL** (the Interlegis/Senate system), which exposes a REST API (`/api/materia/materialegislativa/`
  etc.). That allows one reusable connector for several houses.
- **Confidence:** Low overall. Requires a state-by-state survey.

---

## 5. Accusations, investigations and lawsuits

The most sensitive block and the one with the least API coverage. No free source lets you search for "all lawsuits
of politician X". The solution is to **combine structured official sources with human curation**.

| Source | What it provides | Access | Confidence |
|---|---|---|---|
| **TSE** (candidacy status, `motivo_cassacao`, criminal record certificates) | Rejections (Ficha Limpa), removals from office, declared criminal cases | CSV + PDF | High / Medium |
| **TCU**: accounts ruled irregular (Cadirreg), list for electoral purposes, disqualified officials | Public managers convicted by the TCU | Public API with CSV export (`certidoes-apf.apps.tcu.gov.br`); **the TCU firewall blocked the test**, retry from GCP | Medium |
| **CGU** (Portal da Transparência): CEIS, CNEP, CEAF | Sanctions and dismissals (more companies and civil servants than politicians) | Free API with a **key** (sign-up by email, `chave-api-dados` header) | High |
| **Conselho de Ética** (Ethics Council, Chamber and Senate) | Complaints for breach of parliamentary decorum | Chamber and Senate APIs (type `REP`) | High |
| **STF** (court of jurisdiction for deputies, senators and the president) | Inquiries (INQ), criminal actions (AP), petitions | Search by litigant on the portal (no API); "Corte Aberta" has an aggregated CSV | Low |
| **STJ** (court of jurisdiction for governors) | Inquiries and criminal actions | Search on the portal (no API) | Low |
| **DataJud (CNJ)** | Case progress **by case number** | Free API with a public key. **Does not search by litigant name** (LGPD, the data protection law) | Medium: only useful for following cases already identified |
| **CNJ: registry of people convicted of administrative misconduct (CNCIAI)** | Convictions for misconduct (improbidade) and ineligibility | Web lookup, no API | Low |
| **News** (see section 6) | Federal Police operations, charges filed by the PGR | GDELT/RSS + human review | Medium |

**Proposed editorial rule** (see `decisions.md`): only publish an item with **case number + court + exact legal
status** (under investigation / charged / defendant / convicted at first instance / convicted with a final
judgment / acquitted / dismissed), date and a link to the source. Without that, it does not go into the PDF.

---

## 6. Statements and hot topics

### 6.1 Official sources (free)
- **Floor speeches:** Chamber (`/deputados/{id}/discursos`, with transcript) and Senate (`/senador/{codigo}/discursos`).
  Filter by the topic's keywords (e.g. "6x1", "jornada", "bets", "apostas") and summarize the position.
- **Roll-call votes:** the most objective signal of a position. Each hot topic is linked to one or more votes.
- **Party and government guidance** (Chamber): lets us compute alignment and "voted against the party".

### 6.2 News (free)
- **GDELT DOC 2.0 API** (`api.gdeltproject.org/api/v2/doc/doc`): no key, filters by country (`sourcecountry:BR`)
  and language. Limits: a rolling window of about 3 months and up to 250 results per query. Good for monitoring
  from now on; not useful for history. **Confidence:** Medium.
- **RSS** from Agência Câmara, Agência Senado and Agência Brasil: free and official.
- **Google News RSS:** free, but with no guarantee about the terms of use. Avoid as a primary source.
- **Wikipedia/Wikidata:** free API. Wikidata helps match IDs (Chamber, Senate, TSE) and confirm basic facts.

### 6.3 Social media (outside the free scope)
- X/Twitter: paid API. Instagram/Facebook: no access to third-party profiles. YouTube Data API: free with a quota,
  but would require transcription. Bluesky: free API, little adoption among politicians. **Recommendation:** do
  not use in the MVP.

### 6.4 Hot topics (context as of October 31, 2026, according to the press; confirm in official sources)
- **Fim da escala 6x1 (end of the 6-day work week) — PEC 221/2019** (working week from 44 h to 40 h, with no pay
  cut). The Chamber passed it in May 2026 and the Senate on October 14, 2026, by 75 to 1 in both rounds. It goes on
  to promulgation. **There are roll-call votes in both houses.**
- **Proibição das bets (ban on betting sites).** An MP of September 25, 2026 bans the operation, offering and
  advertising of fixed-odds betting (the press cites MP 1.394/2026; to be confirmed). Congress must vote on it
  within 120 days and it is already being challenged at the STF. There is also PL 2.470/2026 (bans betting
  advertising), approved by the Senate's Science and Technology Committee on September 2, 2026. **There is no
  roll-call floor vote yet**, so for now positions come from speeches and statements.
- **2026 elections:** first round on October 4 and runoff on October 25. According to the press, Lula was
  re-elected against Flávio Bolsonaro (final result to be confirmed with the TSE). The president takes office on
  January 5, 2027 and the governors on January 6, 2027 (rule from EC 111/2021). The new Congress legislature begins
  on February 1, 2027.

---

## 7. Support

- **IBGE Localidades API** (`servicodados.ibge.gov.br`): names and codes of states and municipalities. Free, no key.
- **Official photos:** Chamber (`urlFoto`), Senate (`UrlFotoParlamentar`), TSE (DivulgaCandContas). Use with credit.

---

## 8. Domains used (allowed in Claude's environment on November 1, 2026)

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

## Sources consulted for this research
Link titles are in English; the linked pages are mostly in Portuguese.
- [senado-br-mcp: open-source Senate API client (code, June 2026)](https://github.com/SidneyBissoli/senado-br-mcp)
- [Base dos Dados: Senate pipeline, deprecation headers](https://github.com/basedosdados/pipelines/pull/2254)
- [AgenteCidadaoMCP: limitations of the Chamber API](https://glama.ai/mcp/servers/@gvc2000/AgenteCidadaoMCP/blob/297aa658a904cd3b543a19b2bc88bb929d19cb60/docs/LIMITACOES_API_CAMARA.md)
- [Gist: collecting speeches through the Chamber API v2](https://gist.github.com/fernandobarbalho/a256a2b18e71772528d759ac8c06baeb)
- [CamaraBR (R): annual votacoesVotos files](https://rdrr.io/github/dmarcelinobr/CamaraBR/src/R/loadVotacaoCamara.R)
- [gov.br catalog: Portal da Transparência API](https://www.gov.br/conecta/catalogo/sistemas/controle-e-transparencia)
- [cidadao.ai: integration with Portal da Transparência](https://huggingface.co/spaces/neural-thinker/cidadao.ai-backend/blob/main/docs/api/PORTAL_TRANSPARENCIA_INTEGRATION.md)
- [TCU: open data](https://portal.tcu.gov.br/carta-de-servicos/transparencia/dados-abertos-do-tcu) · [Certificate of accounts ruled irregular for electoral purposes](https://portal.tcu.gov.br/carta-de-servicos/certidoes/certidao-de-contas-julgadas-irregulares-para-fins-eleitorais)
- [DataJud Public API terms of use](https://formularios.cnj.jus.br/wp-content/uploads/2023/11/Termos-de-uso-api-publica-V1.2.pdf) · [DataJud public vs. private comparison](https://judit.io/blog/artigos/datajud-cnj-api-publica-x-privada-comparacao/)
- [CNJ: misconduct registry now includes ineligibility rulings](https://www.cnj.jus.br/cadastro-de-improbidade-passa-a-incluir-decisoes-que-acarretam-inelegibilidade/)
- [SciELO preprint (2025): open data from the state legislative assemblies](https://preprints.scielo.org/index.php/scielo/preprint/view/12275)
- [SAPL: issue about the REST API](https://github.com/interlegis/sapl/issues/2728)
- [GDELT DOC 2.0 API](https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/)
- [TSE: where to look up candidate data (September 2026)](https://www.tse.jus.br/comunicacao/noticias/2026/Setembro/faltam-20-dias-onde-consultar-informacoes-sobre-candidatas-e-candidatos) · [TSE: partial campaign finance reports 2026](https://www.tse.jus.br/comunicacao/noticias/2026/Setembro/tse-disponibiliza-dados-da-prestacao-de-contas-parcial-das-campanhas-eleitorais)
- [Congresso em Foco: Senate passes the 6x1 PEC by 75 to 1](https://www.congressoemfoco.com.br/noticia/123241/por-75-votos-a-um-senado-aprova-pec-do-fim-da-escala-6x1) · [How each senator voted](https://www.congressoemfoco.com.br/noticia/123263/veja-como-cada-senador-votou-na-pec-do-fim-da-escala-6x1) · [Gazeta do Povo](https://www.gazetadopovo.com.br/economia/senado-aprova-pec-do-fim-da-escala-6x1/)
- [O Povo: Lula bans betting sites from October 6](https://mais.opovo.com.br/jornal/economia/2026/09/26/lula-proibe-operacao-de-bets-no-brasil-a-partir-do-dia-6-de-outubro.html) · [Band: betting companies appeal to the STF](https://www.band.com.br/politica/bets-recorrem-ao-stf-contra-mp-de-lula-que-proibiu-apostas-no-pais) · [Jornal do Comércio: Senate CCT approves bill against betting advertising](https://www.jornaldocomercio.com/economia/2026/09/1262069-cct-do-senado-aprova-projeto-que-proibe-propagandas-e-patrocinios-de-bets.html)
- [SBT News: Flávio Bolsonaro and Lula in the runoff](https://sbtnews.sbt.com.br/noticia/eleicoes/flavio-bolsonaro-e-lula-vao-disputar-2-turno) · [Tribuna de Jundiaí: runoff](https://tribunadejundiai.com.br/politica/eleicoes-2026/lula-segundo-turno-eleicoes-2026/)
- [TSE: Resolution 23.732 (AI in campaign advertising)](https://www.tse.jus.br/eleicoes/eleicoes-2024-content/normas-e-documentacoes/arquivos/tse-resolucao-no-23-732-propaganda-alteradora)
