from puxa.coletores import tse


def test_ler_candidatos_usa_csv_nacional_em_latin1(zip_tse):
    df = tse.ler_candidatos(zip_tse)
    assert df.height == 4
    assert df["NM_CANDIDATO"][0] == "JOÃO DA SILVA"


def test_eleitos_fica_com_o_ultimo_turno(zip_tse):
    df = tse.ler_candidatos(zip_tse)
    resultado = tse.eleitos(df, {"PRESIDENTE", "DEPUTADO FEDERAL"})
    assert sorted(resultado["NM_URNA_CANDIDATO"].to_list()) == ["JOÃO", "MARIA"]
    joao = resultado.filter(resultado["SQ_CANDIDATO"] == "1")
    assert joao["NR_TURNO"][0] == "2"


def test_cpf_valido_descarta_mascaras_do_tse():
    assert tse.cpf_valido("-4") is None
    assert tse.cpf_valido("#NULO") is None
    assert tse.cpf_valido("7068093868") == "07068093868"


def test_data_iso():
    assert tse.data_iso("06/10/1945") == "1945-10-06"
    assert tse.data_iso("") is None
