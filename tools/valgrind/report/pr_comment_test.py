#!/usr/bin/env python3
"""Tests for pr_comment.py

Run with Bazel:
    bazel test //tools/valgrind/report/...
"""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tools.valgrind.report.metrics import Report, build_metric, build_report, write_report
from tools.valgrind.report.pr_comment import (
    DEFAULT_MARKER,
    METRIC_HEADER,
    SUMMARY_HEADER,
    format_comment,
    format_percent,
    main,
)


def _report(label: str, value: float, baseline: float, extra_metrics: list | None = None) -> Report:
    metrics = [build_metric("cpu_instructions", "CPU instructions", "", value, baseline, 5.0)]
    metrics += extra_metrics or []
    return build_report(label, f"{label}/baseline.txt", metrics)


class FormatPercentTest(unittest.TestCase):
    def test_keeps_decimals_for_ordinary_deltas(self) -> None:
        self.assertEqual(format_percent(42.0), "+42.00%")
        self.assertEqual(format_percent(-42.0), "-42.00%")

    def test_drops_decimals_once_the_delta_is_huge(self) -> None:
        # An unfilled placeholder baseline yields percentages this large.
        self.assertEqual(format_percent(4200.0), "+4,200%")


class FormatCommentTest(unittest.TestCase):
    def test_single_target_summary_and_details(self) -> None:
        comment = format_comment([_report("run_replay", 1050, 1000)], DEFAULT_MARKER, "Title", "abc1234")

        self.assertTrue(comment.startswith(DEFAULT_MARKER))
        self.assertIn("## Title", comment)
        self.assertIn(SUMMARY_HEADER, comment)
        self.assertIn('| `run_replay` | <abbr title="within tolerance">✅</abbr> | +5.00% |', comment)
        self.assertIn("<summary>✅ run_replay</summary>", comment)
        self.assertIn(METRIC_HEADER, comment)
        self.assertIn("| CPU instructions | 1,050 | 1,000 | +50 (+5.00%) |", comment)
        self.assertIn("Baseline: `run_replay/baseline.txt` · tolerance ±5.00%", comment)
        self.assertIn("Commit: `abc1234`", comment)

    def test_status_symbol_carries_a_tooltip_instead_of_a_legend(self) -> None:
        comment = format_comment([_report("run_replay", 2000, 1000)], DEFAULT_MARKER, "Title", None)

        self.assertIn('<abbr title="regression: grew past the tolerance">❌</abbr>', comment)
        self.assertNotIn("within tolerance ·", comment)
        self.assertNotIn("Commit:", comment)

    def test_several_metrics_become_several_rows(self) -> None:
        heap = build_metric("peak_heap_mb", "Peak memory (heap)", "MB", 15.405, 15.400, 5.0)
        comment = format_comment([_report("run_replay", 1000, 1000, [heap])], DEFAULT_MARKER, "Title", None)

        self.assertIn("| CPU instructions | 1,000 | 1,000 | +0 (+0.00%) |", comment)
        self.assertIn("| Peak memory (heap) | 15.405 MB | 15.400 MB | +0.005 MB (+0.03%) |", comment)
        # The summary column still tracks CPU only.
        self.assertIn("| +0.00% |", comment)

    def test_several_targets_share_one_summary_but_get_their_own_block(self) -> None:
        reports = [_report("zeta", 900, 1000), _report("alpha", 2000, 1000)]

        comment = format_comment(reports, DEFAULT_MARKER, "Title", None)

        self.assertEqual(comment.count(SUMMARY_HEADER), 1)
        self.assertEqual(comment.count("<details>"), 2)
        self.assertLess(comment.index("| `alpha` |"), comment.index("| `zeta` |"))

    def test_target_without_the_summary_metric_renders_a_dash(self) -> None:
        heap = build_metric("peak_heap_mb", "Peak memory (heap)", "MB", 15.405, 15.400, 5.0)
        memory_only = build_report("massif_target", "pkg/baseline.txt", [heap])

        comment = format_comment([memory_only], DEFAULT_MARKER, "Title", None)

        self.assertIn("| — |", comment)

    def test_differing_tolerances_are_not_claimed_to_be_one(self) -> None:
        loose = build_metric("peak_heap_mb", "Peak memory (heap)", "MB", 15.4, 15.4, 20.0)

        comment = format_comment([_report("run_replay", 1000, 1000, [loose])], DEFAULT_MARKER, "Title", None)

        self.assertIn("tolerance per metric", comment)


class MainTest(unittest.TestCase):
    def test_merges_every_report_given(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first, second = Path(tmp) / "a.json", Path(tmp) / "b.json"
            write_report(_report("first", 1050, 1000), first)
            write_report(_report("second", 990, 1000), second)

            out = io.StringIO()
            with redirect_stdout(out):
                exit_code = main([str(first), str(second), "--commit", "deadbee"])

            self.assertEqual(exit_code, 0)
            comment = out.getvalue()
            self.assertIn("| `first` |", comment)
            self.assertIn("| `second` |", comment)
            self.assertEqual(comment.count(SUMMARY_HEADER), 1)

    def test_fails_on_an_unreadable_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(main([str(Path(tmp) / "missing.json")]), 1)


if __name__ == "__main__":
    unittest.main()
