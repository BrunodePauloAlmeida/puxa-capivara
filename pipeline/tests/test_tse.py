from puxa.collectors import tse


def test_read_candidates_uses_national_csv_in_latin1(tse_zip):
    df = tse.read_candidates(tse_zip)
    assert df.height == 4
    assert df["NM_CANDIDATO"][0] == "JOÃO DA SILVA"


def test_elected_keeps_the_last_round(tse_zip):
    df = tse.read_candidates(tse_zip)
    result = tse.elected(df, {"PRESIDENTE", "DEPUTADO FEDERAL"})
    assert sorted(result["NM_URNA_CANDIDATO"].to_list()) == ["JOÃO", "MARIA"]
    joao = result.filter(result["SQ_CANDIDATO"] == "1")
    assert joao["NR_TURNO"][0] == "2"


def test_valid_cpf_discards_tse_masks():
    assert tse.valid_cpf("-4") is None
    assert tse.valid_cpf("#NULO") is None
    assert tse.valid_cpf("7068093868") == "07068093868"


def test_iso_date():
    assert tse.iso_date("06/10/1945") == "1945-10-06"
    assert tse.iso_date("") is None
