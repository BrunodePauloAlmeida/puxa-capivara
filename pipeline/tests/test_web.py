import json
from datetime import date

from PIL import Image
from test_profile import _data

from puxa import web


def test_short_role():
    assert (
        web.short_role(["Deputada federal em exercício · PSOL-SP · reeleita em 2026"]) == "Deputada federal"
    )
    assert web.short_role(["Eleito senador em 2026 · PT-PE"]) == "Eleito senador em 2026"
    assert web.short_role([]) == ""


def test_search_text_without_accents_or_repetition():
    assert web.search_text("Érika Hilton", "ERIKA SANTOS SILVA") == "erika hilton santos silva"
    assert web.search_text("Lula", None) == "lula"


def test_export(tmp_path):
    photos, pdfs, dest = tmp_path / "photos", tmp_path / "pdf", tmp_path / "web"
    photos.mkdir()
    pdfs.mkdir()
    Image.new("RGB", (480, 640), "gray").save(photos / "fulana.jpg")
    (pdfs / "fulana.pdf").write_bytes(b"%PDF-1.4 test")

    meta = web.export(_data(), photos, pdfs, dest, today=date(2026, 11, 1))

    assert meta["people"] == 2 and meta["with_photo"] == 1 and meta["missing_pdf"] == ["gov"]
    assert meta["in_office"] == {"president": 0, "governor": 1, "senator": 0, "federal_deputy": 1}
    assert meta["elected_2026"]["federal_deputy"] == 1
    index = {r["id"]: r for r in json.loads((dest / "index.json").read_text())}
    assert index["fulana"]["role"] == "Deputada federal" and index["fulana"]["party_state"] == "AAA-SP"
    assert index["fulana"]["search"] == "fulana silva de tal"
    # Without a 2026 candidacy, the civil name does not go into the search (same rule as the profile).
    assert index["gov"]["search"] == "beltrano" and not index["gov"]["photo"]

    person = json.loads((dest / "people" / "fulana.json").read_text())
    assert "photo" not in person and person["has_photo"] and person["has_pdf"]
    assert person["votes"] and person["bills"]["first_author"] == 5
    with Image.open(dest / "photos" / "fulana.jpg") as img:
        assert img.size == (240, 320)
    assert (dest / "pdf" / "fulana.pdf").read_bytes().startswith(b"%PDF")
