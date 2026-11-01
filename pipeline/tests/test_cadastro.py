from conftest import candidatos

from puxa import cadastro
from puxa.cadastro import Papel, Registro


def _dep(id_, nome, uf="SP", partido="AAA", cpf=None, nascimento=None):
    return (
        {"id": id_, "nome": nome.title(), "siglaUf": uf, "siglaPartido": partido, "urlFoto": f"foto{id_}"},
        {
            "nomeCivil": nome,
            "cpf": cpf,
            "dataNascimento": nascimento,
            "ultimoStatus": {"nomeEleitoral": nome.title()},
        },
    )


def test_liga_camara_e_tse_pelo_cpf():
    dep, det = _dep(10, "MARIA SOUZA", cpf="00000000272", nascimento="1970-04-03")
    df26 = candidatos(
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
    registros = cadastro.registros_camara([dep], {10: det}) + cadastro.registros_tse_2026(df26)
    grupos, pendencias = cadastro.resolver(registros)
    pessoas = cadastro.montar_pessoas(grupos, {})
    assert len(pessoas) == 1 and not pendencias
    p = pessoas[0]
    assert (p.camara_id, p.tse_sq_2026, p.nome_urna) == ("10", "2", "MARIA")
    assert {(x.cargo, x.situacao) for x in p.papeis} == {
        ("deputado_federal", "em_exercicio"),
        ("deputado_federal", "eleito_2026"),
    }


def test_liga_senado_e_tse_por_nascimento_e_nome_parecido():
    senador = {
        "codigo": "5",
        "nome": "Zé Lima",
        "nome_completo": "José Carlos Lima",
        "partido": "BBB",
        "uf": "RJ",
        "participacao": "Titular",
    }
    detalhe = {"DadosBasicosParlamentar": {"DataNascimento": "1965-01-02"}}
    df26 = candidatos(
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
    registros = cadastro.registros_senado([senador], {"5": detalhe}) + cadastro.registros_tse_2026(df26)
    grupos, _ = cadastro.resolver(registros)
    pessoas = cadastro.montar_pessoas(grupos, {})
    assert len(pessoas) == 1
    assert pessoas[0].senado_codigo == "5" and pessoas[0].cpf == "00000000434"


def test_nunca_une_cpfs_diferentes_e_registra_pendencia():
    a = Registro(
        "camara",
        "1",
        "ANA PAULA",
        cpf="00000000191",
        nascimento="1980-01-01",
        uf="SP",
        papeis=[Papel("deputado_federal", "em_exercicio", "SP", "A", "camara")],
    )
    b = Registro(
        "tse2026",
        "9",
        "ANA PAULA",
        cpf="00000000272",
        nascimento="1980-01-01",
        uf="SP",
        papeis=[Papel("deputado_federal", "eleito_2026", "SP", "A", "tse2026")],
    )
    grupos, pendencias = cadastro.resolver([a, b])
    assert len(grupos) == 2
    assert [p.tipo for p in pendencias] == ["conflito_cpf"]


def test_descarta_candidatos_sem_papel():
    df26 = candidatos(
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
    grupos, _ = cadastro.resolver(cadastro.registros_tse_2026(df26))
    assert grupos == []


def test_governador_que_disputou_outro_cargo_passa_para_o_vice():
    df22 = candidatos(
        [
            ("1", "MG", "GOVERNADOR", "100", "TITULAR UM", "TITULAR", "-4", "", "AAA", "ELEITO"),
            ("1", "MG", "VICE-GOVERNADOR", "101", "VICE UM", "VICE", "-4", "", "AAA", "ELEITO"),
            ("1", "BA", "GOVERNADOR", "200", "TITULAR DOIS", "DOIS", "-4", "", "BBB", "ELEITO"),
            ("1", "BA", "VICE-GOVERNADOR", "201", "VICE DOIS", "VICE2", "-4", "", "BBB", "ELEITO"),
            ("2", "BR", "PRESIDENTE", "300", "PRESIDENTE ATUAL", "PRES", "-4", "", "CCC", "ELEITO"),
        ]
    )
    df26 = candidatos(
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
    registros, pendencias = cadastro.executivo_em_exercicio(df22, df26, ajustes=[])
    por_uf = {p.uf: r for r in registros for p in r.papeis if p.cargo == "governador"}
    assert por_uf["MG"].nome_civil == "VICE UM" and por_uf["MG"].papeis[0].inferido
    assert por_uf["BA"].nome_civil == "TITULAR DOIS" and not por_uf["BA"].papeis[0].inferido
    assert any(r.papeis[0].cargo == "presidente" for r in registros)
    assert [p.tipo for p in pendencias] == ["governador_inferido"]

    # O titular de MG continua no cadastro como senador eleito; o de BA vira uma pessoa só (2022 + 2026).
    grupos, _ = cadastro.resolver(registros + cadastro.registros_tse_2026(df26))
    pessoas = {p.nome_civil: p for p in cadastro.montar_pessoas(grupos, {})}
    assert {(x.cargo, x.situacao) for x in pessoas["TITULAR DOIS"].papeis} == {
        ("governador", "em_exercicio"),
        ("governador", "eleito_2026"),
    }
    assert pessoas["TITULAR DOIS"].tse_sq_2022 == "200" and pessoas["TITULAR DOIS"].tse_sq_2026 == "600"


def test_ajuste_manual_tem_prioridade_sobre_a_inferencia():
    df22 = candidatos([("1", "MG", "GOVERNADOR", "100", "TITULAR UM", "T", "-4", "", "AAA", "ELEITO")])
    ajustes = [{"uf": "MG", "nome_civil": "OUTRA PESSOA", "partido": "ZZZ", "motivo": "fonte X"}]
    registros, _ = cadastro.executivo_em_exercicio(df22, candidatos([]), ajustes)
    assert registros[0].nome_civil == "OUTRA PESSOA" and registros[0].papeis[0].observacao == "fonte X"


def test_ids_sao_estaveis_e_resolvem_homonimos():
    def grupo(chave_id, nome, uf):
        return [
            Registro(
                "camara",
                chave_id,
                nome,
                nome_urna=nome,
                uf=uf,
                papeis=[Papel("deputado_federal", "em_exercicio", uf, "A", "camara")],
            )
        ]

    grupos = [grupo("1", "Pastor Joao", "SP"), grupo("2", "Pastor Joao", "RJ")]
    ids = cadastro.atribuir_ids(grupos, {})
    assert sorted(ids) == ["pastor-joao", "pastor-joao-sp"] or sorted(ids) == [
        "pastor-joao",
        "pastor-joao-rj",
    ]

    # Na execução seguinte, cada um mantém o seu, mesmo que a ordem mude.
    anteriores = {"camara:1": ids[0], "camara:2": ids[1]}
    assert cadastro.atribuir_ids(list(reversed(grupos)), anteriores) == [ids[1], ids[0]]
