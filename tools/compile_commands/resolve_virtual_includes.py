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

Must run from the workspace root, which the paths in compile_commands.json are
relative to.
"""

import argparse
import json
import os
import re
from collections import defaultdict
from collections.abc import Iterator
from functools import cache
from pathlib import Path

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
    in_workspace = os.path.commonpath([source_dir, real_workspace]) == real_workspace
    return source_dir if in_workspace and os.path.isdir(source_dir) else None


def virtual_include_replacements(aquery: dict, workspace: str) -> dict[str, list[str]]:
    """Map each _virtual_includes dir to the include dirs that replace it.

    The value is the source dir of the headers, then the _virtual_includes dir
    if the lib also has generated headers. A dir without exactly one source dir
    in the workspace is not in the result.
    """
    source_roots: dict[str, set[str | None]] = defaultdict(set)
    with_generated_headers: set[str] = set()
    for input_path, output_path in symlinks(aquery):
        match = VIRTUAL_HEADER.fullmatch(output_path)
        if match is None:
            continue
        virtual_dir, include_path = match.groups()
        if input_path.startswith("bazel-out/"):
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


def split_joined_include_flag(arg: str) -> tuple[str, str] | None:
    """Split an arg such as -I<dir> into the flag and the dir."""
    for flag in INCLUDE_FLAGS:
        if arg.startswith(flag):
            return flag, arg[len(flag) :]
    return None


def rewrite_include_flags(
    arguments: list[str], replacements: dict[str, list[str]]
) -> list[str]:
    """Replace each include flag for a mapped dir with one flag per replacement dir."""
    rewritten: list[str] = []
    index = 0
    while index < len(arguments):
        arg = arguments[index]
        next_arg = arguments[index + 1] if index + 1 < len(arguments) else ""
        if arg in INCLUDE_FLAGS and next_arg in replacements:
            for directory in replacements[next_arg]:
                rewritten += [arg, directory]
            index += 2
            continue
        joined = split_joined_include_flag(arg)
        if joined is not None and joined[1] in replacements:
            flag, virtual_dir = joined
            rewritten += [flag + directory for directory in replacements[virtual_dir]]
        else:
            rewritten.append(arg)
        index += 1
    return rewritten


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--aquery",
        type=Path,
        required=True,
        help="Symlink actions from `bazel aquery --output=jsonproto`",
    )
    parser.add_argument("compile_commands", type=Path)
    args = parser.parse_args(argv)

    replacements = virtual_include_replacements(
        json.loads(args.aquery.read_text()), os.getcwd()
    )
    entries = json.loads(args.compile_commands.read_text())
    for entry in entries:
        entry["arguments"] = rewrite_include_flags(entry["arguments"], replacements)
    args.compile_commands.write_text(json.dumps(entries))


if __name__ == "__main__":
    main()
