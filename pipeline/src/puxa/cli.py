"""Pipeline command line: `uv run puxa registry`."""

import argparse
import json
import logging
import sys

import polars as pl

from puxa import bills, photos, profile, registry, votes, web
from puxa.collectors import chamber, senate, tse
from puxa.config import CURATION, DATA, PROCESSED
from puxa.http import Client

log = logging.getLogger("puxa")


def cmd_registry(_: argparse.Namespace) -> int:
    folder = PROCESSED / "registry"
    with Client(interval=0.1) as cli:
        log.info("Chamber: deputies in office")
        deputies = chamber.deputies_in_office(cli)
        bulk = chamber.bulk_details(cli)
        # Record from the yearly file; if the full record (with CPF) was downloaded before, it takes priority.
        deputy_details = {d["id"]: chamber.cached_details(d["id"]) or bulk.get(d["id"], {}) for d in deputies}

        log.info("Senate: senators in office")
        senators = senate.senators_in_office(cli)
        senator_details = {s["code"]: senate.senator_details(cli, s["code"]) for s in senators}

        log.info("TSE: 2022 and 2026 candidacies")
        df22 = tse.read_candidates(tse.download_candidates(cli, 2022))
        df26 = tse.read_candidates(tse.download_candidates(cli, 2026))

        deprecated = dict(cli.deprecated)

    overrides = registry.load_overrides(CURATION / "governors_in_office.yaml")
    executive, issues = registry.executive_in_office(df22, df26, overrides)
    records = (
        registry.chamber_records(deputies, deputy_details)
        + registry.senate_records(senators, senator_details)
        + executive
        + registry.tse_2026_records(df26)
    )
    groups, conflicts = registry.resolve(records)
    people = registry.build_people(groups, registry.load_slugs(folder))
    issues += conflicts + registry.coverage_issues(people)
    registry.save(people, issues, folder)

    print(registry.summary(people, issues))
    for route, info in deprecated.items():
        print(f"WARNING: deprecated route {route} (sunset {info['sunset']})")
    print(f"Files in {folder}")
    return 0


def _people() -> pl.DataFrame:
    file = PROCESSED / "registry" / "people.parquet"
    if not file.exists():
        raise SystemExit("Run first: uv run puxa registry")
    return pl.read_parquet(file)


def cmd_votes(_: argparse.Namespace) -> int:
    topics = votes.load_topics(CURATION / "key_votes.yaml")
    with Client(interval=0.3) as cli:
        df_topics, df_roll_calls, df_votes = votes.build(cli, topics, _people())
    folder = PROCESSED / "votes"
    votes.save(df_topics, df_roll_calls, df_votes, folder)
    print(
        df_roll_calls.select(
            "topic_id", "house", "id", "date", "main", "yes", "no", "abstention", "total_records"
        )
    )
    linked = df_votes.filter(pl.col("person_id").is_not_null())
    print(f"Votes: {df_votes.height} records, {linked.height} from people in the registry")
    print(f"Files in {folder}")
    return 0


def cmd_bills(_: argparse.Namespace) -> int:
    with Client(interval=0.3) as cli:
        summary, highlights = bills.build(cli, _people())
    folder = PROCESSED / "bills"
    bills.save(summary, highlights, folder)
    for house in ("chamber", "senate"):
        r = summary.filter(pl.col("house") == house)
        print(
            f"{house}: {r.height} legislators, {r['introduced'].sum()} bills, "
            f"{r['became_law_as_first_author'].sum()} became law with them as first author"
        )
    print(f"Highlights: {highlights.height}. Files in {folder}")
    return 0


def cmd_photos(_: argparse.Namespace) -> int:
    people = _people()
    with Client(interval=0.1) as cli:
        manifest = photos.download_photos(cli, people)
    no_photo = sorted(set(people["id"]) - set(manifest))
    print(
        f"Photos: {len(manifest)} of {people.height} people. Without photo: {len(no_photo)} {no_photo[:10]}"
    )
    return 0


def cmd_profile(args: argparse.Namespace) -> int:
    data = profile.Dataset.load()
    ids = data.people["id"].to_list() if args.all else args.ids
    if not ids:
        raise SystemExit("Give the IDs (e.g. uv run puxa profile erika-hilton lula) or use --all")
    unknown = sorted(set(ids) - set(data.people["id"]))
    if unknown:
        raise SystemExit(f"IDs not in the registry: {unknown}")
    manifest_path = photos.photos_dir() / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    html_dir, pdf_dir = DATA / "site" / "html", DATA / "site" / "pdf"
    html_dir.mkdir(parents=True, exist_ok=True)
    pages = []
    for person_id in ids:
        content = profile.html(profile.context(person_id, data, photo_manifest=manifest))
        (html_dir / f"{person_id}.html").write_text(content, encoding="utf-8")
        pages.append((person_id, content))
    if args.no_pdf:
        print(f"{len(pages)} HTML profiles in {html_dir}")
        return 0
    did_not_fit = profile.generate_pdfs(pages, pdf_dir)
    print(
        f"{len(pages)} PDFs in {pdf_dir}"
        + (f"; did not fit on one page: {did_not_fit}" if did_not_fit else "")
    )
    return 1 if did_not_fit else 0


def cmd_site(_: argparse.Namespace) -> int:
    data = profile.Dataset.load()
    manifest_path = photos.photos_dir() / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    dest = DATA / "site" / "web"
    meta = web.export(data, photos.photos_dir(), DATA / "site" / "pdf", dest, photo_manifest=manifest)
    print(
        f"{meta['people']} people ({meta['with_photo']} with photo) in {dest}"
        + (f"; missing PDF: {len(meta['missing_pdf'])}" if meta["missing_pdf"] else "")
    )
    return 0


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(prog="puxa")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("registry", help="Builds the master registry of politicians").set_defaults(
        func=cmd_registry
    )
    sub.add_parser("votes", help="Collects the votes on the key roll calls").set_defaults(func=cmd_votes)
    sub.add_parser("bills", help="Collects the legislative output").set_defaults(func=cmd_bills)
    sub.add_parser("photos", help="Downloads the official photos").set_defaults(func=cmd_photos)
    p_profile = sub.add_parser("profile", help="Generates the one-page profile (HTML and PDF)")
    p_profile.add_argument("ids", nargs="*", help="Registry IDs (e.g. erika-hilton)")
    p_profile.add_argument("--all", action="store_true", help="Generates for every person in the registry")
    p_profile.add_argument("--no-pdf", action="store_true", help="HTML only")
    p_profile.set_defaults(func=cmd_profile)
    sub.add_parser("site", help="Exports the site data (index, JSON profiles, photos, PDFs)").set_defaults(
        func=cmd_site
    )
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
