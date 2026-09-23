# Vehicle Reference Catalog

Auditable reference data for a deterministic vehicle-shopping agent: approved sources become preserved originals, raw extraction, reviewed mappings, and versioned local JSON. The Python reader loads and indexes a release once, with no document parsing or network calls at query time.

**Status:** working acquisition/extraction and v0.1 catalog tooling, not a populated production catalog. Active collection is US Toyota, MY2015 onward, including already-published 2027 brochures and general/accessory references. Historical completeness is unverified. No VIN decoding or individual inventory records; the existing Search service owns inventory and JD Power integration.

## Documentation

- [PRD.md](PRD.md): product requirements, end-state curated schema and acceptance gates.
- [ARD.md](ARD.md): architecture, current contracts, schema migration and operator runbook.
- [TASKS.md](TASKS.md): delivery checklist and remaining work.
- [DATA_STATUS.md](DATA_STATUS.md): measured collection results and gaps.
- [SOURCE_RIGHTS_REVIEW.md](SOURCE_RIGHTS_REVIEW.md): source-use decisions and holds.

## Download Original PDFs

[Download the 130 original Toyota PDFs (ZIP)](https://github.com/bbrennan/vehicles/releases/download/raw-pdfs-2026-09-22/toyota-us-original-pdfs-20260922.zip), or open the [PDF release](https://github.com/bbrennan/vehicles/releases/tag/raw-pdfs-2026-09-22).

The ZIP contains ordinary, readable-named `.pdf` files with their original bytes, not symlinks. It contains no extracted JSON, text, layout, or acquisition manifests. The uncompressed PDFs total about 1.16 GB. Release assets are separate from Git history and are not included by `git clone` or GitHub's source-code ZIP.

This is the acquired US Toyota corpus, not complete MY2015-onward coverage: 2015-2019 and other documented gaps remain unresolved. See [DATA_STATUS.md](DATA_STATUS.md). The PDF-only download can be opened directly, but the managed offline extraction CLI also requires local acquisition manifests; this ZIP is not a complete pipeline backup.

## Setup

Requires Python 3.11+ and Poppler (`pdfinfo`, `pdftotext`) on `PATH`. Validated on macOS; other platforms and symlink behavior are unverified.

```sh
git clone https://github.com/bbrennan/vehicles.git
cd vehicles
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
brew install poppler
.venv/bin/python -m unittest discover -s tests -v
```

Use the platform package manager instead of Homebrew on other systems. Tests are synthetic and do not download the corpus. Black/pycodestyle are optional developer tools.

## Collect Toyota PDFs

Use fresh run IDs. Discovery snapshots official listing pages and adds explicitly unverified historical URL-pattern candidates. Future-year PDFs are included only when linked by official listings.

```sh
.venv/bin/python -m vehicle_catalog.toyota discover --run us-inventory-001 --minimum-year 2015 --through-year 2027
.venv/bin/python -m vehicle_catalog.toyota download --inventory data/staged/us-inventory-001/inventory.json --run us-brochures-001 --max-documents 600
```

Inspect the inventory before download and the report/events afterward. Collection is sequential, first-party-only, capped at 600 targets and 100 MiB per PDF; generic fetch retains its 20 MiB default. Redirects are rejected for review. Failures preserve successful artifacts and yield nonzero exit status. No automatic retry or exhaustive historical discovery is claimed. A 404 is a failed URL, not proof a brochure/model did not exist.

Small reviewed vehicle/reference plans are also supported:

```sh
.venv/bin/python -m vehicle_catalog.documents --plan config/toyota-documents.json --run toyota-vehicles-001
.venv/bin/python -m vehicle_catalog.documents --plan config/toyota-reference-documents.json --run toyota-reference-001
```

## Extract Raw Evidence

Downloads produce physical-page text and JSON. For coordinate-preserving raw layout from a completed PDF run:

```sh
.venv/bin/python -m vehicle_catalog.layout --raw data/raw/us-brochures-001 --out data/staged/us-layout-001
```

Outputs preserve page dimensions, word/line/block bounding boxes, source hash, tool version, exact Poppler bbox output and per-artifact outcomes. Invalid XML control characters are counted/replaced in parsed text while original output is retained. These are **raw layout observations, not semantic tables or curated facts**. Headers, legends, units, footnotes and trim applicability require review. Image-only regions require separate OCR/manual work.

Re-extract page text from a managed small-plan run using its matching current plan:

```sh
.venv/bin/python -m vehicle_catalog.documents --plan config/toyota-documents.json --run toyota-vehicles-001 --extract-existing --out data/staged/toyota-text-002
```

Offline commands require original blobs/manifests, verify hashes, and refuse existing output directories. Arbitrary unregistered PDF import is not implemented. Listing HTML artifacts must stay separate from PDF runs.

## Storage and Curation

```text
config/                 Source/scope plans and empty mapping template
schemas/                Generated v0.1 JSON Schemas
vehicle_catalog/        Acquisition, extraction, build and reader
tests/                  Synthetic contract and pipeline tests
data/raw/<run>/         Original bytes, manifests, readable PDF symlinks
data/staged/<run>/      Unreviewed text/layout/candidates, events, report
data/curated/           Explicit reviewed mappings
data/releases/          Validated versioned catalogs
```

All `data/` remains gitignored. Only the explicitly selected original PDFs are shared through the release asset above; extracted data and local manifests are not uploaded. Back up the managed corpus separately. Keep raw runs together because readable PDF links point to hash-named originals. Never edit through those links.

Verify identity from document content, not filenames or dealer headings. Use [config/mapping.json](config/mapping.json) and [schemas/mapping.schema.json](schemas/mapping.schema.json) for reviewed mappings. Current facts cover features, measurements, ratings, colors and specifications. Missing means unknown; unavailable requires evidence. Preserve market, package conditions, units, methodology and footnotes.

Normalized packages, ownership programs, knowledge, coverage and model-year changes described in PRD/ARD are proposed extensions, not implemented v0.1 capabilities. After factual review and publication approval:

```sh
.venv/bin/python -m vehicle_catalog build --raw data/raw/us-brochures-001 --mapping data/curated/pilot-001/mapping.json --out data/releases/pilot-001/catalog.json
.venv/bin/python -m vehicle_catalog validate data/releases/pilot-001/catalog.json
```

The checked-in mapping is intentionally empty and cannot build a catalog. All source publication flags remain false. The builder validates evidence references and contracts, but does not authenticate reviewers or prove factual entailment.

## Runtime Use

```python
from pathlib import Path
from vehicle_catalog.reader import LocalCatalog

catalog = LocalCatalog(Path("data/releases/pilot-001/catalog.json"))
trims = catalog.trims(market="US", year=2025, make="Toyota", model="Camry")
matches = catalog.with_feature(
    "head_up_display", market="US", year=2025, mode="available"
)
```

Other methods: `get`, `colors`, `compare` (2-6 configurations within one market). Results reflect only reviewed coverage and retain conditions. Examples do not imply those records exist. No production latency benchmark is claimed.

## Boundaries

Toyota/Lexus ToS are assumed satisfied per project-owner instruction; active collection is Toyota-only. The owner explicitly authorized sharing these original PDFs on GitHub; that does not grant downstream users a new license to their contents. EPA, Honda, IIHS and third-party archive ingestion remain held. NHTSA tooling exists separately.

Production gates: historical coverage audit, representative complete model-year factual review, current-rights enforcement independent of old manifests, authenticated approvals, backup/restore, release rollback and runtime benchmarks. CA/MX and other makes require separate coverage work. Download counts never establish complete history.