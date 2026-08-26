#!/usr/bin/env python3
"""Tests for lint.py

Run with Bazel:
    bazel test //tools/...
"""

import unittest
from pathlib import Path

from tools.lint.lint import (
    CLANG_TIDY,
    CPPCHECK,
    build_command,
    build_events_path,
    extract_command,
    merge_command,
    output_dir,
    parse_args,
    select_linters,
)

WORKSPACE = Path("/workspace")
BEP = Path("/tmp/bep.json")


class TestParseArgs(unittest.TestCase):
    def test_defaults(self):
        """No arguments lints everything with clang-tidy and no patches."""
        args = parse_args([])
        self.assertEqual(args.targets, ["//..."])
        self.assertEqual(args.linters, "clang-tidy")
        self.assertFalse(args.create_patches)
        self.assertFalse(args.apply_patches)

    def test_targets_are_variadic(self):
        """--targets accepts several targets."""
        args = parse_args(["--targets", "//a:b", "//c/..."])
        self.assertEqual(args.targets, ["//a:b", "//c/..."])

    def test_create_patches(self):
        """--create-patches does not imply applying them."""
        args = parse_args(["--create-patches"])
        self.assertTrue(args.create_patches)
        self.assertFalse(args.apply_patches)

    def test_apply_patches_implies_create_patches(self):
        """--apply-patches turns on patch creation as well."""
        args = parse_args(["--apply-patches"])
        self.assertTrue(args.create_patches)
        self.assertTrue(args.apply_patches)

    def test_linters_list(self):
        """--linters takes a comma-separated list."""
        args = parse_args(["--linters", "clang-tidy,cppcheck"])
        self.assertEqual(args.linters, "clang-tidy,cppcheck")


class TestSelectLinters(unittest.TestCase):
    def test_default_is_clang_tidy_only(self):
        """The default linter list resolves to clang-tidy alone."""
        self.assertEqual(select_linters(parse_args([]).linters), [CLANG_TIDY])

    def test_order_is_preserved(self):
        """Linters run in the order requested."""
        selected = select_linters("cppcheck,clang-tidy")
        self.assertEqual(
            [linter.name for linter in selected], ["cppcheck", "clang-tidy"]
        )

    def test_whitespace_and_empty_entries_are_ignored(self):
        """Spaces and stray commas do not produce unknown linters."""
        selected = select_linters(" clang-tidy , cppcheck,")
        self.assertEqual(
            [linter.name for linter in selected], ["clang-tidy", "cppcheck"]
        )

    def test_unknown_linter_exits(self):
        """An unknown linter name aborts."""
        with self.assertRaises(SystemExit):
            select_linters("clang-tidy,nosuchlinter")


class TestOutputPaths(unittest.TestCase):
    def test_clang_tidy_path_is_unchanged(self):
        """clang-tidy keeps the output directory current CI reads."""
        self.assertEqual(
            output_dir(WORKSPACE, CLANG_TIDY), Path("/workspace/clang-tidy-output")
        )

    def test_each_linter_gets_a_sibling_directory(self):
        """Other linters report next to, not into, the clang-tidy directory."""
        self.assertEqual(
            output_dir(WORKSPACE, CPPCHECK), Path("/workspace/cppcheck-output")
        )


class TestBuildCommand(unittest.TestCase):
    def test_clang_tidy_flags(self):
        """clang-tidy keeps the flag set the shell driver used."""
        self.assertEqual(
            build_command(CLANG_TIDY, ["//..."], BEP, create_patches=False),
            [
                "bazel",
                "build",
                "--build_event_json_file=/tmp/bep.json",
                "--remote_download_regex=.*AspectRulesLint.*",
                "--skip_incompatible_explicit_targets",
                "--aspects=//tools/lint:linters.bzl%clang_tidy",
                "--output_groups=rules_lint_machine",
                "--keep_going",
                "//...",
            ],
        )

    def test_create_patches_adds_the_fix_flags(self):
        """Patch creation asks for fixes and the patch output group."""
        command = build_command(CLANG_TIDY, ["//..."], BEP, create_patches=True)
        self.assertEqual(
            command[-3:],
            [
                "--@aspect_rules_lint//lint:fix",
                "--output_groups=rules_lint_patch",
                "//...",
            ],
        )

    def test_cppcheck_requests_its_aspect_and_both_output_groups(self):
        """cppcheck names its aspect and asks for the XML alongside the SARIF."""
        command = build_command(CPPCHECK, ["//a:b"], BEP, create_patches=False)
        self.assertIn("--aspects=//tools/lint:linters.bzl%cppcheck", command)
        self.assertIn("--output_groups=rules_lint_machine", command)
        self.assertIn("--output_groups=rules_lint_xml", command)

    def test_each_linter_requests_only_its_own_aspect(self):
        """A shared aspect would put one linter's findings in another's report."""
        for linter, own, other in (
            (CLANG_TIDY, "clang_tidy", "cppcheck"),
            (CPPCHECK, "cppcheck", "clang_tidy"),
        ):
            command = build_command(linter, ["//a:b"], BEP, create_patches=False)
            self.assertIn(f"--aspects=//tools/lint:linters.bzl%{own}", command)
            self.assertNotIn(f"--aspects=//tools/lint:linters.bzl%{other}", command)
            self.assertNotIn("--config=lint", command)

    def test_targets_come_last(self):
        """Targets follow the flags so bazel does not read them as flag values."""
        command = build_command(CPPCHECK, ["//a:b", "//c:d"], BEP, create_patches=False)
        self.assertEqual(command[-2:], ["//a:b", "//c:d"])


class TestExtractCommand(unittest.TestCase):
    def test_clang_tidy_report_path_is_unchanged(self):
        """The clang-tidy SARIF stays where current CI expects it."""
        self.assertEqual(
            extract_command(WORKSPACE, CLANG_TIDY, BEP),
            [
                "--build-event-json-file=/tmp/bep.json",
                "--bazel-output-path=/workspace",
                "--output-merged-sarif-file=/workspace/clang-tidy-output/merged-report.sarif",
                "--output-patch-folder=/workspace/clang-tidy-output/patches",
                "--exit-code=1",
            ],
        )

    def test_each_linter_gets_its_own_sarif(self):
        """Linters do not share a SARIF file, which reviewdog would mislabel."""
        clang_tidy = extract_command(WORKSPACE, CLANG_TIDY, BEP)
        cppcheck = extract_command(WORKSPACE, CPPCHECK, BEP)
        self.assertIn(
            "--output-merged-sarif-file=/workspace/cppcheck-output/merged-report.sarif",
            cppcheck,
        )
        self.assertNotEqual(clang_tidy, cppcheck)

    def test_exit_code_is_requested(self):
        """The driver's exit code comes from extract_lint_results."""
        self.assertIn("--exit-code=1", extract_command(WORKSPACE, CPPCHECK, BEP))


class TestMergeCommand(unittest.TestCase):
    def test_clang_tidy_has_nothing_to_merge(self):
        """A linter without XML reports skips the merge step."""
        self.assertIsNone(merge_command(WORKSPACE, CLANG_TIDY, BEP))

    def test_cppcheck_xml_is_merged_next_to_its_sarif(self):
        """The merged XML lands in the linter's own output directory."""
        self.assertEqual(
            merge_command(WORKSPACE, CPPCHECK, BEP),
            [
                "--build-event-json-file=/tmp/bep.json",
                "--workspace-root=/workspace",
                "--output-file=/workspace/cppcheck-output/merged-report.xml",
            ],
        )

    def test_merging_follows_the_xml_output_group(self):
        """Any linter asking for the XML output group gets its reports merged."""
        (linter,) = select_linters("clang-tidy")
        linter = linter._replace(output_groups=("rules_lint_machine", "rules_lint_xml"))
        self.assertIsNotNone(merge_command(WORKSPACE, linter, BEP))


class TestIncompatibleTargets(unittest.TestCase):
    """An explicitly named incompatible target must not fail the build."""

    def test_skip_incompatible_explicit_targets_is_passed(self):
        """Callers may name a Windows or fuzzer target through --targets."""
        for linter in (CLANG_TIDY, CPPCHECK):
            self.assertIn(
                "--skip_incompatible_explicit_targets",
                build_command(linter, ["//..."], BEP, False),
            )


class TestBuildEventsPath(unittest.TestCase):
    """Resolving the --build-events template."""

    def test_relative_path_resolves_against_workspace(self):
        """A relative template lands inside the workspace, not the cwd."""
        self.assertEqual(
            build_events_path(WORKSPACE, CPPCHECK, "cppcheck-output/events.json"),
            Path("/workspace/cppcheck-output/events.json"),
        )

    def test_absolute_path_is_kept(self):
        """An absolute template is used as given."""
        self.assertEqual(
            build_events_path(WORKSPACE, CPPCHECK, "/tmp/events.json"),
            Path("/tmp/events.json"),
        )

    def test_linter_placeholder_is_substituted(self):
        """The {linter} placeholder keeps several linters from colliding."""
        self.assertEqual(
            build_events_path(WORKSPACE, CLANG_TIDY, "out/{linter}-events.json"),
            Path("/workspace/out/clang-tidy-events.json"),
        )
        self.assertEqual(
            build_events_path(WORKSPACE, CPPCHECK, "out/{linter}-events.json"),
            Path("/workspace/out/cppcheck-events.json"),
        )

    def test_defaults_to_none(self):
        """Without the flag the driver keeps using a temporary file."""
        self.assertIsNone(parse_args([]).build_events)

    def test_flag_is_parsed(self):
        """The flag is exposed as build_events."""
        self.assertEqual(
            parse_args(["--build-events", "e.json"]).build_events, "e.json"
        )


if __name__ == "__main__":
    unittest.main()
