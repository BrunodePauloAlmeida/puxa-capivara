import io
import zipfile

import polars as pl
import pytest

COLUNAS = [
    "NR_TURNO",
    "SG_UF",
    "DS_CARGO",
    "SQ_CANDIDATO",
    "NM_CANDIDATO",
    "NM_URNA_CANDIDATO",
    "NR_CPF_CANDIDATO",
    "DT_NASCIMENTO",
    "SG_PARTIDO",
    "DS_SIT_TOT_TURNO",
]


def candidatos(linhas: list[tuple]) -> pl.DataFrame:
    """DataFrame no formato do consulta_cand do TSE (só as colunas usadas)."""
    return pl.DataFrame(
        [dict(zip(COLUNAS, linha, strict=True)) for linha in linhas], schema=dict.fromkeys(COLUNAS, pl.String)
    )


@pytest.fixture
def zip_tse(tmp_path):
    """Zip com um CSV nacional em latin-1 e ';', como o TSE publica."""
    cabecalho = ";".join(f'"{c}"' for c in COLUNAS)
    linhas = [
        '"1";"BR";"PRESIDENTE";"1";"JOÃO DA SILVA";"JOÃO";"00000000191";"01/02/1960";"AAA";"2º TURNO"',
        '"2";"BR";"PRESIDENTE";"1";"JOÃO DA SILVA";"JOÃO";"00000000191";"01/02/1960";"AAA";"ELEITO"',
        '"1";"SP";"DEPUTADO FEDERAL";"2";"MARIA SOUZA";"MARIA";"00000000272";"03/04/1970";"BBB";"ELEITO POR QP"',
        '"1";"SP";"DEPUTADO FEDERAL";"3";"PEDRO LIMA";"PEDRO";"00000000353";"05/06/1980";"CCC";"SUPLENTE"',
    ]
    conteudo = "\n".join([cabecalho, *linhas]).encode("latin-1")
    arquivo = tmp_path / "consulta_cand_2026.zip"
    with zipfile.ZipFile(arquivo, "w") as z:
        z.writestr("consulta_cand_2026_SP.csv", b"ignorar")
        z.writestr("consulta_cand_2026_BRASIL.csv", io.BytesIO(conteudo).getvalue())
    return arquivo
