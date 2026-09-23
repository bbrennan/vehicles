import argparse
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, build_opener

from vehicle_catalog.batch import Pilot
from vehicle_catalog.models import Sources
from vehicle_catalog.pipeline import (
    MAX_BYTES,
    NoRedirect,
    digest,
    encode,
    write_once,
)

BASE = "https://www.fueleconomy.gov/ws/rest/vehicle/menu/"


def menu_items(data):
    if not isinstance(data, dict) or "menuItem" not in data:
        raise ValueError("unrecognized EPA menu response")
    items = data["menuItem"]
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        raise ValueError("EPA menu items must be a list or singleton object")
    seen = set()
    for item in items:
        if not isinstance(item, dict) or set(item) != {"text", "value"}:
            raise ValueError("unexpected EPA menu item structure")
        if any(
            not isinstance(item[key], str) or not item[key].strip()
            for key in ("text", "value")
        ):
            raise ValueError("EPA menu labels and values must be strings")
        if item["value"] in seen:
            raise ValueError("duplicate EPA menu value")
        seen.add(item["value"])
    return items


def capture_menu(raw: Path, menu: str, *, year=None, make=None):
    if menu not in {"year", "model"}:
        raise ValueError("only year and model menus are supported")
    url = BASE + menu
    if menu == "model":
        if not isinstance(year, int) or make not in {"Toyota", "Honda"}:
            raise ValueError("model discovery requires an approved make/year")
        url += "?" + urlencode({"year": year, "make": make})
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "VehicleReferenceResearch/0.1",
        },
    )
    with build_opener(NoRedirect()).open(request, timeout=30) as response:
        payload = response.read(MAX_BYTES + 1)
        if not payload or len(payload) > MAX_BYTES:
            raise ValueError("empty or oversized discovery response")
        metadata = {
            "kind": "epa_discovery_snapshot",
            "id": uuid.uuid4().hex,
            "publisher": "FuelEconomy.gov / EPA",
            "market": "US",
            "url": url,
            "final_url": response.geturl(),
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "http_status": response.status,
            "media_type": response.headers.get_content_type(),
            "sha256": digest(payload),
            "byte_count": len(payload),
            "publication_approved": False,
            "rights_reference": (
                "User-authorized bounded public API discovery; "
                "https://www.fueleconomy.gov/feg/ws/; "
                "commercial publication review remains pending"
            ),
        }
    write_once(raw / f"{metadata['sha256']}.blob", payload)
    write_once(raw / f"{metadata['id']}.json", encode(metadata))
    if "json" not in metadata["media_type"]:
        raise ValueError(
            "discovery response is not JSON; raw snapshot retained"
        )
    return metadata, menu_items(json.loads(payload))


def run_discovery(pilot: Pilot, root: Path, run_id: str, through_year: int):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", run_id):
        raise ValueError("invalid run ID")
    if not set(pilot.makes).issubset({"Toyota", "Honda"}):
        raise ValueError("this discovery adapter supports Toyota/Honda only")
    if len(set(pilot.makes)) != len(pilot.makes) or "US" not in pilot.markets:
        raise ValueError("unique makes and US scope required")
    upper = min(through_year, pilot.maximum_year or through_year)
    if not pilot.minimum_year <= upper <= datetime.now().year + 1:
        raise ValueError("invalid discovery year window")
    if (upper - pilot.minimum_year + 1) * len(pilot.makes) > 80:
        raise ValueError("discovery exceeds 80 make/year request budget")
    raw = root / "raw" / run_id
    staged = root / "staged" / run_id
    if raw.exists() or staged.exists():
        raise ValueError("run already exists; choose a new ID")
    raw.mkdir(parents=True)
    staged.mkdir(parents=True)
    write_once(staged / "pilot.json", encode(pilot.model_dump(mode="json")))
    queries = []
    rows = []
    try:
        metadata, items = capture_menu(raw, "year")
        years = {int(item["value"]) for item in items}
        queries.append(
            {
                "menu": "year",
                "status": "acquired",
                "artifact_id": metadata["id"],
            }
        )
    except (OSError, ValueError) as error:
        years = None
        queries.append(
            {
                "menu": "year",
                "status": "failed",
                "error": f"{type(error).__name__}: {error}",
            }
        )
    write_once(staged / "events/000.json", encode(queries[-1]))
    if years is not None:
        for year in range(pilot.minimum_year, upper + 1):
            for make in pilot.makes:
                query = {"market": "US", "year": year, "make": make}
                if year not in years:
                    query["status"] = "not_listed_by_year_menu"
                else:
                    try:
                        metadata, items = capture_menu(
                            raw,
                            "model",
                            year=year,
                            make=make,
                        )
                        query.update(
                            status="acquired",
                            artifact_id=metadata["id"],
                            source_model_count=len(items),
                        )
                        for item in items:
                            rows.append(
                                {
                                    "market": "US",
                                    "year": year,
                                    "make": make,
                                    "source_model_label": item["text"],
                                    "source_model_value": item["value"],
                                    "artifact_id": metadata["id"],
                                    "status": "source_reported_not_curated",
                                }
                            )
                    except (OSError, ValueError) as error:
                        query.update(
                            status="failed",
                            error=f"{type(error).__name__}: {error}",
                        )
                queries.append(query)
                write_once(
                    staged / f"events/{len(queries)-1:03d}.json", encode(query)
                )
                print(f"{make} {year}: {query['status']}", flush=True)
    register = {
        "kind": "source_coverage_register",
        "run_id": run_id,
        "minimum_year": pilot.minimum_year,
        "through_year": upper,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "source_model_year_rows": len(rows),
        "successful_queries": sum(
            query["status"] == "acquired" for query in queries
        ),
        "failed_queries": sum(
            query["status"] == "failed" for query in queries
        ),
        "unacquired_markets": [
            market for market in pilot.markets if market != "US"
        ],
        "limitations": [
            "EPA model labels may contain powertrain/body descriptors.",
            "Rows are neither canonical models nor retail trim lists.",
            "Missing listings do not prove discontinuation or unavailability.",
            "US EPA coverage is not a complete North American offering list.",
        ],
        "queries": queries,
        "rows": rows,
    }
    write_once(staged / "coverage.json", encode(register))
    return register


def require_epa_access(sources: Sources):
    entries = [source for source in sources.sources if source.adapter == "epa"]
    if not entries or any(
        not source.acquisition_approved for source in entries
    ):
        raise ValueError("EPA discovery is on hold pending source-use review")


def main():
    parser = argparse.ArgumentParser(
        description="Preserve EPA model discovery"
    )
    parser.add_argument(
        "--pilot", type=Path, default=Path("config/pilot.json")
    )
    parser.add_argument(
        "--sources", type=Path, default=Path("config/sources.json")
    )
    parser.add_argument("--root", type=Path, default=Path("data"))
    parser.add_argument("--run", required=True)
    parser.add_argument(
        "--through-year", type=int, default=datetime.now().year + 1
    )
    args = parser.parse_args()
    require_epa_access(Sources.model_validate_json(args.sources.read_bytes()))
    pilot = Pilot.model_validate_json(args.pilot.read_bytes())
    result = run_discovery(pilot, args.root, args.run, args.through_year)
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "run_id",
                    "source_model_year_rows",
                    "successful_queries",
                    "failed_queries",
                    "unacquired_markets",
                )
            },
            indent=2,
        )
    )
    return 1 if result["failed_queries"] else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
