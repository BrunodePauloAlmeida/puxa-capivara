"""Câmara dos Deputados: API Dados Abertos v2 (sem chave).

Validado em 01/11/2026: /votacoes/{id}/votos traz os votos nominais de 2026 (ex.: PEC 221/2019)."""

import csv
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from puxa.config import BRUTO, CAMARA_API, CAMARA_ARQUIVOS
from puxa.http import Cliente


def _paginar(cli: Cliente, url: str, params: dict[str, Any] | None = None) -> Iterator[dict]:
    proximo: str | None = url
    while proximo:
        corpo = cli.get_json(proximo, params=params)
        yield from corpo["dados"]
        proximo = next((link["href"] for link in corpo.get("links", []) if link["rel"] == "next"), None)
        params = None  # o link "next" já traz os parâmetros


def deputados_em_exercicio(cli: Cliente) -> list[dict]:
    return list(
        _paginar(cli, f"{CAMARA_API}/deputados", {"itens": 100, "ordem": "ASC", "ordenarPor": "nome"})
    )


def fichas_em_lote(cli: Cliente, pasta: Path = BRUTO / "camara") -> dict[int, dict]:
    """Nome civil e data de nascimento de todos os deputados (arquivo anual, um download só).

    Preferível às 513 chamadas a /deputados/{id}, que em 01/11/2026 devolviam 504 com frequência.
    O arquivo não traz CPF (a coluna vem vazia)."""
    arquivo = cli.baixar(f"{CAMARA_ARQUIVOS}/deputados/csv/deputados.csv", pasta / "deputados.csv")
    fichas = {}
    with arquivo.open(encoding="utf-8-sig", newline="") as f:
        for linha in csv.DictReader(f, delimiter=";"):
            id_deputado = int(linha["uri"].rstrip("/").rsplit("/", 1)[1])
            fichas[id_deputado] = {
                "nomeCivil": linha["nomeCivil"],
                "cpf": linha["cpf"] or None,
                "dataNascimento": linha["dataNascimento"] or None,
            }
    return fichas


def ficha_em_cache(id_deputado: int, cache: Path = BRUTO / "camara" / "deputados") -> dict | None:
    """Ficha completa já baixada antes por detalhe_deputado (traz CPF), se existir."""
    arquivo = cache / f"{id_deputado}.json"
    return json.loads(arquivo.read_text()) if arquivo.exists() else None


def detalhe_deputado(
    cli: Cliente, id_deputado: int, cache: Path | None = BRUTO / "camara" / "deputados"
) -> dict:
    """Ficha completa (inclui CPF e data de nascimento). Guarda a resposta bruta em disco."""
    if cache:
        arquivo = cache / f"{id_deputado}.json"
        if arquivo.exists():
            return json.loads(arquivo.read_text())
    dados = cli.get_json(f"{CAMARA_API}/deputados/{id_deputado}")["dados"]
    if cache:
        cache.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(json.dumps(dados, ensure_ascii=False))
    return dados


def votacoes_da_proposicao(cli: Cliente, id_proposicao: int) -> list[dict]:
    return cli.get_json(f"{CAMARA_API}/proposicoes/{id_proposicao}/votacoes")["dados"]


def votos(cli: Cliente, id_votacao: str) -> list[dict]:
    return cli.get_json(f"{CAMARA_API}/votacoes/{id_votacao}/votos")["dados"]


def orientacoes(cli: Cliente, id_votacao: str) -> list[dict]:
    return cli.get_json(f"{CAMARA_API}/votacoes/{id_votacao}/orientacoes")["dados"]
