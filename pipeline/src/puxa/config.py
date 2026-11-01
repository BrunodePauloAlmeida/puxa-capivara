"""Caminhos e endereços usados pelo pipeline."""

import os
from pathlib import Path

RAIZ_REPO = Path(__file__).resolve().parents[3]

# Onde os dados ficam localmente. Em produção (Cloud Run Job) vai apontar para um disco montado do Cloud Storage.
DADOS = Path(os.environ.get("PUXA_DADOS", RAIZ_REPO / "dados"))
BRUTO = DADOS / "bruto"
PROCESSADO = DADOS / "processado"

CURADORIA = Path(os.environ.get("PUXA_CURADORIA", RAIZ_REPO / "curadoria"))

USER_AGENT = "puxa-capivara/0.1 (+https://github.com/BrunodePauloAlmeida/puxa-capivara)"

CAMARA_API = "https://dadosabertos.camara.leg.br/api/v2"
CAMARA_ARQUIVOS = "https://dadosabertos.camara.leg.br/arquivos"
SENADO_API = "https://legis.senado.leg.br/dadosabertos"
TSE_CDN = "https://cdn.tse.jus.br/estatistica/sead/odsele"
