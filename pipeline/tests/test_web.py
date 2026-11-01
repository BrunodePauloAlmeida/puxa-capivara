import json
from datetime import date

from PIL import Image
from test_ficha import _dados

from puxa import web


def test_cargo_curto():
    assert (
        web.cargo_curto(["Deputada federal em exercício · PSOL-SP · reeleita em 2026"]) == "Deputada federal"
    )
    assert web.cargo_curto(["Eleito senador em 2026 · PT-PE"]) == "Eleito senador em 2026"
    assert web.cargo_curto([]) == ""


def test_texto_de_busca_sem_acento_e_sem_repeticao():
    assert web.texto_de_busca("Érika Hilton", "ERIKA SANTOS SILVA") == "erika hilton santos silva"
    assert web.texto_de_busca("Lula", None) == "lula"


def test_exportar(tmp_path):
    fotos, pdfs, destino = tmp_path / "fotos", tmp_path / "pdf", tmp_path / "web"
    fotos.mkdir()
    pdfs.mkdir()
    Image.new("RGB", (480, 640), "gray").save(fotos / "fulana.jpg")
    (pdfs / "fulana.pdf").write_bytes(b"%PDF-1.4 teste")

    meta = web.exportar(_dados(), fotos, pdfs, destino, hoje=date(2026, 11, 1))

    assert meta["pessoas"] == 2 and meta["com_foto"] == 1 and meta["sem_pdf"] == ["gov"]
    assert meta["em_exercicio"] == {"presidente": 0, "governador": 1, "senador": 0, "deputado_federal": 1}
    assert meta["eleitos_2026"]["deputado_federal"] == 1
    indice = {r["id"]: r for r in json.loads((destino / "indice.json").read_text())}
    assert indice["fulana"]["cargo"] == "Deputada federal" and indice["fulana"]["partido_uf"] == "AAA-SP"
    assert indice["fulana"]["busca"] == "fulana silva de tal"
    # Sem candidatura em 2026, o nome civil não entra na busca (mesma regra da ficha).
    assert indice["gov"]["busca"] == "beltrano" and not indice["gov"]["foto"]

    pessoa = json.loads((destino / "pessoas" / "fulana.json").read_text())
    assert "foto" not in pessoa and pessoa["tem_foto"] and pessoa["tem_pdf"]
    assert pessoa["votacoes"] and pessoa["producao"]["primeiro_autor"] == 5
    with Image.open(destino / "fotos" / "fulana.jpg") as img:
        assert img.size == (240, 320)
    assert (destino / "pdf" / "fulana.pdf").read_bytes().startswith(b"%PDF")
