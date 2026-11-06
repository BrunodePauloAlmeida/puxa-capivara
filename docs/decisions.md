# Open decisions

Each item carries the current recommendation. When a decision is made, record the choice and the date here.

## D1. Who is included: current office holders, those elected in 2026, or both?
The election ended on October 25, 2026. Current terms end in January/February 2027, and many of those elected do
not hold office yet (e.g. new deputies), so they do not show up in the Chamber of Deputies (Câmara) and Federal
Senate (Senado) APIs.
- **Recommendation:** both. A master registry with everyone currently in office + everyone elected in 2026.
  Newcomers get a profile with only TSE data and their history until they take office.
- **Decision (October 31, 2026):** current office holders + those elected in 2026.

## D2. Are state deputies included?
There are 1,059 state deputies + 24 district deputies, in 27 different systems with no common standard.
- **Recommendation:** out of the MVP. They come in Phase 5, starting with the assemblies that have an API.
- **Decision (October 31, 2026):** after the MVP (Phase 5), starting with the assemblies that have an API.

## D3. Use of (paid) AI to summarize speeches and news
The data sources are free, but turning a speech or news story into a "position on the topic" requires a language
model (low cost, but not zero) or sticking to votes + excerpts found by keyword.
- **Recommendation:** use AI with human review before publishing and an "AI-generated summary" notice in the PDF.
- **Decision (October 31, 2026):** use AI with human review before publishing and a notice that the content is
  AI-generated.

## D4. Editorial rule for accusations and investigations
- **Recommendation:** publish only with case number + court + exact legal status + date + link. Items that come
  from news go into a queue and are published only after being confirmed in an official source. Also show
  dismissals and acquittals. A channel for corrections and right of reply.
- **Decision (October 31, 2026):** automatic official sources + a curation queue for items that come from news
  and from searches at the STF/STJ.

## D5. Which key votes and hot topics?
Choosing votes is an editorial act: it needs a public criterion and topics that matter across the whole spectrum.
- **Hot topics (October 2026):** Fim da escala 6x1 (end of the 6-day work week, PEC 221/2019) and Proibição das
  bets (ban on betting sites; MP of September 2026 and PL 2.470/2026).
- **Suggested key votes 2023–2026** (confirm numbers and dates in Phase 0): Reforma Tributária (tax reform,
  PEC 45/2019), Arcabouço Fiscal (fiscal framework, PLP 93/2023), Marco Temporal (PL 2.903/2023), Isenção do IR até
  R$ 5 mil (income tax exemption up to R$ 5,000, PL 1.087/2025), PEC da Blindagem (PEC 3/2021), Licenciamento
  ambiental (environmental licensing, PL 2.159/2021), sentencing for January 8 (dosimetria das penas do 8 de
  janeiro), fim da escala 6x1 (PEC 221/2019).
- **Proposed criterion:** roll-call vote on the floor + wide public attention + high impact, reviewed every six
  months.
- **Decision (November 1, 2026):** the suggested key votes and both hot topics were approved.

## D6. Stack and hosting
- **Initial recommendation:** Python for the pipeline, a static site (Astro or Next.js), PDF via Playwright, daily
  GitHub Actions, free hosting (Cloudflare Pages or Vercel).
- **Decision (November 1, 2026):** stack approved, but hosted on **Google Cloud, following the same pattern as
  Observa Custódia**: Next.js on Cloud Run with Firebase Hosting in front, the pipeline as a scheduled Cloud Run
  Job, Cloud Storage, GitHub Actions with Workload Identity Federation, and secrets in Bitwarden. Details in
  `architecture.md`.

## D7. Access and configuration
- [x] Allow the domains listed in `data-sources.md`, section 8, in Claude's environment
- [x] Install the Claude app on GitHub for this repository
- [x] Free Portal da Transparência (CGU) API key, stored in Bitwarden as `PORTAL_TRANSPARENCIA_API_KEY`
- [ ] DataJud (CNJ) public key, published on the DataJud wiki (only in Phase 3)
- [ ] Create the Google Cloud project with billing enabled, Firebase added, and Workload Identity Federation for
  GitHub Actions (step by step in the roadmap, Phase 0)
- [x] Create the `puxa-capivara` project in Bitwarden Secrets Manager
- [ ] Make the Bitwarden token available to Claude (environment variable `BITWARDEN_ACCESS_TOKEN`, takes effect from
  a new session onward) and to CI (the `BITWARDEN_ACCESS_TOKEN` secret on GitHub)
