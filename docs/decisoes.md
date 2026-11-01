# Decisões em aberto

Cada item traz a recomendação atual. Quando uma decisão for tomada, registrar aqui a escolha e a data.

## D1. Quem entra: mandatários atuais, eleitos em 2026 ou os dois?
A eleição terminou em 25/10/2026. Os mandatos atuais acabam em jan/fev de 2027, e boa parte dos eleitos ainda não
tem mandato (ex.: deputados novos), então não aparece nas APIs da Câmara e do Senado.
- **Recomendação:** os dois. Cadastro mestre com todos os atuais + todos os eleitos em 2026. Quem é novo tem perfil
  só com TSE e histórico até a posse.
- **Decisão (31/10/2026):** atuais + eleitos em 2026.

## D2. Deputados estaduais entram?
São 1.059 deputados estaduais + 24 distritais, em 27 sistemas diferentes e sem padrão.
- **Recomendação:** fora do MVP. Entram na Fase 5, começando pelas assembleias que têm API.
- **Decisão (31/10/2026):** depois do MVP (Fase 5), começando pelas assembleias com API.

## D3. Uso de IA (pago) para resumir discursos e notícias
As fontes de dados são gratuitas, mas transformar discurso/notícia em "posição sobre o tema" exige um modelo de
linguagem (custo baixo, mas não zero) ou ficar só em votos + trechos achados por palavra-chave.
- **Recomendação:** usar IA com revisão humana antes de publicar e aviso "resumo gerado por IA" no PDF.
- **Decisão (31/10/2026):** usar IA com revisão humana antes de publicar e aviso de conteúdo gerado por IA.

## D4. Regra editorial para acusações e investigações
- **Recomendação:** só publicar com número do processo + tribunal + status jurídico exato + data + link. Itens
  vindos de notícias entram numa fila e só são publicados depois de confirmados em fonte oficial. Mostrar também
  arquivamentos e absolvições. Canal de correção e direito de resposta.
- **Decisão (31/10/2026):** fontes oficiais automáticas + fila de curadoria para itens vindos de notícias e buscas no STF/STJ.

## D5. Quais votações-chave e temas do momento?
Escolher votações é um ato editorial: precisa de critério público e de temas que interessem a todo o espectro.
- **Temas do momento (out/2026):** Fim da escala 6x1 (PEC 221/2019) e Proibição das bets (MP de set/2026 e PL 2.470/2026).
- **Sugestões de votações-chave 2023–2026** (confirmar números e datas na Fase 0): Reforma Tributária (PEC 45/2019),
  Arcabouço Fiscal (PLP 93/2023), Marco Temporal (PL 2.903/2023), Isenção do IR até R$ 5 mil (PL 1.087/2025),
  PEC da Blindagem (PEC 3/2021), Licenciamento ambiental (PL 2.159/2021), dosimetria das penas do 8 de janeiro,
  fim da escala 6x1 (PEC 221/2019).
- **Proposta de critério:** votação nominal em plenário + grande repercussão + alto impacto, revisado a cada semestre.
- **Decisão (01/11/2026):** aprovadas as votações-chave sugeridas e os dois temas do momento.

## D6. Stack e hospedagem
- **Recomendação inicial:** Python no pipeline, site estático (Astro ou Next.js), PDF via Playwright, GitHub Actions
  diário, hospedagem grátis (Cloudflare Pages ou Vercel).
- **Decisão (01/11/2026):** stack aprovada, mas hospedada no **Google Cloud, no mesmo padrão do Observa Custódia**:
  Next.js no Cloud Run com Firebase Hosting na frente, pipeline como Cloud Run Job agendado, Cloud Storage,
  GitHub Actions com Workload Identity Federation e segredos no Bitwarden. Detalhes em `arquitetura.md`.

## D7. Acessos e configuração
- [x] Liberar no ambiente do Claude os domínios listados em `fontes-de-dados.md`, seção 8
- [x] Instalar o app do Claude no GitHub para este repositório
- [x] Chave gratuita da API do Portal da Transparência (CGU), guardada no Bitwarden como `PORTAL_TRANSPARENCIA_API_KEY`
- [ ] Chave pública do DataJud (CNJ), publicada na wiki do DataJud (só na Fase 3)
- [ ] Criar o projeto no Google Cloud com faturamento ativado, Firebase adicionado e Workload Identity Federation
  para o GitHub Actions (passo a passo no roadmap, Fase 0)
- [x] Criar o projeto `puxa-capivara` no Bitwarden Secrets Manager
- [ ] Disponibilizar o token do Bitwarden para o Claude (variável de ambiente `BITWARDEN_ACCESS_TOKEN`, vale a partir de uma sessão nova) e para o CI (secret `BITWARDEN_ACCESS_TOKEN` no GitHub)
