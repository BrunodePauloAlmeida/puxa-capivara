"""Cliente HTTP educado: identifica o projeto, espaça as requisições, repete em falhas temporárias
e registra serviços que o provedor marcou como depreciados (headers Deprecation/Sunset do Senado)."""

import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from puxa.config import USER_AGENT

log = logging.getLogger(__name__)

STATUS_TEMPORARIOS = {429, 500, 502, 503, 504}


def _falha_temporaria(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in STATUS_TEMPORARIOS


_repetir = retry(
    retry=retry_if_exception(_falha_temporaria),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)


class Cliente:
    def __init__(self, intervalo: float = 0.2, transport: httpx.BaseTransport | None = None):
        self.intervalo = intervalo
        self._ultimo = 0.0
        self._http = httpx.Client(
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=httpx.Timeout(60.0, connect=20.0),
            follow_redirects=True,
            transport=transport,
        )
        # rota -> {"deprecation": ..., "sunset": ..., "sucessor": ...}
        self.depreciados: dict[str, dict[str, str | None]] = {}

    def __enter__(self) -> "Cliente":
        return self

    def __exit__(self, *_: object) -> None:
        self._http.close()

    def _esperar(self) -> None:
        falta = self.intervalo - (time.monotonic() - self._ultimo)
        if falta > 0:
            time.sleep(falta)
        self._ultimo = time.monotonic()

    def _checar_depreciacao(self, resposta: httpx.Response) -> None:
        h = resposta.headers
        if "deprecation" not in h and "sunset" not in h:
            return
        rota = resposta.request.url.copy_with(query=None).path
        if rota not in self.depreciados:
            self.depreciados[rota] = {
                "deprecation": h.get("deprecation"),
                "sunset": h.get("sunset"),
                "sucessor": h.get("link"),
            }
            log.warning(
                "Serviço depreciado: %s (sunset %s, sucessor %s)", rota, h.get("sunset"), h.get("link")
            )

    @_repetir
    def get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        self._esperar()
        resposta = self._http.get(url, params=params)
        self._checar_depreciacao(resposta)
        resposta.raise_for_status()
        return resposta.json()

    @_repetir
    def baixar(self, url: str, destino: Path) -> Path:
        """Baixa um arquivo grande. Pula o download se o arquivo local tem o mesmo tamanho e data do servidor."""
        destino.parent.mkdir(parents=True, exist_ok=True)
        meta_path = destino.with_name(destino.name + ".meta.json")
        self._esperar()
        cabecalho = self._http.head(url)
        cabecalho.raise_for_status()
        meta = {
            "url": url,
            "last_modified": cabecalho.headers.get("last-modified"),
            "content_length": cabecalho.headers.get("content-length"),
        }
        if destino.exists() and meta_path.exists() and json.loads(meta_path.read_text()) == meta:
            log.info("Sem mudança, usando cópia local: %s", destino.name)
            return destino
        log.info("Baixando %s", url)
        temporario = destino.with_name(destino.name + ".parcial")
        with self._http.stream("GET", url) as resposta:
            resposta.raise_for_status()
            with temporario.open("wb") as f:
                for bloco in resposta.iter_bytes(1 << 20):
                    f.write(bloco)
        temporario.replace(destino)
        meta_path.write_text(json.dumps(meta))
        return destino
