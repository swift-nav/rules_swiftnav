#!/usr/bin/env python3
"""
Read build outputs from a Bazel Build Event Protocol JSON file.

Linter aspects expose their reports as extra outputs, which the Build Event
Protocol lists by name. Collecting them from there rather than by globbing
bazel-out keeps working when remote caching leaves outputs unmaterialised
locally.
"""

import json
import sys
from pathlib import Path


def files_from_bep(
    build_event_json_file: Path,
    workspace_root: Path | None,
    suffix: str,
) -> list[Path]:
    """
    Collect paths of build outputs whose name ends with the given suffix.

    The BEP file is newline-delimited JSON. Each line is parsed for
    namedSetOfFiles entries, and files whose name ends with the given suffix
    are collected.

    Args:
        build_event_json_file: Path to the Bazel build event JSON file
        workspace_root: Directory relative BEP paths are resolved against.
            When None, paths are kept as-is (relative to the current working
            directory)
        suffix: File name suffix to filter on

    Returns:
        List of matching file paths
    """
    files: list[Path] = []

    with open(build_event_json_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as e:
                print(
                    f"Error: Build event JSON file contains errors: "
                    f"{build_event_json_file}: {e}",
                    file=sys.stderr,
                )
                sys.exit(1)

            named_set = event.get("namedSetOfFiles")
            if named_set is None:
                continue

            for file_info in named_set.get("files", []):
                name = file_info.get("name", "")
                if not name.endswith(suffix):
                    continue
                path_prefix = list(file_info.get("pathPrefix", []))
                path = Path("/".join(path_prefix + [name]))
                if not path.is_absolute() and workspace_root is not None:
                    path = workspace_root / path
                files.append(path)

    return files
