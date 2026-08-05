#!/usr/bin/env python3
"""Tests for metrics.py

Run with Bazel:
    bazel test //tools/valgrind/report/...
"""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from metrics import (
    STATUS_OVER_LIMIT,
    STATUS_PASS,
    STATUS_REGRESSION,
    STATUS_STALE_BASELINE,
    Measured,
    Measurement,
    Metric,
    build_metric,
    build_report,
    format_baseline,
    format_delta,
    format_limit,
    format_number,
    format_value,
    print_measurement,
    print_summary,
    read_baseline,
    read_limit,
    read_measurement,
    worst_status,
    write_measurement,
)


def _metric(
    value: float,
    baseline: float,
    unit: str = "",
    key: str = "cpu_instructions",
    max_value: float | None = None,
) -> Metric:
    return build_metric(key, "CPU instructions", unit, value, baseline, 5.0, max_value)


class BuildMetricTest(unittest.TestCase):
    def test_tolerance_boundary_passes(self) -> None:
        self.assertEqual(_metric(105, 100)["status"], STATUS_PASS)

    def test_increase_beyond_tolerance_is_a_regression(self) -> None:
        self.assertEqual(_metric(106, 100)["status"], STATUS_REGRESSION)

    def test_large_improvement_flags_a_stale_baseline(self) -> None:
        self.assertEqual(_metric(80, 100)["status"], STATUS_STALE_BASELINE)

    def test_zero_baseline_does_not_divide(self) -> None:
        metric = _metric(10, 0)
        self.assertAlmostEqual(metric["delta_pct"], 0.0)
        self.assertEqual(metric["status"], STATUS_PASS)

    def test_no_limit_by_default(self) -> None:
        self.assertIsNone(_metric(100, 100)["max"])

    def test_a_value_on_the_limit_passes(self) -> None:
        self.assertEqual(_metric(50, 50, max_value=50)["status"], STATUS_PASS)

    def test_exceeding_the_limit_outranks_being_on_baseline(self) -> None:
        self.assertEqual(_metric(51, 50, max_value=50)["status"], STATUS_OVER_LIMIT)


class WorstStatusTest(unittest.TestCase):
    def test_over_limit_outranks_everything(self) -> None:
        self.assertEqual(
            worst_status([STATUS_REGRESSION, STATUS_OVER_LIMIT]), STATUS_OVER_LIMIT
        )

    def test_regression_outranks_everything_below_it(self) -> None:
        self.assertEqual(
            worst_status([STATUS_PASS, STATUS_STALE_BASELINE, STATUS_REGRESSION]),
            STATUS_REGRESSION,
        )

    def test_stale_baseline_outranks_pass(self) -> None:
        self.assertEqual(
            worst_status([STATUS_PASS, STATUS_STALE_BASELINE]), STATUS_STALE_BASELINE
        )

    def test_all_passing_passes(self) -> None:
        self.assertEqual(worst_status([STATUS_PASS, STATUS_PASS]), STATUS_PASS)

    def test_no_metrics_passes(self) -> None:
        self.assertEqual(worst_status([]), STATUS_PASS)


class BuildReportTest(unittest.TestCase):
    def test_verdict_is_the_worst_metric(self) -> None:
        report = build_report(
            "target",
            "pkg/baseline.txt",
            [_metric(100, 100), _metric(200, 100, key="peak_heap_mb")],
        )

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
            path = self._file(
                tmp, '{"cpu_instructions": 28032185999, "memory_heap_mb": 15.405}'
            )

            self.assertEqual(read_baseline(path, "cpu_instructions"), 28032185999)
            self.assertAlmostEqual(read_baseline(path, "memory_heap_mb"), 15.405)

    def test_rejects_a_missing_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self._file(tmp, '{"memory_heap_mb": 15.405}')
            with self.assertRaises(ValueError):
                read_baseline(path, "cpu_instructions")

    def test_rejects_anything_but_a_positive_number(self) -> None:
        # 0 is an unfilled placeholder, not something to compare against.
        for content in (
            '{"cpu_instructions": 0}',
            '{"cpu_instructions": -5}',
            '{"cpu_instructions": "42"}',
        ):
            with (
                self.subTest(content=content),
                tempfile.TemporaryDirectory() as tmp,
                self.assertRaises(ValueError),
            ):
                read_baseline(self._file(tmp, content), "cpu_instructions")

    def test_rejects_malformed_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
            read_baseline(self._file(tmp, "not json"), "cpu_instructions")


class ReadLimitTest(unittest.TestCase):
    @staticmethod
    def _file(tmp: str, content: str) -> Path:
        path = Path(tmp) / "baseline.json"
        path.write_text(content)
        return path

    def test_reads_the_ceiling_beside_the_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self._file(
                tmp, '{"memory_heap_mb": 15.405, "memory_heap_mb_max": 50}'
            )
            self.assertEqual(read_limit(path, "memory_heap_mb"), 50)

    def test_a_missing_ceiling_is_not_an_error(self) -> None:
        # Most metrics are only gated against their previous value.
        with tempfile.TemporaryDirectory() as tmp:
            path = self._file(tmp, '{"memory_heap_mb": 15.405}')
            self.assertIsNone(read_limit(path, "memory_heap_mb"))

    def test_rejects_a_present_but_unusable_ceiling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
            read_limit(self._file(tmp, '{"memory_heap_mb_max": 0}'), "memory_heap_mb")


class FormatNumberTest(unittest.TestCase):
    def test_counts_render_as_integers(self) -> None:
        self.assertEqual(format_number(18817704711, ""), "18,817,704,711")

    def test_units_render_to_three_decimals(self) -> None:
        self.assertEqual(format_number(15.4051, "MB"), "15.405 MB")

    def test_signed_always_carries_a_sign(self) -> None:
        self.assertEqual(format_number(50, "", signed=True), "+50")
        self.assertEqual(format_number(-0.5, "MB", signed=True), "-0.500 MB")

    def test_metric_helpers_use_the_metric_unit(self) -> None:
        metric = _metric(15.405, 15.4, unit="MB", max_value=50)

        self.assertEqual(format_value(metric), "15.405 MB")
        self.assertEqual(format_baseline(metric), "15.400 MB")
        self.assertEqual(format_delta(metric), "+0.005 MB")
        self.assertEqual(format_limit(metric), "50.000 MB")

    def test_a_metric_without_a_limit_renders_a_dash(self) -> None:
        self.assertEqual(format_limit(_metric(15.405, 15.4, unit="MB")), "—")


class PrintSummaryTest(unittest.TestCase):
    @staticmethod
    def _run(metrics: list[Metric]) -> tuple[int, str, str]:
        report = build_report("target", "pkg/baseline.json", metrics)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = print_summary(report)
        return code, out.getvalue(), err.getvalue()

    def test_passing_says_nothing_on_stderr(self) -> None:
        code, out, err = self._run([_metric(100, 100)])

        self.assertEqual(code, 0)
        self.assertIn("CPU instructions: 100", out)
        self.assertEqual(err, "")

    def test_regression_fails_and_spells_out_the_refresh(self) -> None:
        code, _, err = self._run([_metric(200, 100)])

        self.assertEqual(code, 1)
        self.assertIn('set "cpu_instructions": 200 in pkg/baseline.json', err)

    def test_the_refresh_hint_keeps_decimals_for_a_unit(self) -> None:
        _, _, err = self._run([_metric(20.5, 10, unit="MB", key="memory_heap_mb")])

        self.assertIn('set "memory_heap_mb": 20.500 in pkg/baseline.json', err)

    def test_over_limit_fails_and_names_the_ceiling(self) -> None:
        code, _, err = self._run([_metric(60, 100, unit="MB", max_value=50)])

        self.assertEqual(code, 1)
        self.assertIn("the limit is 50.000 MB", err)
        # A ceiling is not fixed by moving the baseline, so do not suggest it.
        self.assertNotIn("refresh", err)

    def test_a_stale_baseline_warns_on_stdout_without_failing(self) -> None:
        code, out, err = self._run([_metric(10, 100)])

        self.assertEqual(code, 0)
        self.assertIn("Consider refreshing it with:", out)
        self.assertEqual(err, "")

    def test_only_the_metrics_at_fault_are_named(self) -> None:
        _, _, err = self._run(
            [_metric(100, 100), _metric(200, 100, key="memory_heap_mb")]
        )

        self.assertIn('set "memory_heap_mb"', err)
        self.assertNotIn('set "cpu_instructions"', err)


class MeasurementTest(unittest.TestCase):
    _MEASUREMENT = Measurement(
        label="//pkg:target",
        metrics=[
            Measured(key="memory_heap_mb", name="Peak heap", unit="MB", value=10.5),
            Measured(key="cpu_instructions", name="CPU", unit="", value=1000),
        ],
    )

    def test_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "measurement.json"
            write_measurement(self._MEASUREMENT, path)

            self.assertEqual(read_measurement(path), self._MEASUREMENT)

    def test_rejects_a_file_that_is_not_a_measurement(self) -> None:
        # A truncated or hand-edited measurement must not compare as if it were
        # empty, which would pass every baseline vacuously.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "measurement.json"
            for content in ('{"label": "x"}', "[]", '{"label": "x", "metrics": []}'):
                path.write_text(content)
                with self.assertRaises(ValueError):
                    read_measurement(path)

    def test_prints_each_metric_in_its_own_unit(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            print_measurement(self._MEASUREMENT)

        self.assertEqual(out.getvalue(), "Peak heap: 10.500 MB\nCPU: 1,000\n")


if __name__ == "__main__":
    unittest.main()
