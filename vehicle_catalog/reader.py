from pathlib import Path

from vehicle_catalog.models import (
    Catalog,
    ColorFact,
    FeatureFact,
    MeasurementFact,
    RatingFact,
    SpecificationFact,
)


class LocalCatalog:
    def __init__(self, path: Path):
        self._catalog = Catalog.model_validate_json(path.read_bytes())
        self._records = {
            record.configuration.id: record for record in self._catalog.records
        }
        self._models = {}
        self._features = {}
        for record in self._catalog.records:
            configuration = record.configuration
            key = (
                configuration.market,
                configuration.year,
                configuration.make.casefold(),
                configuration.model.casefold(),
            )
            self._models.setdefault(key, []).append(configuration.id)
            for fact in record.facts:
                if isinstance(fact, FeatureFact):
                    self._features.setdefault(fact.feature, []).append(
                        (configuration.id, fact)
                    )

    def _result(self, **values):
        return {
            "release_id": self._catalog.release_id,
            "coverage": "partial; absence is not evidence of unavailability",
            "coverage_notes": list(self._catalog.coverage_notes),
            **values,
        }

    def get(self, configuration_id: str):
        record = self._records.get(configuration_id)
        return self._result(
            status="found" if record else "unknown",
            record=record.model_dump(mode="json") if record else None,
        )

    def trims(self, *, market: str, year: int, make: str, model: str):
        identifiers = self._models.get(
            (market, year, make.casefold(), model.casefold()), []
        )
        return self._result(
            trims=sorted(
                {
                    self._records[identifier].configuration.trim
                    for identifier in identifiers
                }
            ),
            configuration_ids=list(identifiers),
        )

    def with_feature(
        self,
        feature: str,
        *,
        market: str,
        year: int,
        mode: str = "standard",
        limit: int = 100,
    ):
        if mode not in {"standard", "available"} or not 1 <= limit <= 1000:
            raise ValueError("invalid feature search mode or limit")
        if feature not in self._catalog.feature_vocabulary:
            return self._result(status="unknown_feature", matches=[])
        matches = []
        total = 0
        for identifier, fact in self._features.get(feature, []):
            configuration = self._records[identifier].configuration
            if configuration.market != market or configuration.year != year:
                continue
            if fact.availability == "unavailable":
                continue
            if mode == "standard" and (
                fact.availability != "standard"
                or not fact.conditions.is_unconditional()
            ):
                continue
            total += 1
            if len(matches) < limit:
                matches.append(
                    {
                        "configuration_id": identifier,
                        "fact": fact.model_dump(mode="json"),
                    }
                )
        return self._result(
            status="ok", matches=matches, total=total, truncated=total > limit
        )

    def colors(self, configuration_id: str):
        record = self._records.get(configuration_id)
        return self._result(
            status="found" if record else "unknown",
            colors=(
                [
                    fact.model_dump(mode="json")
                    for fact in record.facts
                    if isinstance(fact, ColorFact)
                ]
                if record
                else []
            ),
        )

    def compare(self, configuration_ids: list[str]):
        if not 2 <= len(configuration_ids) <= 6 or len(
            set(configuration_ids)
        ) != len(configuration_ids):
            raise ValueError("compare requires 2-6 distinct configuration IDs")
        records = [
            self._records[identifier] for identifier in configuration_ids
        ]
        if len({record.configuration.market for record in records}) != 1:
            raise ValueError(
                "cross-market comparisons require explicit policy"
            )
        rows = {}
        for record in records:
            for fact in record.facts:
                if isinstance(fact, FeatureFact):
                    key = (fact.kind, fact.feature)
                elif isinstance(fact, MeasurementFact):
                    key = (
                        fact.kind,
                        fact.metric,
                        fact.unit,
                        fact.basis,
                        fact.fuel,
                    )
                elif isinstance(fact, RatingFact):
                    key = (
                        fact.kind,
                        fact.agency,
                        fact.test,
                        fact.methodology,
                        fact.scale,
                    )
                elif isinstance(fact, SpecificationFact):
                    key = (fact.kind, fact.attribute)
                else:
                    key = (fact.kind, fact.location, fact.name, fact.code)
                key = (*key, fact.conditions.model_dump_json())
                rows.setdefault(key, {})[record.configuration.id] = (
                    fact.model_dump(mode="json")
                )
        return self._result(
            rows=[
                {
                    "key": list(key),
                    "values": {
                        identifier: values.get(identifier)
                        for identifier in configuration_ids
                    },
                }
                for key, values in sorted(
                    rows.items(), key=lambda item: str(item[0])
                )
            ],
            note=(
                "Null means unknown. Rows preserve basis and conditions; "
                "no inferred equivalence or change claims."
            ),
        )
