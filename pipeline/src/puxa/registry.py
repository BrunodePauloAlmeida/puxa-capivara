"""Master registry: one record per politician, linking the IDs from each source.

Scope (decision D1): whoever holds office today and whoever was elected in 2026 as president, governor, senator
or federal deputy.

How people are linked across sources, from the strongest rule to the weakest:
  1. same CPF (Chamber and TSE 2026 publish it);
  2. same civil name and same birth date;
  3. same birth date, similar names (Jaccard >= 0.6) and same state;
  4. same civil name and same state, when the birth date is missing (TSE 2018/2022 no longer publishes it);
  5. same birth date, same ballot name and same state (catches social names and abbreviated civil names).
Two records with different CPFs are never merged; the attempt becomes an issue for review.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

import polars as pl
import yaml

from puxa.collectors import tse
from puxa.text import normalize_name, similarity, slugify

log = logging.getLogger(__name__)

TSE_ROLES = {
    "PRESIDENTE": "president",
    "GOVERNADOR": "governor",
    "SENADOR": "senator",
    "DEPUTADO FEDERAL": "federal_deputy",
}
SIMILARITY_THRESHOLD = 0.6


@dataclass
class Role:
    role: str  # president | governor | senator | federal_deputy
    status: str  # in_office | elected_2026
    state: str | None
    party: str | None
    source: str
    inferred: bool = False
    note: str = ""


@dataclass
class Record:
    source: str  # chamber | senate | tse2026 | tse2022 | curation
    source_id: str
    civil_name: str
    ballot_name: str | None = None
    cpf: str | None = None
    birth_date: str | None = None  # YYYY-MM-DD
    state: str | None = None
    election_state: str | None = None  # SG_UF of the TSE candidacy (includes "BR" for president)
    party: str | None = None
    photo: str | None = None
    gender: str | None = None  # "F" | "M"
    roles: list[Role] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.source}:{self.source_id}"


@dataclass
class Person:
    id: str
    ballot_name: str
    civil_name: str
    birth_date: str | None
    cpf: str | None  # internal use for matching; never goes to the site
    chamber_id: str | None
    senate_code: str | None
    tse_sq_2026: str | None
    tse_sq_2022: str | None
    tse_state_2026: str | None
    tse_state_2022: str | None
    photo: str | None
    gender: str | None
    keys: list[str]
    roles: list[Role]


@dataclass
class Issue:
    kind: str
    description: str
    keys: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------------------------------------------
# Records from each source


def _gender(value: str | None) -> str | None:
    """'F', 'Feminino', 'FEMININO' -> 'F'; 'M', 'Masculino' -> 'M'."""
    if not value:
        return None
    initial = value.strip()[:1].upper()
    return initial if initial in ("F", "M") else None


def chamber_records(deputies: list[dict], details: dict[int, dict]) -> list[Record]:
    records = []
    for d in deputies:
        det = details.get(d["id"], {})
        status = det.get("ultimoStatus", {})
        records.append(
            Record(
                source="chamber",
                source_id=str(d["id"]),
                civil_name=det.get("nomeCivil") or d["nome"],
                ballot_name=status.get("nomeEleitoral") or d["nome"],
                cpf=tse.valid_cpf(det.get("cpf")),
                birth_date=det.get("dataNascimento"),
                state=d["siglaUf"],
                party=d["siglaPartido"],
                photo=d.get("urlFoto"),
                gender=_gender(det.get("sexo") or det.get("siglaSexo")),
                roles=[Role("federal_deputy", "in_office", d["siglaUf"], d["siglaPartido"], "chamber")],
            )
        )
    return records


def senate_records(senators: list[dict], details: dict[str, dict]) -> list[Record]:
    records = []
    for s in senators:
        basics = details.get(s["code"], {}).get("DadosBasicosParlamentar", {})
        note = "" if (s.get("participation") or "Titular") == "Titular" else f"{s['participation']} in office"
        records.append(
            Record(
                source="senate",
                source_id=str(s["code"]),
                civil_name=s["full_name"],
                ballot_name=s["name"],
                birth_date=basics.get("DataNascimento"),
                state=s["state"],
                party=s["party"],
                photo=s.get("photo"),
                gender=_gender(s.get("sex")),
                roles=[Role("senator", "in_office", s["state"], s["party"], "senate", note=note)],
            )
        )
    return records


def _tse_record(row: dict, source: str, roles: list[Role] | None = None) -> Record:
    state = row["SG_UF"] if row["SG_UF"] not in ("BR", "") else None
    return Record(
        source=source,
        source_id=row["SQ_CANDIDATO"],
        civil_name=row["NM_CANDIDATO"],
        ballot_name=row["NM_URNA_CANDIDATO"],
        cpf=tse.valid_cpf(row.get("NR_CPF_CANDIDATO")),
        birth_date=tse.iso_date(row.get("DT_NASCIMENTO")),
        state=state,
        election_state=row["SG_UF"] or None,
        party=row.get("SG_PARTIDO"),
        gender=_gender(row.get("DS_GENERO")),
        roles=roles or [],
    )


def tse_2026_records(df26: pl.DataFrame) -> list[Record]:
    """Those elected in 2026 (with a role) + every other candidate, including for state deputy, only to find the
    CPF and birth date of current office holders (several federal deputies ran for a state seat)."""
    df = tse.latest_status(df26)
    records = []
    for row in df.iter_rows(named=True):
        roles = []
        role = TSE_ROLES.get(row["DS_CARGO"])
        if role and row["DS_SIT_TOT_TURNO"] in tse.ELECTED_STATUSES:
            state = row["SG_UF"] if row["SG_UF"] != "BR" else None
            roles.append(Role(role, "elected_2026", state, row["SG_PARTIDO"], "tse2026"))
        records.append(_tse_record(row, "tse2026", roles))
    return records


def executive_in_office(
    df22: pl.DataFrame, df26: pl.DataFrame, overrides: list[dict]
) -> tuple[list[Record], list[Issue]]:
    """President and governors in office today.

    There is no API with the current governors. Starts from those elected in 2022 and infers changes: whoever ran
    for another office in 2026 had to resign by April (desincompatibilização), and the vice took over. The
    inference is flagged for review; manual corrections go in curation/governors_in_office.yaml.
    """
    e22 = tse.elected(df22, {"PRESIDENTE", "GOVERNADOR", "VICE-GOVERNADOR"})
    candidacies26: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for row in tse.latest_status(df26).iter_rows(named=True):
        candidacies26[normalize_name(row["NM_CANDIDATO"])].append((row["DS_CARGO"], row["SG_UF"]))

    records: list[Record] = []
    issues: list[Issue] = []

    for row in e22.filter(pl.col("DS_CARGO") == "PRESIDENTE").iter_rows(named=True):
        role = Role("president", "in_office", None, row["SG_PARTIDO"], "tse2022")
        records.append(_tse_record(row, "tse2022", [role]))

    overrides_by_state = {o["state"]: o for o in overrides}
    vices = {
        row["SG_UF"]: row for row in e22.filter(pl.col("DS_CARGO") == "VICE-GOVERNADOR").iter_rows(named=True)
    }

    for incumbent in e22.filter(pl.col("DS_CARGO") == "GOVERNADOR").sort("SG_UF").iter_rows(named=True):
        state = incumbent["SG_UF"]
        if state in overrides_by_state:
            o = overrides_by_state[state]
            role = Role("governor", "in_office", state, o.get("party"), "curation", note=o["reason"])
            records.append(
                Record("curation", f"governor-{state}", o["civil_name"], state=state, roles=[role])
            )
            continue

        others = [
            (office, state26)
            for office, state26 in candidacies26.get(normalize_name(incumbent["NM_CANDIDATO"]), [])
            if office != "GOVERNADOR" and state26 in (state, "BR")
        ]
        if not others:
            role = Role("governor", "in_office", state, incumbent["SG_PARTIDO"], "tse2022")
            records.append(_tse_record(incumbent, "tse2022", [role]))
            continue

        vice = vices.get(state)
        office_sought = others[0][0].lower()
        if vice is None:
            issues.append(
                Issue(
                    "governor_without_vice",
                    f"{state}: incumbent ran for {office_sought} and no vice was found",
                )
            )
            continue
        note = (
            f"Incumbent elected in 2022 ({incumbent['NM_URNA_CANDIDATO']}) ran for {office_sought} in 2026; "
            "resignation presumed, vice in office. Check."
        )
        role = Role("governor", "in_office", state, vice["SG_PARTIDO"], "tse2022", inferred=True, note=note)
        records.append(_tse_record(vice, "tse2022", [role]))
        issues.append(Issue("governor_inferred", f"{state}: {note}", [f"tse2022:{vice['SQ_CANDIDATO']}"]))

        vice_others = [
            office
            for office, state26 in candidacies26.get(normalize_name(vice["NM_CANDIDATO"]), [])
            if office not in ("GOVERNADOR", "VICE-GOVERNADOR") and state26 in (state, "BR")
        ]
        if vice_others:
            issues.append(
                Issue(
                    "governor_vice_also_ran",
                    f"{state}: the vice also ran for {vice_others[0].lower()} in 2026; check who governs today",
                    [f"tse2022:{vice['SQ_CANDIDATO']}"],
                )
            )
    return records, issues


def load_overrides(file: Path) -> list[dict]:
    if not file.exists():
        return []
    return (yaml.safe_load(file.read_text()) or {}).get("overrides") or []


# --------------------------------------------------------------------------------------------------------------
# Identity resolution


class _Groups:
    """Union-find that refuses to merge groups with different CPFs."""

    def __init__(self, records: list[Record]):
        self.parent = list(range(len(records)))
        self.cpfs: list[set[str]] = [{r.cpf} if r.cpf else set() for r in records]

    def root(self, i: int) -> int:
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, a: int, b: int) -> bool:
        ra, rb = self.root(a), self.root(b)
        if ra == rb:
            return True
        if self.cpfs[ra] and self.cpfs[rb] and self.cpfs[ra] != self.cpfs[rb]:
            return False
        self.parent[rb] = ra
        self.cpfs[ra] |= self.cpfs[rb]
        return True


def _compatible_state(a: Record, b: Record) -> bool:
    return a.state is None or b.state is None or a.state == b.state


def resolve(records: list[Record]) -> tuple[list[list[Record]], list[Issue]]:
    groups = _Groups(records)
    issues: list[Issue] = []
    seen_conflicts: set[tuple[int, int]] = set()

    def attempt(i: int, j: int, rule: str) -> None:
        if not groups.union(i, j) and (i, j) not in seen_conflicts:
            seen_conflicts.add((i, j))
            a, b = records[i], records[j]
            issues.append(
                Issue(
                    "cpf_conflict",
                    f"{rule}: '{a.civil_name}' and '{b.civil_name}' have different CPFs",
                    [a.key, b.key],
                )
            )

    by_cpf: dict[str, list[int]] = defaultdict(list)
    by_name: dict[str, list[int]] = defaultdict(list)
    by_birth_date: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(records):
        if r.cpf:
            by_cpf[r.cpf].append(i)
        by_name[normalize_name(r.civil_name)].append(i)
        if r.birth_date:
            by_birth_date[r.birth_date].append(i)

    # 1. CPF
    for indices in by_cpf.values():
        for j in indices[1:]:
            attempt(indices[0], j, "cpf")
    # 2. name + birth date and 4. name + state when the birth date is missing
    for indices in by_name.values():
        for x, i in enumerate(indices):
            for j in indices[x + 1 :]:
                a, b = records[i], records[j]
                if a.birth_date and b.birth_date:
                    if a.birth_date == b.birth_date:
                        attempt(i, j, "name+birth_date")
                elif _compatible_state(a, b) and not (a.cpf and b.cpf):
                    attempt(i, j, "name+state")
    # 3. birth date + similar name + state
    for indices in by_birth_date.values():
        for x, i in enumerate(indices):
            for j in indices[x + 1 :]:
                a, b = records[i], records[j]
                if not _compatible_state(a, b):
                    continue
                if similarity(a.civil_name, b.civil_name) >= SIMILARITY_THRESHOLD:
                    attempt(i, j, "birth_date+similar_name")
                # 5. birth date + ballot name
                elif a.ballot_name and normalize_name(a.ballot_name) == normalize_name(b.ballot_name):
                    attempt(i, j, "birth_date+ballot_name")

    grouped: dict[int, list[Record]] = defaultdict(list)
    for i, r in enumerate(records):
        grouped[groups.root(i)].append(r)
    # Only those with some role matter; the other records served only for matching.
    with_role = [g for g in grouped.values() if any(r.roles for r in g)]
    return with_role, issues


# --------------------------------------------------------------------------------------------------------------
# Building people and stable IDs

# Display name: the parliamentary name ("Hugo Motta") is better than the TSE ballot name, which is sometimes just
# the first name ("HUGO"). The TSE is used for those without a seat in Congress.
_BALLOT_NAME_PRIORITY = ["chamber", "senate", "tse2026", "tse2022", "curation"]
_CIVIL_NAME_PRIORITY = ["tse2026", "chamber", "senate", "tse2022", "curation"]


def _first(group: list[Record], attribute: str, priority: list[str]) -> str | None:
    for source in priority:
        for r in group:
            if r.source == source and getattr(r, attribute):
                return getattr(r, attribute)
    return None


def _source_id(group: list[Record], source: str) -> str | None:
    return next((r.source_id for r in group if r.source == source), None)


def assign_ids(groups: list[list[Record]], previous: dict[str, str]) -> list[str]:
    """One slug per person ('tabata-amaral'). Whoever already had a slug in a previous run keeps the same one."""
    used: set[str] = set()
    ids: list[str | None] = [None] * len(groups)

    for n, group in enumerate(groups):
        for r in group:
            slug = previous.get(r.key)
            if slug and slug not in used:
                ids[n] = slug
                used.add(slug)
                break

    pending = [n for n in range(len(groups)) if ids[n] is None]
    pending.sort(
        key=lambda n: (
            normalize_name(_first(groups[n], "ballot_name", _BALLOT_NAME_PRIORITY)),
            sorted(r.key for r in groups[n]),
        )
    )
    for n in pending:
        group = groups[n]
        base = slugify(_first(group, "ballot_name", _BALLOT_NAME_PRIORITY) or group[0].civil_name)
        state = next((p.state for r in group for p in r.roles if p.state), None)
        candidates = [base] + ([f"{base}-{state.lower()}"] if state else [])
        slug = next((c for c in candidates if c not in used), None)
        suffix = 2
        while slug is None:
            attempt = f"{candidates[-1]}-{suffix}"
            slug = attempt if attempt not in used else None
            suffix += 1
        ids[n] = slug
        used.add(slug)
    return ids  # type: ignore[return-value]


def build_people(groups: list[list[Record]], previous: dict[str, str]) -> list[Person]:
    ids = assign_ids(groups, previous)
    people = []
    for pid, group in zip(ids, groups, strict=True):
        # Records with a role first: if the person has two candidacies in 2026 (switched office at registration),
        # the one with a result counts, not the abandoned one.
        group = sorted(group, key=lambda r: not r.roles)
        roles: list[Role] = []
        for r in group:
            for p in r.roles:
                if all((p.role, p.status) != (q.role, q.status) for q in roles):
                    roles.append(p)
        people.append(
            Person(
                id=pid,
                ballot_name=_first(group, "ballot_name", _BALLOT_NAME_PRIORITY) or group[0].civil_name,
                civil_name=_first(group, "civil_name", _CIVIL_NAME_PRIORITY) or "",
                birth_date=next((r.birth_date for r in group if r.birth_date), None),
                cpf=next((r.cpf for r in group if r.cpf), None),
                chamber_id=_source_id(group, "chamber"),
                senate_code=_source_id(group, "senate"),
                tse_sq_2026=_source_id(group, "tse2026"),
                tse_sq_2022=_source_id(group, "tse2022"),
                tse_state_2026=next((r.election_state for r in group if r.source == "tse2026"), None),
                tse_state_2022=next((r.election_state for r in group if r.source == "tse2022"), None),
                photo=_first(group, "photo", ["chamber", "senate"]),
                gender=_first(group, "gender", ["chamber", "senate", "tse2026", "tse2022"]),
                keys=sorted(r.key for r in group),
                roles=roles,
            )
        )
    return sorted(people, key=lambda p: p.id)


def coverage_issues(people: list[Person]) -> list[Issue]:
    """Warnings useful for review: who ended up without a CPF or without a link to the 2026 TSE data."""
    warnings = []
    for p in people:
        roles = {(x.role, x.status) for x in p.roles}
        if ("federal_deputy", "in_office") in roles and not p.cpf:
            warnings.append(Issue("deputy_without_cpf", f"{p.id}: deputy in office without CPF", p.keys))
        if p.tse_sq_2022 and not p.tse_sq_2026 and not p.chamber_id and not p.senate_code:
            warnings.append(
                Issue(
                    "executive_without_cpf",
                    f"{p.id}: no CPF (did not run in 2026 or was not linked to TSE 2026)",
                    p.keys,
                )
            )
    return warnings


# --------------------------------------------------------------------------------------------------------------
# Output


def save(people: list[Person], issues: list[Issue], folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    people_rows = [
        {k: v for k, v in asdict(p).items() if k not in ("roles", "keys")} | {"keys": ",".join(p.keys)}
        for p in people
    ]
    role_rows = [{"person_id": p.id} | asdict(role) for p in people for role in p.roles]
    issue_rows = [asdict(x) | {"keys": ",".join(x.keys)} for x in issues]

    df_people = pl.DataFrame(people_rows)
    df_roles = pl.DataFrame(role_rows)
    df_issues = pl.DataFrame(
        issue_rows, schema={"kind": pl.String, "description": pl.String, "keys": pl.String}
    )
    for name, df in (("people", df_people), ("roles", df_roles), ("issues", df_issues)):
        df.write_parquet(folder / f"{name}.parquet")
        df.write_csv(folder / f"{name}.csv")

    slugs = {key: p.id for p in people for key in p.keys}
    (folder / "slugs.json").write_text(json.dumps(slugs, ensure_ascii=False, indent=0, sort_keys=True))


def load_slugs(folder: Path) -> dict[str, str]:
    file = folder / "slugs.json"
    return json.loads(file.read_text()) if file.exists() else {}


def summary(people: list[Person], issues: list[Issue]) -> str:
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for p in people:
        for role in p.roles:
            counts[(role.role, role.status)] += 1
    lines = [f"People in the registry: {len(people)}"]
    for (role, status), n in sorted(counts.items()):
        lines.append(f"  {role:<17} {status:<13} {n}")
    kinds: dict[str, int] = defaultdict(int)
    for x in issues:
        kinds[x.kind] += 1
    lines.append(f"Issues for review: {len(issues)}")
    for kind, n in sorted(kinds.items()):
        lines.append(f"  {kind:<32} {n}")
    return "\n".join(lines)
