import argparse
import sys
from pathlib import Path

from vehicle_catalog.models import Candidates, Catalog, MappingPlan, Sources
from vehicle_catalog.pipeline import (
    build,
    encode,
    fetch,
    source_by_id,
    transform,
    write_once,
)


def main():
    parser = argparse.ArgumentParser(
        description="Build evidence-backed local vehicle catalogs"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    schema = commands.add_parser("schema")
    schema.add_argument("--out", type=Path, default=Path("schemas"))
    acquire = commands.add_parser("fetch")
    acquire.add_argument("--sources", type=Path, required=True)
    acquire.add_argument("--source", required=True)
    acquire.add_argument("--raw", type=Path, default=Path("data/raw"))
    extract = commands.add_parser("transform")
    extract.add_argument("--raw", type=Path, default=Path("data/raw"))
    extract.add_argument("--out", type=Path, required=True)
    publish = commands.add_parser("build")
    publish.add_argument("--raw", type=Path, default=Path("data/raw"))
    publish.add_argument("--mapping", type=Path, required=True)
    publish.add_argument("--out", type=Path, required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("catalog", type=Path)
    args = parser.parse_args()
    if args.command == "schema":
        for name, model in {
            "catalog": Catalog,
            "mapping": MappingPlan,
            "sources": Sources,
            "candidates": Candidates,
        }.items():
            write_once(
                args.out / f"{name}.schema.json",
                encode(model.model_json_schema()),
            )
        print(f"Schemas written to {args.out}")
    elif args.command == "fetch":
        artifact = fetch(source_by_id(args.sources, args.source), args.raw)
        print(artifact.model_dump_json(indent=2))
    elif args.command == "transform":
        result = transform(args.raw)
        write_once(args.out, encode(result.model_dump(mode="json")))
        print(
            f"Wrote {len(result.candidates)} unassigned candidates; "
            "none are published"
        )
    elif args.command == "build":
        catalog = build(args.raw, args.mapping)
        write_once(
            args.out.with_suffix(".mapping.json"), args.mapping.read_bytes()
        )
        write_once(args.out, encode(catalog.model_dump(mode="json")))
        print(
            f"Published {len(catalog.records)} configurations "
            f"in {catalog.release_id}"
        )
    else:
        catalog = Catalog.model_validate_json(args.catalog.read_bytes())
        print(
            f"Valid release {catalog.release_id}: "
            f"{len(catalog.records)} configurations"
        )


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
