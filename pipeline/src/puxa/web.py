"""Exporta os dados do site (v1) a partir do cadastro, das votações, da produção, das fotos e dos PDFs já gerados.

Saída em dados/site/web/ (é o que vai para o Cloud Storage):
  meta.json            versão, data de geração e contagens por cargo
  indice.json          uma linha por pessoa, para a busca (nome, cargo, partido-UF, texto de busca)
  pessoas/{id}.json    o mesmo conteúdo da ficha em PDF, sem a foto embutida
  fotos/{id}.jpg       foto reduzida (até 320 px de altura)
  pdf/{id}.pdf         o PDF da ficha (gerado antes com `uv run puxa ficha --todos`)
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import date
from pathlib import Path

from PIL import Image

from puxa import ficha
from puxa.texto import normalizar_nome

log = logging.getLogger(__name__)

ALTURA_FOTO = 320
ORDEM_CARGOS = ["presidente", "governador", "senador", "deputado_federal"]


def cargo_curto(linhas_de_cargo: list[str]) -> str:
    """'Deputada federal em exercício · PSOL-SP · reeleita em 2026' -> 'Deputada federal'."""
    if not linhas_de_cargo:
        return ""
    return linhas_de_cargo[0].split(" · ")[0].removesuffix(" em exercício")


def texto_de_busca(*partes: str | None) -> str:
    """Nome de urna e nome civil normalizados (sem acento, minúsculas), sem repetir palavras."""
    vistos: list[str] = []
    for parte in partes:
        for palavra in normalizar_nome(parte or "").lower().split():
            if palavra not in vistos:
                vistos.append(palavra)
    return " ".join(vistos)


def linha_do_indice(ctx: dict, cargos: list[str], uf: str | None, tem_foto: bool) -> dict:
    return {
        "id": ctx["id"],
        "nome": ctx["nome"],
        "cargo": cargo_curto(ctx["cargos"]),
        "partido_uf": ctx["partido_uf"],
        "uf": uf,
        "cargos": cargos,
        "foto": tem_foto,
        "iniciais": ctx["iniciais"],
        # Busca só pelo nome civil que a ficha mostra (o do TSE), pelo mesmo motivo da ficha: nome social.
        "busca": texto_de_busca(ctx["nome"], ctx["nome_civil"]),
    }


def reduzir_foto(origem: Path, destino: Path, altura: int = ALTURA_FOTO) -> None:
    with Image.open(origem) as img:
        img = img.convert("RGB")
        if img.height > altura:
            img = img.resize((round(img.width * altura / img.height), altura), Image.Resampling.LANCZOS)
        img.save(destino, "JPEG", quality=82, optimize=True, progressive=True)


def exportar(
    dados: ficha.Dados,
    pasta_fotos: Path,
    pasta_pdf: Path,
    destino: Path,
    manifesto_fotos: dict | None = None,
    hoje: date | None = None,
) -> dict:
    hoje = hoje or date.today()
    for sub in ("pessoas", "fotos", "pdf"):
        (destino / sub).mkdir(parents=True, exist_ok=True)

    papeis_por_pessoa: dict[str, list[dict]] = {}
    for p in dados.papeis.iter_rows(named=True):
        papeis_por_pessoa.setdefault(p["pessoa_id"], []).append(p)

    indice, sem_pdf = [], []
    for pessoa_id in dados.pessoas["id"].to_list():
        foto = pasta_fotos / f"{pessoa_id}.jpg"
        tem_foto = foto.exists()
        if tem_foto:
            reduzir_foto(foto, destino / "fotos" / f"{pessoa_id}.jpg")

        pdf = pasta_pdf / f"{pessoa_id}.pdf"
        if pdf.exists():
            shutil.copyfile(pdf, destino / "pdf" / f"{pessoa_id}.pdf")
        else:
            sem_pdf.append(pessoa_id)

        ctx = ficha.contexto(pessoa_id, dados, hoje=hoje, pasta_fotos=None, manifesto_fotos=manifesto_fotos)
        ctx.pop("foto")
        ctx["tem_foto"] = tem_foto
        ctx["tem_pdf"] = pdf.exists()
        (destino / "pessoas" / f"{pessoa_id}.json").write_text(
            json.dumps(ctx, ensure_ascii=False), encoding="utf-8"
        )

        papeis = papeis_por_pessoa.get(pessoa_id, [])
        cargos = sorted({p["cargo"] for p in papeis}, key=ORDEM_CARGOS.index)
        principal = next((p for p in papeis if p["situacao"] == "em_exercicio"), papeis[0] if papeis else {})
        indice.append(linha_do_indice(ctx, cargos, principal.get("uf"), tem_foto))

    indice.sort(key=lambda r: r["busca"])

    def contar(situacao: str) -> dict[str, int]:
        pessoas_por_cargo = {c: set() for c in ORDEM_CARGOS}
        for p in dados.papeis.filter(dados.papeis["situacao"] == situacao).iter_rows(named=True):
            pessoas_por_cargo[p["cargo"]].add(p["pessoa_id"])
        return {c: len(ids) for c, ids in pessoas_por_cargo.items()}

    meta = {
        "versao": ficha.VERSAO,
        "gerado_em": hoje.isoformat(),
        "pessoas": len(indice),
        "em_exercicio": contar("em_exercicio"),
        "eleitos_2026": contar("eleito_2026"),
        "com_foto": sum(r["foto"] for r in indice),
        "sem_pdf": sem_pdf,
    }
    (destino / "indice.json").write_text(json.dumps(indice, ensure_ascii=False), encoding="utf-8")
    (destino / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    if sem_pdf:
        log.warning("%d pessoas sem PDF (rode `uv run puxa ficha --todos`): %s", len(sem_pdf), sem_pdf[:10])
    return meta
