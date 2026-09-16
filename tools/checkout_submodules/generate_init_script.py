# Copyright (C) 2022-2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

"""Emit the CI submodule-checkout script from MODULE.bazel's local_path_override set.

MODULE.bazel is the source of truth for which submodules the Bazel build reads.
Paths that are not Bazel modules (LFS data, for example) come in via --extra-path.
"""

import argparse
import re

_OVERRIDE_RE = re.compile(r"local_path_override\((.*?)\)", re.DOTALL)
_PATH_RE = re.compile(r"""path\s*=\s*["']([^"']+)["']""")

_TEMPLATE = """#!/usr/bin/env bash
# Generated from MODULE.bazel. Do not edit.
# To update this file, run:
#   bazel run {update_target}
set -euo pipefail

# actions/checkout disables the LFS smudge filter when lfs is false; these
# clones bypass it, and the LFS credentials are only configured later.
export GIT_LFS_SKIP_SMUDGE=1

# Groups are ordered shallow to deep: a nested submodule can only be
# initialized once its parent working tree exists.
declare -a SUBMODULE_GROUPS=(
{groups}
)

for group in "${{SUBMODULE_GROUPS[@]}}"; do
  parent="${{group%%|*}}"
  read -r -a paths <<<"${{group#*|}}"
  git -C "${{parent}}" submodule update \\
    --init --depth=1 --jobs "${{SUBMODULE_JOBS:-4}}" -- "${{paths[@]}}"
done
"""


def module_paths(module_file):
    paths = []
    for block in _OVERRIDE_RE.findall(module_file.read()):
        match = _PATH_RE.search(block)
        if match:
            paths.append(match.group(1).strip("/"))
    return paths


def group_by_parent(paths):
    """Map each path to the deepest other path containing it, or "." for top level."""
    groups = {}
    for path in paths:
        parent = max(
            (other for other in paths if path.startswith(other + "/")),
            key=len,
            default="",
        )
        child = path[len(parent) + 1 :] if parent else path
        groups.setdefault(parent or ".", []).append(child)
    return groups


def format_groups(groups):
    def depth(parent):
        return 0 if parent == "." else parent.count("/") + 1

    return "\n".join(
        '  "{}|{}"'.format(parent, " ".join(sorted(groups[parent])))
        for parent in sorted(groups, key=lambda parent: (depth(parent), parent))
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module-file", type=argparse.FileType(), required=True)
    parser.add_argument("--output", type=argparse.FileType("w"), required=True)
    parser.add_argument("--extra-path", action="append", default=[])
    parser.add_argument("--update-target", required=True)
    args = parser.parse_args()

    paths = module_paths(args.module_file) + args.extra_path
    args.output.write(
        _TEMPLATE.format(
            groups=format_groups(group_by_parent(paths)),
            update_target=args.update_target,
        )
    )


if __name__ == "__main__":
    main()
