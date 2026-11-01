"""Linha de comando do pipeline: `uv run puxa cadastro`."""

import argparse
import json
import logging
import sys

import polars as pl

from puxa import cadastro, ficha, fotos, producao, votacoes
from puxa.coletores import camara, senado, tse
from puxa.config import CURADORIA, DADOS, PROCESSADO
from puxa.http import Cliente

log = logging.getLogger("puxa")


def cmd_cadastro(_: argparse.Namespace) -> int:
    pasta = PROCESSADO / "cadastro"
    with Cliente(intervalo=0.1) as cli:
        log.info("Câmara: deputados em exercício")
        deputados = camara.deputados_em_exercicio(cli)
        lote = camara.fichas_em_lote(cli)
        # Ficha do arquivo anual; se a ficha completa (com CPF) já foi baixada antes, ela tem prioridade.
        detalhes_dep = {d["id"]: camara.ficha_em_cache(d["id"]) or lote.get(d["id"], {}) for d in deputados}

        log.info("Senado: senadores em exercício")
        senadores = senado.senadores_em_exercicio(cli)
        detalhes_sen = {s["codigo"]: senado.detalhe_senador(cli, s["codigo"]) for s in senadores}

        log.info("TSE: candidaturas 2022 e 2026")
        df22 = tse.ler_candidatos(tse.baixar_candidatos(cli, 2022))
        df26 = tse.ler_candidatos(tse.baixar_candidatos(cli, 2026))

        depreciados = dict(cli.depreciados)

    ajustes = cadastro.carregar_ajustes(CURADORIA / "governadores_em_exercicio.yaml")
    executivo, pendencias = cadastro.executivo_em_exercicio(df22, df26, ajustes)
    registros = (
        cadastro.registros_camara(deputados, detalhes_dep)
        + cadastro.registros_senado(senadores, detalhes_sen)
        + executivo
        + cadastro.registros_tse_2026(df26)
    )
    grupos, conflitos = cadastro.resolver(registros)
    pessoas = cadastro.montar_pessoas(grupos, cadastro.carregar_slugs(pasta))
    pendencias += conflitos + cadastro.pendencias_de_cobertura(pessoas)
    cadastro.salvar(pessoas, pendencias, pasta)

    print(cadastro.resumo(pessoas, pendencias))
    for rota, info in depreciados.items():
        print(f"AVISO: rota depreciada {rota} (sunset {info['sunset']})")
    print(f"Arquivos em {pasta}")
    return 0


def _pessoas() -> pl.DataFrame:
    arquivo = PROCESSADO / "cadastro" / "pessoas.parquet"
    if not arquivo.exists():
        raise SystemExit("Rode antes: uv run puxa cadastro")
    return pl.read_parquet(arquivo)


def cmd_votacoes(_: argparse.Namespace) -> int:
    temas = votacoes.carregar_temas(CURADORIA / "votacoes_chave.yaml")
    with Cliente(intervalo=0.3) as cli:
        df_temas, df_votacoes, df_votos = votacoes.montar(cli, temas, _pessoas())
    pasta = PROCESSADO / "votacoes"
    votacoes.salvar(df_temas, df_votacoes, df_votos, pasta)
    print(
        df_votacoes.select(
            "tema_id", "casa", "id", "data", "principal", "sim", "nao", "abstencao", "total_registros"
        )
    )
    ligados = df_votos.filter(pl.col("pessoa_id").is_not_null())
    print(f"Votos: {df_votos.height} registros, {ligados.height} de pessoas do cadastro")
    print(f"Arquivos em {pasta}")
    return 0


def cmd_producao(_: argparse.Namespace) -> int:
    with Cliente(intervalo=0.3) as cli:
        resumo, destaques = producao.montar(cli, _pessoas())
    pasta = PROCESSADO / "producao"
    producao.salvar(resumo, destaques, pasta)
    for casa in ("camara", "senado"):
        r = resumo.filter(pl.col("casa") == casa)
        print(
            f"{casa}: {r.height} parlamentares, {r['apresentados'].sum()} projetos, "
            f"{r['viraram_norma_como_primeiro_autor'].sum()} viraram norma com eles como primeiro autor"
        )
    print(f"Destaques: {destaques.height}. Arquivos em {pasta}")
    return 0


def cmd_fotos(_: argparse.Namespace) -> int:
    pessoas = _pessoas()
    with Cliente(intervalo=0.1) as cli:
        manifesto = fotos.baixar_fotos(cli, pessoas)
    sem_foto = sorted(set(pessoas["id"]) - set(manifesto))
    print(f"Fotos: {len(manifesto)} de {pessoas.height} pessoas. Sem foto: {len(sem_foto)} {sem_foto[:10]}")
    return 0


def cmd_ficha(args: argparse.Namespace) -> int:
    dados = ficha.Dados.carregar()
    ids = dados.pessoas["id"].to_list() if args.todos else args.ids
    if not ids:
        raise SystemExit("Informe os IDs (ex.: uv run puxa ficha erika-hilton lula) ou use --todos")
    desconhecidos = sorted(set(ids) - set(dados.pessoas["id"]))
    if desconhecidos:
        raise SystemExit(f"IDs fora do cadastro: {desconhecidos}")
    manifesto_path = fotos.pasta_fotos() / "manifesto.json"
    manifesto = json.loads(manifesto_path.read_text()) if manifesto_path.exists() else {}

    pasta_html, pasta_pdf = DADOS / "site" / "html", DADOS / "site" / "pdf"
    pasta_html.mkdir(parents=True, exist_ok=True)
    paginas = []
    for pessoa_id in ids:
        conteudo = ficha.html(ficha.contexto(pessoa_id, dados, manifesto_fotos=manifesto))
        (pasta_html / f"{pessoa_id}.html").write_text(conteudo, encoding="utf-8")
        paginas.append((pessoa_id, conteudo))
    if args.sem_pdf:
        print(f"{len(paginas)} fichas em HTML em {pasta_html}")
        return 0
    nao_couberam = ficha.gerar_pdfs(paginas, pasta_pdf)
    print(
        f"{len(paginas)} PDFs em {pasta_pdf}"
        + (f"; não couberam em uma página: {nao_couberam}" if nao_couberam else "")
    )
    return 1 if nao_couberam else 0


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(prog="puxa")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("cadastro", help="Monta o cadastro mestre de políticos").set_defaults(func=cmd_cadastro)
    sub.add_parser("votacoes", help="Coleta os votos das votações-chave").set_defaults(func=cmd_votacoes)
    sub.add_parser("producao", help="Coleta a produção legislativa").set_defaults(func=cmd_producao)
    sub.add_parser("fotos", help="Baixa as fotos oficiais").set_defaults(func=cmd_fotos)
    p_ficha = sub.add_parser("ficha", help="Gera a ficha de uma página (HTML e PDF)")
    p_ficha.add_argument("ids", nargs="*", help="IDs do cadastro (ex.: erika-hilton)")
    p_ficha.add_argument("--todos", action="store_true", help="Gera para todas as pessoas do cadastro")
    p_ficha.add_argument("--sem-pdf", action="store_true", help="Só o HTML")
    p_ficha.set_defaults(func=cmd_ficha)
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
