#!/usr/bin/env python3
"""Tests for callgrind_report.py

Run with Bazel:
    bazel test //tools/valgrind/...
"""

import json
import tempfile
import unittest
from pathlib import Path

from tools.valgrind.callgrind_report import (
    INSTRUCTIONS_FILENAME,
    REPORT_JSON_FILENAME,
    REPORT_MD_FILENAME,
    STATUS_PASS,
    STATUS_REGRESSION,
    STATUS_STALE_BASELINE,
    TABLE_HEADER,
    Report,
    build_report,
    find_output_files,
    format_row,
    main,
    read_baseline,
    sum_instructions,
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
            self.assertEqual(sum_instructions(find_output_files(tmp)), 1250000)

    def test_ignores_everything_but_per_process_dumps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "valgrind-callgrind.1", _SUMMARY_DUMP)
            # The report files this tool writes into the same directory must
            # never be picked up as callgrind output on a re-run.
            _write(root / INSTRUCTIONS_FILENAME, "1000000\n")
            _write(root / REPORT_MD_FILENAME, "| table |\n")

            self.assertEqual([Path(p).name for p in find_output_files(tmp)], ["valgrind-callgrind.1"])

    def test_raises_when_no_dump_carries_a_total(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _write(Path(tmp) / "valgrind-callgrind.1", "version: 1\nfn=main\n0 12\n")
            with self.assertRaises(ValueError):
                sum_instructions(find_output_files(tmp))


class ReadBaselineTest(unittest.TestCase):
    def test_reads_integer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(read_baseline(_write(Path(tmp) / "baseline.txt", "  1230982304\n")), 1230982304)

    def test_rejects_anything_but_a_positive_integer(self) -> None:
        # 0 is an unfilled placeholder, not something to compare against.
        for content in ("1.2e9\n", "0\n", "-5\n", "\n"):
            with (
                self.subTest(content=content),
                tempfile.TemporaryDirectory() as tmp,
                self.assertRaises(ValueError),
            ):
                read_baseline(_write(Path(tmp) / "baseline.txt", content))


class BuildReportTest(unittest.TestCase):
    @staticmethod
    def _status(measured: int, baseline: int) -> str:
        return build_report("target", measured, baseline, "pkg/baseline.txt", 5.0)["status"]

    def test_tolerance_boundary_passes(self) -> None:
        self.assertEqual(self._status(measured=105, baseline=100), STATUS_PASS)

    def test_increase_beyond_tolerance_is_a_regression(self) -> None:
        self.assertEqual(self._status(measured=106, baseline=100), STATUS_REGRESSION)

    def test_large_improvement_flags_a_stale_baseline(self) -> None:
        self.assertEqual(self._status(measured=80, baseline=100), STATUS_STALE_BASELINE)


class FormatRowTest(unittest.TestCase):
    def test_renders_every_column(self) -> None:
        report: Report = build_report("my_target", 1050, 1000, "pkg/baseline.txt", 5.0)
        self.assertEqual(
            format_row(report),
            "| `my_target` | 1,050 | 1,000 | +50 (+5.00%) | ±5.00% | ✅ pass |",
        )


class MainTest(unittest.TestCase):
    @staticmethod
    def _output_dir(tmp: str) -> str:
        _write(Path(tmp) / "valgrind-callgrind.1", _SUMMARY_DUMP)
        return tmp

    @staticmethod
    def _run(tmp: str, baseline_value: str, tolerance_pct: str = "5") -> int:
        baseline = _write(Path(tmp) / "baseline.txt", baseline_value)
        return main(
            [
                "--output-dir",
                tmp,
                "--label",
                "my_target",
                "--instructions-baseline",
                str(baseline),
                "--baseline-label",
                "pkg/baseline.txt",
                "--tolerance-pct",
                tolerance_pct,
            ]
        )

    def test_writes_instructions_file_without_a_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._output_dir(tmp)

            self.assertEqual(main(["--output-dir", tmp]), 0)

            self.assertEqual((Path(tmp) / INSTRUCTIONS_FILENAME).read_text(), "1000000\n")
            self.assertFalse((Path(tmp) / REPORT_JSON_FILENAME).exists())

    def test_fails_when_no_callgrind_output_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(main(["--output-dir", tmp]), 1)

    def test_passes_within_tolerance_and_writes_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._output_dir(tmp)

            self.assertEqual(self._run(tmp, "980000\n"), 0)

            report = json.loads((Path(tmp) / REPORT_JSON_FILENAME).read_text())
            self.assertEqual(report["status"], STATUS_PASS)
            self.assertEqual(report["label"], "my_target")
            self.assertEqual(report["cpu_instructions"], 1000000)
            self.assertEqual(report["baseline"], 980000)
            self.assertEqual(report["baseline_file"], "pkg/baseline.txt")
            self.assertTrue((Path(tmp) / REPORT_MD_FILENAME).read_text().startswith(TABLE_HEADER))

    def test_fails_on_regression_beyond_tolerance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._output_dir(tmp)

            self.assertEqual(self._run(tmp, "900000\n"), 1)

            report = json.loads((Path(tmp) / REPORT_JSON_FILENAME).read_text())
            self.assertEqual(report["status"], STATUS_REGRESSION)

    def test_stale_baseline_warns_but_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._output_dir(tmp)

            self.assertEqual(self._run(tmp, "2000000\n"), 0)

            report = json.loads((Path(tmp) / REPORT_JSON_FILENAME).read_text())
            self.assertEqual(report["status"], STATUS_STALE_BASELINE)

    def test_fails_on_malformed_baseline_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._output_dir(tmp)
            self.assertEqual(self._run(tmp, "not a number\n"), 1)

    def test_fails_on_placeholder_baseline_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._output_dir(tmp)
            self.assertEqual(self._run(tmp, "0\n"), 1)
            self.assertFalse((Path(tmp) / REPORT_JSON_FILENAME).exists())


if __name__ == "__main__":
    unittest.main()
