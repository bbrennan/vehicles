# Product Requirements Document

## 1. Document Control

- Product: Vehicle Reference Data Retrieval and Catalog Preparation.
- Version: 0.2, 2026-09-22; adds proposed brochure narrative design; draft for project-owner review, not production acceptance.
- Current operating state: US Toyota acquisition resumed by user authorization, MY2015 onward including already-published 2027 and general/accessory brochures. Public delivery includes code/docs and a source-URL/checksum manifest for direct local PDF downloads from Toyota. The hosted ZIP is removed; PDFs, extracted JSON/text/layout and local manifests stay out of Git. No curated catalog publication is scheduled.
- Technical companion and operator commands: [ARD.md](ARD.md).
- Decision authority: project owner for scope; designated source-use reviewer for rights; vehicle-data reviewer for factual applicability. Named assignees and release approver remain to be assigned.

## 2. Problem and Outcome

A deterministic vehicle-shopping agent needs auditable reference facts, not answers reconstructed from model memory or whole brochures at runtime. Source documents vary by market, year, trim, drivetrain, package, and effective date. Public source labels are not necessarily retail trims, and missing information is not evidence that equipment is unavailable.

Build a repeatable offline process to retrieve approved source evidence, preserve originals, extract reviewable data, and eventually publish validated local JSON catalogs. The immediate deliverable is trustworthy raw acquisition and staging, not a claim of complete Toyota coverage or an autonomous document-to-facts system.

The eventual catalog complements the existing Search service, which owns OpenSearch-backed inventory navigation and JD Power access. This project neither replaces that service nor calls JD Power for inventory.

Alongside hard facts, a proposed reviewed narrative layer will help the agent explain how features work and why they may matter to a shopper's stated needs. It is explanatory context, not an alternative source of equipment availability, objective rankings or guaranteed outcomes. See Section 12 for its extraction, retrieval and evaluation plan.

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
- Hosted brochure redistribution (replaced by direct local downloads), separate image reuse, model training, or external AI processing without separately established scope and rights.
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
| FR-14 | Extract atomic narrative candidates separately from typed facts | Each candidate preserves source passage, physical page/region, qualifiers, footnotes and pending review state |
| FR-15 | Publish only reviewed, correctly scoped explanations and attributed positioning | Fact-dependent narratives resolve to accepted facts; unresolved applicability, contradictions and unsupported claims block publication |
| FR-16 | Retrieve a bounded narrative bundle using deterministic scope and intent filters | Stable ordering, release/evidence IDs, required qualifiers, explicit unknowns; no runtime document search or network |
| FR-17 | Improve explanation usefulness without reducing factual accuracy | Fact-only versus fact-plus-narrative pilot passes the factual, safety and attribution gates in Section 12 |

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
| Narrative talking point | Atomic reviewed explanation, practical benefit or attributed OEM positioning; intent tags, applicability, supporting fact/knowledge IDs, qualifiers and evidence | Proposed; no narrative extractor, schema or reader method implemented; see Section 12 |
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

## 12. Brochure Narrative and Talking Points

### Decision and Product Hypothesis

Extract selected talking material as **reviewed explanatory knowledge**, alongside but separate from hard facts. Specifications answer "what does it have?"; explanations answer "how does it work?" and "why might that matter for my use?" Brochures are useful first-party descriptions, but not independent road tests or neutral comparative assessments. Do not ingest all promotional copy as answer-ready truth.

Hypothesis: a small set of scoped, evidence-linked talking points improves the relevance and clarity of shopping answers over facts alone, without increasing unsupported assertions. A paired evaluation on the same shopper questions can disconfirm this; failing the factual gates or showing no usefulness gain blocks expansion.

### Evidence From the Retained Sample

The retained US 2025 Camry brochure illustrates the distinction. Its performance section combines a description of available AWD torque delivery with variant-dependent horsepower and an "up to" economy figure; nearby copy adds subjective driving language. Design and comfort sections mix trim-specific styling, available equipment, photo captions and broad comfort claims. The existing raw text preserves those passages, and layout extraction supplies page/word geometry, but neither identifies their semantic scope automatically.

| Brochure material | Treatment | Boundary |
| --- | --- | --- |
| AWD operating description | Candidate system explanation, linked to the reviewed system version and AWD fitment facts | Do not apply to FWD or imply guaranteed traction/safety in every condition |
| Economy or horsepower in promotional prose | Route the numerical claim to the typed fact workflow first | Never combine maxima from different configurations; retain basis, qualifiers and disclosures |
| Available heated/ventilated seats | Candidate comfort explanation linked to verified availability | Do not describe the feature as standard or fitted to a listed vehicle |
| Trim-specific styling description | Scoped design talking point, separating observable attributes from subjective positioning | Do not propagate one trim's design/materials across the model family |
| Broad claims of excitement, luxury or ideal lifestyle fit | Usually omit; retain useful distinctions only as attributed OEM positioning | Not an independent judgment, proof of superiority or personalized suitability |
| TSS/ToyotaCare general-reference material | Shared versioned knowledge/program records with limitations and eligibility | A general reference does not establish vehicle fitment or a used shopper's current eligibility |

These are extraction-design examples, not approved facts or publishable vehicle recommendations. Pilot reviewers must verify complete source pages, equipment tables and disclosures before accepting them.

### Content Classes and Editorial Rules

- `system_explanation`: what a system does and how it operates; factual, version-specific and evidence-backed. Generic explanation may be used without asserting fitment; vehicle-specific use requires a supporting fitment fact.
- `practical_benefit`: a restrained, reviewer-approved connection between a supported feature and a stated shopper need. Mark whether the source states the benefit or a reviewer derived it. A derived rationale must not introduce unmeasured performance, reliability, safety or savings claims.
- `oem_positioning`: useful subjective manufacturer framing, explicitly attributed in the answer, such as Toyota's emphasis on a trim's sporty design. Excluded from objective scoring, filtering and winner selection.

Keep one claim per candidate. Split mixed passages into separate facts, explanations and positioning so a qualifier cannot be lost during summarization. Prefer concise original paraphrases; keep source wording in restricted evidence storage rather than reproducing long brochure passages in shopper answers. The Toyota/Lexus ToS assumption remains in force; normal publication/source-use controls still apply, and this plan does not authorize external AI processing or model training.

Discard generic slogans, unsupported superlatives, urgency language and claims of universal lifestyle fit. Dated awards or comparisons require a separately reviewed factual claim with issuer, date, comparison set and methodology; exclude them from the initial narrative pilot. Historical launch offers, connectivity subscriptions, warranties and ownership benefits require explicit effective dates and eligibility, not an assumption that they remain valid for a used vehicle today. Never use brochure positioning to compensate for missing facts or unresolved conflicts.

### Proposed Data Contract

Add a `NarrativePoint` collection to a future versioned release, referencing the same canonical applicability, knowledge, fact and evidence entities as Section 11. Do not overload `SpecificationFact.value` or duplicate a technical explanation across every configuration. Existing v0.1 models and runtime APIs remain unchanged until migration is implemented.

| Field group | Required content |
| --- | --- |
| Identity/version | Stable point ID, revision, content class, language, source revision and supersession relationship |
| Content | Short title and neutral approved text; distinction between source-stated content and reviewer-derived rationale; explicit publisher attribution for positioning |
| Relevance | Controlled topic and shopper-intent tags, such as commuting, cabin comfort, cargo, towing, traction, accessibility or design; editorial priority, not a persuasive score |
| Applicability | Explicit model-year offering/configuration IDs or generic system scope; market, system version, package/region/production constraints and effective dates where relevant; unresolved scope cannot be published |
| Dependencies | Supporting accepted fact IDs and/or shared knowledge/program IDs; vehicle-specific feature explanations require fitment support; numerical claims use fact references rather than copied values |
| Qualifications | Structured required qualifiers and limitations with evidence; attribution requirement; allowed usage (`generic_explanation`, `vehicle_explanation`, `attributed_description`); prohibited stronger implications |
| Evidence | Artifact ID/hash, physical page and region, exact source span, heading context, related table/caption/legend and footnote references, extraction method/version |
| Review | Pending/accepted/rejected/needs-evidence/superseded status, reviewer, date, rationale, factual and editorial decisions, publication decision reference |

Raw spans and proposal/rejection history stay in staging/curation. The runtime projection includes only approved text, supported references, resolved applicability, required qualifications and compact citation locators. Missing qualifiers are not an empty default: reviewers must explicitly confirm whether none apply. Qualifiers travel with the point as one indivisible retrieval unit. Build rejects unresolved references, incompatible markets/years/versions, expired usage, contradictory claims and missing attribution. Any changed supporting fact, source revision or scope invalidates dependent approval until re-reviewed; activated releases remain immutable.

### Offline Extraction and Review Plan

1. Select a small pilot from retained vehicle and general-reference PDFs. Reuse page text and layout; introduce no new acquisition solely for this pilot.
2. Propose heading/paragraph/caption regions using layout and section context. Retain neighboring context and disclosure references; separate columns explicitly. Image-only text and uncertain reading order enter a manual-review queue rather than producing guessed claims.
3. Classify and split passages into typed-fact candidates, system explanations, practical benefits, OEM positioning and discarded copy. Normalize controlled tags; preserve original labels and all qualifiers. Optional model-assisted drafting is an offline proposal step only, subject to separately approved processing; deterministic/manual extraction must remain viable.
4. Link candidate scope and dependencies to reviewed configuration facts or shared knowledge. General-reference explanations may remain generic, but cannot answer "does this car have it?" without fitment evidence. Deduplicate shared explanations by system/version and preserve each supporting source; repeated marketing language is not independent corroboration.
5. Have the vehicle-data reviewer verify source entailment, scope and conditions, and an editorial review verify paraphrase, attribution and usefulness. One named reviewer may hold both roles in the pilot, with separate recorded decisions. Factual uncertainty is a blocker, not a model-confidence threshold.
6. Build a versioned narrative projection, validate dependency/qualification invariants, and test it with the factual release. Enable only accepted points; keep staged candidates inaccessible to the shopper agent. Audit and rollback facts and narratives together using a pinned release ID.

### Runtime Agent Design

Preserve deterministic local retrieval. A proposed API such as `talking_points(subject_id, intent_tags, release_id, limit=3)` returns a typed evidence bundle, not free-form brochure chunks. A subject must be a resolved configuration, model-year offering, or generic system/version; each has different permissible claims. This method and the narrative index are not implemented today.

1. Resolve explicit shopper context and fetch hard facts first when the question concerns availability, specifications, comparisons or eligibility. The existing Search service remains authoritative for individual inventory. Brochure data must never establish that a specific used vehicle has optional equipment or an active benefit.
2. Filter accepted points by market/year/subject, supported dependencies, resolved conditions, effective dates and allowed usage. With unknown trim/package context, withhold conditional vehicle claims or return them as explicitly conditional model-level descriptions; do not silently satisfy unknown conditions. Ask a targeted clarification only when needed to answer the actual question.
3. Rank eligible points by controlled intent match, scope specificity and reviewed editorial priority, then stable ID for ties. Deduplicate overlapping points; return at most three initially, with truncation/coverage indicators. No vector database, network, document parsing or model relevance judgment is required within the lookup. An agent may map natural language to allowed intent tags, but that mapping cannot widen applicability.
4. Return each point's approved text, content class, fact references, qualifiers, attribution, evidence locators and release ID. Exact filters/specification answers use facts, not narrative matching. No match means no supported talking point, not that the vehicle lacks the feature.
5. Prefer approved templates in the first pilot. If the ecommerce agent generates connective prose, it must preserve all facts, availability qualifiers, limitations and attribution, and cite the evidence bundle. It may not add comparisons, guarantees or benefits absent from the bundle. Validate structured output references and required clauses; on failure, fall back to the approved text or fact-only answer. Such checks constrain output but do not prove arbitrary free-form prose correct, so generation requires separate evaluation.

Brochure text is untrusted source data, never agent instructions. It cannot change tool permissions, prompt policy or source priority. Unknowns and conflicting evidence remain visible. A fact/narrative contradiction blocks the point and requires review rather than silently allowing one claim to overwrite another. Keep full internal evidence links even when shopper-facing citation display is compact; positioning must remain attributed in the visible answer.

### Pilot Tasks and Acceptance

All tasks below are planned, not delivered by this PRD update. Use Camry 2025, Tundra 2025 and Corolla Cross 2024 plus relevant retained general references as an initial mixed-use sample; this is not complete narrative coverage.

| Task | Deliverable and dependency |
| --- | --- |
| N1: Label a sample | Review 30-50 candidate passages across performance, comfort, design, utility and safety/ownership limitations; record accepted/rejected classes and reasons |
| N2: Establish factual support | Review the identities, fitment facts, system versions and eligibility needed by selected points; unresolved dependencies stay blocked |
| N3: Implement contract/extraction | Versioned candidate and curated schemas, reusable raw-layout extraction, review workflow and dependency invalidation; update ARD when implementation begins |
| N4: Implement retrieval | Release projection and local index, deterministic filters/ranking, compact evidence bundles and approved rendering templates |
| N5: Evaluate and gate | Paired fact-only versus fact-plus-narrative benchmark; report usefulness, unsupported claims, qualifier/attribution retention, coverage, review effort and incremental latency/memory |
| N6: Roll out selectively | Enable reviewed subjects/intents only after acceptance; retain fact-only fallback, pin releases and test rollback; expand by reviewed coverage rather than PDF volume |

Before drafting the pilot points, lock at least 40 evaluation questions and expected constraints, including helpful explanations and adversarial cases: wrong market/year/trim, FWD versus AWD, optional versus standard, mismatched maxima, unspecified package, used-car benefits, expired programs, attributed positioning, conflicting sources, missing evidence and instruction-like source text. Include TSS limitations without claiming collision prevention or independent safety superiority. Keep a portion of questions held out from wording and rule tuning.

Acceptance requires zero unsupported objective claims, fitment/market/year leakage or safety guarantees in the test set; 100% preservation of applicable qualifiers, attribution, valid evidence references and release consistency; correct withholding/fallback for every negative fixture; and stable retrieval ordering for identical inputs/releases. These are pilot gates, not a claim of zero production risk. Reviewers should prefer fact-plus-narrative answers for usefulness on at least 70% of the explanatory-question subset, with ties reported separately and no critical factual regression. Failure of either factual or usefulness gates blocks expansion. Measure warm lookup overhead and worker memory separately from answer-generation time, and agree a numeric production budget under Section 7 before rollout. Record review minutes per accepted point to determine whether the approach is economical to scale.

Use narrative to explain supported choices, not to maximize persuasion. Match only shopper-stated needs; do not infer sensitive traits, invent personal suitability or hide tradeoffs to steer a sale. Cross-vehicle recommendations must still rest on comparable reviewed facts and the shopper's explicit criteria, not the intensity of brochure language.