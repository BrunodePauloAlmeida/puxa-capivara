"""Federal Senate (Senado): Dados Abertos (no key).

Validated on 01/11/2026. The /plenario/... and /materia/... routes are deprecated (sunset 01/02/2026, still
responding). Use their successors: /votacao (roll-call votes) and /processo (bills and authorship)."""

import json
from pathlib import Path
from typing import Any

from puxa.config import RAW, SENATE_API
from puxa.http import Client


def as_list(value: Any) -> list:
    """The Senate JSON comes from XML: a single item arrives as a dict, several as a list."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def senators_in_office(cli: Client) -> list[dict]:
    body = cli.get_json(f"{SENATE_API}/senador/lista/atual")
    legislators = as_list(body["ListaParlamentarEmExercicio"]["Parlamentares"]["Parlamentar"])
    result = []
    for p in legislators:
        ident = p["IdentificacaoParlamentar"]
        term = p.get("Mandato", {})
        result.append(
            {
                "code": ident["CodigoParlamentar"],
                "name": ident["NomeParlamentar"],
                "full_name": ident["NomeCompletoParlamentar"],
                "party": ident.get("SiglaPartidoParlamentar"),
                "state": ident.get("UfParlamentar"),
                "photo": (ident.get("UrlFotoParlamentar") or "").replace("http://", "https://") or None,
                "participation": term.get("DescricaoParticipacao"),  # Titular / 1º Suplente ...
                "sex": ident.get("SexoParlamentar"),
            }
        )
    return result


def senator_details(cli: Client, code: str, cache: Path | None = RAW / "senate" / "senators") -> dict:
    """Basic data (includes birth date). Stores the raw response on disk."""
    if cache:
        file = cache / f"{code}.json"
        if file.exists():
            return json.loads(file.read_text())
    data = cli.get_json(f"{SENATE_API}/senador/{code}")["DetalheParlamentar"]["Parlamentar"]
    if cache:
        cache.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(data, ensure_ascii=False))
    return data


def roll_calls(cli: Client, **filters: Any) -> list[dict]:
    """Roll-call votes with each senator's vote. Filters: dataInicio, dataFim, sigla, numero, ano,
    codigoParlamentar, idProcesso..."""
    return as_list(cli.get_json(f"{SENATE_API}/votacao", params=filters))


def processes(cli: Client, **filters: Any) -> list[dict]:
    """Bills. Filters: sigla, numero, ano, codigoParlamentarAutor, tramitando..."""
    return as_list(cli.get_json(f"{SENATE_API}/processo", params=filters))
