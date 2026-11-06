# Source validation (Phase 0)

Live tests done on November 1, 2026, from the development environment (outside Google Cloud). This document
corrects [`data-sources.md`](data-sources.md) where the initial research was wrong or incomplete.

## Summary

| Source | Result | Notes |
|---|---|---|
| Chamber: API v2 | ✅ Works | 2026 roll-call votes available (the risk flagged earlier **was not confirmed**) |
| Chamber: annual files | ✅ Works | `votacoesVotos-2026.csv` (17.6 MB), updated every day overnight |
| Senate: Dados Abertos | ✅ Works, with deprecated routes | `/plenario/...` and `/materia/...` with a *sunset* on February 1, 2026 (they still respond). Use `/votacao` and `/processo` |
| TSE: open data (CKAN + CDN) | ✅ Works | 2026 already has results and CPF; criminal record certificates published as open data |
| TSE: DivulgaCandContas | ❌ HTTP 403 | Blocked for this environment. Not missed: everything we need is in the open data |
| TCU: lists of responsible officials | ⚠️ Blocked by the TCU firewall | The public API exists (CSV export); test from GCP in São Paulo |
| Wikidata | ✅ Works | Property P7480 = federal deputy ID |
| GDELT | ⚠️ HTTP 429 | Limit of 1 request every 5 s; even when respecting it, this environment was blocked. Test from GCP |
| IBGE Localidades | ⚠️ Connection closed | Not critical: the list of states can be hardcoded |
| LexML | ✅ Responds | Not explored yet |
| Portal da Transparência (CGU) | ⏳ Key missing | The Bitwarden token was not available in this session |
| DataJud (CNJ) | ⏳ Phase 3 | Responds 401 without a key, as expected |

## Câmara dos Deputados (Chamber of Deputies)

- `GET /deputados` returns the **513 deputies in office** on a single page (with `itens=600`). The detail record
  (`/deputados/{id}`) has `cpf`, `nomeCivil`, `dataNascimento`, `escolaridade` and `ultimoStatus.nomeEleitoral`.
- Current legislature: 57 (February 1, 2023 to January 31, 2027).
- **PEC 221/2019 (end of the 6-day work week, fim da escala 6x1)**: bill `2233802`. Status: *Transformado em Norma
  Jurídica* (became law), as **Emenda Constitucional 141/2026** (published in the DOU on October 16, 2026).
  - First round: vote `2233802-424`, May 27, 2026: Sim 472, Não 22, Obstrução 1.
  - Second round: vote `2233802-438`, May 27, 2026: Sim 461, Não 19.
  - `/votacoes/{id}/votos` returns each vote with the deputy; `/votacoes/{id}/orientacoes` returns the guidance of
    each party, bloc, Governo, Oposição and Minoria.
- Speeches (`/deputados/{id}/discursos`) include `sumario`, `keywords` and the full `transcricao`.
- Annual files available and updated on October 31, 2026: `votacoesVotos`, `votacoes`, `votacoesOrientacoes`,
  `eventosPresencaDeputados`, `proposicoesAutores`.

## Senado Federal (Federal Senate)

- The OpenAPI specification is at `/dadosabertos/v3/api-docs` (version 4.1.3, 157 routes, **42 deprecated**).
- Deprecated routes respond with `Deprecation: 18/03/2025`, `Sunset: 01/02/2026` and the successor in the `Link`
  header. The pipeline logs these headers and warns at the end of the run.

| For | Use | Do not use (deprecated) |
|---|---|---|
| Roll-call votes | `/votacao?dataInicio=&dataFim=` or `?codigoParlamentar=` or `?sigla=&numero=&ano=` | `/plenario/lista/votacao/...`, `/senador/{codigo}/votacoes` |
| Bills and authorship | `/processo?codigoParlamentarAutor=` or `?sigla=&numero=&ano=` | `/materia/...`, `/senador/{codigo}/autorias` |
| Rapporteurships | `/processo/relatoria?codigoParlamentar=` | `/senador/{codigo}/relatorias` |
| Party guidance | `/plenario/votacao/orientacaoBancada/{dataInicio}/{dataFim}` | (not deprecated) |
| Speeches | `/senador/{codigo}/discursos` and `/discurso/texto-integral/{codigo}` | (not deprecated) |
| Senators | `/senador/lista/atual`, `/senador/{codigo}` (birth date) | (not deprecated) |

- `/senador/lista/atual`: **81 in office**, flagged as titular or alternate (suplente). No CPF.
- **PEC 221/2019 in the Senate**: process `9056435`, nickname "Fim da escala 6x1", resulting law EC 141 of
  October 16, 2026.
  - First round: voting session `7106`, October 14, 2026. Second round: `7107`, October 14, 2026.
  - In both rounds: Sim 75, Não 1, session chair (art. 51) 1, and the codes `P-NRV` 2, `AP` 1 and `LS` 1 (Senate
    codes for present without a recorded vote, leaves of absence and leaves; the code table has to be handled in
    processing).
  - Each senator's vote comes in the `/votacao` response itself.
- The old routes return XML converted to JSON (a single item becomes an object, not a list); the new ones use
  clean camelCase JSON.

## TSE

- CKAN catalog: `dadosabertos.tse.jus.br/api/3/action/package_show?id=candidatos-2026`. Files on the CDN
  `cdn.tse.jus.br/estatistica/sead/odsele/...`, **updated on October 31, 2026**.
- `consulta_cand_2026.zip` (3.3 MB): 21,017 candidacies, **with the final result**:

| Office | Elected |
|---|---|
| President | 1 (Lula, runoff) |
| Governor | 27 |
| Senator | 54 |
| Federal deputy | 513 (385 by party quotient + 128 by highest averages) |

- The 2026 file has **CPF and birth date**. In the **2018 and 2022 files the CPF is masked (`-4`) and the birth
  date is empty**. That is why matching with earlier elections is by civil name + state.
- **Criminal record certificates** are published as open data (`certidao_criminal_2026_{UF}.zip`), without
  needing DivulgaCandContas. They are large: SP is 2.4 GB and BR (presidential candidates) 69 MB, because they
  include all candidates. In Phase 3, download and extract only those of the politicians in the registry.
- Also available: assets (`bem_candidato`), reasons for removal, social media, government proposals, candidacy
  history and photos per state.

## TCU

- The open data page points to public lists at `certidoes.apps.tcu.gov.br`: officials with irregular accounts,
  the **list for electoral purposes**, disqualified officials and companies barred from public contracts.
- The site uses a public API (`certidoes-apf.apps.tcu.gov.br/api/publico/{lista}/exportar-para-csv`).
- The call from this environment was **blocked by the TCU's web application firewall**. Next step: test from Google
  Cloud in São Paulo. If it is still blocked, download the CSV from the site periodically (the list for electoral
  purposes changes little) or ask the TCU for access.

## Consequences for the project

1. Roll-call votes from both houses are guaranteed via API. The 6x1 PEC can already go into the PDF.
2. The Senate collector must use only the new routes (`/votacao`, `/processo`).
3. The master registry matches the Chamber and the TSE by CPF; the Senate and the TSE by birth date and name;
   2022 governors by civil name and state.
4. Current governors **are not in any API**: the pipeline infers them from those elected in 2022 and from who ran
   for another office in 2026, and curation confirms it (`curation/governors_in_office.yaml`).
5. TCU and GDELT have to be tested from Google Cloud in São Paulo before going into the roadmap as automatic
   sources.

## First run of the master registry (November 1, 2026)

`uv run puxa registry` brought together **862 people**:

| Office | In office | Elected in 2026 |
|---|---|---|
| President | 1 | 1 (the same person) |
| Governor | 27 | 27 |
| Senator | 81 | 54 |
| Federal deputy | 513 | 513 (303 are re-elections of the incumbent) |

- 500 of the 513 deputies in office were linked to their 2026 candidacy; the other 13 are not among the 2026
  candidates (12 checked one by one).
- 49 of the 81 senators in office were linked to TSE 2026 (the others did not run; most have terms until 2031).
- **Governors:** 8 inferred changes (the incumbent ran for the Senate or the Presidency and the vice-governor took
  over): AC, AM, ES, GO, MG, MT, PA and PB. In AM the vice-governor also ran for another office, so who governs
  today needs checking. Leaves of absence and court-ordered removals do not show up in any API and need a manual
  check of all 27.
- 31 open items for review, in `data/processed/registry/issues.csv`.
- Lessons built into the code: also match against candidacies for state deputy (several federal deputies ran for a
  state seat), accept the social name via the ballot name, and fuzzy-match spellings (Souza/Sousa,
  Thereza/Tereza).

## Key votes (collected on November 1, 2026)

Curated list in `curation/key_votes.yaml`; collected with `uv run puxa votes`. The tally computed from the
individual votes matches the official tally of each vote. The outcome comes from the process in the Senate.

| Topic | Chamber (main) | Senate (main) | Outcome |
|---|---|---|---|
| Reforma Tributária (tax reform, PEC 45/2019) | `2196833-326`, Jul 6, 2023: 382 to 118 | `6773`, Nov 8, 2023: 53 to 24 | EC 132/2023 |
| Arcabouço fiscal (fiscal framework, PLP 93/2023) | `2357053-47`, May 23, 2023: 372 to 108 | `6714`, Jun 21, 2023 | LC 200/2023 |
| Marco temporal (PL 490/2007 and PL 2903/2023) | `345311-270`, May 30, 2023: 283 to 155 | `6756`, Sep 27, 2023 | Lei 14.701/2023, with a partial veto |
| Isenção do IR até R$ 5 mil (income tax exemption up to R$ 5,000, PL 1087/2025) | `2487436-169`, Oct 1, 2025: 493 to 0 | no roll-call vote (passed on Nov 5, 2025) | Lei 15.270/2025 |
| PEC da Blindagem (PEC 3/2021) | `2270800-135`, Sep 16, 2025: 353 to 134 | rejected in the CCJ on Sep 24, 2025 | rejected |
| Licenciamento ambiental (environmental licensing, PL 2159/2021) | `257161-454`, Jul 17, 2025: 267 to 116 | `6935`, May 21, 2025 | Lei 15.190/2025, with a partial veto |
| Dosimetria do 8 de janeiro (sentencing for January 8, PL 2162/2023) | `2358548-89`, Dec 10, 2025: 291 to 148 | `7041`, Dec 17, 2025: 48 to 25 | Lei 15.402/2026 (status in the Senate: "vetada", vetoed) |
| Fim da escala 6x1 (end of the 6-day work week, PEC 221/2019) | `2233802-424`, May 27, 2026: 472 to 22 | `7106`, Oct 14, 2026: 75 to 1 | EC 141/2026 |

Notes:
- The Chamber's record count includes whoever chaired the session ("Artigo 17"), who does not vote.
- The Chamber only lists those who recorded a vote. Anyone missing was absent or not in office on that date; the
  PDF has to say "não votou" ("did not vote") without stating the reason.
- The Senate lists all 81 senators, with the reason for any absence. The codes come from the official table
  `/plenario/lista/tiposComparecimento`.
- Party guidance (Chamber): resolved for single parties and federations. Blocs appear abbreviated
  ("Bl UniPpPsd...") and are still left unmatched.

## Legislative output (collected on November 1, 2026)

Collected with `uv run puxa bills`. Window: bills introduced since February 1, 2019. Types: PL, PLP, PEC, PDL and
resolution bills (PRC in the Chamber, PRS in the Senate).

| | Chamber (513) | Senate (81) |
|---|---|---|
| Bills (authorship and co-authorship) | 51,638; median 66 per deputy | 14,279; median 166 per senator |
| As first author | median 37 | median 54 |
| Became law, as first author | 375 in total; at most 18 per person | 291 in total; at most 17 |

Decisions and limitations:
- **The number that is comparable across the two houses is "as first author".** In the Chamber, supporting
  signatures on PECs (171 are required) come with `proponente = 0` and **do not count** as authorship. That is why
  the pipeline's totals are lower than those of the API's `idDeputadoAutor` filter (e.g. Luiz Carlos Motta, PL-SP,
  66 versus 94; the difference is exactly the number of supporting signatures). In the Senate, all signatories
  appear as authors, with no distinction.
- **Law number:** the Chamber's file almost never includes the resulting law (the last dispatch only mentions it in
  30 of 326 cases in 2023, and `urnFinal` is empty). The pipeline looks the law up in the Senate process for the
  highlights: 551 of 565 highlights have the number; the 14 without one are Chamber resolutions (PRC), which do not
  go through the Senate.
- **Attached bills (apensados):** when a bill is attached to another one that becomes law, only the main one shows
  up as "Transformado em Norma Jurídica". The author of the attached bill gets no credit.
- **People who switched houses** only have their output counted for the house they are in now.
- Two senators in office show up with zero bills in the period (alternates who took over recently).
