import httpx

from puxa import http


def test_repete_em_429_e_registra_rota_depreciada():
    chamadas = {"n": 0}

    def responder(request: httpx.Request) -> httpx.Response:
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            return httpx.Response(429)
        return httpx.Response(
            200,
            json={"ok": True},
            headers={
                "Deprecation": "Tue, 18 Mar 2025",
                "Sunset": "Sun, 01 Feb 2026",
                "Link": "<https://x/votacao>",
            },
        )

    cli = http.Cliente(intervalo=0, transport=httpx.MockTransport(responder))
    cli.get_json.retry.wait = lambda *_: 0  # sem espera entre tentativas no teste
    assert cli.get_json("https://exemplo.leg.br/plenario/lista/votacao/20261014?x=1") == {"ok": True}
    assert chamadas["n"] == 2
    assert cli.depreciados["/plenario/lista/votacao/20261014"]["sunset"] == "Sun, 01 Feb 2026"


def test_baixar_pula_quando_arquivo_nao_mudou(tmp_path):
    downloads = {"n": 0}

    def responder(request: httpx.Request) -> httpx.Response:
        headers = {"Last-Modified": "Sat, 31 Oct 2026", "Content-Length": "3"}
        if request.method == "HEAD":
            return httpx.Response(200, headers=headers)
        downloads["n"] += 1
        return httpx.Response(200, content=b"abc", headers=headers)

    cli = http.Cliente(intervalo=0, transport=httpx.MockTransport(responder))
    destino = tmp_path / "a.zip"
    cli.baixar("https://cdn.exemplo/a.zip", destino)
    cli.baixar("https://cdn.exemplo/a.zip", destino)
    assert destino.read_bytes() == b"abc" and downloads["n"] == 1
