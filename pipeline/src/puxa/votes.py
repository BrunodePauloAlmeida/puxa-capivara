"""Key votes: reads the curated list (curation/key_votes.yaml), downloads each legislator's vote in both
Houses and links each vote to the master registry.

Vote categories (field `vote`; the original stays in `original_vote`):
  yes, no, abstention, obstruction, presiding (was presiding over the session and does not vote),
  present_no_vote, absent, secret_vote, other.
In the Chamber, the API only lists who registered a vote: whoever does not appear was absent or had no seat on
that date. In the Senate, the list has all 81, with the reason for the absence (leave, mission, parliamentary
activity...).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import polars as pl
import yaml

from puxa.collectors import senate
from puxa.config import CHAMBER_API, RAW, SENATE_API
from puxa.http import Client
from puxa.text import normalize_name

log = logging.getLogger(__name__)

HOUSES = ("chamber", "senate")


@dataclass
class KeyVote:
    topic_id: str
    title: str
    house: str
    id: str
    date: str
    description: str
    main: bool
    bill: str


# --------------------------------------------------------------------------------------------------------------
# Curation


def load_topics(file: Path) -> list[dict]:
    topics = (yaml.safe_load(file.read_text()) or {}).get("key_votes") or []
    validate_topics(topics)
    return topics


def validate_topics(topics: list[dict]) -> None:
    """Fails early if the curation has a data-entry error."""
    ids = [t["id"] for t in topics]
    repeated = {i for i in ids if ids.count(i) > 1}
    if repeated:
        raise ValueError(f"Repeated topic IDs: {sorted(repeated)}")
    for t in topics:
        for field_name in ("title", "bill", "summary", "yes_means"):
            if not t.get(field_name):
                raise ValueError(f"Topic {t['id']}: missing field '{field_name}'")
        for house in HOUSES:
            roll_calls = t.get(house) or []
            explanation = (t.get("no_roll_call") or {}).get(house)
            if not roll_calls and not explanation:
                raise ValueError(
                    f"Topic {t['id']}: no roll calls in the {house} and no explanation in no_roll_call"
                )
            if roll_calls and sum(bool(v.get("main")) for v in roll_calls) != 1:
                raise ValueError(f"Topic {t['id']}: the {house} needs exactly one main roll call")


def curated_roll_calls(topics: list[dict]) -> list[KeyVote]:
    result = []
    for t in topics:
        for house in HOUSES:
            for v in t.get(house) or []:
                result.append(
                    KeyVote(
                        topic_id=t["id"],
                        title=t["title"],
                        house=house,
                        id=str(v["id"]),
                        date=str(v["date"]),
                        description=v["description"],
                        main=bool(v.get("main")),
                        bill=v.get("bill") or t["bill"],
                    )
                )
    return result


def split_bill(text: str) -> tuple[str, int, int]:
    """'PEC 45/2019' -> ('PEC', 45, 2019)."""
    m = re.search(r"([A-Z]+)\s+(\d+)/(\d{4})", text)
    if not m:
        raise ValueError(f"Bill in unexpected format: {text!r}")
    return m.group(1), int(m.group(2)), int(m.group(3))


# --------------------------------------------------------------------------------------------------------------
# Normalization


CHAMBER_VOTES = {
    "SIM": "yes",
    "NAO": "no",
    "ABSTENCAO": "abstention",
    "OBSTRUCAO": "obstruction",
    "ARTIGO": "presiding",  # "Artigo 17": whoever presides over the session does not vote
}

SENATE_VOTES = {
    "Sim": "yes",
    "Não": "no",
    "Abstenção": "abstention",
    "P-OD": "obstruction",
    "Presidente (art. 51 RISF)": "presiding",
    "P-NRV": "present_no_vote",
    "Votou": "secret_vote",
    "NCom": "absent",
}

# Codes that appear in the votes but are not in the official table of attendance types.
SENATE_EXTRA_DESCRIPTIONS = {
    "P-NRV": "Presente, não registrou voto",
    "P-OD": "Presente, obstrução declarada",
    "NCom": "Não compareceu",
    "Votou": "Votou (votação secreta)",
    "Presidente (art. 51 RISF)": "Presidente da sessão (não vota)",
}


def normalize_chamber_vote(kind: str | None) -> str:
    key = normalize_name(kind).split(" ")[0] if kind else ""
    return CHAMBER_VOTES.get(key, "other")


def normalize_senate_vote(code: str | None, legend: dict[str, str]) -> str:
    if code in SENATE_VOTES:
        return SENATE_VOTES[code]
    if code in legend:  # leaves, missions, parliamentary activity etc.
        return "absent"
    return "other"


def party_guidance(party: str | None, guidance: dict[str, str]) -> str | None:
    """Guidance for the deputy's caucus: a single party or a federation ('Fdr PT-PCdoB-PV').
    Blocs appear abbreviated by the Chamber ('Bl UniPpPsd...') and have no match for now."""
    if not party:
        return None
    target = normalize_name(party)
    for code, orientation in guidance.items():
        name = normalize_name(code)
        if name == target:
            return orientation or None
        if code.startswith("Fdr ") and target in {normalize_name(p) for p in code[4:].split("-")}:
            return orientation or None
    return None


# --------------------------------------------------------------------------------------------------------------
# Collection (with a cache of the raw responses)


def _cache_json(file: Path, fetch) -> Any:
    if file.exists():
        return json.loads(file.read_text())
    data = fetch()
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(data, ensure_ascii=False))
    return data


def fetch_chamber(cli: Client, roll_call_id: str, folder: Path = RAW / "chamber" / "votes") -> dict:
    def fetch() -> dict:
        return {
            "roll_call": cli.get_json(f"{CHAMBER_API}/votacoes/{roll_call_id}")["dados"],
            "votes": cli.get_json(f"{CHAMBER_API}/votacoes/{roll_call_id}/votos")["dados"],
            "guidance": cli.get_json(f"{CHAMBER_API}/votacoes/{roll_call_id}/orientacoes")["dados"],
        }

    return _cache_json(folder / f"{roll_call_id}.json", fetch)


def fetch_senate(cli: Client, v: KeyVote, folder: Path = RAW / "senate" / "votes") -> dict:
    def fetch() -> dict:
        code, number, year = split_bill(v.bill)
        for roll_call in senate.roll_calls(cli, sigla=code, numero=number, ano=year):
            if str(roll_call["codigoSessaoVotacao"]) == v.id:
                return roll_call
        raise LookupError(f"Roll call {v.id} not found in the Senate for {v.bill}")

    return _cache_json(folder / f"{v.id}.json", fetch)


def senate_legend(cli: Client, folder: Path = RAW / "senate") -> dict[str, str]:
    body = _cache_json(
        folder / "attendance_types.json",
        lambda: cli.get_json(f"{SENATE_API}/plenario/lista/tiposComparecimento"),
    )
    types = senate.as_list(body["ListaTiposComparecimento"]["TiposComparecimento"]["TipoComparecimento"])
    return {t["Sigla"]: t["Descricao"] for t in types} | SENATE_EXTRA_DESCRIPTIONS


def final_status(cli: Client, topic: dict) -> dict[str, str | None]:
    """Resulting law and status, from the Senate process (which records the outcome in both Houses)."""
    senate_bill = next((v.get("bill") for v in topic.get("senate") or [] if v.get("bill")), None)
    code, number, year = split_bill(senate_bill or topic["bill"])
    processes = senate.processes(cli, sigla=code, numero=number, ano=year)
    if not processes:
        return {"resulting_law": None, "status": None}
    p = processes[0]
    return {"resulting_law": p.get("normaGerada"), "status": p.get("situacaoAtual")}


# --------------------------------------------------------------------------------------------------------------
# Turning into tables


def chamber_rows(v: KeyVote, raw: dict, person_by_chamber: dict[str, str]) -> list[dict]:
    guidance = {o["siglaPartidoBloco"]: o.get("orientacaoVoto") for o in raw["guidance"]}
    government = guidance.get("Governo") or None
    rows = []
    for vote in raw["votes"]:
        dep = vote["deputado_"]
        rows.append(
            {
                "topic_id": v.topic_id,
                "house": "chamber",
                "roll_call_id": v.id,
                "main": v.main,
                "legislator_id": str(dep["id"]),
                "person_id": person_by_chamber.get(str(dep["id"])),
                "name": dep["nome"],
                "party": dep.get("siglaPartido"),
                "state": dep.get("siglaUf"),
                "vote": normalize_chamber_vote(vote.get("tipoVoto")),
                "original_vote": vote.get("tipoVoto"),
                "vote_description": vote.get("tipoVoto"),
                "party_guidance": party_guidance(dep.get("siglaPartido"), guidance),
                "government_guidance": government,
            }
        )
    return rows


def senate_rows(
    v: KeyVote, raw: dict, person_by_senate: dict[str, str], legend: dict[str, str]
) -> list[dict]:
    rows = []
    for vote in raw.get("votos") or []:
        code = vote.get("siglaVotoParlamentar")
        rows.append(
            {
                "topic_id": v.topic_id,
                "house": "senate",
                "roll_call_id": v.id,
                "main": v.main,
                "legislator_id": str(vote["codigoParlamentar"]),
                "person_id": person_by_senate.get(str(vote["codigoParlamentar"])),
                "name": vote["nomeParlamentar"],
                "party": vote.get("siglaPartidoParlamentar"),
                "state": vote.get("siglaUFParlamentar"),
                "vote": normalize_senate_vote(code, legend),
                "original_vote": code,
                "vote_description": vote.get("descricaoVotoParlamentar") or legend.get(code, code),
                "party_guidance": None,
                "government_guidance": None,
            }
        )
    return rows


def tally(rows: list[dict]) -> dict[str, int]:
    counts = {"yes": 0, "no": 0, "abstention": 0, "obstruction": 0}
    for row in rows:
        if row["vote"] in counts:
            counts[row["vote"]] += 1
    return counts


# --------------------------------------------------------------------------------------------------------------
# Orchestration


def build(
    cli: Client, topics: list[dict], people: pl.DataFrame
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
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
    legend = senate_legend(cli)

    votes: list[dict] = []
    metadata: list[dict] = []
    for v in curated_roll_calls(topics):
        log.info("Roll call %s %s (%s)", v.house, v.id, v.topic_id)
        if v.house == "chamber":
            rows = chamber_rows(v, fetch_chamber(cli, v.id), person_by_chamber)
        else:
            rows = senate_rows(v, fetch_senate(cli, v), person_by_senate, legend)
        votes.extend(rows)
        metadata.append(asdict(v) | tally(rows) | {"total_records": len(rows)})

    topic_rows = []
    for t in topics:
        topic_rows.append(
            {
                "topic_id": t["id"],
                "title": t["title"],
                "bill": t["bill"],
                "summary": t["summary"],
                "yes_means": t["yes_means"],
                "hot_topic": bool(t.get("hot_topic")),
                "no_roll_call_chamber": (t.get("no_roll_call") or {}).get("chamber"),
                "no_roll_call_senate": (t.get("no_roll_call") or {}).get("senate"),
            }
            | final_status(cli, t)
        )
    return pl.DataFrame(topic_rows), pl.DataFrame(metadata), pl.DataFrame(votes)


def save(topics: pl.DataFrame, roll_calls: pl.DataFrame, votes: pl.DataFrame, folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for name, df in (("topics", topics), ("roll_calls", roll_calls), ("votes", votes)):
        df.write_parquet(folder / f"{name}.parquet")
        df.write_csv(folder / f"{name}.csv")
