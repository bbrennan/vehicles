from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Name = Annotated[str, Field(min_length=1, pattern=r"\S")]
Market = Literal["US", "CA", "MX"]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Evidence(Model):
    artifact_id: Name
    locator: Name
    source_record_id: Name
    original_value: Name


class Conditions(Model):
    package_codes: list[Name] = Field(default_factory=list)
    regions: list[Name] = Field(default_factory=list)
    production_from: date | None = None
    production_to: date | None = None
    notes: list[Name] = Field(default_factory=list)

    @model_validator(mode="after")
    def date_order(self):
        if self.production_from and self.production_to:
            if self.production_from > self.production_to:
                raise ValueError(
                    "production_from must not exceed production_to"
                )
        return self

    def is_unconditional(self) -> bool:
        return not any(self.model_dump().values())


class Configuration(Model):
    id: Name
    market: Market
    year: int = Field(ge=1900, le=2200, strict=True)
    make: Name
    model: Name
    trim: Name
    body_style: Name | None = None
    drivetrain: Literal["FWD", "RWD", "AWD", "4WD"] | None = None
    powertrain: Literal["ICE", "HEV", "PHEV", "BEV", "FCEV"] | None = None
    engine: Name | None = None
    transmission: Name | None = None
    battery: Name | None = None
    wheels: Name | None = None
    cab: Name | None = None
    bed: Name | None = None
    generation: Name | None = None
    evidence: list[Evidence] = Field(min_length=1)


class FactBase(Model):
    id: Name
    conditions: Conditions = Field(default_factory=Conditions)
    evidence: list[Evidence] = Field(min_length=1)


class FeatureFact(FactBase):
    kind: Literal["feature"]
    feature: Name
    availability: Literal["standard", "optional", "package", "unavailable"]

    @model_validator(mode="after")
    def package_required(self):
        if (
            self.availability == "package"
            and not self.conditions.package_codes
        ):
            raise ValueError("package availability requires package_codes")
        return self


class MeasurementFact(FactBase):
    kind: Literal["measurement"]
    metric: Literal[
        "fuel_economy_city",
        "fuel_economy_highway",
        "fuel_economy_combined",
        "electric_range",
        "total_range",
        "electricity_consumption_combined",
        "length",
        "width",
        "height",
        "wheelbase",
        "cargo_volume",
        "towing_capacity",
        "payload",
        "seating_capacity",
        "battery_capacity",
        "charging_power",
        "charging_duration",
        "power",
        "torque",
        "msrp",
    ]
    value: float = Field(ge=0, strict=True)
    unit: Literal[
        "mpg_us",
        "mpge_us",
        "L/100km",
        "mi",
        "km",
        "kWh/100mi",
        "kWh/100km",
        "mm",
        "in",
        "L",
        "ft3",
        "kg",
        "lb",
        "person",
        "kWh",
        "kW",
        "min",
        "hp",
        "Nm",
        "lb-ft",
        "USD",
        "CAD",
        "MXN",
    ]
    basis: Name
    fuel: Name | None = None

    @model_validator(mode="after")
    def valid_unit(self):
        units = {
            "fuel_economy_city": {"mpg_us", "mpge_us", "L/100km"},
            "fuel_economy_highway": {"mpg_us", "mpge_us", "L/100km"},
            "fuel_economy_combined": {"mpg_us", "mpge_us", "L/100km"},
            "electric_range": {"mi", "km"},
            "total_range": {"mi", "km"},
            "electricity_consumption_combined": {"kWh/100mi", "kWh/100km"},
            "length": {"mm", "in"},
            "width": {"mm", "in"},
            "height": {"mm", "in"},
            "wheelbase": {"mm", "in"},
            "cargo_volume": {"L", "ft3"},
            "towing_capacity": {"kg", "lb"},
            "payload": {"kg", "lb"},
            "seating_capacity": {"person"},
            "battery_capacity": {"kWh"},
            "charging_power": {"kW"},
            "charging_duration": {"min"},
            "power": {"hp", "kW"},
            "torque": {"Nm", "lb-ft"},
            "msrp": {"USD", "CAD", "MXN"},
        }
        if self.unit not in units[self.metric]:
            raise ValueError(f"invalid unit for {self.metric}")
        if self.metric.startswith("fuel_economy") and not self.fuel:
            raise ValueError("fuel economy requires a fuel description")
        if self.metric == "seating_capacity" and not self.value.is_integer():
            raise ValueError("seating capacity must be a whole number")
        return self


class RatingFact(FactBase):
    kind: Literal["rating"]
    agency: Literal["NHTSA", "IIHS", "OTHER"]
    test: Name
    methodology: Name
    scale: Name
    value: Name
    published_applicability: Name

    @model_validator(mode="after")
    def nhtsa_scale(self):
        if self.agency == "NHTSA":
            if self.scale != "stars_1_5" or self.value not in {
                "1",
                "2",
                "3",
                "4",
                "5",
            }:
                raise ValueError(
                    "NHTSA star ratings require a value from 1 to 5"
                )
        return self


class ColorFact(FactBase):
    kind: Literal["color"]
    location: Literal["exterior", "interior"]
    name: Name
    code: Name | None = None
    availability: Literal["standard", "optional", "package", "unavailable"]
    paired_color_codes: list[Name] = Field(default_factory=list)

    @model_validator(mode="after")
    def package_required(self):
        if (
            self.availability == "package"
            and not self.conditions.package_codes
        ):
            raise ValueError("package availability requires package_codes")
        return self


class SpecificationFact(FactBase):
    kind: Literal["specification"]
    attribute: Name
    value: Name


Fact = Annotated[
    FeatureFact | MeasurementFact | RatingFact | ColorFact | SpecificationFact,
    Field(discriminator="kind"),
]


class Record(Model):
    configuration: Configuration
    facts: list[Fact]


class Source(Model):
    id: Name
    publisher: Name
    adapter: Literal["epa", "nhtsa", "document"]
    url: Name
    market: Market
    acquisition_approved: bool = False
    publication_approved: bool = False
    rights_reference: Name


class Sources(Model):
    sources: list[Source]


class Artifact(Model):
    id: Name
    source: Source
    retrieved_at: datetime
    final_url: Name
    media_type: Name
    sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    byte_count: int = Field(gt=0)


class Review(Model):
    reviewer: Name
    reviewed_on: date
    rationale: Name
    evidence: list[Evidence] = Field(min_length=1)


class Candidate(Model):
    id: Name
    artifact_id: Name
    market: Market
    source_record_id: Name
    source_identity: dict[str, str]
    fact: Fact


class Candidates(Model):
    schema_version: Literal["0.1.0"] = "0.1.0"
    artifacts: list[Artifact]
    candidates: list[Candidate]


class Assignment(Model):
    candidate_id: Name
    configuration_id: Name
    review: Review


class ReviewedFact(Model):
    configuration_id: Name
    fact: Fact
    review: Review


class MappingPlan(Model):
    schema_version: Literal["0.1.0"] = "0.1.0"
    release_id: Name
    configurations: list[Configuration]
    assignments: list[Assignment] = Field(default_factory=list)
    reviewed_facts: list[ReviewedFact] = Field(default_factory=list)
    feature_vocabulary: dict[str, Name]
    specification_vocabulary: dict[str, Name] = Field(default_factory=dict)
    coverage_notes: list[Name] = Field(min_length=1)


class Catalog(Model):
    schema_version: Literal["0.1.0"] = "0.1.0"
    release_id: Name
    built_at: datetime
    artifacts: list[Artifact]
    records: list[Record]
    feature_vocabulary: dict[str, Name]
    specification_vocabulary: dict[str, Name]
    coverage_notes: list[Name] = Field(min_length=1)
    mapping_plan_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

    @model_validator(mode="after")
    def integrity(self):
        artifacts = {artifact.id: artifact for artifact in self.artifacts}
        if len(artifacts) != len(self.artifacts):
            raise ValueError("duplicate artifact IDs")
        if len({record.configuration.id for record in self.records}) != len(
            self.records
        ):
            raise ValueError("duplicate configuration IDs")
        identities = set()
        for record in self.records:
            configuration = record.configuration
            identity = configuration.model_dump_json(
                exclude={"id", "evidence"}
            )
            if identity in identities:
                raise ValueError("duplicate configuration identity")
            identities.add(identity)
            if len({fact.id for fact in record.facts}) != len(record.facts):
                raise ValueError("duplicate fact IDs within a configuration")
            facts_by_key = {}
            for fact in record.facts:
                if (
                    isinstance(fact, FeatureFact)
                    and fact.feature not in self.feature_vocabulary
                ):
                    raise ValueError(f"unknown feature: {fact.feature}")
                if isinstance(fact, SpecificationFact):
                    if fact.attribute not in self.specification_vocabulary:
                        raise ValueError(
                            f"unknown specification: {fact.attribute}"
                        )
                key_fields = {
                    "feature": ("feature",),
                    "measurement": ("metric", "basis", "fuel"),
                    "rating": ("agency", "test", "methodology"),
                    "color": ("location", "name", "code"),
                    "specification": ("attribute",),
                }[fact.kind]
                key = (
                    fact.kind,
                    *(getattr(fact, field) for field in key_fields),
                )
                if key in facts_by_key:
                    raise ValueError(
                        f"duplicate or potentially conflicting fact: {key}"
                    )
                facts_by_key[key] = fact
            evidence = configuration.evidence + [
                item for fact in record.facts for item in fact.evidence
            ]
            for item in evidence:
                artifact = artifacts.get(item.artifact_id)
                if artifact is None:
                    raise ValueError(f"missing artifact: {item.artifact_id}")
                if not artifact.source.publication_approved:
                    raise ValueError("publication requires source approval")
                if artifact.source.market != configuration.market:
                    raise ValueError(
                        "cross-market evidence requires "
                        "a separate reviewed source"
                    )
        return self
