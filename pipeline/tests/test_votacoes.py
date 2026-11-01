import pytest

from puxa import votacoes
from puxa.config import CURADORIA
from puxa.votacoes import VotacaoChave

LEGENDA = {"AP": "Atividade parlamentar", "LS": "Licença saúde"} | votacoes.DESCRICOES_SENADO_EXTRAS


def test_curadoria_real_e_valida():
    temas = votacoes.carregar_temas(CURADORIA / "votacoes_chave.yaml")
    assert len(temas) == 8
    principais = [v for v in votacoes.votacoes_da_curadoria(temas) if v.principal]
    # Uma principal por Casa, menos onde o Senado não teve votação nominal (IR e PEC da Blindagem).
    assert len(principais) == 14


def _tema(**extra):
    base = {
        "id": "x",
        "titulo": "X",
        "proposicao": "PL 1/2025",
        "resumo": "r",
        "significado_sim": "s",
        "camara": [{"id": "1-1", "data": "2025-01-01", "descricao": "d", "principal": True}],
        "senado": [{"id": "9", "data": "2025-02-01", "descricao": "d", "principal": True}],
    }
    return base | extra


def test_validacao_exige_uma_principal_por_casa():
    with pytest.raises(ValueError, match="exatamente uma votação principal"):
        votacoes.validar_temas([_tema(senado=[{"id": "9", "data": "x", "descricao": "d"}])])


def test_validacao_exige_explicacao_quando_nao_ha_votacao():
    with pytest.raises(ValueError, match="sem_votacao_nominal"):
        votacoes.validar_temas([_tema(senado=[])])
    votacoes.validar_temas([_tema(senado=[], sem_votacao_nominal={"senado": "Aprovado sem voto nominal."})])


def test_proposicao_propria_da_votacao_tem_prioridade():
    tema = _tema(
        camara=[{"id": "1-1", "data": "x", "descricao": "d", "principal": True, "proposicao": "PL 490/2007"}]
    )
    v = votacoes.votacoes_da_curadoria([tema])[0]
    assert v.proposicao == "PL 490/2007"
    assert votacoes.separar_proposicao("PL 490/2007 (Câmara)") == ("PL", 490, 2007)


@pytest.mark.parametrize(
    ("tipo", "esperado"),
    [
        ("Sim", "sim"),
        ("Não", "nao"),
        ("Abstenção", "abstencao"),
        ("Obstrução", "obstrucao"),
        ("Artigo 17", "presidente"),
        ("?", "outro"),
    ],
)
def test_normalizar_voto_camara(tipo, esperado):
    assert votacoes.normalizar_voto_camara(tipo) == esperado


@pytest.mark.parametrize(
    ("sigla", "esperado"),
    [
        ("Sim", "sim"),
        ("Não", "nao"),
        ("P-NRV", "presente_sem_voto"),
        ("AP", "ausente"),
        ("LS", "ausente"),
        ("Presidente (art. 51 RISF)", "presidente"),
        ("XYZ", "outro"),
    ],
)
def test_normalizar_voto_senado(sigla, esperado):
    assert votacoes.normalizar_voto_senado(sigla, LEGENDA) == esperado


def test_orientacao_do_partido_por_partido_e_federacao():
    orientacoes = {"PL": "Sim", "Fdr PT-PCdoB-PV": "Não", "Bl UniPpPsd...": "Sim", "Governo": "Não"}
    assert votacoes.orientacao_do_partido("PL", orientacoes) == "Sim"
    assert votacoes.orientacao_do_partido("PCdoB", orientacoes) == "Não"
    assert (
        votacoes.orientacao_do_partido("UNIÃO", orientacoes) is None
    )  # bloco abreviado, sem correspondência


def test_linhas_camara_liga_ao_cadastro_e_registra_orientacoes():
    v = VotacaoChave("t", "T", "camara", "1-1", "2026-05-27", "1º turno", True, "PEC 1/2026")
    bruto = {
        "votos": [
            {
                "tipoVoto": "Sim",
                "deputado_": {"id": 10, "nome": "Fulana", "siglaPartido": "PT", "siglaUf": "SP"},
            },
            {
                "tipoVoto": "Não",
                "deputado_": {"id": 11, "nome": "Ciclano", "siglaPartido": "NOVO", "siglaUf": "RJ"},
            },
        ],
        "orientacoes": [
            {"siglaPartidoBloco": "Fdr PT-PCdoB-PV", "orientacaoVoto": "Sim"},
            {"siglaPartidoBloco": "Governo", "orientacaoVoto": "Sim"},
        ],
    }
    linhas = votacoes.linhas_camara(v, bruto, {"10": "fulana"})
    assert [
        (x["pessoa_id"], x["voto"], x["orientacao_partido"], x["orientacao_governo"]) for x in linhas
    ] == [
        ("fulana", "sim", "Sim", "Sim"),
        (None, "nao", None, "Sim"),
    ]
    assert votacoes.placar(linhas) == {"sim": 1, "nao": 1, "abstencao": 0, "obstrucao": 0}


def test_linhas_senado_usa_a_legenda_oficial():
    v = VotacaoChave("t", "T", "senado", "7106", "2026-10-14", "1º turno", True, "PEC 221/2019")
    bruto = {
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
    linhas = votacoes.linhas_senado(v, bruto, {"5": "a"}, LEGENDA)
    assert [(x["pessoa_id"], x["voto"], x["voto_descricao"]) for x in linhas] == [
        ("a", "sim", "Sim"),
        (None, "ausente", "Licença saúde"),
    ]
