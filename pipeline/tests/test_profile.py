import re
from datetime import date

import polars as pl
import pytest

from puxa import profile
from puxa.text import display_name


def _data(**extra) -> profile.Dataset:
    people = pl.DataFrame(
        [
            {
                "id": "fulana",
                "ballot_name": "Fulana Silva",
                "civil_name": "FULANA DE TAL SILVA",
                "gender": "F",
                "chamber_id": "10",
                "senate_code": None,
                "tse_sq_2026": "1",
                "tse_sq_2022": None,
            },
            {
                "id": "gov",
                "ballot_name": "BELTRANO",
                "civil_name": "BELTRANO DOS SANTOS",
                "gender": "M",
                "chamber_id": None,
                "senate_code": None,
                "tse_sq_2026": None,
                "tse_sq_2022": "2",
            },
        ]
    )
    roles = pl.DataFrame(
        [
            {
                "person_id": "fulana",
                "role": "federal_deputy",
                "status": "in_office",
                "state": "SP",
                "party": "AAA",
                "inferred": False,
            },
            {
                "person_id": "fulana",
                "role": "federal_deputy",
                "status": "elected_2026",
                "state": "SP",
                "party": "AAA",
                "inferred": False,
            },
            {
                "person_id": "gov",
                "role": "governor",
                "status": "in_office",
                "state": "MG",
                "party": "BBB",
                "inferred": True,
            },
        ]
    )
    topics = pl.DataFrame(
        [
            {
                "topic_id": "t1",
                "title": "Tema Um",
                "yes_means": "a favor",
                "hot_topic": False,
                "no_roll_call_chamber": None,
                "no_roll_call_senate": None,
                "resulting_law": "Lei nº 1",
                "status": None,
            },
            {
                "topic_id": "t2",
                "title": "Tema Dois",
                "yes_means": "a favor",
                "hot_topic": False,
                "no_roll_call_chamber": None,
                "no_roll_call_senate": "Sem voto no Senado.",
                "resulting_law": None,
                "status": "REJEITADA",
            },
            {
                "topic_id": "t3",
                "title": "Tema do Momento",
                "yes_means": "a favor",
                "hot_topic": True,
                "no_roll_call_chamber": None,
                "no_roll_call_senate": None,
                "resulting_law": None,
                "status": None,
            },
        ]
    )
    roll_calls = pl.DataFrame(
        [
            {"topic_id": t, "house": "chamber", "id": f"{t}-c", "date": "2025-01-02", "main": True}
            for t in ("t1", "t2", "t3")
        ]
    )
    votes = pl.DataFrame(
        [
            {
                "topic_id": "t1",
                "house": "chamber",
                "person_id": "fulana",
                "main": True,
                "vote": "no",
                "vote_description": "Não",
            },
            {
                "topic_id": "t3",
                "house": "chamber",
                "person_id": "fulana",
                "main": True,
                "vote": "yes",
                "vote_description": "Sim",
            },
        ]
    )
    bills = pl.DataFrame(
        [
            {
                "person_id": "fulana",
                "house": "chamber",
                "since": "2019-02-01",
                "as_first_author": 5,
                "introduced": 9,
                "became_law_as_first_author": 1,
            }
        ]
    )
    highlights = pl.DataFrame(
        [{"person_id": "fulana", "identifier": "PL 1/2023", "law": "Lei nº 1", "summary": "Faz algo."}]
    )
    base = dict(
        people=people,
        roles=roles,
        topics=topics,
        roll_calls=roll_calls,
        votes=votes,
        bills=bills,
        highlights=highlights,
    )
    return profile.Dataset(**(base | extra))


def test_display_name():
    assert display_name("TARCISIO GOMES DE FREITAS") == "Tarcisio Gomes de Freitas"
    assert display_name("JHC") == "JHC"
    assert display_name("Hugo Motta") == "Hugo Motta"
    assert display_name("ANA-PAULA DA SILVA") == "Ana-Paula da Silva"


def test_context_reelected_deputy():
    ctx = profile.context("fulana", _data(), today=date(2026, 11, 1), photos_dir=None)
    assert ctx["roles"] == ["Deputada federal em exercício · AAA-SP · reeleita em 2026"]
    assert ctx["civil_name"] == "Fulana de Tal Silva"
    assert [(v["title"], v["vote"]) for v in ctx["hot_topics"]] == [("Tema do Momento", "Sim")]
    votes = {v["title"]: v for v in ctx["votes"]}
    assert (votes["Tema Um"]["vote"], votes["Tema Um"]["class"], votes["Tema Um"]["outcome"]) == (
        "Não",
        "no",
        "Lei nº 1",
    )
    # No vote in the Chamber and no "no roll call" explanation for the Chamber: no record.
    assert (votes["Tema Dois"]["vote"], votes["Tema Dois"]["outcome"]) == ("Sem registro", "Rejeitada")
    assert ctx["bills"]["first_author"] == 5 and ctx["bills"]["highlights"][0]["law"] == "Lei nº 1"
    assert ctx["generated_at"] == "01/11/2026"


def test_context_governor_without_congress_and_inferred():
    ctx = profile.context("gov", _data())
    assert ctx["name"] == "Beltrano"
    assert ctx["civil_name"] == ""  # no 2026 candidacy: civil name not shown
    assert ctx["roles"] == ["Governador em exercício · BBB-MG · dado em verificação"]
    assert not ctx["in_congress"] and ctx["bills"] is None


def test_role_lines_elected_to_another_office_and_unknown_gender():
    roles = [
        {
            "role": "federal_deputy",
            "status": "in_office",
            "state": "RJ",
            "party": "X",
            "inferred": False,
        },
        {"role": "senator", "status": "elected_2026", "state": "RJ", "party": "X", "inferred": False},
    ]
    assert profile.role_lines(roles, None) == [
        "Deputado(a) federal em exercício · X-RJ",
        "Eleito(a) senador(a) em 2026 · X-RJ",
    ]


def test_html_shows_the_collected_blocks():
    page = profile.html(profile.context("fulana", _data()))
    for snippet in (
        "Fulana Silva",
        "Temas do momento",
        "Votações-chave",
        "Produção legislativa",
        "PL 1/2023",
        "Rascunho v1",
    ):
        assert snippet in page
    assert "<script" not in page


def test_html_escapes_content():
    data = _data()
    data.highlights = data.highlights.with_columns(pl.lit("<script>x</script>").alias("summary"))
    assert "<script>x" not in profile.html(profile.context("fulana", data))


@pytest.mark.skipif(profile.chromium_path() is None, reason="Chromium not available")
def test_pdf_has_one_page(tmp_path):
    page = profile.html(profile.context("fulana", _data()))
    assert profile.generate_pdfs([("fulana", page)], tmp_path) == []
    content = (tmp_path / "fulana.pdf").read_bytes()
    assert len(re.findall(rb"/Type\s*/Page[^s]", content)) == 1
