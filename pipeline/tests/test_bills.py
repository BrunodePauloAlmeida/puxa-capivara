import json

import polars as pl

from puxa import bills


def test_law_from_dispatch():
    assert (
        bills.law_from_dispatch("Transformado na Lei Ordinária 15270/2025. DOU 27/11/2025")
        == "Lei Ordinária 15270/2025"
    )
    assert (
        bills.law_from_dispatch("Transformado na Emenda Constitucional 141/2026. DOU 16/10/2026 PÁG 02")
        == "Emenda Constitucional 141/2026"
    )
    assert bills.law_from_dispatch("Aguardando parecer") is None


def _bill(id_, kind, date, status="Aguardando Parecer", dispatch=""):
    return {
        "id": id_,
        "siglaTipo": kind,
        "numero": id_,
        "ano": date[:4],
        "ementa": f"ementa {id_}",
        "dataApresentacao": f"{date}T10:00:00",
        "ultimoStatus_dataHora": f"{date}T10:00:00",
        "ultimoStatus_descricaoSituacao": status,
        "ultimoStatus_despacho": dispatch,
    }


def test_chamber_bills_counts_types_window_and_first_author():
    proposals = pl.DataFrame(
        [
            _bill(
                "1",
                "PL",
                "2023-03-01",
                bills.CHAMBER_LAW_STATUS,
                "Transformado na Lei Ordinária 1/2024.",
            ),
            _bill("2", "PEC", "2024-05-01"),
            _bill("3", "REQ", "2024-05-01"),  # request: does not count
            _bill("4", "PL", "2018-12-01"),  # before the window: does not count
            _bill(
                "5",
                "PL",
                "2025-01-10",
                bills.CHAMBER_LAW_STATUS,
                "Transformado na Lei Ordinária 2/2025.",
            ),
        ]
    )
    authors = pl.DataFrame(
        [
            {"idProposicao": "1", "idDeputadoAutor": "10", "ordemAssinatura": "1", "proponente": "1"},
            {"idProposicao": "2", "idDeputadoAutor": "10", "ordemAssinatura": "5", "proponente": "1"},
            {"idProposicao": "3", "idDeputadoAutor": "10", "ordemAssinatura": "1", "proponente": "1"},
            {"idProposicao": "4", "idDeputadoAutor": "10", "ordemAssinatura": "1", "proponente": "1"},
            {"idProposicao": "5", "idDeputadoAutor": "10", "ordemAssinatura": "2", "proponente": "1"},
            {
                "idProposicao": "1",
                "idDeputadoAutor": "99",
                "ordemAssinatura": "2",
                "proponente": "1",
            },  # not in the registry
        ]
    )
    summary, highlights = bills.chamber_bills(proposals, authors, {"10": "fulana", "20": "no-bills"})
    rows = {r["person_id"]: r for r in summary.iter_rows(named=True)}
    f = rows["fulana"]
    assert (
        f["introduced"],
        f["as_first_author"],
        f["became_law"],
        f["became_law_as_first_author"],
    ) == (3, 1, 2, 1)
    assert json.loads(f["by_type"]) == {"PEC": 1, "PL": 2}
    assert rows["no-bills"]["introduced"] == 0
    assert highlights.select("person_id", "identifier", "law").rows() == [
        ("fulana", "PL 1/2023", "Lei Ordinária 1/2024")
    ]


def test_first_author_in_the_senate():
    authorship = "Senador Alan Rick (UNIÃO/AC), Senador Fulano (PL/RJ)"
    assert bills.is_first_author(authorship, "Alan Rick")
    assert not bills.is_first_author(authorship, "Fulano")
    assert bills.is_first_author("Senadora Damares Alves (REPUBLICANOS/DF)", "Damares Alves")


def test_senate_bills_filters_types_and_counts_laws():
    processes = [
        {
            "identificacao": "PL 1/2023",
            "dataApresentacao": "2023-03-01",
            "autoria": "Senador A (X/AC)",
            "normaGerada": "Lei nº 1 de 01/01/2024",
            "dataSituacaoAtual": "2024-01-01",
            "ementa": "e1",
        },
        {
            "identificacao": "PEC 2/2023",
            "dataApresentacao": "2023-04-01",
            "autoria": "Senador B (Y/AM), Senador A (X/AC)",
            "ementa": "e2",
        },
        {
            "identificacao": "RQS 3/2023",
            "dataApresentacao": "2023-04-01",
            "autoria": "Senador A (X/AC)",
            "ementa": "e3",
        },
    ]
    rows = bills.senate_rows("5", "A", processes)
    summary, highlights = bills.senate_bills(rows, {"5": "a"})
    r = summary.row(0, named=True)
    assert (r["introduced"], r["as_first_author"], r["became_law_as_first_author"]) == (2, 1, 1)
    assert highlights["law"].to_list() == ["Lei nº 1 de 01/01/2024"]


def test_fill_laws_looks_up_in_the_senate_only_what_is_missing(tmp_path, monkeypatch):
    import httpx

    from puxa.http import Client

    calls = []

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(dict(request.url.params))
        return httpx.Response(
            200, json=[{"identificacao": "PL 7/2023", "normaGerada": "Lei nº 14.800 de 10/01/2024"}]
        )

    monkeypatch.setattr(bills, "RAW", tmp_path)
    cli = Client(interval=0, transport=httpx.MockTransport(respond))
    highlights = pl.DataFrame(
        {"identifier": ["PL 7/2023", "PL 8/2023"], "law": [None, "Lei Ordinária 1/2024"]},
        schema={"identifier": pl.String, "law": pl.String},
    )
    result = bills.fill_laws(cli, highlights)
    assert result["law"].to_list() == ["Lei nº 14.800 de 10/01/2024", "Lei Ordinária 1/2024"]
    assert calls == [{"sigla": "PL", "numero": "7", "ano": "2023"}]
