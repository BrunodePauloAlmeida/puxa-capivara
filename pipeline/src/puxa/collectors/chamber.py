"""Chamber of Deputies (Câmara): Dados Abertos API v2 (no key).

Validated on 01/11/2026: /votacoes/{id}/votos returns the 2026 roll-call votes (e.g. PEC 221/2019)."""

import csv
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from puxa.config import CHAMBER_API, CHAMBER_FILES, RAW
from puxa.http import Client


def _paginate(cli: Client, url: str, params: dict[str, Any] | None = None) -> Iterator[dict]:
    next_url: str | None = url
    while next_url:
        body = cli.get_json(next_url, params=params)
        yield from body["dados"]
        next_url = next((link["href"] for link in body.get("links", []) if link["rel"] == "next"), None)
        params = None  # the "next" link already carries the parameters


def deputies_in_office(cli: Client) -> list[dict]:
    return list(
        _paginate(cli, f"{CHAMBER_API}/deputados", {"itens": 100, "ordem": "ASC", "ordenarPor": "nome"})
    )


def bulk_details(cli: Client, folder: Path = RAW / "chamber") -> dict[int, dict]:
    """Civil name and birth date of every deputy (yearly file, a single download).

    Preferable to the 513 calls to /deputados/{id}, which on 01/11/2026 often returned 504.
    The file has no CPF (the column comes empty)."""
    file = cli.download(f"{CHAMBER_FILES}/deputados/csv/deputados.csv", folder / "deputados.csv")
    details = {}
    with file.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f, delimiter=";"):
            deputy_id = int(row["uri"].rstrip("/").rsplit("/", 1)[1])
            details[deputy_id] = {
                "nomeCivil": row["nomeCivil"],
                "cpf": row["cpf"] or None,
                "dataNascimento": row["dataNascimento"] or None,
                "sexo": row["siglaSexo"] or None,
            }
    return details


def cached_details(deputy_id: int, cache: Path = RAW / "chamber" / "deputies") -> dict | None:
    """Full record previously downloaded by deputy_details (includes CPF), if it exists."""
    file = cache / f"{deputy_id}.json"
    return json.loads(file.read_text()) if file.exists() else None


def deputy_details(cli: Client, deputy_id: int, cache: Path | None = RAW / "chamber" / "deputies") -> dict:
    """Full record (includes CPF and birth date). Stores the raw response on disk."""
    if cache:
        file = cache / f"{deputy_id}.json"
        if file.exists():
            return json.loads(file.read_text())
    data = cli.get_json(f"{CHAMBER_API}/deputados/{deputy_id}")["dados"]
    if cache:
        cache.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(data, ensure_ascii=False))
    return data


def bill_roll_calls(cli: Client, bill_id: int) -> list[dict]:
    return cli.get_json(f"{CHAMBER_API}/proposicoes/{bill_id}/votacoes")["dados"]


def votes(cli: Client, roll_call_id: str) -> list[dict]:
    return cli.get_json(f"{CHAMBER_API}/votacoes/{roll_call_id}/votos")["dados"]


def guidance(cli: Client, roll_call_id: str) -> list[dict]:
    return cli.get_json(f"{CHAMBER_API}/votacoes/{roll_call_id}/orientacoes")["dados"]
