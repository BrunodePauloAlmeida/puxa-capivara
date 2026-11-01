"""TSE: arquivos do Portal de Dados Abertos (CDN, sem chave).

Validado em 01/11/2026: consulta_cand_2026 já traz o resultado (eleitos) e o CPF. Nos arquivos de 2018 e 2022
o CPF vem mascarado (-4) e a data de nascimento vem vazia, então o cruzamento com eleições antigas é por nome."""

import io
import zipfile
from pathlib import Path

import polars as pl

from puxa.config import BRUTO, TSE_CDN
from puxa.http import Cliente

SITUACOES_ELEITO = {"ELEITO", "ELEITO POR QP", "ELEITO POR MÉDIA"}
CPF_INVALIDOS = {"", "-1", "-3", "-4", "#NULO", "#NULO#"}


def baixar_candidatos(cli: Cliente, ano: int, pasta: Path = BRUTO / "tse") -> Path:
    return cli.baixar(f"{TSE_CDN}/consulta_cand/consulta_cand_{ano}.zip", pasta / f"consulta_cand_{ano}.zip")


def ler_candidatos(arquivo_zip: Path) -> pl.DataFrame:
    """Lê o CSV nacional (…_BRASIL.csv) de dentro do zip. Tudo como texto; o TSE usa latin-1 e ';'."""
    with zipfile.ZipFile(arquivo_zip) as z:
        nome = next(n for n in z.namelist() if n.upper().endswith("_BRASIL.CSV"))
        texto = z.read(nome).decode("latin-1")
    return pl.read_csv(io.StringIO(texto), separator=";", infer_schema=False)


def ultima_situacao(df: pl.DataFrame) -> pl.DataFrame:
    """Quem foi ao 2º turno aparece duas vezes; fica a linha do turno mais recente."""
    return df.sort("NR_TURNO").unique(subset=["SQ_CANDIDATO"], keep="last", maintain_order=True)


def eleitos(df: pl.DataFrame, cargos: set[str]) -> pl.DataFrame:
    df = ultima_situacao(df)
    return df.filter(pl.col("DS_CARGO").is_in(cargos) & pl.col("DS_SIT_TOT_TURNO").is_in(SITUACOES_ELEITO))


def cpf_valido(cpf: str | None) -> str | None:
    if cpf is None or cpf.strip() in CPF_INVALIDOS:
        return None
    digitos = "".join(c for c in cpf if c.isdigit())
    return digitos.zfill(11) if digitos else None


def data_iso(data_br: str | None) -> str | None:
    """'06/10/1945' -> '1945-10-06'."""
    if not data_br or "/" not in data_br:
        return None
    dia, mes, ano = data_br.split("/")
    return f"{ano}-{mes.zfill(2)}-{dia.zfill(2)}"
