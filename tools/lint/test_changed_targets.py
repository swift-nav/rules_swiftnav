#!/usr/bin/env python3
"""Tests for changed_targets.py

Run with Bazel:
    bazel test //tools/lint:test_changed_targets
"""

import io
import subprocess
import unittest
from pathlib import Path
from unittest import mock

import tools.lint.changed_targets as changed_targets
from tools.lint.changed_targets import (
    QUERY_PARTIAL_EXIT_CODE,
    SOURCE_EXTENSIONS,
    QueryError,
    bazel_query,
    main,
    owning_targets,
    parse_args,
    query_labels,
    source_files,
)


def completed(
    returncode: int, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["bazel", "query"], returncode=returncode, stdout=stdout, stderr=stderr
    )


class TestParseArgs(unittest.TestCase):
    def test_base_is_required(self):
        with self.assertRaises(SystemExit):
            parse_args([])

    def test_defaults(self):
        args = parse_args(["--base", "origin/master"])
        self.assertEqual(args.base, "origin/master")
        self.assertEqual(args.extensions, list(SOURCE_EXTENSIONS))

    def test_extensions_override(self):
        args = parse_args(["--base", "abc", "--extensions", "cc", "h"])
        self.assertEqual(args.extensions, ["cc", "h"])


class TestSourceFiles(unittest.TestCase):
    def test_keeps_only_source_extensions(self):
        files = ["a/b.cc", "a/b.h", "a/BUILD.bazel", "MODULE.bazel", "x/y.py"]
        self.assertEqual(
            source_files(files, SOURCE_EXTENSIONS, []), ["a/b.cc", "a/b.h"]
        )

    def test_drops_ignored_directories(self):
        files = ["third_party/lib/x.cc", "third_party_ext/x.cc", "src/x.cc"]
        self.assertEqual(
            source_files(files, SOURCE_EXTENSIONS, ["third_party"]),
            ["third_party_ext/x.cc", "src/x.cc"],
        )

    def test_extension_match_is_exact(self):
        """`.hxx` must not match `.h` and a bare `h` file is not a header."""
        self.assertEqual(source_files(["a.hxx", "h"], ["h"], []), [])


class TestOwningTargets(unittest.TestCase):
    def test_no_files_runs_no_query(self):
        def fail(expression):
            raise AssertionError(f"unexpected query: {expression}")

        self.assertEqual(owning_targets([], fail), [])

    def test_no_owner_stops_after_first_query(self):
        queries = []

        def run(expression):
            queries.append(expression)
            return []

        self.assertEqual(owning_targets(["a/orphan.cc"], run), [])
        self.assertEqual(queries, ["same_pkg_direct_rdeps(set(a/orphan.cc))"])

    def test_direct_owners_are_not_expanded(self):
        """A cc_library with sources lints its own files; its consumers are not linted."""
        answers = {
            "same_pkg_direct_rdeps(set(common/src/area_id.cc))": ["//common:common"],
            'set(//common:common) - kind("^cc_.* rule$", set(//common:common)) '
            '+ attr("srcs", "^\\[\\]$", kind("cc_library rule", set(//common:common)))': [],
            'kind("^cc_(library|binary|test) rule$", set(//common:common))': [
                "//common:common"
            ],
        }
        self.assertEqual(
            owning_targets(["common/src/area_id.cc"], lambda q: answers[q]),
            ["//common:common"],
        )

    def test_filegroup_and_header_only_owners_are_expanded(self):
        answers = {
            "same_pkg_direct_rdeps(set(a/x.h b/y.cc))": [
                "//a:hdrs_only",
                "//b:test.srcs",
            ],
            'set(//a:hdrs_only //b:test.srcs) - kind("^cc_.* rule$", set(//a:hdrs_only //b:test.srcs)) '
            '+ attr("srcs", "^\\[\\]$", kind("cc_library rule", set(//a:hdrs_only //b:test.srcs)))': [
                "//a:hdrs_only",
                "//b:test.srcs",
            ],
            "same_pkg_direct_rdeps(set(//a:hdrs_only //b:test.srcs))": [
                "//a:bin",
                "//b:test",
            ],
            'kind("^cc_(library|binary|test) rule$", set(//a:bin //a:hdrs_only //b:test //b:test.srcs))': [
                "//b:test",
                "//a:hdrs_only",
                "//a:bin",
            ],
        }
        self.assertEqual(
            owning_targets(["a/x.h", "b/y.cc"], lambda q: answers[q]),
            ["//a:bin", "//a:hdrs_only", "//b:test"],
        )


class TestQueryLabels(unittest.TestCase):
    def test_success_returns_labels(self):
        self.assertEqual(
            query_labels(completed(0, "//a:a\n//b:b\n")), ["//a:a", "//b:b"]
        )

    def test_partial_result_is_not_an_error(self):
        """Exit 3 is how a changed file that no target owns reaches us; dropping it must not fail CI."""
        with mock.patch("sys.stderr", new=io.StringIO()) as stderr:
            self.assertEqual(
                query_labels(
                    completed(QUERY_PARTIAL_EXIT_CODE, "//a:a\n", "skipped x\n")
                ),
                ["//a:a"],
            )
        self.assertIn("skipped x", stderr.getvalue())

    def test_other_failure_raises(self):
        with mock.patch("sys.stderr", new=io.StringIO()):
            with self.assertRaises(QueryError) as raised:
                query_labels(completed(1, stderr="boom\n"))
        self.assertEqual(raised.exception.returncode, 1)


class TestBazelQuery(unittest.TestCase):
    def run_query(self, expression: str) -> subprocess.CompletedProcess:
        recorded = {}

        def fake_run(command, **kwargs):
            recorded["command"] = command
            query_file = command[-1].removeprefix("--query_file=")
            recorded["expression"] = Path(query_file).read_text()
            return completed(0, "//a:a\n")

        with mock.patch.object(subprocess, "run", side_effect=fake_run):
            bazel_query(Path("/workspace"))(expression)
        return recorded

    def test_expression_goes_to_a_file_not_argv(self):
        """A large pull request exceeds MAX_ARG_STRLEN if the expression is an argument."""
        expression = "same_pkg_direct_rdeps(set(%s))" % " ".join(
            f"pkg/file{index}.cc" for index in range(20000)
        )
        recorded = self.run_query(expression)
        self.assertEqual(recorded["expression"], expression)
        self.assertNotIn(expression, recorded["command"])
        self.assertTrue(recorded["command"][-1].startswith("--query_file="))

    def test_query_file_is_removed(self):
        recorded = self.run_query("//a:a")
        query_file = recorded["command"][-1].removeprefix("--query_file=")
        self.assertFalse(Path(query_file).exists())


class TestMain(unittest.TestCase):
    def run_main(self, run_query):
        with (
            mock.patch.object(
                changed_targets, "changed_files", return_value=["a/x.cc"]
            ),
            mock.patch.object(changed_targets, "ignored_directories", return_value=[]),
            mock.patch.object(changed_targets, "bazel_query", return_value=run_query),
            mock.patch("sys.stdout", new=io.StringIO()) as stdout,
            mock.patch("sys.stderr", new=io.StringIO()),
        ):
            return main(["--base", "origin/master"]), stdout.getvalue()

    def test_query_failure_propagates_exit_code(self):
        """A returncode of 0 here would let CI lint nothing while staying green."""

        def run(expression):
            raise QueryError(37)

        returncode, stdout = self.run_main(run)
        self.assertEqual(returncode, 37)
        self.assertEqual(stdout, "")

    def test_targets_are_printed_to_stdout(self):
        answers = {
            "same_pkg_direct_rdeps(set(a/x.cc))": ["//a:a"],
            'set(//a:a) - kind("^cc_.* rule$", set(//a:a)) '
            '+ attr("srcs", "^\\[\\]$", kind("cc_library rule", set(//a:a)))': [],
            'kind("^cc_(library|binary|test) rule$", set(//a:a))': ["//a:a"],
        }
        returncode, stdout = self.run_main(lambda expression: answers[expression])
        self.assertEqual(returncode, 0)
        self.assertEqual(stdout, "//a:a\n")


if __name__ == "__main__":
    unittest.main()
