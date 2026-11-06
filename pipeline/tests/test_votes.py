import pytest

from puxa import votes
from puxa.config import CURATION
from puxa.votes import KeyVote

LEGEND = {"AP": "Atividade parlamentar", "LS": "Licença saúde"} | votes.SENATE_EXTRA_DESCRIPTIONS


def test_real_curation_is_valid():
    topics = votes.load_topics(CURATION / "key_votes.yaml")
    assert len(topics) == 8
    main = [v for v in votes.curated_roll_calls(topics) if v.main]
    # One main roll call per House, except where the Senate had no roll-call vote (IR and PEC da Blindagem).
    assert len(main) == 14


def _topic(**extra):
    base = {
        "id": "x",
        "title": "X",
        "bill": "PL 1/2025",
        "summary": "r",
        "yes_means": "s",
        "chamber": [{"id": "1-1", "date": "2025-01-01", "description": "d", "main": True}],
        "senate": [{"id": "9", "date": "2025-02-01", "description": "d", "main": True}],
    }
    return base | extra


def test_validation_requires_one_main_per_house():
    with pytest.raises(ValueError, match="exactly one main roll call"):
        votes.validate_topics([_topic(senate=[{"id": "9", "date": "x", "description": "d"}])])


def test_validation_requires_explanation_when_there_is_no_roll_call():
    with pytest.raises(ValueError, match="no_roll_call"):
        votes.validate_topics([_topic(senate=[])])
    votes.validate_topics([_topic(senate=[], no_roll_call={"senate": "Aprovado sem voto nominal."})])


def test_roll_call_own_bill_takes_priority():
    topic = _topic(
        chamber=[{"id": "1-1", "date": "x", "description": "d", "main": True, "bill": "PL 490/2007"}]
    )
    v = votes.curated_roll_calls([topic])[0]
    assert v.bill == "PL 490/2007"
    assert votes.split_bill("PL 490/2007 (Câmara)") == ("PL", 490, 2007)


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("Sim", "yes"),
        ("Não", "no"),
        ("Abstenção", "abstention"),
        ("Obstrução", "obstruction"),
        ("Artigo 17", "presiding"),
        ("?", "other"),
    ],
)
def test_normalize_chamber_vote(kind, expected):
    assert votes.normalize_chamber_vote(kind) == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("Sim", "yes"),
        ("Não", "no"),
        ("P-NRV", "present_no_vote"),
        ("AP", "absent"),
        ("LS", "absent"),
        ("Presidente (art. 51 RISF)", "presiding"),
        ("XYZ", "other"),
    ],
)
def test_normalize_senate_vote(code, expected):
    assert votes.normalize_senate_vote(code, LEGEND) == expected


def test_party_guidance_by_party_and_federation():
    guidance = {"PL": "Sim", "Fdr PT-PCdoB-PV": "Não", "Bl UniPpPsd...": "Sim", "Governo": "Não"}
    assert votes.party_guidance("PL", guidance) == "Sim"
    assert votes.party_guidance("PCdoB", guidance) == "Não"
    assert votes.party_guidance("UNIÃO", guidance) is None  # abbreviated bloc, no match


def test_chamber_rows_link_to_registry_and_record_guidance():
    v = KeyVote("t", "T", "chamber", "1-1", "2026-05-27", "1º turno", True, "PEC 1/2026")
    raw = {
        "votes": [
            {
                "tipoVoto": "Sim",
                "deputado_": {"id": 10, "nome": "Fulana", "siglaPartido": "PT", "siglaUf": "SP"},
            },
            {
                "tipoVoto": "Não",
                "deputado_": {"id": 11, "nome": "Ciclano", "siglaPartido": "NOVO", "siglaUf": "RJ"},
            },
        ],
        "guidance": [
            {"siglaPartidoBloco": "Fdr PT-PCdoB-PV", "orientacaoVoto": "Sim"},
            {"siglaPartidoBloco": "Governo", "orientacaoVoto": "Sim"},
        ],
    }
    rows = votes.chamber_rows(v, raw, {"10": "fulana"})
    assert [(x["person_id"], x["vote"], x["party_guidance"], x["government_guidance"]) for x in rows] == [
        ("fulana", "yes", "Sim", "Sim"),
        (None, "no", None, "Sim"),
    ]
    assert votes.tally(rows) == {"yes": 1, "no": 1, "abstention": 0, "obstruction": 0}


def test_senate_rows_use_the_official_legend():
    v = KeyVote("t", "T", "senate", "7106", "2026-10-14", "1º turno", True, "PEC 221/2019")
    raw = {
        "votos": [
            {
                "codigoParlamentar": 5,
                "nomeParlamentar": "A",
                "siglaVotoParlamentar": "Sim",
                "siglaPartidoParlamentar": "X",
                "siglaUFParlamentar": "AC",
            },
            {
                "codigoParlamentar": 6,
                "nomeParlamentar": "B",
                "siglaVotoParlamentar": "LS",
                "siglaPartidoParlamentar": "Y",
                "siglaUFParlamentar": "AM",
            },
        ]
    }
    rows = votes.senate_rows(v, raw, {"5": "a"}, LEGEND)
    assert [(x["person_id"], x["vote"], x["vote_description"]) for x in rows] == [
        ("a", "yes", "Sim"),
        (None, "absent", "Licença saúde"),
    ]
