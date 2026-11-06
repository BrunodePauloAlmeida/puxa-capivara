from conftest import candidates

from puxa import registry
from puxa.registry import Record, Role


def _dep(id_, name, state="SP", party="AAA", cpf=None, birth_date=None):
    return (
        {"id": id_, "nome": name.title(), "siglaUf": state, "siglaPartido": party, "urlFoto": f"foto{id_}"},
        {
            "nomeCivil": name,
            "cpf": cpf,
            "dataNascimento": birth_date,
            "ultimoStatus": {"nomeEleitoral": name.title()},
        },
    )


def test_links_chamber_and_tse_by_cpf():
    dep, det = _dep(10, "MARIA SOUZA", cpf="00000000272", birth_date="1970-04-03")
    df26 = candidates(
        [
            (
                "1",
                "SP",
                "DEPUTADO FEDERAL",
                "2",
                "MARIA SOUZA LIMA",
                "MARIA",
                "00000000272",
                "03/04/1970",
                "AAA",
                "ELEITO POR QP",
            )
        ]
    )
    records = registry.chamber_records([dep], {10: det}) + registry.tse_2026_records(df26)
    groups, issues = registry.resolve(records)
    people = registry.build_people(groups, {})
    assert len(people) == 1 and not issues
    p = people[0]
    assert (p.chamber_id, p.tse_sq_2026, p.ballot_name) == ("10", "2", "Maria Souza")
    assert {(x.role, x.status) for x in p.roles} == {
        ("federal_deputy", "in_office"),
        ("federal_deputy", "elected_2026"),
    }


def test_links_senate_and_tse_by_birth_date_and_similar_name():
    senator = {
        "code": "5",
        "name": "Zé Lima",
        "full_name": "José Carlos Lima",
        "party": "BBB",
        "state": "RJ",
        "participation": "Titular",
    }
    details = {"DadosBasicosParlamentar": {"DataNascimento": "1965-01-02"}}
    df26 = candidates(
        [
            (
                "1",
                "RJ",
                "GOVERNADOR",
                "7",
                "JOSÉ CARLOS DE LIMA",
                "ZÉ LIMA",
                "00000000434",
                "02/01/1965",
                "BBB",
                "NÃO ELEITO",
            )
        ]
    )
    records = registry.senate_records([senator], {"5": details}) + registry.tse_2026_records(df26)
    groups, _ = registry.resolve(records)
    people = registry.build_people(groups, {})
    assert len(people) == 1
    assert people[0].senate_code == "5" and people[0].cpf == "00000000434"


def test_never_merges_different_cpfs_and_records_issue():
    a = Record(
        "chamber",
        "1",
        "ANA PAULA",
        cpf="00000000191",
        birth_date="1980-01-01",
        state="SP",
        roles=[Role("federal_deputy", "in_office", "SP", "A", "chamber")],
    )
    b = Record(
        "tse2026",
        "9",
        "ANA PAULA",
        cpf="00000000272",
        birth_date="1980-01-01",
        state="SP",
        roles=[Role("federal_deputy", "elected_2026", "SP", "A", "tse2026")],
    )
    groups, issues = registry.resolve([a, b])
    assert len(groups) == 2
    assert [p.kind for p in issues] == ["cpf_conflict"]


def test_discards_candidates_without_role():
    df26 = candidates(
        [
            (
                "1",
                "SP",
                "DEPUTADO FEDERAL",
                "3",
                "PEDRO LIMA",
                "PEDRO",
                "00000000353",
                "05/06/1980",
                "C",
                "SUPLENTE",
            )
        ]
    )
    groups, _ = registry.resolve(registry.tse_2026_records(df26))
    assert groups == []


def test_governor_who_ran_for_another_office_passes_to_the_vice():
    df22 = candidates(
        [
            ("1", "MG", "GOVERNADOR", "100", "TITULAR UM", "TITULAR", "-4", "", "AAA", "ELEITO"),
            ("1", "MG", "VICE-GOVERNADOR", "101", "VICE UM", "VICE", "-4", "", "AAA", "ELEITO"),
            ("1", "BA", "GOVERNADOR", "200", "TITULAR DOIS", "DOIS", "-4", "", "BBB", "ELEITO"),
            ("1", "BA", "VICE-GOVERNADOR", "201", "VICE DOIS", "VICE2", "-4", "", "BBB", "ELEITO"),
            ("2", "BR", "PRESIDENTE", "300", "PRESIDENTE ATUAL", "PRES", "-4", "", "CCC", "ELEITO"),
        ]
    )
    df26 = candidates(
        [
            (
                "1",
                "MG",
                "SENADOR",
                "500",
                "TITULAR UM",
                "TITULAR",
                "00000000191",
                "01/01/1960",
                "AAA",
                "ELEITO",
            ),
            (
                "1",
                "BA",
                "GOVERNADOR",
                "600",
                "TITULAR DOIS",
                "DOIS",
                "00000000272",
                "01/01/1961",
                "BBB",
                "ELEITO",
            ),
        ]
    )
    records, issues = registry.executive_in_office(df22, df26, overrides=[])
    by_state = {p.state: r for r in records for p in r.roles if p.role == "governor"}
    assert by_state["MG"].civil_name == "VICE UM" and by_state["MG"].roles[0].inferred
    assert by_state["BA"].civil_name == "TITULAR DOIS" and not by_state["BA"].roles[0].inferred
    assert any(r.roles[0].role == "president" for r in records)
    assert [p.kind for p in issues] == ["governor_inferred"]

    # The MG incumbent stays in the registry as an elected senator; the BA one becomes a single person (2022 + 2026).
    groups, _ = registry.resolve(records + registry.tse_2026_records(df26))
    people = {p.civil_name: p for p in registry.build_people(groups, {})}
    assert {(x.role, x.status) for x in people["TITULAR DOIS"].roles} == {
        ("governor", "in_office"),
        ("governor", "elected_2026"),
    }
    assert people["TITULAR DOIS"].tse_sq_2022 == "200" and people["TITULAR DOIS"].tse_sq_2026 == "600"


def test_manual_override_takes_priority_over_inference():
    df22 = candidates([("1", "MG", "GOVERNADOR", "100", "TITULAR UM", "T", "-4", "", "AAA", "ELEITO")])
    overrides = [{"state": "MG", "civil_name": "OUTRA PESSOA", "party": "ZZZ", "reason": "fonte X"}]
    records, _ = registry.executive_in_office(df22, candidates([]), overrides)
    assert records[0].civil_name == "OUTRA PESSOA" and records[0].roles[0].note == "fonte X"


def test_ids_are_stable_and_resolve_namesakes():
    def group(key_id, name, state):
        return [
            Record(
                "chamber",
                key_id,
                name,
                ballot_name=name,
                state=state,
                roles=[Role("federal_deputy", "in_office", state, "A", "chamber")],
            )
        ]

    groups = [group("1", "Pastor Joao", "SP"), group("2", "Pastor Joao", "RJ")]
    ids = registry.assign_ids(groups, {})
    assert sorted(ids) == ["pastor-joao", "pastor-joao-sp"] or sorted(ids) == [
        "pastor-joao",
        "pastor-joao-rj",
    ]

    # On the next run, each keeps its own, even if the order changes.
    previous = {"chamber:1": ids[0], "chamber:2": ids[1]}
    assert registry.assign_ids(list(reversed(groups)), previous) == [ids[1], ids[0]]


def test_links_social_name_by_ballot_name_and_birth_date():
    # The Chamber publishes the civil name; the TSE, the social name. Birth date, state and ballot name remain.
    dep, det = _dep(30, "ERIKA SANTOS SILVA", birth_date="1992-12-09")
    dep["nome"] = det["ultimoStatus"]["nomeEleitoral"] = "Erika Hilton"
    df26 = candidates(
        [
            (
                "1",
                "SP",
                "DEPUTADO FEDERAL",
                "8",
                "ERIKA HILTON",
                "ERIKA HILTON",
                "00000000515",
                "09/12/1992",
                "P",
                "ELEITO POR QP",
            )
        ]
    )
    groups, _ = registry.resolve(registry.chamber_records([dep], {30: det}) + registry.tse_2026_records(df26))
    assert len(groups) == 1


def test_state_deputy_candidacy_also_serves_for_matching():
    dep, det = _dep(40, "LUIZA ERUNDINA DE SOUSA", birth_date="1934-11-30")
    df26 = candidates(
        [
            (
                "1",
                "SP",
                "DEPUTADO ESTADUAL",
                "9",
                "LUIZA ERUNDINA DE SOUSA",
                "ERUNDINA",
                "00000000604",
                "30/11/1934",
                "P",
                "SUPLENTE",
            )
        ]
    )
    groups, _ = registry.resolve(registry.chamber_records([dep], {40: det}) + registry.tse_2026_records(df26))
    people = registry.build_people(groups, {})
    assert len(people) == 1 and people[0].cpf == "00000000604"
    # A state candidacy does not become a role in the registry.
    assert [(p.role, p.status) for p in people[0].roles] == [("federal_deputy", "in_office")]


def test_with_two_candidacies_in_2026_the_one_with_a_result_counts():
    df26 = candidates(
        [
            (
                "1",
                "CE",
                "DEPUTADO ESTADUAL",
                "70",
                "FULANA DE TAL",
                "FULANA",
                "00000000787",
                "01/01/1990",
                "P",
                "#NULO",
            ),
            (
                "1",
                "CE",
                "DEPUTADO FEDERAL",
                "71",
                "FULANA DE TAL",
                "FULANA",
                "00000000787",
                "01/01/1990",
                "P",
                "ELEITO POR QP",
            ),
        ]
    )
    groups, _ = registry.resolve(registry.tse_2026_records(df26))
    assert registry.build_people(groups, {})[0].tse_sq_2026 == "71"
