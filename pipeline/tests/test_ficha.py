import re
from datetime import date

import polars as pl
import pytest

from puxa import ficha
from puxa.texto import nome_exibicao


def _dados(**extra) -> ficha.Dados:
    pessoas = pl.DataFrame(
        [
            {
                "id": "fulana",
                "nome_urna": "Fulana Silva",
                "nome_civil": "FULANA DE TAL SILVA",
                "genero": "F",
                "camara_id": "10",
                "senado_codigo": None,
                "tse_sq_2026": "1",
                "tse_sq_2022": None,
            },
            {
                "id": "gov",
                "nome_urna": "BELTRANO",
                "nome_civil": "BELTRANO DOS SANTOS",
                "genero": "M",
                "camara_id": None,
                "senado_codigo": None,
                "tse_sq_2026": None,
                "tse_sq_2022": "2",
            },
        ]
    )
    papeis = pl.DataFrame(
        [
            {
                "pessoa_id": "fulana",
                "cargo": "deputado_federal",
                "situacao": "em_exercicio",
                "uf": "SP",
                "partido": "AAA",
                "inferido": False,
            },
            {
                "pessoa_id": "fulana",
                "cargo": "deputado_federal",
                "situacao": "eleito_2026",
                "uf": "SP",
                "partido": "AAA",
                "inferido": False,
            },
            {
                "pessoa_id": "gov",
                "cargo": "governador",
                "situacao": "em_exercicio",
                "uf": "MG",
                "partido": "BBB",
                "inferido": True,
            },
        ]
    )
    temas = pl.DataFrame(
        [
            {
                "tema_id": "t1",
                "titulo": "Tema Um",
                "significado_sim": "a favor",
                "tema_do_momento": False,
                "sem_votacao_nominal_camara": None,
                "sem_votacao_nominal_senado": None,
                "norma_gerada": "Lei nº 1",
                "situacao": None,
            },
            {
                "tema_id": "t2",
                "titulo": "Tema Dois",
                "significado_sim": "a favor",
                "tema_do_momento": False,
                "sem_votacao_nominal_camara": None,
                "sem_votacao_nominal_senado": "Sem voto no Senado.",
                "norma_gerada": None,
                "situacao": "REJEITADA",
            },
            {
                "tema_id": "t3",
                "titulo": "Tema do Momento",
                "significado_sim": "a favor",
                "tema_do_momento": True,
                "sem_votacao_nominal_camara": None,
                "sem_votacao_nominal_senado": None,
                "norma_gerada": None,
                "situacao": None,
            },
        ]
    )
    votacoes = pl.DataFrame(
        [
            {"tema_id": t, "casa": "camara", "id": f"{t}-c", "data": "2025-01-02", "principal": True}
            for t in ("t1", "t2", "t3")
        ]
    )
    votos = pl.DataFrame(
        [
            {
                "tema_id": "t1",
                "casa": "camara",
                "pessoa_id": "fulana",
                "principal": True,
                "voto": "nao",
                "voto_descricao": "Não",
            },
            {
                "tema_id": "t3",
                "casa": "camara",
                "pessoa_id": "fulana",
                "principal": True,
                "voto": "sim",
                "voto_descricao": "Sim",
            },
        ]
    )
    producao = pl.DataFrame(
        [
            {
                "pessoa_id": "fulana",
                "casa": "camara",
                "desde": "2019-02-01",
                "como_primeiro_autor": 5,
                "apresentados": 9,
                "viraram_norma_como_primeiro_autor": 1,
            }
        ]
    )
    destaques = pl.DataFrame(
        [{"pessoa_id": "fulana", "identificacao": "PL 1/2023", "norma": "Lei nº 1", "ementa": "Faz algo."}]
    )
    base = dict(
        pessoas=pessoas,
        papeis=papeis,
        temas=temas,
        votacoes=votacoes,
        votos=votos,
        producao=producao,
        destaques=destaques,
    )
    return ficha.Dados(**(base | extra))


def test_nome_exibicao():
    assert nome_exibicao("TARCISIO GOMES DE FREITAS") == "Tarcisio Gomes de Freitas"
    assert nome_exibicao("JHC") == "JHC"
    assert nome_exibicao("Hugo Motta") == "Hugo Motta"
    assert nome_exibicao("ANA-PAULA DA SILVA") == "Ana-Paula da Silva"


def test_contexto_deputada_reeleita():
    ctx = ficha.contexto("fulana", _dados(), hoje=date(2026, 11, 1), pasta_fotos=None)
    assert ctx["cargos"] == ["Deputada federal em exercício · AAA-SP · reeleita em 2026"]
    assert ctx["nome_civil"] == "Fulana de Tal Silva"
    assert [(v["titulo"], v["voto"]) for v in ctx["temas_do_momento"]] == [("Tema do Momento", "Sim")]
    votos = {v["titulo"]: v for v in ctx["votacoes"]}
    assert (votos["Tema Um"]["voto"], votos["Tema Um"]["classe"], votos["Tema Um"]["desfecho"]) == (
        "Não",
        "nao",
        "Lei nº 1",
    )
    # Sem voto na Câmara e sem explicação de "sem votação nominal" para a Câmara: sem registro.
    assert (votos["Tema Dois"]["voto"], votos["Tema Dois"]["desfecho"]) == ("Sem registro", "Rejeitada")
    assert ctx["producao"]["primeiro_autor"] == 5 and ctx["producao"]["destaques"][0]["norma"] == "Lei nº 1"
    assert ctx["gerado_em"] == "01/11/2026"


def test_contexto_governador_sem_congresso_e_inferido():
    ctx = ficha.contexto("gov", _dados())
    assert ctx["nome"] == "Beltrano"
    assert ctx["nome_civil"] == ""  # sem candidatura em 2026: não mostra nome civil
    assert ctx["cargos"] == ["Governador em exercício · BBB-MG · dado em verificação"]
    assert not ctx["tem_congresso"] and ctx["producao"] is None


def test_linhas_de_cargo_eleito_para_outro_cargo_e_genero_desconhecido():
    papeis = [
        {
            "cargo": "deputado_federal",
            "situacao": "em_exercicio",
            "uf": "RJ",
            "partido": "X",
            "inferido": False,
        },
        {"cargo": "senador", "situacao": "eleito_2026", "uf": "RJ", "partido": "X", "inferido": False},
    ]
    assert ficha.linhas_de_cargo(papeis, None) == [
        "Deputado(a) federal em exercício · X-RJ",
        "Eleito(a) senador(a) em 2026 · X-RJ",
    ]


def test_html_mostra_os_blocos_coletados():
    pagina = ficha.html(ficha.contexto("fulana", _dados()))
    for trecho in (
        "Fulana Silva",
        "Temas do momento",
        "Votações-chave",
        "Produção legislativa",
        "PL 1/2023",
        "Rascunho v1",
    ):
        assert trecho in pagina
    assert "<script" not in pagina


def test_html_escapa_conteudo():
    dados = _dados()
    dados.destaques = dados.destaques.with_columns(pl.lit("<script>x</script>").alias("ementa"))
    assert "<script>x" not in ficha.html(ficha.contexto("fulana", dados))


@pytest.mark.skipif(ficha.caminho_chromium() is None, reason="Chromium não disponível")
def test_pdf_tem_uma_pagina(tmp_path):
    pagina = ficha.html(ficha.contexto("fulana", _dados()))
    assert ficha.gerar_pdfs([("fulana", pagina)], tmp_path) == []
    conteudo = (tmp_path / "fulana.pdf").read_bytes()
    assert len(re.findall(rb"/Type\s*/Page[^s]", conteudo)) == 1
