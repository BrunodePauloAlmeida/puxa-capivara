import httpx

from puxa.collectors import chamber
from puxa.http import Client

CSV = (
    '﻿"uri";"nome";"idLegislaturaInicial";"idLegislaturaFinal";"nomeCivil";"cpf";"siglaSexo";"urlRedeSocial";'
    '"urlWebsite";"dataNascimento";"dataFalecimento";"ufNascimento";"municipioNascimento"\n'
    '"https://dadosabertos.camara.leg.br/api/v2/deputados/204379";"Acácio Favacho";"56";"57";'
    '"ACÁCIO DA SILVA FAVACHO NETO";"";"M";"";"";"1983-09-28";"";"AP";"Macapá"\n'
)


def test_bulk_details_reads_civil_name_and_birth_date(tmp_path):
    def respond(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=CSV.encode("utf-8"), headers={"Last-Modified": "x"})

    cli = Client(interval=0, transport=httpx.MockTransport(respond))
    details = chamber.bulk_details(cli, folder=tmp_path)
    assert details == {
        204379: {
            "nomeCivil": "ACÁCIO DA SILVA FAVACHO NETO",
            "cpf": None,
            "dataNascimento": "1983-09-28",
            "sexo": "M",
        }
    }
