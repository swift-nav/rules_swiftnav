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
    STATUS_UNRECORDED,
    TABLE_HEADER,
    Report,
    build_report,
    find_output_files,
    format_markdown,
    format_row,
    main,
    parse_instructions,
    read_baseline,
    sum_instructions,
)

_SUMMARY_DUMP = """\
version: 1
creator: callgrind-3.22.0
events: Ir
fn=main
0 12
summary: 1000000
"""

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


class ParseInstructionsTest(unittest.TestCase):
    def test_reads_summary_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dump = _write(Path(tmp) / "valgrind-callgrind.123", _SUMMARY_DUMP)
            self.assertEqual(parse_instructions(dump), 1000000)

    def test_falls_back_to_totals_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dump = _write(Path(tmp) / "valgrind-callgrind.123", _TOTALS_DUMP)
            self.assertEqual(parse_instructions(dump), 250000)

    def test_reads_first_field_of_multi_event_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dump = _write(Path(tmp) / "valgrind-callgrind.123", "events: Ir Dr Dw\nsummary: 4200 100 50\n")
            self.assertEqual(parse_instructions(dump), 4200)

    def test_returns_none_without_a_total(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dump = _write(Path(tmp) / "valgrind-callgrind.123", "version: 1\nfn=main\n0 12\n")
            self.assertIsNone(parse_instructions(dump))


class FindOutputFilesTest(unittest.TestCase):
    def test_matches_only_per_process_dumps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "valgrind-callgrind.1", _SUMMARY_DUMP)
            _write(root / "valgrind-callgrind.22", _SUMMARY_DUMP)
            # Report files this tool writes into the same directory, plus an
            # unrelated file, must never be treated as callgrind output.
            _write(root / INSTRUCTIONS_FILENAME, "1000000\n")
            _write(root / REPORT_MD_FILENAME, "| table |\n")
            _write(root / "some-other-output.txt", "noise\n")

            found = [Path(p).name for p in find_output_files(tmp)]
            self.assertEqual(found, ["valgrind-callgrind.1", "valgrind-callgrind.22"])


class SumInstructionsTest(unittest.TestCase):
    def test_sums_across_processes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "valgrind-callgrind.1", _SUMMARY_DUMP)
            _write(root / "valgrind-callgrind.2", _TOTALS_DUMP)
            self.assertEqual(sum_instructions(find_output_files(tmp)), 1250000)

    def test_skips_dumps_without_a_total(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "valgrind-callgrind.1", _SUMMARY_DUMP)
            _write(root / "valgrind-callgrind.2", "version: 1\n")
            self.assertEqual(sum_instructions(find_output_files(tmp)), 1000000)

    def test_raises_without_any_usable_dump(self) -> None:
        with self.assertRaises(ValueError):
            sum_instructions([])


class ReadBaselineTest(unittest.TestCase):
    def test_reads_integer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(Path(tmp) / "baseline.txt", "  1230982304\n")
            self.assertEqual(read_baseline(path), 1230982304)

    def test_rejects_non_integer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(Path(tmp) / "baseline.txt", "1.2e9\n")
            with self.assertRaises(ValueError):
                read_baseline(path)

    def test_rejects_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(Path(tmp) / "baseline.txt", "\n")
            with self.assertRaises(ValueError):
                read_baseline(path)


class BuildReportTest(unittest.TestCase):
    @staticmethod
    def _report(measured: int, baseline: int, tolerance_pct: float = 5.0) -> Report:
        return build_report("target", measured, baseline, "pkg/baseline.txt", tolerance_pct)

    def test_increase_within_tolerance_passes(self) -> None:
        report = self._report(measured=104, baseline=100)
        self.assertEqual(report["status"], STATUS_PASS)
        self.assertEqual(report["delta"], 4)
        self.assertAlmostEqual(report["delta_pct"], 4.0)

    def test_increase_beyond_tolerance_is_a_regression(self) -> None:
        self.assertEqual(self._report(measured=106, baseline=100)["status"], STATUS_REGRESSION)

    def test_tolerance_boundary_passes(self) -> None:
        self.assertEqual(self._report(measured=105, baseline=100)["status"], STATUS_PASS)

    def test_large_improvement_flags_a_stale_baseline(self) -> None:
        report = self._report(measured=80, baseline=100)
        self.assertEqual(report["status"], STATUS_STALE_BASELINE)
        self.assertEqual(report["delta"], -20)

    def test_unrecorded_baseline_does_not_pass_silently(self) -> None:
        # A freshly added baseline file holds 0 until a real run fills it in.
        report = self._report(measured=1000, baseline=0)
        self.assertEqual(report["status"], STATUS_UNRECORDED)
        self.assertEqual(report["cpu_instructions"], 1000)
        self.assertEqual(report["delta"], 0)
        self.assertEqual(report["delta_pct"], 0.0)

    def test_carries_label_and_baseline_file(self) -> None:
        report = self._report(measured=100, baseline=100)
        self.assertEqual(report["label"], "target")
        self.assertEqual(report["baseline_file"], "pkg/baseline.txt")


class FormatTest(unittest.TestCase):
    def test_row_renders_every_column(self) -> None:
        report = build_report("my_target", 1050, 1000, "pkg/baseline.txt", 5.0)
        self.assertEqual(
            format_row(report),
            "| `my_target` | 1,050 | 1,000 | +50 (+5.00%) | ±5.00% | ✅ pass |",
        )

    def test_rows_of_several_reports_share_one_header(self) -> None:
        # The shape the CI comment relies on when merging multiple targets.
        reports = [
            build_report("first", 1050, 1000, "a/baseline.txt", 5.0),
            build_report("second", 900, 1000, "b/baseline.txt", 5.0),
        ]
        table = "\n".join([TABLE_HEADER, *(format_row(r) for r in reports)])
        self.assertEqual(len(table.splitlines()), 4)
        self.assertIn("| `first` |", table)
        self.assertIn("| `second` |", table)

    def test_markdown_is_a_standalone_table(self) -> None:
        markdown = format_markdown(build_report("my_target", 1050, 1000, "pkg/baseline.txt", 5.0))
        self.assertTrue(markdown.startswith(TABLE_HEADER))
        self.assertIn("| `my_target` |", markdown)
        self.assertIn("Baseline file: `pkg/baseline.txt`", markdown)


class MainTest(unittest.TestCase):
    @staticmethod
    def _output_dir(tmp: str, *dumps: tuple[int, str]) -> str:
        for pid, content in dumps:
            _write(Path(tmp) / f"valgrind-callgrind.{pid}", content)
        return tmp

    def test_writes_instructions_file_without_a_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._output_dir(tmp, (1, _SUMMARY_DUMP), (2, _TOTALS_DUMP))

            self.assertEqual(main(["--output-dir", tmp]), 0)

            self.assertEqual((Path(tmp) / INSTRUCTIONS_FILENAME).read_text(), "1250000\n")
            self.assertFalse((Path(tmp) / REPORT_JSON_FILENAME).exists())

    def test_fails_when_no_callgrind_output_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(main(["--output-dir", tmp]), 1)

    def test_passes_within_tolerance_and_writes_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._output_dir(tmp, (1, _SUMMARY_DUMP))
            baseline = _write(Path(tmp) / "baseline.txt", "980000\n")

            exit_code = main(
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
                    "5",
                ]
            )

            self.assertEqual(exit_code, 0)
            report = json.loads((Path(tmp) / REPORT_JSON_FILENAME).read_text())
            self.assertEqual(report["status"], STATUS_PASS)
            self.assertEqual(report["label"], "my_target")
            self.assertEqual(report["cpu_instructions"], 1000000)
            self.assertEqual(report["baseline"], 980000)
            self.assertEqual(report["baseline_file"], "pkg/baseline.txt")
            self.assertIn("pkg/baseline.txt", (Path(tmp) / REPORT_MD_FILENAME).read_text())

    def test_fails_on_regression_beyond_tolerance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._output_dir(tmp, (1, _SUMMARY_DUMP))
            baseline = _write(Path(tmp) / "baseline.txt", "900000\n")

            exit_code = main(["--output-dir", tmp, "--instructions-baseline", str(baseline), "--tolerance-pct", "5"])

            self.assertEqual(exit_code, 1)
            report = json.loads((Path(tmp) / REPORT_JSON_FILENAME).read_text())
            self.assertEqual(report["status"], STATUS_REGRESSION)

    def test_tolerance_can_be_widened_to_accept_a_regression(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._output_dir(tmp, (1, _SUMMARY_DUMP))
            baseline = _write(Path(tmp) / "baseline.txt", "900000\n")

            exit_code = main(["--output-dir", tmp, "--instructions-baseline", str(baseline), "--tolerance-pct", "20"])

            self.assertEqual(exit_code, 0)

    def test_stale_baseline_warns_but_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._output_dir(tmp, (1, _SUMMARY_DUMP))
            baseline = _write(Path(tmp) / "baseline.txt", "2000000\n")

            exit_code = main(["--output-dir", tmp, "--instructions-baseline", str(baseline), "--tolerance-pct", "5"])

            self.assertEqual(exit_code, 0)
            report = json.loads((Path(tmp) / REPORT_JSON_FILENAME).read_text())
            self.assertEqual(report["status"], STATUS_STALE_BASELINE)

    def test_fails_on_missing_baseline_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._output_dir(tmp, (1, _SUMMARY_DUMP))
            missing = str(Path(tmp) / "does-not-exist.txt")

            self.assertEqual(main(["--output-dir", tmp, "--instructions-baseline", missing]), 1)

    def test_fails_on_an_unrecorded_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._output_dir(tmp, (1, _SUMMARY_DUMP))
            baseline = _write(Path(tmp) / "baseline.txt", "0\n")

            self.assertEqual(main(["--output-dir", tmp, "--instructions-baseline", str(baseline)]), 1)

            report = json.loads((Path(tmp) / REPORT_JSON_FILENAME).read_text())
            self.assertEqual(report["status"], STATUS_UNRECORDED)
            self.assertEqual(report["cpu_instructions"], 1000000)

    def test_fails_on_malformed_baseline_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._output_dir(tmp, (1, _SUMMARY_DUMP))
            baseline = _write(Path(tmp) / "baseline.txt", "not a number\n")

            self.assertEqual(main(["--output-dir", tmp, "--instructions-baseline", str(baseline)]), 1)


if __name__ == "__main__":
    unittest.main()
