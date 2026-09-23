# Acquisition Status

Date: 2026-09-22. Active collection: US Toyota, MY2015 onward, including already-published 2027 and general/accessory brochures. Acquisition resumed by user request. Historical completeness remains unverified.

## Rights Hold

First-party Toyota sources are acquired under the user's Toyota ToS assumption. EPA, Honda, IIHS and third-party archive restrictions are unchanged. All publication approvals remain false. See [SOURCE_RIGHTS_REVIEW.md](SOURCE_RIGHTS_REVIEW.md).

The user deleted all historical `toyota-honda-*` run folders. Their API records, discovery register, and archive brochures are no longer available locally. They were not recreated. Legacy source configurations are not copies of that deleted evidence. Lexus remains outside active acquisition scope.

## Approved Policy

- Active make: Toyota only. Other makes remain part of the longer-term mission.
- Model-year lower bound: 2015, inclusive, configurable. No fixed upper bound; acquire only actually documented offerings.
- Include discontinued models for their qualifying model years and markets; never exclude them merely because they are discontinued today.
- Target design markets: US, Canada, Mexico. Active collection is US-first; CA/MX are deferred and cannot inherit US coverage.
- No VIN or inventory ingestion. No release is available to the shopping agent yet.

## Retained Toyota Documents

The expanded run acquired 130 PDFs from 490 URLs: 40 official listing links plus 450 unverified historical pattern candidates. Text extraction succeeded for 129 PDFs / 2,944 pages; one image-only chart needs OCR/manual review. Layout output covers all 130 PDFs / 2,945 pages, but the chart contains no useful word evidence. No curated facts were produced.

Across the expanded run and the two earlier runs there are 139 acquisition records, representing **130 unique PDF SHA-256 hashes**. The earlier nine PDFs are duplicate bytes already represented in the expanded run. All 139 artifact hashes and byte counts were verified. Artifact byte totals (including duplicates) are 1,191,836,014 bytes. Readable symlinks are under each raw run's `pdfs/` directory; managed data remains gitignored. The owner replaced hosted PDF delivery with direct Toyota downloads; extracted data and manifests remain local.

### Original PDF Download

Run `python -m vehicle_catalog.download_pdfs` after installing requirements; see [README.md](README.md). The 130 known source URLs and checksums are in [config/toyota-pdfs.csv](config/toyota-pdfs.csv); the default refresh merges current official listing links. Live verification found 132 targets and successfully downloaded/hash-verified one ToyotaCare PDF in a temporary working directory, then skipped it on rerun. The full corpus was not redownloaded for this script check. Source availability can change; coverage is still partial.

The prior PDF ZIP was a GitHub Release asset only, never a Git object. It has been removed in favor of direct downloads; no Git history rewrite is needed. Original local PDFs and historical acquisition evidence remain intact. No extracted data is published.

Current run IDs: `toyota-us-inventory-20260922` (five listing snapshots), `toyota-us-brochures-20260922` (download/text results), and `toyota-us-layout-20260922` (offline geometry). Inspect local `data/staged/<run>/report.json` and `events/`; discovery instead has `inventory.json`. These private-data paths are not distributed on GitHub.

### Download Outcomes

| Outcome | Count |
| --- | ---: |
| Acquired PDFs | 130 |
| HTTP 404 | 347 |
| Redirects rejected for source review | 11 |
| Empty response or 100 MiB limit exceeded | 2 |
| Acquired but no usable text | 1 (included in acquired count) |

Two officially linked accessory PDFs failed the size/empty guard: 2026 Tundra and 2026 4Runner. The 2026 accessory portfolio succeeded with the explicitly larger collector limit. Redirects affect 11 guessed 2025 vehicle URLs and must be reviewed, not blindly followed or relabeled as 2025. No access/rate-limit failures were observed; future runs stop on HTTP 401/403/429.

### URL-Year Hints, Not Reviewed Identity

| URL year | Acquired PDFs |
| --- | ---: |
| 2015-2019 | 0 |
| 2020 | 8 |
| 2021 | 17 |
| 2022 | 19 |
| 2023 | 19 |
| 2024 | 20 |
| 2025 | 10 |
| 2026 | 28 |
| 2027 | 4 |
| Undated general references | 5 |

These include vehicle, accessory and reference documents, not counts of models or complete offerings. Some vehicles share brochures. Pattern candidates deliberately remain unverified and include tokens that were not offered in every year; their failures are not missing-model evidence. The tested legacy 2015 Camry `/content/ebrochure/` path also returned 404. Historical filenames/locations, revisions and discontinued offerings require an independent coverage register.

### Earlier Sample Runs

| Run | Extracted documents | Pages | Outcome |
| --- | --- | --- | --- |
| `toyota-official-vehicles-20260922` | Camry 2025, Tundra 2025, Corolla Cross 2024 | 72 | 3 of 3 extracted |
| `toyota-official-reference-20260922` | TSS 4.0, TSS 3.0, TSS 2.5/2.5+, TSS precautions, ToyotaCare, ToyotaCare BEV | 25 | 6 of 7 extracted |

- [Vehicle plan](config/toyota-documents.json)
- [Reference plan](config/toyota-reference-documents.json)

The original accessory portfolio attempt failed the 20 MiB/empty guard; the expanded run later acquired it with a 100 MiB cap. Historical reports are unchanged.

Vehicle links were discovered through [Toyota of Somerset](https://www.toyotaofsomerset.com/brochures.htm), with downloads from Toyota.com. The dealer's 2025 heading includes a 2024 Corolla Cross PDF; extracted cover text supports the individual years above. The listing is not a complete model/year register.

General documents came from [Toyota's other brochures page](https://www.toyota.com/brochures/other-brochures/). The TSS 2.5 download describes both 2.5 and 2.5+. The precautions document says MY2019 and newer and warns functionality varies. These observations do not establish trim equipment or universal program eligibility.

## Not Yet Covered

- No curated configurations, retail trim lists, or published catalogs.
- No reviewed OEM features, packages, colors, dimensions, warranties, or published document-derived claims.
- No claim of complete coverage for any sampled model year, make, model, or powertrain.
- No Canadian or Mexican source records acquired.
- No retained API detail records or model-discovery register after historical deletion.
- No curated discontinued-model configurations or verified final-offering dates.
- No comprehensive multi-market MY2015-onward inventory, complete detail-record sweep, or pre-2015 exceptions.
- No broad EV/PHEV coverage; dual-fuel mapping remains explicitly unsupported by the current automated extractor.

## Verification

- 36 unit tests passed; Black and pycodestyle passed.
- Offline CLI extracted all 9 retained PDFs / 97 pages using real Poppler tools with HTTP acquisition blocked.
- Re-extracted text hashes and page contents matched previous outputs. All retained raw/staged file hashes remained unchanged; temporary verification outputs were removed.
- New collection completed all 490 attempts; exit status 1 correctly reflects partial failures. Layout extraction completed offline for all 130 acquired PDFs. The chart's empty geometry is not semantic extraction success.
- No release publication or restoration of deleted mixed-make runs occurred. All current publication flags remain false.
- Product requirements are in [PRD.md](PRD.md); architecture, scripts and commands are in [ARD.md](ARD.md).

## Next Acquisition Work

1. Locate historical first-party sources for unresolved 2015-2019 coverage, alternate filenames, and the 11 redirected URLs; review the two oversized/empty accessory responses. Do not bypass held third-party sources.
2. Build a Toyota model/year coverage register from eligible sources and select a complete representative model-year family for factual review.
3. Validate document extraction visually, preserving trim tables, packages, colors, legends, and footnotes; review identity/applicability before mapping API facts.
4. Review Canadian/Mexican sources and terms independently before dedicated acquisition; do not relabel US data as those markets.
5. Publish a small reviewed release only after rights and configuration/evidence checks pass.

The managed corpus remains gitignored. Back up `data/` independently: the direct download manifest is not a backup of local provenance, extracted data or review state, and upstream files may disappear.