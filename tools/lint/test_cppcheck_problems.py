#!/usr/bin/env python3
"""Tests for cppcheck_problems.py

Run with Bazel:
    bazel test //tools/...
"""

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tools.lint.cppcheck_problems import format_problems, main

REPORT = """<?xml version="1.0" encoding="UTF-8"?>
<results version="2">
  <cppcheck version="2.16"/>
  <errors>
    <error id="misra-cpp-2023-7.0.2" severity="style" msg="Implicit conversion">
      <location file="src/a.cc" line="12" column="4"/>
    </error>
    <error id="missingInclude" severity="information" msg="No location"/>
    <error id="nullPointer" severity="error" msg="Null pointer">
      <location file="src/b.cc" line="3"/>
      <location file="src/b.cc" line="1" column="2"/>
    </error>
  </errors>
</results>
"""


class TestFormatProblems(unittest.TestCase):
    """Turning a cppcheck XML report into problemMatcher lines."""

    def test_one_line_per_error_with_a_location(self):
        """Errors without a location are dropped, the others become lines."""
        self.assertEqual(
            format_problems(REPORT),
            [
                "src/a.cc:12:4: [misra-cpp-2023-7.0.2] style: Implicit conversion",
                "src/b.cc:3:0: [nullPointer] error: Null pointer",
            ],
        )

    def test_empty_report_has_no_problems(self):
        """A report without errors yields nothing."""
        self.assertEqual(format_problems("<results><errors/></results>"), [])


class TestMain(unittest.TestCase):
    """Command line behaviour."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_prints_problems_of_the_report(self):
        """The report's problems are printed to stdout."""
        report = self.p / "merged-report.xml"
        report.write_text(REPORT)
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(main([str(report)]), 0)
        self.assertIn("src/a.cc:12:4: [misra-cpp-2023-7.0.2]", out.getvalue())

    def test_relative_report_is_resolved_from_working_directory(self):
        """Under bazel run, relative paths are relative to where it was run."""
        (self.p / "merged-report.xml").write_text(REPORT)
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(
                ["merged-report.xml"], environ={"BUILD_WORKING_DIRECTORY": str(self.p)}
            )
        self.assertEqual(code, 0)
        self.assertIn("src/b.cc:3:0", out.getvalue())

    def test_missing_report_fails(self):
        """A report that does not exist is an error, not an empty result."""
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(main([str(self.p / "absent.xml")]), 1)
        self.assertIn("absent.xml", err.getvalue())


if __name__ == "__main__":
    unittest.main()
