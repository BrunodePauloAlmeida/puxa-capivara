"""Ficha de uma página (v1): junta cadastro, votações-chave e produção legislativa de uma pessoa, preenche o
template HTML e imprime em PDF A4 com o Chromium (Playwright).

Escolhas editoriais da v1:
- Cores dos votos neutras (azul para Sim, terracota para Não), sem verde/vermelho, para não sugerir certo/errado.
- "Sem registro" na Câmara = ausente ou sem mandato na data; a ficha não afirma o motivo.
- Blocos ainda não coletados (patrimônio, processos, declarações) não aparecem; o rodapé avisa que virão.
"""

from __future__ import annotations

import base64
import glob
import logging
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import polars as pl
from jinja2 import Environment, PackageLoader, select_autoescape

from puxa.config import DADOS, PROCESSADO
from puxa.texto import nome_exibicao

log = logging.getLogger(__name__)

VERSAO = "v1"
MAX_DESTAQUES = 3
MAX_EMENTA = 150

ROTULOS_CARGO = {
    "deputado_federal": ("Deputado federal", "Deputada federal", "Deputado(a) federal"),
    "senador": ("Senador", "Senadora", "Senador(a)"),
    "governador": ("Governador", "Governadora", "Governador(a)"),
    "presidente": ("Presidente da República", "Presidente da República", "Presidente da República"),
}
CASAS = {"camara": "Câmara", "senado": "Senado"}

# rótulo e classe CSS de cada categoria de voto
VOTOS = {
    "sim": ("Sim", "sim"),
    "nao": ("Não", "nao"),
    "abstencao": ("Abstenção", "meio"),
    "obstrucao": ("Obstrução", "meio"),
    "presidente": ("Presidia a sessão", "neutro"),
    "presente_sem_voto": ("Presente, sem voto", "neutro"),
    "ausente": ("Ausente", "neutro"),
    "voto_secreto": ("Voto secreto", "neutro"),
    "outro": ("Outro", "neutro"),
}


@dataclass
class Dados:
    pessoas: pl.DataFrame
    papeis: pl.DataFrame
    temas: pl.DataFrame
    votacoes: pl.DataFrame
    votos: pl.DataFrame
    producao: pl.DataFrame
    destaques: pl.DataFrame

    @classmethod
    def carregar(cls, pasta: Path = PROCESSADO) -> Dados:
        def ler(caminho: str) -> pl.DataFrame:
            arquivo = pasta / caminho
            if not arquivo.exists():
                raise SystemExit(f"Falta {arquivo}. Rode antes: uv run puxa cadastro / votacoes / producao")
            return pl.read_parquet(arquivo)

        return cls(
            pessoas=ler("cadastro/pessoas.parquet"),
            papeis=ler("cadastro/papeis.parquet"),
            temas=ler("votacoes/temas.parquet"),
            votacoes=ler("votacoes/votacoes.parquet"),
            votos=ler("votacoes/votos.parquet"),
            producao=ler("producao/producao.parquet"),
            destaques=ler("producao/destaques.parquet"),
        )


# --------------------------------------------------------------------------------------------------------------
# Textos


def rotulo_cargo(cargo: str, genero: str | None) -> str:
    masc, fem, neutro = ROTULOS_CARGO[cargo]
    return {"M": masc, "F": fem}.get(genero or "", neutro)


def flexao(genero: str | None, masc: str, fem: str) -> str:
    return {"M": masc, "F": fem}.get(genero or "", f"{masc}(a)")


def _partido_uf(partido: str | None, uf: str | None) -> str:
    return "-".join(x for x in (partido, uf) if x)


def linhas_de_cargo(papeis: list[dict], genero: str | None) -> list[str]:
    """Ex.: ['Deputada federal em exercício · PSOL-SP · reeleita em 2026', 'Eleito senador em 2026 · PT-PE']."""
    em_exercicio = [p for p in papeis if p["situacao"] == "em_exercicio"]
    eleitos = [p for p in papeis if p["situacao"] == "eleito_2026"]
    linhas = []
    for p in em_exercicio:
        partes = [f"{rotulo_cargo(p['cargo'], genero)} em exercício", _partido_uf(p["partido"], p["uf"])]
        if any(e["cargo"] == p["cargo"] for e in eleitos):
            partes.append(f"{flexao(genero, 'reeleito', 'reeleita')} em 2026")
        if p.get("inferido"):
            partes.append("dado em verificação")
        linhas.append(" · ".join(x for x in partes if x))
    for e in eleitos:
        if any(p["cargo"] == e["cargo"] for p in em_exercicio):
            continue
        cargo = rotulo_cargo(e["cargo"], genero)
        cargo = cargo if e["cargo"] == "presidente" else cargo[0].lower() + cargo[1:]
        linhas.append(
            " · ".join(
                x
                for x in (
                    f"{flexao(genero, 'Eleito', 'Eleita')} {cargo} em 2026",
                    _partido_uf(e["partido"], e["uf"]),
                )
                if x
            )
        )
    return linhas


def encurtar(texto: str | None, limite: int = MAX_EMENTA) -> str:
    texto = " ".join((texto or "").split())
    if len(texto) <= limite:
        return texto
    return texto[: limite - 1].rsplit(" ", 1)[0].rstrip(",;:.") + "…"


def data_br(iso: str | None) -> str:
    if not iso or len(iso) < 10:
        return ""
    ano, mes, dia = iso[:10].split("-")
    return f"{dia}/{mes}/{ano}"


def iniciais(nome: str) -> str:
    partes = [p for p in nome.split() if p[:1].isalpha()]
    return "".join(p[0] for p in (partes[:1] + partes[-1:] if len(partes) > 1 else partes)).upper()


def foto_data_uri(pessoa_id: str, pasta: Path | None = None) -> str | None:
    arquivo = (pasta or DADOS / "fotos") / f"{pessoa_id}.jpg"
    if not arquivo.exists():
        return None
    return "data:image/jpeg;base64," + base64.b64encode(arquivo.read_bytes()).decode()


# --------------------------------------------------------------------------------------------------------------
# Contexto da ficha


def _linha_voto(tema: dict, voto: dict | None, casa: str, votacao: dict | None) -> dict:
    if voto:
        rotulo, classe = VOTOS.get(voto["voto"], VOTOS["outro"])
        detalhe = voto["voto_descricao"] if voto["voto"] == "ausente" and voto.get("voto_descricao") else ""
    else:
        explicacao = tema.get(f"sem_votacao_nominal_{casa}")
        rotulo, classe = ("Sem votação nominal", "vazio") if explicacao else ("Sem registro", "vazio")
        detalhe = encurtar(explicacao, 120) if explicacao else ""
    return {
        "titulo": tema["titulo"],
        "significado_sim": tema["significado_sim"],
        "casa": CASAS[casa],
        "data": data_br(votacao["data"]) if votacao else "",
        "voto": rotulo,
        "classe": classe,
        "detalhe": detalhe,
        "desfecho": tema.get("norma_gerada") or (tema.get("situacao") or "").capitalize(),
    }


def votos_da_pessoa(pessoa: dict, dados: Dados) -> tuple[list[dict], list[dict]]:
    """(temas do momento, demais votações-chave) com o voto da pessoa em cada uma."""
    casas = [c for c, chave in (("camara", "camara_id"), ("senado", "senado_codigo")) if pessoa.get(chave)]
    meus = dados.votos.filter((pl.col("pessoa_id") == pessoa["id"]) & pl.col("principal"))
    for casa in meus["casa"].unique().to_list():
        if casa not in casas:
            casas.append(casa)
    if not casas:
        return [], []

    principais = {
        (v["tema_id"], v["casa"]): v for v in dados.votacoes.filter(pl.col("principal")).iter_rows(named=True)
    }
    do_momento, chave = [], []
    for tema in dados.temas.iter_rows(named=True):
        for casa in casas:
            voto = next(
                iter(
                    meus.filter((pl.col("tema_id") == tema["tema_id"]) & (pl.col("casa") == casa)).iter_rows(
                        named=True
                    )
                ),
                None,
            )
            linha = _linha_voto(tema, voto, casa, principais.get((tema["tema_id"], casa)))
            (do_momento if tema["tema_do_momento"] else chave).append(linha)
    return do_momento, chave


def producao_da_pessoa(pessoa: dict, dados: Dados) -> dict | None:
    linhas = dados.producao.filter(pl.col("pessoa_id") == pessoa["id"])
    if linhas.is_empty():
        return None
    r = linhas.row(0, named=True)
    destaques = [
        {"identificacao": d["identificacao"], "norma": d["norma"], "ementa": encurtar(d["ementa"])}
        for d in dados.destaques.filter(pl.col("pessoa_id") == pessoa["id"])
        .head(MAX_DESTAQUES)
        .iter_rows(named=True)
    ]
    return {
        "casa": CASAS[r["casa"]],
        "desde": r["desde"][:4],
        "primeiro_autor": r["como_primeiro_autor"],
        "total": r["apresentados"],
        "viraram_norma": r["viraram_norma_como_primeiro_autor"],
        "destaques": destaques,
    }


def contexto(
    pessoa_id: str,
    dados: Dados,
    hoje: date | None = None,
    pasta_fotos: Path | None = None,
    manifesto_fotos: dict | None = None,
) -> dict:
    pessoa = dados.pessoas.filter(pl.col("id") == pessoa_id).row(0, named=True)
    papeis = dados.papeis.filter(pl.col("pessoa_id") == pessoa_id).to_dicts()
    do_momento, chave = votos_da_pessoa(pessoa, dados)
    principal = next((p for p in papeis if p["situacao"] == "em_exercicio"), papeis[0] if papeis else {})
    return {
        "id": pessoa_id,
        "nome": nome_exibicao(pessoa["nome_urna"]),
        # Só o nome civil do TSE, que respeita o nome social; o da Câmara pode trazer o nome de registro.
        "nome_civil": nome_exibicao(pessoa["nome_civil"]) if pessoa.get("tse_sq_2026") else "",
        "iniciais": iniciais(pessoa["nome_urna"]),
        "foto": foto_data_uri(pessoa_id, pasta_fotos),
        "fonte_foto": (manifesto_fotos or {}).get(pessoa_id, {}).get("fonte"),
        "cargos": linhas_de_cargo(papeis, pessoa.get("genero")),
        "partido_uf": _partido_uf(principal.get("partido"), principal.get("uf")),
        "temas_do_momento": do_momento,
        "votacoes": chave,
        "tem_congresso": bool(do_momento or chave),
        "producao": producao_da_pessoa(pessoa, dados),
        "gerado_em": data_br((hoje or date.today()).isoformat()),
        "versao": VERSAO,
    }


# --------------------------------------------------------------------------------------------------------------
# HTML e PDF


def _ambiente() -> Environment:
    return Environment(
        loader=PackageLoader("puxa", "templates"), autoescape=select_autoescape(["html", "j2"])
    )


def html(ctx: dict) -> str:
    return _ambiente().get_template("ficha.html.j2").render(**ctx)


def caminho_chromium() -> str | None:
    """Chromium a usar: PUXA_CHROMIUM, ou o pré-instalado do ambiente de desenvolvimento, ou o padrão do
    Playwright (na imagem de produção, instalado com `playwright install chromium`)."""
    if os.environ.get("PUXA_CHROMIUM"):
        return os.environ["PUXA_CHROMIUM"]
    candidatos = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux64/chrome"))
    return candidatos[-1] if candidatos else None


_CABE_NA_PAGINA = (
    "() => { const p = document.querySelector('.pagina'); return p.scrollHeight <= p.clientHeight + 1; }"
)


def gerar_pdfs(fichas: list[tuple[str, str]], pasta: Path) -> list[str]:
    """Imprime cada (id, html) em pasta/{id}.pdf. Se o conteúdo não couber, tenta a versão compacta.
    Devolve os IDs que nem assim couberam em uma página."""
    from playwright.sync_api import sync_playwright

    pasta.mkdir(parents=True, exist_ok=True)
    nao_couberam = []
    with sync_playwright() as p:
        executavel = caminho_chromium()
        navegador = (
            p.chromium.launch(executable_path=executavel, args=["--no-sandbox"])
            if executavel
            else p.chromium.launch()
        )
        pagina = navegador.new_page()
        for pessoa_id, conteudo in fichas:
            pagina.set_content(conteudo, wait_until="load")
            if not pagina.evaluate(_CABE_NA_PAGINA):
                pagina.evaluate("() => document.body.classList.add('compacta')")
                if not pagina.evaluate(_CABE_NA_PAGINA):
                    nao_couberam.append(pessoa_id)
                    log.warning("Ficha de %s não coube em uma página", pessoa_id)
            pagina.pdf(path=str(pasta / f"{pessoa_id}.pdf"), prefer_css_page_size=True, print_background=True)
        navegador.close()
    return nao_couberam
