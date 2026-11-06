import io
import zipfile

import polars as pl
import pytest

COLUMNS = [
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


def candidates(rows: list[tuple]) -> pl.DataFrame:
    """DataFrame in the format of the TSE consulta_cand (only the columns used)."""
    return pl.DataFrame(
        [dict(zip(COLUMNS, row, strict=True)) for row in rows], schema=dict.fromkeys(COLUMNS, pl.String)
    )


@pytest.fixture
def tse_zip(tmp_path):
    """Zip with a national CSV in latin-1 and ';', as the TSE publishes it."""
    header = ";".join(f'"{c}"' for c in COLUMNS)
    rows = [
        '"1";"BR";"PRESIDENTE";"1";"JOÃO DA SILVA";"JOÃO";"00000000191";"01/02/1960";"AAA";"2º TURNO"',
        '"2";"BR";"PRESIDENTE";"1";"JOÃO DA SILVA";"JOÃO";"00000000191";"01/02/1960";"AAA";"ELEITO"',
        '"1";"SP";"DEPUTADO FEDERAL";"2";"MARIA SOUZA";"MARIA";"00000000272";"03/04/1970";"BBB";"ELEITO POR QP"',
        '"1";"SP";"DEPUTADO FEDERAL";"3";"PEDRO LIMA";"PEDRO";"00000000353";"05/06/1980";"CCC";"SUPLENTE"',
    ]
    content = "\n".join([header, *rows]).encode("latin-1")
    file = tmp_path / "consulta_cand_2026.zip"
    with zipfile.ZipFile(file, "w") as z:
        z.writestr("consulta_cand_2026_SP.csv", b"ignore")
        z.writestr("consulta_cand_2026_BRASIL.csv", io.BytesIO(content).getvalue())
    return file
