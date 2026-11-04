# Copyright (C) 2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

"""Tests for resolve_virtual_includes.py.

Run with Bazel:
    bazel test //tools/compile_commands:resolve_virtual_includes_test
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from tools.compile_commands.resolve_virtual_includes import (
    main,
    rewrite_include_flags,
    virtual_include_replacements,
)

# The Symlink actions of a test workspace, from `bazel aquery --output=jsonproto`.
AQUERY_FIXTURE = (
    Path(os.path.abspath(__file__)).parent / "testdata" / "aquery_symlinks.json"
)

FASTBUILD = "bazel-out/darwin_arm64-fastbuild/bin"
EXEC = "bazel-out/darwin_arm64-opt-exec/bin"

# The source headers of the fixture, relative to the workspace.
SOURCE_HEADERS = [
    "pkg_a/include/a/a.h",
    "pkg_b/b.h",
    "pkg_c/src/c.h",
    "pkg_d/d.h",
    "pkg_m/include/m/m.h",
    "third_party/inner/include/inner/inner.h",
]

VIRTUAL_A = f"{FASTBUILD}/pkg_a/_virtual_includes/a"
LINK_A = ("pkg_a/include/a/a.h", f"{VIRTUAL_A}/a/a.h")


def symlink_aquery(links: list[tuple[str, str]]) -> dict:
    """Make an aquery result with one Symlink action for each (input, output) pair."""
    fragments: list[dict] = []
    fragment_ids: dict[str, int] = {}

    def fragment_id(path: str) -> int:
        if path not in fragment_ids:
            parent, _, label = path.rpartition("/")
            fragment = {"label": label}
            if parent:
                fragment["parentId"] = fragment_id(parent)
            fragment["id"] = len(fragments) + 1
            fragments.append(fragment)
            fragment_ids[path] = fragment["id"]
        return fragment_ids[path]

    artifacts: list[dict] = []
    dep_sets: list[dict] = []
    actions: list[dict] = []
    for input_path, output_path in links:
        input_id = len(artifacts) + 1
        artifacts.append({"id": input_id, "pathFragmentId": fragment_id(input_path)})
        output_id = len(artifacts) + 1
        artifacts.append({"id": output_id, "pathFragmentId": fragment_id(output_path)})
        dep_set_id = len(dep_sets) + 1
        dep_sets.append({"id": dep_set_id, "directArtifactIds": [input_id]})
        actions.append(
            {
                "mnemonic": "Symlink",
                "inputDepSetIds": [dep_set_id],
                "outputIds": [output_id],
            }
        )
    return {
        "pathFragments": fragments,
        "artifacts": artifacts,
        "depSetOfFiles": dep_sets,
        "actions": actions,
    }


class WorkspaceTestCase(unittest.TestCase):
    """A workspace with the source headers of the fixture and no bazel-out dir.

    <workspace>/external points to <output_base>/external. There, the module
    inner+ points to <workspace>/third_party/inner, as a local_path_override does.
    """

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.workspace = root / "workspace"
        for header in SOURCE_HEADERS:
            self.make_file(self.workspace / header)
        self.external = root / "output_base" / "external"
        self.external.mkdir(parents=True)
        (self.external / "inner+").symlink_to(self.workspace / "third_party" / "inner")
        (self.workspace / "external").symlink_to(self.external)

    @staticmethod
    def make_file(path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()

    def source_dir(self, path: str) -> str:
        """The real path of a dir in the workspace."""
        return os.path.realpath(self.workspace / path)

    def replacements(self, aquery: dict) -> dict[str, list[str]]:
        return virtual_include_replacements(aquery, str(self.workspace))

    def fixture_replacements(self) -> dict[str, list[str]]:
        return self.replacements(json.loads(AQUERY_FIXTURE.read_text()))


class TestVirtualIncludeReplacements(WorkspaceTestCase):
    """Mapping _virtual_includes dirs to source dirs from aquery Symlink actions."""

    def test_strip_include_prefix_maps_to_source_dir_in_every_config(self):
        """A strip_include_prefix lib maps to its source dir in each config."""
        replacements = self.fixture_replacements()
        expected = [self.source_dir("pkg_a/include")]
        self.assertEqual(replacements[VIRTUAL_A], expected)
        self.assertEqual(replacements[f"{EXEC}/pkg_a/_virtual_includes/a"], expected)

    def test_include_prefix_is_not_mapped(self):
        """A lib with include_prefix is not mapped, also with strip_include_prefix."""
        replacements = self.fixture_replacements()
        self.assertNotIn(f"{FASTBUILD}/pkg_b/_virtual_includes/b", replacements)
        self.assertNotIn(f"{FASTBUILD}/pkg_c/_virtual_includes/c", replacements)

    def test_strip_include_prefix_slash_maps_to_workspace_root(self):
        """A lib with strip_include_prefix "/" maps to the workspace root."""
        replacements = self.fixture_replacements()
        expected = [os.path.realpath(self.workspace)]
        self.assertEqual(
            replacements[f"{FASTBUILD}/pkg_d/_virtual_includes/d"], expected
        )
        self.assertEqual(replacements[f"{EXEC}/pkg_d/_virtual_includes/d"], expected)

    def test_generated_headers_only_is_not_mapped(self):
        """A lib with only generated headers is not mapped."""
        self.assertNotIn(
            f"{FASTBUILD}/pkg_g/_virtual_includes/g", self.fixture_replacements()
        )

    def test_mixed_headers_keep_virtual_dir_after_source_dir(self):
        """A lib with mixed headers maps to its source dir, then to its virtual dir."""
        virtual_dir = f"{FASTBUILD}/pkg_m/_virtual_includes/m"
        self.assertEqual(
            self.fixture_replacements()[virtual_dir],
            [self.source_dir("pkg_m/include"), virtual_dir],
        )

    def test_main_repo_package_and_local_module_map_into_workspace(self):
        """A nested package and an in-workspace module map to the same source dir."""
        replacements = self.fixture_replacements()
        expected = [self.source_dir("third_party/inner/include")]
        self.assertEqual(
            replacements[f"{FASTBUILD}/third_party/inner/_virtual_includes/inner"],
            expected,
        )
        self.assertEqual(
            replacements[f"{FASTBUILD}/external/inner+/_virtual_includes/inner"],
            expected,
        )

    def test_external_repo_outside_workspace_is_not_mapped(self):
        """A lib of an external repo outside the workspace is not mapped."""
        self.make_file(self.external / "far+" / "include" / "far" / "far.h")
        aquery = symlink_aquery(
            [
                LINK_A,
                (
                    "external/far+/include/far/far.h",
                    f"{FASTBUILD}/external/far+/_virtual_includes/far/far/far.h",
                ),
            ]
        )
        self.assertEqual(
            self.replacements(aquery), {VIRTUAL_A: [self.source_dir("pkg_a/include")]}
        )

    def test_source_headers_with_different_roots_are_not_mapped(self):
        """A lib with source headers from different roots is not mapped."""
        self.make_file(self.workspace / "pkg_x" / "include" / "x" / "x.h")
        self.make_file(self.workspace / "pkg_x" / "other" / "x" / "y.h")
        virtual_x = f"{FASTBUILD}/pkg_x/_virtual_includes/x"
        aquery = symlink_aquery(
            [
                LINK_A,
                ("pkg_x/include/x/x.h", f"{virtual_x}/x/x.h"),
                ("pkg_x/other/x/y.h", f"{virtual_x}/x/y.h"),
            ]
        )
        self.assertEqual(
            self.replacements(aquery), {VIRTUAL_A: [self.source_dir("pkg_a/include")]}
        )

    def test_empty_aquery_gives_empty_mapping(self):
        """An empty aquery result gives no replacements."""
        self.assertEqual(self.replacements({}), {})

    def test_mapping_does_not_need_bazel_out(self):
        """The mapping comes from the aquery result alone, with no bazel-out dir."""
        self.assertFalse(os.path.lexists(self.workspace / "bazel-out"))
        self.assertIn(VIRTUAL_A, self.fixture_replacements())


SOURCE_A = "/workspace/pkg_a/include"
VIRTUAL_M = f"{FASTBUILD}/pkg_m/_virtual_includes/m"
SOURCE_M = "/workspace/pkg_m/include"
REPLACEMENTS = {VIRTUAL_A: [SOURCE_A], VIRTUAL_M: [SOURCE_M, VIRTUAL_M]}


class TestRewriteIncludeFlags(unittest.TestCase):
    """Replacing the include flags of _virtual_includes dirs."""

    @staticmethod
    def rewrite(arguments: list[str]) -> list[str]:
        return rewrite_include_flags(list(arguments), REPLACEMENTS)

    def test_joined_include_flag(self):
        """A joined -I flag gets the source dir."""
        self.assertEqual(self.rewrite([f"-I{VIRTUAL_A}"]), [f"-I{SOURCE_A}"])

    def test_separate_isystem_flag(self):
        """A separate -isystem flag gets the source dir."""
        self.assertEqual(self.rewrite(["-isystem", VIRTUAL_A]), ["-isystem", SOURCE_A])

    def test_iquote_flag_in_both_forms(self):
        """A joined and a separate -iquote flag get the source dir."""
        self.assertEqual(
            self.rewrite([f"-iquote{VIRTUAL_A}", "-iquote", VIRTUAL_A]),
            [f"-iquote{SOURCE_A}", "-iquote", SOURCE_A],
        )

    def test_mixed_lib_gets_one_flag_per_dir(self):
        """A dir with two replacements gets two flags of the same form, in order."""
        self.assertEqual(
            self.rewrite([f"-I{VIRTUAL_M}", "-isystem", VIRTUAL_M]),
            [
                f"-I{SOURCE_M}",
                f"-I{VIRTUAL_M}",
                "-isystem",
                SOURCE_M,
                "-isystem",
                VIRTUAL_M,
            ],
        )

    def test_unknown_dir_is_unchanged(self):
        """An include flag for a dir that has no replacement is unchanged."""
        arguments = [
            "-Iother/include",
            "-isystem",
            f"{FASTBUILD}/pkg_z/_virtual_includes/z",
            f"-I{VIRTUAL_A}/a",
        ]
        self.assertEqual(self.rewrite(arguments), arguments)

    def test_args_that_only_contain_a_dir_are_unchanged(self):
        """An arg that is not an include flag is unchanged, even with a dir in it."""
        arguments = [f"-DX={VIRTUAL_A}", f"-fmodule-map-file={VIRTUAL_A}/x.cppmap"]
        self.assertEqual(self.rewrite(arguments), arguments)

    def test_other_args_keep_their_order(self):
        """The args around a rewritten flag keep their order."""
        before = ["clang", "-c", "a.cc", "-idirafter"]
        after = ["-DNDEBUG", "-o", "a.o"]
        self.assertEqual(
            self.rewrite([*before, VIRTUAL_A, *after]), [*before, SOURCE_A, *after]
        )


class TestMain(WorkspaceTestCase):
    """The command line entry point."""

    def test_rewrites_compile_commands_in_place(self):
        """main rewrites arguments in place and keeps directory, file and output."""
        output = f"{FASTBUILD}/pkg_a/_objs/a/a.o"
        entry = {
            "directory": str(self.workspace),
            "file": "pkg_a/a.cc",
            "output": output,
            "arguments": ["clang", f"-I{VIRTUAL_A}", "-c", "pkg_a/a.cc", "-o", output],
        }
        compile_commands = self.workspace / "compile_commands.json"
        compile_commands.write_text(json.dumps([entry]))
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.workspace)

        main([f"--aquery={AQUERY_FIXTURE}", str(compile_commands)])

        rewritten_arguments = [
            "clang",
            f"-I{self.source_dir('pkg_a/include')}",
            "-c",
            "pkg_a/a.cc",
            "-o",
            output,
        ]
        self.assertEqual(
            json.loads(compile_commands.read_text()),
            [{**entry, "arguments": rewritten_arguments}],
        )


if __name__ == "__main__":
    unittest.main()
