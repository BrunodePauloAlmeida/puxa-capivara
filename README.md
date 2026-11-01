# Dados do site (branch `dados-site`)

Pacote que o site lê do Cloud Storage, guardado aqui com Git LFS para não pesar na `main`.

- `site-web.tar.gz`: saída de `uv run puxa site` (pasta `dados/site/web/`): `meta.json`, `indice.json`,
  `pessoas/{id}.json`, `fotos/{id}.jpg` e `pdf/{id}.pdf`.
- Versão atual: v1, gerada em 01/11/2026, 862 pessoas. Rascunho: dados em validação.

Para publicar no bucket: Actions > **Publicar dados do site** > Run workflow (ver `docs/deploy.md` na `main`).

Para atualizar: gerar de novo com o pipeline, substituir `site-web.tar.gz` neste branch e fazer push.

```bash
tar -czf site-web.tar.gz -C dados/site/web .
```
