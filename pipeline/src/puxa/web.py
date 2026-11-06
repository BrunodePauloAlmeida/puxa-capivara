"""Exports the site data (v1) from the registry, votes, bills, photos and the PDFs already generated.

Output in data/site/web/ (this is what goes to Cloud Storage):
  meta.json            version, generation date and counts per role
  index.json           one row per person, for search (name, role, party-state, search text)
  people/{id}.json     the same content as the PDF profile, without the embedded photo
  photos/{id}.jpg      reduced photo (up to 320 px tall)
  pdf/{id}.pdf         the profile PDF (generated earlier with `uv run puxa profile --all`)
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import date
from pathlib import Path

from PIL import Image

from puxa import profile
from puxa.text import normalize_name

log = logging.getLogger(__name__)

PHOTO_HEIGHT = 320
ROLE_ORDER = ["president", "governor", "senator", "federal_deputy"]


def short_role(role_lines: list[str]) -> str:
    """'Deputada federal em exercício · PSOL-SP · reeleita em 2026' -> 'Deputada federal'."""
    if not role_lines:
        return ""
    return role_lines[0].split(" · ")[0].removesuffix(" em exercício")


def search_text(*parts: str | None) -> str:
    """Ballot name and civil name normalized (no accents, lowercase), without repeating words."""
    seen: list[str] = []
    for part in parts:
        for word in normalize_name(part or "").lower().split():
            if word not in seen:
                seen.append(word)
    return " ".join(seen)


def index_row(ctx: dict, roles: list[str], state: str | None, has_photo: bool) -> dict:
    return {
        "id": ctx["id"],
        "name": ctx["name"],
        "role": short_role(ctx["roles"]),
        "party_state": ctx["party_state"],
        "state": state,
        "roles": roles,
        "photo": has_photo,
        "initials": ctx["initials"],
        # Search only by the civil name the profile shows (the TSE's), for the same reason as the profile: social name.
        "search": search_text(ctx["name"], ctx["civil_name"]),
    }


def shrink_photo(source: Path, dest: Path, height: int = PHOTO_HEIGHT) -> None:
    with Image.open(source) as img:
        img = img.convert("RGB")
        if img.height > height:
            img = img.resize((round(img.width * height / img.height), height), Image.Resampling.LANCZOS)
        img.save(dest, "JPEG", quality=82, optimize=True, progressive=True)


def export(
    data: profile.Dataset,
    photos_dir: Path,
    pdf_dir: Path,
    dest: Path,
    photo_manifest: dict | None = None,
    today: date | None = None,
) -> dict:
    today = today or date.today()
    for sub in ("people", "photos", "pdf"):
        (dest / sub).mkdir(parents=True, exist_ok=True)

    roles_by_person: dict[str, list[dict]] = {}
    for p in data.roles.iter_rows(named=True):
        roles_by_person.setdefault(p["person_id"], []).append(p)

    index, missing_pdf = [], []
    for person_id in data.people["id"].to_list():
        photo = photos_dir / f"{person_id}.jpg"
        has_photo = photo.exists()
        if has_photo:
            shrink_photo(photo, dest / "photos" / f"{person_id}.jpg")

        pdf = pdf_dir / f"{person_id}.pdf"
        if pdf.exists():
            shutil.copyfile(pdf, dest / "pdf" / f"{person_id}.pdf")
        else:
            missing_pdf.append(person_id)

        ctx = profile.context(person_id, data, today=today, photos_dir=None, photo_manifest=photo_manifest)
        ctx.pop("photo")
        ctx["has_photo"] = has_photo
        ctx["has_pdf"] = pdf.exists()
        (dest / "people" / f"{person_id}.json").write_text(
            json.dumps(ctx, ensure_ascii=False), encoding="utf-8"
        )

        roles = roles_by_person.get(person_id, [])
        role_codes = sorted({p["role"] for p in roles}, key=ROLE_ORDER.index)
        main = next((p for p in roles if p["status"] == "in_office"), roles[0] if roles else {})
        index.append(index_row(ctx, role_codes, main.get("state"), has_photo))

    index.sort(key=lambda r: r["search"])

    def count(status: str) -> dict[str, int]:
        people_by_role = {c: set() for c in ROLE_ORDER}
        for p in data.roles.filter(data.roles["status"] == status).iter_rows(named=True):
            people_by_role[p["role"]].add(p["person_id"])
        return {c: len(ids) for c, ids in people_by_role.items()}

    meta = {
        "version": profile.VERSION,
        "generated_at": today.isoformat(),
        "people": len(index),
        "in_office": count("in_office"),
        "elected_2026": count("elected_2026"),
        "with_photo": sum(r["photo"] for r in index),
        "missing_pdf": missing_pdf,
    }
    (dest / "index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    (dest / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    if missing_pdf:
        log.warning(
            "%d people without a PDF (run `uv run puxa profile --all`): %s",
            len(missing_pdf),
            missing_pdf[:10],
        )
    return meta
