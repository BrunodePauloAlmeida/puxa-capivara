# Roadmap: everything built by December 31, 2026

Updated on November 1, 2026. All development fits in eight weeks, from November 2 to December 31, 2026: four
two-week sprints and one wrap-up week. After that, the 2028 and 2030 elections are operation of the finished
system, not new construction phases.

The version for sponsors, with costs, team, governance and risks, is kept in a separate document.

## Already delivered

- [x] Sources validated live (`source-validation.md`)
- [x] Master registry with 862 people (`puxa registry`)
- [x] Key votes: 8 topics, 19 roll-call votes (`puxa votes`)
- [x] Legislative output since 2019 (`puxa bills`)
- [x] Official photos and the PDF profile, draft v1 (`puxa photos`, `puxa profile`)

## Sprint 1: profile v2 and the site live (November 2 to 15)

- [ ] Profile v2: a real summary, read in 30 seconds (principles below), tested with 10 voters
- [ ] Assets, donors and TSE career history for the 862 people
- [ ] Attendance, alignment with party and government, parliamentary allowance (cota parlamentar) and budget
      amendments
- [ ] Google Cloud project, public site with search, a page per person, PDF and a mobile image
- [ ] Automatic daily update; check of the 27 governors; review of the key-vote summaries
- [ ] Test TCU and GDELT from Google Cloud

**Done when:** the site is live with the 862 v2 profiles.

### Principles for profile v2
1. At most about 120 words on the page, besides the names.
2. Fact = number + short label; explanation, date and source go on the site.
3. Five fixed blocks, in the same order for any office: who they are; in 30 seconds (four indicators); how they
   voted or what they delivered; hot topics; career and money.
4. A block with no data is not shown.
5. Votes in an icon grid, with a single legend.
6. One-line footer with sources, date and a QR code to the official page (to verify the profile).
7. Two formats: A4 and a vertical image for messaging apps.

## Sprint 2: performance in office of the president and governors (November 16 to 29)

- [ ] Public accounts: personnel spending, debt, investment and fiscal result, at the start and end of the term
      (Tesouro Nacional, SICONFI), and the audit court's opinion
- [ ] Results: education, health, public safety, jobs and income, at the start and end of the term, next to the
      national average (IBGE, INEP, DATASUS, Banco Central)
- [ ] Promises and delivery: the TSE government plan summarized by AI with human review
- [ ] Acts: provisional measures (medidas provisórias), vetoes, laws and the approval rate of the government's
      bills (president); laws and vetoes where the assembly publishes data (governors)
- [ ] Previous terms for everyone and a public methodology page

**Done when:** the 28 executive profiles have all four lenses, reviewed by an editor.

## Sprint 3: everyone elected and every candidate, from the TSE data (November 30 to December 13)

- [ ] Base profile (identity, career, assets, donors, criminal record certificates and government plan) for the
      5,541 mayors and 58,174 city councillors elected in 2024, the state deputies, and all 2024 and 2026
      candidates (about 485,000 candidacies)
- [ ] Mayors' performance: accounts (SICONFI), municipal indicators and official gazettes (Querido Diário)
- [ ] Scale: parallel collection per state (Cloud Run Jobs), BigQuery for the large datasets, server-side search,
      PDF on demand with caching

**Done when:** every person elected or running in 2024 and 2026 has a profile.

## Sprint 4: lawsuits, statements and legislative houses (December 14 to 27)

- [ ] Official lawsuit collectors: TSE criminal record certificates, TCU, CGU (key in Bitwarden), ethics councils
- [ ] Curation queue for STF and STJ; case progress through DataJud
- [ ] Speeches and news by topic, AI summary with review; configurable hot topics
- [ ] Votes and bills from city councils and state assemblies with open data (SAPL and state capitals)
- [ ] Correction and right-of-reply channel (within 48 h)

**Done when:** the lawsuit and statement blocks are published for everyone in office, with a favorable legal
opinion.

## Wrap-up: testing and launch (December 28 to 31)

- [ ] Load test at campaign volume, final review and launch of full coverage

**Done when:** on December 31, 2026 the system is live, updated every day without manual intervention.

## To fit in 2026

- The deadline depends on the team and the Google Cloud project being ready at the start of sprint 1, and on
  development keeping the pace of the prototype, built with AI assistance in two days.
- What depends on third parties does not hold up the launch: if the legal opinion is not out by December 27, the
  lawsuit block comes in January; city councils and assemblies without open data come in over 2027.
- Human curation (STF and STJ lawsuits, review of AI summaries) starts in December and is ongoing.

## After 2026: operation

- **2027:** automatic change of office holders at the inaugurations (January 5, January 6 and February 1); city
  councils and assemblies without open data.
- **2028:** candidate registrations from August 15 (hourly ingestion during that period) and a profile within
  48 h; first round on October 1 and runoff on October 29; those elected take office on January 1, 2029.
- **2030:** the same cycle for the general elections, with the first round on October 6.

## Main risks

| Risk | Mitigation |
|---|---|
| Eight-week deadline | Scope fixed per sprint; what depends on third parties moves to operation without holding up the launch |
| Lawsuit for libel or defamation | Official source for every fact, exact legal status, human review, correction within 48 h |
| Perceived bias | Public methodology, a plural advisory board, the same blocks for everyone, neutral colors |
| Uneven municipal data | The same TSE base for everyone; each city's coverage stated in the profile |
| API changes or outages | Copies of the raw responses, deprecated-service warnings, bulk files |
| Traffic spike during the campaign | Load test in December, CDN, PDF on demand with caching |
| Fake profiles circulating | Verification QR code on every PDF |
