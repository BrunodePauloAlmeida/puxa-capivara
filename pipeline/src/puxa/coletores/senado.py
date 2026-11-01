"""Senado Federal: Dados Abertos (sem chave).

Validado em 01/11/2026. Rotas /plenario/... e /materia/... estão depreciadas (sunset 01/02/2026, ainda respondem).
Usar as sucessoras: /votacao (votos nominais) e /processo (matérias e autoria)."""

import json
from pathlib import Path
from typing import Any

from puxa.config import BRUTO, SENADO_API
from puxa.http import Cliente


def como_lista(valor: Any) -> list:
    """O JSON do Senado vem de XML: um único item chega como dicionário, vários como lista."""
    if valor is None:
        return []
    return valor if isinstance(valor, list) else [valor]


def senadores_em_exercicio(cli: Cliente) -> list[dict]:
    corpo = cli.get_json(f"{SENADO_API}/senador/lista/atual")
    parlamentares = como_lista(corpo["ListaParlamentarEmExercicio"]["Parlamentares"]["Parlamentar"])
    resultado = []
    for p in parlamentares:
        ident = p["IdentificacaoParlamentar"]
        mandato = p.get("Mandato", {})
        resultado.append(
            {
                "codigo": ident["CodigoParlamentar"],
                "nome": ident["NomeParlamentar"],
                "nome_completo": ident["NomeCompletoParlamentar"],
                "partido": ident.get("SiglaPartidoParlamentar"),
                "uf": ident.get("UfParlamentar"),
                "foto": (ident.get("UrlFotoParlamentar") or "").replace("http://", "https://") or None,
                "participacao": mandato.get("DescricaoParticipacao"),  # Titular / 1º Suplente ...
                "sexo": ident.get("SexoParlamentar"),
            }
        )
    return resultado


def detalhe_senador(cli: Cliente, codigo: str, cache: Path | None = BRUTO / "senado" / "senadores") -> dict:
    """Dados básicos (inclui data de nascimento). Guarda a resposta bruta em disco."""
    if cache:
        arquivo = cache / f"{codigo}.json"
        if arquivo.exists():
            return json.loads(arquivo.read_text())
    dados = cli.get_json(f"{SENADO_API}/senador/{codigo}")["DetalheParlamentar"]["Parlamentar"]
    if cache:
        cache.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(json.dumps(dados, ensure_ascii=False))
    return dados


def votacoes(cli: Cliente, **filtros: Any) -> list[dict]:
    """Votações nominais com os votos de cada senador. Filtros: dataInicio, dataFim, sigla, numero, ano,
    codigoParlamentar, idProcesso..."""
    return como_lista(cli.get_json(f"{SENADO_API}/votacao", params=filtros))


def processos(cli: Cliente, **filtros: Any) -> list[dict]:
    """Matérias. Filtros: sigla, numero, ano, codigoParlamentarAutor, tramitando..."""
    return como_lista(cli.get_json(f"{SENADO_API}/processo", params=filtros))
