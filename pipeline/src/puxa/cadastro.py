"""Cadastro mestre: um registro por político, ligando os IDs de cada fonte.

Escopo (decisão D1): quem está no cargo hoje e quem foi eleito em 2026 para presidente, governador, senador
e deputado federal.

Como as pessoas são ligadas entre fontes, da regra mais forte para a mais fraca:
  1. mesmo CPF (Câmara e TSE 2026 publicam);
  2. mesmo nome civil e mesma data de nascimento;
  3. mesma data de nascimento, nomes parecidos (Jaccard >= 0,6) e mesma UF;
  4. mesmo nome civil e mesma UF, quando falta a data de nascimento (TSE 2018/2022 não publica mais);
  5. mesma data de nascimento, mesmo nome de urna e mesma UF (pega nome social e nome civil abreviado).
Dois registros com CPFs diferentes nunca são unidos; a tentativa vira pendência para revisão.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

import polars as pl
import yaml

from puxa.coletores import tse
from puxa.texto import normalizar_nome, semelhanca, slugify

log = logging.getLogger(__name__)

CARGOS_TSE = {
    "PRESIDENTE": "presidente",
    "GOVERNADOR": "governador",
    "SENADOR": "senador",
    "DEPUTADO FEDERAL": "deputado_federal",
}
LIMIAR_SEMELHANCA = 0.6


@dataclass
class Papel:
    cargo: str  # presidente | governador | senador | deputado_federal
    situacao: str  # em_exercicio | eleito_2026
    uf: str | None
    partido: str | None
    fonte: str
    inferido: bool = False
    observacao: str = ""


@dataclass
class Registro:
    fonte: str  # camara | senado | tse2026 | tse2022 | curadoria
    id_fonte: str
    nome_civil: str
    nome_urna: str | None = None
    cpf: str | None = None
    nascimento: str | None = None  # AAAA-MM-DD
    uf: str | None = None
    partido: str | None = None
    foto: str | None = None
    papeis: list[Papel] = field(default_factory=list)

    @property
    def chave(self) -> str:
        return f"{self.fonte}:{self.id_fonte}"


@dataclass
class Pessoa:
    id: str
    nome_urna: str
    nome_civil: str
    nascimento: str | None
    cpf: str | None  # uso interno para cruzamentos; nunca vai para o site
    camara_id: str | None
    senado_codigo: str | None
    tse_sq_2026: str | None
    tse_sq_2022: str | None
    foto: str | None
    chaves: list[str]
    papeis: list[Papel]


@dataclass
class Pendencia:
    tipo: str
    descricao: str
    chaves: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------------------------------------------
# Registros de cada fonte


def registros_camara(deputados: list[dict], detalhes: dict[int, dict]) -> list[Registro]:
    registros = []
    for d in deputados:
        det = detalhes.get(d["id"], {})
        status = det.get("ultimoStatus", {})
        registros.append(
            Registro(
                fonte="camara",
                id_fonte=str(d["id"]),
                nome_civil=det.get("nomeCivil") or d["nome"],
                nome_urna=status.get("nomeEleitoral") or d["nome"],
                cpf=tse.cpf_valido(det.get("cpf")),
                nascimento=det.get("dataNascimento"),
                uf=d["siglaUf"],
                partido=d["siglaPartido"],
                foto=d.get("urlFoto"),
                papeis=[Papel("deputado_federal", "em_exercicio", d["siglaUf"], d["siglaPartido"], "camara")],
            )
        )
    return registros


def registros_senado(senadores: list[dict], detalhes: dict[str, dict]) -> list[Registro]:
    registros = []
    for s in senadores:
        basicos = detalhes.get(s["codigo"], {}).get("DadosBasicosParlamentar", {})
        observacao = (
            "" if (s.get("participacao") or "Titular") == "Titular" else f"{s['participacao']} em exercício"
        )
        registros.append(
            Registro(
                fonte="senado",
                id_fonte=str(s["codigo"]),
                nome_civil=s["nome_completo"],
                nome_urna=s["nome"],
                nascimento=basicos.get("DataNascimento"),
                uf=s["uf"],
                partido=s["partido"],
                foto=s.get("foto"),
                papeis=[
                    Papel("senador", "em_exercicio", s["uf"], s["partido"], "senado", observacao=observacao)
                ],
            )
        )
    return registros


def _registro_tse(linha: dict, fonte: str, papeis: list[Papel] | None = None) -> Registro:
    uf = linha["SG_UF"] if linha["SG_UF"] not in ("BR", "") else None
    return Registro(
        fonte=fonte,
        id_fonte=linha["SQ_CANDIDATO"],
        nome_civil=linha["NM_CANDIDATO"],
        nome_urna=linha["NM_URNA_CANDIDATO"],
        cpf=tse.cpf_valido(linha.get("NR_CPF_CANDIDATO")),
        nascimento=tse.data_iso(linha.get("DT_NASCIMENTO")),
        uf=uf,
        partido=linha.get("SG_PARTIDO"),
        papeis=papeis or [],
    )


def registros_tse_2026(df26: pl.DataFrame) -> list[Registro]:
    """Eleitos em 2026 (com papel) + todos os demais candidatos, inclusive a deputado estadual, só para achar
    CPF e data de nascimento de quem tem cargo hoje (vários deputados federais disputaram vaga estadual)."""
    df = tse.ultima_situacao(df26)
    registros = []
    for linha in df.iter_rows(named=True):
        papeis = []
        cargo = CARGOS_TSE.get(linha["DS_CARGO"])
        if cargo and linha["DS_SIT_TOT_TURNO"] in tse.SITUACOES_ELEITO:
            uf = linha["SG_UF"] if linha["SG_UF"] != "BR" else None
            papeis.append(Papel(cargo, "eleito_2026", uf, linha["SG_PARTIDO"], "tse2026"))
        registros.append(_registro_tse(linha, "tse2026", papeis))
    return registros


def executivo_em_exercicio(
    df22: pl.DataFrame, df26: pl.DataFrame, ajustes: list[dict]
) -> tuple[list[Registro], list[Pendencia]]:
    """Presidente e governadores no cargo hoje.

    Não existe API com os governadores atuais. Parte dos eleitos em 2022 e infere trocas: quem disputou outro
    cargo em 2026 teve de renunciar até abril (desincompatibilização), e o vice assumiu. A inferência fica
    marcada para revisão; correções manuais vão em curadoria/governadores_em_exercicio.yaml.
    """
    e22 = tse.eleitos(df22, {"PRESIDENTE", "GOVERNADOR", "VICE-GOVERNADOR"})
    candidaturas26: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for linha in tse.ultima_situacao(df26).iter_rows(named=True):
        candidaturas26[normalizar_nome(linha["NM_CANDIDATO"])].append((linha["DS_CARGO"], linha["SG_UF"]))

    registros: list[Registro] = []
    pendencias: list[Pendencia] = []

    for linha in e22.filter(pl.col("DS_CARGO") == "PRESIDENTE").iter_rows(named=True):
        papel = Papel("presidente", "em_exercicio", None, linha["SG_PARTIDO"], "tse2022")
        registros.append(_registro_tse(linha, "tse2022", [papel]))

    ajustes_por_uf = {a["uf"]: a for a in ajustes}
    vices = {
        linha["SG_UF"]: linha
        for linha in e22.filter(pl.col("DS_CARGO") == "VICE-GOVERNADOR").iter_rows(named=True)
    }

    for titular in e22.filter(pl.col("DS_CARGO") == "GOVERNADOR").sort("SG_UF").iter_rows(named=True):
        uf = titular["SG_UF"]
        if uf in ajustes_por_uf:
            a = ajustes_por_uf[uf]
            papel = Papel(
                "governador", "em_exercicio", uf, a.get("partido"), "curadoria", observacao=a["motivo"]
            )
            registros.append(
                Registro("curadoria", f"governador-{uf}", a["nome_civil"], uf=uf, papeis=[papel])
            )
            continue

        outros = [
            (cargo, uf26)
            for cargo, uf26 in candidaturas26.get(normalizar_nome(titular["NM_CANDIDATO"]), [])
            if cargo != "GOVERNADOR" and uf26 in (uf, "BR")
        ]
        if not outros:
            papel = Papel("governador", "em_exercicio", uf, titular["SG_PARTIDO"], "tse2022")
            registros.append(_registro_tse(titular, "tse2022", [papel]))
            continue

        vice = vices.get(uf)
        cargo_disputado = outros[0][0].lower()
        if vice is None:
            pendencias.append(
                Pendencia(
                    "governador_sem_vice", f"{uf}: titular disputou {cargo_disputado} e não achei o vice"
                )
            )
            continue
        obs = (
            f"Titular eleito em 2022 ({titular['NM_URNA_CANDIDATO']}) disputou {cargo_disputado} em 2026; "
            "renúncia presumida, vice no cargo. Conferir."
        )
        papel = Papel(
            "governador", "em_exercicio", uf, vice["SG_PARTIDO"], "tse2022", inferido=True, observacao=obs
        )
        registros.append(_registro_tse(vice, "tse2022", [papel]))
        pendencias.append(
            Pendencia("governador_inferido", f"{uf}: {obs}", [f"tse2022:{vice['SQ_CANDIDATO']}"])
        )

        outros_vice = [
            cargo
            for cargo, uf26 in candidaturas26.get(normalizar_nome(vice["NM_CANDIDATO"]), [])
            if cargo not in ("GOVERNADOR", "VICE-GOVERNADOR") and uf26 in (uf, "BR")
        ]
        if outros_vice:
            pendencias.append(
                Pendencia(
                    "governador_vice_tambem_disputou",
                    f"{uf}: o vice também disputou {outros_vice[0].lower()} em 2026; conferir quem governa hoje",
                    [f"tse2022:{vice['SQ_CANDIDATO']}"],
                )
            )
    return registros, pendencias


def carregar_ajustes(arquivo: Path) -> list[dict]:
    if not arquivo.exists():
        return []
    return (yaml.safe_load(arquivo.read_text()) or {}).get("ajustes") or []


# --------------------------------------------------------------------------------------------------------------
# Resolução de identidade


class _Grupos:
    """Union-find que se recusa a unir grupos com CPFs diferentes."""

    def __init__(self, registros: list[Registro]):
        self.pai = list(range(len(registros)))
        self.cpfs: list[set[str]] = [{r.cpf} if r.cpf else set() for r in registros]

    def raiz(self, i: int) -> int:
        while self.pai[i] != i:
            self.pai[i] = self.pai[self.pai[i]]
            i = self.pai[i]
        return i

    def unir(self, a: int, b: int) -> bool:
        ra, rb = self.raiz(a), self.raiz(b)
        if ra == rb:
            return True
        if self.cpfs[ra] and self.cpfs[rb] and self.cpfs[ra] != self.cpfs[rb]:
            return False
        self.pai[rb] = ra
        self.cpfs[ra] |= self.cpfs[rb]
        return True


def _uf_compativel(a: Registro, b: Registro) -> bool:
    return a.uf is None or b.uf is None or a.uf == b.uf


def resolver(registros: list[Registro]) -> tuple[list[list[Registro]], list[Pendencia]]:
    grupos = _Grupos(registros)
    pendencias: list[Pendencia] = []
    conflitos_vistos: set[tuple[int, int]] = set()

    def tentar(i: int, j: int, regra: str) -> None:
        if not grupos.unir(i, j) and (i, j) not in conflitos_vistos:
            conflitos_vistos.add((i, j))
            a, b = registros[i], registros[j]
            pendencias.append(
                Pendencia(
                    "conflito_cpf",
                    f"{regra}: '{a.nome_civil}' e '{b.nome_civil}' têm CPFs diferentes",
                    [a.chave, b.chave],
                )
            )

    por_cpf: dict[str, list[int]] = defaultdict(list)
    por_nome: dict[str, list[int]] = defaultdict(list)
    por_nascimento: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(registros):
        if r.cpf:
            por_cpf[r.cpf].append(i)
        por_nome[normalizar_nome(r.nome_civil)].append(i)
        if r.nascimento:
            por_nascimento[r.nascimento].append(i)

    # 1. CPF
    for indices in por_cpf.values():
        for j in indices[1:]:
            tentar(indices[0], j, "cpf")
    # 2. nome + nascimento e 4. nome + UF quando falta nascimento
    for indices in por_nome.values():
        for x, i in enumerate(indices):
            for j in indices[x + 1 :]:
                a, b = registros[i], registros[j]
                if a.nascimento and b.nascimento:
                    if a.nascimento == b.nascimento:
                        tentar(i, j, "nome+nascimento")
                elif _uf_compativel(a, b) and not (a.cpf and b.cpf):
                    tentar(i, j, "nome+uf")
    # 3. nascimento + nome parecido + UF
    for indices in por_nascimento.values():
        for x, i in enumerate(indices):
            for j in indices[x + 1 :]:
                a, b = registros[i], registros[j]
                if not _uf_compativel(a, b):
                    continue
                if semelhanca(a.nome_civil, b.nome_civil) >= LIMIAR_SEMELHANCA:
                    tentar(i, j, "nascimento+nome_parecido")
                # 5. nascimento + nome de urna
                elif a.nome_urna and normalizar_nome(a.nome_urna) == normalizar_nome(b.nome_urna):
                    tentar(i, j, "nascimento+nome_urna")

    agrupados: dict[int, list[Registro]] = defaultdict(list)
    for i, r in enumerate(registros):
        agrupados[grupos.raiz(i)].append(r)
    # Só interessa quem tem algum papel; os demais registros serviram apenas para o cruzamento.
    com_papel = [g for g in agrupados.values() if any(r.papeis for r in g)]
    return com_papel, pendencias


# --------------------------------------------------------------------------------------------------------------
# Montagem das pessoas e IDs estáveis

# Nome de exibição: o nome parlamentar ("Hugo Motta") é melhor que o nome de urna do TSE, que às vezes é só
# o primeiro nome ("HUGO"). O TSE fica para quem não tem mandato no Congresso.
_PRIORIDADE_NOME_URNA = ["camara", "senado", "tse2026", "tse2022", "curadoria"]
_PRIORIDADE_NOME_CIVIL = ["tse2026", "camara", "senado", "tse2022", "curadoria"]


def _primeiro(grupo: list[Registro], atributo: str, prioridade: list[str]) -> str | None:
    for fonte in prioridade:
        for r in grupo:
            if r.fonte == fonte and getattr(r, atributo):
                return getattr(r, atributo)
    return None


def _id_da_fonte(grupo: list[Registro], fonte: str) -> str | None:
    return next((r.id_fonte for r in grupo if r.fonte == fonte), None)


def atribuir_ids(grupos: list[list[Registro]], anteriores: dict[str, str]) -> list[str]:
    """Um slug por pessoa ('tabata-amaral'). Quem já tinha slug numa execução anterior mantém o mesmo."""
    usados: set[str] = set()
    ids: list[str | None] = [None] * len(grupos)

    for n, grupo in enumerate(grupos):
        for r in grupo:
            slug = anteriores.get(r.chave)
            if slug and slug not in usados:
                ids[n] = slug
                usados.add(slug)
                break

    pendentes = [n for n in range(len(grupos)) if ids[n] is None]
    pendentes.sort(
        key=lambda n: (
            normalizar_nome(_primeiro(grupos[n], "nome_urna", _PRIORIDADE_NOME_URNA)),
            sorted(r.chave for r in grupos[n]),
        )
    )
    for n in pendentes:
        grupo = grupos[n]
        base = slugify(_primeiro(grupo, "nome_urna", _PRIORIDADE_NOME_URNA) or grupo[0].nome_civil)
        uf = next((p.uf for r in grupo for p in r.papeis if p.uf), None)
        candidatos = [base] + ([f"{base}-{uf.lower()}"] if uf else [])
        slug = next((c for c in candidatos if c not in usados), None)
        sufixo = 2
        while slug is None:
            tentativa = f"{candidatos[-1]}-{sufixo}"
            slug = tentativa if tentativa not in usados else None
            sufixo += 1
        ids[n] = slug
        usados.add(slug)
    return ids  # type: ignore[return-value]


def montar_pessoas(grupos: list[list[Registro]], anteriores: dict[str, str]) -> list[Pessoa]:
    ids = atribuir_ids(grupos, anteriores)
    pessoas = []
    for pid, grupo in zip(ids, grupos, strict=True):
        # Registros com papel primeiro: se a pessoa tem duas candidaturas em 2026 (trocou de cargo no registro),
        # vale a que tem resultado, não a abandonada.
        grupo = sorted(grupo, key=lambda r: not r.papeis)
        papeis: list[Papel] = []
        for r in grupo:
            for p in r.papeis:
                if all((p.cargo, p.situacao) != (q.cargo, q.situacao) for q in papeis):
                    papeis.append(p)
        pessoas.append(
            Pessoa(
                id=pid,
                nome_urna=_primeiro(grupo, "nome_urna", _PRIORIDADE_NOME_URNA) or grupo[0].nome_civil,
                nome_civil=_primeiro(grupo, "nome_civil", _PRIORIDADE_NOME_CIVIL) or "",
                nascimento=next((r.nascimento for r in grupo if r.nascimento), None),
                cpf=next((r.cpf for r in grupo if r.cpf), None),
                camara_id=_id_da_fonte(grupo, "camara"),
                senado_codigo=_id_da_fonte(grupo, "senado"),
                tse_sq_2026=_id_da_fonte(grupo, "tse2026"),
                tse_sq_2022=_id_da_fonte(grupo, "tse2022"),
                foto=_primeiro(grupo, "foto", ["camara", "senado"]),
                chaves=sorted(r.chave for r in grupo),
                papeis=papeis,
            )
        )
    return sorted(pessoas, key=lambda p: p.id)


def pendencias_de_cobertura(pessoas: list[Pessoa]) -> list[Pendencia]:
    """Avisos úteis para a revisão: quem ficou sem CPF ou sem ligação com o TSE de 2026."""
    avisos = []
    for p in pessoas:
        cargos = {(x.cargo, x.situacao) for x in p.papeis}
        if ("deputado_federal", "em_exercicio") in cargos and not p.cpf:
            avisos.append(Pendencia("deputado_sem_cpf", f"{p.id}: deputado em exercício sem CPF", p.chaves))
        if p.tse_sq_2022 and not p.tse_sq_2026 and not p.camara_id and not p.senado_codigo:
            avisos.append(
                Pendencia(
                    "executivo_sem_cpf",
                    f"{p.id}: sem CPF (não disputou 2026 ou não foi ligado ao TSE 2026)",
                    p.chaves,
                )
            )
    return avisos


# --------------------------------------------------------------------------------------------------------------
# Saída


def salvar(pessoas: list[Pessoa], pendencias: list[Pendencia], pasta: Path) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    linhas_pessoas = [
        {k: v for k, v in asdict(p).items() if k not in ("papeis", "chaves")} | {"chaves": ",".join(p.chaves)}
        for p in pessoas
    ]
    linhas_papeis = [{"pessoa_id": p.id} | asdict(papel) for p in pessoas for papel in p.papeis]
    linhas_pendencias = [asdict(x) | {"chaves": ",".join(x.chaves)} for x in pendencias]

    df_pessoas = pl.DataFrame(linhas_pessoas)
    df_papeis = pl.DataFrame(linhas_papeis)
    df_pend = pl.DataFrame(
        linhas_pendencias, schema={"tipo": pl.String, "descricao": pl.String, "chaves": pl.String}
    )
    for nome, df in (("pessoas", df_pessoas), ("papeis", df_papeis), ("pendencias", df_pend)):
        df.write_parquet(pasta / f"{nome}.parquet")
        df.write_csv(pasta / f"{nome}.csv")

    slugs = {chave: p.id for p in pessoas for chave in p.chaves}
    (pasta / "slugs.json").write_text(json.dumps(slugs, ensure_ascii=False, indent=0, sort_keys=True))


def carregar_slugs(pasta: Path) -> dict[str, str]:
    arquivo = pasta / "slugs.json"
    return json.loads(arquivo.read_text()) if arquivo.exists() else {}


def resumo(pessoas: list[Pessoa], pendencias: list[Pendencia]) -> str:
    contagem: dict[tuple[str, str], int] = defaultdict(int)
    for p in pessoas:
        for papel in p.papeis:
            contagem[(papel.cargo, papel.situacao)] += 1
    linhas = [f"Pessoas no cadastro: {len(pessoas)}"]
    for (cargo, situacao), n in sorted(contagem.items()):
        linhas.append(f"  {cargo:<17} {situacao:<13} {n}")
    tipos: dict[str, int] = defaultdict(int)
    for x in pendencias:
        tipos[x.tipo] += 1
    linhas.append(f"Pendências para revisão: {len(pendencias)}")
    for tipo, n in sorted(tipos.items()):
        linhas.append(f"  {tipo:<32} {n}")
    return "\n".join(linhas)
