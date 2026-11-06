"""Convert a site data package from the old Portuguese format (v1, November 1, 2026) to the English one.

The publish workflow runs this when the package still has indice.json. Only the standard library is used.
Usage: python3 infra/convert-site-data.py <old web dir> <new web dir>
"""
import json, shutil, sys
from pathlib import Path

ROLE = {"presidente": "president", "governador": "governor", "senador": "senator", "deputado_federal": "federal_deputy"}
CLASS = {"sim": "yes", "nao": "no", "meio": "partial", "neutro": "neutral", "vazio": "empty"}

META = {"versao": "version", "gerado_em": "generated_at", "pessoas": "people", "em_exercicio": "in_office",
        "eleitos_2026": "elected_2026", "com_foto": "with_photo", "sem_pdf": "missing_pdf"}
INDEX = {"id": "id", "nome": "name", "cargo": "role", "partido_uf": "party_state", "uf": "state", "cargos": "roles",
         "foto": "photo", "iniciais": "initials", "busca": "search"}
PERSON = {"id": "id", "nome": "name", "nome_civil": "civil_name", "iniciais": "initials", "fonte_foto": "photo_source",
          "cargos": "roles", "partido_uf": "party_state", "temas_do_momento": "hot_topics", "votacoes": "votes",
          "tem_congresso": "in_congress", "producao": "bills", "gerado_em": "generated_at", "versao": "version",
          "tem_foto": "has_photo", "tem_pdf": "has_pdf"}
VOTE = {"titulo": "title", "significado_sim": "yes_means", "casa": "house", "data": "date", "voto": "vote",
        "classe": "class", "detalhe": "detail", "desfecho": "outcome"}
BILLS = {"casa": "house", "desde": "since", "primeiro_autor": "first_author", "total": "total",
         "viraram_norma": "became_law", "destaques": "highlights"}
HIGHLIGHT = {"identificacao": "identifier", "norma": "law", "ementa": "summary"}


def rename(d: dict, table: dict) -> dict:
    missing = set(d) - set(table)
    if missing:
        raise SystemExit(f"unknown keys {sorted(missing)}")
    return {table[k]: v for k, v in d.items()}


def vote(v: dict) -> dict:
    v = rename(v, VOTE)
    v["class"] = CLASS[v["class"]]
    return v


def person(p: dict) -> dict:
    p = rename(p, PERSON)
    p["hot_topics"] = [vote(v) for v in p["hot_topics"]]
    p["votes"] = [vote(v) for v in p["votes"]]
    if p["bills"] is not None:
        p["bills"] = rename(p["bills"], BILLS)
        p["bills"]["highlights"] = [rename(h, HIGHLIGHT) for h in p["bills"]["highlights"]]
    return p


def main(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    (dst / "people").mkdir(parents=True)
    meta = rename(json.loads((src / "meta.json").read_text()), META)
    for k in ("in_office", "elected_2026"):
        meta[k] = {ROLE[r]: n for r, n in meta[k].items()}
    (dst / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

    index = []
    for row in json.loads((src / "indice.json").read_text()):
        row = rename(row, INDEX)
        row["roles"] = [ROLE[r] for r in row["roles"]]
        index.append(row)
    (dst / "index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")

    for f in sorted((src / "pessoas").glob("*.json")):
        p = person(json.loads(f.read_text()))
        (dst / "people" / f.name).write_text(json.dumps(p, ensure_ascii=False), encoding="utf-8")
    shutil.copytree(src / "fotos", dst / "photos")
    shutil.copytree(src / "pdf", dst / "pdf")
    print(f"{len(index)} index rows, {len(list((dst / 'people').iterdir()))} people, "
          f"{len(list((dst / 'photos').iterdir()))} photos, {len(list((dst / 'pdf').iterdir()))} PDFs")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
