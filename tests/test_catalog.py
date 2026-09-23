import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from vehicle_catalog.batch import Pilot, run, verify_identity
from vehicle_catalog.discovery import (
    menu_items,
    require_epa_access,
    run_discovery,
)
from vehicle_catalog.documents import (
    DocumentPlan,
    DocumentTarget,
    ReferenceDocumentTarget,
    link_pdf,
    reextract_documents,
    run_documents,
    split_pages,
)
from vehicle_catalog.models import (
    Artifact,
    Catalog,
    FeatureFact,
    MeasurementFact,
    RatingFact,
    Source,
    Sources,
)
from vehicle_catalog.pipeline import (
    build,
    digest,
    encode,
    extract,
    fetch,
    transform,
    write_once,
)
from vehicle_catalog.reader import LocalCatalog

EVIDENCE = [
    {
        "artifact_id": "fixture",
        "locator": "page:1",
        "source_record_id": "fixture",
        "original_value": "Synthetic test evidence, not vehicle data",
    }
]


class DiscoveryTests(unittest.TestCase):
    def test_offline_document_extraction(self):
        source = Source(
            id="toyota-test",
            publisher="Synthetic",
            adapter="document",
            url="https://example.com/test.pdf",
            market="US",
            acquisition_approved=True,
            rights_reference="Synthetic test",
        )
        target = DocumentTarget(
            source=source, make="Toyota", model="Camry", year=2025
        )
        plan = DocumentPlan(documents=[target])
        pilot = Pilot(
            makes=["Toyota"],
            markets=["US"],
            minimum_year=2015,
            targets=[
                {
                    "source_id": source.id,
                    "make": "Toyota",
                    "model": "Camry",
                    "year": 2025,
                }
            ],
        )
        payload = b"%PDF-1.7\nSynthetic"
        artifact = Artifact(
            id="offline-fixture",
            source=source,
            retrieved_at=datetime.now(timezone.utc),
            final_url=source.url,
            media_type="application/pdf",
            sha256=digest(payload),
            byte_count=len(payload),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw/test"
            write_once(
                raw / "fixture.json", encode(artifact.model_dump(mode="json"))
            )
            write_once(raw / f"{artifact.sha256}.blob", payload)
            before = {path.name: path.read_bytes() for path in raw.iterdir()}
            out = root / "staged/offline"
            with (
                patch("vehicle_catalog.documents.fetch") as retrieve,
                patch(
                    "vehicle_catalog.documents.extract_pdf",
                    return_value={"page_count": 1},
                ) as extract_document,
            ):
                report = reextract_documents(plan, pilot, raw, out)
                self.assertEqual(report["extracted"], 1)
                self.assertEqual(report["published_facts"], 0)
                extract_document.assert_called_once()
                retrieve.assert_not_called()
                with self.assertRaisesRegex(ValueError, "already exists"):
                    reextract_documents(plan, pilot, raw, out)
                with self.assertRaisesRegex(ValueError, "outside raw"):
                    reextract_documents(plan, pilot, raw, raw / "derived")
                denied = target.model_copy(
                    update={
                        "source": source.model_copy(
                            update={"acquisition_approved": False}
                        )
                    }
                )
                blocked = root / "staged/blocked"
                with self.assertRaisesRegex(ValueError, "not approved"):
                    reextract_documents(
                        DocumentPlan(documents=[denied]), pilot, raw, blocked
                    )
                mismatch = target.model_copy(
                    update={
                        "source": source.model_copy(
                            update={"url": "https://example.com/other.pdf"}
                        )
                    }
                )
                with self.assertRaisesRegex(ValueError, "does not match"):
                    reextract_documents(
                        DocumentPlan(documents=[mismatch]),
                        pilot,
                        raw,
                        blocked,
                    )
                self.assertFalse(blocked.exists())
                self.assertEqual(extract_document.call_count, 1)
            with patch(
                "vehicle_catalog.documents.extract_pdf",
                side_effect=ValueError("synthetic failure"),
            ):
                report = reextract_documents(
                    plan, pilot, raw, root / "staged/failure"
                )
                self.assertEqual(report["extracted"], 0)
                self.assertIn(
                    "synthetic failure", report["results"][0]["error"]
                )
            self.assertEqual(
                before,
                {path.name: path.read_bytes() for path in raw.iterdir()},
            )

    def test_readable_pdf_links(self):
        payload = b"%PDF-1.7\nsynthetic fixture"
        artifact = Artifact(
            id="pdf-test",
            source=Source(
                id="Toyota-US-Camry-2025",
                publisher="Synthetic",
                adapter="document",
                url="https://example.com/test.pdf",
                market="US",
                rights_reference="Synthetic test",
            ),
            retrieved_at=datetime.now(timezone.utc),
            final_url="https://example.com/test.pdf",
            media_type="application/pdf",
            sha256=digest(payload),
            byte_count=len(payload),
        )
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory)
            original = raw / f"{artifact.sha256}.blob"
            write_once(original, payload)
            path = link_pdf(artifact, raw)
            self.assertEqual(path.name, "toyota-us-camry-2025.pdf")
            self.assertTrue(path.is_symlink())
            self.assertFalse(path.readlink().is_absolute())
            self.assertEqual(path.read_bytes(), payload)
            self.assertEqual(link_pdf(artifact, raw), path)
            other_payload = b"%PDF-1.7\ndifferent fixture"
            other = artifact.model_copy(
                update={
                    "sha256": digest(other_payload),
                    "byte_count": len(other_payload),
                }
            )
            write_once(raw / f"{other.sha256}.blob", other_payload)
            with self.assertRaisesRegex(ValueError, "refusing"):
                link_pdf(other, raw)
            self.assertEqual(path.read_bytes(), payload)
            unsafe = artifact.model_copy(
                update={
                    "source": artifact.source.model_copy(
                        update={"id": "../../Toyota/Reference"}
                    )
                }
            )
            safe_path = link_pdf(unsafe, raw)
            self.assertEqual(safe_path.parent, raw / "pdfs")
            self.assertEqual(safe_path.name, "toyota-reference.pdf")
            invalid_payload = b"not a PDF"
            invalid = artifact.model_copy(
                update={
                    "sha256": digest(invalid_payload),
                    "byte_count": len(invalid_payload),
                }
            )
            write_once(raw / f"{invalid.sha256}.blob", invalid_payload)
            with self.assertRaisesRegex(ValueError, "integrity"):
                link_pdf(invalid, raw)
            with self.assertRaisesRegex(ValueError, "integrity"):
                link_pdf(artifact.model_copy(update={"byte_count": 1}), raw)

    def test_reference_document_identity_and_scope(self):
        source = Source(
            id="reference",
            publisher="Synthetic",
            adapter="document",
            url="https://example.com/reference.pdf",
            market="US",
            acquisition_approved=True,
            rights_reference="Synthetic test",
        )
        reference = ReferenceDocumentTarget(
            kind="reference",
            source=source,
            make="Toyota",
            title="Safety system",
            topic="safety",
            version="3.0",
        )
        plan = DocumentPlan.model_validate(
            {"documents": [reference.model_dump()]}
        )
        self.assertIsInstance(plan.documents[0], ReferenceDocumentTarget)
        for field, value in (("year", 2026), ("model", "All")):
            with self.assertRaises(ValidationError):
                ReferenceDocumentTarget.model_validate(
                    {**reference.model_dump(), field: value}
                )
        with self.assertRaises(ValidationError):
            DocumentTarget(source=source, make="Toyota")
        pilot = Pilot(
            makes=["Toyota"],
            markets=["US"],
            minimum_year=2015,
            targets=[
                {
                    "source_id": "reference",
                    "make": "Toyota",
                    "model": "Camry",
                    "year": 2025,
                }
            ],
        )
        invalid_targets = [
            reference.model_copy(update={"make": "Honda"}),
            reference.model_copy(
                update={"source": source.model_copy(update={"market": "CA"})}
            ),
            reference.model_copy(
                update={
                    "source": source.model_copy(
                        update={"acquisition_approved": False}
                    )
                }
            ),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("vehicle_catalog.documents.fetch") as retrieve:
                for target in invalid_targets:
                    with self.assertRaises(ValueError):
                        run_documents(
                            DocumentPlan(documents=[target]),
                            pilot,
                            root,
                            "blocked",
                        )
                retrieve.assert_not_called()
                self.assertFalse((root / "raw").exists())
                retrieve.return_value.id = "synthetic-reference"
                with (
                    patch(
                        "vehicle_catalog.documents.extract_pdf",
                        return_value={"page_count": 2},
                    ),
                    patch(
                        "vehicle_catalog.documents.link_pdf",
                        return_value=root / "raw/reference/pdfs/reference.pdf",
                    ),
                ):
                    report = run_documents(plan, pilot, root, "reference")
                self.assertEqual(report["extracted"], 1)
                self.assertEqual(report["published_facts"], 0)
                result = report["results"][0]
                self.assertNotIn("year", result["declared_scope"])
                self.assertEqual(result["applicability_review"], "pending")
                self.assertEqual(result["pdf_path"], "pdfs/reference.pdf")

    def test_discovery_requires_source_approval(self):
        source = Source(
            id="test-epa",
            publisher="Synthetic",
            adapter="epa",
            url="https://www.fueleconomy.gov/ws/rest/vehicle/1",
            market="US",
            rights_reference="Synthetic test; not a permission grant",
        )
        with self.assertRaisesRegex(ValueError, "on hold"):
            require_epa_access(Sources(sources=[source]))
        with self.assertRaisesRegex(ValueError, "on hold"):
            require_epa_access(Sources(sources=[]))
        approved = source.model_copy(update={"acquisition_approved": True})
        require_epa_access(Sources(sources=[approved]))

    def test_pdf_page_boundaries_and_blank_pages(self):
        pages = split_pages("First\f\fThird\f", 3)
        self.assertTrue(pages[1]["blank_text"])
        self.assertEqual(pages[2]["physical_page"], 3)
        with self.assertRaisesRegex(ValueError, "boundaries"):
            split_pages("Only one page\f", 2)
        with self.assertRaisesRegex(ValueError, "OCR"):
            split_pages("\f\f", 2)

    def test_document_scope_rejected_before_network(self):
        pilot = Pilot(
            makes=["Honda"],
            markets=["US"],
            minimum_year=2015,
            targets=[
                {
                    "source_id": "test",
                    "make": "Honda",
                    "model": "CR-V",
                    "year": 2018,
                }
            ],
        )
        target = DocumentTarget(
            make="Honda",
            model="CR-V",
            year=2014,
            source=Source(
                id="test",
                publisher="Synthetic",
                adapter="document",
                url="https://example.com/test.pdf",
                market="US",
                acquisition_approved=True,
                rights_reference="Synthetic test",
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            with patch("vehicle_catalog.documents.fetch") as retrieve:
                with self.assertRaisesRegex(ValueError, "outside"):
                    run_documents(
                        DocumentPlan(documents=[target]),
                        pilot,
                        Path(directory),
                        "test",
                    )
                retrieve.assert_not_called()

    def test_menu_shapes_and_invalid_values(self):
        item = {"text": "Civic", "value": "Civic"}
        self.assertEqual(menu_items({"menuItem": item}), [item])
        self.assertEqual(menu_items({"menuItem": []}), [])
        with self.assertRaisesRegex(ValueError, "unrecognized"):
            menu_items({"error": "unavailable"})
        with self.assertRaisesRegex(ValueError, "duplicate"):
            menu_items({"menuItem": [item, item]})

    def test_discovery_respects_floor_and_preserves_failures(self):
        pilot = Pilot(
            makes=["Toyota", "Honda"],
            markets=["US", "CA", "MX"],
            minimum_year=2015,
            targets=[
                {
                    "source_id": "test",
                    "make": "Honda",
                    "model": "Fit",
                    "year": 2015,
                }
            ],
        )
        requested = []

        def capture(raw, menu, **parameters):
            requested.append((menu, parameters))
            if menu == "year":
                return {"id": "years"}, [
                    {"text": str(year), "value": str(year)}
                    for year in (2014, 2015, 2016)
                ]
            if parameters == {"year": 2016, "make": "Honda"}:
                raise OSError("synthetic outage")
            return {"id": str(parameters)}, [{"text": "Fit", "value": "Fit"}]

        with tempfile.TemporaryDirectory() as directory:
            with patch(
                "vehicle_catalog.discovery.capture_menu", side_effect=capture
            ):
                result = run_discovery(pilot, Path(directory), "test", 2016)
            self.assertEqual(result["failed_queries"], 1)
            self.assertEqual(result["source_model_year_rows"], 3)
            self.assertEqual(result["unacquired_markets"], ["CA", "MX"])
            self.assertTrue(all(row["year"] >= 2015 for row in result["rows"]))
            self.assertEqual(len(requested), 5)
            self.assertTrue(
                (Path(directory) / "staged/test/coverage.json").exists()
            )


class SchemaTests(unittest.TestCase):
    def test_package_requires_package_code(self):
        with self.assertRaises(ValidationError):
            FeatureFact(
                id="test",
                kind="feature",
                feature="head_up_display",
                availability="package",
                evidence=EVIDENCE,
            )

    def test_unit_must_match_metric(self):
        with self.assertRaises(ValidationError):
            MeasurementFact(
                id="test",
                kind="measurement",
                metric="electric_range",
                value=300.0,
                unit="mpg_us",
                basis="EPA",
                evidence=EVIDENCE,
            )

    def test_not_rated_is_not_a_star_value(self):
        with self.assertRaises(ValidationError):
            RatingFact(
                id="test",
                kind="rating",
                agency="NHTSA",
                test="overall",
                methodology="NCAP",
                scale="stars_1_5",
                value="Not Rated",
                published_applicability="Synthetic",
                evidence=EVIDENCE,
            )


class PipelineTests(unittest.TestCase):
    def pilot(self):
        return Pilot(
            makes=["Example"],
            markets=["US", "CA", "MX"],
            minimum_year=2015,
            targets=[
                {
                    "source_id": "synthetic",
                    "make": "Example",
                    "model": "Sample",
                    "year": 2024,
                }
            ],
        )

    def test_pilot_year_floor_and_discontinued_policy(self):
        pilot = self.pilot()
        self.assertFalse(pilot.eligible("Example", 2014, "US"))
        self.assertTrue(pilot.eligible("Example", 2015, "US"))
        self.assertTrue(pilot.eligible("Example", 2018, "MX"))
        self.assertFalse(pilot.eligible("Other", 2024, "US"))
        self.assertFalse(pilot.eligible("Example", 2024, "GB"))

    def test_pilot_verifies_returned_identity(self):
        pilot = self.pilot()
        verify_identity(pilot, pilot.targets[0], self.artifact, self.payload)
        pilot.targets[0].model = "Different"
        with self.assertRaisesRegex(ValueError, "differs"):
            verify_identity(
                pilot, pilot.targets[0], self.artifact, self.payload
            )

    def test_pilot_records_failure_and_continues(self):
        pilot = self.pilot()
        pilot.targets.append(
            pilot.targets[0].model_copy(
                update={
                    "source_id": "second",
                }
            )
        )
        second = self.source.model_copy(update={"id": "second"})

        def retrieve(source, raw):
            if source.id == "synthetic":
                raise OSError("synthetic connection failure")
            write_once(raw / f"{self.artifact.sha256}.blob", self.payload)
            return self.artifact

        with patch("vehicle_catalog.batch.fetch", side_effect=retrieve):
            report = run(
                pilot,
                Sources(sources=[self.source, second]),
                self.root / "batch",
                "test-run",
            )
        self.assertEqual(report["acquired"], 1)
        self.assertEqual(report["staged"], 1)
        self.assertEqual(report["candidate_count"], 3)
        self.assertEqual(report["results"][0]["acquisition"], "failed")
        for layer in ("raw", "staged", "curated", "releases"):
            self.assertTrue((self.root / "batch" / layer).is_dir())

    def test_pilot_rejects_reused_run_and_missing_approval(self):
        root = self.root / "existing"
        (root / "raw" / "first").mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "already exists"):
            run(self.pilot(), Sources(sources=[self.source]), root, "first")
        source = self.source.model_copy(update={"acquisition_approved": False})
        with patch("vehicle_catalog.batch.fetch") as retrieve:
            with self.assertRaisesRegex(ValueError, "not approved"):
                run(self.pilot(), Sources(sources=[source]), root, "second")
            retrieve.assert_not_called()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.raw = self.root / "raw"
        self.source = Source(
            id="synthetic",
            publisher="Synthetic fixture",
            adapter="epa",
            market="US",
            url="https://www.fueleconomy.gov/ws/rest/vehicle/1",
            acquisition_approved=True,
            publication_approved=True,
            rights_reference="Synthetic tests only; not real vehicle evidence",
        )
        self.payload = encode(
            {
                "id": "1",
                "make": "Example",
                "model": "Sample",
                "year": 2024,
                "fuelType1": "Regular Gasoline",
                "city08": 25,
                "highway08": 30,
                "comb08": 27,
            }
        )
        self.artifact = Artifact(
            id="fixture",
            source=self.source,
            retrieved_at=datetime.now(timezone.utc),
            final_url=self.source.url,
            media_type="application/json",
            sha256=digest(self.payload),
            byte_count=len(self.payload),
        )
        self.persist_artifact()
        self.evidence = [
            {
                "artifact_id": "fixture",
                "locator": "/id",
                "source_record_id": "1",
                "original_value": "1",
            }
        ]
        self.review = {
            "reviewer": "test-reviewer",
            "reviewed_on": "2026-09-22",
            "rationale": "Synthetic mapping for test only",
            "evidence": self.evidence,
        }
        self.plan = {
            "release_id": "test-only",
            "configurations": [
                {
                    "id": "sample",
                    "market": "US",
                    "year": 2024,
                    "make": "Example",
                    "model": "Sample",
                    "trim": "Example Trim",
                    "evidence": self.evidence,
                }
            ],
            "assignments": [],
            "reviewed_facts": [],
            "feature_vocabulary": {"head_up_display": "Head-up display"},
            "coverage_notes": [
                "Synthetic partial test catalog, not vehicle facts"
            ],
        }
        self.plan_path = self.root / "mapping.json"

    def persist_artifact(self):
        write_once(self.raw / f"{self.artifact.sha256}.blob", self.payload)
        write_once(
            self.raw / "fixture.json",
            encode(self.artifact.model_dump(mode="json")),
        )

    def publish(self):
        self.plan_path.write_bytes(encode(self.plan))
        return build(self.raw, self.plan_path)

    def add_feature(self, availability="standard", conditions=None):
        self.plan["reviewed_facts"].append(
            {
                "configuration_id": "sample",
                "review": self.review,
                "fact": {
                    "id": "hud",
                    "kind": "feature",
                    "feature": "head_up_display",
                    "availability": availability,
                    "conditions": conditions or {},
                    "evidence": self.evidence,
                },
            }
        )

    def reader(self, catalog):
        path = self.root / "catalog.json"
        write_once(path, encode(catalog.model_dump(mode="json")))
        return LocalCatalog(path)

    def test_transform_never_assigns_a_trim(self):
        transformed = transform(self.raw)
        self.assertEqual(len(transformed.candidates), 3)
        self.assertNotIn("trim", transformed.candidates[0].source_identity)
        self.assertEqual(self.publish().records[0].facts, [])

    def test_reviewed_mapping_builds_a_local_catalog(self):
        self.plan["assignments"] = [
            {
                "candidate_id": "fixture:comb08",
                "configuration_id": "sample",
                "review": self.review,
            }
        ]
        catalog = self.publish()
        self.assertEqual(catalog.records[0].facts[0].value, 27)
        self.assertEqual(
            catalog.mapping_plan_sha256, digest(self.plan_path.read_bytes())
        )
        reader = self.reader(catalog)
        self.assertEqual(
            reader.trims(
                market="US", year=2024, make="example", model="sample"
            )["trims"],
            ["Example Trim"],
        )
        self.assertEqual(reader.get("missing")["status"], "unknown")
        self.assertIn("partial", reader.get("sample")["coverage"])

    def test_missing_review_is_rejected(self):
        self.plan["assignments"] = [
            {"candidate_id": "fixture:comb08", "configuration_id": "sample"}
        ]
        with self.assertRaises(ValidationError):
            self.publish()

    def test_cross_market_and_cross_year_mapping_rejected(self):
        self.plan["assignments"] = [
            {
                "candidate_id": "fixture:comb08",
                "configuration_id": "sample",
                "review": self.review,
            }
        ]
        self.plan["configurations"][0]["market"] = "CA"
        with self.assertRaisesRegex(ValueError, "cross-market"):
            self.publish()
        self.plan["configurations"][0]["market"] = "US"
        self.plan["configurations"][0]["year"] = 2025
        with self.assertRaisesRegex(ValueError, "cross-year"):
            self.publish()

    def test_tampered_blob_rejected(self):
        (self.raw / f"{self.artifact.sha256}.blob").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "integrity"):
            transform(self.raw)

    def test_source_approval_checked_before_network(self):
        source = self.source.model_copy(update={"acquisition_approved": False})
        with patch("vehicle_catalog.pipeline.build_opener") as opener:
            with self.assertRaisesRegex(ValueError, "not approved"):
                fetch(source, self.raw)
            opener.assert_not_called()

    def test_publication_requires_approval(self):
        catalog = self.publish().model_dump(mode="json")
        catalog["artifacts"][0]["source"]["publication_approved"] = False
        with self.assertRaisesRegex(ValidationError, "approval"):
            Catalog.model_validate(catalog)

    def test_package_feature_not_returned_as_standard(self):
        self.add_feature("package", {"package_codes": ["TEST"]})
        reader = self.reader(self.publish())
        self.assertEqual(
            reader.with_feature("head_up_display", market="US", year=2024)[
                "matches"
            ],
            [],
        )
        available = reader.with_feature(
            "head_up_display", market="US", year=2024, mode="available"
        )
        self.assertEqual(
            available["matches"][0]["fact"]["conditions"]["package_codes"],
            ["TEST"],
        )

    def test_conditional_standard_is_not_universal(self):
        self.add_feature("standard", {"regions": ["Test Region"]})
        reader = self.reader(self.publish())
        self.assertEqual(
            reader.with_feature("head_up_display", market="US", year=2024)[
                "matches"
            ],
            [],
        )

    def test_conflicting_feature_claims_block_publication(self):
        self.add_feature()
        self.add_feature("unavailable")
        self.plan["reviewed_facts"][1]["fact"]["id"] = "other-hud"
        with self.assertRaisesRegex(ValueError, "conflicting"):
            self.publish()

    def test_compare_preserves_unknown_values(self):
        other = dict(
            self.plan["configurations"][0], id="other", trim="Other Trim"
        )
        self.plan["configurations"].append(other)
        self.add_feature()
        comparison = self.reader(self.publish()).compare(["sample", "other"])
        self.assertIsNone(comparison["rows"][0]["values"]["other"])

    def test_immutable_outputs(self):
        path = self.root / "immutable.json"
        write_once(path, b"one")
        write_once(path, b"one")
        with self.assertRaisesRegex(ValueError, "overwrite"):
            write_once(path, b"two")
        self.assertEqual(path.read_bytes(), b"one")

    def test_epa_electric_units_and_sentinels(self):
        data = json.loads(self.payload)
        data.update(
            fuelType1="Electricity",
            range=300,
            combE=28,
            city08=0,
            highway08=-1,
        )
        candidates = extract(self.artifact, encode(data))
        self.assertEqual(
            {candidate.fact.metric for candidate in candidates},
            {
                "fuel_economy_combined",
                "electric_range",
                "electricity_consumption_combined",
            },
        )
        self.assertEqual(candidates[0].fact.unit, "mpge_us")

    def test_phev_is_not_silently_mapped_as_gasoline(self):
        data = json.loads(self.payload)
        data["fuelType2"] = "Electricity"
        with self.assertRaisesRegex(ValueError, "PHEV"):
            extract(self.artifact, encode(data))

    def test_response_identity_must_match_url(self):
        data = json.loads(self.payload)
        data["id"] = "999"
        with self.assertRaisesRegex(ValueError, "record ID"):
            extract(self.artifact, encode(data))

    def test_nhtsa_unrated_fields_stay_absent(self):
        source = self.source.model_copy(
            update={
                "adapter": "nhtsa",
                "url": "https://api.nhtsa.gov/SafetyRatings/VehicleId/1",
            }
        )
        artifact = self.artifact.model_copy(update={"source": source})
        payload = encode(
            {
                "Results": [
                    {
                        "VehicleId": 1,
                        "Make": "Example",
                        "Model": "Sample",
                        "ModelYear": 2024,
                        "VehicleDescription": "Synthetic AWD",
                        "OverallRating": "5",
                        "RolloverRating": "Not Rated",
                    }
                ]
            }
        )
        candidates = extract(artifact, payload)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].fact.value, "5")


if __name__ == "__main__":
    unittest.main()
