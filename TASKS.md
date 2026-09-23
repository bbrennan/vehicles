# Toyota Retrieval Tasks

Updated 2026-09-22. Acquisition resumed by user request. Scope: US Toyota brochures for MY2015 onward, including already-published 2027 editions and general/accessory brochures. Canada/Mexico are deferred, not implicitly covered. Public GitHub delivery includes docs, scripts, tests and schemas; raw PDFs, extracted text, local environments and private data are excluded.

- [x] Confirm US-first scope and public repository contents with project owner.
- [x] Define the end-state curated schema and raw-to-curated mapping contract in PRD/ARD.
- [x] Prepare repository README, ignore rules and reproducible setup.
- [x] Implement bounded first-party brochure inventory/download with per-URL outcomes, provenance, and historical coverage gaps.
- [x] Run first collection pass: 490 URLs attempted, 130 PDFs acquired, 129 text-extracted; distinguish official links from unverified candidates.
- [ ] Complete historical coverage: resolve 2015-2019 sources, alternate filenames, 11 redirects, two accessory size/empty failures, and the independent model/year/document denominator.
- [x] Provide offline raw extraction with page text and table-layout evidence, without presenting unreviewed extraction as curated facts.
- [x] Run tests and real-PDF extraction checks: 36 tests/lint pass; 130 layout outputs; original hashes verified; gaps in DATA_STATUS.md.
- [x] Commit and push reviewed project files to https://github.com/bbrennan/vehicles; initial commit `7ef753f` verified against remote `main`. Raw/staged data excluded.

## Completion Rules

“All” remains a coverage objective until a reviewed US model/year/document register has no unresolved gaps. A missing URL does not prove no brochure exists or no vehicle was offered. Current website links do not establish historical completeness. General brochures without an evidenced publication date are retained as current references, not assigned a guessed model year.

No held EPA, Honda, IIHS or third-party archive source is enabled by this task. No deleted mixed-make run is restored. PDF/table outputs stay unreviewed until identity, columns, legends, footnotes and applicability are checked. Current-state code and proposed schema extensions must be labeled separately.