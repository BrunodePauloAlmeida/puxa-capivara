"""Linha de comando do pipeline: `uv run puxa cadastro`."""

import argparse
import logging
import sys

from puxa import cadastro
from puxa.coletores import camara, senado, tse
from puxa.config import CURADORIA, PROCESSADO
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


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(prog="puxa")
    sub = parser.add_subparsers(dest="comando", required=True)
    sub.add_parser("cadastro", help="Monta o cadastro mestre de políticos").set_defaults(func=cmd_cadastro)
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
