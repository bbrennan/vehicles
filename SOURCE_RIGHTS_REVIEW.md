# Source Rights Review

Reviewed: 2026-09-22. Preliminary engineering due diligence, not a legal opinion or provider permission. Applicable licenses, contracts, statutory rights, and jurisdiction should be assessed by qualified counsel before commercial deployment.

## Toyota and Lexus Project Assumption

On 2026-09-22, the user instructed: "You can assume any ToS for Toyota and Lexus are satisfied." Treat Toyota and Lexus terms of service as satisfied for the intended project use. This is a user-supplied project assumption, not independently verified contract evidence. No additional Toyota/Lexus ToS outreach is required to proceed with otherwise eligible first-party sources.

This does not satisfy terms imposed by third-party hosts or data providers, including Auto-Brochures.com, FuelEconomy.gov, Honda, or IIHS. Legacy archive sources remain held; their acquired samples were deleted by the user. Factual identity, applicability and publication checks still apply. US Toyota acquisition has resumed by user authorization for MY2015 onward, including published 2027 and general/accessory brochures. Lexus, model training and separate marketing-image reuse are not added.

The owner subsequently explicitly authorized public GitHub delivery of the original PDFs, optionally zipped, while prohibiting extracted JSON uploads. Delivery uses a PDF-only Release ZIP; extracted text/layout and acquisition manifests also stay local. This supersedes the earlier code/docs-only delivery choice and relies on the same owner-supplied Toyota ToS assumption, not an independently verified license or a new license to downstream users. Historical manifests and their publication flags remain unchanged; this corpus-sharing decision does not approve curated facts for shopper use.

## Public Access Is Not Public Domain

A publicly downloadable brochure may still contain copyrighted text, photographs, artwork, and layout. Downloading it, retaining an internal copy, extracting factual attributes, displaying excerpts, redistributing the PDF, and training a model are different uses and may have different legal bases and contractual restrictions.

In the US, facts generally are not protected by copyright in themselves. That does not settle permitted acquisition, copying of expression or compilations, contractual restrictions, or rights in Canada and Mexico. A fact-only catalog can reduce some copyright concerns but is not an automatic exemption from all source terms.

Likewise, an API can be deliberately public and free to access while retaining operational restrictions or limitations on particular content. Government-hosted material can include contractor-created and third-party works; do not assume every file on a government domain is public domain.

Project authorization to proceed is not a license from the content owner. Earlier acquisition notes recorded project authorization, not established commercial rights. A local catalog or internal prototype for a commercial product should not automatically be characterized as noncommercial or personal use.

## Findings by Source

| Source | Observed terms | Current project disposition |
| --- | --- | --- |
| NHTSA | Its Terms of Use says information presented on the site is public information and may be distributed or copied. It also disclaims third-party noninfringement warranties and prohibits misuse of the system. | Stronger basis for bounded public-information acquisition. Existing NHTSA acquisition flags remain enabled; publication remains disabled pending normal review of the actual dataset/content and use. |
| FuelEconomy.gov / ORNL | Copyright notice describes contractor-sponsored documents and expressly permits noncommercial, scientific, and educational distribution/use. Vehicle photos are separately owned. The API page supplies downloads and endpoint documentation, but the reviewed text does not establish an explicit commercial license for our intended use. | Further EPA detail acquisition and discovery are paused. Ask whether the document notice applies to API/bulk factual records and obtain a documented basis for commercial catalog use. This is an unresolved scope question, not a conclusion that all EPA facts are copyrighted or unusable. |
| Honda websites covered by its terms | Terms limit the express download permission to personal noncommercial home use. They prohibit systematic retrieval to compile a database without written permission and contain restrictions on crawling/scraping and redistribution. | Do not automate collection from covered Honda sites for this catalog without the necessary authorization or reviewed legal basis. The archive-hosted brochure's access contract and underlying content rights must be evaluated separately. |
| Toyota and Lexus | User instructed on 2026-09-22 to assume their ToS are satisfied. Toyota legal terms were not independently retrieved; no independent Lexus terms review is claimed. | Accept the user-supplied ToS assumption for intended project use. First-party sources need no further OEM ToS clearance. The existing archive-hosted Toyota source remains held for separate host review; Lexus remains outside the current acquisition scope. |
| Auto-Brochures.com | About page describes an archive of mainly US brochures. No explicit license for commercial catalog creation was established. A robots.txt attempt produced a missing-page response; this is not permission. | Archive hosting does not establish authority to sublicense OEM content. Both brochure sources are on hold. |
| IIHS | Published policy requires written permission for commercial copying or redistribution and certain repeated noncommercial uses. | Permission-gated. No ingestion or publication approval. |

### Primary References

- [NHTSA Terms of Use, Ownership and liability sections](https://www.nhtsa.gov/about-nhtsa/terms-use)
- [NHTSA datasets and APIs](https://www.nhtsa.gov/nhtsa-datasets-and-apis)
- [FuelEconomy.gov copyright/security notice](https://www.fueleconomy.gov/feg/ORNL-disclaimer.htm)
- [FuelEconomy.gov web services](https://www.fueleconomy.gov/feg/ws/)
- [FuelEconomy.gov contacts](https://www.fueleconomy.gov/feg/contacts.shtml)
- [American Honda Terms and Conditions](https://www.honda.com/privacy/terms-and-conditions), especially Applicability, American Honda's Intellectual Property, and User Restrictions. Page states last updated February 20, 2025.
- [Toyota legal-terms URL attempted](https://www.toyota.com/support/legal-terms/); substantive content not successfully retrieved.
- [Auto-Brochures.com About](https://www.auto-brochures.com/_about.html)
- [IIHS copyright policy](https://www.iihs.org/copyright-information-and-privacy-policy)

These are reviewed live references, not immutable snapshots of the terms. Before approving a source, retain a dated policy/permission record with the applicable version, content hash where appropriate, reviewer, and use scope. Do not treat US website terms as automatically governing Canadian or Mexican publishers, or assume those markets grant identical rights.

## Current Controls and Existing Data

- [config/documents.json](config/documents.json): both brochure acquisition flags remain false; publication remains false. Toyota ToS are assumed satisfied, but its configured archive host remains unresolved. Honda's hold is unchanged.
- [config/sources.json](config/sources.json): all four EPA acquisition flags are now false; two NHTSA flags remain true. All publication flags remain false.
- [config/toyota-documents.json](config/toyota-documents.json) and [config/toyota-reference-documents.json](config/toyota-reference-documents.json): acquisition flags true, publication false. The US Toyota collector uses the same user authorization and preserves publication false in every manifest.
- The EPA discovery CLI checks the source registry before requesting menus. The document and detail-fetch commands already check acquisition flags.
- The user deleted historical mixed-make run folders on 2026-09-22. Their raw/staged artifacts are no longer present locally and have not been restored; this does not establish the disposition of external backups.
- Remaining runs contain first-party Toyota documents, not the deleted archive samples. No release has been published. Do not reacquire or process held sources without resolving their separate restrictions.
- Current controls are operator workflow checks, not a tamper-proof authorization system. Trusted callers can invoke lower-level functions, and historical manifests preserve earlier flags. Before production, current rights decisions must govern processing and publication independently of old acquisition snapshots.

Deleted runs previously contained six detailed API records, 27 EPA discovery snapshots, and two archive-hosted brochures. Those historical counts are not available evidence. [DATA_STATUS.md](DATA_STATUS.md) records current first-party Toyota totals and gaps.

## Approval Checklist

Record decisions separately for each source and content class:

1. Automated access: permitted endpoints/documents, rate limits, caching, and refresh rules.
2. Storage and processing: retention of originals, OCR/extraction, derived factual data, and use of external processing vendors.
3. Product use: internal reference catalog and customer-facing factual answers in a commercial shopping agent.
4. Distribution: shipping JSON to agent deployments, dealer/partner access, excerpts/citations, and full-document redistribution.
5. Conditions: attribution, disclaimers, trademarks, nonendorsement, geography, sublicensing, expiry, and deletion obligations.
6. Evidence: applicable terms or written permission, reviewer/owner, review date, and next review trigger. Approval may rest on an applicable license or counsel-reviewed legal basis; written permission is not asserted to be universally required for facts.

Review brochure photos/art separately from extracted specifications. The proposed product does not need to reproduce OEM marketing copy or images to answer factual shopping questions. Attribution and provenance help auditing but do not themselves supply permission.

## Provider Questions

FuelEconomy.gov lists `fueleconomy@ornl.gov` for questions. IIHS lists `legal@iihs.org` for content-use requests. Use established licensing contacts for Honda. Toyota/Lexus ToS outreach is not required under the user-supplied assumption above; third-party host questions remain separate.

Suggested request, to be tailored and sent by the project owner:

> We are building a commercial vehicle-shopping research system. We would like to retrieve specified vehicle reference data, retain original evidence privately, normalize factual attributes into versioned JSON, and serve factual answers through software used by dealership shoppers. We do not propose model training, public redistribution of original brochures, or reproduction of marketing images. Please confirm the applicable terms or permission for automated retrieval, internal storage/extraction, distribution of the derived factual catalog to our deployments, and customer-facing use. Please identify any attribution, rate, territorial, retention, or other restrictions. For FuelEconomy.gov, does the posted document copyright notice apply to structured API and bulk vehicle records, and what is the basis for commercial reuse of those records?

No permission requests have been sent. Resume held acquisition only after the relevant use has a documented basis; select licensed alternatives if a source cannot support it.