#!/usr/bin/env python3
"""Tests for callgrind_report.py

Run with Bazel:
    bazel test //tools/valgrind/report/...
"""

import tempfile
import unittest
from pathlib import Path

from tools.valgrind.report.callgrind_report import (
    INSTRUCTIONS_FILENAME,
    REPORT_JSON_FILENAME,
    find_output_files,
    main,
    sum_instructions,
)
from tools.valgrind.report.metrics import (
    STATUS_PASS,
    STATUS_REGRESSION,
    STATUS_STALE_BASELINE,
    read_report,
)

# Multi-event summary line: the first field is Ir, the rest are other events.
_SUMMARY_DUMP = """\
version: 1
creator: callgrind-3.22.0
events: Ir Dr Dw
fn=main
0 12
summary: 1000000 100 50
"""

# Older callgrind writes "totals:" instead of "summary:".
_TOTALS_DUMP = """\
version: 1
events: Ir
fn=main
0 12
totals: 250000
"""


def _write(path: Path, content: str) -> Path:
    path.write_text(content)
    return path


class ReadCallgrindOutputTest(unittest.TestCase):
    def test_sums_both_dump_formats_across_processes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _write(Path(tmp) / "valgrind-callgrind.1", _SUMMARY_DUMP)
            _write(Path(tmp) / "valgrind-callgrind.2", _TOTALS_DUMP)
            self.assertEqual(sum_instructions(find_output_files(Path(tmp))), 1250000)

    def test_counts_multi_part_and_per_thread_dumps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "valgrind-callgrind.1.2", _SUMMARY_DUMP)
            _write(root / "valgrind-callgrind.2-01", _TOTALS_DUMP)
            _write(root / "valgrind-callgrind.3.1-02", _TOTALS_DUMP)

            self.assertEqual(sum_instructions(find_output_files(root)), 1500000)

    def test_ignores_everything_but_per_process_dumps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "valgrind-callgrind.1", _SUMMARY_DUMP)
            # The files this tool writes into the same directory must never be
            # picked up as callgrind output on a re-run.
            _write(root / INSTRUCTIONS_FILENAME, "1000000\n")
            _write(root / REPORT_JSON_FILENAME, "{}\n")

            self.assertEqual(
                [p.name for p in find_output_files(root)], ["valgrind-callgrind.1"]
            )

    def test_raises_when_no_dump_carries_a_total(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _write(Path(tmp) / "valgrind-callgrind.1", "version: 1\nfn=main\n0 12\n")
            with self.assertRaises(ValueError):
                sum_instructions(find_output_files(Path(tmp)))


class MainTest(unittest.TestCase):
    @staticmethod
    def _output_dir(tmp: str) -> str:
        _write(Path(tmp) / "valgrind-callgrind.1", _SUMMARY_DUMP)
        return tmp

    @staticmethod
    def _run(tmp: str, baseline_json: str, tolerance_pct: str = "5") -> int:
        baseline = _write(Path(tmp) / "baseline.json", baseline_json)
        return main(
            [
                "--output-dir",
                tmp,
                "--label",
                "my_target",
                "--baseline",
                str(baseline),
                "--baseline-label",
                "pkg/baseline.json",
                "--tolerance-pct",
                tolerance_pct,
            ]
        )

    def test_writes_instructions_file_without_a_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._output_dir(tmp)

            self.assertEqual(main(["--output-dir", tmp]), 0)

            self.assertEqual(
                (Path(tmp) / INSTRUCTIONS_FILENAME).read_text(), "1000000\n"
            )
            self.assertFalse((Path(tmp) / REPORT_JSON_FILENAME).exists())

    def test_fails_when_no_callgrind_output_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(main(["--output-dir", tmp]), 1)

    def test_passes_within_tolerance_and_writes_one_cpu_metric(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._output_dir(tmp)

            self.assertEqual(self._run(tmp, '{"cpu_instructions": 980000}'), 0)

            report = read_report(Path(tmp) / REPORT_JSON_FILENAME)
            self.assertEqual(report["status"], STATUS_PASS)
            self.assertEqual(report["label"], "my_target")
            self.assertEqual(report["baseline_file"], "pkg/baseline.json")
            self.assertEqual(len(report["metrics"]), 1)
            metric = report["metrics"][0]
            self.assertEqual(metric["key"], "cpu_instructions")
            self.assertEqual(metric["name"], "CPU instructions")
            self.assertEqual(metric["unit"], "")
            self.assertEqual(metric["value"], 1000000)
            self.assertEqual(metric["baseline"], 980000)
            self.assertAlmostEqual(metric["tolerance_pct"], 5.0)

    def test_fails_on_regression_beyond_tolerance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._output_dir(tmp)

            self.assertEqual(self._run(tmp, '{"cpu_instructions": 900000}'), 1)

            self.assertEqual(
                read_report(Path(tmp) / REPORT_JSON_FILENAME)["status"],
                STATUS_REGRESSION,
            )

    def test_stale_baseline_warns_but_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._output_dir(tmp)

            self.assertEqual(self._run(tmp, '{"cpu_instructions": 2000000}'), 0)

            self.assertEqual(
                read_report(Path(tmp) / REPORT_JSON_FILENAME)["status"],
                STATUS_STALE_BASELINE,
            )

    def test_fails_on_an_unusable_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._output_dir(tmp)
            self.assertEqual(self._run(tmp, '{"cpu_instructions": "not a number"}'), 1)


if __name__ == "__main__":
    unittest.main()
