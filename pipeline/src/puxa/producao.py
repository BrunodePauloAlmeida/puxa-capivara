"""Produção legislativa: projetos apresentados por cada parlamentar e quantos viraram norma (lei, emenda
constitucional, decreto legislativo, resolução).

Janela: proposições apresentadas desde 01/02/2019 (legislaturas 56 e 57).
Tipos contados: projetos de lei, de lei complementar, de decreto legislativo, de resolução e PECs. Requerimentos,
indicações e emendas ficam de fora, porque existem aos milhares e inflariam a contagem sem dizer muito.

Câmara: arquivos anuais (proposicoes-{ano}.csv e proposicoesAutores-{ano}.csv), um download por ano em vez de
milhares de chamadas à API. "Primeiro autor" = ordemAssinatura 1; os demais proponentes são coautores.
Senado: /processo?codigoParlamentarAutor=. "Primeiro autor" = primeiro nome do campo `autoria`.

Limitação conhecida: quem mudou de Casa (ex.: deputado até 2022 e senador desde 2023) só tem contada a produção
na Casa em que está agora.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date
from pathlib import Path

import polars as pl

from puxa.coletores import senado
from puxa.config import BRUTO, CAMARA_ARQUIVOS
from puxa.http import Cliente
from puxa.texto import normalizar_nome

log = logging.getLogger(__name__)

DESDE = "2019-02-01"
TIPOS_CAMARA = {"PL", "PLP", "PEC", "PDL", "PRC"}
TIPOS_SENADO = {"PL", "PLP", "PEC", "PDL", "PRS"}
SITUACAO_NORMA_CAMARA = "Transformado em Norma Jurídica"
MAX_DESTAQUES = 5

_NORMA_NO_DESPACHO = re.compile(r"Transformad[oa] n[ao]s? (.+?\d[\d.]*/\d{4})", re.IGNORECASE)


def norma_do_despacho(despacho: str | None) -> str | None:
    """'Transformado na Lei Ordinária 15270/2025. DOU ...' -> 'Lei Ordinária 15270/2025'."""
    if not despacho:
        return None
    m = _NORMA_NO_DESPACHO.search(despacho)
    return m.group(1).strip() if m else None


# --------------------------------------------------------------------------------------------------------------
# Câmara


def baixar_anuais_camara(
    cli: Cliente, anos: range, pasta: Path = BRUTO / "camara" / "arquivos"
) -> list[tuple[Path, Path]]:
    pares = []
    for ano in anos:
        prop = cli.baixar(
            f"{CAMARA_ARQUIVOS}/proposicoes/csv/proposicoes-{ano}.csv", pasta / f"proposicoes-{ano}.csv"
        )
        aut = cli.baixar(
            f"{CAMARA_ARQUIVOS}/proposicoesAutores/csv/proposicoesAutores-{ano}.csv",
            pasta / f"proposicoesAutores-{ano}.csv",
        )
        pares.append((prop, aut))
    return pares


_COLUNAS_PROP = [
    "id",
    "siglaTipo",
    "numero",
    "ano",
    "ementa",
    "dataApresentacao",
    "ultimoStatus_dataHora",
    "ultimoStatus_descricaoSituacao",
    "ultimoStatus_despacho",
]
_COLUNAS_AUT = ["idProposicao", "idDeputadoAutor", "ordemAssinatura", "proponente"]


def ler_anuais_camara(pares: list[tuple[Path, Path]]) -> tuple[pl.DataFrame, pl.DataFrame]:
    def ler(arquivo: Path, colunas: list[str]) -> pl.DataFrame:
        return pl.read_csv(arquivo, separator=";", infer_schema=False, columns=colunas, encoding="utf8-lossy")

    proposicoes = pl.concat([ler(p, _COLUNAS_PROP) for p, _ in pares]).unique(subset="id", keep="last")
    autores = pl.concat([ler(a, _COLUNAS_AUT) for _, a in pares]).unique()
    return proposicoes, autores


def producao_camara(proposicoes: pl.DataFrame, autores: pl.DataFrame, pessoa_por_camara: dict[str, str]):
    projetos = proposicoes.filter(
        pl.col("siglaTipo").is_in(TIPOS_CAMARA) & (pl.col("dataApresentacao").str.slice(0, 10) >= DESDE)
    ).with_columns(
        (pl.col("ultimoStatus_descricaoSituacao") == SITUACAO_NORMA_CAMARA).alias("virou_norma"),
        (pl.col("siglaTipo") + " " + pl.col("numero") + "/" + pl.col("ano")).alias("identificacao"),
    )
    autoria = (
        autores.filter(
            (pl.col("proponente") == "1") & pl.col("idDeputadoAutor").is_in(list(pessoa_por_camara))
        )
        .with_columns((pl.col("ordemAssinatura") == "1").alias("primeiro_autor"))
        .join(projetos, left_on="idProposicao", right_on="id", how="inner")
    )
    resumo = _resumir(autoria, chave="idDeputadoAutor", tipo="siglaTipo")
    destaques = (
        autoria.filter(pl.col("virou_norma") & pl.col("primeiro_autor"))
        .with_columns(
            pl.col("ultimoStatus_despacho")
            .map_elements(norma_do_despacho, return_dtype=pl.String)
            .alias("norma"),
            pl.col("ultimoStatus_dataHora").str.slice(0, 10).alias("data_norma"),
        )
        .select(
            pl.col("idDeputadoAutor").alias("parlamentar_id"),
            "identificacao",
            "ementa",
            "norma",
            "data_norma",
        )
    )
    return _com_pessoa(resumo, destaques, pessoa_por_camara, "camara")


# --------------------------------------------------------------------------------------------------------------
# Senado


def processos_do_senador(cli: Cliente, codigo: str, pasta: Path = BRUTO / "senado" / "autoria") -> list[dict]:
    arquivo = pasta / f"{codigo}.json"
    if arquivo.exists():
        return json.loads(arquivo.read_text())
    dados = senado.processos(cli, codigoParlamentarAutor=codigo)
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(json.dumps(dados, ensure_ascii=False))
    return dados


def e_primeiro_autor(autoria: str | None, nome_parlamentar: str) -> bool:
    """'Senador Alan Rick (UNIÃO/AC), Senador Fulano (...)' -> o primeiro nome é o do senador?"""
    if not autoria:
        return False
    primeiro = normalizar_nome(autoria.split(",")[0].split("(")[0])
    primeiro = re.sub(r"^(SENADORA?|DEPUTAD[OA]) (FEDERAL )?", "", primeiro).strip()
    return primeiro == normalizar_nome(nome_parlamentar)


def linhas_senado(codigo: str, nome_parlamentar: str, processos: list[dict]) -> list[dict]:
    linhas = []
    for p in processos:
        identificacao = p.get("identificacao") or ""
        sigla = identificacao.split(" ")[0]
        if sigla not in TIPOS_SENADO or (p.get("dataApresentacao") or "") < DESDE:
            continue
        linhas.append(
            {
                "parlamentar_id": codigo,
                "identificacao": identificacao,
                "tipo": sigla,
                "ementa": p.get("ementa"),
                "primeiro_autor": e_primeiro_autor(p.get("autoria"), nome_parlamentar),
                "virou_norma": bool(p.get("normaGerada")),
                "norma": p.get("normaGerada"),
                "data_norma": p.get("dataSituacaoAtual") if p.get("normaGerada") else None,
            }
        )
    return linhas


def producao_senado(linhas: list[dict], pessoa_por_senado: dict[str, str]):
    schema = {
        "parlamentar_id": pl.String,
        "identificacao": pl.String,
        "tipo": pl.String,
        "ementa": pl.String,
        "primeiro_autor": pl.Boolean,
        "virou_norma": pl.Boolean,
        "norma": pl.String,
        "data_norma": pl.String,
    }
    autoria = pl.DataFrame(linhas, schema=schema)
    resumo = _resumir(autoria, chave="parlamentar_id", tipo="tipo")
    destaques = autoria.filter(pl.col("virou_norma") & pl.col("primeiro_autor")).select(
        "parlamentar_id", "identificacao", "ementa", "norma", "data_norma"
    )
    return _com_pessoa(resumo, destaques, pessoa_por_senado, "senado")


# --------------------------------------------------------------------------------------------------------------
# Comum


def _resumir(autoria: pl.DataFrame, chave: str, tipo: str) -> pl.DataFrame:
    if autoria.is_empty():
        return pl.DataFrame(
            schema={
                "parlamentar_id": pl.String,
                "apresentados": pl.UInt32,
                "como_primeiro_autor": pl.UInt32,
                "viraram_norma": pl.UInt32,
                "viraram_norma_como_primeiro_autor": pl.UInt32,
                "por_tipo": pl.String,
            }
        )
    por_tipo = (
        autoria.group_by(chave, tipo)
        .len()
        .group_by(chave)
        .agg(pl.struct(tipo, "len").alias("tipos"))
        .with_columns(
            pl.col("tipos")
            .map_elements(
                lambda s: json.dumps({x[tipo]: x["len"] for x in s}, sort_keys=True), return_dtype=pl.String
            )
            .alias("por_tipo")
        )
        .drop("tipos")
    )
    return (
        autoria.group_by(chave)
        .agg(
            pl.len().alias("apresentados"),
            pl.col("primeiro_autor").sum().alias("como_primeiro_autor"),
            pl.col("virou_norma").sum().alias("viraram_norma"),
            (pl.col("virou_norma") & pl.col("primeiro_autor"))
            .sum()
            .alias("viraram_norma_como_primeiro_autor"),
        )
        .join(por_tipo, on=chave)
        .rename({chave: "parlamentar_id"})
    )


def _com_pessoa(resumo: pl.DataFrame, destaques: pl.DataFrame, mapa: dict[str, str], casa: str):
    mapa_df = pl.DataFrame(
        {"parlamentar_id": list(mapa), "pessoa_id": list(mapa.values())},
        schema={"parlamentar_id": pl.String, "pessoa_id": pl.String},
    )
    # Todo parlamentar em exercício aparece, mesmo com zero projetos.
    resumo = (
        mapa_df.join(resumo, on="parlamentar_id", how="left")
        .with_columns(
            pl.lit(casa).alias("casa"),
            pl.lit(DESDE).alias("desde"),
            pl.col(
                "apresentados", "como_primeiro_autor", "viraram_norma", "viraram_norma_como_primeiro_autor"
            )
            .fill_null(0)
            .cast(pl.UInt32),
            pl.col("por_tipo").fill_null("{}"),
        )
        .sort("pessoa_id")
    )
    destaques = (
        destaques.join(mapa_df, on="parlamentar_id", how="inner")
        .with_columns(pl.lit(casa).alias("casa"))
        .sort(["pessoa_id", "data_norma"], descending=[False, True], nulls_last=True)
        .group_by("pessoa_id", maintain_order=True)
        .head(MAX_DESTAQUES)
    )
    return resumo, destaques


def norma_pelo_senado(cli: Cliente, identificacao: str, pasta: Path | None = None) -> str | None:
    """Norma gerada por uma proposição, pelo processo no Senado. A numeração é unificada entre as Casas desde 2019,
    e o Senado registra a norma também dos projetos que nasceram na Câmara."""
    sigla, resto = identificacao.split(" ", 1)
    numero, ano = resto.split("/")
    pasta = pasta or BRUTO / "senado" / "processos"
    arquivo = pasta / f"{sigla}-{numero}-{ano}.json"
    if arquivo.exists():
        processos = json.loads(arquivo.read_text())
    else:
        processos = senado.processos(cli, sigla=sigla, numero=numero, ano=ano)
        pasta.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(json.dumps(processos, ensure_ascii=False))
    return next((p["normaGerada"] for p in processos if p.get("normaGerada")), None)


def completar_normas(cli: Cliente, destaques: pl.DataFrame) -> pl.DataFrame:
    """O arquivo da Câmara quase nunca traz o número da lei; busca no Senado só para os destaques."""
    faltando = destaques.filter(pl.col("norma").is_null())["identificacao"].unique().to_list()
    if not faltando:
        return destaques
    achadas = {identificacao: norma_pelo_senado(cli, identificacao) for identificacao in faltando}
    return destaques.with_columns(
        pl.coalesce(
            pl.col("norma"),
            pl.col("identificacao").replace_strict(achadas, default=None, return_dtype=pl.String),
        ).alias("norma")
    )


def montar(
    cli: Cliente, pessoas: pl.DataFrame, ano_final: int | None = None
) -> tuple[pl.DataFrame, pl.DataFrame]:
    ano_final = ano_final or date.today().year
    pessoa_por_camara = {
        r["camara_id"]: r["id"]
        for r in pessoas.select("id", "camara_id").iter_rows(named=True)
        if r["camara_id"]
    }
    pessoa_por_senado = {
        r["senado_codigo"]: r["id"]
        for r in pessoas.select("id", "senado_codigo").iter_rows(named=True)
        if r["senado_codigo"]
    }

    log.info("Câmara: arquivos anuais de proposições %s–%s", DESDE[:4], ano_final)
    proposicoes, autores = ler_anuais_camara(baixar_anuais_camara(cli, range(int(DESDE[:4]), ano_final + 1)))
    resumo_c, destaques_c = producao_camara(proposicoes, autores, pessoa_por_camara)
    log.info("Senado: número da norma de %d destaques da Câmara", destaques_c.height)
    destaques_c = completar_normas(cli, destaques_c)

    log.info("Senado: autoria de %d senadores", len(pessoa_por_senado))
    nomes = {s["codigo"]: s["nome"] for s in senado.senadores_em_exercicio(cli)}
    linhas: list[dict] = []
    for codigo in pessoa_por_senado:
        linhas.extend(linhas_senado(codigo, nomes.get(codigo, ""), processos_do_senador(cli, codigo)))
    resumo_s, destaques_s = producao_senado(linhas, pessoa_por_senado)

    return pl.concat([resumo_c, resumo_s], how="diagonal"), pl.concat(
        [destaques_c, destaques_s], how="diagonal"
    )


def salvar(resumo: pl.DataFrame, destaques: pl.DataFrame, pasta: Path) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    for nome, df in (("producao", resumo), ("destaques", destaques)):
        df.write_parquet(pasta / f"{nome}.parquet")
        df.write_csv(pasta / f"{nome}.csv")
