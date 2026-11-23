"""Offline unit tests for hydroshare_collect.build_snapshot (CAM-1490).

Uses fakes at the hsclient boundary (objects exposing the same public
interface as hsclient's Resource/Aggregation) instead of a live connection,
per the spec's "offline hsclient-boundary fixtures" testing decision.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hydroshare_collect import build_snapshot, extract_resource_id  # noqa: E402


class FakeMetadata:
    def __init__(self, type_name=None, url=None, title=None, **fields):
        self.type = type_name
        self.url = url
        self.title = title
        self._fields = fields

    def dict(self, by_alias=False):
        data = {"url": self.url, "title": self.title}
        data.update(self._fields)
        return data


class FakeAggregation:
    def __init__(self, metadata: FakeMetadata, files=None, files_error=None):
        self.metadata = metadata
        self._files = files or []
        self._files_error = files_error

    def files(self):
        if self._files_error:
            raise self._files_error
        return self._files


class FakeResource:
    def __init__(self, metadata, system_metadata=None, files=None, aggregations=None, aggregations_error=None):
        self.metadata = metadata
        self._system_metadata = system_metadata or {}
        self._files = files or []
        self._aggregations = aggregations or []
        self._aggregations_error = aggregations_error

    def system_metadata(self):
        return self._system_metadata

    def files(self):
        return self._files

    def aggregations(self):
        if self._aggregations_error:
            raise self._aggregations_error
        return self._aggregations


RESOURCE_METADATA = FakeMetadata(url="https://www.hydroshare.org/resource/abc/", title="A resource", abstract="")


class ExtractResourceIdTests(unittest.TestCase):
    def test_extracts_id_from_url_with_trailing_slash(self):
        resource_id = extract_resource_id(
            "https://www.hydroshare.org/resource/5d5da76611d64b7a8105fadbc5ac7828/"
        )
        self.assertEqual(resource_id, "5d5da76611d64b7a8105fadbc5ac7828")

    def test_extracts_bare_id(self):
        self.assertEqual(
            extract_resource_id("5d5da76611d64b7a8105fadbc5ac7828"),
            "5d5da76611d64b7a8105fadbc5ac7828",
        )

    def test_rejects_input_without_32_char_id(self):
        with self.assertRaises(ValueError):
            extract_resource_id("https://www.hydroshare.org/resource/short/")


class BuildSnapshotTests(unittest.TestCase):
    def test_multiple_modelprogram_aggregations_are_all_collected(self):
        aggs = [
            FakeAggregation(FakeMetadata(type_name="ModelProgram", url=f"https://hs/agg/{i}", title=f"Model {i}"))
            for i in range(3)
        ]
        resource = FakeResource(RESOURCE_METADATA, aggregations=aggs)

        snapshot = build_snapshot(resource)

        self.assertEqual(snapshot["scope_gate"]["type_counts"], {"ModelProgram": 3})
        self.assertTrue(snapshot["scope_gate"]["in_scope"])
        self.assertEqual(len(snapshot["aggregations"]), 3)
        self.assertEqual(snapshot["collection"]["status"], "complete")

    def test_multiple_physical_files_do_not_inflate_aggregation_count(self):
        agg = FakeAggregation(
            FakeMetadata(type_name="ModelProgram", url="https://hs/agg/0", title="Model"),
            files=["main.py", "README.md", "model.exe"],
        )
        resource = FakeResource(RESOURCE_METADATA, aggregations=[agg])

        snapshot = build_snapshot(resource)

        self.assertEqual(len(snapshot["aggregations"]), 1)
        self.assertEqual(len(snapshot["aggregations"][0]["files"]), 3)

    def test_mixed_qualifying_and_non_qualifying_types(self):
        aggs = [
            FakeAggregation(FakeMetadata(type_name="ModelProgram", url="https://hs/agg/0", title="Model")),
            FakeAggregation(FakeMetadata(type_name="Generic", url="https://hs/agg/1", title="Some data")),
        ]
        resource = FakeResource(RESOURCE_METADATA, aggregations=aggs)

        snapshot = build_snapshot(resource)

        self.assertEqual(len(snapshot["aggregations"]), 1)
        self.assertEqual(len(snapshot["other_aggregations"]), 1)
        self.assertEqual(snapshot["other_aggregations"][0]["type"], "Generic")

    def test_no_qualifying_aggregation_reports_out_of_scope(self):
        aggs = [FakeAggregation(FakeMetadata(type_name="Generic", url="https://hs/agg/0", title="Data"))]
        resource = FakeResource(RESOURCE_METADATA, aggregations=aggs)

        snapshot = build_snapshot(resource)

        self.assertFalse(snapshot["scope_gate"]["in_scope"])
        self.assertEqual(snapshot["aggregations"], [])

    def test_blank_optional_field_is_not_a_collection_error(self):
        resource = FakeResource(RESOURCE_METADATA, aggregations=[])

        snapshot = build_snapshot(resource)

        self.assertEqual(snapshot["collection"]["status"], "complete")
        self.assertEqual(snapshot["collection"]["errors"], [])
        self.assertEqual(snapshot["global"]["metadata"]["abstract"], "")

    def test_collection_failure_is_recorded_and_marks_run_failed(self):
        resource = FakeResource(RESOURCE_METADATA, aggregations_error=RuntimeError("401 Unauthorized"))

        snapshot = build_snapshot(resource)

        self.assertEqual(snapshot["collection"]["status"], "failed")
        self.assertEqual(len(snapshot["collection"]["errors"]), 1)
        self.assertEqual(snapshot["collection"]["errors"][0]["scope"], "aggregations")
        self.assertIn("401", snapshot["collection"]["errors"][0]["message"])


if __name__ == "__main__":
    unittest.main()
