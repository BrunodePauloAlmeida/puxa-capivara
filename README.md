# Site data (`site-data` branch)

The package the site reads from Cloud Storage, kept here with Git LFS so it doesn't weigh down `main`.

- `site-web.tar.gz`: output of `uv run puxa site` (the `data/site/web/` folder). The current package predates the
  English translation and still uses the Portuguese format (`indice.json`, `pessoas/`, `fotos/`); the publish
  workflow converts it. New packages have `meta.json`, `index.json`, `people/{id}.json`, `photos/{id}.jpg` and
  `pdf/{id}.pdf`.
- Current version: v1, generated on November 1, 2026, 862 people. Draft: data still being validated.

To publish to the bucket: Actions > **Publish site data** > Run workflow (see `docs/deploy.md` on `main`).

To update: regenerate with the pipeline, replace `site-web.tar.gz` on this branch and push.

```bash
tar -czf site-web.tar.gz -C data/site/web .
```
