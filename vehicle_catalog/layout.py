import argparse
import math
import re
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree

from vehicle_catalog.pipeline import encode, load_artifacts, write_once

INVALID_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")


def coordinates(element):
    values = {
        key: float(element.attrib[key])
        for key in ("xMin", "yMin", "xMax", "yMax")
    }
    if not all(math.isfinite(value) for value in values.values()):
        raise ValueError("nonfinite PDF coordinate")
    return values


def parse_layout(payload: bytes):
    text = payload.decode("utf-8")
    root = ElementTree.fromstring(INVALID_XML.sub("\ufffd", text))
    pages = []
    for number, page in enumerate(root.findall(".//{*}page"), 1):
        width, height = float(page.attrib["width"]), float(
            page.attrib["height"]
        )
        if not all(
            math.isfinite(value) and value > 0 for value in (width, height)
        ):
            raise ValueError("invalid PDF page dimensions")
        blocks = []
        for block in page.findall(".//{*}block"):
            lines = []
            for line in block.findall(".//{*}line"):
                words = [
                    {
                        "text": "".join(word.itertext()),
                        "bbox": coordinates(word),
                    }
                    for word in line.findall(".//{*}word")
                ]
                lines.append({"bbox": coordinates(line), "words": words})
            blocks.append({"bbox": coordinates(block), "lines": lines})
        pages.append(
            {
                "physical_page": number,
                "width": width,
                "height": height,
                "blocks": blocks,
            }
        )
    if not pages:
        raise ValueError("no pages in PDF layout")
    return pages


def extract_layout(raw: Path, out: Path):
    if out.exists() or out.is_symlink():
        raise ValueError("output already exists")
    if out.resolve().is_relative_to(raw.parent.resolve()):
        raise ValueError("output must be outside raw storage")
    artifacts = load_artifacts(raw)
    for artifact in artifacts:
        if (
            artifact.source.adapter != "document"
            or not artifact.source.acquisition_approved
            or not re.fullmatch(r"[A-Za-z0-9_-]+", artifact.id)
        ):
            raise ValueError(
                "approved document artifacts with safe IDs required"
            )
    out.mkdir(parents=True)
    version = subprocess.run(
        ["pdftotext", "-v"],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    results = []
    for artifact in artifacts:
        result = {
            "artifact_id": artifact.id,
            "source_id": artifact.source.id,
            "status": "failed",
        }
        try:
            path = raw / f"{artifact.sha256}.blob"
            with path.open("rb") as handle:
                if handle.read(5) != b"%PDF-":
                    raise ValueError("not a PDF")
            process = subprocess.run(
                ["pdftotext", "-bbox-layout", "-enc", "UTF-8", str(path), "-"],
                check=True,
                capture_output=True,
                timeout=90,
            )
            if len(process.stdout) > 50 * 1024 * 1024:
                raise ValueError("layout exceeds 50 MiB")
            write_once(out / f"{artifact.id}.bbox.xhtml", process.stdout)
            pages = parse_layout(process.stdout)
            if len(pages) > 200:
                raise ValueError("layout exceeds 200 pages")
            layout = {
                "schema_version": "0.1.0",
                "artifact_id": artifact.id,
                "original_sha256": artifact.sha256,
                "source_url": artifact.source.url,
                "coordinate_space": "Poppler page coordinates in points",
                "extractor": (version.stderr or version.stdout).strip(),
                "review_status": "unreviewed_raw_layout",
                "invalid_xml_characters_replaced": len(
                    INVALID_XML.findall(process.stdout.decode("utf-8"))
                ),
                "limitations": [
                    "Blocks/lines/words are not semantic table rows or cells.",
                    "Headers, units, footnotes and applicability need review.",
                    "No OCR; scanned regions may have no text.",
                ],
                "warnings": process.stderr.decode("utf-8", errors="replace"),
                "pages": pages,
            }
            write_once(out / f"{artifact.id}.layout.json", encode(layout))
            result.update(status="extracted", page_count=len(pages))
        except (
            OSError,
            ValueError,
            KeyError,
            ElementTree.ParseError,
            subprocess.SubprocessError,
        ) as error:
            result["error"] = f"{type(error).__name__}: {error}"
        results.append(result)
        write_once(out / f"events/{len(results):04d}.json", encode(result))
        print(f"{artifact.source.id}: {result['status']}", flush=True)
    report = {
        "requested": len(artifacts),
        "results": results,
        "extracted": sum(item["status"] == "extracted" for item in results),
        "published_facts": 0,
    }
    write_once(out / "report.json", encode(report))
    return report


def main():
    parser = argparse.ArgumentParser(
        description="Extract raw PDF layout evidence offline"
    )
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = extract_layout(args.raw, args.out)
    return int(report["extracted"] != report["requested"])


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
