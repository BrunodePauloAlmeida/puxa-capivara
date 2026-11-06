"""TSE (Superior Electoral Court): Open Data Portal files (CDN, no key).

Validated on 01/11/2026: consulta_cand_2026 already includes the result (elected) and the CPF. In the 2018 and
2022 files the CPF is masked (-4) and the birth date is empty, so matching against older elections is by name."""

import io
import zipfile
from pathlib import Path

import polars as pl

from puxa.config import RAW, TSE_CDN
from puxa.http import Client

ELECTED_STATUSES = {"ELEITO", "ELEITO POR QP", "ELEITO POR MÉDIA"}
INVALID_CPFS = {"", "-1", "-3", "-4", "#NULO", "#NULO#"}


def download_candidates(cli: Client, year: int, folder: Path = RAW / "tse") -> Path:
    return cli.download(
        f"{TSE_CDN}/consulta_cand/consulta_cand_{year}.zip", folder / f"consulta_cand_{year}.zip"
    )


def read_candidates(zip_file: Path) -> pl.DataFrame:
    """Reads the national CSV (…_BRASIL.csv) inside the zip. Everything as text; the TSE uses latin-1 and ';'."""
    with zipfile.ZipFile(zip_file) as z:
        name = next(n for n in z.namelist() if n.upper().endswith("_BRASIL.CSV"))
        text = z.read(name).decode("latin-1")
    return pl.read_csv(io.StringIO(text), separator=";", infer_schema=False)


def latest_status(df: pl.DataFrame) -> pl.DataFrame:
    """Whoever went to the runoff appears twice; the row from the latest round is kept."""
    return df.sort("NR_TURNO").unique(subset=["SQ_CANDIDATO"], keep="last", maintain_order=True)


def elected(df: pl.DataFrame, offices: set[str]) -> pl.DataFrame:
    df = latest_status(df)
    return df.filter(pl.col("DS_CARGO").is_in(offices) & pl.col("DS_SIT_TOT_TURNO").is_in(ELECTED_STATUSES))


def valid_cpf(cpf: str | None) -> str | None:
    if cpf is None or cpf.strip() in INVALID_CPFS:
        return None
    digits = "".join(c for c in cpf if c.isdigit())
    return digits.zfill(11) if digits else None


def iso_date(br_date: str | None) -> str | None:
    """'06/10/1945' -> '1945-10-06'."""
    if not br_date or "/" not in br_date:
        return None
    day, month, year = br_date.split("/")
    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
