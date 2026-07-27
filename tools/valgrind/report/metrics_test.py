#!/usr/bin/env python3
"""Tests for metrics.py

Run with Bazel:
    bazel test //tools/valgrind/report/...
"""

import tempfile
import unittest
from pathlib import Path

from tools.valgrind.report.metrics import (
    STATUS_PASS,
    STATUS_REGRESSION,
    STATUS_STALE_BASELINE,
    Metric,
    build_metric,
    build_report,
    format_baseline,
    format_delta,
    format_number,
    format_value,
    read_baseline,
    worst_status,
)


def _metric(value: float, baseline: float, unit: str = "", key: str = "cpu_instructions") -> Metric:
    return build_metric(key, "CPU instructions", unit, value, baseline, 5.0)


class BuildMetricTest(unittest.TestCase):
    def test_tolerance_boundary_passes(self) -> None:
        self.assertEqual(_metric(105, 100)["status"], STATUS_PASS)

    def test_increase_beyond_tolerance_is_a_regression(self) -> None:
        self.assertEqual(_metric(106, 100)["status"], STATUS_REGRESSION)

    def test_large_improvement_flags_a_stale_baseline(self) -> None:
        self.assertEqual(_metric(80, 100)["status"], STATUS_STALE_BASELINE)

    def test_zero_baseline_does_not_divide(self) -> None:
        metric = _metric(10, 0)
        self.assertEqual(metric["delta_pct"], 0.0)
        self.assertEqual(metric["status"], STATUS_PASS)


class WorstStatusTest(unittest.TestCase):
    def test_regression_outranks_everything(self) -> None:
        self.assertEqual(worst_status([STATUS_PASS, STATUS_STALE_BASELINE, STATUS_REGRESSION]), STATUS_REGRESSION)

    def test_stale_baseline_outranks_pass(self) -> None:
        self.assertEqual(worst_status([STATUS_PASS, STATUS_STALE_BASELINE]), STATUS_STALE_BASELINE)

    def test_all_passing_passes(self) -> None:
        self.assertEqual(worst_status([STATUS_PASS, STATUS_PASS]), STATUS_PASS)

    def test_no_metrics_passes(self) -> None:
        self.assertEqual(worst_status([]), STATUS_PASS)


class BuildReportTest(unittest.TestCase):
    def test_verdict_is_the_worst_metric(self) -> None:
        report = build_report("target", "pkg/baseline.txt", [_metric(100, 100), _metric(200, 100, key="peak_heap_mb")])

        self.assertEqual(report["status"], STATUS_REGRESSION)
        self.assertEqual(report["label"], "target")
        self.assertEqual(report["baseline_file"], "pkg/baseline.txt")
        self.assertEqual(len(report["metrics"]), 2)


class ReadBaselineTest(unittest.TestCase):
    @staticmethod
    def _file(tmp: str, content: str) -> Path:
        path = Path(tmp) / "baseline.json"
        path.write_text(content)
        return path

    def test_reads_the_requested_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self._file(tmp, '{"cpu_instructions": 28032185999, "memory_heap_mb": 15.405}')

            self.assertEqual(read_baseline(path, "cpu_instructions"), 28032185999)
            self.assertEqual(read_baseline(path, "memory_heap_mb"), 15.405)

    def test_rejects_a_missing_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self._file(tmp, '{"memory_heap_mb": 15.405}')
            with self.assertRaises(ValueError):
                read_baseline(path, "cpu_instructions")

    def test_rejects_anything_but_a_positive_number(self) -> None:
        # 0 is an unfilled placeholder, not something to compare against.
        for content in ('{"cpu_instructions": 0}', '{"cpu_instructions": -5}', '{"cpu_instructions": "42"}'):
            with (
                self.subTest(content=content),
                tempfile.TemporaryDirectory() as tmp,
                self.assertRaises(ValueError),
            ):
                read_baseline(self._file(tmp, content), "cpu_instructions")

    def test_rejects_malformed_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
            read_baseline(self._file(tmp, "not json"), "cpu_instructions")


class FormatNumberTest(unittest.TestCase):
    def test_counts_render_as_integers(self) -> None:
        self.assertEqual(format_number(18817704711, ""), "18,817,704,711")

    def test_units_render_to_three_decimals(self) -> None:
        self.assertEqual(format_number(15.4051, "MB"), "15.405 MB")

    def test_signed_always_carries_a_sign(self) -> None:
        self.assertEqual(format_number(50, "", signed=True), "+50")
        self.assertEqual(format_number(-0.5, "MB", signed=True), "-0.500 MB")

    def test_metric_helpers_use_the_metric_unit(self) -> None:
        metric = _metric(15.405, 15.4, unit="MB")

        self.assertEqual(format_value(metric), "15.405 MB")
        self.assertEqual(format_baseline(metric), "15.400 MB")
        self.assertEqual(format_delta(metric), "+0.005 MB")


if __name__ == "__main__":
    unittest.main()
