#!/usr/bin/env python3
"""Offline mapper from a HydroShare source snapshot to CodeMeta (CAM-1490).

Reads a snapshot produced by hydroshare_collect.py (no network access) and
writes a standalone resource CodeMeta record plus one aggregation CodeMeta
record per ModelProgram aggregation, with a companion provenance report
identifying each mapped value's source scope, source field, and rule.

ModelInstance aggregations are inventoried in the snapshot but not yet mapped
to CodeMeta in this slice (see CAM-1492); this mapper reports how many were
found without producing records for them.

Mapping refuses to run against an incomplete collection
(snapshot["collection"]["status"] != "complete") and fails loudly instead of
producing apparently-complete output.

Usage:
    python3 hydroshare_map.py <snapshot.json> --out-dir <dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

CODEMETA_CONTEXT = "https://w3id.org/codemeta/3.0"

# Field-mapping field names are grounded against the installed hsmodels
# schemas (ResourceMetadataIn / ModelProgramMetadataIn): title, abstract,
# subjects, creators, rights, url, identifier, version, release_date,
# website, code_repository, programming_languages, operating_systems.


class MappingError(Exception):
    """Raised when mapping cannot proceed against the given snapshot."""


def _creator_to_codemeta(creator: dict) -> dict:
    name = creator.get("name")
    organization = creator.get("organization")
    person: dict = {"@type": "Person" if name else "Organization", "name": name or organization}
    orcid = (creator.get("identifiers") or {}).get("ORCID")
    if orcid:
        person["@id"] = orcid
    return person


def _rights_to_license(rights: Any) -> str | None:
    if not rights:
        return None
    if isinstance(rights, dict):
        return rights.get("url") or rights.get("statement")
    return str(rights)


class _Mapping:
    """Accumulates a CodeMeta record plus its field-level provenance."""

    def __init__(self, scope: str):
        self.scope = scope
        self.codemeta: dict = {"@context": CODEMETA_CONTEXT, "@type": "SoftwareSourceCode"}
        self.provenance: list[dict] = []

    def put(self, field: str, source_field: str, value: Any, rule: str = "direct") -> None:
        if value in (None, "", [], {}):
            return
        self.codemeta[field] = value
        self.provenance.append(
            {"field": field, "scope": self.scope, "source_field": source_field, "rule": rule}
        )


def map_resource(global_scope: dict) -> tuple[dict, list[dict]]:
    """Map the standalone resource record. Independent of aggregation mapping."""
    metadata = global_scope.get("metadata", {})
    mapping = _Mapping("resource")

    mapping.put("name", "title", metadata.get("title"))
    mapping.put("description", "abstract", metadata.get("abstract"))
    mapping.put("keywords", "subjects", metadata.get("subjects"))
    mapping.put("license", "rights", _rights_to_license(metadata.get("rights")))
    mapping.put("identifier", "identifier", metadata.get("identifier") or metadata.get("url"))
    creators = metadata.get("creators") or []
    if creators:
        mapping.put("author", "creators", [_creator_to_codemeta(c) for c in creators])
    return mapping.codemeta, mapping.provenance


def map_aggregation(agg: dict) -> tuple[dict, list[dict]]:
    """Map one ModelProgram aggregation. No parent-metadata fallback (CAM-1491)."""
    metadata = agg.get("metadata", {})
    mapping = _Mapping("aggregation")

    mapping.put("name", "title", metadata.get("title"))
    mapping.put("keywords", "subjects", metadata.get("subjects"))
    mapping.put("license", "rights", _rights_to_license(metadata.get("rights")))
    mapping.put("identifier", "url", agg.get("url") or metadata.get("url"))
    mapping.put("datePublished", "release_date", metadata.get("release_date"))
    mapping.put("version", "version", metadata.get("version"))
    mapping.put("codeRepository", "code_repository", metadata.get("code_repository"))
    mapping.put("url", "website", metadata.get("website"))
    mapping.put("programmingLanguage", "programming_languages", metadata.get("programming_languages"))
    mapping.put("operatingSystem", "operating_systems", metadata.get("operating_systems"))
    creators = metadata.get("creators") or []
    if creators:
        mapping.put("author", "creators", [_creator_to_codemeta(c) for c in creators])
    return mapping.codemeta, mapping.provenance


def map_snapshot(snapshot: dict) -> dict:
    """Map a full snapshot. Raises MappingError on an incomplete collection."""
    collection = snapshot.get("collection", {})
    if collection.get("status") != "complete":
        raise MappingError(
            "Refusing to map an incomplete collection. "
            f"Recorded errors: {collection.get('errors')}"
        )

    resource_codemeta, resource_provenance = map_resource(snapshot.get("global", {}))

    aggregation_records = []
    deferred_modelinstance_count = 0
    for agg in snapshot.get("aggregations", []):
        if agg.get("type") == "ModelInstance":
            deferred_modelinstance_count += 1
            continue
        if agg.get("type") != "ModelProgram":
            continue
        codemeta, provenance = map_aggregation(agg)
        aggregation_records.append({"url": agg.get("url"), "codemeta": codemeta, "provenance": provenance})

    return {
        "resource": {"codemeta": resource_codemeta, "provenance": resource_provenance},
        "aggregations": aggregation_records,
        "notes": {
            "deferred_modelinstance_count": deferred_modelinstance_count,
            "deferred_modelinstance_reason": (
                "ModelInstance mapping is not implemented in this slice (see CAM-1492); "
                "these aggregations were inventoried but did not receive a CodeMeta record."
                if deferred_modelinstance_count
                else None
            ),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Map a HydroShare source snapshot to CodeMeta offline.")
    parser.add_argument("snapshot", help="Path to a snapshot JSON written by hydroshare_collect.py")
    parser.add_argument("--out-dir", required=True, help="Directory to write mapped CodeMeta/provenance output")
    args = parser.parse_args(argv)

    with open(args.snapshot, encoding="utf-8") as fh:
        snapshot = json.load(fh)

    try:
        result = map_snapshot(snapshot)
    except MappingError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "resource-codemeta.json", "w", encoding="utf-8") as fh:
        json.dump(result["resource"]["codemeta"], fh, indent=2, sort_keys=True)
    for i, record in enumerate(result["aggregations"]):
        with open(out_dir / f"aggregation-{i}-codemeta.json", "w", encoding="utf-8") as fh:
            json.dump(record["codemeta"], fh, indent=2, sort_keys=True)
    with open(out_dir / "mapping-report.json", "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, sort_keys=True)

    print(
        f"Mapped {len(result['aggregations'])} aggregation record(s) and 1 resource record to {out_dir}"
    )
    if result["notes"]["deferred_modelinstance_count"]:
        print(f"note: {result['notes']['deferred_modelinstance_reason']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
