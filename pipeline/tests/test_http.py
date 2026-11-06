import httpx

from puxa import http


def test_retries_on_429_and_records_deprecated_route():
    calls = {"n": 0}

    def respond(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
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

    cli = http.Client(interval=0, transport=httpx.MockTransport(respond))
    cli.get_json.retry.wait = lambda *_: 0  # no wait between attempts in the test
    assert cli.get_json("https://exemplo.leg.br/plenario/lista/votacao/20261014?x=1") == {"ok": True}
    assert calls["n"] == 2
    assert cli.deprecated["/plenario/lista/votacao/20261014"]["sunset"] == "Sun, 01 Feb 2026"


def test_download_skips_when_file_unchanged(tmp_path):
    downloads = {"n": 0}

    def respond(request: httpx.Request) -> httpx.Response:
        headers = {"Last-Modified": "Sat, 31 Oct 2026", "Content-Length": "3"}
        if request.method == "HEAD":
            return httpx.Response(200, headers=headers)
        downloads["n"] += 1
        return httpx.Response(200, content=b"abc", headers=headers)

    cli = http.Client(interval=0, transport=httpx.MockTransport(respond))
    dest = tmp_path / "a.zip"
    cli.download("https://cdn.exemplo/a.zip", dest)
    cli.download("https://cdn.exemplo/a.zip", dest)
    assert dest.read_bytes() == b"abc" and downloads["n"] == 1
