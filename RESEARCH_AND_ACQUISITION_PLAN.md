# Vehicle Reference Data: Research and Raw Acquisition Plan

Research date: 2026-09-22
Status: Historical source research with subsequent implementation decisions recorded below; source permissions and coverage still require confirmation.

## Subsequent Decisions

- Active scope is Toyota-only, MY2015 onward, including discontinued models for qualifying years. This supersedes the deleted Toyota/Honda pilot. US-first acquisition resumed by user request, including already-published 2027 and general/accessory brochures; CA/MX remain deferred. [DATA_STATUS.md](DATA_STATUS.md) records actual coverage. [PRD.md](PRD.md) and [ARD.md](ARD.md) supersede this historical plan where they differ.
- Coverage targets any new or used vehicle of any make that could appear at a Toyota or Lexus dealership in North America. US/Canada/Mexico are separate schema markets; country-specific source coverage is not yet established.
- The existing agent uses two APIs on the existing OpenSearch-based Search service for inventory exploration. It does not call JD Power directly. This project does not replace that inventory path or ingest VIN-level data.
- The reference catalog will initially be local, versioned JSON accessed through deterministic Python methods. No additional Search service operation or OpenSearch index is required for this implementation.
- The user has now requested a first harmonized schema and acquisition/transformation/mapping scripts. See [README.md](README.md) and [schemas/catalog.schema.json](schemas/catalog.schema.json) for the v0.1 implementation and limitations.
- The original recommendations below to defer all schema work are superseded by that request. Preserve raw acquisition separately and revise the initial schema against representative source evidence before declaring it production-ready.

## 1. Purpose and Agreed Direction

Build an auditable vehicle reference dataset for an ecommerce vehicle shopping agent. The eventual catalog must support filtering by model year, make, model, and trim, including features, safety ratings, fuel economy, and electric range.

The intended agent behavior is to answer vehicle-fact questions from approved evidence rather than model memory. A catalog alone cannot guarantee this behavior; evidence requirements and answer enforcement will need to be designed and tested in a later phase.

### Confirmed scope decisions

- VIN decoding, VIN-level information, and individual inventory vehicles are out of scope.
- Start with raw data acquisition, not a canonical vehicle schema.
- Perform a second discovery and design round using the acquired material to determine standardization requirements.
- A first schema and local JSON reader are now implemented; final coverage, agent contracts, and production schema approval still require validation against acquired data.
- Year/make/model/trim is the desired filtering interface, not an assumption that all sources publish at that granularity.

### Working assumptions, not approved scope

- The government examples researched here are US-oriented; this is a current source limitation, not the North American catalog's intended coverage boundary.
- Begin with a representative pilot rather than attempting every manufacturer and model year.
- Prioritize source coverage and evidence quality over the number of acquired documents.
- Retain original source terminology and structure during acquisition.

## 2. Executive Findings

1. No single source researched here provides complete, authoritative trim equipment, safety ratings, and efficiency data together.
2. OEM brochures and specifications are promising sources for trim equipment, but package conditions, legends, footnotes, revisions, and market differences must survive acquisition.
3. FuelEconomy.gov is an important addition to the initial source list. It provides structured EPA fuel economy and range information, APIs, and bulk downloads.
4. NHTSA safety ratings are separate from vPIC. The observed safety records identify vehicle variants, not a universal trim taxonomy.
5. vPIC is primarily a manufacturer-information and VIN-decoding resource. It should not be the foundation of this project. Evaluate only its non-VIN reference endpoints if they solve a demonstrated acquisition need.
6. Data.gov's vPIC entry points to the same underlying service. It is a discovery/metadata record, not an independent corroborating source.
7. IIHS contributes distinct safety information, but its published policy requires written permission for commercial copying or redistribution. Treat commercial ingestion as permission-gated.
8. Public accessibility does not establish permission for bulk collection, long-term storage, redistribution, or commercial use.
9. Cross-source standardization is necessary, but its rules should be based on the raw corpus rather than assumed in advance.

## 3. Source Assessment

### 3.1 Auto-Brochures.com

Sources reviewed:

- [Homepage](https://www.auto-brochures.com/)
- [About the collection](https://www.auto-brochures.com/_about.html)
- [Toyota brochure index](https://www.auto-brochures.com/toyota.html)
- [2024 Toyota RAV4 brochure](https://www.auto-brochures.com/makes/Toyota/RAV4/Toyota_US%20RAV4_2024.pdf)

Observed findings:

- The site describes its collection as mainly US-market brochures, with some international-market material, particularly for smaller-volume manufacturers.
- It distinguishes newer, originally digital PDFs from older scanned brochures.
- The Toyota index contains multiple model years and examples of multiple brochure revisions for a model year.
- A 2024 RAV4 PDF was accessible. The web text reader could not extract meaningful content, but local `pdftotext -layout` extraction completed successfully.
- That spot-check establishes text-extraction feasibility for one PDF only. Trim-column alignment, feature assignments, footnotes, page citations, and extraction accuracy were not validated.

Potential role: historical OEM-document discovery and acquisition where permission permits.

Limitations and follow-up:

- Do not infer completeness from the size of the archive.
- Verify model year and market inside each document, not just in the filename or index label.
- Record the document's OEM publisher separately from its archive host.
- An archive copy and the same OEM-hosted brochure are not two independent factual sources.
- No commercial acquisition or reuse permission was established in this research. Review applicable terms and seek clarification before bulk collection.

### 3.2 OEM Websites and Documents

Sources reviewed:

- [Toyota brochure directory](https://www.toyota.com/brochures/cars-minivan/)
- [Toyota vehicles page reached through an older brochure route](https://www.toyota.com/all-vehicles/ebrochure/)
- [2026 Toyota Camry brochure](https://www.toyota.com/content/dam/toyota/brochures/pdf/2026/camry_ebrochure.pdf)
- [Toyota legal terms](https://www.toyota.com/support/legal-terms/)
- [2024 RAV4 pressroom URL attempted](https://pressroom.toyota.com/vehicle/2024-toyota-rav4/)

Observed findings:

- Toyota's current brochure directory exposes direct PDF links, including current and upcoming model-year documents.
- The older brochure route returned a vehicle-listing page, illustrating that discovery URLs can change function.
- The Camry PDF could not be meaningfully extracted by the web text reader. No local extraction was attempted for that document.
- The RAV4 pressroom request returned HTTP 403. Its content was not verified.
- The legal-terms fetch returned insufficient substantive terms to establish acquisition or reuse rights.

Potential role: primary published evidence for trim names, standard/optional equipment, packages, dimensions, powertrains, towing, warranties, and manufacturer estimates, subject to the actual document's coverage.

Limitations and follow-up:

- This was a Toyota spot-check, not a cross-OEM coverage study.
- Research official brochures, specification sheets, order guides, and equipment matrices separately. They may provide different levels of detail.
- Owner manuals can describe equipment that is optional or unavailable on a particular trim; they are not proof of trim inclusion.
- Marketing phrases such as "available" and "up to" must retain their qualifications.
- Current webpages may replace historical information. Preserve permitted snapshots and revision metadata.
- Do not bypass access controls. Use permitted documents, request access, or record an acquisition gap.

### 3.3 NHTSA vPIC and Data.gov

Sources reviewed:

- [vPIC API documentation](https://vpic.nhtsa.dot.gov/api/)
- [vPIC FAQ](https://vpic.nhtsa.dot.gov/api/Home/Index/FAQ)
- [Data.gov vPIC JSON catalog entry](https://catalog.data.gov/dataset/nhtsa-product-information-catalog-and-vehicle-listing-vpic-vehicle-api-json)

Observed findings:

- vPIC is populated from manufacturer submissions and is strongly oriented toward vehicle identification and VIN decoding.
- It documents non-VIN make/model discovery endpoints, including `GetModelsForMakeYear`.
- The FAQ says the public API does not require application registration or a licensing requirement to use the service.
- The API documentation warns of automated traffic-rate controls. Public availability is not an operational service-level guarantee.
- The Data.gov entry links to vPIC and showed an unknown-license metadata link. That metadata label should not be treated as a definitive legal determination; evaluate the publisher's terms directly.

Recommendation: exclude VIN endpoints entirely. Keep non-VIN reference endpoints optional until a concrete discovery need justifies them. Nothing reviewed establishes vPIC as a complete consumer trim or feature catalog.

### 3.4 NHTSA Safety Ratings and Other Datasets

Sources reviewed:

- [NHTSA datasets and APIs](https://www.nhtsa.gov/nhtsa-datasets-and-apis)
- [2024 Toyota RAV4 safety-record lookup](https://api.nhtsa.gov/SafetyRatings/modelyear/2024/make/Toyota/model/RAV4?format=json)
- [Safety record 19443](https://api.nhtsa.gov/SafetyRatings/VehicleId/19443?format=json)

Observed findings:

- NHTSA lists separate resources for ratings, recalls, investigations, complaints, and manufacturer communications.
- The RAV4 lookup returned two records: `19443`, described as "2024 Toyota RAV4 SUV AWD", and `19442`, described as "2024 Toyota RAV4 SUV FWD".
- Record `19443` returned separate overall, frontal, side, and rollover ratings, plus other fields. It also included a `Not Rated` value for a secondary rollover field.
- These source-specific vehicle record IDs identify reference entries; they are not VINs and do not introduce VIN-level scope.
- The general ratings webpage could not be reliably retrieved with the web reader; it surfaced a tracking redirect. The datasets page and example API responses were accessible.

Potential role: official NCAP safety-rating records, preserved at their published granularity.

Limitations and follow-up:

- Do not assume a rating belongs to every trim based on matching year/make/model text alone.
- Retain the source description, component ratings, test metadata, applicability notes, and unavailability markers where supplied.
- Verify comparison rules, historical methodology changes, and coverage before designing safety comparisons.
- The returned endpoints were spot-checked; a full API contract, coverage audit, and production access test were not completed.
- Recalls and complaints are optional future scope. They are not substitutes for safety ratings or validated reliability scores.

### 3.5 FuelEconomy.gov / EPA

Sources reviewed:

- [Web services and field documentation](https://www.fueleconomy.gov/feg/ws/)
- [Download fuel economy data](https://www.fueleconomy.gov/feg/download.shtml)
- [2024 Toyota RAV4 AWD options](https://www.fueleconomy.gov/ws/rest/vehicle/menu/options?year=2024&make=Toyota&model=RAV4%20AWD)
- [Vehicle record 47387](https://www.fueleconomy.gov/ws/rest/vehicle/47387)
- [Vehicle record 47388](https://www.fueleconomy.gov/ws/rest/vehicle/47388)

Observed findings:

- The service documents JSON/XML responses, vehicle-detail endpoints, and year/make/model/options menus.
- Bulk CSV/XML downloads are available. The all-years download page listed 1984-2026 at the time of research, with a September 18, 2026 update date; it also listed a preliminary 2027 guide separately.
- Documented fields cover city/highway/combined economy, fuel types, drivetrain, transmission, electricity consumption, range-related measurements, and other attributes.
- The RAV4 AWD options request returned two records: `47387` with a stop-start descriptor and `47388` without that descriptor. Both descriptions included an eight-speed automatic, four cylinders, and 2.5 L displacement.
- The retrieved XML showed `city08` values of 27 and 25, respectively. This demonstrates that year/make/model/AWD alone does not identify one efficiency record. It does not establish a mapping to specific retail trims.
- The documentation notes that certain economy fields represent MPGe for electric and CNG vehicles rather than conventional MPG.
- The all-years dataset includes revised estimates, while individual-year guides are described as reflecting original label estimates.

Potential role: primary structured source for EPA-rated economy and range.

Limitations and follow-up:

- Preserve source IDs and configurations without immediately assigning them to OEM trims.
- Separate fuel economy from odometer mileage, which is outside this project's scope.
- Preserve MPG versus MPGe, fuel type, electric versus total range, test basis, units, and qualifiers. Do not collapse them into one generic mileage field.
- Do not treat every numeric zero or negative sentinel as a real measurement. Interpret fields using source documentation during standardization.
- Keep EPA estimates separate from manufacturer estimates and owner-reported MPG. Owner-reported data is not proposed for the initial pilot.
- Validate EV/PHEV records separately; the live detail spot-check here covered gasoline records only.
- Review usage, redistribution, and attribution requirements before production use; no comprehensive rights review was completed.

### 3.6 IIHS

Sources reviewed:

- [Vehicle ratings](https://www.iihs.org/ratings)
- [2024 Toyota RAV4 ratings](https://www.iihs.org/ratings/vehicle/toyota/rav4-4-door-suv/2024)
- [Copyright information and privacy policy](https://www.iihs.org/copyright-information-and-privacy-policy)

Observed findings:

- IIHS publishes crashworthiness and crash-avoidance evaluations using its own categories and methodology, distinct from NHTSA's ratings.
- The RAV4 page separates original and updated moderate-overlap tests and explicitly states model-year applicability for individual tests.
- The page distinguishes tested vehicles from the wider model-year ranges to which the publisher applies a rating.
- The copyright policy permits limited noncommercial, educational, and personal use under stated conditions. It says commercial copying or redistribution requires written permission and provides `legal@iihs.org` for requests.

Potential role: additional safety evidence if commercial rights and an approved acquisition method are obtained.

Limitations and follow-up:

- Commercial ingestion is permission-gated. Research access does not establish product-use rights.
- No supported public bulk API or commercial feed was verified during this research.
- Preserve test versions, rating scales, award criteria, equipment conditions, and publisher-stated applicability.
- Do not combine IIHS categories and NHTSA stars into an invented universal safety score.

## 4. Why Acquisition Should Precede Standardization

The live examples expose different source structures for the same nominal vehicle:

| Source | Observed representation | Unresolved question |
| --- | --- | --- |
| OEM brochure | Model-year document with trim/equipment content to validate | Can tables, legends, and package notes be extracted accurately? |
| NHTSA NCAP | Separate AWD and FWD reference records | Which retail configurations does each rating cover? |
| FuelEconomy.gov | Multiple powertrain records even within RAV4 AWD | What evidence supports a mapping from each record to retail trims? |
| IIHS | Test-specific results with stated applicability ranges | Which conditions must accompany each published result? |

The acquisition phase should preserve these differences, not resolve them through guessed joins. A source's broader or narrower coverage is valuable evidence for the next design round.

## 5. Phase 1: Raw Acquisition Plan

### 5.1 Confirm the Acquisition Boundary

Decisions required before bulk acquisition:

1. Initial market or markets, including treatment of regional variants.
2. Model-year range and whether upcoming/preliminary years are included.
3. Manufacturers, models, and vehicle classes to prioritize.
4. Initial data domains: features, safety, and efficiency are the stated priorities; dimensions, cargo, towing, charging, warranty, and pricing remain candidates.
5. Whether licensed commercial sources are acceptable when public sources leave material gaps.
6. Budget, legal-review owner, storage environment, and expected refresh frequency.

Do not ask the team to approve a final vehicle ontology or presentation schema at this stage.

### 5.2 Use a Representative Pilot

Recommended starting sample, subject to approval: approximately 12 model-year families across at least three OEMs. A model-year family here is a sampling unit, not a proposed canonical entity.

Select overlapping cases that exercise:

- Gasoline, hybrid, plug-in hybrid, and battery-electric vehicles.
- Multiple trims and drivetrain variants.
- Package-dependent equipment, including heated seats and head-up displays where documented.
- At least one pickup or other vehicle with body/cab/bed-dependent specifications.
- A previous model year and a current or upcoming model year.
- A scanned document and a digitally generated PDF, if relevant to the approved year range.
- Multiple revisions or a mid-year equipment change where discoverable.
- Missing ratings or ambiguous cross-source matches.

The researched RAV4 example is a useful candidate, not an approved mandatory selection. Avoid using one OEM's document format as the basis for the whole pipeline.

### 5.3 Establish Source Access and Rights

For each candidate source, record technical access separately from rights approval. Review permitted automated access, request volume, commercial extraction, storage, redistribution, excerpts, attribution, and any use of third-party extraction services.

Possible dispositions: approved, approval pending, restricted, or rejected. These are acquisition workflow labels, not a legal conclusion. Keep unresolved sources out of bulk ingestion until the relevant review is complete.

Prefer official downloads and documented APIs. Respect access controls, applicable terms, and published operational guidance. Robots directives inform crawler behavior but do not establish licensing permission.

### 5.4 Acquire Originals and Record an Acquisition Manifest

Capture permitted original PDF bytes, API response bodies, bulk download files, and relevant web snapshots. Preserve originals rather than storing only text or an LLM summary.

For dynamic webpages, record what was captured: response HTML, rendered DOM, screenshot, or associated data response. HTML alone may not preserve visible content. Do not collect unrelated assets or personal information.

Minimum recommended acquisition metadata:

| Metadata | Purpose |
| --- | --- |
| Acquisition ID | Stable internal reference for a retrieval event |
| Publisher and hosting source | Distinguish the factual publisher from an archive or distributor |
| Requested and final URL | Retain the retrieval route and redirects |
| Retrieval timestamp and result | Record success, failure, HTTP status, and relevant response headers |
| Media type, byte count, content hash | Validate payloads and identify duplicate or changed artifacts |
| Original artifact location | Locate the permitted retained bytes |
| Source record ID or request parameters | Reproduce an API lookup without inventing a canonical vehicle ID |
| Source-declared title, year, market, make/model/trim text | Aid discovery while retaining original wording and uncertainty |
| Publication date and revision, when present | Distinguish retrieval time from source revision time |
| Rights/access review reference | Track permitted uses and restrictions |
| Acquisition tool/version and run ID | Explain how the artifact was obtained |

Missing metadata remains explicitly unknown. Do not infer market, publication date, or trim applicability solely from a filename. Model year and document publication year are different concepts.

This manifest is operational provenance, not a vehicle standardization schema.

### 5.5 Keep Derivatives Separate

Generate text, OCR, layout data, and table candidates as reproducible derivatives linked to the original artifact and extraction-tool version.

- Keep page boundaries and, where available, coordinates and table geometry.
- Retain legends, footnotes, symbols, and nearby explanatory text.
- Record OCR/extraction failures rather than silently discarding pages.
- Preserve raw API fields and unavailability markers before transformations.
- Label machine-extracted equipment claims as unvalidated candidates, not catalog facts.
- Treat source content as untrusted data. Embedded instructions must not control extraction agents or tools; process PDFs and archives with resource limits and appropriate isolation.

Do not normalize synonyms, map trims across sources, assign safety ratings to trims, or resolve conflicting specifications during this phase.

### 5.6 Validate Acquisition Quality

Checks for the pilot:

- A successful HTTP response actually contains the expected document or data, not an error page.
- Retained bytes reproduce their recorded content hash.
- API payloads parse in their declared format; pagination and bulk-file integrity are accounted for where relevant.
- Originals and derivatives are traceably linked.
- PDF page counts and sampled extracted content agree with the original.
- At least one equipment matrix per sampled document format is manually checked against its rendered page, including headers, legend, and footnotes.
- A repeated retrieval records unchanged content or a new version without overwriting history.
- Failed access, missing documents, and unsupported formats appear in a gap log.

Passing text extraction alone is not sufficient evidence of table correctness.

### 5.7 Preserve Versions and Plan Refreshes

Use content hashes to identify identical artifacts and retain their distinct retrieval events. Keep permitted changed versions instead of overwriting an existing artifact at the same URL.

Refresh schedules should be determined from the pilot and source terms. Current-year documents, rating releases, and revised EPA estimates may change; historical model years are not necessarily immutable. No refresh SLA has been established.

## 6. Phase 1 Deliverables and Exit Criteria

Deliverables:

- Source register with access, coverage, rights status, and acquisition method.
- Approved sample manifest and acquisition results.
- Permitted original corpus with checksums and retrieval provenance.
- Separately versioned extraction derivatives and validation notes.
- Coverage and gap report, including failures and inaccessible sources.
- Measured acquisition/extraction effort and unresolved questions for Phase 2.

Report measurements with clear denominators: attempted versus successful acquisitions, sampled artifacts with complete provenance, extraction success by format, manually inspected table results, and covered versus missing sample targets. Document count alone is not a coverage measure.

Ready for Phase 2 when:

1. The agreed sample is acquired, or missing items have an explicit reason and disposition.
2. Every retained artifact has the required acquisition provenance and an appropriate rights disposition.
3. The sample exposes multiple OEM formats and the agreed powertrain/equipment edge cases.
4. Extraction limits and unresolved source differences are documented with concrete examples.
5. The team can inspect representative originals and derivatives when making standardization decisions.

Do not require a complete production catalog to exit this phase. Conversely, do not describe a pilot corpus as comprehensive market coverage.

## 7. Phase 2: Deferred Standardization Discovery

Questions to answer using the acquired corpus:

- How should model families, retail trims, packages, body variants, powertrains, and regional naming be represented?
- When is year/make/model/trim sufficient for a fact, and what additional applicability conditions are necessary?
- Which source identifiers and explicit evidence support cross-source mappings? How are unresolved mappings retained?
- How should source terminology map to feature concepts without merging different capabilities, such as heated versus ventilated seats?
- How should standard, optional, package-dependent, unavailable, and unknown equipment be distinguished?
- How are feature location and scope retained, such as front versus rear seats?
- How are source units, fuel types, test cycles, manufacturer estimates, and EPA estimates distinguished?
- How are safety methodology versions, tested configurations, and publisher-authorized applicability represented?
- How are conflicting claims, source revisions, and temporal applicability handled without silently choosing a convenient value?
- What evidence is required to support positive, negative, comparative, and aggregate claims?
- What review workflow and quality measures are proportionate to each data domain?

Expected outcome: evidence-based proposals for terminology, mapping rules, provenance requirements, validation, and storage. Final presentation views and catalogs may be included if the discovery supports those decisions; otherwise, defer them.

## 8. Later Agent and Catalog Requirements

These are requirements to preserve, not a finalized architecture:

- Vehicle-fact answers must be traceable to approved evidence with appropriate applicability and revision context.
- Missing data must not become a negative claim. "Not documented" is not "not equipped."
- Optional equipment must not become standard equipment through summarization.
- Ambiguous configuration matches should produce qualification, clarification, or abstention, not guessed facts.
- Retrieval alone is insufficient: later testing must verify that each output claim is supported, correctly scoped, and not supplied from model memory.
- Comparisons and derived values need explicit rules and provenance, not just citations to loosely related documents.

Subsequent decision: local JSON artifacts and Python access methods are selected for v0.1. The accompanying implementation establishes an initial canonical schema; no database, vector index, additional network API, or agent framework is required.

## 9. Research Limits and Recommended Next Step

This research verified source documentation, several live API examples, a Toyota brochure directory, one local PDF text-extraction attempt, and IIHS's published reuse policy. It did not establish cross-OEM completeness, validate a trim-feature extraction pipeline, secure commercial permissions, or benchmark acquisition at scale.

The web reader failed on both attempted PDFs; local extraction worked for the RAV4 PDF only. Toyota pressroom access was blocked, Toyota's substantive legal terms were not successfully extracted, and the general NHTSA ratings webpage was not reliably retrieved. These limitations should remain visible in subsequent planning.

The original research did not retain a raw corpus. Subsequent implementation has now retained six API response artifacts and staged their candidates; see [DATA_STATUS.md](DATA_STATUS.md). Other URLs, observed record IDs, and research notes remain pointers for follow-up, not substitutes for immutable acquisition evidence. Live pages and responses may change.

Next step: confirm the acquisition boundary and representative sample, then complete source-access/rights review and perform a bounded raw-acquisition pilot. Use its findings to begin the separate standardization discovery and design round.