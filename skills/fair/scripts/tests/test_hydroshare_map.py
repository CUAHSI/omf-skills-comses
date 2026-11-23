"""Offline unit tests for hydroshare_map (CAM-1490).

Operates purely on saved snapshot dicts; no network access and no hsclient
dependency, per the spec's "mapping operates on a saved snapshot" decision.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hydroshare_map import MappingError, map_resource, map_snapshot  # noqa: E402

SUMMA_AGGREGATION = {
    "url": "https://www.hydroshare.org/resource/5d5.../data/contents/summa/",
    "type": "ModelProgram",
    "metadata": {
        "title": "SUMMA",
        "version": "2.0.0",
        "release_date": "2017-05-30",
        "code_repository": "https://github.com/NCAR/summa",
        "website": "http://www.ral.ucar.edu/projects/summa",
        "rights": {
            "statement": "This resource is shared under the Creative Commons Attribution CC BY.",
            "url": "http://creativecommons.org/licenses/by/4.0/",
        },
        "creators": [
            {"name": "Martyn Clark", "identifiers": {}},
            {"name": "Bart Nijssen", "identifiers": {}},
        ],
        "programming_languages": [],
        "operating_systems": [],
        "subjects": ["hydrology"],
    },
    "files": ["summa.exe"],
}


def complete_snapshot(aggregations, global_metadata=None):
    return {
        "global": {"metadata": global_metadata or {"title": "A resource", "creators": []}},
        "aggregations": aggregations,
        "collection": {"status": "complete", "errors": []},
    }


class MapResourceTests(unittest.TestCase):
    def test_resource_mapping_is_independent_of_aggregations(self):
        codemeta, provenance = map_resource(
            {"metadata": {"title": "Parent resource", "abstract": "A parent abstract"}}
        )

        self.assertEqual(codemeta["name"], "Parent resource")
        self.assertEqual(codemeta["description"], "A parent abstract")
        self.assertTrue(all(p["scope"] == "resource" for p in provenance))


class MapSnapshotTests(unittest.TestCase):
    def test_summa_aggregation_direct_fields(self):
        result = map_snapshot(complete_snapshot([SUMMA_AGGREGATION]))

        codemeta = result["aggregations"][0]["codemeta"]
        self.assertEqual(codemeta["name"], "SUMMA")
        self.assertEqual(codemeta["version"], "2.0.0")
        self.assertEqual(codemeta["datePublished"], "2017-05-30")
        self.assertEqual(codemeta["codeRepository"], "https://github.com/NCAR/summa")
        self.assertEqual(codemeta["url"], "http://www.ral.ucar.edu/projects/summa")
        self.assertEqual(codemeta["license"], "http://creativecommons.org/licenses/by/4.0/")
        self.assertNotIn("programmingLanguage", codemeta)
        self.assertNotIn("operatingSystem", codemeta)
        self.assertEqual([a["name"] for a in codemeta["author"]], ["Martyn Clark", "Bart Nijssen"])

    def test_n_modelprogram_aggregations_produce_n_records_plus_one_resource_record(self):
        aggs = [
            {**SUMMA_AGGREGATION, "url": f"https://hs/agg/{i}"} for i in range(3)
        ]
        result = map_snapshot(complete_snapshot(aggs))

        self.assertEqual(len(result["aggregations"]), 3)
        self.assertIn("codemeta", result["resource"])

    def test_non_qualifying_aggregation_type_is_ignored(self):
        other = {**SUMMA_AGGREGATION, "type": "Generic"}
        result = map_snapshot(complete_snapshot([other]))

        self.assertEqual(result["aggregations"], [])

    def test_modelinstance_aggregations_are_deferred_not_dropped_silently(self):
        instance = {**SUMMA_AGGREGATION, "type": "ModelInstance"}
        result = map_snapshot(complete_snapshot([instance]))

        self.assertEqual(result["aggregations"], [])
        self.assertEqual(result["notes"]["deferred_modelinstance_count"], 1)
        self.assertIsNotNone(result["notes"]["deferred_modelinstance_reason"])

    def test_incomplete_collection_refuses_to_map(self):
        snapshot = complete_snapshot([SUMMA_AGGREGATION])
        snapshot["collection"] = {"status": "failed", "errors": [{"scope": "aggregations", "message": "401"}]}

        with self.assertRaises(MappingError):
            map_snapshot(snapshot)

    def test_empty_optional_fields_are_simply_absent_from_codemeta(self):
        agg = {
            **SUMMA_AGGREGATION,
            "metadata": {**SUMMA_AGGREGATION["metadata"], "programming_languages": [], "operating_systems": []},
        }
        result = map_snapshot(complete_snapshot([agg]))

        codemeta = result["aggregations"][0]["codemeta"]
        self.assertNotIn("programmingLanguage", codemeta)
        self.assertNotIn("operatingSystem", codemeta)


if __name__ == "__main__":
    unittest.main()
