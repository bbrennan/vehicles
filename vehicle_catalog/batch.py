import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from pydantic import Field, model_validator

from vehicle_catalog.models import Candidates, Market, Model, Name, Sources
from vehicle_catalog.pipeline import digest, encode, extract, fetch, write_once


class Target(Model):
    source_id: Name
    make: Name
    model: Name
    year: int = Field(ge=1900, le=2200, strict=True)


class Pilot(Model):
    makes: list[Name] = Field(min_length=1)
    markets: list[Market] = Field(min_length=1)
    minimum_year: int = Field(ge=1900, le=2200, strict=True)
    maximum_year: int | None = Field(default=None, ge=1900, le=2200)
    targets: list[Target] = Field(min_length=1)

    def eligible(self, make: str, year: int, market: str) -> bool:
        return (
            make.casefold() in {item.casefold() for item in self.makes}
            and market in self.markets
            and year >= self.minimum_year
            and (self.maximum_year is None or year <= self.maximum_year)
        )

    @model_validator(mode="after")
    def valid_scope(self):
        if (
            self.maximum_year is not None
            and self.maximum_year < self.minimum_year
        ):
            raise ValueError("maximum year precedes minimum year")
        identifiers = [target.source_id for target in self.targets]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("duplicate pilot source IDs")
        for target in self.targets:
            if not self.eligible(target.make, target.year, self.markets[0]):
                raise ValueError("planned target is outside pilot scope")
        return self


def verify_identity(pilot: Pilot, target: Target, artifact, payload: bytes):
    if digest(payload) != artifact.sha256:
        raise ValueError("downloaded artifact hash mismatch")
    data = json.loads(payload)
    if artifact.source.adapter == "epa":
        identity = (data["make"], data["model"], data["year"])
    elif artifact.source.adapter == "nhtsa":
        if len(data["Results"]) != 1:
            raise ValueError("expected exactly one safety record")
        record = data["Results"][0]
        identity = (record["Make"], record["Model"], record["ModelYear"])
    else:
        raise ValueError("document identity requires manual review")
    make, model, year = str(identity[0]), str(identity[1]), int(identity[2])
    if not pilot.eligible(make, year, artifact.source.market):
        raise ValueError("returned identity is outside pilot scope")
    if (make.casefold(), model.casefold(), year) != (
        target.make.casefold(),
        target.model.casefold(),
        target.year,
    ):
        raise ValueError("returned identity differs from planned target")


def run(pilot: Pilot, sources: Sources, root: Path, run_id: str):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", run_id):
        raise ValueError("invalid run ID")
    registry = {source.id: source for source in sources.sources}
    if len(registry) != len(sources.sources):
        raise ValueError("duplicate registry source IDs")
    for target in pilot.targets:
        source = registry.get(target.source_id)
        if source is None:
            raise ValueError(f"unknown source: {target.source_id}")
        if not source.acquisition_approved:
            raise ValueError(f"acquisition not approved: {source.id}")
        if source.market not in pilot.markets:
            raise ValueError("source market is outside scope")
    raw = root / "raw" / run_id
    staged = root / "staged" / run_id
    if raw.exists() or staged.exists():
        raise ValueError("run already exists; use a new run ID")
    for directory in (raw, staged, root / "curated", root / "releases"):
        directory.mkdir(
            parents=True, exist_ok=False if directory == raw else True
        )
    write_once(staged / "pilot.json", encode(pilot.model_dump(mode="json")))
    write_once(
        staged / "sources.json", encode(sources.model_dump(mode="json"))
    )
    artifacts = []
    candidates = []
    results = []
    for target in pilot.targets:
        result = {
            "target": target.model_dump(mode="json"),
            "acquisition": "failed",
            "staging": "not_attempted",
        }
        try:
            artifact = fetch(registry[target.source_id], raw)
            result.update(acquisition="acquired", artifact_id=artifact.id)
            payload = (raw / f"{artifact.sha256}.blob").read_bytes()
            result["staging"] = "failed"
            verify_identity(pilot, target, artifact, payload)
            extracted = extract(artifact, payload)
            artifacts.append(artifact)
            candidates.extend(extracted)
            result.update(staging="staged", candidate_count=len(extracted))
        except (OSError, ValueError, KeyError, TypeError) as error:
            result["error"] = f"{type(error).__name__}: {error}"
        results.append(result)
        write_once(
            staged / "events" / f"{len(results):03d}.json", encode(result)
        )
        print(
            f"{target.source_id}: {result['acquisition']}, "
            f"{result['staging']}",
            flush=True,
        )
    bundle = Candidates(artifacts=artifacts, candidates=candidates)
    write_once(
        staged / "candidates.json", encode(bundle.model_dump(mode="json"))
    )
    report = {
        "run_id": run_id,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "requested": len(pilot.targets),
        "acquired": sum(item["acquisition"] == "acquired" for item in results),
        "staged": sum(item["staging"] == "staged" for item in results),
        "candidate_count": len(candidates),
        "curated_configurations": 0,
        "published_configurations": 0,
        "results": results,
    }
    write_once(staged / "report.json", encode(report))
    return report


def main():
    parser = argparse.ArgumentParser(
        description="Bounded raw acquisition pilot"
    )
    parser.add_argument(
        "--pilot", type=Path, default=Path("config/pilot.json")
    )
    parser.add_argument(
        "--sources", type=Path, default=Path("config/sources.json")
    )
    parser.add_argument("--root", type=Path, default=Path("data"))
    parser.add_argument("--run", required=True)
    args = parser.parse_args()
    pilot = Pilot.model_validate_json(args.pilot.read_bytes())
    sources = Sources.model_validate_json(args.sources.read_bytes())
    report = run(pilot, sources, args.root, args.run)
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "results"},
            indent=2,
        )
    )
    return 0 if report["staged"] == report["requested"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
