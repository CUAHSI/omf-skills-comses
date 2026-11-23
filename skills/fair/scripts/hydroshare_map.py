#!/usr/bin/env python3
"""Offline mapper from a HydroShare source snapshot to CodeMeta (CAM-1490, CAM-1491).

Reads a snapshot produced by hydroshare_collect.py (no network access) and
writes a standalone resource CodeMeta record plus one aggregation CodeMeta
record per ModelProgram aggregation, with a companion provenance report
identifying each mapped value's source scope, source field, and rule.

Aggregation records are enriched through an approved, field-specific parent
(resource) inheritance allowlist (CAM-1491): authors, rights/license, title,
and a provisional description fallback may inherit from the parent resource
when the aggregation value is absent. Every other field (identifier, dates,
version, repository, website, languages, operating systems, keywords) stays
aggregation-only. Inherited values are flagged in the provenance report rather
than presented as direct declarations, and generic titles are reported as a
quality issue rather than silently rewritten.

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


# Approved parent-inheritance allowlist (CAM-1491): authors, rights/license,
# title/name, and a provisional description fallback. Everything else stays
# aggregation-only; this is not a general resource-to-aggregation merge.
GENERIC_TITLE_VALUES = {"model program", "model instance", "untitled", "untitled resource"}


def _is_generic_title(title: str | None) -> bool:
    return bool(title) and title.strip().lower() in GENERIC_TITLE_VALUES


def map_aggregation(agg: dict, parent_metadata: dict | None = None) -> tuple[dict, list[dict], list[dict]]:
    """Map one ModelProgram/ModelInstance aggregation, with approved parent inheritance.

    `parent_metadata` is the resource-level metadata dict (global scope). Direct
    aggregation values always take precedence; only authors, rights, title, and
    a provisional description may fall back to the parent when the aggregation
    value is absent. Identifier, dates, version, repository, website,
    languages, operating systems, and keywords are aggregation-only and never
    inherit from the parent. Returns (codemeta, provenance, quality_issues).
    """
    metadata = agg.get("metadata", {})
    parent_metadata = parent_metadata or {}
    mapping = _Mapping("aggregation")
    quality_issues: list[dict] = []

    # Aggregation-only fields: never fall back to parent.
    mapping.put("keywords", "subjects", metadata.get("subjects"))
    mapping.put("identifier", "url", agg.get("url") or metadata.get("url"))
    mapping.put("datePublished", "release_date", metadata.get("release_date"))
    mapping.put("version", "version", metadata.get("version"))
    mapping.put("codeRepository", "code_repository", metadata.get("code_repository"))
    mapping.put("url", "website", metadata.get("website"))
    mapping.put("programmingLanguage", "programming_languages", metadata.get("programming_languages"))
    mapping.put("operatingSystem", "operating_systems", metadata.get("operating_systems"))

    title = metadata.get("title")
    if title:
        mapping.put("name", "title", title)
        if _is_generic_title(title):
            quality_issues.append({"field": "name", "issue": "generic-title", "value": title})
    elif parent_metadata.get("title"):
        mapping.put("name", "title", parent_metadata.get("title"), rule="inherited-parent")

    creators = metadata.get("creators") or []
    if creators:
        mapping.put("author", "creators", [_creator_to_codemeta(c) for c in creators])
    else:
        parent_creators = parent_metadata.get("creators") or []
        if parent_creators:
            mapping.put(
                "author", "creators", [_creator_to_codemeta(c) for c in parent_creators], rule="inherited-parent"
            )

    rights = metadata.get("rights")
    if rights:
        mapping.put("license", "rights", _rights_to_license(rights))
    elif parent_metadata.get("rights"):
        mapping.put("license", "rights", _rights_to_license(parent_metadata.get("rights")), rule="inherited-parent")

    # hsmodels ModelProgram/ModelInstance aggregation metadata has no abstract
    # field today, so this fallback is the only current description source;
    # "abstract" is checked first so a future direct field still wins.
    description = metadata.get("abstract")
    if description:
        mapping.put("description", "abstract", description)
    elif parent_metadata.get("abstract"):
        mapping.put(
            "description", "abstract", parent_metadata.get("abstract"), rule="inherited-parent-provisional"
        )

    return mapping.codemeta, mapping.provenance, quality_issues


def map_snapshot(snapshot: dict) -> dict:
    """Map a full snapshot. Raises MappingError on an incomplete collection."""
    collection = snapshot.get("collection", {})
    if collection.get("status") != "complete":
        raise MappingError(
            "Refusing to map an incomplete collection. "
            f"Recorded errors: {collection.get('errors')}"
        )

    global_metadata = snapshot.get("global", {}).get("metadata", {})
    resource_codemeta, resource_provenance = map_resource(snapshot.get("global", {}))

    aggregation_records = []
    deferred_modelinstance_count = 0
    for agg in snapshot.get("aggregations", []):
        if agg.get("type") == "ModelInstance":
            deferred_modelinstance_count += 1
            continue
        if agg.get("type") != "ModelProgram":
            continue
        codemeta, provenance, quality_issues = map_aggregation(agg, global_metadata)
        aggregation_records.append(
            {"url": agg.get("url"), "codemeta": codemeta, "provenance": provenance, "quality_issues": quality_issues}
        )

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
            "description_inheritance_policy": (
                "provisional: parent-abstract fallback for aggregation description is an interim "
                "policy pending review of whether a resource abstract accurately describes each "
                "aggregation, especially in multi-model resources (see CAM-1490 spec Further Notes)."
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
