#!/usr/bin/env python3
"""Tests for compare.py

Run with Bazel:
    bazel test //tools/valgrind/report/...
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from compare import DEFAULT_TOLERANCE_PCT, main, run
from metrics import (
    STATUS_OVER_LIMIT,
    STATUS_PASS,
    STATUS_REGRESSION,
    STATUS_STALE_BASELINE,
    Measured,
    Measurement,
    Report,
    read_report,
    write_measurement,
)

# Two metrics with units, as massif measures them, so a report keeps them in the
# order the measurement listed.
_MEMORY = Measurement(
    label="my_target",
    metrics=[
        Measured(
            key="memory_heap_mb", name="Peak heap (massif)", unit="MB", value=10.0
        ),
        Measured(key="memory_total_mb", name="Peak memory", unit="MB", value=15.0),
    ],
)

# One unitless metric, as callgrind measures it.
_CPU = Measurement(
    label="my_target",
    metrics=[
        Measured(
            key="cpu_instructions", name="CPU instructions", unit="", value=1000000
        )
    ],
)


def _write(path: Path, content: str) -> Path:
    path.write_text(content)
    return path


class RunTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.report_out = self.tmp / "report.json"

    def _measurement(self, measurement: Measurement) -> Path:
        path = self.tmp / "measurement.json"
        write_measurement(measurement, path)
        return path

    def _run(self, measurement: Measurement, baseline_json: str) -> int:
        return run(
            self._measurement(measurement),
            baseline=_write(self.tmp / "baseline.json", baseline_json),
            baseline_label="pkg/baseline.json",
            report_out=self.report_out,
        )

    def _report(self) -> Report:
        return read_report(self.report_out)

    def test_writes_no_report_without_a_baseline(self) -> None:
        # A target can profile before anyone has decided what it should cost.
        self.assertEqual(run(self._measurement(_MEMORY)), 0)
        self.assertFalse(self.report_out.exists())

    def test_passes_on_baseline_and_carries_every_metric_through(self) -> None:
        self.assertEqual(
            self._run(_MEMORY, '{"memory_heap_mb": 10, "memory_total_mb": 15}'), 0
        )

        report = self._report()
        self.assertEqual(report["status"], STATUS_PASS)
        self.assertEqual(report["label"], "my_target")
        self.assertEqual(report["baseline_file"], "pkg/baseline.json")
        self.assertEqual(
            [metric["key"] for metric in report["metrics"]],
            ["memory_heap_mb", "memory_total_mb"],
        )
        self.assertEqual(report["metrics"][0]["name"], "Peak heap (massif)")
        self.assertEqual(report["metrics"][0]["unit"], "MB")
        self.assertAlmostEqual(
            report["metrics"][0]["tolerance_pct"], DEFAULT_TOLERANCE_PCT
        )

    def test_fails_when_one_metric_regresses(self) -> None:
        self.assertEqual(
            self._run(_MEMORY, '{"memory_heap_mb": 5, "memory_total_mb": 15}'), 1
        )

        report = self._report()
        self.assertEqual(report["status"], STATUS_REGRESSION)
        self.assertEqual(report["metrics"][0]["status"], STATUS_REGRESSION)
        self.assertEqual(report["metrics"][1]["status"], STATUS_PASS)

    def test_fails_when_a_metric_is_over_its_absolute_limit(self) -> None:
        # On baseline, so only the ceiling can fail it.
        baseline = (
            '{"memory_heap_mb": 10, "memory_heap_mb_max": 8, "memory_total_mb": 15}'
        )
        self.assertEqual(self._run(_MEMORY, baseline), 1)

        report = self._report()
        self.assertEqual(report["status"], STATUS_OVER_LIMIT)
        self.assertEqual(report["metrics"][0]["max"], 8)

    def test_stale_baseline_warns_but_succeeds(self) -> None:
        self.assertEqual(
            self._run(_MEMORY, '{"memory_heap_mb": 40, "memory_total_mb": 15}'), 0
        )
        self.assertEqual(self._report()["status"], STATUS_STALE_BASELINE)

    def test_fails_on_a_baseline_missing_a_metric(self) -> None:
        self.assertEqual(self._run(_MEMORY, '{"memory_heap_mb": 10}'), 1)
        self.assertFalse(self.report_out.exists())

    def test_fails_on_an_unusable_baseline(self) -> None:
        self.assertEqual(self._run(_CPU, '{"cpu_instructions": "not a number"}'), 1)

    def test_fails_on_a_missing_baseline_file(self) -> None:
        self.assertEqual(
            run(self._measurement(_CPU), baseline=self.tmp / "absent.json"), 1
        )

    def test_gates_a_unitless_metric_the_same_way(self) -> None:
        # compare knows nothing about which profiler produced the measurement.
        self.assertEqual(self._run(_CPU, '{"cpu_instructions": 900000}'), 1)
        self.assertEqual(self._report()["status"], STATUS_REGRESSION)

    def test_fails_on_a_measurement_it_cannot_read(self) -> None:
        path = _write(self.tmp / "measurement.json", '{"label": "x"}')
        self.assertEqual(run(path, baseline=self.tmp / "baseline.json"), 1)

    def test_fails_on_a_measurement_with_no_metrics(self) -> None:
        # An empty measurement would otherwise pass every baseline vacuously.
        path = _write(
            self.tmp / "measurement.json", json.dumps({"label": "x", "metrics": []})
        )
        self.assertEqual(run(path, baseline=self.tmp / "baseline.json"), 1)


class MainTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.measurement = self.tmp / "measurement.json"
        write_measurement(_CPU, self.measurement)
        self.baseline = _write(
            self.tmp / "baseline.json", '{"cpu_instructions": 1000000}'
        )
        self.outputs = self.tmp / "outputs"
        self.outputs.mkdir()

    def _main(self, *args: str, environ: dict[str, str] | None = None) -> int:
        with mock.patch.dict(os.environ, environ or {}, clear=True):
            return main(
                [
                    "--measurement",
                    str(self.measurement),
                    "--baseline",
                    str(self.baseline),
                    *args,
                ]
            )

    def test_writes_the_report_into_the_test_outputs(self) -> None:
        # The name and location are what pr_comment and CI already expect, so
        # splitting the halves changed nothing downstream.
        code = self._main(
            "--report-name",
            "valgrind-callgrind.report.json",
            environ={"TEST_UNDECLARED_OUTPUTS_DIR": str(self.outputs)},
        )

        self.assertEqual(code, 0)
        self.assertTrue((self.outputs / "valgrind-callgrind.report.json").exists())

    def test_an_explicit_output_dir_beats_the_environment(self) -> None:
        elsewhere = self.tmp / "elsewhere"
        elsewhere.mkdir()

        self._main(
            "--report-name",
            "r.json",
            "--output-dir",
            str(elsewhere),
            environ={"TEST_UNDECLARED_OUTPUTS_DIR": str(self.outputs)},
        )

        self.assertTrue((elsewhere / "r.json").exists())
        self.assertFalse((self.outputs / "r.json").exists())

    def test_only_prints_when_run_outside_a_test(self) -> None:
        # A bare `bazel run` has nowhere to put a report and just says what it
        # found.
        self.assertEqual(self._main("--report-name", "r.json"), 0)
        self.assertFalse((self.tmp / "r.json").exists())

    def test_needs_a_name_before_it_writes_anything(self) -> None:
        self.assertEqual(
            self._main(environ={"TEST_UNDECLARED_OUTPUTS_DIR": str(self.outputs)}), 0
        )
        self.assertEqual(list(self.outputs.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
