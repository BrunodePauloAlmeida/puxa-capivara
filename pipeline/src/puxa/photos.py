"""Official photos: Chamber or Senate for those with a seat in Congress; TSE (candidacy photo) for the rest.

Output: data/photos/{person_id}.jpg and data/photos/manifest.json with the source of each photo.
"""

from __future__ import annotations

import json
import logging
import zipfile
from collections import defaultdict
from pathlib import Path

import polars as pl

from puxa.config import DATA, RAW
from puxa.http import Client

log = logging.getLogger(__name__)

TSE_PHOTOS = (
    "https://cdn.tse.jus.br/estatistica/sead/eleicoes/eleicoes{year}/fotos/foto_cand{year}_{state}_div.zip"
)


def photos_dir() -> Path:
    return DATA / "photos"


def tse_plan(people: pl.DataFrame) -> dict[tuple[int, str], list[tuple[str, str]]]:
    """(year, zip state) -> [(person_id, SQ)] for those without a Chamber or Senate photo."""
    plan: dict[tuple[int, str], list[tuple[str, str]]] = defaultdict(list)
    for p in people.filter(pl.col("photo").is_null()).iter_rows(named=True):
        if p["tse_sq_2026"] and p["tse_state_2026"]:
            plan[(2026, p["tse_state_2026"])].append((p["id"], p["tse_sq_2026"]))
        elif p["tse_sq_2022"] and p["tse_state_2022"]:
            plan[(2022, p["tse_state_2022"])].append((p["id"], p["tse_sq_2022"]))
    return plan


def extract_from_zip(zip_file: Path, state: str, sq: str, dest: Path) -> bool:
    """The TSE names photos F{UF}{SQ}_div.jpg (e.g. FBR280002542548_div.jpg)."""
    with zipfile.ZipFile(zip_file) as z:
        names = {n.upper(): n for n in z.namelist()}
        for candidate in (f"F{state}{sq}_DIV.JPG", f"F{state}{sq}_DIV.JPEG"):
            if candidate in names:
                dest.write_bytes(z.read(names[candidate]))
                return True
    return False


def download_photos(cli: Client, people: pl.DataFrame) -> dict[str, dict]:
    folder = photos_dir()
    folder.mkdir(parents=True, exist_ok=True)
    manifest_path = folder / "manifest.json"
    manifest: dict[str, dict] = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    for p in people.filter(pl.col("photo").is_not_null()).iter_rows(named=True):
        dest = folder / f"{p['id']}.jpg"
        if dest.exists() and manifest.get(p["id"], {}).get("url") == p["photo"]:
            continue
        try:
            cli.download(p["photo"], dest)
            source = "Câmara dos Deputados" if "camara.leg.br" in p["photo"] else "Senado Federal"
            manifest[p["id"]] = {"file": dest.name, "source": source, "url": p["photo"]}
        except Exception as error:  # the photo is optional: the profile uses the initials
            log.warning("No photo for %s: %s", p["id"], error)

    for (year, state), targets in sorted(tse_plan(people).items()):
        missing = [(pid, sq) for pid, sq in targets if not (folder / f"{pid}.jpg").exists()]
        if not missing:
            continue
        zip_file = cli.download(
            TSE_PHOTOS.format(year=year, state=state),
            RAW / "tse" / "photos" / f"foto_cand{year}_{state}_div.zip",
        )
        for pid, sq in missing:
            dest = folder / f"{pid}.jpg"
            if extract_from_zip(zip_file, state, sq, dest):
                manifest[pid] = {"file": dest.name, "source": f"TSE, candidatura de {year}"}
            else:
                log.warning("Photo of %s (SQ %s) is not in the zip %s/%s", pid, sq, year, state)

    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True))
    return manifest
