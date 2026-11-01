import json

import polars as pl

from puxa import producao


def test_norma_do_despacho():
    assert (
        producao.norma_do_despacho("Transformado na Lei Ordinária 15270/2025. DOU 27/11/2025")
        == "Lei Ordinária 15270/2025"
    )
    assert (
        producao.norma_do_despacho("Transformado na Emenda Constitucional 141/2026. DOU 16/10/2026 PÁG 02")
        == "Emenda Constitucional 141/2026"
    )
    assert producao.norma_do_despacho("Aguardando parecer") is None


def _prop(id_, tipo, data, situacao="Aguardando Parecer", despacho=""):
    return {
        "id": id_,
        "siglaTipo": tipo,
        "numero": id_,
        "ano": data[:4],
        "ementa": f"ementa {id_}",
        "dataApresentacao": f"{data}T10:00:00",
        "ultimoStatus_dataHora": f"{data}T10:00:00",
        "ultimoStatus_descricaoSituacao": situacao,
        "ultimoStatus_despacho": despacho,
    }


def test_producao_camara_conta_tipos_janela_e_primeiro_autor():
    proposicoes = pl.DataFrame(
        [
            _prop(
                "1",
                "PL",
                "2023-03-01",
                producao.SITUACAO_NORMA_CAMARA,
                "Transformado na Lei Ordinária 1/2024.",
            ),
            _prop("2", "PEC", "2024-05-01"),
            _prop("3", "REQ", "2024-05-01"),  # requerimento: não conta
            _prop("4", "PL", "2018-12-01"),  # antes da janela: não conta
            _prop(
                "5",
                "PL",
                "2025-01-10",
                producao.SITUACAO_NORMA_CAMARA,
                "Transformado na Lei Ordinária 2/2025.",
            ),
        ]
    )
    autores = pl.DataFrame(
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
            },  # fora do cadastro
        ]
    )
    resumo, destaques = producao.producao_camara(proposicoes, autores, {"10": "fulana", "20": "sem-projetos"})
    linhas = {r["pessoa_id"]: r for r in resumo.iter_rows(named=True)}
    f = linhas["fulana"]
    assert (
        f["apresentados"],
        f["como_primeiro_autor"],
        f["viraram_norma"],
        f["viraram_norma_como_primeiro_autor"],
    ) == (3, 1, 2, 1)
    assert json.loads(f["por_tipo"]) == {"PEC": 1, "PL": 2}
    assert linhas["sem-projetos"]["apresentados"] == 0
    assert destaques.select("pessoa_id", "identificacao", "norma").rows() == [
        ("fulana", "PL 1/2023", "Lei Ordinária 1/2024")
    ]


def test_primeiro_autor_no_senado():
    autoria = "Senador Alan Rick (UNIÃO/AC), Senador Fulano (PL/RJ)"
    assert producao.e_primeiro_autor(autoria, "Alan Rick")
    assert not producao.e_primeiro_autor(autoria, "Fulano")
    assert producao.e_primeiro_autor("Senadora Damares Alves (REPUBLICANOS/DF)", "Damares Alves")


def test_producao_senado_filtra_tipos_e_conta_normas():
    processos = [
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
    linhas = producao.linhas_senado("5", "A", processos)
    resumo, destaques = producao.producao_senado(linhas, {"5": "a"})
    r = resumo.row(0, named=True)
    assert (r["apresentados"], r["como_primeiro_autor"], r["viraram_norma_como_primeiro_autor"]) == (2, 1, 1)
    assert destaques["norma"].to_list() == ["Lei nº 1 de 01/01/2024"]


def test_completar_normas_busca_no_senado_so_o_que_falta(tmp_path, monkeypatch):
    import httpx

    from puxa.http import Cliente

    chamadas = []

    def responder(request: httpx.Request) -> httpx.Response:
        chamadas.append(dict(request.url.params))
        return httpx.Response(
            200, json=[{"identificacao": "PL 7/2023", "normaGerada": "Lei nº 14.800 de 10/01/2024"}]
        )

    monkeypatch.setattr(producao, "BRUTO", tmp_path)
    cli = Cliente(intervalo=0, transport=httpx.MockTransport(responder))
    destaques = pl.DataFrame(
        {"identificacao": ["PL 7/2023", "PL 8/2023"], "norma": [None, "Lei Ordinária 1/2024"]},
        schema={"identificacao": pl.String, "norma": pl.String},
    )
    resultado = producao.completar_normas(cli, destaques)
    assert resultado["norma"].to_list() == ["Lei nº 14.800 de 10/01/2024", "Lei Ordinária 1/2024"]
    assert chamadas == [{"sigla": "PL", "numero": "7", "ano": "2023"}]
