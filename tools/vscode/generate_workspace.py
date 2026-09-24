#!/usr/bin/env python3
"""
Generate the VS Code workspace of a Bazel C++ repository.

Run from the repository:
    bazel run @rules_swiftnav//tools/vscode:generate_workspace

It writes <repository>.code-workspace from the defaults of workspace.py, the
repository's cc targets, and the optional .vscode-workspace.json (committed)
and .vscode-workspace.local.json (per developer, not committed) configs.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Mapping, Optional, Sequence

from tools.vscode.workspace import (
    ConfigError,
    generate,
    load_config,
    merge_configs,
    parse_targets,
)

CONFIG_FILES = (".vscode-workspace.json", ".vscode-workspace.local.json")


def query_cc_targets(workspace_dir: Path) -> str:
    """Query the repository's cc targets.

    Args:
        workspace_dir: The repository root.

    Returns:
        The query's XML output.
    """
    return subprocess.check_output(
        ["bazel", "query", 'kind("cc_.*", //...)', "--output=xml"],
        cwd=workspace_dir,
        text=True,
    )


def load_configs(workspace_dir: Path) -> dict:
    """Load the repository's config and overlay the local one, if they exist."""
    config: dict = {}
    for name in CONFIG_FILES:
        path = workspace_dir / name
        if path.exists():
            config = merge_configs(config, load_config(path.read_text(), str(path)))
    return config


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--workspace-dir",
        type=Path,
        help="Repository root (default: the workspace `bazel run` was invoked in)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Workspace file to write (default: <workspace-dir>/<repository>.code-workspace)",
    )
    return parser.parse_args(argv)


def main(
    argv: Sequence[str],
    environ: Optional[Mapping[str, str]] = None,
    query: Callable[[Path], str] = query_cc_targets,
) -> int:
    """Generate the workspace file.

    Args:
        argv: Command line arguments, without the program name.
        environ: Environment, os.environ if None.
        query: Returns the XML of the repository's cc targets.

    Returns:
        The exit code.
    """
    if environ is None:
        environ = os.environ
    args = parse_args(argv)
    # bazel run starts the binary from its runfiles, not from where it was run.
    working_dir = Path(environ.get("BUILD_WORKING_DIRECTORY", "."))
    workspace_dir = args.workspace_dir or environ.get("BUILD_WORKSPACE_DIRECTORY")
    if workspace_dir is None:
        print("Error: run with `bazel run`, or pass --workspace-dir", file=sys.stderr)
        return 1
    workspace_dir = (working_dir / workspace_dir).absolute()
    repo_name = workspace_dir.name
    output = (
        working_dir / args.output
        if args.output
        else workspace_dir / f"{repo_name}.code-workspace"
    )

    try:
        workspace = generate(
            config=load_configs(workspace_dir),
            targets=parse_targets(query(workspace_dir)),
            repo_name=repo_name,
            has_lldbinit=(workspace_dir / ".lldbinit").exists(),
        )
    except ConfigError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    output.write_text(json.dumps(workspace, indent=2) + "\n")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
