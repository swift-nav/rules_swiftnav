#!/usr/bin/env python3
"""Tests for merge_cppcheck_xml.py

Run with Bazel:
    bazel test //tools/...
"""

import json
import os
import sys
import tempfile
import unittest
import unittest.mock
import xml.etree.ElementTree as ET
from pathlib import Path

from tools.lint.bep import files_from_bep
from tools.lint.merge_cppcheck_xml import (
    CPPCHECK_XML_SUFFIX,
    main,
    merge_reports,
    parse_xml_report,
    write_merged_report,
)


class TestReportFilesFromBep(unittest.TestCase):
    """Selecting cppcheck reports out of a build event stream."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_bep(self, events: list) -> Path:
        """Write a list of event dicts as a newline-delimited BEP JSON file."""
        bep_file = self.p / "bep.json"
        with open(bep_file, "w") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")
        return bep_file

    def _reports(self, bep_file: Path, workspace_root: Path) -> list:
        return files_from_bep(
            build_event_json_file=bep_file,
            workspace_root=workspace_root,
            suffix=CPPCHECK_XML_SUFFIX,
        )

    def test_selects_files_matching_cppcheck_suffix(self):
        """Files ending in the cppcheck XML suffix are selected."""
        bep_file = self._write_bep(
            [
                {
                    "namedSetOfFiles": {
                        "files": [
                            {
                                "name": "target.AspectRulesLintCppCheck.xml",
                                "pathPrefix": [
                                    "bazel-out",
                                    "k8-fastbuild",
                                    "bin",
                                    "pkg",
                                ],
                            }
                        ]
                    }
                }
            ]
        )

        files = self._reports(bep_file, self.p)

        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].name.endswith(CPPCHECK_XML_SUFFIX))

    def test_ignores_non_matching_names(self):
        """Non-cppcheck files and non-namedSetOfFiles events are ignored."""
        bep_file = self._write_bep(
            [
                {
                    "namedSetOfFiles": {
                        "files": [
                            {
                                "name": "target.AspectRulesLintCppCheck.xml",
                                "pathPrefix": ["bazel-out", "pkg"],
                            },
                            {
                                "name": "target.AspectRulesLintClangTidy.report",
                                "pathPrefix": ["bazel-out", "pkg"],
                            },
                            {
                                "name": "unrelated.xml",
                                "pathPrefix": ["bazel-out", "pkg"],
                            },
                        ]
                    }
                },
                {"progress": {}},
            ]
        )

        files = self._reports(bep_file, self.p)

        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].name.endswith(CPPCHECK_XML_SUFFIX))

    def test_resolves_relative_paths_against_workspace_root(self):
        """A relative pathPrefix is joined against the workspace root."""
        bep_file = self._write_bep(
            [
                {
                    "namedSetOfFiles": {
                        "files": [
                            {
                                "name": "target.AspectRulesLintCppCheck.xml",
                                "pathPrefix": ["bazel-out", "pkg"],
                            }
                        ]
                    }
                }
            ]
        )

        files = self._reports(bep_file, self.p)

        self.assertEqual(
            files[0],
            self.p / "bazel-out" / "pkg" / "target.AspectRulesLintCppCheck.xml",
        )

    def test_keeps_absolute_paths_unchanged(self):
        """An already-absolute BEP path is not re-joined against the workspace root."""
        abs_prefix_dir = self.p / "abs" / "pkg"
        bep_file = self._write_bep(
            [
                {
                    "namedSetOfFiles": {
                        "files": [
                            {
                                "name": "target.AspectRulesLintCppCheck.xml",
                                "pathPrefix": [str(abs_prefix_dir)],
                            }
                        ]
                    }
                }
            ]
        )

        # A workspace root different from the prefix proves it is ignored here.
        files = self._reports(bep_file, Path("/some/other/root"))

        self.assertEqual(
            files[0], abs_prefix_dir / "target.AspectRulesLintCppCheck.xml"
        )


class TestParseXmlReport(unittest.TestCase):
    """Reading a single cppcheck report."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_parse_valid_xml(self):
        """A well-formed report parses into its root element."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<results version="3">
    <cppcheck version="2.10"/>
    <errors>
        <error id="unusedVariable" severity="style" msg="Unused variable: x">
            <location file="test.cpp" line="10" column="5"/>
        </error>
    </errors>
</results>"""

        test_file = self.p / "test.xml"
        test_file.write_text(xml_content)

        root = parse_xml_report(test_file)
        self.assertIsNotNone(root)
        self.assertEqual(root.tag, "results")
        self.assertEqual(root.get("version"), "3")

    def test_parse_xml_with_prefix(self):
        """cppcheck's progress chatter ahead of the declaration is skipped."""
        content = """Some informational message
Checking file.cpp...
<?xml version="1.0" encoding="UTF-8"?>
<results version="3">
    <errors/>
</results>"""

        test_file = self.p / "test_prefix.xml"
        test_file.write_text(content)

        root = parse_xml_report(test_file)
        self.assertIsNotNone(root)
        self.assertEqual(root.tag, "results")

    def test_parse_invalid_xml(self):
        """A file without an XML declaration yields None."""
        test_file = self.p / "invalid.xml"
        test_file.write_text("Not valid XML content")

        self.assertIsNone(parse_xml_report(test_file))

    def test_parse_malformed_xml(self):
        """An unparsable document yields None rather than raising."""
        test_file = self.p / "malformed.xml"
        test_file.write_text('<?xml version="1.0"?><results><errors></results>')

        self.assertIsNone(parse_xml_report(test_file))

    def test_parse_empty_file(self):
        """A zero-byte report yields None."""
        test_file = self.p / "empty.xml"
        test_file.touch()

        self.assertIsNone(parse_xml_report(test_file))

    def test_parse_nonexistent_file(self):
        """A report that was never written yields None."""
        self.assertIsNone(parse_xml_report(Path("/nonexistent/file.xml")))


class TestMergeReports(unittest.TestCase):
    """Combining several cppcheck reports."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _create_test_report(
        self, filename, errors_list, checkers_list=None, metrics_list=None
    ) -> Path:
        """Write a cppcheck report holding the given errors, checkers and metrics."""
        root = ET.Element("results", version="3")
        ET.SubElement(root, "cppcheck", version="2.10")

        errors = ET.SubElement(root, "errors")
        for error_data in errors_list:
            error = ET.SubElement(
                errors,
                "error",
                id=error_data["id"],
                severity=error_data.get("severity", "style"),
                msg=error_data["msg"],
            )
            if "file" in error_data:
                ET.SubElement(
                    error,
                    "location",
                    file=error_data["file"],
                    line=str(error_data["line"]),
                    column=str(error_data.get("column", 1)),
                )

        ET.SubElement(root, "safety")
        ET.SubElement(root, "critical-errors")

        checkers = ET.SubElement(root, "checkers-report")
        for checker_id in checkers_list or []:
            ET.SubElement(checkers, "checker", id=checker_id)

        metrics = ET.SubElement(root, "metrics")
        for metric_data in metrics_list or []:
            ET.SubElement(
                metrics,
                "metric",
                fileName=metric_data["fileName"],
                function=metric_data.get("function", ""),
                id=metric_data["id"],
                lineNumber=str(metric_data["lineNumber"]),
                value=str(metric_data["value"]),
            )

        filepath = self.p / filename
        ET.ElementTree(root).write(filepath, encoding="UTF-8", xml_declaration=True)
        return filepath

    def test_merge_single_report(self):
        """A single report is carried into the merged results."""
        report = self._create_test_report(
            "report1.xml",
            [
                {
                    "id": "unusedVariable",
                    "msg": "Unused variable: x",
                    "file": "test.cpp",
                    "line": 10,
                }
            ],
        )

        merged = merge_reports([report])

        self.assertIsNotNone(merged)
        self.assertEqual(merged.tag, "results")
        self.assertEqual(len(list(merged.find("errors"))), 1)

    def test_merge_multiple_reports(self):
        """Distinct errors from several reports are all kept."""
        report1 = self._create_test_report(
            "report1.xml",
            [
                {
                    "id": "unusedVariable",
                    "msg": "Unused variable: x",
                    "file": "test1.cpp",
                    "line": 10,
                }
            ],
        )
        report2 = self._create_test_report(
            "report2.xml",
            [
                {
                    "id": "uninitvar",
                    "msg": "Uninitialized variable: y",
                    "file": "test2.cpp",
                    "line": 20,
                }
            ],
        )

        merged = merge_reports([report1, report2])

        self.assertEqual(len(list(merged.find("errors"))), 2)

    def test_merge_deduplicates_identical_errors(self):
        """The same finding reported by two targets appears once."""
        error_data = {
            "id": "unusedVariable",
            "msg": "Unused variable: x",
            "file": "test.cpp",
            "line": 10,
        }
        report1 = self._create_test_report("report1.xml", [error_data])
        report2 = self._create_test_report("report2.xml", [error_data])

        merged = merge_reports([report1, report2])

        self.assertEqual(len(list(merged.find("errors"))), 1)

    def test_merge_different_errors_same_file(self):
        """Findings differing only in message and line stay separate."""
        report1 = self._create_test_report(
            "report1.xml",
            [
                {
                    "id": "unusedVariable",
                    "msg": "Unused variable: x",
                    "file": "test.cpp",
                    "line": 10,
                }
            ],
        )
        report2 = self._create_test_report(
            "report2.xml",
            [
                {
                    "id": "unusedVariable",
                    "msg": "Unused variable: y",
                    "file": "test.cpp",
                    "line": 20,
                }
            ],
        )

        merged = merge_reports([report1, report2])

        self.assertEqual(len(list(merged.find("errors"))), 2)

    def test_merge_keeps_append_order(self):
        """Errors keep the order the reports were merged in."""
        report1 = self._create_test_report(
            "report1.xml",
            [{"id": "zzz", "msg": "later", "file": "b.cpp", "line": 2}],
        )
        report2 = self._create_test_report(
            "report2.xml",
            [{"id": "aaa", "msg": "earlier", "file": "a.cpp", "line": 1}],
        )

        merged = merge_reports([report1, report2])

        self.assertEqual(
            [error.get("id") for error in merged.find("errors")], ["zzz", "aaa"]
        )

    def test_merge_checkers_deduplication(self):
        """Each checker is listed once across all reports."""
        report1 = self._create_test_report("report1.xml", [], ["checker1", "checker2"])
        report2 = self._create_test_report("report2.xml", [], ["checker2", "checker3"])

        merged = merge_reports([report1, report2])

        checker_ids = [
            c.get("id") for c in merged.find("checkers-report") if c.tag == "checker"
        ]
        self.assertEqual(sorted(checker_ids), ["checker1", "checker2", "checker3"])

    def test_merge_copies_cppcheck_metadata_once(self):
        """The cppcheck metadata element is taken from the first valid report."""
        report1 = self._create_test_report("report1.xml", [])
        report2 = self._create_test_report("report2.xml", [])

        merged = merge_reports([report1, report2])

        self.assertEqual(len(merged.findall("cppcheck")), 1)
        self.assertEqual(merged.find("cppcheck").get("version"), "2.10")

    def test_merge_empty_reports(self):
        """Reports without findings merge to an empty errors section."""
        report1 = self._create_test_report("report1.xml", [])
        report2 = self._create_test_report("report2.xml", [])

        merged = merge_reports([report1, report2])

        self.assertEqual(len(list(merged.find("errors"))), 0)

    def test_merge_handles_invalid_reports(self):
        """An unparsable report is skipped without losing the valid ones."""
        valid_report = self._create_test_report(
            "valid.xml",
            [
                {
                    "id": "unusedVariable",
                    "msg": "Unused variable: x",
                    "file": "test.cpp",
                    "line": 10,
                }
            ],
        )

        invalid_file = self.p / "invalid.xml"
        invalid_file.write_text("Not valid XML")

        merged = merge_reports([valid_report, invalid_file])

        self.assertEqual(len(list(merged.find("errors"))), 1)

    def test_merge_handles_missing_and_empty_reports(self):
        """Targets with no lintable sources produce no XML, which is not an error."""
        valid_report = self._create_test_report(
            "valid.xml",
            [
                {
                    "id": "unusedVariable",
                    "msg": "Unused variable: x",
                    "file": "test.cpp",
                    "line": 10,
                }
            ],
        )
        empty_report = self.p / "empty.xml"
        empty_report.touch()

        merged = merge_reports([self.p / "ghost.xml", empty_report, valid_report])

        self.assertEqual(len(list(merged.find("errors"))), 1)

    def test_merge_metrics_section(self):
        """Metrics from every report are appended."""
        report1 = self._create_test_report(
            "report1.xml",
            [],
            None,
            [
                {
                    "fileName": "test1.cpp",
                    "function": "foo",
                    "id": "HISCall",
                    "lineNumber": 10,
                    "value": 5,
                }
            ],
        )
        report2 = self._create_test_report(
            "report2.xml",
            [],
            None,
            [
                {
                    "fileName": "test2.cpp",
                    "function": "bar",
                    "id": "HISParam",
                    "lineNumber": 20,
                    "value": 3,
                }
            ],
        )

        merged = merge_reports([report1, report2])

        metrics = merged.find("metrics")
        self.assertIsNotNone(metrics)
        self.assertEqual(len(list(metrics)), 2)

    def test_merge_multiple_metrics_same_report(self):
        """All metrics of one report are kept."""
        report = self._create_test_report(
            "report.xml",
            [],
            None,
            [
                {
                    "fileName": "test.cpp",
                    "function": "foo",
                    "id": "HISCall",
                    "lineNumber": 10,
                    "value": 5,
                },
                {
                    "fileName": "test.cpp",
                    "function": "foo",
                    "id": "HISParam",
                    "lineNumber": 10,
                    "value": 3,
                },
                {
                    "fileName": "test.cpp",
                    "function": "bar",
                    "id": "cyclomaticComplexity",
                    "lineNumber": 20,
                    "value": 8,
                },
            ],
        )

        merged = merge_reports([report])

        self.assertEqual(len(list(merged.find("metrics"))), 3)

    def test_merge_metrics_are_not_deduplicated(self):
        """Identical metrics are audit evidence per target, so both are kept."""
        metric = {
            "fileName": "test.cpp",
            "function": "foo",
            "id": "HISCall",
            "lineNumber": 10,
            "value": 5,
        }
        report1 = self._create_test_report("report1.xml", [], None, [metric])
        report2 = self._create_test_report("report2.xml", [], None, [metric])

        merged = merge_reports([report1, report2])

        self.assertEqual(len(list(merged.find("metrics"))), 2)

    def test_merge_empty_metrics_section(self):
        """Empty metrics sections merge to an empty section."""
        report1 = self._create_test_report("report1.xml", [], None, [])
        report2 = self._create_test_report("report2.xml", [], None, [])

        merged = merge_reports([report1, report2])

        metrics = merged.find("metrics")
        self.assertIsNotNone(metrics)
        self.assertEqual(len(list(metrics)), 0)


class TestWriteMergedReport(unittest.TestCase):
    """Writing the consolidated report."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _merged_root(self) -> ET.Element:
        merged_root = ET.Element("results", version="3")
        ET.SubElement(merged_root, "cppcheck", version="2.10")
        errors = ET.SubElement(merged_root, "errors")
        error = ET.SubElement(errors, "error", id="test", msg="Test error")
        ET.SubElement(error, "location", file="test.cpp", line="10")
        return merged_root

    def test_write_merged_report(self):
        """The merged report is written as a valid XML document."""
        output_file = self.p / "output.xml"
        write_merged_report(self._merged_root(), output_file)

        self.assertTrue(output_file.exists())

        root = ET.parse(output_file).getroot()
        self.assertEqual(root.tag, "results")
        self.assertEqual(root.get("version"), "3")

    def test_write_declares_the_encoding(self):
        """Downstream cppcheck tools expect the XML declaration."""
        output_file = self.p / "output.xml"
        write_merged_report(self._merged_root(), output_file)

        self.assertTrue(
            output_file.read_text().startswith("<?xml version='1.0' encoding='UTF-8'?>")
        )

    def test_write_creates_the_output_directory(self):
        """The report can be written into a directory that does not exist yet."""
        output_file = self.p / "cppcheck-output" / "merged-report.xml"
        write_merged_report(self._merged_root(), output_file)

        self.assertTrue(output_file.exists())


class TestMain(unittest.TestCase):
    """The command line entry point."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name)
        self.output_file = self.p / "merged.xml"

    def tearDown(self):
        self.tmp.cleanup()

    def _write_report(self, path: Path, error_id: str) -> None:
        """Write a minimal cppcheck report with a single, identifiable error."""
        root = ET.Element("results", version="3")
        ET.SubElement(root, "cppcheck", version="2.10")
        errors = ET.SubElement(root, "errors")
        error = ET.SubElement(errors, "error", id=error_id, severity="style", msg="msg")
        ET.SubElement(error, "location", file="test.cpp", line="1", column="1")
        ET.SubElement(root, "safety")
        ET.SubElement(root, "critical-errors")
        ET.SubElement(root, "checkers-report")
        ET.SubElement(root, "metrics")
        path.parent.mkdir(parents=True, exist_ok=True)
        ET.ElementTree(root).write(path, encoding="UTF-8", xml_declaration=True)

    def _write_bep(self, path_prefix: list) -> Path:
        """Write a BEP file listing one cppcheck report under the given prefix."""
        bep_file = self.p / "bep.json"
        with open(bep_file, "w") as f:
            f.write(
                json.dumps(
                    {
                        "namedSetOfFiles": {
                            "files": [
                                {
                                    "name": "target.AspectRulesLintCppCheck.xml",
                                    "pathPrefix": path_prefix,
                                }
                            ]
                        }
                    }
                )
                + "\n"
            )
        return bep_file

    def _merged_error_ids(self) -> list:
        return [
            e.get("id") for e in ET.parse(self.output_file).getroot().find("errors")
        ]

    def _run(self, argv: list) -> int:
        with unittest.mock.patch.object(sys, "argv", ["merge_cppcheck_xml.py"] + argv):
            return main()

    def test_collects_the_reports_listed_in_the_bep(self):
        """The reports named in the build event file are merged."""
        self._write_report(
            self.p / "bazel-out" / "pkg" / "target.AspectRulesLintCppCheck.xml",
            "bepError",
        )
        bep_file = self._write_bep(["bazel-out", "pkg"])

        self._run(
            [
                "--build-event-json-file",
                str(bep_file),
                "--workspace-root",
                str(self.p),
                "--output-file",
                str(self.output_file),
            ]
        )

        self.assertIn("bepError", self._merged_error_ids())

    def test_workspace_root_resolves_relative_report_paths(self):
        """Relative BEP paths resolve against --workspace-root, not the cwd."""
        workspace = self.p / "workspace"
        self._write_report(
            workspace / "bazel-out" / "pkg" / "target.AspectRulesLintCppCheck.xml",
            "workspaceRootError",
        )
        bep_file = self._write_bep(["bazel-out", "pkg"])

        self._run(
            [
                "--build-event-json-file",
                str(bep_file),
                "--workspace-root",
                str(workspace),
                "--output-file",
                str(self.output_file),
            ]
        )

        self.assertIn("workspaceRootError", self._merged_error_ids())

    def test_workspace_root_defaults_to_the_current_directory(self):
        """Without --workspace-root the cwd stands in for the workspace root."""
        self._write_report(
            self.p / "bazel-out" / "pkg" / "target.AspectRulesLintCppCheck.xml",
            "cwdError",
        )
        bep_file = self._write_bep(["bazel-out", "pkg"])

        cwd = os.getcwd()
        os.chdir(self.p)
        try:
            self._run(
                [
                    "--build-event-json-file",
                    str(bep_file),
                    "--output-file",
                    str(self.output_file),
                ]
            )
        finally:
            os.chdir(cwd)

        self.assertIn("cwdError", self._merged_error_ids())

    def test_no_reports_returns_code_1(self):
        """A build event file listing no cppcheck reports is an error."""
        bep_file = self.p / "empty-bep.json"
        bep_file.write_text(json.dumps({"progress": {}}) + "\n")

        self.assertEqual(
            self._run(
                [
                    "--build-event-json-file",
                    str(bep_file),
                    "--output-file",
                    str(self.output_file),
                ]
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main()
