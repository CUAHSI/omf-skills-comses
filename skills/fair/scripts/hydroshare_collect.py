#!/usr/bin/env python3
"""Maintained HydroShare ModelProgram/ModelInstance collector (CAM-1490).

Collects resource-level and aggregation-level metadata anonymously and
read-only through the public hsclient interface, and writes one source
snapshot JSON. No model content is downloaded. See
skills/fair/assets/hydroshare-assessment-process.md for the workflow this
command supports, and skills/fair/scripts/hydroshare_map.py for the paired
offline mapper.

Usage:
    python3 hydroshare_collect.py <resource-url-or-id> --out snapshot.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from typing import Any

# Aggregation types that qualify a resource for software CodeMeta mapping.
# ModelInstance is inventoried here but not yet mapped (CAM-1492).
IN_SCOPE_TYPES = {"ModelProgram", "ModelInstance"}

RESOURCE_ID_RE = re.compile(r"[0-9a-f]{32}")


class CollectionError(Exception):
    """Raised when collection cannot proceed at all (for example, hsclient missing)."""


def extract_resource_id(resource_url_or_id: str) -> str:
    candidate = resource_url_or_id.strip().rstrip("/")
    last_segment = candidate.split("/")[-1]
    match = RESOURCE_ID_RE.search(last_segment) or RESOURCE_ID_RE.search(candidate)
    if not match:
        raise ValueError(f"Could not find a 32-character resource id in {resource_url_or_id!r}")
    return match.group(0)


def _aggregation_type_name(agg_metadata: Any) -> str:
    type_value = agg_metadata.type
    return getattr(type_value, "value", None) or str(type_value)


def _metadata_to_dict(metadata: Any) -> dict:
    # hsmodels metadata objects are pydantic models; fixtures in tests are plain dicts.
    if hasattr(metadata, "dict"):
        return metadata.dict(by_alias=False)
    if hasattr(metadata, "model_dump"):
        return metadata.model_dump(by_alias=False)
    return dict(metadata)


def build_snapshot(
    resource: Any,
    *,
    hsclient_version: str = "unknown",
    hsmodels_version: str = "unknown",
) -> dict:
    """Collect one source snapshot from an already-opened resource handle.

    `resource` is any object exposing the public hsclient Resource interface
    (`.metadata`, `.system_metadata()`, `.files()`, `.aggregations()`), each
    aggregation exposing the same `.metadata`/`.files()` shape. Tests inject
    fakes at this boundary instead of a live hsclient connection.
    """
    errors: list[dict] = []

    global_metadata: dict = {}
    global_system_metadata: dict = {}
    global_files: list = []
    try:
        global_metadata = _metadata_to_dict(resource.metadata)
    except Exception as exc:  # noqa: BLE001 - collection boundary, report and continue
        errors.append({"scope": "global.metadata", "message": str(exc)})
    try:
        global_system_metadata = resource.system_metadata()
    except Exception as exc:  # noqa: BLE001
        errors.append({"scope": "global.system_metadata", "message": str(exc)})
    try:
        global_files = [str(f) for f in resource.files()]
    except Exception as exc:  # noqa: BLE001
        errors.append({"scope": "global.files", "message": str(exc)})

    aggregations: list = []
    other_aggregations: list = []
    type_counts: dict = {}
    try:
        raw_aggregations = list(resource.aggregations())
    except Exception as exc:  # noqa: BLE001
        errors.append({"scope": "aggregations", "message": str(exc)})
        raw_aggregations = []

    for agg in raw_aggregations:
        try:
            type_name = _aggregation_type_name(agg.metadata)
        except Exception as exc:  # noqa: BLE001
            errors.append({"scope": "aggregation.type", "message": str(exc)})
            continue
        type_counts[type_name] = type_counts.get(type_name, 0) + 1

        if type_name not in IN_SCOPE_TYPES:
            other_aggregations.append(
                {
                    "url": getattr(agg.metadata, "url", None),
                    "type": type_name,
                    "title": getattr(agg.metadata, "title", None),
                }
            )
            continue

        try:
            agg_metadata = _metadata_to_dict(agg.metadata)
            agg_files = [str(f) for f in agg.files()]
        except Exception as exc:  # noqa: BLE001
            errors.append({"scope": f"aggregation[{type_name}]", "message": str(exc)})
            continue

        aggregations.append(
            {
                "url": agg_metadata.get("url"),
                "type": type_name,
                "metadata": agg_metadata,
                "files": agg_files,
            }
        )

    return {
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "versions": {"hsclient": hsclient_version, "hsmodels": hsmodels_version},
        "scope_gate": {
            "aggregation_count": len(raw_aggregations),
            "type_counts": type_counts,
            "in_scope": any(t in IN_SCOPE_TYPES for t in type_counts),
        },
        "global": {
            "metadata": global_metadata,
            "system_metadata": global_system_metadata,
            "files": global_files,
        },
        "aggregations": aggregations,
        "other_aggregations": other_aggregations,
        # Blank/absent optional fields above are missing evidence, not errors.
        # Only request/access/parsing failures populate "errors".
        "collection": {
            "status": "failed" if errors else "complete",
            "errors": errors,
        },
    }


def _open_live_resource(resource_id: str):
    try:
        from hsclient import HydroShare  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised only without hsclient installed
        raise CollectionError(
            "hsclient is not installed. Install it (`pip install hsclient`) to collect from "
            "a live HydroShare resource; offline mapping does not need it."
        ) from exc
    return HydroShare().resource(resource_id)


def _installed_version(module_name: str) -> str:
    try:
        module = __import__(module_name)
    except ImportError:
        return "unknown"
    return getattr(module, "__version__", "unknown")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Collect a HydroShare resource snapshot anonymously and read-only."
    )
    parser.add_argument("resource", help="HydroShare resource URL or 32-character resource id")
    parser.add_argument("--out", required=True, help="Path to write the snapshot JSON")
    args = parser.parse_args(argv)

    try:
        resource_id = extract_resource_id(args.resource)
        resource = _open_live_resource(resource_id)
    except (ValueError, CollectionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    snapshot = build_snapshot(
        resource,
        hsclient_version=_installed_version("hsclient"),
        hsmodels_version=_installed_version("hsmodels"),
    )

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, indent=2, sort_keys=True)

    if snapshot["collection"]["status"] != "complete":
        print(f"warning: collection incomplete, see recorded errors in {args.out}", file=sys.stderr)
        return 2

    if not snapshot["scope_gate"]["in_scope"]:
        print(
            "No ModelProgram or ModelInstance aggregation found. "
            f"Observed types: {snapshot['scope_gate']['type_counts']}",
            file=sys.stderr,
        )
        return 3

    print(f"Collected snapshot written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
