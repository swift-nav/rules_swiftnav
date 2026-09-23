#!/usr/bin/env python3
"""
Print the targets that compile the source files changed since a git ref.

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
from enum import Enum
from pathlib import Path
from typing import Callable, NamedTuple, Sequence


class LanguageConfig(NamedTuple):
    label: str
    extensions: tuple[str, ...]
    # Only these rule kinds get lint actions from the aspects in linters.bzl.
    linted_kinds: str
    # Rule kinds belonging to the language. An owner outside them, such as a
    # filegroup, only passes the sources on and needs a second rdeps round.
    own_kinds: str
    # Query term selecting owners that pass their sources on despite being
    # own_kinds; {owners} stands for the owner labels.
    passthrough_extra: str = ""


CC = LanguageConfig(
    label="C/C++",
    extensions=("c", "cc", "cpp", "cxx", "h", "hh", "hpp", "hxx"),
    linted_kinds="^cc_(library|binary|test) rule$",
    own_kinds="^cc_.* rule$",
    # A header-only cc_library compiles nothing, so its headers only get
    # findings from a same-package consumer compiling against them.
    passthrough_extra='attr("srcs", "^\\[\\]$", kind("cc_library rule", set({owners})))',
)

RUST = LanguageConfig(
    label="Rust",
    extensions=("rs",),
    # The clippy aspect's default rule_kinds.
    linted_kinds="^rust_(library|binary|shared_library|test) rule$",
    own_kinds="^rust_.* rule$",
)

PYTHON = LanguageConfig(
    label="Python",
    extensions=("py", "pyi"),
    # The ty aspect's default rule_kinds.
    linted_kinds="^py_(library|binary|test) rule$",
    own_kinds="^py_.* rule$",
)


class Language(str, Enum):
    CC = "cc"
    RUST = "rust"
    PYTHON = "python"

    # argparse shows choices with str(); the default would print "Language.CC".
    def __str__(self) -> str:
        return self.value


LANGUAGES: dict[Language, LanguageConfig] = {
    Language.CC: CC,
    Language.RUST: RUST,
    Language.PYTHON: PYTHON,
}

# bazel query --keep_going reports the errors it skipped and exits 3 rather than
# failing. Usually that is a changed file that no target lists in its srcs or
# hdrs, but a genuine load error in an affected package looks the same and drops
# that package's targets from the result. Accepted because master lints in full.
QUERY_PARTIAL_EXIT_CODE = 3

RunQuery = Callable[[str], list[str]]


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print the targets owning the files changed since a git ref."
    )
    parser.add_argument(
        "--base",
        required=True,
        help="Git ref to diff against; the diff runs from its merge base with HEAD",
    )
    parser.add_argument(
        "--languages",
        type=Language,
        choices=list(Language),
        nargs="+",
        default=[Language.CC],
        help="Languages whose sources and rule kinds are selected",
    )
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=None,
        help="File extensions that count as sources, overriding the language "
        "default; only valid with a single language",
    )
    args = parser.parse_args(argv)
    if args.extensions is not None and len(args.languages) > 1:
        parser.error("--extensions takes a single language")
    return args


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
    """Keep the sources that live inside the Bazel workspace."""
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


def owning_targets(
    files: Sequence[str], run_query: RunQuery, language: LanguageConfig
) -> list[str]:
    """Linted rules that compile the files, directly or through a same-package filegroup.

    A second same_pkg_direct_rdeps round runs only for owners that do not lint
    the files themselves: rules outside the language that list them, plus
    whatever passthrough_extra adds.
    """
    if not files:
        return []
    direct = run_query(f"same_pkg_direct_rdeps(set({' '.join(files)}))")
    if not direct:
        return []
    owners = " ".join(direct)
    expression = f'set({owners}) - kind("{language.own_kinds}", set({owners}))'
    if language.passthrough_extra:
        expression += " + " + language.passthrough_extra.format(owners=owners)
    passthrough = run_query(expression)
    indirect = (
        run_query(f"same_pkg_direct_rdeps(set({' '.join(passthrough)}))")
        if passthrough
        else []
    )
    candidates = sorted(set(direct) | set(indirect))
    return sorted(
        run_query(f'kind("{language.linted_kinds}", set({" ".join(candidates)}))')
    )


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    workspace = Path(os.environ.get("BUILD_WORKSPACE_DIRECTORY") or os.getcwd())
    changed = changed_files(workspace, args.base)
    ignored = ignored_directories(workspace)
    run_query = bazel_query(workspace)

    targets: set[str] = set()
    for language in (LANGUAGES[name] for name in args.languages):
        files = source_files(
            changed,
            args.extensions if args.extensions is not None else language.extensions,
            ignored,
        )
        print(f"{len(files)} changed {language.label} file(s)", file=sys.stderr)
        for file in files:
            print(f"  {file}", file=sys.stderr)
        try:
            targets.update(owning_targets(files, run_query, language))
        except QueryError as error:
            print(error, file=sys.stderr)
            return error.returncode

    # With stdout redirected, as in CI, the list would otherwise be invisible.
    echo = not sys.stdout.isatty()
    print(f"{len(targets)} target(s) to lint", file=sys.stderr)
    for target in sorted(targets):
        if echo:
            print(f"  {target}", file=sys.stderr)
        print(target)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
