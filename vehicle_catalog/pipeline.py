import hashlib
import json
import math
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from vehicle_catalog.models import (
    Artifact,
    Candidate,
    Candidates,
    Catalog,
    Evidence,
    MappingPlan,
    MeasurementFact,
    RatingFact,
    Record,
    Source,
    Sources,
)

MAX_BYTES = 20 * 1024 * 1024


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def encode(value) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode()


def write_once(path: Path, payload: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=path.parent, delete=False
    ) as temporary:
        temporary.write(payload)
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    try:
        try:
            os.link(temporary_path, path)
        except FileExistsError:
            if path.read_bytes() != payload:
                raise ValueError(f"refusing to overwrite {path}")
    finally:
        temporary_path.unlink()


def validate_url(source: Source):
    parsed = urlparse(source.url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError("source URL must use HTTPS without credentials")
    if parsed.port not in {None, 443} or parsed.fragment:
        raise ValueError("nonstandard ports and fragments are unsupported")
    if source.adapter == "epa":
        if parsed.hostname != "www.fueleconomy.gov" or not re.fullmatch(
            r"/ws/rest/vehicle/\d+", parsed.path
        ):
            raise ValueError(
                "EPA adapter requires an official vehicle-detail endpoint"
            )
    if source.adapter == "nhtsa":
        if parsed.hostname != "api.nhtsa.gov" or not re.fullmatch(
            r"/SafetyRatings/VehicleId/\d+", parsed.path
        ):
            raise ValueError(
                "NHTSA adapter requires an official safety-detail endpoint"
            )
    if source.adapter != "document" and source.market != "US":
        raise ValueError("these government adapters support US records only")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, request, response, code, message, headers, new_url
    ):
        raise ValueError("redirect requires review of the source URL")


def fetch(
    source: Source, raw: Path, *, max_bytes: int = MAX_BYTES
) -> Artifact:
    if not 1 <= max_bytes <= 100 * 1024 * 1024:
        raise ValueError("download limit must be between 1 byte and 100 MiB")
    if not source.acquisition_approved:
        raise ValueError(f"acquisition not approved: {source.id}")
    validate_url(source)
    request = Request(
        source.url,
        headers={
            "Accept": (
                "application/json"
                if source.adapter != "document"
                else "application/pdf,text/html"
            ),
            "User-Agent": "VehicleReferenceResearch/0.1",
        },
    )
    with build_opener(NoRedirect()).open(request, timeout=30) as response:
        payload = response.read(max_bytes + 1)
        if not payload or len(payload) > max_bytes:
            raise ValueError(
                f"empty artifact or artifact exceeds {max_bytes} byte limit"
            )
        media_type = response.headers.get_content_type()
        if source.adapter != "document":
            if "json" not in media_type:
                raise ValueError(
                    "expected JSON response, not an HTML/XML error page"
                )
            json.loads(payload)
        elif media_type == "application/pdf" and not payload.startswith(
            b"%PDF-"
        ):
            raise ValueError("invalid PDF signature")
        elif media_type not in {"application/pdf", "text/html"}:
            raise ValueError("document adapter accepts PDF or HTML only")
        artifact = Artifact(
            id=uuid.uuid4().hex,
            source=source,
            retrieved_at=datetime.now(timezone.utc),
            final_url=response.geturl(),
            media_type=media_type,
            sha256=digest(payload),
            byte_count=len(payload),
        )
    write_once(raw / f"{artifact.sha256}.blob", payload)
    write_once(
        raw / f"{artifact.id}.json", encode(artifact.model_dump(mode="json"))
    )
    return artifact


def load_artifacts(raw: Path) -> list[Artifact]:
    artifacts = [
        Artifact.model_validate_json(path.read_bytes())
        for path in sorted(raw.glob("*.json"))
    ]
    if not artifacts:
        raise ValueError("no acquisition manifests found")
    if len({artifact.id for artifact in artifacts}) != len(artifacts):
        raise ValueError("duplicate artifact IDs")
    for artifact in artifacts:
        validate_url(artifact.source)
        payload = (raw / f"{artifact.sha256}.blob").read_bytes()
        if (
            digest(payload) != artifact.sha256
            or len(payload) != artifact.byte_count
        ):
            raise ValueError(f"artifact integrity failure: {artifact.id}")
    return artifacts


def extract(artifact: Artifact, payload: bytes) -> list[Candidate]:
    if artifact.source.adapter == "document":
        return []
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("expected a source object")
    if artifact.source.adapter == "epa":
        required = {"id", "make", "model", "year", "fuelType1"}
        if not required.issubset(data):
            raise ValueError("EPA response missing identity fields")
        record = data
        record_id = str(record["id"])
        identity = {key: str(record[key]) for key in ("make", "model", "year")}
        for key in (
            "drive",
            "trany",
            "displ",
            "eng_dscr",
            "fuelType1",
            "fuelType2",
        ):
            if key in record:
                identity[key] = str(record[key])
        field_map = {
            "city08": "fuel_economy_city",
            "highway08": "fuel_economy_highway",
            "comb08": "fuel_economy_combined",
        }
        facts = []
        fuel = str(record["fuelType1"])
        if fuel not in {
            "Regular Gasoline",
            "Midgrade Gasoline",
            "Premium Gasoline",
            "Diesel",
            "Electricity",
        }:
            raise ValueError(f"EPA fuel mapping not yet validated: {fuel}")
        if record.get("fuelType2"):
            raise ValueError(
                "dual-fuel/PHEV mapping requires a dedicated validated adapter"
            )
        unit = "mpge_us" if fuel == "Electricity" else "mpg_us"
        for field, metric in field_map.items():
            facts.append((field, metric, unit))
        if fuel == "Electricity":
            facts.extend(
                [
                    ("range", "electric_range", "mi"),
                    ("combE", "electricity_consumption_combined", "kWh/100mi"),
                ]
            )
        candidates = []
        for field, metric, unit in facts:
            raw_value = record.get(field)
            if raw_value in (None, ""):
                continue
            if isinstance(raw_value, bool):
                raise ValueError("boolean is not an EPA measurement")
            value = float(raw_value)
            if not math.isfinite(value):
                raise ValueError("nonfinite EPA measurement")
            if value <= 0:
                continue
            evidence = Evidence(
                artifact_id=artifact.id,
                locator=f"/{field}",
                source_record_id=record_id,
                original_value=str(raw_value),
            )
            fact = MeasurementFact(
                id=f"{artifact.id}:{field}",
                kind="measurement",
                metric=metric,
                value=value,
                unit=unit,
                basis="EPA label estimate",
                fuel=fuel,
                evidence=[evidence],
            )
            candidates.append(
                Candidate(
                    id=fact.id,
                    artifact_id=artifact.id,
                    market="US",
                    source_record_id=record_id,
                    source_identity=identity,
                    fact=fact,
                )
            )
    else:
        results = data.get("Results")
        if not isinstance(results, list) or len(results) != 1:
            raise ValueError(
                "NHTSA detail response must contain exactly one result"
            )
        record = results[0]
        if not {
            "VehicleId",
            "Make",
            "Model",
            "ModelYear",
            "VehicleDescription",
        }.issubset(record):
            raise ValueError("NHTSA response missing identity fields")
        record_id = str(record["VehicleId"])
        identity = {
            "make": str(record["Make"]),
            "model": str(record["Model"]),
            "year": str(record["ModelYear"]),
            "description": str(record["VehicleDescription"]),
        }
        candidates = []
        for field, test in {
            "OverallRating": "overall",
            "OverallFrontCrashRating": "frontal",
            "OverallSideCrashRating": "side",
            "RolloverRating": "rollover",
        }.items():
            value = str(record.get(field, ""))
            if value in {"", "Not Rated", "None"}:
                continue
            evidence = Evidence(
                artifact_id=artifact.id,
                locator=f"/Results/0/{field}",
                source_record_id=record_id,
                original_value=value,
            )
            fact = RatingFact(
                id=f"{artifact.id}:{field}",
                kind="rating",
                agency="NHTSA",
                test=test,
                methodology=(
                    "NCAP; verify applicable model-year protocol during review"
                ),
                scale="stars_1_5",
                value=value,
                published_applicability=str(record["VehicleDescription"]),
                evidence=[evidence],
            )
            candidates.append(
                Candidate(
                    id=fact.id,
                    artifact_id=artifact.id,
                    market="US",
                    source_record_id=record_id,
                    source_identity=identity,
                    fact=fact,
                )
            )
    expected_id = urlparse(artifact.source.url).path.rstrip("/").split("/")[-1]
    if record_id != expected_id:
        raise ValueError("response record ID does not match requested record")
    return candidates


def transform(raw: Path) -> Candidates:
    artifacts = load_artifacts(raw)
    candidates = []
    for artifact in artifacts:
        candidates.extend(
            extract(artifact, (raw / f"{artifact.sha256}.blob").read_bytes())
        )
    return Candidates(artifacts=artifacts, candidates=candidates)


def build(raw: Path, plan_path: Path) -> Catalog:
    extracted = transform(raw)
    plan_bytes = plan_path.read_bytes()
    plan = MappingPlan.model_validate_json(plan_bytes)
    if not plan.configurations:
        raise ValueError("publication requires reviewed configurations")
    configurations = {
        configuration.id: configuration
        for configuration in plan.configurations
    }
    if len(configurations) != len(plan.configurations):
        raise ValueError("duplicate configuration IDs")
    candidates = {
        candidate.id: candidate for candidate in extracted.candidates
    }
    artifacts = {artifact.id: artifact for artifact in extracted.artifacts}
    records = {
        identifier: Record(configuration=configuration, facts=[])
        for identifier, configuration in configurations.items()
    }

    def check_evidence(evidence, market):
        for item in evidence:
            artifact = artifacts.get(item.artifact_id)
            if artifact is None or not artifact.source.publication_approved:
                raise ValueError(
                    "review evidence requires a publication-approved artifact"
                )
            if artifact.source.market != market:
                raise ValueError("cross-market mapping is forbidden")

    assigned = set()
    for assignment in plan.assignments:
        if (
            assignment.configuration_id not in records
            or assignment.candidate_id not in candidates
        ):
            raise ValueError(
                "assignment references an unknown configuration or candidate"
            )
        pair = (assignment.configuration_id, assignment.candidate_id)
        if pair in assigned:
            raise ValueError("duplicate assignment")
        assigned.add(pair)
        record = records[assignment.configuration_id]
        candidate = candidates[assignment.candidate_id]
        if candidate.market != record.configuration.market:
            raise ValueError("cross-market mapping is forbidden")
        if candidate.source_identity["year"] != str(record.configuration.year):
            raise ValueError(
                "cross-year mapping is forbidden for these adapters"
            )
        check_evidence(assignment.review.evidence, record.configuration.market)
        fact = candidate.fact.model_copy(deep=True)
        fact.evidence.extend(assignment.review.evidence)
        record.facts.append(fact)
    for reviewed in plan.reviewed_facts:
        if reviewed.configuration_id not in records:
            raise ValueError(
                "reviewed fact references an unknown configuration"
            )
        record = records[reviewed.configuration_id]
        check_evidence(reviewed.review.evidence, record.configuration.market)
        fact = reviewed.fact.model_copy(deep=True)
        fact.evidence.extend(reviewed.review.evidence)
        record.facts.append(fact)
    for record in records.values():
        record.facts.sort(key=lambda fact: fact.id)
    return Catalog(
        release_id=plan.release_id,
        built_at=datetime.now(timezone.utc),
        artifacts=extracted.artifacts,
        records=sorted(
            records.values(), key=lambda record: record.configuration.id
        ),
        feature_vocabulary=plan.feature_vocabulary,
        specification_vocabulary=plan.specification_vocabulary,
        coverage_notes=plan.coverage_notes,
        mapping_plan_sha256=digest(plan_bytes),
    )


def source_by_id(path: Path, identifier: str) -> Source:
    sources = Sources.model_validate_json(path.read_bytes()).sources
    if len({source.id for source in sources}) != len(sources):
        raise ValueError("duplicate source IDs")
    for source in sources:
        if source.id == identifier:
            return source
    raise ValueError(f"unknown source: {identifier}")
