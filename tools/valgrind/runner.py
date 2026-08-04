#!/usr/bin/env python3
"""Runs a binary under valgrind for the swift_add_valgrind_* macros.

One runner for every tool, invoked as::

    runner.py --tool NAME [runner_flags...] [report_tool [report_args...]] \
        -- [valgrind_flags...] binary [binary_args...]

The report tool half is empty for memcheck, which has nothing to measure. Both
tool paths are passed in because a test's argv[0] is its own name in the
consuming package, not this script's location in the runfiles tree.

memcheck runs as a test, where the directories come from the test environment;
callgrind and massif run as a build action, which has none, so both directories
are passable as flags. Three tokens in the valgrind half expand at run time:
    {OUTPUT_DIR}  -> --output-dir, where valgrind's own output is written
    {TMPDIR}      -> --tmpdir, scratch, discarded
    {RUNFILES}    -> the directory $(location) paths resolve from

Setting VALGRIND_DUMP_DIR in the environment overrides --output-dir, to keep the
raw dumps of a build action for ms_print or KCacheGrind::

    bazel build --action_env=VALGRIND_DUMP_DIR=/tmp/dumps //pkg:target.profile
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# DRD prints one line per thread as it exits, among race reports that are noise.
_STACK_USAGE = re.compile(
    r"thread \d+ finished and used \d+ bytes out of \d+ on its stack"
)


def find_binary(args: list[str]) -> int:
    """Index of the binary in valgrind's half of the command line.

    Found by valgrind's own rule for where its flags stop: the first argument
    that is not a flag.

    Raises:
        ValueError: if no argument looks like the binary.
    """
    binary = next((i for i, a in enumerate(args) if not a.startswith("-")), None)
    if binary is None:
        raise ValueError(
            f"no binary to run under valgrind, every argument is a flag: {' '.join(args)}"
        )
    return binary


def expand(args: list[str], output_dir: Path, tmpdir: Path) -> list[str]:
    """Substitute the runtime tokens, and absolutise the binary path.

    The binary has to be absolute because it may run from a working directory of
    its own, and because its runfiles tree is found beside it.

    Raises:
        ValueError: if no argument looks like the binary.
    """
    tokens = {
        "{OUTPUT_DIR}": output_dir,
        "{TMPDIR}": tmpdir,
        "{RUNFILES}": Path.cwd(),
    }
    for token, path in tokens.items():
        args = [a.replace(token, str(path)) for a in args]

    binary = find_binary(args)
    args[binary] = str(Path(args[binary]).resolve())
    return args


def workdir(workdir_data: list[str], tmpdir: Path) -> Path | None:
    """The directory to run the binary from, or None to stay in the runfiles.

    The files are symlinked in by basename, so a config naming its inputs by
    bare filename resolves them and whatever the binary writes lands outside the
    source tree. Two sharing a basename raise rather than shadow each other.
    """
    if not workdir_data:
        return None

    path = tmpdir / "workdir"
    path.mkdir(exist_ok=True)
    for f in workdir_data:
        (path / Path(f).name).symlink_to(Path(f).resolve())
    return path


def child_env(binary: Path, tmpdir: Path, extra: list[str]) -> dict[str, str]:
    """The environment to run the profiled binary in.

    Under a test the binary lives inside the test's own runfiles tree, so the
    inherited environment already describes it and is left alone. Under a build
    action the runner is a py_binary of its own, and everything it inherited
    describes *its* runfiles: a binary that resolved its data against those
    would look in the wrong tree. So point it at its own, and stand in for the
    test variables a swift_cc_test would otherwise be given.
    """
    env = dict(os.environ)
    runfiles = binary.with_name(binary.name + ".runfiles")
    manifest = binary.with_name(binary.name + ".runfiles_manifest")

    if runfiles.is_dir():
        env["RUNFILES_DIR"] = str(runfiles)
        # The runfiles libraries prefer the manifest when both are set.
        env.pop("RUNFILES_MANIFEST_FILE", None)
        env.setdefault("TEST_SRCDIR", str(runfiles))
    elif manifest.is_file():
        env["RUNFILES_MANIFEST_FILE"] = str(manifest)
        env.pop("RUNFILES_DIR", None)
    else:
        return {**env, **dict(pair.split("=", 1) for pair in extra)}

    # A python parent would leak its interpreter's view of the world onto a
    # child that happens to be python too.
    for name in list(env):
        if name.startswith(("PYTHON", "RULES_PYTHON")) or name == "VIRTUAL_ENV":
            del env[name]

    env.setdefault("TEST_TMPDIR", str(tmpdir))
    env.update(dict(pair.split("=", 1) for pair in extra))
    return env


def valgrind(
    label: str,
    flags: list[str],
    args: list[str],
    cwd: Path | None,
    env: dict[str, str] | None = None,
) -> int:
    """Run one valgrind pass, returning its exit code."""
    print(f"Running {label}...", flush=True)
    return subprocess.run(
        ["valgrind", *flags, *args], cwd=cwd, env=env, check=False
    ).returncode


def callgrind(args: list[str], cwd: Path | None, opts: argparse.Namespace) -> int:
    """Profile CPU instructions. The %p suffix keeps --trace-children dumps apart."""
    out = opts.output_dir / "valgrind-callgrind.%p"
    return valgrind(
        "callgrind",
        ["-q", "--tool=callgrind", f"--callgrind-out-file={out}"],
        args,
        cwd,
        opts.env,
    )


def drd_stack_usage(args: list[str], cwd: Path | None, opts: argparse.Namespace) -> int:
    """Measure thread stacks in a DRD pass, returning its exit code.

    DRD reports each thread's stack high-water as it exits, which is far cheaper
    than asking massif for stacks. The report file is only written once there is
    something in it, so a pass that produced nothing leaves the measuring tool
    free to fall back on massif's own figure rather than reading an empty file.
    """
    # The %p suffix stops --trace-children children truncating each other's log.
    log = opts.tmpdir / "drd.log.%p"
    drd = [
        "--tool=drd",
        "--show-stack-usage=yes",
        "--first-race-only=yes",
        f"--log-file={log}",
    ]
    code = valgrind("DRD (stack)", drd, args, cwd, opts.env)

    usage = [
        line
        for path in sorted(opts.tmpdir.glob("drd.log.*"))
        for line in path.read_text().splitlines()
        if _STACK_USAGE.search(line)
    ]
    if usage:
        (opts.output_dir / "valgrind-drd.stack_usage.txt").write_text(
            "".join(f"{line}\n" for line in usage)
        )
    else:
        print(
            "Warning: the DRD pass reported no thread stack usage, falling back on massif's own figure."
        )

    return code


def massif(args: list[str], cwd: Path | None, opts: argparse.Namespace) -> int:
    """Profile memory, optionally measuring thread stacks in a second DRD pass."""
    out = opts.output_dir / "valgrind-massif.%p"
    code = valgrind(
        "massif (heap)",
        ["-q", "--tool=massif", f"--massif-out-file={out}"],
        args,
        cwd,
        opts.env,
    )

    if code == 0 and opts.stack_usage:
        code = drd_stack_usage(args, cwd, opts)

    return code


def memcheck(args: list[str], cwd: Path | None, opts: argparse.Namespace) -> int:
    """Check for memory errors. valgrind's exit code is the test result."""
    xml = opts.output_dir / "valgrind-memcheck.%p.xml"
    code = valgrind(
        "memcheck",
        ["--tool=memcheck", "--xml=yes", f"--xml-file={xml}"],
        args,
        cwd,
        opts.env,
    )

    if code != 0:
        print(f"Valgrind reported errors. See the XML report: {xml}")
        for report in sorted(opts.output_dir.glob("valgrind-memcheck.*.xml")):
            print(report.read_text())

    return code


TOOLS = {"callgrind": callgrind, "massif": massif, "memcheck": memcheck}


def resolve_dirs(opts: argparse.Namespace) -> list[Path]:
    """Settle the output and scratch directories on opts.

    Neither is required, so the runner is still runnable by hand outside Bazel.
    VALGRIND_DUMP_DIR wins over the flag: a build action passes no directory of
    its own, and naming one is the only way to keep the dumps a build would
    otherwise throw away.

    Returns the directories it invented, which are the caller's to remove: a
    build action outlives no test environment to clean up after it, and a
    callgrind dump left behind every build runs to tens of megabytes.
    """
    invented = []

    override = os.environ.get("VALGRIND_DUMP_DIR")
    if override:
        opts.output_dir = Path(override)
        opts.output_dir.mkdir(parents=True, exist_ok=True)
    elif opts.output_dir is None:
        collected = os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR")
        if collected:
            opts.output_dir = Path(collected)
        else:
            opts.output_dir = Path(tempfile.mkdtemp())
            invented.append(opts.output_dir)

    if opts.tmpdir is None:
        scratch = os.environ.get("TEST_TMPDIR")
        if scratch:
            opts.tmpdir = Path(scratch)
        else:
            opts.tmpdir = Path(tempfile.mkdtemp())
            invented.append(opts.tmpdir)

    return invented


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
        "--output-dir",
        default=None,
        type=Path,
        help="Where valgrind writes its output. Defaults to TEST_UNDECLARED_OUTPUTS_DIR",
    )
    parser.add_argument(
        "--tmpdir",
        default=None,
        type=Path,
        help="Scratch directory. Defaults to TEST_TMPDIR",
    )
    parser.add_argument(
        "--workdir-data",
        action="append",
        default=[],
        metavar="PATH",
        help="File to symlink by basename into a working directory to run the binary from",
    )
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="Environment variable for the profiled binary, overriding the inherited one",
    )
    parser.add_argument(
        "--stack-usage",
        action="store_true",
        help="massif: measure thread stacks in a DRD pass",
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
    invented = resolve_dirs(opts)
    try:
        return run(opts, argv[separator + 1 :])
    finally:
        for path in invented:
            shutil.rmtree(path, ignore_errors=True)


def run(opts: argparse.Namespace, valgrind_args: list[str]) -> int:
    """Run the tool, then the measuring tool if there is one, and report either's code."""
    args = expand(valgrind_args, opts.output_dir, opts.tmpdir)
    opts.env = child_env(Path(args[find_binary(args)]), opts.tmpdir, opts.env)

    code = TOOLS[opts.tool](args, workdir(opts.workdir_data, opts.tmpdir), opts)
    if code != 0 or not opts.report:
        return code

    # Runfiles-relative, and nothing above ever left the runfiles directory.
    report = [opts.report[0], "--output-dir", str(opts.output_dir), *opts.report[1:]]
    return subprocess.run(report, check=False).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
