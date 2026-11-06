"""Polite HTTP client: identifies the project, spaces out requests, retries on transient failures
and records services the provider marked as deprecated (Senate Deprecation/Sunset headers)."""

import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from puxa.config import USER_AGENT

log = logging.getLogger(__name__)

TRANSIENT_STATUS = {429, 500, 502, 503, 504}


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in TRANSIENT_STATUS


_retry = retry(
    retry=retry_if_exception(_is_transient),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)


class Client:
    def __init__(self, interval: float = 0.2, transport: httpx.BaseTransport | None = None):
        self.interval = interval
        self._last = 0.0
        self._http = httpx.Client(
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=httpx.Timeout(60.0, connect=20.0),
            follow_redirects=True,
            transport=transport,
        )
        # route -> {"deprecation": ..., "sunset": ..., "successor": ...}
        self.deprecated: dict[str, dict[str, str | None]] = {}

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *_: object) -> None:
        self._http.close()

    def _wait(self) -> None:
        remaining = self.interval - (time.monotonic() - self._last)
        if remaining > 0:
            time.sleep(remaining)
        self._last = time.monotonic()

    def _check_deprecation(self, response: httpx.Response) -> None:
        h = response.headers
        if "deprecation" not in h and "sunset" not in h:
            return
        route = response.request.url.copy_with(query=None).path
        if route not in self.deprecated:
            self.deprecated[route] = {
                "deprecation": h.get("deprecation"),
                "sunset": h.get("sunset"),
                "successor": h.get("link"),
            }
            log.warning(
                "Deprecated service: %s (sunset %s, successor %s)", route, h.get("sunset"), h.get("link")
            )

    @_retry
    def get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        self._wait()
        response = self._http.get(url, params=params)
        self._check_deprecation(response)
        response.raise_for_status()
        return response.json()

    @_retry
    def download(self, url: str, dest: Path) -> Path:
        """Downloads a large file. Skips the download if the local file has the same size and date as the server's."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        meta_path = dest.with_name(dest.name + ".meta.json")
        self._wait()
        accept_all = {"Accept": "*/*"}  # image servers reject Accept: application/json (406)
        head = self._http.head(url, headers=accept_all)
        head.raise_for_status()
        meta = {
            "url": url,
            "last_modified": head.headers.get("last-modified"),
            "content_length": head.headers.get("content-length"),
        }
        if dest.exists() and meta_path.exists() and json.loads(meta_path.read_text()) == meta:
            log.info("Unchanged, using local copy: %s", dest.name)
            return dest
        log.info("Downloading %s", url)
        partial = dest.with_name(dest.name + ".partial")
        with self._http.stream("GET", url, headers=accept_all) as response:
            response.raise_for_status()
            with partial.open("wb") as f:
                for chunk in response.iter_bytes(1 << 20):
                    f.write(chunk)
        partial.replace(dest)
        meta_path.write_text(json.dumps(meta))
        return dest
