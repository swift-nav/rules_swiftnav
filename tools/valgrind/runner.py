#!/usr/bin/env python3
"""Runs a binary under valgrind for the swift_add_valgrind_* macros.

One runner for every tool, invoked as::

    runner.py --tool NAME [runner_flags...] [report_tool [report_args...]] \
        -- [valgrind_flags...] binary [binary_args...]

The report tool half is empty for memcheck, which has nothing to measure. Both
tool paths are passed in because a test's argv[0] is its own name in the
consuming package, not this script's location in the runfiles tree.

Three tokens in the valgrind half expand at run time:
    {OUTPUT_DIR}  -> TEST_UNDECLARED_OUTPUTS_DIR (collected by Bazel)
    {TMPDIR}      -> TEST_TMPDIR (scratch, discarded)
    {RUNFILES}    -> the directory $(location) paths resolve from
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

RUNFILES = Path.cwd()
OUTPUT_DIR = Path(os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR") or tempfile.mkdtemp())
SCRATCH_DIR = Path(os.environ.get("TEST_TMPDIR") or tempfile.mkdtemp())

# DRD prints one line per thread as it exits, among race reports that are noise.
_STACK_USAGE = re.compile(
    r"thread \d+ finished and used \d+ bytes out of \d+ on its stack"
)


def expand(args: list[str]) -> list[str]:
    """Substitute the runtime tokens, and absolutise the binary path.

    The binary is found by valgrind's own rule for where its flags stop: the
    first argument that is not a flag. It has to be absolute because the binary
    may run from a working directory of its own.

    Raises:
        ValueError: if no argument looks like the binary.
    """
    tokens = {
        "{OUTPUT_DIR}": OUTPUT_DIR,
        "{TMPDIR}": SCRATCH_DIR,
        "{RUNFILES}": RUNFILES,
    }
    for token, path in tokens.items():
        args = [a.replace(token, str(path)) for a in args]

    binary = next((i for i, a in enumerate(args) if not a.startswith("-")), None)
    if binary is None:
        raise ValueError(
            f"no binary to run under valgrind, every argument is a flag: {' '.join(args)}"
        )

    args[binary] = str(Path(args[binary]).resolve())
    return args


def workdir(workdir_data: list[str]) -> Path | None:
    """The directory to run the binary from, or None to stay in the runfiles.

    The files are symlinked in by basename, so a config naming its inputs by
    bare filename resolves them and whatever the binary writes lands outside the
    source tree. Two sharing a basename raise rather than shadow each other.
    """
    if not workdir_data:
        return None

    path = SCRATCH_DIR / "workdir"
    path.mkdir(exist_ok=True)
    for f in workdir_data:
        (path / Path(f).name).symlink_to(Path(f).resolve())
    return path


def valgrind(label: str, flags: list[str], args: list[str], cwd: Path | None) -> int:
    """Run one valgrind pass, returning its exit code."""
    print(f"Running {label}...", flush=True)
    return subprocess.run(["valgrind", *flags, *args], cwd=cwd, check=False).returncode


def callgrind(
    args: list[str], cwd: Path | None, opts: argparse.Namespace
) -> tuple[int, list[str]]:
    """Profile CPU instructions. The %p suffix keeps --trace-children dumps apart."""
    out = OUTPUT_DIR / "valgrind-callgrind.%p"
    return valgrind(
        "callgrind",
        ["-q", "--tool=callgrind", f"--callgrind-out-file={out}"],
        args,
        cwd,
    ), []


def drd_stack_usage(args: list[str], cwd: Path | None) -> int:
    """Measure thread stacks in a DRD pass, returning its exit code.

    DRD reports each thread's stack high-water as it exits, which is far cheaper
    than asking massif for stacks. The report file is only written once there is
    something in it, so a pass that produced nothing leaves the reporting tool
    free to fall back on massif's own figure rather than reading an empty file.
    """
    log = SCRATCH_DIR / "drd.log"
    drd = [
        "--tool=drd",
        "--show-stack-usage=yes",
        "--first-race-only=yes",
        f"--log-file={log}",
    ]
    code = valgrind("DRD (stack)", drd, args, cwd)

    usage = (
        [line for line in log.read_text().splitlines() if _STACK_USAGE.search(line)]
        if log.exists()
        else []
    )
    if usage:
        (OUTPUT_DIR / "valgrind-drd.stack_usage.txt").write_text(
            "".join(f"{line}\n" for line in usage)
        )
    else:
        print(
            "Warning: the DRD pass reported no thread stack usage, falling back on massif's own figure."
        )

    return code


def massif(
    args: list[str], cwd: Path | None, opts: argparse.Namespace
) -> tuple[int, list[str]]:
    """Profile memory, optionally measuring thread stacks in a second DRD pass."""
    dumps = SCRATCH_DIR if opts.dumps_to_tmpdir else OUTPUT_DIR
    out = dumps / "valgrind-massif.%p"
    code = valgrind(
        "massif (heap)", ["-q", "--tool=massif", f"--massif-out-file={out}"], args, cwd
    )

    if code == 0 and opts.stack_usage:
        code = drd_stack_usage(args, cwd)

    return code, ["--dump-dir", str(dumps)]


def memcheck(
    args: list[str], cwd: Path | None, opts: argparse.Namespace
) -> tuple[int, list[str]]:
    """Check for memory errors. valgrind's exit code is the test result."""
    xml = OUTPUT_DIR / "valgrind-memcheck.%p.xml"
    code = valgrind(
        "memcheck", ["--tool=memcheck", "--xml=yes", f"--xml-file={xml}"], args, cwd
    )

    if code != 0:
        print(f"Valgrind reported errors. See the XML report: {xml}")
        for report in sorted(OUTPUT_DIR.glob("valgrind-memcheck.*.xml")):
            print(report.read_text())

    return code, []


TOOLS = {"callgrind": callgrind, "massif": massif, "memcheck": memcheck}


def parse(argv: list[str]) -> argparse.Namespace:
    """Parse the runner's own half of the command line, up to the -- separator."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tool",
        required=True,
        choices=sorted(TOOLS),
        help="Valgrind tool to run under",
    )
    parser.add_argument(
        "--workdir-data",
        action="append",
        default=[],
        metavar="PATH",
        help="File to symlink by basename into a working directory to run the binary from",
    )
    parser.add_argument(
        "--stack-usage",
        action="store_true",
        help="massif: measure thread stacks in a DRD pass",
    )
    parser.add_argument(
        "--dumps-to-tmpdir",
        action="store_true",
        help="massif: keep the raw dumps out of the outputs",
    )
    parser.add_argument(
        "report",
        nargs=argparse.REMAINDER,
        help="Reporting tool and its own arguments. Empty for a tool with nothing to measure",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    if "--" not in argv:
        print(
            f"Error: no -- separating the runner's arguments from valgrind's: {' '.join(argv)}",
            file=sys.stderr,
        )
        return 1

    separator = argv.index("--")
    opts = parse(argv[:separator])
    try:
        args = expand(argv[separator + 1 :])
    except ValueError as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    code, dump_dir = TOOLS[opts.tool](args, workdir(opts.workdir_data), opts)
    if code != 0 or not opts.report:
        return code

    # Runfiles-relative, and nothing above ever left the runfiles directory.
    report = [
        opts.report[0],
        "--output-dir",
        str(OUTPUT_DIR),
        *dump_dir,
        *opts.report[1:],
    ]
    return subprocess.run(report, check=False).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
