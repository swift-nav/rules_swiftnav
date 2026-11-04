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
    add_overlay_flag,
    main,
    overlay_headers,
    rewrite_include_flags,
    vfs_overlay,
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
VIRTUAL_B = f"{FASTBUILD}/pkg_b/_virtual_includes/b"
VIRTUAL_C = f"{FASTBUILD}/pkg_c/_virtual_includes/c"
VIRTUAL_G = f"{FASTBUILD}/pkg_g/_virtual_includes/g"
VIRTUAL_M = f"{FASTBUILD}/pkg_m/_virtual_includes/m"


def fixture_aquery() -> dict:
    return json.loads(AQUERY_FIXTURE.read_text())


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

    def real_path(self, path: str) -> str:
        """The real path of a dir or file in the workspace."""
        return os.path.realpath(self.workspace / path)

    def replacements(self, aquery: dict) -> dict[str, list[str]]:
        return virtual_include_replacements(aquery, str(self.workspace))

    def fixture_replacements(self) -> dict[str, list[str]]:
        return self.replacements(fixture_aquery())

    def run_main(self, entries: list[dict], *flags: str) -> list[dict]:
        """Run main from the workspace and return the rewritten compile commands."""
        compile_commands = self.workspace / "compile_commands.json"
        compile_commands.write_text(json.dumps(entries))
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(self.workspace)
        main([f"--aquery={AQUERY_FIXTURE}", *flags, str(compile_commands)])
        return json.loads(compile_commands.read_text())


class TestVirtualIncludeReplacements(WorkspaceTestCase):
    """Mapping _virtual_includes dirs to source dirs from aquery Symlink actions."""

    def assert_not_mapped(self, links: list[tuple[str, str]]) -> None:
        """Make sure that links get no replacement and that LINK_A gets one."""
        aquery = symlink_aquery([LINK_A, *links])
        self.assertEqual(
            self.replacements(aquery), {VIRTUAL_A: [self.real_path("pkg_a/include")]}
        )

    def test_strip_include_prefix_maps_to_source_dir_in_every_config(self):
        """A strip_include_prefix lib maps to its source dir in each config."""
        replacements = self.fixture_replacements()
        expected = [self.real_path("pkg_a/include")]
        self.assertEqual(replacements[VIRTUAL_A], expected)
        self.assertEqual(replacements[f"{EXEC}/pkg_a/_virtual_includes/a"], expected)

    def test_include_prefix_is_not_mapped(self):
        """A lib with include_prefix is not mapped, also with strip_include_prefix."""
        replacements = self.fixture_replacements()
        self.assertNotIn(VIRTUAL_B, replacements)
        self.assertNotIn(VIRTUAL_C, replacements)

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
        self.assertNotIn(VIRTUAL_G, self.fixture_replacements())

    def test_mixed_headers_keep_virtual_dir_after_source_dir(self):
        """A lib with mixed headers maps to its source dir, then to its virtual dir."""
        self.assertEqual(
            self.fixture_replacements()[VIRTUAL_M],
            [self.real_path("pkg_m/include"), VIRTUAL_M],
        )

    def test_main_repo_package_and_local_module_map_into_workspace(self):
        """A nested package and an in-workspace module map to the same source dir."""
        replacements = self.fixture_replacements()
        expected = [self.real_path("third_party/inner/include")]
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
        self.assert_not_mapped(
            [
                (
                    "external/far+/include/far/far.h",
                    f"{FASTBUILD}/external/far+/_virtual_includes/far/far/far.h",
                ),
            ]
        )

    def test_source_headers_with_different_roots_are_not_mapped(self):
        """A lib with source headers from different roots is not mapped."""
        self.make_file(self.workspace / "pkg_x" / "include" / "x" / "x.h")
        self.make_file(self.workspace / "pkg_x" / "other" / "x" / "y.h")
        virtual_x = f"{FASTBUILD}/pkg_x/_virtual_includes/x"
        self.assert_not_mapped(
            [
                ("pkg_x/include/x/x.h", f"{virtual_x}/x/x.h"),
                ("pkg_x/other/x/y.h", f"{virtual_x}/x/y.h"),
            ]
        )

    def test_empty_aquery_gives_empty_mapping(self):
        """An empty aquery result gives no replacements."""
        self.assertEqual(self.replacements({}), {})

    def test_mapping_does_not_need_bazel_out(self):
        """The mapping comes from the aquery result alone, with no bazel-out dir."""
        self.assertFalse(os.path.lexists(self.workspace / "bazel-out"))
        self.assertIn(VIRTUAL_A, self.fixture_replacements())


SOURCE_A = "/workspace/pkg_a/include"
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
        rewritten_arguments = [
            "clang",
            f"-I{self.real_path('pkg_a/include')}",
            "-c",
            "pkg_a/a.cc",
            "-o",
            output,
        ]
        self.assertEqual(
            self.run_main([entry]), [{**entry, "arguments": rewritten_arguments}]
        )


class TestOverlayHeaders(WorkspaceTestCase):
    """Finding the headers of the _virtual_includes dirs that have no replacement."""

    def headers(
        self, aquery: dict, replacements: dict[str, list[str]] | None = None
    ) -> dict[str, dict[str, str]]:
        if replacements is None:
            replacements = self.replacements(aquery)
        return overlay_headers(aquery, str(self.workspace), replacements)

    def fixture_headers(
        self, replacements: dict[str, list[str]] | None = None
    ) -> dict[str, dict[str, str]]:
        return self.headers(fixture_aquery(), replacements)

    def test_include_prefix_libs_map_include_paths_to_source_files(self):
        """Libs with include_prefix, also with strip_include_prefix, map to sources."""
        headers = self.fixture_headers()
        self.assertEqual(
            headers[VIRTUAL_B], {"vendor_b/b.h": self.real_path("pkg_b/b.h")}
        )
        self.assertEqual(
            headers[VIRTUAL_C], {"cpref/c.h": self.real_path("pkg_c/src/c.h")}
        )

    def test_libs_with_replacement_are_not_in_overlay(self):
        """A lib that has a replacement is not in the overlay."""
        replacements = self.fixture_replacements()
        self.assertEqual(self.fixture_headers().keys() & replacements.keys(), set())

    def test_generated_headers_only_is_not_in_overlay(self):
        """A lib with only generated headers is not in the overlay."""
        self.assertNotIn(VIRTUAL_G, self.fixture_headers())

    def test_generated_headers_of_mixed_lib_are_not_in_overlay(self):
        """A lib with mixed headers and no replacement has only its source headers."""
        self.assertEqual(
            self.fixture_headers(replacements={})[VIRTUAL_M],
            {"m/m.h": self.real_path("pkg_m/include/m/m.h")},
        )

    def test_source_headers_with_different_roots_are_in_overlay(self):
        """A lib with source headers from different roots has all of them."""
        self.make_file(self.workspace / "pkg_x" / "include" / "x" / "x.h")
        self.make_file(self.workspace / "pkg_x" / "other" / "x" / "y.h")
        virtual_x = f"{FASTBUILD}/pkg_x/_virtual_includes/x"
        aquery = symlink_aquery(
            [
                ("pkg_x/include/x/x.h", f"{virtual_x}/x/x.h"),
                ("pkg_x/other/x/y.h", f"{virtual_x}/x/y.h"),
            ]
        )
        self.assertEqual(
            self.headers(aquery),
            {
                virtual_x: {
                    "x/x.h": self.real_path("pkg_x/include/x/x.h"),
                    "x/y.h": self.real_path("pkg_x/other/x/y.h"),
                }
            },
        )

    def test_external_repo_outside_workspace_keeps_path_through_external_link(self):
        """A lib of a repo outside the workspace maps via <workspace>/external."""
        self.make_file(self.external / "far+" / "include" / "far" / "far.h")
        virtual_far = f"{FASTBUILD}/external/far+/_virtual_includes/far"
        far_header = "external/far+/include/far/far.h"
        aquery = symlink_aquery([(far_header, f"{virtual_far}/far/far.h")])
        self.assertEqual(
            self.headers(aquery),
            {virtual_far: {"far/far.h": os.path.join(self.workspace, far_header)}},
        )

    def test_local_module_maps_to_real_source_file_in_workspace(self):
        """A lib of a module in the workspace maps to the real source file path."""
        virtual_inner = f"{FASTBUILD}/external/inner+/_virtual_includes/prefixed"
        aquery = symlink_aquery(
            [
                (
                    "external/inner+/include/inner/inner.h",
                    f"{virtual_inner}/prefix/inner.h",
                )
            ]
        )
        self.assertEqual(
            self.headers(aquery),
            {
                virtual_inner: {
                    "prefix/inner.h": self.real_path(
                        "third_party/inner/include/inner/inner.h"
                    )
                }
            },
        )


DIRECTORY = "/workspace"


def dir_entry(name: str, *contents: dict) -> dict:
    """A directory entry of a virtual file system (VFS) overlay."""
    return {"type": "directory", "name": name, "contents": list(contents)}


def file_entry(name: str, source_file: str) -> dict:
    """A file entry of a VFS overlay that maps to a source file."""
    return {"type": "file", "name": name, "external-contents": source_file}


class TestVfsOverlay(unittest.TestCase):
    """Making a clang VFS overlay from the overlay headers."""

    def test_include_path_becomes_nested_entries_below_virtual_dir(self):
        """Each dir of an include path is a directory entry below the virtual dir."""
        overlay = vfs_overlay(
            {VIRTUAL_B: {"vendor_b/detail/b.h": "/src/b.h"}}, DIRECTORY
        )
        self.assertEqual(
            overlay,
            {
                "version": 0,
                "use-external-names": True,
                "roots": [
                    dir_entry(
                        os.path.join(DIRECTORY, VIRTUAL_B),
                        dir_entry(
                            "vendor_b",
                            dir_entry("detail", file_entry("b.h", "/src/b.h")),
                        ),
                    )
                ],
            },
        )

    def test_headers_in_one_dir_share_its_entry(self):
        """Headers in the same dir share one directory entry."""
        overlay = vfs_overlay(
            {VIRTUAL_B: {"vendor_b/a.h": "/src/a.h", "vendor_b/b.h": "/src/b.h"}},
            DIRECTORY,
        )
        self.assertEqual(
            overlay["roots"],
            [
                dir_entry(
                    os.path.join(DIRECTORY, VIRTUAL_B),
                    dir_entry(
                        "vendor_b",
                        file_entry("a.h", "/src/a.h"),
                        file_entry("b.h", "/src/b.h"),
                    ),
                )
            ],
        )

    def test_roots_and_contents_are_sorted(self):
        """The roots and the contents of each directory entry are in sorted order."""
        overlay = vfs_overlay(
            {
                VIRTUAL_C: {"cpref/c.h": "/src/c.h"},
                VIRTUAL_B: {
                    "vendor_b/y.h": "/src/y.h",
                    "vendor_b/x.h": "/src/x.h",
                    "other/o.h": "/src/o.h",
                },
            },
            DIRECTORY,
        )
        self.assertEqual(
            overlay["roots"],
            [
                dir_entry(
                    os.path.join(DIRECTORY, VIRTUAL_B),
                    dir_entry("other", file_entry("o.h", "/src/o.h")),
                    dir_entry(
                        "vendor_b",
                        file_entry("x.h", "/src/x.h"),
                        file_entry("y.h", "/src/y.h"),
                    ),
                ),
                dir_entry(
                    os.path.join(DIRECTORY, VIRTUAL_C),
                    dir_entry("cpref", file_entry("c.h", "/src/c.h")),
                ),
            ],
        )


OVERLAY_FILE = "/workspace/vfs_overlay.json"


class TestAddOverlayFlag(unittest.TestCase):
    """Adding the overlay flag to the arguments that name an overlay dir."""

    @staticmethod
    def add_flag(arguments: list[str]) -> list[str]:
        return add_overlay_flag(list(arguments), {VIRTUAL_B}, OVERLAY_FILE)

    def test_joined_include_flag_adds_overlay_after_compiler(self):
        """A joined -I flag adds the overlay after the compiler."""
        self.assertEqual(
            self.add_flag(["clang", "-c", "b.cc", f"-I{VIRTUAL_B}"]),
            ["clang", "-ivfsoverlay", OVERLAY_FILE, "-c", "b.cc", f"-I{VIRTUAL_B}"],
        )

    def test_separate_isystem_flag_adds_overlay_after_compiler(self):
        """A separate -isystem flag adds the overlay after the compiler."""
        self.assertEqual(
            self.add_flag(["clang", "-c", "b.cc", "-isystem", VIRTUAL_B]),
            [
                "clang",
                "-ivfsoverlay",
                OVERLAY_FILE,
                "-c",
                "b.cc",
                "-isystem",
                VIRTUAL_B,
            ],
        )

    def test_arguments_without_overlay_dir_are_unchanged(self):
        """Arguments without an include flag for an overlay dir are unchanged."""
        arguments = [
            "clang",
            f"-I{VIRTUAL_A}",
            "-isystem",
            f"{VIRTUAL_B}/vendor_b",
            f"-DX={VIRTUAL_B}",
        ]
        self.assertEqual(self.add_flag(arguments), arguments)

    def test_input_list_is_not_changed(self):
        """The input list stays the same."""
        arguments = ["clang", f"-I{VIRTUAL_B}"]
        add_overlay_flag(arguments, {VIRTUAL_B}, OVERLAY_FILE)
        self.assertEqual(arguments, ["clang", f"-I{VIRTUAL_B}"])


class TestMainWithOverlay(WorkspaceTestCase):
    """The command line entry point with --overlay."""

    def setUp(self):
        super().setUp()
        self.overlay = self.workspace / "vfs_overlay.json"
        entries = self.run_main(
            [self.entry("pkg_b/b.cc", VIRTUAL_B), self.entry("pkg_a/a.cc", VIRTUAL_A)],
            f"--overlay={self.overlay}",
        )
        self.arguments = {entry["file"]: entry["arguments"] for entry in entries}

    def entry(self, file: str, include_dir: str) -> dict:
        return {
            "directory": str(self.workspace),
            "file": file,
            "arguments": ["clang", f"-I{include_dir}", "-c", file],
        }

    def test_writes_overlay_with_include_prefix_lib(self):
        """main writes a JSON overlay with a root for the include_prefix lib."""
        root_b = dir_entry(
            os.path.join(self.workspace, VIRTUAL_B),
            dir_entry("vendor_b", file_entry("b.h", self.real_path("pkg_b/b.h"))),
        )
        self.assertIn(root_b, json.loads(self.overlay.read_text())["roots"])

    def test_entry_with_overlay_dir_gets_overlay_flag(self):
        """An entry that names an overlay dir gets the overlay flag."""
        self.assertEqual(
            self.arguments["pkg_b/b.cc"],
            [
                "clang",
                "-ivfsoverlay",
                str(self.overlay),
                f"-I{VIRTUAL_B}",
                "-c",
                "pkg_b/b.cc",
            ],
        )

    def test_entry_without_overlay_dir_gets_no_overlay_flag(self):
        """An entry that names no overlay dir gets only its include rewrite."""
        self.assertEqual(
            self.arguments["pkg_a/a.cc"],
            ["clang", f"-I{self.real_path('pkg_a/include')}", "-c", "pkg_a/a.cc"],
        )


if __name__ == "__main__":
    unittest.main()
