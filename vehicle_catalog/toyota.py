import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urljoin, urlparse

from vehicle_catalog.documents import extract_pdf, link_pdf
from vehicle_catalog.models import Source
from vehicle_catalog.pipeline import (
    encode,
    fetch,
    write_once,
)

BASE = "https://www.toyota.com/content/dam/toyota/brochures/pdf/"
PAGES = (
    "cars-minivan",
    "trucks",
    "crossovers-suvs",
    "electrified",
    "other-brochures",
)
STEMS = (
    "4runner",
    "86",
    "avalon",
    "avalonhybrid",
    "bz4x",
    "camry",
    "camryhybrid",
    "chr",
    "corolla",
    "corollahatchback",
    "corollaim",
    "corollacross",
    "fjcruiser",
    "gr86",
    "grcorolla",
    "grsupra",
    "grandhighlander",
    "highlander",
    "highlanderhybrid",
    "landcruiser",
    "mirai",
    "prius",
    "priusc",
    "priusv",
    "priusplugin",
    "priusprime",
    "rav4",
    "rav4hybrid",
    "rav4prime",
    "sequoia",
    "sienna",
    "tacoma",
    "toyotacrown",
    "toyotacrownsignia",
    "tundra",
    "venza",
    "yaris",
    "yarisia",
)
RIGHTS = (
    "User-authorized US Toyota first-party collection, 2026-09-22. "
    "Toyota ToS assumed satisfied by user; publication pending review."
)


def source_for(url: str) -> Source:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "www.toyota.com"
        or parsed.query
        or parsed.fragment
        or ".." in parsed.path.split("/")
        or not (
            parsed.path.startswith("/brochures/")
            or parsed.path.startswith("/content/dam/toyota/brochures/pdf/")
        )
    ):
        raise ValueError("only approved first-party Toyota brochure URLs")
    suffix = (
        parsed.path.removeprefix("/content/dam/toyota/brochures/pdf/")
        .removeprefix("/brochures/")
        .removesuffix(".pdf")
    )
    identifier = "toyota-us-" + re.sub(
        r"[^a-z0-9]+", "-", suffix.lower()
    ).strip("-")
    return Source(
        id=identifier,
        publisher="Toyota Motor Sales, U.S.A., Inc.",
        adapter="document",
        url=url,
        market="US",
        acquisition_approved=True,
        rights_reference=RIGHTS,
    )


class BrochureLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if not href:
            return
        url = urljoin("https://www.toyota.com/", href)
        if url.startswith(BASE) and urlparse(url).path.endswith(".pdf"):
            source_for(url)
            self.links.add(url)


def discover(root: Path, run_id: str, minimum_year: int, through_year: int):
    if not 2015 <= minimum_year <= through_year <= datetime.now().year + 1:
        raise ValueError("invalid Toyota year window")
    raw, staged = new_run(root, run_id)
    outcomes = []
    rows = {}
    for page in PAGES:
        url = f"https://www.toyota.com/brochures/{page}/"
        result = {"url": url, "status": "failed"}
        try:
            artifact = fetch(source_for(url), raw)
            parser = BrochureLinks()
            parser.feed((raw / f"{artifact.sha256}.blob").read_text())
            if not parser.links:
                raise ValueError("no brochure links; markup requires review")
            result.update(status="acquired", artifact_id=artifact.id)
            for link in sorted(parser.links):
                years = re.findall(r"/(20\d{2})/", urlparse(link).path)
                year = int(years[0]) if years else None
                if (
                    year is not None
                    and not minimum_year <= year <= through_year
                ):
                    continue
                rows[link] = {
                    "url": link,
                    "discovery": "official_page",
                    "listing_url": url,
                    "listing_artifact_id": artifact.id,
                    "url_year_hint": year,
                    "identity_review": "pending",
                }
        except (OSError, ValueError) as error:
            result["error"] = f"{type(error).__name__}: {error}"
        outcomes.append(result)
        write_once(staged / f"events/{len(outcomes):03d}.json", encode(result))
    for year in range(
        minimum_year, min(through_year, datetime.now().year) + 1
    ):
        for stem in STEMS:
            url = f"{BASE}{year}/{stem}_ebrochure.pdf"
            rows.setdefault(
                url,
                {
                    "url": url,
                    "discovery": "unverified_url_pattern",
                    "url_year_hint": year,
                    "model_token_hint": stem,
                    "identity_review": "pending",
                },
            )
    inventory = {
        "schema_version": "0.1.0",
        "market": "US",
        "make": "Toyota",
        "minimum_year": minimum_year,
        "through_year": through_year,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "complete": False,
        "limitations": [
            "Pattern candidates are not evidence of model offerings.",
            "Historical filenames/editions may be missing; review gaps.",
            "Undated general references are not assigned a model year.",
            "Only explicitly linked future-model-year PDFs are included.",
        ],
        "listing_results": outcomes,
        "documents": list(rows.values()),
    }
    write_once(staged / "inventory.json", encode(inventory))
    return inventory


def new_run(root: Path, run_id: str):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", run_id):
        raise ValueError("invalid run ID")
    raw, staged = root / "raw" / run_id, root / "staged" / run_id
    if raw.exists() or staged.exists():
        raise ValueError("run already exists")
    raw.mkdir(parents=True)
    staged.mkdir(parents=True)
    return raw, staged


def download(
    inventory_path: Path, root: Path, run_id: str, max_documents: int
):
    inventory = json.loads(inventory_path.read_bytes())
    if inventory.get("market") != "US" or inventory.get("make") != "Toyota":
        raise ValueError("US Toyota inventory required")
    rows = inventory["documents"]
    if not 1 <= len(rows) <= max_documents <= 600:
        raise ValueError("document request budget exceeded (maximum 600)")
    sources = [source_for(row["url"]) for row in rows]
    if any(
        not urlparse(source.url).path.endswith(".pdf") for source in sources
    ):
        raise ValueError("download inventory must contain PDF URLs")
    if len({source.url for source in sources}) != len(sources):
        raise ValueError("duplicate URL")
    if len({source.id for source in sources}) != len(sources):
        raise ValueError("duplicate normalized source ID")
    raw, staged = new_run(root, run_id)
    write_once(staged / "inventory.json", encode(inventory))
    results = []
    stopped_reason = None
    for index, (row, source) in enumerate(zip(rows, sources), 1):
        result = {
            **row,
            "source_id": source.id,
            "acquisition": "failed",
            "extraction": "not_attempted",
        }
        try:
            if stopped_reason:
                result["acquisition"] = "not_attempted"
                raise ValueError(stopped_reason)
            artifact = fetch(source, raw, max_bytes=100 * 1024 * 1024)
            result.update(acquisition="acquired", artifact_id=artifact.id)
            result["pdf_path"] = str(link_pdf(artifact, raw).relative_to(raw))
            result["extraction"] = "failed"
            extracted = extract_pdf(artifact, raw, staged)
            result.update(
                extraction="extracted", page_count=extracted["page_count"]
            )
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            result["error"] = f"{type(error).__name__}: {error}"
            if isinstance(error, HTTPError) and error.code in (401, 403, 429):
                stopped_reason = f"collection stopped after HTTP {error.code}"
        results.append(result)
        write_once(staged / f"events/{index:04d}.json", encode(result))
        print(
            f"{index}/{len(rows)} {source.id}: {result['acquisition']} / "
            f"{result['extraction']}",
            flush=True,
        )
    report = {
        "run_id": run_id,
        "complete": False,
        "requested": len(rows),
        "acquired": sum(row["acquisition"] == "acquired" for row in results),
        "extracted": sum(row["extraction"] == "extracted" for row in results),
        "published_facts": 0,
        "stopped_reason": stopped_reason,
        "results": results,
    }
    write_once(staged / "report.json", encode(report))
    return report


def main():
    parser = argparse.ArgumentParser(
        description="US Toyota brochure inventory and retrieval"
    )
    parser.add_argument("mode", choices=("discover", "download"))
    parser.add_argument("--root", type=Path, default=Path("data"))
    parser.add_argument("--run", required=True)
    parser.add_argument("--minimum-year", type=int, default=2015)
    parser.add_argument(
        "--through-year", type=int, default=datetime.now().year + 1
    )
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--max-documents", type=int, default=600)
    args = parser.parse_args()
    if args.mode == "discover":
        result = discover(
            args.root, args.run, args.minimum_year, args.through_year
        )
        print(
            f"Inventoried {len(result['documents'])} URLs; "
            "completeness unverified"
        )
        return int(
            any(row["status"] == "failed" for row in result["listing_results"])
        )
    if args.inventory is None:
        parser.error("download requires --inventory")
    result = download(args.inventory, args.root, args.run, args.max_documents)
    print(
        f"Acquired {result['acquired']}; extracted {result['extracted']}; "
        "published 0"
    )
    return int(result["extracted"] != result["requested"])


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
