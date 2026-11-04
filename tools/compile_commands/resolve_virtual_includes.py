# Copyright (C) 2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

"""Rewrite the _virtual_includes include dirs in compile_commands.json to source dirs.

Bazel puts the headers of some cc_library targets into a _virtual_includes dir
as symlinks. With these include dirs, clangd opens the bazel-out copies of the
headers instead of the sources. This tool replaces each such include dir with
the source dir of its headers. The mapping comes from the Symlink actions of
`bazel aquery`, so it works before a build. A lib that also has generated
headers keeps its _virtual_includes dir after the source dir, so that no header
becomes unreachable.

A _virtual_includes dir without a single source dir in the workspace keeps its
include flag. For these dirs, --overlay writes a clang virtual file system (VFS)
overlay that maps the path of each source header in the dir to the source file,
and adds the overlay to the compile commands that use the dir. Only clang-based
tools read the overlay.

Must run from the workspace root, which the paths in compile_commands.json are
relative to.
"""

import argparse
import json
import os
import re
from collections import defaultdict
from collections.abc import Container, Iterator
from functools import cache
from pathlib import Path
from typing import NamedTuple

INCLUDE_FLAGS = ("-I", "-iquote", "-isystem", "-idirafter")

# A header path in a _virtual_includes dir: the dir, then the include path.
VIRTUAL_HEADER = re.compile(r"(.+?/_virtual_includes/[^/]+)/(.+)")


def symlinks(aquery: dict) -> Iterator[tuple[str, str]]:
    """Yield the (input, output) paths of the Symlink actions in an aquery result."""
    fragments = {
        fragment["id"]: fragment for fragment in aquery.get("pathFragments", [])
    }
    dep_sets = {dep_set["id"]: dep_set for dep_set in aquery.get("depSetOfFiles", [])}

    @cache
    def fragment_path(fragment_id: int) -> str:
        fragment = fragments[fragment_id]
        parent_id = fragment.get("parentId")
        if parent_id is None:
            return fragment["label"]
        return f"{fragment_path(parent_id)}/{fragment['label']}"

    artifact_paths = {
        artifact["id"]: fragment_path(artifact["pathFragmentId"])
        for artifact in aquery.get("artifacts", [])
    }

    def dep_set_paths(dep_set_id: int) -> Iterator[str]:
        dep_set = dep_sets[dep_set_id]
        for artifact_id in dep_set.get("directArtifactIds", []):
            yield artifact_paths[artifact_id]
        for child_id in dep_set.get("transitiveDepSetIds", []):
            yield from dep_set_paths(child_id)

    for action in aquery.get("actions", []):
        if action.get("mnemonic") != "Symlink":
            continue
        inputs = [
            path
            for dep_set_id in action.get("inputDepSetIds", [])
            for path in dep_set_paths(dep_set_id)
        ]
        for output_id in action.get("outputIds", []):
            for input_path in inputs:
                yield input_path, artifact_paths[output_id]


def virtual_headers(aquery: dict) -> Iterator[tuple[str, str, str]]:
    """Yield the (virtual dir, include path, input) of each _virtual_includes header."""
    for input_path, output_path in symlinks(aquery):
        match = VIRTUAL_HEADER.fullmatch(output_path)
        if match is not None:
            virtual_dir, include_path = match.groups()
            yield virtual_dir, include_path, input_path


def is_generated(input_path: str) -> bool:
    return input_path.startswith("bazel-out/")


def is_in_dir(path: str, directory: str) -> bool:
    return os.path.commonpath([path, directory]) == directory


def source_root(input_path: str, include_path: str) -> str | None:
    """The dir from which include_path reaches the source header at input_path.

    Returns "" for the execution root, and None if input_path does not end in
    include_path.
    """
    if input_path == include_path:
        return ""
    if input_path.endswith("/" + include_path):
        return input_path[: -len(include_path) - 1]
    return None


def workspace_source_dir(roots: set[str | None], real_workspace: str) -> str | None:
    """The real path of the single source root, if it is a dir in the workspace."""
    if len(roots) != 1:
        return None
    (root,) = roots
    if root is None:
        return None
    source_dir = os.path.realpath(os.path.join(real_workspace, root))
    in_workspace = is_in_dir(source_dir, real_workspace)
    return source_dir if in_workspace and os.path.isdir(source_dir) else None


def virtual_include_replacements(aquery: dict, workspace: str) -> dict[str, list[str]]:
    """Map each _virtual_includes dir to the include dirs that replace it.

    The value is the source dir of the headers, then the _virtual_includes dir
    if the lib also has generated headers. A dir without exactly one source dir
    in the workspace is not in the result.
    """
    source_roots: dict[str, set[str | None]] = defaultdict(set)
    with_generated_headers: set[str] = set()
    for virtual_dir, include_path, input_path in virtual_headers(aquery):
        if is_generated(input_path):
            with_generated_headers.add(virtual_dir)
        else:
            source_roots[virtual_dir].add(source_root(input_path, include_path))

    real_workspace = os.path.realpath(workspace)
    replacements: dict[str, list[str]] = {}
    for virtual_dir, roots in source_roots.items():
        source_dir = workspace_source_dir(roots, real_workspace)
        if source_dir is None:
            continue
        replacements[virtual_dir] = [source_dir]
        if virtual_dir in with_generated_headers:
            replacements[virtual_dir].append(virtual_dir)
    return replacements


def source_file(input_path: str, workspace: str, real_workspace: str) -> str:
    """The real path of a source header if it is in the workspace.

    Else the path through the workspace, for example through <workspace>/external.
    """
    path = os.path.join(workspace, input_path)
    real_path = os.path.realpath(path)
    return real_path if is_in_dir(real_path, real_workspace) else path


def overlay_headers(
    aquery: dict, workspace: str, replacements: dict[str, list[str]]
) -> dict[str, dict[str, str]]:
    """Map each _virtual_includes dir without a replacement to its source headers.

    The value maps the include path of each source header to its source file. A
    dir without source headers is not in the result.
    """
    real_workspace = os.path.realpath(workspace)
    headers: dict[str, dict[str, str]] = defaultdict(dict)
    for virtual_dir, include_path, input_path in virtual_headers(aquery):
        if virtual_dir not in replacements and not is_generated(input_path):
            headers[virtual_dir][include_path] = source_file(
                input_path, workspace, real_workspace
            )
    return dict(headers)


def include_path_tree(include_paths: dict[str, str]) -> dict:
    """Nest include paths by dir: a dir maps to a dict, a file to its source file."""
    tree: dict = {}
    for include_path, source in include_paths.items():
        *dirs, name = include_path.split("/")
        node = tree
        for dir_name in dirs:
            node = node.setdefault(dir_name, {})
        node[name] = source
    return tree


def overlay_entries(tree: dict) -> list[dict]:
    """The VFS overlay entries of an include path tree, sorted by name."""
    entries: list[dict] = []
    for name, value in sorted(tree.items()):
        if isinstance(value, dict):
            entries.append(
                {"type": "directory", "name": name, "contents": overlay_entries(value)}
            )
        else:
            entries.append({"type": "file", "name": name, "external-contents": value})
    return entries


def vfs_overlay(headers: dict[str, dict[str, str]], directory: str) -> dict:
    """A clang VFS overlay that maps the headers of each virtual dir to sources.

    The virtual dirs are relative to directory. With use-external-names, clang
    reports the path of the source file instead of the virtual path.
    """
    roots = {
        os.path.join(directory, virtual_dir): include_path_tree(include_paths)
        for virtual_dir, include_paths in headers.items()
    }
    return {"version": 0, "use-external-names": True, "roots": overlay_entries(roots)}


class IncludeFlag(NamedTuple):
    """An include flag and its dir, joined (-I<dir>) or as two args (-I <dir>)."""

    flag: str
    directory: str
    joined: bool

    def args(self, directory: str) -> list[str]:
        """The args of this flag, in the same form, for directory."""
        return [self.flag + directory] if self.joined else [self.flag, directory]


def joined_include_flag(arg: str) -> IncludeFlag | None:
    for flag in INCLUDE_FLAGS:
        if arg.startswith(flag):
            return IncludeFlag(flag, arg[len(flag) :], joined=True)
    return None


def split_include_flags(arguments: list[str]) -> Iterator[str | IncludeFlag]:
    """Yield each include flag with its dir as an IncludeFlag, and other args as is."""
    index = 0
    while index < len(arguments):
        arg = arguments[index]
        if arg in INCLUDE_FLAGS and index + 1 < len(arguments):
            yield IncludeFlag(arg, arguments[index + 1], joined=False)
            index += 2
            continue
        yield joined_include_flag(arg) or arg
        index += 1


def rewrite_include_flags(
    arguments: list[str], replacements: dict[str, list[str]]
) -> list[str]:
    """Replace each include flag for a mapped dir with one flag per replacement dir."""
    rewritten: list[str] = []
    for part in split_include_flags(arguments):
        if isinstance(part, str):
            rewritten.append(part)
            continue
        for directory in replacements.get(part.directory, [part.directory]):
            rewritten += part.args(directory)
    return rewritten


def add_overlay_flag(
    arguments: list[str], overlay_dirs: Container[str], overlay_file: str
) -> list[str]:
    """Add the overlay after the compiler if an include flag names an overlay dir."""
    names_overlay_dir = any(
        isinstance(part, IncludeFlag) and part.directory in overlay_dirs
        for part in split_include_flags(arguments)
    )
    if not names_overlay_dir:
        return arguments
    return [arguments[0], "-ivfsoverlay", overlay_file, *arguments[1:]]


def shared_directory(entries: list[dict]) -> str:
    """The directory that all compile commands share, or "" if there are none."""
    return entries[0]["directory"] if entries else ""


def write_json_atomically(path: str, value: object) -> None:
    tmp_path = Path(f"{path}.tmp")
    tmp_path.write_text(json.dumps(value))
    os.replace(tmp_path, path)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--aquery",
        type=Path,
        required=True,
        help="Symlink actions from `bazel aquery --output=jsonproto`",
    )
    parser.add_argument(
        "--overlay",
        help="Path of the VFS overlay file to write and to add to the compile commands",
    )
    parser.add_argument("compile_commands", type=Path)
    args = parser.parse_args(argv)

    aquery = json.loads(args.aquery.read_text())
    workspace = os.getcwd()
    replacements = virtual_include_replacements(aquery, workspace)
    entries = json.loads(args.compile_commands.read_text())
    for entry in entries:
        entry["arguments"] = rewrite_include_flags(entry["arguments"], replacements)

    if args.overlay is not None:
        headers = overlay_headers(aquery, workspace, replacements) if entries else {}
        overlay = vfs_overlay(headers, shared_directory(entries))
        write_json_atomically(args.overlay, overlay)
        for entry in entries:
            entry["arguments"] = add_overlay_flag(
                entry["arguments"], headers.keys(), args.overlay
            )
    args.compile_commands.write_text(json.dumps(entries))


if __name__ == "__main__":
    main()
