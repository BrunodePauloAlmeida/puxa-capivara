import httpx

from puxa.coletores import camara
from puxa.http import Cliente

CSV = (
    '﻿"uri";"nome";"idLegislaturaInicial";"idLegislaturaFinal";"nomeCivil";"cpf";"siglaSexo";"urlRedeSocial";'
    '"urlWebsite";"dataNascimento";"dataFalecimento";"ufNascimento";"municipioNascimento"\n'
    '"https://dadosabertos.camara.leg.br/api/v2/deputados/204379";"Acácio Favacho";"56";"57";'
    '"ACÁCIO DA SILVA FAVACHO NETO";"";"M";"";"";"1983-09-28";"";"AP";"Macapá"\n'
)


def test_fichas_em_lote_le_nome_civil_e_nascimento(tmp_path):
    def responder(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=CSV.encode("utf-8"), headers={"Last-Modified": "x"})

    cli = Cliente(intervalo=0, transport=httpx.MockTransport(responder))
    fichas = camara.fichas_em_lote(cli, pasta=tmp_path)
    assert fichas == {
        204379: {"nomeCivil": "ACÁCIO DA SILVA FAVACHO NETO", "cpf": None, "dataNascimento": "1983-09-28"}
    }
