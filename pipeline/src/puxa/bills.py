"""Legislative output: bills introduced by each legislator and how many became law (statute, constitutional
amendment, legislative decree, resolution).

Window: bills introduced since 01/02/2019 (56th and 57th legislatures).
Types counted: ordinary and complementary bills, legislative decree and resolution bills, and PECs. Requests,
indications and amendments are left out, because they exist by the thousands and would inflate the count without
saying much.

Chamber: yearly files (proposicoes-{year}.csv and proposicoesAutores-{year}.csv), one download per year instead
of thousands of API calls. "First author" = ordemAssinatura 1; the other proponents are co-authors.
Senate: /processo?codigoParlamentarAutor=. "First author" = first name in the `autoria` field.

Known limitation: whoever switched Houses (e.g. deputy until 2022 and senator since 2023) only has their output
counted in the House they are in now.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date
from pathlib import Path

import polars as pl

from puxa.collectors import senate
from puxa.config import CHAMBER_FILES, RAW
from puxa.http import Client
from puxa.text import normalize_name

log = logging.getLogger(__name__)

SINCE = "2019-02-01"
CHAMBER_TYPES = {"PL", "PLP", "PEC", "PDL", "PRC"}
SENATE_TYPES = {"PL", "PLP", "PEC", "PDL", "PRS"}
CHAMBER_LAW_STATUS = "Transformado em Norma Jurídica"
MAX_HIGHLIGHTS = 5

_LAW_IN_DISPATCH = re.compile(r"Transformad[oa] n[ao]s? (.+?\d[\d.]*/\d{4})", re.IGNORECASE)


def law_from_dispatch(dispatch: str | None) -> str | None:
    """'Transformado na Lei Ordinária 15270/2025. DOU ...' -> 'Lei Ordinária 15270/2025'."""
    if not dispatch:
        return None
    m = _LAW_IN_DISPATCH.search(dispatch)
    return m.group(1).strip() if m else None


# --------------------------------------------------------------------------------------------------------------
# Chamber


def download_chamber_yearly(
    cli: Client, years: range, folder: Path = RAW / "chamber" / "files"
) -> list[tuple[Path, Path]]:
    pairs = []
    for year in years:
        bills = cli.download(
            f"{CHAMBER_FILES}/proposicoes/csv/proposicoes-{year}.csv", folder / f"proposicoes-{year}.csv"
        )
        authors = cli.download(
            f"{CHAMBER_FILES}/proposicoesAutores/csv/proposicoesAutores-{year}.csv",
            folder / f"proposicoesAutores-{year}.csv",
        )
        pairs.append((bills, authors))
    return pairs


_BILL_COLUMNS = [
    "id",
    "siglaTipo",
    "numero",
    "ano",
    "ementa",
    "dataApresentacao",
    "ultimoStatus_dataHora",
    "ultimoStatus_descricaoSituacao",
    "ultimoStatus_despacho",
]
_AUTHOR_COLUMNS = ["idProposicao", "idDeputadoAutor", "ordemAssinatura", "proponente"]


def read_chamber_yearly(pairs: list[tuple[Path, Path]]) -> tuple[pl.DataFrame, pl.DataFrame]:
    def read(file: Path, columns: list[str]) -> pl.DataFrame:
        return pl.read_csv(file, separator=";", infer_schema=False, columns=columns, encoding="utf8-lossy")

    bills = pl.concat([read(p, _BILL_COLUMNS) for p, _ in pairs]).unique(subset="id", keep="last")
    authors = pl.concat([read(a, _AUTHOR_COLUMNS) for _, a in pairs]).unique()
    return bills, authors


def chamber_bills(bills: pl.DataFrame, authors: pl.DataFrame, person_by_chamber: dict[str, str]):
    projects = bills.filter(
        pl.col("siglaTipo").is_in(CHAMBER_TYPES) & (pl.col("dataApresentacao").str.slice(0, 10) >= SINCE)
    ).with_columns(
        (pl.col("ultimoStatus_descricaoSituacao") == CHAMBER_LAW_STATUS).alias("became_law"),
        (pl.col("siglaTipo") + " " + pl.col("numero") + "/" + pl.col("ano")).alias("identifier"),
    )
    authorship = (
        authors.filter(
            (pl.col("proponente") == "1") & pl.col("idDeputadoAutor").is_in(list(person_by_chamber))
        )
        .with_columns((pl.col("ordemAssinatura") == "1").alias("first_author"))
        .join(projects, left_on="idProposicao", right_on="id", how="inner")
    )
    summary = _summarize(authorship, key="idDeputadoAutor", type_col="siglaTipo")
    highlights = (
        authorship.filter(pl.col("became_law") & pl.col("first_author"))
        .with_columns(
            pl.col("ultimoStatus_despacho")
            .map_elements(law_from_dispatch, return_dtype=pl.String)
            .alias("law"),
            pl.col("ultimoStatus_dataHora").str.slice(0, 10).alias("law_date"),
        )
        .select(
            pl.col("idDeputadoAutor").alias("legislator_id"),
            "identifier",
            pl.col("ementa").alias("summary"),
            "law",
            "law_date",
        )
    )
    return _with_person(summary, highlights, person_by_chamber, "chamber")


# --------------------------------------------------------------------------------------------------------------
# Senate


def senator_processes(cli: Client, code: str, folder: Path = RAW / "senate" / "authorship") -> list[dict]:
    file = folder / f"{code}.json"
    if file.exists():
        return json.loads(file.read_text())
    data = senate.processes(cli, codigoParlamentarAutor=code)
    folder.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(data, ensure_ascii=False))
    return data


def is_first_author(authorship: str | None, legislator_name: str) -> bool:
    """'Senador Alan Rick (UNIÃO/AC), Senador Fulano (...)' -> is the first name the senator's?"""
    if not authorship:
        return False
    first = normalize_name(authorship.split(",")[0].split("(")[0])
    first = re.sub(r"^(SENADORA?|DEPUTAD[OA]) (FEDERAL )?", "", first).strip()
    return first == normalize_name(legislator_name)


def senate_rows(code: str, legislator_name: str, processes: list[dict]) -> list[dict]:
    rows = []
    for p in processes:
        identifier = p.get("identificacao") or ""
        kind = identifier.split(" ")[0]
        if kind not in SENATE_TYPES or (p.get("dataApresentacao") or "") < SINCE:
            continue
        rows.append(
            {
                "legislator_id": code,
                "identifier": identifier,
                "type": kind,
                "summary": p.get("ementa"),
                "first_author": is_first_author(p.get("autoria"), legislator_name),
                "became_law": bool(p.get("normaGerada")),
                "law": p.get("normaGerada"),
                "law_date": p.get("dataSituacaoAtual") if p.get("normaGerada") else None,
            }
        )
    return rows


def senate_bills(rows: list[dict], person_by_senate: dict[str, str]):
    schema = {
        "legislator_id": pl.String,
        "identifier": pl.String,
        "type": pl.String,
        "summary": pl.String,
        "first_author": pl.Boolean,
        "became_law": pl.Boolean,
        "law": pl.String,
        "law_date": pl.String,
    }
    authorship = pl.DataFrame(rows, schema=schema)
    summary = _summarize(authorship, key="legislator_id", type_col="type")
    highlights = authorship.filter(pl.col("became_law") & pl.col("first_author")).select(
        "legislator_id", "identifier", "summary", "law", "law_date"
    )
    return _with_person(summary, highlights, person_by_senate, "senate")


# --------------------------------------------------------------------------------------------------------------
# Shared


def _summarize(authorship: pl.DataFrame, key: str, type_col: str) -> pl.DataFrame:
    if authorship.is_empty():
        return pl.DataFrame(
            schema={
                "legislator_id": pl.String,
                "introduced": pl.UInt32,
                "as_first_author": pl.UInt32,
                "became_law": pl.UInt32,
                "became_law_as_first_author": pl.UInt32,
                "by_type": pl.String,
            }
        )
    by_type = (
        authorship.group_by(key, type_col)
        .len()
        .group_by(key)
        .agg(pl.struct(type_col, "len").alias("types"))
        .with_columns(
            pl.col("types")
            .map_elements(
                lambda s: json.dumps({x[type_col]: x["len"] for x in s}, sort_keys=True),
                return_dtype=pl.String,
            )
            .alias("by_type")
        )
        .drop("types")
    )
    return (
        authorship.group_by(key)
        .agg(
            pl.len().alias("introduced"),
            pl.col("first_author").sum().alias("as_first_author"),
            pl.col("became_law").sum().alias("became_law"),
            (pl.col("became_law") & pl.col("first_author")).sum().alias("became_law_as_first_author"),
        )
        .join(by_type, on=key)
        .rename({key: "legislator_id"})
    )


def _with_person(summary: pl.DataFrame, highlights: pl.DataFrame, mapping: dict[str, str], house: str):
    mapping_df = pl.DataFrame(
        {"legislator_id": list(mapping), "person_id": list(mapping.values())},
        schema={"legislator_id": pl.String, "person_id": pl.String},
    )
    # Every legislator in office appears, even with zero bills.
    summary = (
        mapping_df.join(summary, on="legislator_id", how="left")
        .with_columns(
            pl.lit(house).alias("house"),
            pl.lit(SINCE).alias("since"),
            pl.col("introduced", "as_first_author", "became_law", "became_law_as_first_author")
            .fill_null(0)
            .cast(pl.UInt32),
            pl.col("by_type").fill_null("{}"),
        )
        .sort("person_id")
    )
    highlights = (
        highlights.join(mapping_df, on="legislator_id", how="inner")
        .with_columns(pl.lit(house).alias("house"))
        .sort(["person_id", "law_date"], descending=[False, True], nulls_last=True)
        .group_by("person_id", maintain_order=True)
        .head(MAX_HIGHLIGHTS)
    )
    return summary, highlights


def law_from_senate(cli: Client, identifier: str, folder: Path | None = None) -> str | None:
    """Law resulting from a bill, from the Senate process. Numbering has been unified across the Houses since
    2019, and the Senate also records the law for bills that originated in the Chamber."""
    code, rest = identifier.split(" ", 1)
    number, year = rest.split("/")
    folder = folder or RAW / "senate" / "processes"
    file = folder / f"{code}-{number}-{year}.json"
    if file.exists():
        processes = json.loads(file.read_text())
    else:
        processes = senate.processes(cli, sigla=code, numero=number, ano=year)
        folder.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(processes, ensure_ascii=False))
    return next((p["normaGerada"] for p in processes if p.get("normaGerada")), None)


def fill_laws(cli: Client, highlights: pl.DataFrame) -> pl.DataFrame:
    """The Chamber file almost never has the law number; looks it up in the Senate only for the highlights."""
    missing = highlights.filter(pl.col("law").is_null())["identifier"].unique().to_list()
    if not missing:
        return highlights
    found = {identifier: law_from_senate(cli, identifier) for identifier in missing}
    return highlights.with_columns(
        pl.coalesce(
            pl.col("law"),
            pl.col("identifier").replace_strict(found, default=None, return_dtype=pl.String),
        ).alias("law")
    )


def build(
    cli: Client, people: pl.DataFrame, final_year: int | None = None
) -> tuple[pl.DataFrame, pl.DataFrame]:
    final_year = final_year or date.today().year
    person_by_chamber = {
        r["chamber_id"]: r["id"]
        for r in people.select("id", "chamber_id").iter_rows(named=True)
        if r["chamber_id"]
    }
    person_by_senate = {
        r["senate_code"]: r["id"]
        for r in people.select("id", "senate_code").iter_rows(named=True)
        if r["senate_code"]
    }

    log.info("Chamber: yearly bill files %s–%s", SINCE[:4], final_year)
    bills, authors = read_chamber_yearly(download_chamber_yearly(cli, range(int(SINCE[:4]), final_year + 1)))
    summary_c, highlights_c = chamber_bills(bills, authors, person_by_chamber)
    log.info("Senate: law number for %d Chamber highlights", highlights_c.height)
    highlights_c = fill_laws(cli, highlights_c)

    log.info("Senate: authorship of %d senators", len(person_by_senate))
    names = {s["code"]: s["name"] for s in senate.senators_in_office(cli)}
    rows: list[dict] = []
    for code in person_by_senate:
        rows.extend(senate_rows(code, names.get(code, ""), senator_processes(cli, code)))
    summary_s, highlights_s = senate_bills(rows, person_by_senate)

    return pl.concat([summary_c, summary_s], how="diagonal"), pl.concat(
        [highlights_c, highlights_s], how="diagonal"
    )


def save(summary: pl.DataFrame, highlights: pl.DataFrame, folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for name, df in (("bills", summary), ("highlights", highlights)):
        df.write_parquet(folder / f"{name}.parquet")
        df.write_csv(folder / f"{name}.csv")
