#!/usr/bin/env python3
"""
Run linter aspects over a Bazel workspace and collect their reports.

Drives one `bazel build` per requested linter, each writing its own Build Event
Protocol file, and hands those events to extract_lint_results to produce one
SARIF report (and optionally patches) per linter. Linters that also emit raw
machine reports, such as cppcheck's XML, get those merged into one file as well.
"""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, NamedTuple, Optional, Sequence

from tools.lint import extract_lint_results, merge_cppcheck_xml

XML_OUTPUT_GROUP = "rules_lint_xml"


def _colors_enabled() -> bool:
    """Whether to emit ANSI escapes.

    Returns:
        True if the output stream renders them.

    CI logs are not terminals but do render escapes, so they opt in by name
    rather than by isatty.
    """
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR") or os.environ.get("GITHUB_ACTIONS"):
        return True
    return sys.stdout.isatty()


COLOR = _colors_enabled()
BOLD = "\033[1m" if COLOR else ""
DIM = "\033[2m" if COLOR else ""
CYAN = "\033[36m" if COLOR else ""
RED = "\033[31m" if COLOR else ""
RESET = "\033[0m" if COLOR else ""


def banner(text: str) -> None:
    """Announce the linter a run is starting.

    Args:
        text: The linter's name.
    """
    print(f"\n{BOLD}{CYAN}=== {text} ==={RESET}", flush=True)


def step(text: str) -> None:
    """Announce what the next command is for.

    Args:
        text: A description of the step.
    """
    print(f"\n{BOLD}--> {text}{RESET}", flush=True)


def note(text: str) -> None:
    """Print a detail that is not a step of its own.

    Args:
        text: The detail.
    """
    print(f"{DIM}{text}{RESET}", flush=True)


def warn(text: str) -> None:
    """Report a problem that does not stop the run.

    Args:
        text: The message.
    """
    print(f"{RED}{text}{RESET}", file=sys.stderr, flush=True)


def echo(command: Sequence[str]) -> None:
    """Echo a command line before running it.

    Args:
        command: The command, as its argument list.
    """
    print(f"{DIM}+ {' '.join(command)}{RESET}", flush=True)


class Linter(NamedTuple):
    """A linter this driver knows how to invoke.

    Attributes:
        name: Identifier used on the command line and to derive output paths.
        aspects: Aspects requested explicitly on the command line.
        output_groups: Output groups the aspects write their reports to.
    """

    name: str
    aspects: Sequence[str]
    output_groups: Sequence[str]


CLANG_TIDY = Linter(
    name="clang-tidy",
    aspects=("//tools/lint:linters.bzl%clang_tidy",),
    output_groups=("rules_lint_machine",),
)

CPPCHECK = Linter(
    name="cppcheck",
    aspects=("//tools/lint:linters.bzl%cppcheck",),
    # The XML is a separate audit deliverable: the compliance, HTML and HIS
    # report tools downstream read it rather than the SARIF.
    output_groups=("rules_lint_machine", XML_OUTPUT_GROUP),
)

LINTERS = {linter.name: linter for linter in (CLANG_TIDY, CPPCHECK)}

DEFAULT_LINTERS = CLANG_TIDY.name

# The report tools keep their py_binary targets for other callers, but this
# driver imports them rather than shelling out: `bazel run` inside a `bazel run`
# costs a nested server round-trip per linter and buries their tracebacks.


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    """Parse the driver's command line.

    Args:
        argv: Argument list without the program name.

    Returns:
        The parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Run linter aspects over a Bazel workspace and collect their reports."
    )
    parser.add_argument(
        "--create-patches",
        action="store_true",
        help="Ask the linters for fixes and collect them as patch files",
    )
    parser.add_argument(
        "--apply-patches",
        action="store_true",
        help="Create patches and apply them to the workspace",
    )
    targets = parser.add_mutually_exclusive_group()
    targets.add_argument(
        "--targets",
        nargs="+",
        default=["//..."],
        help="Targets to lint",
    )
    targets.add_argument(
        "--targets-file",
        metavar="FILE",
        help=(
            "Read the targets to lint from FILE, one per line. An empty file "
            "lints nothing, so callers computing the target set need no "
            "special case for it"
        ),
    )
    parser.add_argument(
        "--linters",
        default=DEFAULT_LINTERS,
        help=(
            "Comma-separated linters to run, one of "
            f"{', '.join(sorted(LINTERS))} (default: {DEFAULT_LINTERS})"
        ),
    )
    parser.add_argument(
        "--min-severity",
        choices=extract_lint_results.SARIF_LEVELS,
        default=None,
        help=(
            "Raise findings weaker than this severity up to it in the SARIF "
            "report, so that reporters gating on severity treat them alike"
        ),
    )
    parser.add_argument(
        "--build-events",
        metavar="FILE",
        help=(
            "Write bazel's build event json to FILE and keep it, for callers "
            "that post-process other output groups. May contain a {linter} "
            "placeholder, which is required when running several linters"
        ),
    )

    args = parser.parse_args(argv)
    if args.apply_patches:
        args.create_patches = True
    return args


def select_linters(names: str) -> list[Linter]:
    """Resolve a comma-separated linter list into linter definitions.

    Args:
        names: Comma-separated linter names.

    Returns:
        The selected linters, in the order requested.
    """
    selected = []
    for name in [part.strip() for part in names.split(",") if part.strip()]:
        if name not in LINTERS:
            sys.exit(f"Unknown linter: {name}. Known: {', '.join(sorted(LINTERS))}")
        selected.append(LINTERS[name])
    return selected


def output_dir(workspace: Path, linter: Linter) -> Path:
    """Return the directory a linter writes its report and patches to.

    Args:
        workspace: Workspace root.
        linter: The linter.

    Returns:
        The output directory.
    """
    return workspace / f"{linter.name}-output"


def read_targets_file(workspace: Path, path: str) -> list[str]:
    """Read the targets listed in a `--targets-file`.

    Args:
        workspace: Workspace root, which a relative path resolves against.
        path: The file, one target per line.

    Returns:
        The targets, blank lines dropped; empty for an empty file.
    """
    file = Path(path)
    if not file.is_absolute():
        file = workspace / file
    return [line.strip() for line in file.read_text().splitlines() if line.strip()]


def build_events_path(workspace: Path, linter: Linter, template: str) -> Path:
    """Resolve the `--build-events` template for one linter.

    Args:
        workspace: Workspace root, which relative templates resolve against.
        linter: The linter.
        template: The template, optionally containing a `{linter}` placeholder.

    Returns:
        The path bazel should write this linter's build events to.
    """
    path = Path(template.format(linter=linter.name))
    return path if path.is_absolute() else workspace / path


def build_command(
    linter: Linter,
    targets: Sequence[str],
    build_event_json_file: Path,
    create_patches: bool,
) -> list[str]:
    """Build the `bazel build` command running a linter's aspects.

    Args:
        linter: The linter.
        targets: Targets to lint.
        build_event_json_file: Path bazel writes its build events to.
        create_patches: Whether to ask the linters for fixes.

    Returns:
        The command.
    """
    command = [
        "bazel",
        "build",
        f"--build_event_json_file={build_event_json_file}",
        "--remote_download_regex=.*AspectRulesLint.*",
        # Explicitly requesting a target that is incompatible with the host
        # platform is an error, and callers may name the Windows or fuzzer
        # targets directly through --targets. Wildcards skip those on their own.
        "--skip_incompatible_explicit_targets",
    ]
    command += [f"--aspects={aspect}" for aspect in linter.aspects]
    command += [f"--output_groups={group}" for group in linter.output_groups]
    # rules_lint puts the human-readable report in the _validation output
    # group, which Bazel builds regardless of --output_groups. Without this,
    # clang-tidy runs twice per source file for a report nobody reads.
    command.append("--norun_validations")
    command.append("--keep_going")
    if create_patches:
        command += [
            "--@aspect_rules_lint//lint:fix",
            "--output_groups=rules_lint_patch",
        ]
    return command + list(targets)


def extract_command(
    workspace: Path,
    linter: Linter,
    build_event_json_file: Path,
    min_severity: Optional[str] = None,
) -> list[str]:
    """Build the command turning a linter's build events into a report.

    Args:
        workspace: Workspace root.
        linter: The linter.
        build_event_json_file: Path bazel wrote its build events to.
        min_severity: Severity to raise weaker findings to, or None to keep the
            severities the linter reported.

    Returns:
        The arguments for extract_lint_results.main.
    """
    reports = output_dir(workspace, linter)
    command = [
        f"--build-event-json-file={build_event_json_file}",
        f"--bazel-output-path={workspace}",
        f"--output-merged-sarif-file={reports / 'merged-report.sarif'}",
        f"--output-patch-folder={reports / 'patches'}",
        "--exit-code=1",
    ]
    if min_severity is not None:
        command.append(f"--min-severity={min_severity}")
    return command


def merge_command(
    workspace: Path, linter: Linter, build_event_json_file: Path
) -> Optional[list[str]]:
    """Build the command consolidating a linter's XML reports into one file.

    Args:
        workspace: Workspace root.
        linter: The linter.
        build_event_json_file: Path bazel wrote its build events to.

    Returns:
        The arguments for merge_cppcheck_xml.main, or None if the linter emits
        no XML reports.
    """
    if XML_OUTPUT_GROUP not in linter.output_groups:
        return None
    reports = output_dir(workspace, linter)
    return [
        f"--build-event-json-file={build_event_json_file}",
        f"--workspace-root={workspace}",
        f"--output-file={reports / 'merged-report.xml'}",
    ]


def run(command: Sequence[str], workspace: Path) -> int:
    """Run a command from the workspace root.

    Args:
        command: The command to run.
        workspace: Workspace root.

    Returns:
        The command's exit code.
    """
    echo(command)
    return subprocess.run(command, cwd=workspace, check=False).returncode


def run_report_tool(
    name: str, entry_point: Callable[[Sequence[str]], int], args: Sequence[str]
) -> int:
    """Run one of the report tools in this process.

    Args:
        name: The tool's name, for the echoed command line.
        entry_point: The tool's main function.
        args: Arguments to pass to it.

    Returns:
        The tool's exit code.

    A tool that calls sys.exit reports its code rather than tearing this process
    down, so one linter's failure still leaves the others to run.
    """
    echo([name, *args])
    try:
        return entry_point(args)
    except SystemExit as exit_request:
        code = exit_request.code
        if code is None:
            return 0
        return code if isinstance(code, int) else 1


def apply_patches(workspace: Path, linter: Linter) -> int:
    """Apply a linter's collected patches to the workspace.

    Args:
        workspace: Workspace root.
        linter: The linter.

    Returns:
        The exit code of the first failing `patch` call, or 0.
    """
    for patch in sorted((output_dir(workspace, linter) / "patches").glob("*.patch")):
        with open(patch, "r") as f:
            code = subprocess.run(
                ["patch", "-p1"], cwd=workspace, stdin=f, check=False
            ).returncode
        if code != 0:
            return code
    return 0


def lint(workspace: Path, linter: Linter, args: argparse.Namespace) -> int:
    """Run one linter and collect its report.

    Args:
        workspace: Workspace root.
        linter: The linter.
        args: The parsed command line.

    Returns:
        The exit code reported for this linter.
    """
    if args.targets_file:
        targets = read_targets_file(workspace, args.targets_file)
    else:
        targets = list(args.targets)

    banner(linter.name)

    if args.build_events:
        build_events = build_events_path(workspace, linter, args.build_events)
        build_events.parent.mkdir(parents=True, exist_ok=True)
        build_events = str(build_events)
    else:
        handle, build_events = tempfile.mkstemp()
        os.close(handle)
    note(f"Build events for {linter.name} in {build_events}")
    try:
        step(f"Linting {len(targets)} target pattern(s) with the {linter.name} aspect")
        build_code = run(
            build_command(linter, targets, Path(build_events), args.create_patches),
            workspace,
        )
        # The build runs with --keep_going, so a partial failure still leaves
        # reports for the targets that did analyse. Collect those rather than
        # discarding the run, and surface the failure through the exit code.
        if build_code != 0:
            warn(
                f"bazel build for {linter.name} exited {build_code}, "
                "collecting reports for the targets that succeeded"
            )

        step("Extracting SARIF findings from the build event reports")
        code = run_report_tool(
            "extract_lint_results",
            extract_lint_results.main,
            extract_command(workspace, linter, Path(build_events), args.min_severity),
        )
        code = code or build_code

        merge = merge_command(workspace, linter, Path(build_events))
        if merge is not None:
            step("Merging the per-target cppcheck XML reports into one")
            # A merge failure loses an audit deliverable but says nothing about
            # the findings, whose severity the extraction step already reported.
            if (
                run_report_tool("merge_cppcheck_xml", merge_cppcheck_xml.main, merge)
                != 0
            ):
                warn(f"Merging the {linter.name} XML reports failed")
    finally:
        if not args.build_events:
            os.unlink(build_events)

    if args.apply_patches:
        step("Applying the fixes the linter proposed")
        patch_code = apply_patches(workspace, linter)
        if patch_code != 0:
            return patch_code

    print(
        f"\n{BOLD}{linter.name} reports:{RESET} {output_dir(workspace, linter)}",
        flush=True,
    )
    return code


def main() -> int:
    """Run the requested linters.

    Returns:
        The first non-zero linter exit code, or 0.
    """
    args = parse_args(sys.argv[1:])
    linters = select_linters(args.linters)

    if args.build_events and len(linters) > 1 and "{linter}" not in args.build_events:
        sys.exit(
            "--build-events needs a {linter} placeholder when running several "
            "linters, otherwise they would overwrite each other's events"
        )

    workspace = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    if not workspace:
        workspace = os.getcwd()
        note(
            f"Environment variable BUILD_WORKSPACE_DIRECTORY is not set. "
            f"Assuming {workspace} is the workspace root."
        )

    exit_code = 0
    for linter in linters:
        code = lint(Path(workspace), linter, args)
        if code != 0 and exit_code == 0:
            exit_code = code
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
