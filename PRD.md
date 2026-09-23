# Product Requirements Document

## 1. Document Control

- Product: Vehicle Reference Data Retrieval and Catalog Preparation.
- Version: 0.1, 2026-09-22; draft for project-owner review, not production acceptance.
- Current operating state: US Toyota acquisition resumed by user authorization, MY2015 onward including already-published 2027 and general/accessory brochures. Public delivery contains code/docs, not raw data. No publication is scheduled.
- Technical companion and operator commands: [ARD.md](ARD.md).
- Decision authority: project owner for scope; designated source-use reviewer for rights; vehicle-data reviewer for factual applicability. Named assignees and release approver remain to be assigned.

## 2. Problem and Outcome

A deterministic vehicle-shopping agent needs auditable reference facts, not answers reconstructed from model memory or whole brochures at runtime. Source documents vary by market, year, trim, drivetrain, package, and effective date. Public source labels are not necessarily retail trims, and missing information is not evidence that equipment is unavailable.

Build a repeatable offline process to retrieve approved source evidence, preserve originals, extract reviewable data, and eventually publish validated local JSON catalogs. The immediate deliverable is trustworthy raw acquisition and staging, not a claim of complete Toyota coverage or an autonomous document-to-facts system.

The eventual catalog complements the existing Search service, which owns OpenSearch-backed inventory navigation and JD Power access. This project neither replaces that service nor calls JD Power for inventory.

## 3. Users and Workflows

| User | Job to be done |
| --- | --- |
| Data operator | Select approved sources, run bounded retrieval, find readable originals, inspect failures, and re-extract without redownloading |
| Vehicle-data reviewer | Verify identity, table columns, legends, footnotes, package conditions, and market/year applicability against original pages |
| Source-use reviewer | Establish permitted acquisition, processing, retention, and distribution independently of factual correctness |
| Agent engineer | Load a versioned catalog once per process and query deterministic Python methods with evidence and coverage boundaries |
| Shopper, downstream | Get supported trim, feature, color, specification, economy, and safety comparisons with explicit unknowns |

Representative downstream questions include: Tundra trim differences; available colors; which configurations have head-up displays; and changes between model years. Cross-make comparison remains an eventual goal, not an MVP coverage claim. Model-year change detection is not implemented.

## 4. Scope

### Active MVP

- Toyota only, MY2015 onward, including discontinued models for qualifying years. The year floor is configurable; do not delete old reference records merely because vehicles age.
- Market-aware design for US, Canada, and Mexico. Current retained evidence is US-only; no cross-market relabeling.
- First-party vehicle PDFs plus general references such as TSS, ToyotaCare, and accessories. A general reference is not a vehicle configuration and has no invented model/year.
- Approved structured government endpoints through dedicated adapters. NHTSA NCAP acquisition is configured; EPA implementation exists but remains on hold.
- Original-byte storage, provenance, checksums, readable PDF names, extraction outputs, run reports, and explicit failures.
- Manual scope/applicability review before facts are promoted into curated data or a release.

### Out of Scope

- VIN decoding, VIN-level records, individual inventory, pricing/offers for a specific dealer vehicle, and customer personal data.
- Unbounded crawling, bypassing access controls, or silently expanding makes/markets.
- Automatic OCR, reliable PDF table interpretation, automatic trim inheritance, fuzzy source-to-trim assignment, or universal applicability inferred from a general brochure.
- Public brochure redistribution, image reuse, model training, or sending originals to external AI processors without separately established scope and rights.
- Production hosting, a new retrieval service/OpenSearch index, and replacement of the existing inventory APIs.

Lexus ToS may be assumed satisfied per user instruction, but Lexus is not currently in acquisition scope. Other makes remain part of the longer-term product mission.

## 5. Source Strategy

| Source class | Intended contribution | Current state |
| --- | --- | --- |
| Toyota-hosted vehicle brochures | Trim, equipment, colors, dimensions and specifications, subject to page review | Download/extract supported; 3 PDFs retained |
| Toyota general brochures | System definitions, limitations, ownership programs, accessory context | Download/extract supported; 6 PDFs retained; not trim equipment evidence by themselves |
| NHTSA NCAP JSON | Configuration-specific safety ratings | Adapter available; one Toyota target configured; no retained API run after historical deletion |
| FuelEconomy.gov JSON/menu data | Economy, range, source variants and discovery | Adapters available; acquisition held pending commercial-use clarification |
| HTML, manuals, pressroom/spec sheets | Discovery pointers or future complementary evidence | Low-level HTML byte capture exists; no semantic HTML extractor or dedicated acquisition plan |
| IIHS, third-party archives, licensed feeds | Additional ratings or historical coverage | Not cleared/implemented as active ingestion paths |

The user directs us to assume Toyota/Lexus ToS are satisfied for intended project use. This does not resolve third-party terms. All current publication flags remain false. See [SOURCE_RIGHTS_REVIEW.md](SOURCE_RIGHTS_REVIEW.md) for the source review and limitations.

## 6. Functional Requirements

| ID | Requirement | Acceptance evidence |
| --- | --- | --- |
| FR-01 | Run only selected, in-scope, approved acquisition targets | Reject unapproved/out-of-scope plan before network access |
| FR-02 | Download PDFs directly from reviewed URLs; manual download must not be required | Bounded document command stores originals and extracts pages |
| FR-03 | Preserve each original response with source ID/URL, retrieval timestamp, media type, byte count and SHA-256 | Every successful raw artifact has a manifest and matching bytes |
| FR-04 | Expose understandable PDF names without replacing canonical evidence | Relative `pdfs/<source-id>.pdf` links resolve to hash-verified originals; conflicts fail |
| FR-05 | Separate acquisition from text/JSON extraction, review, and publication | Raw failures and extraction failures distinguishable; no automatic published facts |
| FR-06 | Re-extract retained managed PDFs without network access or overwriting previous output | Offline command checks current source plan and writes fresh output/report |
| FR-07 | Preserve physical page boundaries, blank pages, extraction tool/version and warnings | Page-count validation; empty/scanned PDFs become explicit failures, not fabricated facts |
| FR-08 | Distinguish general references from vehicle evidence | Reference targets reject model/year fields; version/applicability stays reviewable |
| FR-09 | Report requested, successful, failed, and unattempted work | Per-target events and final report; partial failure returns nonzero; prior successes retained |
| FR-10 | Prevent silent overwrites and preserve provenance across revisions | Fresh acquisition run IDs; conflicting writes rejected; old results unchanged |
| FR-11 | Support structured JSON without a PDF prerequisite | NCAP/EPA-specific validation and candidate extraction tests; source approvals still apply |
| FR-12 | Record coverage gaps explicitly | Counts distinguish source documents, source records, and reviewed configurations; missing is not unavailable |
| FR-13 | Publish only evidence-backed, reviewed configuration facts | Explicit reviewed mappings, evidence references, and publication approval checks |

Arbitrary unregistered local PDFs are not an implemented input. Offline mode accepts managed raw artifacts plus manifests. A future import workflow must preserve source provenance and distinguish local import time from original download time.

## 7. Quality and Operational Requirements

- Determinism: extraction settings and source hashes recorded; identical inputs/settings produce the same textual content where tool behavior permits. Run IDs/timestamps are provenance, not stable content identifiers.
- Integrity: detect modified originals before downstream use. Write-once conventions are not tamper-proof storage or an access-control system.
- Safety: bounded downloads and subprocess timeouts; no secrets in plans; no redirect following without source review. PDF parsing is not yet sandboxed.
- Correctness: distinguish unknown, unavailable, optional, package-dependent, and standard. Preserve units, methodology, conditions, and disclosures. Retain US/CA/MX separately.
- Latency: no PDF parsing, network requests, or model reasoning in catalog lookup. Load/index once per process. A representative scale and numeric p95 latency/memory budget must be agreed and measured before production acceptance; no benchmark claim is made now.
- Portability: Python 3.11+ and Poppler for PDF work; current validation environment is macOS. Other OS support, including symlink behavior, is unverified.
- Retention: `data/` is gitignored. Operator must arrange approved backup and restore testing before treating the corpus as durable. No automatic backup exists.

## 8. Current Baseline

Before expanded collection on 2026-09-22, two Toyota runs contained 9 PDFs / 97 pages. Latest totals are in [DATA_STATUS.md](DATA_STATUS.md):

- Vehicle: Camry 2025, Tundra 2025, Corolla Cross 2024; 72 pages.
- General: TSS 4.0, TSS 3.0, TSS 2.5/2.5+, TSS precautions, ToyotaCare, ToyotaCare BEV; 25 pages.
- The original accessory attempt failed the empty-response/20 MiB guard. The new Toyota collector explicitly permits 100 MiB; generic fetch remains 20 MiB by default.
- No curated configurations or published release. Extracted pages remain unreviewed; a filename is not approval of document applicability.
- The user deleted all historical mixed Toyota/Honda run folders. Their previously reported API/discovery/archive counts are not available evidence and must not be restored without authorization.

This baseline is a sample, not complete lineup, trim, year, geography, or discontinued-model coverage.

## 9. Acceptance and Release Gates

| Gate | Required outcome |
| --- | --- |
| G1: Raw pipeline handoff | Operator commands documented; synthetic tests pass; retained originals hash-check; offline extraction exercised on real PDFs without network; holds preserved |
| G2: Representative factual pilot | Reviewer checks one complete model-year family, selected trim tables and footnotes visually; identity and conditional facts supported; unresolved cells remain unknown |
| G3: Coverage expansion | Reviewed Toyota year/model/market register with explicit source/gap state; source permissions and operational limits checked before each new plan |
| G4: Production publication | Current rights decisions enforced independently of historical snapshots; named approvals; backup/restore and release rollback demonstrated; agreed runtime performance verified |

G1 does not imply G2-G4 acceptance. Stop a run when approval or scope preflight fails; keep a recorded partial result when individual source operations fail. Do not infer success from exit status of only an intermediate command.

## 10. Risks and Open Decisions

| Risk / question | Required treatment |
| --- | --- |
| Dealer headings differ from PDF years | Verify PDF cover/content, not only listing labels or URL paths |
| Same brochure covers multiple powertrains or versions | Preserve one original; review each applicability assignment separately |
| PDF columns/inheritance/footnotes misread | Page-image verification and reviewer sign-off before structured facts |
| General safety/program information overgeneralized | Retain system version, eligibility, time/mileage limits and exclusions; never infer fitted equipment |
| Rights change after acquisition | Current-decision gate for processing/publication is a production requirement, not fully implemented |
| Source disappears or mutable URL changes | Preserve retrieved bytes, hash and time; never replace old evidence silently |
| History/Canada/Mexico coverage unclear | Build a coverage register and approved source plan; no implied parity with US |
| Large/scanned documents | Decide size policy and OCR/sandbox requirements explicitly; present failures meanwhile |

Next work: audit historical coverage, assign reviewers, and agree the first model-year family and quality/performance targets. See [TASKS.md](TASKS.md).

## 11. End-State Curated Schema

The target contract below extends the executable v0.1 schema. Proposed entities require a versioned migration, builder and reader support before publication.

| Entity | Required meaning and relationships | Current support |
| --- | --- | --- |
| Vocabulary and aliases | Canonical make/model/trim/feature/metric identities; aliases scoped by publisher, market and year | Initial feature/metric vocabulary; alias registry proposed |
| Model-year offering | Market, model, year, trims, variants, source-backed offering dates, discontinued history and completeness | Configuration fields today; explicit offering entity proposed |
| Configuration | Stable ID, market/year/make/model/trim and relevant body, powertrain, drivetrain, engine, transmission, battery, wheel, cab/bed discriminators | Implemented; unknown discriminators do not imply universal applicability |
| Feature | Controlled capability, standard/optional/package/unavailable status, conditions and evidence | Implemented; missing means unknown |
| Measurement | Metric, numeric value, unit, basis/test cycle, fuel, conditions; MSRP must preserve currency/date/exclusions | Core implemented; structured ranges and price exclusions proposed |
| Specification | Controlled descriptive attribute/value, applicability and evidence | Implemented |
| Rating | Agency, test, methodology/version, scale, result and tested applicability | Implemented; methodologies cannot be silently equated |
| Color combination | Interior/exterior code/name, availability, pairing and trim/package/date restrictions | Basic colors/pairings implemented; normalized combinations proposed |
| Package/accessory | Offering-scoped code, contents, dependencies/exclusions, pricing, compatible configurations and factory/port/dealer installation channel | Package codes only today; graph/accessory entities proposed |
| Reference knowledge | Versioned system definitions and limitations, linked to configurations only with separate fitment evidence | Staged PDFs only; curated entity proposed |
| Ownership/warranty | Provider, market, eligibility, effective dates, duration AND/OR distance limits, exclusions and transferability | Staged PDFs only; typed entities proposed |
| Applicability | Explicit configuration scope, packages, regions, production/effective dates; unsupported scope remains unresolved | Basic conditions implemented; typed expressions proposed |
| Evidence/review | Artifact/hash, exact source wording/value, physical page/region or JSON pointer, legends/footnotes; reviewer, date, decision and rationale | Basic references/reviews implemented; typed geometry and authenticated approvals proposed |
| Coverage/conflict | Market/model/year/document/fact-family denominator, attempts, acquired/extraction/review states, unresolved reasons | Run reports and notes implemented; normalized entities proposed |
| Release/change | Schema/data version, source revisions, mapping hash, coverage, supersession and explicit model-year change evidence | Releases implemented; signed manifests, rollback and reviewed change entities proposed |

### Raw-to-Curated Acceptance

1. Preserve original bytes and provenance; verify market/model/year and vehicle/reference/accessory classification from content, not filename alone.
2. Extract physical-page text and word/line/block geometry. Retain symbols, legends, units and footnotes. Geometry is not a semantic table.
3. Review table boundaries, spanning headers, cells, legends and footnote links. Preserve original cells and regions before normalization. Image-only content needs separately approved OCR/manual transcription.
4. Resolve labels to canonical identities and vocabulary. Record transformations, units, methodology, conditions and reviewer decisions.
5. Validate source-use approval, referential integrity and conflicts. Publish only accepted claims; retain rejected/unresolved candidates outside runtime data.
6. Test representative shopping questions against reviewed golden records. Coverage describes answerable questions, not PDF counts.

General system descriptions do not prove equipment fitment; accessories do not prove installation. Package dependencies must be acyclic and satisfiable. Ownership benefits must retain eligibility and limit semantics. Missing facts cannot establish unavailability or model-year removal. Historical completeness requires an independently reviewed US offering/document register for each year since 2015. URL guesses are not that denominator. CA/MX remain deferred.