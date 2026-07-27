#!/usr/bin/env python3
"""Tests for callgrind_comment.py

Run with Bazel:
    bazel test //tools/valgrind/...
"""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tools.valgrind.callgrind_comment import (
    DEFAULT_MARKER,
    TABLE_HEADER,
    format_comment,
    main,
)
from tools.valgrind.callgrind_report import build_report


def _write_report(path: Path, label: str, measured: int, baseline: int) -> Path:
    report = build_report(label, measured, baseline, f"{label}/baseline.txt", 5.0)
    path.write_text(json.dumps(report))
    return path


class FormatCommentTest(unittest.TestCase):
    def test_single_report_renders_one_row(self) -> None:
        report = build_report("only_target", 1050, 1000, "pkg/baseline.txt", 5.0)

        comment = format_comment([report], DEFAULT_MARKER, "Title", "abc1234")

        self.assertTrue(comment.startswith(DEFAULT_MARKER))
        self.assertIn("## Title", comment)
        self.assertIn(TABLE_HEADER, comment)
        self.assertIn("| `only_target` | 1,050 | 1,000 | +50 (+5.00%) | ±5.00% | ✅ pass |", comment)
        self.assertIn("Baseline for `only_target`: `pkg/baseline.txt`", comment)
        self.assertIn("Commit: `abc1234`", comment)

    def test_several_reports_share_one_table_sorted_by_label(self) -> None:
        reports = [
            build_report("zeta", 900, 1000, "z/baseline.txt", 5.0),
            build_report("alpha", 2000, 1000, "a/baseline.txt", 5.0),
        ]

        comment = format_comment(reports, DEFAULT_MARKER, "Title", None)

        self.assertEqual(comment.count(TABLE_HEADER), 1)
        self.assertLess(comment.index("| `alpha` |"), comment.index("| `zeta` |"))
        self.assertIn("❌ regression", comment)
        self.assertIn("⚠️ baseline stale", comment)
        self.assertNotIn("Commit:", comment)


class MainTest(unittest.TestCase):
    def test_merges_every_report_given(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first = _write_report(Path(tmp) / "a.json", "first", 1050, 1000)
            second = _write_report(Path(tmp) / "b.json", "second", 990, 1000)

            out = io.StringIO()
            with redirect_stdout(out):
                exit_code = main([str(first), str(second), "--commit", "deadbee"])

            self.assertEqual(exit_code, 0)
            comment = out.getvalue()
            self.assertIn("| `first` |", comment)
            self.assertIn("| `second` |", comment)
            self.assertEqual(comment.count(TABLE_HEADER), 1)

    def test_fails_on_an_unreadable_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(main([str(Path(tmp) / "missing.json")]), 1)


if __name__ == "__main__":
    unittest.main()
