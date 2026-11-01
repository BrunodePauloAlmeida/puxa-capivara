"""Votações-chave: lê a lista curada (curadoria/votacoes_chave.yaml), baixa o voto de cada parlamentar nas duas
Casas e liga cada voto ao cadastro mestre.

Categorias de voto (campo `voto`; o original fica em `voto_original`):
  sim, nao, abstencao, obstrucao, presidente (presidia a sessão e não vota), presente_sem_voto, ausente,
  voto_secreto, outro.
Na Câmara, a API só lista quem registrou voto: quem não aparece estava ausente ou não tinha mandato na data.
No Senado, a lista traz todos os 81, com o motivo da ausência (licença, missão, atividade parlamentar...).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import polars as pl
import yaml

from puxa.coletores import senado
from puxa.config import BRUTO, CAMARA_API, SENADO_API
from puxa.http import Cliente
from puxa.texto import normalizar_nome

log = logging.getLogger(__name__)

CASAS = ("camara", "senado")


@dataclass
class VotacaoChave:
    tema_id: str
    titulo: str
    casa: str
    id: str
    data: str
    descricao: str
    principal: bool
    proposicao: str


# --------------------------------------------------------------------------------------------------------------
# Curadoria


def carregar_temas(arquivo: Path) -> list[dict]:
    temas = (yaml.safe_load(arquivo.read_text()) or {}).get("votacoes_chave") or []
    validar_temas(temas)
    return temas


def validar_temas(temas: list[dict]) -> None:
    """Falha cedo se a curadoria tiver erro de preenchimento."""
    ids = [t["id"] for t in temas]
    repetidos = {i for i in ids if ids.count(i) > 1}
    if repetidos:
        raise ValueError(f"IDs de tema repetidos: {sorted(repetidos)}")
    for t in temas:
        for campo in ("titulo", "proposicao", "resumo", "significado_sim"):
            if not t.get(campo):
                raise ValueError(f"Tema {t['id']}: falta o campo '{campo}'")
        for casa in CASAS:
            votacoes = t.get(casa) or []
            explicacao = (t.get("sem_votacao_nominal") or {}).get(casa)
            if not votacoes and not explicacao:
                raise ValueError(
                    f"Tema {t['id']}: sem votações na {casa} e sem explicação em sem_votacao_nominal"
                )
            if votacoes and sum(bool(v.get("principal")) for v in votacoes) != 1:
                raise ValueError(f"Tema {t['id']}: a {casa} precisa de exatamente uma votação principal")


def votacoes_da_curadoria(temas: list[dict]) -> list[VotacaoChave]:
    resultado = []
    for t in temas:
        for casa in CASAS:
            for v in t.get(casa) or []:
                resultado.append(
                    VotacaoChave(
                        tema_id=t["id"],
                        titulo=t["titulo"],
                        casa=casa,
                        id=str(v["id"]),
                        data=str(v["data"]),
                        descricao=v["descricao"],
                        principal=bool(v.get("principal")),
                        proposicao=v.get("proposicao") or t["proposicao"],
                    )
                )
    return resultado


def separar_proposicao(texto: str) -> tuple[str, int, int]:
    """'PEC 45/2019' -> ('PEC', 45, 2019)."""
    m = re.search(r"([A-Z]+)\s+(\d+)/(\d{4})", texto)
    if not m:
        raise ValueError(f"Proposição em formato inesperado: {texto!r}")
    return m.group(1), int(m.group(2)), int(m.group(3))


# --------------------------------------------------------------------------------------------------------------
# Normalização


VOTOS_CAMARA = {
    "SIM": "sim",
    "NAO": "nao",
    "ABSTENCAO": "abstencao",
    "OBSTRUCAO": "obstrucao",
    "ARTIGO": "presidente",  # "Artigo 17": quem preside a sessão não vota
}

VOTOS_SENADO = {
    "Sim": "sim",
    "Não": "nao",
    "Abstenção": "abstencao",
    "P-OD": "obstrucao",
    "Presidente (art. 51 RISF)": "presidente",
    "P-NRV": "presente_sem_voto",
    "Votou": "voto_secreto",
    "NCom": "ausente",
}

# Siglas que aparecem nos votos mas não estão na tabela oficial de tipos de comparecimento.
DESCRICOES_SENADO_EXTRAS = {
    "P-NRV": "Presente, não registrou voto",
    "P-OD": "Presente, obstrução declarada",
    "NCom": "Não compareceu",
    "Votou": "Votou (votação secreta)",
    "Presidente (art. 51 RISF)": "Presidente da sessão (não vota)",
}


def normalizar_voto_camara(tipo: str | None) -> str:
    chave = normalizar_nome(tipo).split(" ")[0] if tipo else ""
    return VOTOS_CAMARA.get(chave, "outro")


def normalizar_voto_senado(sigla: str | None, legenda: dict[str, str]) -> str:
    if sigla in VOTOS_SENADO:
        return VOTOS_SENADO[sigla]
    if sigla in legenda:  # licenças, missões, atividade parlamentar etc.
        return "ausente"
    return "outro"


def orientacao_do_partido(partido: str | None, orientacoes: dict[str, str]) -> str | None:
    """Orientação da bancada do deputado: partido isolado ou federação ('Fdr PT-PCdoB-PV').
    Blocos aparecem abreviados pela Câmara ('Bl UniPpPsd...') e ficam sem correspondência por enquanto."""
    if not partido:
        return None
    alvo = normalizar_nome(partido)
    for sigla, orientacao in orientacoes.items():
        nome = normalizar_nome(sigla)
        if nome == alvo:
            return orientacao or None
        if sigla.startswith("Fdr ") and alvo in {normalizar_nome(p) for p in sigla[4:].split("-")}:
            return orientacao or None
    return None


# --------------------------------------------------------------------------------------------------------------
# Coleta (com cache das respostas brutas)


def _cache_json(arquivo: Path, obter) -> Any:
    if arquivo.exists():
        return json.loads(arquivo.read_text())
    dados = obter()
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    arquivo.write_text(json.dumps(dados, ensure_ascii=False))
    return dados


def coletar_camara(cli: Cliente, id_votacao: str, pasta: Path = BRUTO / "camara" / "votacoes") -> dict:
    def obter() -> dict:
        return {
            "votacao": cli.get_json(f"{CAMARA_API}/votacoes/{id_votacao}")["dados"],
            "votos": cli.get_json(f"{CAMARA_API}/votacoes/{id_votacao}/votos")["dados"],
            "orientacoes": cli.get_json(f"{CAMARA_API}/votacoes/{id_votacao}/orientacoes")["dados"],
        }

    return _cache_json(pasta / f"{id_votacao}.json", obter)


def coletar_senado(cli: Cliente, v: VotacaoChave, pasta: Path = BRUTO / "senado" / "votacoes") -> dict:
    def obter() -> dict:
        sigla, numero, ano = separar_proposicao(v.proposicao)
        for votacao in senado.votacoes(cli, sigla=sigla, numero=numero, ano=ano):
            if str(votacao["codigoSessaoVotacao"]) == v.id:
                return votacao
        raise LookupError(f"Votação {v.id} não encontrada no Senado para {v.proposicao}")

    return _cache_json(pasta / f"{v.id}.json", obter)


def legenda_senado(cli: Cliente, pasta: Path = BRUTO / "senado") -> dict[str, str]:
    corpo = _cache_json(
        pasta / "tipos_comparecimento.json",
        lambda: cli.get_json(f"{SENADO_API}/plenario/lista/tiposComparecimento"),
    )
    tipos = senado.como_lista(corpo["ListaTiposComparecimento"]["TiposComparecimento"]["TipoComparecimento"])
    return {t["Sigla"]: t["Descricao"] for t in tipos} | DESCRICOES_SENADO_EXTRAS


def situacao_final(cli: Cliente, tema: dict) -> dict[str, str | None]:
    """Norma gerada e situação, pelo processo no Senado (que registra o desfecho das duas Casas)."""
    proposicao_senado = next(
        (v.get("proposicao") for v in tema.get("senado") or [] if v.get("proposicao")), None
    )
    sigla, numero, ano = separar_proposicao(proposicao_senado or tema["proposicao"])
    processos = senado.processos(cli, sigla=sigla, numero=numero, ano=ano)
    if not processos:
        return {"norma_gerada": None, "situacao": None}
    p = processos[0]
    return {"norma_gerada": p.get("normaGerada"), "situacao": p.get("situacaoAtual")}


# --------------------------------------------------------------------------------------------------------------
# Transformação em tabelas


def linhas_camara(v: VotacaoChave, bruto: dict, pessoa_por_camara: dict[str, str]) -> list[dict]:
    orientacoes = {o["siglaPartidoBloco"]: o.get("orientacaoVoto") for o in bruto["orientacoes"]}
    governo = orientacoes.get("Governo") or None
    linhas = []
    for voto in bruto["votos"]:
        dep = voto["deputado_"]
        linhas.append(
            {
                "tema_id": v.tema_id,
                "casa": "camara",
                "votacao_id": v.id,
                "principal": v.principal,
                "parlamentar_id": str(dep["id"]),
                "pessoa_id": pessoa_por_camara.get(str(dep["id"])),
                "nome": dep["nome"],
                "partido": dep.get("siglaPartido"),
                "uf": dep.get("siglaUf"),
                "voto": normalizar_voto_camara(voto.get("tipoVoto")),
                "voto_original": voto.get("tipoVoto"),
                "voto_descricao": voto.get("tipoVoto"),
                "orientacao_partido": orientacao_do_partido(dep.get("siglaPartido"), orientacoes),
                "orientacao_governo": governo,
            }
        )
    return linhas


def linhas_senado(
    v: VotacaoChave, bruto: dict, pessoa_por_senado: dict[str, str], legenda: dict[str, str]
) -> list[dict]:
    linhas = []
    for voto in bruto.get("votos") or []:
        sigla = voto.get("siglaVotoParlamentar")
        linhas.append(
            {
                "tema_id": v.tema_id,
                "casa": "senado",
                "votacao_id": v.id,
                "principal": v.principal,
                "parlamentar_id": str(voto["codigoParlamentar"]),
                "pessoa_id": pessoa_por_senado.get(str(voto["codigoParlamentar"])),
                "nome": voto["nomeParlamentar"],
                "partido": voto.get("siglaPartidoParlamentar"),
                "uf": voto.get("siglaUFParlamentar"),
                "voto": normalizar_voto_senado(sigla, legenda),
                "voto_original": sigla,
                "voto_descricao": voto.get("descricaoVotoParlamentar") or legenda.get(sigla, sigla),
                "orientacao_partido": None,
                "orientacao_governo": None,
            }
        )
    return linhas


def placar(linhas: list[dict]) -> dict[str, int]:
    contagem = {"sim": 0, "nao": 0, "abstencao": 0, "obstrucao": 0}
    for linha in linhas:
        if linha["voto"] in contagem:
            contagem[linha["voto"]] += 1
    return contagem


# --------------------------------------------------------------------------------------------------------------
# Orquestração


def montar(
    cli: Cliente, temas: list[dict], pessoas: pl.DataFrame
) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
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
    legenda = legenda_senado(cli)

    votos: list[dict] = []
    metadados: list[dict] = []
    for v in votacoes_da_curadoria(temas):
        log.info("Votação %s %s (%s)", v.casa, v.id, v.tema_id)
        if v.casa == "camara":
            linhas = linhas_camara(v, coletar_camara(cli, v.id), pessoa_por_camara)
        else:
            linhas = linhas_senado(v, coletar_senado(cli, v), pessoa_por_senado, legenda)
        votos.extend(linhas)
        metadados.append(asdict(v) | placar(linhas) | {"total_registros": len(linhas)})

    linhas_temas = []
    for t in temas:
        linhas_temas.append(
            {
                "tema_id": t["id"],
                "titulo": t["titulo"],
                "proposicao": t["proposicao"],
                "resumo": t["resumo"],
                "significado_sim": t["significado_sim"],
                "tema_do_momento": bool(t.get("tema_do_momento")),
                "sem_votacao_nominal_camara": (t.get("sem_votacao_nominal") or {}).get("camara"),
                "sem_votacao_nominal_senado": (t.get("sem_votacao_nominal") or {}).get("senado"),
            }
            | situacao_final(cli, t)
        )
    return pl.DataFrame(linhas_temas), pl.DataFrame(metadados), pl.DataFrame(votos)


def salvar(temas: pl.DataFrame, votacoes: pl.DataFrame, votos: pl.DataFrame, pasta: Path) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    for nome, df in (("temas", temas), ("votacoes", votacoes), ("votos", votos)):
        df.write_parquet(pasta / f"{nome}.parquet")
        df.write_csv(pasta / f"{nome}.csv")
