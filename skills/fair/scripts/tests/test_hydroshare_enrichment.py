"""Offline unit tests for parent-metadata enrichment in hydroshare_map (CAM-1491).

Uses separate resource and aggregation fixtures to establish field origin,
per the spec's testing decision that combined metadata alone is not evidence
of which scope originally supplied a field.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hydroshare_map import map_aggregation, map_snapshot  # noqa: E402

PARENT_METADATA = {
    "title": "Parent resource title",
    "abstract": "Parent resource abstract describing the whole resource.",
    "creators": [{"name": "Parent Author One"}, {"name": "Parent Author Two"}],
    "rights": {"statement": "Parent rights statement", "url": "http://creativecommons.org/licenses/by/4.0/"},
    "identifier": "https://doi.org/10.1000/parent-doi",
    "subjects": ["parent-topic"],
}

BARE_AGGREGATION_METADATA = {
    "title": None,
    "subjects": [],
    "rights": None,
    "creators": [],
    "url": "https://hs/agg/0",
    "release_date": None,
    "version": None,
    "code_repository": None,
    "website": None,
    "programming_languages": [],
    "operating_systems": [],
}


def bare_aggregation(**overrides):
    metadata = {**BARE_AGGREGATION_METADATA, **overrides}
    return {"url": metadata["url"], "type": "ModelProgram", "metadata": metadata, "files": []}


class AuthorInheritanceTests(unittest.TestCase):
    def test_inherits_parent_creators_in_order_when_aggregation_authors_absent(self):
        codemeta, provenance, _ = map_aggregation(bare_aggregation(), PARENT_METADATA)

        self.assertEqual([a["name"] for a in codemeta["author"]], ["Parent Author One", "Parent Author Two"])
        author_prov = next(p for p in provenance if p["field"] == "author")
        self.assertEqual(author_prov["rule"], "inherited-parent")

    def test_direct_aggregation_authors_take_precedence(self):
        codemeta, provenance, _ = map_aggregation(
            bare_aggregation(creators=[{"name": "Direct Author"}]), PARENT_METADATA
        )

        self.assertEqual([a["name"] for a in codemeta["author"]], ["Direct Author"])
        author_prov = next(p for p in provenance if p["field"] == "author")
        self.assertEqual(author_prov["rule"], "direct")


class LicenseInheritanceTests(unittest.TestCase):
    def test_inherits_parent_rights_when_aggregation_rights_absent(self):
        codemeta, provenance, _ = map_aggregation(bare_aggregation(), PARENT_METADATA)

        self.assertEqual(codemeta["license"], "http://creativecommons.org/licenses/by/4.0/")
        license_prov = next(p for p in provenance if p["field"] == "license")
        self.assertEqual(license_prov["rule"], "inherited-parent")

    def test_aggregation_rights_take_precedence_over_parent(self):
        agg_rights = {"statement": "Aggregation rights", "url": "http://creativecommons.org/licenses/by-sa/4.0/"}
        codemeta, provenance, _ = map_aggregation(bare_aggregation(rights=agg_rights), PARENT_METADATA)

        self.assertEqual(codemeta["license"], "http://creativecommons.org/licenses/by-sa/4.0/")
        license_prov = next(p for p in provenance if p["field"] == "license")
        self.assertEqual(license_prov["rule"], "direct")


class TitleInheritanceTests(unittest.TestCase):
    def test_generic_explicit_title_is_preserved_and_flagged(self):
        codemeta, provenance, quality_issues = map_aggregation(
            bare_aggregation(title="Model Program"), PARENT_METADATA
        )

        self.assertEqual(codemeta["name"], "Model Program")
        name_prov = next(p for p in provenance if p["field"] == "name")
        self.assertEqual(name_prov["rule"], "direct")
        self.assertEqual(quality_issues, [{"field": "name", "issue": "generic-title", "value": "Model Program"}])

    def test_inherits_parent_title_only_when_aggregation_title_absent(self):
        codemeta, provenance, quality_issues = map_aggregation(bare_aggregation(), PARENT_METADATA)

        self.assertEqual(codemeta["name"], "Parent resource title")
        name_prov = next(p for p in provenance if p["field"] == "name")
        self.assertEqual(name_prov["rule"], "inherited-parent")
        self.assertEqual(quality_issues, [])


class DescriptionInheritanceTests(unittest.TestCase):
    def test_provisionally_inherits_parent_abstract_when_aggregation_description_absent(self):
        codemeta, provenance, _ = map_aggregation(bare_aggregation(), PARENT_METADATA)

        self.assertEqual(codemeta["description"], PARENT_METADATA["abstract"])
        description_prov = next(p for p in provenance if p["field"] == "description")
        self.assertEqual(description_prov["rule"], "inherited-parent-provisional")

    def test_direct_aggregation_description_takes_precedence(self):
        codemeta, provenance, _ = map_aggregation(
            bare_aggregation(abstract="Direct aggregation description"), PARENT_METADATA
        )

        self.assertEqual(codemeta["description"], "Direct aggregation description")
        description_prov = next(p for p in provenance if p["field"] == "description")
        self.assertEqual(description_prov["rule"], "direct")


class NoUnapprovedFallbackTests(unittest.TestCase):
    def test_empty_aggregation_subjects_do_not_inherit_parent_keywords(self):
        codemeta, _, _ = map_aggregation(bare_aggregation(subjects=[]), PARENT_METADATA)

        self.assertNotIn("keywords", codemeta)

    def test_parent_identifier_does_not_become_aggregation_identifier(self):
        codemeta, _, _ = map_aggregation(bare_aggregation(url=None), PARENT_METADATA)

        self.assertNotIn("identifier", codemeta)

    def test_parent_has_no_release_date_fallback(self):
        parent_with_date = {**PARENT_METADATA, "created": "2010-01-01"}
        codemeta, _, _ = map_aggregation(bare_aggregation(), parent_with_date)

        self.assertNotIn("datePublished", codemeta)

    def test_no_parent_metadata_leaves_fields_absent(self):
        codemeta, provenance, quality_issues = map_aggregation(bare_aggregation(url=None), {})

        self.assertNotIn("author", codemeta)
        self.assertNotIn("license", codemeta)
        self.assertNotIn("name", codemeta)
        self.assertNotIn("description", codemeta)
        self.assertEqual(provenance, [])
        self.assertEqual(quality_issues, [])


class MapSnapshotEnrichmentTests(unittest.TestCase):
    def test_map_snapshot_passes_parent_metadata_to_aggregation_mapping(self):
        snapshot = {
            "global": {"metadata": PARENT_METADATA},
            "aggregations": [bare_aggregation()],
            "collection": {"status": "complete", "errors": []},
        }

        result = map_snapshot(snapshot)

        record = result["aggregations"][0]
        self.assertEqual(record["codemeta"]["name"], "Parent resource title")
        self.assertEqual([a["name"] for a in record["codemeta"]["author"]], ["Parent Author One", "Parent Author Two"])
        self.assertIn("quality_issues", record)
        self.assertIsNotNone(result["notes"]["description_inheritance_policy"])


if __name__ == "__main__":
    unittest.main()
