import argparse
import csv
import hashlib
import json
import re
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse

from vehicle_catalog.pipeline import encode, fetch, write_once
from vehicle_catalog.toyota import BrochureLinks, PAGES, source_for

MANIFEST = Path(__file__).resolve().parent.parent / "config/toyota-pdfs.csv"


def targets(refresh=True):
    with MANIFEST.open(newline="", encoding="utf-8") as handle:
        rows = {row["url"]: row for row in csv.DictReader(handle)}
    errors = []
    if refresh:
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory)
            for page in PAGES:
                url = f"https://www.toyota.com/brochures/{page}/"
                try:
                    artifact = fetch(source_for(url), raw)
                    parser = BrochureLinks()
                    parser.feed((raw / f"{artifact.sha256}.blob").read_text())
                    if not parser.links:
                        raise ValueError("no brochure links found")
                    for link in sorted(parser.links):
                        years = re.findall(r"/(20\d{2})/", urlparse(link).path)
                        if (
                            years
                            and not 2015
                            <= int(years[0])
                            <= datetime.now().year + 1
                        ):
                            continue
                        rows.setdefault(link, {"url": link, "sha256": ""})
                except (OSError, ValueError) as error:
                    errors.append({"url": url, "error": str(error)})
                    if isinstance(error, HTTPError) and error.code in (
                        401,
                        403,
                        429,
                    ):
                        raise ValueError(
                            f"listing access stopped: HTTP {error.code}"
                        ) from error
    return list(rows.values()), errors


def download_pdfs(rows, output):
    if not 1 <= len(rows) <= 600:
        raise ValueError("expected 1-600 PDF targets")
    sources = [source_for(row["url"]) for row in rows]
    if any(
        not urlparse(source.url).path.endswith(".pdf") for source in sources
    ):
        raise ValueError("PDF URLs required")
    if len({source.id for source in sources}) != len(sources):
        raise ValueError("duplicate PDF filenames")
    output.mkdir(parents=True, exist_ok=True)
    results = []
    stopped = None
    for row, source in zip(rows, sources):
        path = output / f"{source.id}.pdf"
        metadata = output / ".metadata" / f"{source.id}.json"
        result = {"url": source.url, "filename": path.name, "status": "failed"}
        try:
            if stopped:
                result["status"] = "not_attempted"
                raise ValueError(stopped)
            expected = row.get("sha256", "")
            if path.is_symlink() or metadata.is_symlink():
                raise ValueError("refusing symlink destination")
            if path.exists():
                if not expected and metadata.exists():
                    prior = json.loads(metadata.read_bytes())
                    if prior["source"]["url"] == source.url:
                        expected = prior["sha256"]
                if not expected:
                    raise ValueError("existing PDF has no verification hash")
                with path.open("rb") as handle:
                    if handle.read(5) != b"%PDF-":
                        raise ValueError("existing file is not a PDF")
                    handle.seek(0)
                    actual = hashlib.file_digest(handle, "sha256").hexdigest()
                if actual != expected:
                    raise ValueError(
                        "existing PDF checksum mismatch; not overwritten"
                    )
                result.update(status="verified_existing", sha256=actual)
            else:
                with tempfile.TemporaryDirectory() as directory:
                    raw = Path(directory)
                    artifact = fetch(source, raw, max_bytes=100 * 1024 * 1024)
                    payload = (raw / f"{artifact.sha256}.blob").read_bytes()
                    if not payload.startswith(b"%PDF-"):
                        raise ValueError("response is not a PDF")
                    if expected and artifact.sha256 != expected:
                        raise ValueError(
                            "Toyota PDF changed; review manifest "
                            "before updating"
                        )
                    if metadata.exists():
                        prior = json.loads(metadata.read_bytes())
                        if (
                            prior["source"]["url"] != source.url
                            or prior["sha256"] != artifact.sha256
                        ):
                            raise ValueError("local provenance conflict")
                    else:
                        write_once(
                            metadata, encode(artifact.model_dump(mode="json"))
                        )
                    write_once(path, payload)
                    result.update(status="downloaded", sha256=artifact.sha256)
        except (OSError, ValueError, KeyError) as error:
            result["error"] = f"{type(error).__name__}: {error}"
            if isinstance(error, HTTPError) and error.code in (401, 403, 429):
                stopped = f"download stopped after HTTP {error.code}"
        results.append(result)
        print(f"{path.name}: {result['status']}", flush=True)
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Download original PDFs directly from Toyota"
    )
    parser.add_argument("--output", type=Path, default=Path("data/pdfs"))
    parser.add_argument(
        "--no-refresh",
        action="store_true",
        help="Use only the checked-in known-PDF URL list",
    )
    args = parser.parse_args()
    rows, errors = targets(refresh=not args.no_refresh)
    results = download_pdfs(rows, args.output)
    report = {
        "complete_history": False,
        "listing_errors": errors,
        "results": results,
    }
    report_path = args.output / ".metadata" / f"run-{uuid.uuid4().hex}.json"
    write_once(report_path, encode(report))
    succeeded = sum(
        row["status"] in ("downloaded", "verified_existing") for row in results
    )
    print(f"{succeeded}/{len(results)} PDFs available; report: {report_path}")
    return int(bool(errors) or succeeded != len(results))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
