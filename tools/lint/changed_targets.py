#!/usr/bin/env python3
"""
Print the C/C++ targets that compile the source files changed since a git ref.

On a pull request reviewdog only shows findings on changed lines, so linting
anything but the targets that compile the changed files is wasted work. Owners
are looked up with same_pkg_direct_rdeps, which loads only the packages holding
the changed files; rdeps(//..., ...) would load the whole graph instead.
"""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Sequence

SOURCE_EXTENSIONS = ("c", "cc", "cpp", "cxx", "h", "hh", "hpp", "hxx")

# Only these rule kinds get lint actions from the aspects in linters.bzl.
LINTED_RULE_KINDS = "^cc_(library|binary|test) rule$"

# bazel query --keep_going reports the errors it skipped and exits 3 rather than
# failing. Usually that is a changed file that no target lists in its srcs or
# hdrs, but a genuine load error in an affected package looks the same and drops
# that package's targets from the result. Accepted because master lints in full.
QUERY_PARTIAL_EXIT_CODE = 3

RunQuery = Callable[[str], list[str]]


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print the C/C++ targets owning the files changed since a git ref."
    )
    parser.add_argument(
        "--base",
        required=True,
        help="Git ref to diff against; the diff runs from its merge base with HEAD",
    )
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=list(SOURCE_EXTENSIONS),
        help="File extensions that count as C/C++ sources",
    )
    return parser.parse_args(argv)


def changed_files(workspace: Path, base: str) -> list[str]:
    """Files added, copied, modified or renamed between merge-base(base, HEAD) and HEAD."""
    result = subprocess.run(
        # -z keeps paths raw; without it core.quotePath escapes spaces and
        # non-ASCII bytes into quoted tokens that are not valid target labels.
        ["git", "diff", "-z", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD"],
        cwd=workspace,
        check=True,
        capture_output=True,
        text=True,
    )
    return [file for file in result.stdout.split("\0") if file]


def ignored_directories(workspace: Path) -> list[str]:
    """Directory prefixes listed in .bazelignore, which no package can own."""
    bazelignore = workspace / ".bazelignore"
    if not bazelignore.is_file():
        return []
    entries = []
    for line in bazelignore.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            entries.append(line.rstrip("/"))
    return entries


def source_files(
    files: Sequence[str], extensions: Sequence[str], ignored: Sequence[str]
) -> list[str]:
    """Keep the C/C++ sources that live inside the Bazel workspace."""
    suffixes = tuple(f".{extension}" for extension in extensions)
    selected = []
    for file in files:
        if not file.endswith(suffixes):
            continue
        if any(file == prefix or file.startswith(prefix + "/") for prefix in ignored):
            continue
        selected.append(file)
    return selected


class QueryError(Exception):
    def __init__(self, returncode: int):
        super().__init__(f"bazel query failed with exit code {returncode}")
        self.returncode = returncode


def query_labels(result: subprocess.CompletedProcess) -> list[str]:
    """Labels from a finished bazel query, tolerating a partial result."""
    # Always forwarded: it is the only record of what the partial result skipped.
    sys.stderr.write(result.stderr)
    if result.returncode not in (0, QUERY_PARTIAL_EXIT_CODE):
        raise QueryError(result.returncode)
    return result.stdout.split()


def bazel_query(workspace: Path) -> RunQuery:
    def run(expression: str) -> list[str]:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".query", encoding="utf-8"
        ) as query_file:
            query_file.write(expression)
            query_file.flush()
            return query_labels(
                subprocess.run(
                    [
                        "bazel",
                        "query",
                        "--keep_going",
                        "--output=label",
                        "--noshow_progress",
                        "--ui_event_filters=-info",
                        f"--query_file={query_file.name}",
                    ],
                    cwd=workspace,
                    check=False,
                    capture_output=True,
                    text=True,
                )
            )

    return run


def owning_targets(files: Sequence[str], run_query: RunQuery) -> list[str]:
    """Linted rules that compile the files, directly or through a same-package filegroup.

    A second same_pkg_direct_rdeps round runs only for owners that do not lint
    the files themselves: filegroups and other non-cc rules listing them, and
    header-only libraries, whose headers get findings from a same-package
    consumer compiling against them.
    """
    if not files:
        return []
    direct = run_query(f"same_pkg_direct_rdeps(set({' '.join(files)}))")
    if not direct:
        return []
    owners = " ".join(direct)
    passthrough = run_query(
        f'set({owners}) - kind("^cc_.* rule$", set({owners})) '
        f'+ attr("srcs", "^\\[\\]$", kind("cc_library rule", set({owners})))'
    )
    indirect = (
        run_query(f"same_pkg_direct_rdeps(set({' '.join(passthrough)}))")
        if passthrough
        else []
    )
    candidates = sorted(set(direct) | set(indirect))
    return sorted(
        run_query(f'kind("{LINTED_RULE_KINDS}", set({" ".join(candidates)}))')
    )


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    workspace = Path(os.environ.get("BUILD_WORKSPACE_DIRECTORY") or os.getcwd())

    files = source_files(
        changed_files(workspace, args.base),
        args.extensions,
        ignored_directories(workspace),
    )
    print(f"{len(files)} changed C/C++ file(s)", file=sys.stderr)
    for file in files:
        print(f"  {file}", file=sys.stderr)

    try:
        targets = owning_targets(files, bazel_query(workspace))
    except QueryError as error:
        print(error, file=sys.stderr)
        return error.returncode
    # With stdout redirected, as in CI, the list would otherwise be invisible.
    echo = not sys.stdout.isatty()
    print(f"{len(targets)} target(s) to lint", file=sys.stderr)
    for target in targets:
        if echo:
            print(f"  {target}", file=sys.stderr)
        print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
