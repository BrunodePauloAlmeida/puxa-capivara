"""Fotos oficiais: Câmara ou Senado para quem tem mandato no Congresso; TSE (foto da candidatura) para os demais.

Saída: dados/fotos/{pessoa_id}.jpg e dados/fotos/manifesto.json com a fonte de cada foto.
"""

from __future__ import annotations

import json
import logging
import zipfile
from collections import defaultdict
from pathlib import Path

import polars as pl

from puxa.config import BRUTO, DADOS
from puxa.http import Cliente

log = logging.getLogger(__name__)

TSE_FOTOS = "https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes{ano}/fotos/foto_cand{ano}_{uf}_div.zip"


def pasta_fotos() -> Path:
    return DADOS / "fotos"


def plano_tse(pessoas: pl.DataFrame) -> dict[tuple[int, str], list[tuple[str, str]]]:
    """(ano, UF do zip) -> [(pessoa_id, SQ)] para quem não tem foto da Câmara ou do Senado."""
    plano: dict[tuple[int, str], list[tuple[str, str]]] = defaultdict(list)
    for p in pessoas.filter(pl.col("foto").is_null()).iter_rows(named=True):
        if p["tse_sq_2026"] and p["tse_uf_2026"]:
            plano[(2026, p["tse_uf_2026"])].append((p["id"], p["tse_sq_2026"]))
        elif p["tse_sq_2022"] and p["tse_uf_2022"]:
            plano[(2022, p["tse_uf_2022"])].append((p["id"], p["tse_sq_2022"]))
    return plano


def extrair_do_zip(arquivo_zip: Path, uf: str, sq: str, destino: Path) -> bool:
    """O TSE nomeia as fotos como F{UF}{SQ}_div.jpg (ex.: FBR280002542548_div.jpg)."""
    with zipfile.ZipFile(arquivo_zip) as z:
        nomes = {n.upper(): n for n in z.namelist()}
        for candidato in (f"F{uf}{sq}_DIV.JPG", f"F{uf}{sq}_DIV.JPEG"):
            if candidato in nomes:
                destino.write_bytes(z.read(nomes[candidato]))
                return True
    return False


def baixar_fotos(cli: Cliente, pessoas: pl.DataFrame) -> dict[str, dict]:
    pasta = pasta_fotos()
    pasta.mkdir(parents=True, exist_ok=True)
    manifesto_path = pasta / "manifesto.json"
    manifesto: dict[str, dict] = json.loads(manifesto_path.read_text()) if manifesto_path.exists() else {}

    for p in pessoas.filter(pl.col("foto").is_not_null()).iter_rows(named=True):
        destino = pasta / f"{p['id']}.jpg"
        if destino.exists() and manifesto.get(p["id"], {}).get("url") == p["foto"]:
            continue
        try:
            cli.baixar(p["foto"], destino)
            fonte = "Câmara dos Deputados" if "camara.leg.br" in p["foto"] else "Senado Federal"
            manifesto[p["id"]] = {"arquivo": destino.name, "fonte": fonte, "url": p["foto"]}
        except Exception as erro:  # foto é opcional: a ficha usa as iniciais
            log.warning("Sem foto para %s: %s", p["id"], erro)

    for (ano, uf), alvos in sorted(plano_tse(pessoas).items()):
        faltando = [(pid, sq) for pid, sq in alvos if not (pasta / f"{pid}.jpg").exists()]
        if not faltando:
            continue
        arquivo_zip = cli.baixar(
            TSE_FOTOS.format(ano=ano, uf=uf), BRUTO / "tse" / "fotos" / f"foto_cand{ano}_{uf}_div.zip"
        )
        for pid, sq in faltando:
            destino = pasta / f"{pid}.jpg"
            if extrair_do_zip(arquivo_zip, uf, sq, destino):
                manifesto[pid] = {"arquivo": destino.name, "fonte": f"TSE, candidatura de {ano}"}
            else:
                log.warning("Foto de %s (SQ %s) não está no zip %s/%s", pid, sq, ano, uf)

    manifesto_path.write_text(json.dumps(manifesto, ensure_ascii=False, indent=1, sort_keys=True))
    return manifesto
