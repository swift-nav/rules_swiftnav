# Copyright (C) 2026 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

"""Rewrite _virtual_includes include dirs in compile_commands.json to the source dirs they mirror.

Without this, clangd go-to-definition opens headers through the bazel-out symlink tree.
Must run from the workspace root, which compile_commands.json paths are relative to.
"""

import argparse
import json
import os
import re
from functools import cache
from pathlib import Path

VIRTUAL_INCLUDES = re.compile(
    r"bazel-out/[^/]+/bin/(?:[^ ]*?/)?_virtual_includes/[^/ ]+"
)


@cache
def source_root(virtual_dir: str) -> str | None:
    """Source dir mirrored by virtual_dir, or None if its headers don't share a single workspace root."""
    if not os.path.isdir(virtual_dir):
        # Unbuilt configs (e.g. exec) have no tree on disk: use the same lib from any built config.
        suffix = virtual_dir.split("/bin/", 1)[1]
        built = sorted(Path("bazel-out").glob(f"*/bin/{suffix}"))
        if not built:
            return None
        virtual_dir = str(built[0])
    roots: set[str] = set()
    for dirpath, _, filenames in os.walk(virtual_dir):
        for name in filenames:
            link = Path(dirpath, name)
            if not link.is_symlink():
                continue
            rel = str(link.relative_to(virtual_dir))
            target = str(link.resolve())
            if not target.endswith("/" + rel):
                return None
            roots.add(target[: -len(rel) - 1])
    if len(roots) != 1:
        return None
    root = roots.pop()
    workspace = str(Path.cwd().resolve())
    return root if root.startswith(workspace + "/") else None


def rewrite(arg: str) -> str:
    return VIRTUAL_INCLUDES.sub(lambda m: source_root(m.group(0)) or m.group(0), arg)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("compile_commands", type=Path)
    args = parser.parse_args()

    entries = json.loads(args.compile_commands.read_text())
    for entry in entries:
        entry["arguments"] = [rewrite(a) for a in entry["arguments"]]
    args.compile_commands.write_text(json.dumps(entries))


if __name__ == "__main__":
    main()
