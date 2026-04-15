#!/usr/bin/env python3
"""Tests for extract_lint_results.py

Run with Bazel:
    bazel test //tools/...
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.lint.extract_lint_results import (
    collect_and_merge_sarif,
    collect_patches,
    deduplicate_runs,
    extract_files_from_bep,
    extract_rule_ids,
    filter_errors_only,
    filter_external_dependencies,
    main,
    merge_sarif_reports,
    normalize_path,
    normalize_sarif_paths,
)


def _write_sarif(path: Path, results: list, tool_name: str = "ClangTidy") -> None:
    """Write a minimal SARIF file with the given results."""
    data = {
        "version": "2.1.0",
        "runs": [{"tool": {"driver": {"name": tool_name}}, "results": results}],
    }
    with open(path, "w") as f:
        json.dump(data, f)


def _file(name: str, path_prefix: list) -> dict:
    """Build a single BEP file entry."""
    return {"name": name, "pathPrefix": path_prefix}


def _named_set_event(*files: dict) -> str:
    """Return a BEP namedSetOfFiles JSON line for the given file entries."""
    return json.dumps({"namedSetOfFiles": {"files": list(files)}}) + "\n"


def _write_bep(bep_path: Path, file_paths: list) -> None:
    """Write a BEP JSON file with namedSetOfFiles entries for the given paths."""
    with open(bep_path, "w") as f:
        for file_path in file_paths:
            parts = str(file_path).split("/")
            f.write(_named_set_event(_file(name=parts[-1], path_prefix=parts[:-1])))


class TestExtractFilesFromBep(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_named_set_entries_returns_empty(self):
        """BEP file with no namedSetOfFiles events yields no files."""
        bep = self.p / "bep.json"
        with open(bep, "w") as f:
            f.write(json.dumps({"started": {"uuid": "abc"}}) + "\n")

        self.assertEqual(
            extract_files_from_bep(bep, bazel_output_path=None, ext=".report"), []
        )

    def test_returns_files_matching_extension(self):
        """Only files whose name ends with the requested extension are returned."""
        bep = self.p / "bep.json"
        bep.write_text(
            _named_set_event(
                _file(name="foo.report", path_prefix=["/tmp"]),
                _file(name="foo.report.exit_code", path_prefix=["/tmp"]),
                _file(name="other.txt", path_prefix=["/tmp"]),
            )
        )

        result = extract_files_from_bep(bep, bazel_output_path=None, ext=".report")
        self.assertEqual(result, [Path("/tmp/foo.report")])

    def test_collects_from_multiple_events(self):
        """Files from every namedSetOfFiles event in the BEP file are collected."""
        bep = self.p / "bep.json"
        with open(bep, "w") as f:
            f.write(_named_set_event(_file(name="a.report", path_prefix=["/tmp"])))
            f.write(json.dumps({"started": {"uuid": "skip"}}) + "\n")
            f.write(_named_set_event(_file(name="b.report", path_prefix=["/tmp"])))

        result = extract_files_from_bep(bep, bazel_output_path=None, ext=".report")
        self.assertEqual(len(result), 2)

    def test_relative_path_resolved_with_bazel_output_path(self):
        """A relative path from the BEP is joined with bazel_output_path."""
        bep = self.p / "bep.json"
        bep.write_text(_named_set_event(_file(name="foo.report", path_prefix=["bazel-out", "k8-fastbuild", "bin"])))

        result = extract_files_from_bep(
            bep, bazel_output_path=Path("/workspace"), ext=".report"
        )
        self.assertEqual(
            result, [Path("/workspace/bazel-out/k8-fastbuild/bin/foo.report")]
        )

    def test_absolute_path_not_modified_by_bazel_output_path(self):
        """An absolute path in the BEP is used as-is regardless of bazel_output_path."""
        bep = self.p / "bep.json"
        bep.write_text(_named_set_event(_file(name="foo.report", path_prefix=["/absolute", "path"])))

        result = extract_files_from_bep(
            bep, bazel_output_path=Path("/workspace"), ext=".report"
        )
        self.assertEqual(result, [Path("/absolute/path/foo.report")])

    def test_invalid_json_line_exits_with_code_1(self):
        """Invalid JSON lines in the BEP file cause exit with code 1."""
        bep = self.p / "bep.json"
        with open(bep, "w") as f:
            f.write("not valid json\n")
            f.write(_named_set_event(_file(name="foo.report", path_prefix=["/tmp"])))

        with self.assertRaises(SystemExit) as ctx:
            extract_files_from_bep(bep, bazel_output_path=None, ext=".report")
        self.assertEqual(ctx.exception.code, 1)


class TestNormalizePath(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_execroot_main_with_numeric_hash(self):
        """Bazel path with numeric hash segment before execroot is stripped."""
        self.assertEqual(
            normalize_path("../../../902/execroot/_main/lib/file.h"),
            "lib/file.h",
        )

    def test_execroot_double_underscore_main(self):
        """Bazel path with __main__ workspace name is stripped."""
        self.assertEqual(
            normalize_path("../../execroot/__main__/integration/main.cc"),
            "integration/main.cc",
        )

    def test_non_execroot_path_strips_leading_dotdot(self):
        """Paths without execroot have leading ../ segments removed."""
        self.assertEqual(
            normalize_path("../../../some/other/path.cc"),
            "some/other/path.cc",
        )

    def test_already_relative_path_unchanged(self):
        """A path with no leading ../ and no execroot is returned unchanged."""
        self.assertEqual(
            normalize_path("lib/src/file.cc"),
            "lib/src/file.cc",
        )

    def test_virtual_includes_symlink_resolved_to_real_source_path(self):
        """_virtual_includes path is resolved via symlink to the real source file.

        This mirrors the strip_include_prefix case: Bazel creates a symlink forest
        under _virtual_includes/ pointing into the real include/ directory.
        Clang-tidy reports the symlink path; we must map it back to the actual
        source path so reviewdog can match the PR diff.
        """
        # Real source file: <workspace>/mylib/include/mylib/header.h
        real_include_dir = self.workspace / "mylib" / "include"
        real_include_dir.mkdir(parents=True)
        real_file = real_include_dir / "mylib" / "header.h"
        real_file.parent.mkdir(parents=True)
        real_file.touch()

        # Bazel symlink: bazel-out/.../bin/mylib/_virtual_includes/mylib/
        #                -> <workspace>/mylib/include/
        virtual_includes_dir = (
            self.workspace
            / "bazel-out"
            / "k8-fastbuild"
            / "bin"
            / "mylib"
            / "_virtual_includes"
            / "mylib"
        )
        virtual_includes_dir.parent.mkdir(parents=True)
        virtual_includes_dir.symlink_to(real_include_dir)

        uri = "bazel-out/k8-fastbuild/bin/mylib/_virtual_includes/mylib/mylib/header.h"
        result = normalize_path(uri, workspace_root=self.workspace)

        self.assertEqual(result, "mylib/include/mylib/header.h")

    def test_virtual_includes_without_workspace_root_returned_as_is(self):
        """Without workspace_root, _virtual_includes paths are not resolved."""
        uri = "bazel-out/k8-fastbuild/bin/pkg/_virtual_includes/pkg/pkg/file.h"
        self.assertEqual(normalize_path(uri, workspace_root=None), uri)

    def test_virtual_includes_broken_symlink_falls_back_to_original(self):
        """If the _virtual_includes symlink does not exist, the path is kept unchanged."""
        uri = "bazel-out/k8-fastbuild/bin/pkg/_virtual_includes/pkg/pkg/file.h"
        # workspace_root is provided but the symlink does not exist on disk
        result = normalize_path(uri, workspace_root=self.workspace)
        self.assertEqual(result, uri)

    def test_execroot_path_with_virtual_includes_is_fully_resolved(self):
        """execroot prefix is stripped first, then _virtual_includes symlink is resolved."""
        real_include_dir = self.workspace / "pkg" / "include"
        real_include_dir.mkdir(parents=True)
        (real_include_dir / "pkg").mkdir()
        (real_include_dir / "pkg" / "file.h").touch()

        virtual_dir = (
            self.workspace
            / "bazel-out"
            / "k8-fastbuild"
            / "bin"
            / "pkg"
            / "_virtual_includes"
            / "pkg"
        )
        virtual_dir.parent.mkdir(parents=True)
        virtual_dir.symlink_to(real_include_dir)

        uri = "../../execroot/_main/bazel-out/k8-fastbuild/bin/pkg/_virtual_includes/pkg/pkg/file.h"
        result = normalize_path(uri, workspace_root=self.workspace)
        self.assertEqual(result, "pkg/include/pkg/file.h")


class TestNormalizeSarifPaths(unittest.TestCase):
    def test_normalizes_uri_and_removes_uri_base_id(self):
        """execroot URI is normalized and uriBaseId is removed."""
        run = {
            "results": [
                {
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {
                                    "uri": "../../../902/execroot/_main/lib/file.h",
                                    "uriBaseId": "%SRCROOT%",
                                }
                            }
                        }
                    ]
                }
            ]
        }
        artifact = normalize_sarif_paths(run)["results"][0]["locations"][0][
            "physicalLocation"
        ]["artifactLocation"]
        self.assertEqual(artifact["uri"], "lib/file.h")
        self.assertNotIn("uriBaseId", artifact)

    def test_all_results_are_normalized(self):
        """Every result in the run has its path normalized."""
        run = {
            "results": [
                {
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": "../../execroot/_main/a.cc"}
                            }
                        }
                    ]
                },
                {
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": "../../execroot/_main/b.cc"}
                            }
                        }
                    ]
                },
            ]
        }
        normalized = normalize_sarif_paths(run)
        self.assertEqual(
            normalized["results"][0]["locations"][0]["physicalLocation"][
                "artifactLocation"
            ]["uri"],
            "a.cc",
        )
        self.assertEqual(
            normalized["results"][1]["locations"][0]["physicalLocation"][
                "artifactLocation"
            ]["uri"],
            "b.cc",
        )

    def test_run_without_results_key_is_unchanged(self):
        """A run dict without a 'results' key is returned without error."""
        run = {"tool": {"driver": {"name": "ClangTidy"}}}
        result = normalize_sarif_paths(run)
        self.assertNotIn("results", result)

    def test_result_without_physical_location_is_unchanged(self):
        """A result with no physicalLocation is left intact."""
        run = {"results": [{"message": {"text": "no location"}}]}
        result = normalize_sarif_paths(run)
        self.assertEqual(result["results"][0]["message"]["text"], "no location")


class TestFilterExternalDependencies(unittest.TestCase):
    def _result(self, uri: str) -> dict:
        return {"locations": [{"physicalLocation": {"artifactLocation": {"uri": uri}}}]}

    def test_external_results_removed(self):
        """Results whose primary URI starts with 'external/' are dropped."""
        run = {"results": [
            self._result("external/dep+/include/dep/file.h"),
            self._result("lib/src/file.cc"),
        ]}
        result = filter_external_dependencies(run)
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(
            result["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"],
            "lib/src/file.cc",
        )

    def test_all_external_results_emptied(self):
        """A run whose only results are external dependencies is emptied."""
        run = {"results": [
            self._result("external/dep2+/include/dep2/file.hpp"),
        ]}
        result = filter_external_dependencies(run)
        self.assertEqual(result["results"], [])

    def test_run_without_results_key_unchanged(self):
        """A run dict without a 'results' key is returned without error."""
        run = {"tool": {"driver": {"name": "ClangTidy"}}}
        result = filter_external_dependencies(run)
        self.assertNotIn("results", result)

    def test_result_without_location_kept(self):
        """A result with no locations (no URI to check) is kept."""
        run = {"results": [{"message": {"text": "no location"}}]}
        result = filter_external_dependencies(run)
        self.assertEqual(len(result["results"]), 1)


class TestExtractRuleIds(unittest.TestCase):
    def _run(self, results):
        return {"tool": {"driver": {"name": "ClangTidy", "rules": []}}, "results": results}

    def test_rule_id_extracted_from_message_bracket_suffix(self):
        """ruleId is parsed from the trailing [check-name] in the message text."""
        run = self._run([{"level": "warning", "message": {"text": "some issue [misc-include-cleaner]"}}])
        result = extract_rule_ids(run)
        self.assertEqual(result["results"][0]["ruleId"], "misc-include-cleaner")

    def test_existing_rule_id_not_overwritten(self):
        """Results that already have ruleId are left unchanged."""
        run = self._run([{"ruleId": "existing-rule", "message": {"text": "msg [other-rule]"}}])
        result = extract_rule_ids(run)
        self.assertEqual(result["results"][0]["ruleId"], "existing-rule")

    def test_message_without_bracket_suffix_skipped(self):
        """Results whose message has no [check-name] suffix get no ruleId added."""
        run = self._run([{"level": "warning", "message": {"text": "no check name here"}}])
        result = extract_rule_ids(run)
        self.assertNotIn("ruleId", result["results"][0])

    def test_rules_array_populated_in_driver(self):
        """Extracted check names are added to tool.driver.rules with defaultConfiguration.level."""
        run = self._run([
            {"level": "warning", "message": {"text": "issue [modernize-use-nullptr]"}},
            {"level": "error", "message": {"text": "issue [misc-include-cleaner]"}},
        ])
        result = extract_rule_ids(run)
        rules_by_id = {r["id"]: r for r in result["tool"]["driver"]["rules"]}
        self.assertIn("modernize-use-nullptr", rules_by_id)
        self.assertIn("misc-include-cleaner", rules_by_id)
        self.assertEqual(rules_by_id["modernize-use-nullptr"]["defaultConfiguration"]["level"], "warning")
        self.assertEqual(rules_by_id["misc-include-cleaner"]["defaultConfiguration"]["level"], "error")

    def test_duplicate_check_names_appear_once_in_rules(self):
        """The same check name appearing in multiple results is deduplicated in rules."""
        run = self._run([
            {"message": {"text": "a [misc-include-cleaner]"}},
            {"message": {"text": "b [misc-include-cleaner]"}},
        ])
        result = extract_rule_ids(run)
        ids = [r["id"] for r in result["tool"]["driver"]["rules"]]
        self.assertEqual(ids.count("misc-include-cleaner"), 1)

    def test_merge_sarif_reports_populates_rule_ids(self):
        """End-to-end: merge_sarif_reports fills in ruleId from message text."""
        with tempfile.TemporaryDirectory() as tmp:
            inp = Path(tmp) / "a.sarif"
            data = {
                "version": "2.1.0",
                "runs": [{"tool": {"driver": {"name": "ClangTidy"}}, "results": [
                    {"level": "warning",
                     "message": {"text": "nested namespaces can be concatenated [modernize-concat-nested-namespaces]"},
                     "locations": [{"physicalLocation": {"artifactLocation": {"uri": "src/file.cc"},
                                                         "region": {"startLine": 5, "startColumn": 1}}}]},
                ]}],
            }
            with open(inp, "w") as f:
                json.dump(data, f)
            out = Path(tmp) / "out.sarif"
            merge_sarif_reports([inp], out)
            result = json.loads(out.read_text())
            self.assertEqual(result["runs"][0]["results"][0]["ruleId"], "modernize-concat-nested-namespaces")


class TestFilterErrorsOnly(unittest.TestCase):
    def test_keeps_only_error_level_results(self):
        """warning, note, and none results are removed; error results are kept."""
        run = {
            "results": [
                {"level": "error", "message": {"text": "err"}},
                {"level": "warning", "message": {"text": "warn"}},
                {"level": "note", "message": {"text": "note"}},
                {"level": "none", "message": {"text": "none"}},
            ]
        }
        filtered = filter_errors_only(run)
        self.assertEqual(len(filtered["results"]), 1)
        self.assertEqual(filtered["results"][0]["level"], "error")

    def test_results_missing_level_field_are_removed(self):
        """Results without a 'level' key are excluded."""
        run = {
            "results": [
                {"message": {"text": "no level"}},
                {"level": "error", "message": {"text": "err"}},
            ]
        }
        filtered = filter_errors_only(run)
        self.assertEqual(len(filtered["results"]), 1)

    def test_run_without_results_key_is_returned_as_is(self):
        run = {"tool": {"driver": {"name": "tool"}}}
        result = filter_errors_only(run)
        self.assertNotIn("results", result)


class TestDeduplicateRuns(unittest.TestCase):
    def _result(self, uri, line, col, rule_id):
        return {
            "ruleId": rule_id,
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": uri},
                        "region": {"startLine": line, "startColumn": col},
                    }
                }
            ],
        }

    def test_no_duplicates_unchanged(self):
        """Runs with no duplicate results are returned as-is."""
        runs = [
            {
                "results": [
                    self._result("a.h", 10, 1, "rule1"),
                    self._result("b.h", 20, 1, "rule2"),
                ]
            }
        ]
        result = deduplicate_runs(runs)
        self.assertEqual(len(result[0]["results"]), 2)

    def test_same_result_across_runs_deduplicated(self):
        """The same (uri, line, col, ruleId) in two runs keeps only the first occurrence."""
        dup = self._result("include/foo.h", 45, 3, "google-explicit-constructor")
        runs = [{"results": [dup]}, {"results": [dup]}]
        result = deduplicate_runs(runs)
        total = sum(len(r["results"]) for r in result)
        self.assertEqual(total, 1)

    def test_different_rules_same_location_both_kept(self):
        """Two different rules at the same location are both kept."""
        runs = [
            {
                "results": [
                    self._result("foo.h", 10, 1, "rule-a"),
                    self._result("foo.h", 10, 1, "rule-b"),
                ]
            }
        ]
        result = deduplicate_runs(runs)
        self.assertEqual(len(result[0]["results"]), 2)

    def test_same_rule_different_lines_both_kept(self):
        """Same rule on different lines are both kept."""
        runs = [
            {
                "results": [
                    self._result("foo.h", 10, 1, "rule-a"),
                    self._result("foo.h", 20, 1, "rule-a"),
                ]
            }
        ]
        result = deduplicate_runs(runs)
        self.assertEqual(len(result[0]["results"]), 2)

    def test_run_without_results_key_unchanged(self):
        """A run with no 'results' key is left intact."""
        runs = [{"tool": {"driver": {"name": "ClangTidy"}}}]
        result = deduplicate_runs(runs)
        self.assertNotIn("results", result[0])

    def test_multiple_duplicate_runs_mirrors_real_header_scenario(self):
        """Mirrors the real scenario: same header warning in N .cc compilation units."""
        header_warn = self._result(
            "mylib/include/mylib/header1.h",
            45,
            3,
            "google-explicit-constructor",
        )
        other = self._result(
            "mylib/include/mylib/header2.h",
            129,
            1,
            "readability-convert-member-functions-to-static",
        )
        runs = [
            {"results": [header_warn, other]},
            {"results": [header_warn]},
            {"results": [header_warn]},
        ]
        result = deduplicate_runs(runs)
        total = sum(len(r["results"]) for r in result)
        self.assertEqual(total, 2)


class TestMergeSarifReports(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_empty_input_creates_valid_empty_sarif(self):
        """No input files --> output is a valid SARIF 2.1.0 file with empty runs."""
        out = self.p / "out.sarif"
        count = merge_sarif_reports([], out)
        self.assertEqual(count, 0)
        self.assertTrue(out.exists())
        data = json.loads(out.read_text())
        self.assertEqual(data["version"], "2.1.0")
        self.assertEqual(data["runs"], [])

    def test_single_file_runs_are_included(self):
        """Runs from a single input file appear in the output."""
        inp = self.p / "a.sarif"
        _write_sarif(inp, [{"message": {"text": "issue"}}], tool_name="ToolA")
        out = self.p / "out.sarif"
        merge_sarif_reports([inp], out)
        data = json.loads(out.read_text())
        self.assertEqual(len(data["runs"]), 1)
        self.assertEqual(data["runs"][0]["tool"]["driver"]["name"], "ToolA")

    def test_multiple_files_runs_are_combined(self):
        """Runs from all input files are combined into the output."""
        inp1, inp2 = self.p / "a.sarif", self.p / "b.sarif"
        _write_sarif(
            inp1,
            [
                {
                    "message": {"text": "e1"},
                    "ruleId": "check-1",
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": "a.cc"},
                                "region": {"startLine": 1, "startColumn": 1},
                            }
                        }
                    ],
                }
            ],
            tool_name="Tool1",
        )
        _write_sarif(
            inp2,
            [
                {
                    "message": {"text": "e2"},
                    "ruleId": "check-2",
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": "b.cc"},
                                "region": {"startLine": 2, "startColumn": 1},
                            }
                        }
                    ],
                }
            ],
            tool_name="Tool2",
        )
        out = self.p / "out.sarif"
        merge_sarif_reports([inp1, inp2], out)
        data = json.loads(out.read_text())
        names = {r["tool"]["driver"]["name"] for r in data["runs"]}
        self.assertEqual(names, {"Tool1", "Tool2"})

    def test_returns_total_result_count(self):
        """Return value equals total number of results across all input files."""
        inp1, inp2 = self.p / "a.sarif", self.p / "b.sarif"
        _write_sarif(inp1, [{"message": {"text": "e1"}}, {"message": {"text": "e2"}}])
        _write_sarif(inp2, [{"message": {"text": "e3"}}])
        out = self.p / "out.sarif"
        self.assertEqual(merge_sarif_reports([inp1, inp2], out), 3)

    def test_empty_files_are_skipped(self):
        """Zero-byte files are silently skipped."""
        valid = self.p / "valid.sarif"
        empty = self.p / "empty.sarif"
        _write_sarif(valid, [{"message": {"text": "issue"}}], tool_name="T")
        empty.touch()
        out = self.p / "out.sarif"
        merge_sarif_reports([valid, empty], out)
        data = json.loads(out.read_text())
        self.assertEqual(len(data["runs"]), 1)

    def test_nonexistent_files_are_skipped(self):
        """Non-existent paths in the input list are silently skipped."""
        out = self.p / "out.sarif"
        merge_sarif_reports([self.p / "ghost.sarif"], out)
        data = json.loads(out.read_text())
        self.assertEqual(data["runs"], [])

    def test_invalid_json_file_exits_with_code_1(self):
        """Files containing invalid JSON cause exit with code 1."""
        bad = self.p / "bad.sarif"
        bad.write_text("not json")
        good = self.p / "good.sarif"
        _write_sarif(good, [{"message": {"text": "issue"}}], tool_name="Good")
        out = self.p / "out.sarif"
        with self.assertRaises(SystemExit) as ctx:
            merge_sarif_reports([bad, good], out)
        self.assertEqual(ctx.exception.code, 1)

    def test_schema_uri_preserved_from_first_valid_file(self):
        """The $schema field from the first valid input file appears in the output."""
        inp = self.p / "a.sarif"
        data = {
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "version": "2.1.0",
            "runs": [],
        }
        with open(inp, "w") as f:
            json.dump(data, f)
        out = self.p / "out.sarif"
        merge_sarif_reports([inp], out)
        result = json.loads(out.read_text())
        self.assertEqual(
            result["$schema"], "https://json.schemastore.org/sarif-2.1.0.json"
        )

    def test_only_errors_filters_non_error_results(self):
        """With only_errors=True, warnings and notes are removed from the output."""
        inp = self.p / "a.sarif"
        _write_sarif(
            inp,
            [
                {"level": "error", "message": {"text": "err"}},
                {"level": "warning", "message": {"text": "warn"}},
            ],
        )
        out = self.p / "out.sarif"
        count = merge_sarif_reports([inp], out, only_errors=True)
        data = json.loads(out.read_text())
        self.assertEqual(count, 1)
        self.assertEqual(len(data["runs"][0]["results"]), 1)
        self.assertEqual(data["runs"][0]["results"][0]["level"], "error")

    def test_bazel_execroot_paths_are_normalized(self):
        """Bazel execroot URIs in results are rewritten to repo-relative paths."""
        inp = self.p / "a.sarif"
        data = {
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {"driver": {"name": "T"}},
                    "results": [
                        {
                            "locations": [
                                {
                                    "physicalLocation": {
                                        "artifactLocation": {
                                            "uri": "../../../902/execroot/_main/lib/file.cc",
                                            "uriBaseId": "%SRCROOT%",
                                        }
                                    }
                                }
                            ]
                        }
                    ],
                }
            ],
        }
        with open(inp, "w") as f:
            json.dump(data, f)
        out = self.p / "out.sarif"
        merge_sarif_reports([inp], out)
        result = json.loads(out.read_text())
        artifact = result["runs"][0]["results"][0]["locations"][0]["physicalLocation"][
            "artifactLocation"
        ]
        self.assertEqual(artifact["uri"], "lib/file.cc")
        self.assertNotIn("uriBaseId", artifact)

    def test_output_directory_is_created_if_missing(self):
        """The output file's parent directory is created automatically."""
        inp = self.p / "a.sarif"
        _write_sarif(inp, [])
        out = self.p / "subdir" / "nested" / "out.sarif"
        merge_sarif_reports([inp], out)
        self.assertTrue(out.exists())

    def test_workspace_root_resolves_virtual_includes_in_sarif(self):
        """merge_sarif_reports resolves _virtual_includes symlinks when workspace_root is given.

        Reproduces the strip_include_prefix case: Bazel creates _virtual_includes/
        symlinks. The merged SARIF must contain the real source path so reviewdog
        can match it against the PR diff.
        """
        # Real source file
        real_include_dir = self.p / "mylib" / "include"
        (real_include_dir / "mylib").mkdir(parents=True)
        (real_include_dir / "mylib" / "header.h").touch()

        # Bazel virtual-includes symlink
        virtual_dir = (
            self.p
            / "bazel-out"
            / "k8-fastbuild"
            / "bin"
            / "mylib"
            / "_virtual_includes"
            / "mylib"
        )
        virtual_dir.parent.mkdir(parents=True)
        virtual_dir.symlink_to(real_include_dir)

        virtual_uri = "bazel-out/k8-fastbuild/bin/mylib/_virtual_includes/mylib/mylib/header.h"
        inp = self.p / "a.sarif"
        data = {
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {"driver": {"name": "ClangTidy"}},
                    "results": [
                        {
                            "level": "warning",
                            "locations": [
                                {
                                    "physicalLocation": {
                                        "artifactLocation": {"uri": virtual_uri}
                                    }
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        with open(inp, "w") as f:
            json.dump(data, f)

        out = self.p / "out.sarif"
        merge_sarif_reports([inp], out, workspace_root=self.p)

        result = json.loads(out.read_text())
        uri = result["runs"][0]["results"][0]["locations"][0]["physicalLocation"][
            "artifactLocation"
        ]["uri"]
        self.assertEqual(uri, "mylib/include/mylib/header.h")

    def test_runs_without_results_are_excluded(self):
        """Runs that have no results (e.g. clang-tidy found nothing) are dropped from the merged output."""
        inp = self.p / "mixed.sarif"
        data = {
            "version": "2.1.0",
            "runs": [
                {"tool": {"driver": {"name": "ClangTidy"}}},
                {"tool": {"driver": {"name": "ClangTidy"}}, "results": []},
                {
                    "tool": {"driver": {"name": "ClangTidy"}},
                    "results": [
                        {
                            "level": "warning",
                            "message": {"text": "issue"},
                            "locations": [
                                {
                                    "physicalLocation": {
                                        "artifactLocation": {"uri": "foo.cc"}
                                    }
                                }
                            ],
                        }
                    ],
                },
            ],
        }
        with open(inp, "w") as f:
            json.dump(data, f)
        out = self.p / "out.sarif"
        count = merge_sarif_reports([inp], out)
        result = json.loads(out.read_text())
        self.assertEqual(count, 1)
        self.assertEqual(len(result["runs"]), 1)
        self.assertEqual(len(result["runs"][0]["results"]), 1)

    def test_runs_emptied_by_deduplication_are_excluded(self):
        """Runs whose results are all duplicates of earlier runs are dropped from the merged output."""
        result = {
            "level": "warning",
            "message": {"text": "issue"},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": "foo.cc"},
                        "region": {"startLine": 10, "startColumn": 1},
                    }
                }
            ],
            "ruleId": "some-check",
        }
        inp1 = self.p / "a.sarif"
        inp2 = self.p / "b.sarif"
        _write_sarif(inp1, [result])
        _write_sarif(inp2, [result])  # exact duplicate — deduplication empties this run
        out = self.p / "out.sarif"
        merge_sarif_reports([inp1, inp2], out)
        data = json.loads(out.read_text())
        self.assertEqual(len(data["runs"]), 1)


class TestCollectAndMergeSarif(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_finds_report_files_and_merges_them(self):
        """Report files discovered via BEP are merged into the output SARIF file."""
        report = self.p / "target.AspectRulesLintClangTidy.report"
        _write_sarif(report, [{"message": {"text": "issue"}}], tool_name="ClangTidy")
        bep = self.p / "bep.json"
        _write_bep(bep, [report])
        out = self.p / "out.sarif"

        count = collect_and_merge_sarif(bep, out, bazel_output_path=self.p)

        self.assertTrue(out.exists())
        data = json.loads(out.read_text())
        self.assertEqual(len(data["runs"]), 1)
        self.assertEqual(count, 1)

    def test_no_report_files_creates_empty_sarif(self):
        """If the BEP lists no .report files, an empty but valid SARIF file is written."""
        bep = self.p / "bep.json"
        with open(bep, "w") as f:
            f.write(json.dumps({"started": {"uuid": "x"}}) + "\n")
        out = self.p / "out.sarif"

        count = collect_and_merge_sarif(bep, out, bazel_output_path=self.p)

        data = json.loads(out.read_text())
        self.assertEqual(data["runs"], [])
        self.assertEqual(count, 0)


class TestCollectPatches(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_nonempty_patch_files_are_copied(self):
        """Non-empty patch files listed in the BEP are copied to the output folder."""
        patch_file = self.p / "fix.patch"
        patch_file.write_text("--- a/file.cc\n+++ b/file.cc\n@@ -1 +1 @@\n-old\n+new\n")
        bep = self.p / "bep.json"
        _write_bep(bep, [patch_file])
        out_dir = self.p / "patches"

        collect_patches(bep, out_dir, bazel_output_path=self.p)

        self.assertTrue((out_dir / "fix.patch").exists())
        self.assertEqual((out_dir / "fix.patch").read_text(), patch_file.read_text())

    def test_empty_patch_files_are_skipped(self):
        """Zero-byte patch files are not copied to the output folder."""
        empty_patch = self.p / "empty.patch"
        empty_patch.touch()
        bep = self.p / "bep.json"
        _write_bep(bep, [empty_patch])
        out_dir = self.p / "patches"

        collect_patches(bep, out_dir, bazel_output_path=self.p)

        self.assertFalse((out_dir / "empty.patch").exists())

    def test_nonexistent_patch_files_are_skipped(self):
        """Patch file paths that don't exist are silently skipped."""
        bep = self.p / "bep.json"
        _write_bep(bep, [self.p / "ghost.patch"])
        out_dir = self.p / "patches"

        collect_patches(bep, out_dir, bazel_output_path=self.p)

        # Output dir may or may not be created; no files should be in it
        if out_dir.exists():
            self.assertEqual(list(out_dir.iterdir()), [])

    def test_output_directory_is_created_if_missing(self):
        """The output directory is created even if no patch files are copied."""
        patch_file = self.p / "a.patch"
        patch_file.write_text("diff content")
        bep = self.p / "bep.json"
        _write_bep(bep, [patch_file])
        out_dir = self.p / "new" / "nested" / "patches"

        collect_patches(bep, out_dir, bazel_output_path=self.p)

        self.assertTrue(out_dir.exists())

    def test_no_patch_files_in_bep_does_nothing(self):
        """A BEP with no .patch entries results in an empty output directory."""
        bep = self.p / "bep.json"
        with open(bep, "w") as f:
            f.write(
                json.dumps(
                    {
                        "namedSetOfFiles": {
                            "files": [
                                {"name": "foo.report", "pathPrefix": ["/tmp"]},
                            ]
                        }
                    }
                )
                + "\n"
            )
        out_dir = self.p / "patches"

        collect_patches(bep, out_dir, bazel_output_path=self.p)

        # Output dir is always created; it should be empty
        self.assertTrue(out_dir.exists())
        self.assertEqual(list(out_dir.iterdir()), [])


class TestMain(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_bep_with_sarif(self, num_results: int, levels: list = None) -> tuple:
        """Create a .report SARIF file and a BEP pointing to it. Returns (bep_path, output_path)."""
        if levels is None:
            results = [{"message": {"text": f"issue {i}"}} for i in range(num_results)]
        else:
            results = [
                {"level": lvl, "message": {"text": f"issue {i}"}}
                for i, lvl in enumerate(levels)
            ]
        report = self.p / "target.report"
        _write_sarif(report, results)
        bep = self.p / "bep.json"
        _write_bep(bep, [report])
        out = self.p / "merged.sarif"
        return bep, out

    def test_missing_bep_file_exits_with_code_1(self):
        """A non-existent --build-event-json-file causes exit with code 1."""
        with patch(
            "sys.argv",
            [
                "extract_lint_results.py",
                "--build-event-json-file",
                str(self.p / "missing.json"),
                "--bazel-output-path",
                str(self.p),
            ],
        ):
            with self.assertRaises(SystemExit) as ctx:
                main()
        self.assertEqual(ctx.exception.code, 1)

    def test_exit_code_triggered_when_errors_found(self):
        """--exit-code N causes sys.exit(N) when total results > 0."""
        bep, out = self._make_bep_with_sarif(num_results=2)
        with patch(
            "sys.argv",
            [
                "extract_lint_results.py",
                "--build-event-json-file",
                str(bep),
                "--bazel-output-path",
                str(self.p),
                "--output-merged-sarif-file",
                str(out),
                "--exit-code",
                "1",
            ],
        ):
            with self.assertRaises(SystemExit) as ctx:
                main()
        self.assertEqual(ctx.exception.code, 1)

    def test_exit_code_not_triggered_when_no_results(self):
        """--exit-code N does not call sys.exit when there are no results."""
        bep, out = self._make_bep_with_sarif(num_results=0)
        with patch(
            "sys.argv",
            [
                "extract_lint_results.py",
                "--build-event-json-file",
                str(bep),
                "--bazel-output-path",
                str(self.p),
                "--output-merged-sarif-file",
                str(out),
                "--exit-code",
                "1",
            ],
        ):
            main()  # must not raise

    def test_output_patch_folder_collects_patches(self):
        """--output-patch-folder causes non-empty patch files to be copied."""
        patch_file = self.p / "fix.patch"
        patch_file.write_text("--- a\n+++ b\n@@ -1 +1 @@\n")
        bep = self.p / "bep.json"
        _write_bep(bep, [patch_file])
        patch_out = self.p / "collected_patches"

        with patch(
            "sys.argv",
            [
                "extract_lint_results.py",
                "--build-event-json-file",
                str(bep),
                "--bazel-output-path",
                str(self.p),
                "--output-patch-folder",
                str(patch_out),
            ],
        ):
            main()

        self.assertTrue((patch_out / "fix.patch").exists())

    def test_no_output_file_argument_does_not_crash(self):
        """Omitting --output-merged-sarif-file is allowed and causes no crash."""
        bep = self.p / "bep.json"
        with open(bep, "w") as f:
            f.write(json.dumps({"started": {}}) + "\n")
        with patch(
            "sys.argv",
            [
                "extract_lint_results.py",
                "--build-event-json-file",
                str(bep),
                "--bazel-output-path",
                str(self.p),
            ],
        ):
            main()  # must not raise


if __name__ == "__main__":
    unittest.main()
