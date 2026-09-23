import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Literal

from pydantic import Field

from vehicle_catalog.batch import Pilot
from vehicle_catalog.models import Artifact, Model, Name, Source
from vehicle_catalog.pipeline import (
    digest,
    encode,
    fetch,
    load_artifacts,
    write_once,
)


class DocumentTarget(Model):
    source: Source
    make: Name
    model: Name
    year: int = Field(ge=1900, le=2200, strict=True)


class ReferenceDocumentTarget(Model):
    kind: Literal["reference"]
    source: Source
    make: Name
    title: Name
    topic: Literal["safety", "accessories", "ownership"]
    version: Name | None = None


class DocumentPlan(Model):
    documents: list[DocumentTarget | ReferenceDocumentTarget] = Field(
        min_length=1, max_length=10
    )


def link_pdf(artifact: Artifact, raw: Path) -> Path:
    payload = (raw / f"{artifact.sha256}.blob").read_bytes()
    if (
        digest(payload) != artifact.sha256
        or len(payload) != artifact.byte_count
        or not payload.startswith(b"%PDF-")
    ):
        raise ValueError("PDF artifact integrity or signature failure")
    name = re.sub(r"[^a-z0-9_-]+", "-", artifact.source.id.lower()).strip("-_")
    if not name or len(name) > 180:
        raise ValueError("source ID cannot form a readable PDF filename")
    folder = raw / "pdfs"
    if folder.is_symlink():
        raise ValueError("PDF directory must not be a symbolic link")
    folder.mkdir(exist_ok=True)
    path = folder / f"{name}.pdf"
    target = Path("..") / f"{artifact.sha256}.blob"
    try:
        path.symlink_to(target)
    except FileExistsError:
        if not path.is_symlink() or path.readlink() != target:
            raise ValueError(f"refusing to overwrite {path}")
    return path


def split_pages(text: str, expected_pages: int):
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    if len(pages) != expected_pages:
        raise ValueError("text page boundaries do not match PDF page count")
    if not any(page.strip() for page in pages):
        raise ValueError("no usable text; OCR/manual extraction required")
    return [
        {
            "physical_page": index,
            "text": page,
            "blank_text": not bool(page.strip()),
        }
        for index, page in enumerate(pages, 1)
    ]


def extract_pdf(artifact, raw: Path, staged: Path):
    path = raw / f"{artifact.sha256}.blob"
    payload = path.read_bytes()
    if digest(payload) != artifact.sha256 or not payload.startswith(b"%PDF-"):
        raise ValueError("PDF artifact integrity or signature failure")
    info = subprocess.run(
        ["pdfinfo", str(path)],
        check=True,
        capture_output=True,
        timeout=30,
        text=True,
    ).stdout
    match = re.search(r"^Pages:\s+(\d+)\s*$", info, re.MULTILINE)
    if not match or not 1 <= int(match[1]) <= 200:
        raise ValueError("PDF page count unavailable or exceeds 200-page cap")
    converted = subprocess.run(
        ["pdftotext", "-layout", "-enc", "UTF-8", str(path), "-"],
        check=True,
        capture_output=True,
        timeout=60,
    )
    if len(converted.stdout) > 50 * 1024 * 1024:
        raise ValueError("extracted text exceeds 50 MiB limit")
    text = converted.stdout.decode("utf-8")
    pages = split_pages(text, int(match[1]))
    version = subprocess.run(
        ["pdftotext", "-v"],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    result = {
        "artifact_id": artifact.id,
        "original_sha256": artifact.sha256,
        "text_sha256": digest(converted.stdout),
        "extractor": (version.stderr or version.stdout).splitlines()[0],
        "arguments": ["-layout", "-enc", "UTF-8"],
        "page_count": len(pages),
        "review_status": "unreviewed_extraction",
        "warnings": converted.stderr.decode("utf-8", errors="replace"),
        "pages": pages,
    }
    write_once(staged / f"{artifact.id}.txt", converted.stdout)
    write_once(staged / f"{artifact.id}.pages.json", encode(result))
    return result


def validate_plan(plan: DocumentPlan, pilot: Pilot):
    ids = [target.source.id for target in plan.documents]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate document source ID")
    for target in plan.documents:
        if isinstance(target, DocumentTarget):
            eligible = pilot.eligible(
                target.make, target.year, target.source.market
            )
        else:
            eligible = (
                target.make.casefold()
                in {make.casefold() for make in pilot.makes}
                and target.source.market in pilot.markets
            )
        if not eligible:
            raise ValueError("planned document is outside pilot scope")
        if target.source.adapter != "document":
            raise ValueError("document plan requires document sources")
        if not target.source.acquisition_approved:
            raise ValueError("document acquisition not approved")


def reextract_documents(
    plan: DocumentPlan, pilot: Pilot, raw: Path, out: Path
):
    validate_plan(plan, pilot)
    if out.exists() or out.is_symlink():
        raise ValueError("output already exists; choose a new directory")
    if out.resolve().is_relative_to(raw.parent.resolve()):
        raise ValueError("extraction output must be outside raw storage")
    artifacts = load_artifacts(raw)
    registry = {target.source.id: target for target in plan.documents}
    for artifact in artifacts:
        target = registry.get(artifact.source.id)
        if target is None or (
            artifact.source.url,
            artifact.source.market,
            artifact.source.adapter,
        ) != (
            target.source.url,
            target.source.market,
            target.source.adapter,
        ):
            raise ValueError("artifact does not match current document plan")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", artifact.id):
            raise ValueError("unsafe artifact ID")
    out.mkdir(parents=True)
    write_once(out / "plan.json", encode(plan.model_dump(mode="json")))
    write_once(out / "pilot.json", encode(pilot.model_dump(mode="json")))
    results = []
    for artifact in artifacts:
        target = registry[artifact.source.id]
        result = {
            "artifact_id": artifact.id,
            "source_id": artifact.source.id,
            "declared_scope": target.model_dump(exclude={"source"}),
            "identity_review": "pending",
            "applicability_review": "pending",
            "extraction": "failed",
        }
        try:
            extracted = extract_pdf(artifact, raw, out)
            result.update(
                extraction="extracted", page_count=extracted["page_count"]
            )
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            result["error"] = f"{type(error).__name__}: {error}"
        results.append(result)
        write_once(out / f"events/{len(results):03d}.json", encode(result))
    report = {
        "mode": "offline_reextraction",
        "raw_directory": str(raw),
        "requested": len(artifacts),
        "extracted": sum(
            result["extraction"] == "extracted" for result in results
        ),
        "published_facts": 0,
        "results": results,
    }
    write_once(out / "report.json", encode(report))
    return report


def run_documents(plan: DocumentPlan, pilot: Pilot, root: Path, run_id: str):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", run_id):
        raise ValueError("invalid run ID")
    validate_plan(plan, pilot)
    raw, staged = root / "raw" / run_id, root / "staged" / run_id
    if raw.exists() or staged.exists():
        raise ValueError("run already exists")
    raw.mkdir(parents=True)
    staged.mkdir(parents=True)
    write_once(staged / "plan.json", encode(plan.model_dump(mode="json")))
    results = []
    for target in plan.documents:
        result = {
            "source_id": target.source.id,
            "declared_scope": target.model_dump(exclude={"source"}),
            "identity_review": "pending",
            "applicability_review": "pending",
            "acquisition": "failed",
            "extraction": "not_attempted",
        }
        try:
            artifact = fetch(target.source, raw)
            result.update(
                acquisition="acquired",
                artifact_id=artifact.id,
                extraction="failed",
            )
            result["pdf_path"] = str(link_pdf(artifact, raw).relative_to(raw))
            extracted = extract_pdf(artifact, raw, staged)
            result.update(
                extraction="extracted", page_count=extracted["page_count"]
            )
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            result["error"] = f"{type(error).__name__}: {error}"
        results.append(result)
        write_once(staged / f"events/{len(results):03d}.json", encode(result))
        print(
            f"{target.source.id}: {result['acquisition']}, "
            f"{result['extraction']}",
            flush=True,
        )
    report = {
        "run_id": run_id,
        "requested": len(results),
        "acquired": sum(item["acquisition"] == "acquired" for item in results),
        "extracted": sum(
            item["extraction"] == "extracted" for item in results
        ),
        "published_facts": 0,
        "results": results,
    }
    write_once(staged / "report.json", encode(report))
    return report


def main():
    parser = argparse.ArgumentParser(
        description="Download approved PDFs or extract retained PDFs offline"
    )
    parser.add_argument(
        "--plan", type=Path, default=Path("config/toyota-documents.json")
    )
    parser.add_argument(
        "--pilot", type=Path, default=Path("config/pilot.json")
    )
    parser.add_argument("--root", type=Path, default=Path("data"))
    parser.add_argument("--run", required=True)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--link-existing",
        action="store_true",
        help="Create readable PDF links for an existing run; no downloads",
    )
    modes.add_argument(
        "--extract-existing",
        action="store_true",
        help="Re-extract a retained raw run without network access",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="New output directory required for --extract-existing",
    )
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", args.run):
        parser.error("invalid run ID")
    if args.extract_existing != (args.out is not None):
        parser.error("--out is required only with --extract-existing")
    if args.link_existing:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", args.run):
            raise ValueError("invalid run ID")
        raw = args.root / "raw" / args.run
        artifacts = load_artifacts(raw)
        for artifact in artifacts:
            if artifact.source.adapter == "document":
                print(link_pdf(artifact, raw))
        return 0
    plan = DocumentPlan.model_validate_json(args.plan.read_bytes())
    pilot = Pilot.model_validate_json(args.pilot.read_bytes())
    if args.extract_existing:
        report = reextract_documents(
            plan, pilot, args.root / "raw" / args.run, args.out
        )
        print(f"Extracted {report['extracted']}; downloaded 0; published 0")
        return 0 if report["extracted"] == report["requested"] else 1
    report = run_documents(plan, pilot, args.root, args.run)
    print(
        f"Acquired {report['acquired']}; extracted {report['extracted']}; "
        "published 0"
    )
    return 0 if report["extracted"] == report["requested"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
