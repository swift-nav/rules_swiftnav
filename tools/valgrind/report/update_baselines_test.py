#!/usr/bin/env python3
"""Tests for update_baselines.py

Run with Bazel:
    bazel test //tools/valgrind/report/...
"""

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tools.valgrind.report.metrics import (
    Metric,
    build_metric,
    build_report,
    write_report,
)
from tools.valgrind.report.update_baselines import main


def _cpu(value: float, baseline: float) -> Metric:
    return build_metric(
        "cpu_instructions", "CPU instructions", "", value, baseline, 5.0
    )


def _heap(value: float, baseline: float, max_value: float | None = None) -> Metric:
    return build_metric(
        "memory_heap_mb", "Peak memory (heap)", "MB", value, baseline, 5.0, max_value
    )


class UpdateBaselinesTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.workspace = Path(tmp.name) / "workspace"
        (self.workspace / "pkg").mkdir(parents=True)
        self.reports_dir = Path(tmp.name) / "reports"
        self.reports_dir.mkdir()

    def _baseline(self, text: str, name: str = "pkg/baseline.json") -> Path:
        path = self.workspace / name
        path.write_text(text)
        return path

    def _run(self, *reports: tuple[list[Metric], str]) -> tuple[int, str, str]:
        paths = []
        for i, (metrics, baseline_file) in enumerate(reports):
            path = self.reports_dir / f"{i}.report.json"
            write_report(build_report(f"//pkg:t{i}", baseline_file, metrics), path)
            paths.append(str(path))

        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--workspace", str(self.workspace), *paths])
        return code, out.getvalue(), err.getvalue()

    def test_regression_and_stale_metrics_take_the_measured_value(self) -> None:
        baseline = self._baseline(
            '{\n  "cpu_instructions": 1000,\n  "memory_heap_mb": 10.000\n}\n'
        )

        code, out, _ = self._run(
            ([_cpu(1200, 1000), _heap(5.25, 10)], "pkg/baseline.json")
        )

        self.assertEqual(code, 0)
        self.assertEqual(
            baseline.read_text(),
            '{\n  "cpu_instructions": 1200,\n  "memory_heap_mb": 5.250\n}\n',
        )
        self.assertIn("pkg/baseline.json: cpu_instructions 1000 -> 1200", out)

    def test_untouched_entries_keep_their_text(self) -> None:
        # 0.550 must not become 0.55, nor the ceiling move.
        baseline = self._baseline(
            '{\n  "cpu_instructions": 1000,\n  "memory_heap_extra_mb": 0.550,\n'
            '  "cpu_instructions_max": 5000\n}\n'
        )

        self._run(([_cpu(1200, 1000)], "pkg/baseline.json"))

        self.assertEqual(
            baseline.read_text(),
            '{\n  "cpu_instructions": 1200,\n  "memory_heap_extra_mb": 0.550,\n'
            '  "cpu_instructions_max": 5000\n}\n',
        )

    def test_passing_and_over_limit_metrics_are_left_alone(self) -> None:
        text = '{\n  "cpu_instructions": 1000,\n  "memory_heap_mb": 10.000\n}\n'
        baseline = self._baseline(text)

        code, out, err = self._run(
            ([_cpu(1010, 1000), _heap(60, 10, max_value=50)], "pkg/baseline.json")
        )

        self.assertEqual(code, 0)
        self.assertEqual(baseline.read_text(), text)
        self.assertIn("No baseline needed updating.", out)
        self.assertIn("memory_heap_mb is over its limit", err)

    def test_reports_sharing_a_file_are_merged(self) -> None:
        baseline = self._baseline('{\n  "cpu_instructions": 1000\n}\n')

        code, _, _ = self._run(
            ([_cpu(1200, 1000)], "pkg/baseline.json"),
            ([_cpu(1200, 1000)], "pkg/baseline.json"),
        )

        self.assertEqual(code, 0)
        self.assertEqual(baseline.read_text(), '{\n  "cpu_instructions": 1200\n}\n')

    def test_reports_disagreeing_on_a_shared_value_fail(self) -> None:
        text = '{\n  "cpu_instructions": 1000\n}\n'
        baseline = self._baseline(text)

        code, _, err = self._run(
            ([_cpu(1200, 1000)], "pkg/baseline.json"),
            ([_cpu(1300, 1000)], "pkg/baseline.json"),
        )

        self.assertEqual(code, 1)
        self.assertIn("reports disagree", err)
        self.assertEqual(baseline.read_text(), text)

    def test_a_bad_file_leaves_every_file_untouched(self) -> None:
        good_text = '{\n  "cpu_instructions": 1000\n}\n'
        good = self._baseline(good_text, "pkg/a.json")
        self._baseline('{\n  "memory_heap_mb": 10\n}\n', "pkg/b.json")

        code, _, err = self._run(
            ([_cpu(1200, 1000)], "pkg/a.json"),
            ([_cpu(1200, 1000)], "pkg/b.json"),
        )

        self.assertEqual(code, 1)
        self.assertIn("no 'cpu_instructions' entry", err)
        self.assertEqual(good.read_text(), good_text)

    def test_paths_outside_the_workspace_are_refused(self) -> None:
        outside = self.workspace.parent / "outside.json"
        outside.write_text('{\n  "cpu_instructions": 1000\n}\n')

        for baseline_file in (str(outside), "../outside.json", "pkg/missing.json"):
            with self.subTest(baseline_file=baseline_file):
                code, _, err = self._run(([_cpu(1200, 1000)], baseline_file))
                self.assertEqual(code, 1)
                self.assertIn("could not update the baselines", err)
        self.assertEqual(outside.read_text(), '{\n  "cpu_instructions": 1000\n}\n')

    def test_a_non_numeric_entry_is_refused(self) -> None:
        self._baseline('{\n  "cpu_instructions": "1000"\n}\n')

        code, _, err = self._run(([_cpu(1200, 1000)], "pkg/baseline.json"))

        self.assertEqual(code, 1)
        self.assertIn("is not a number", err)


if __name__ == "__main__":
    unittest.main()
