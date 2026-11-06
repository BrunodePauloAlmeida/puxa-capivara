"""Paths and URLs used by the pipeline."""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

# Where data lives locally. In production (Cloud Run Job) it will point to a mounted Cloud Storage disk.
DATA = Path(os.environ.get("PUXA_DATA", REPO_ROOT / "data"))
RAW = DATA / "raw"
PROCESSED = DATA / "processed"

CURATION = Path(os.environ.get("PUXA_CURATION", REPO_ROOT / "curation"))

USER_AGENT = "puxa-capivara/0.1 (+https://github.com/BrunodePauloAlmeida/puxa-capivara)"

CHAMBER_API = "https://dadosabertos.camara.leg.br/api/v2"
CHAMBER_FILES = "https://dadosabertos.camara.leg.br/arquivos"
SENATE_API = "https://legis.senado.leg.br/dadosabertos"
TSE_CDN = "https://cdn.tse.jus.br/estatistica/sead/odsele"
