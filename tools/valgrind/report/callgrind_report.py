#!/usr/bin/env python3
"""Summarise callgrind output and optionally gate on an instruction baseline.

Reads the raw ``valgrind-callgrind.<pid>`` files a callgrind run leaves in the
output directory, sums the instruction counts (Ir) across every process, and
writes the total to ``valgrind-callgrind.instructions``.

When an instructions baseline is supplied the total is compared against it and
the tool exits non-zero once the measured count exceeds the baseline by more
than the tolerance, which turns a plain ``bazel test`` into a runtime
regression gate. The comparison is also written to
``valgrind-callgrind.report.json`` in the shared report format, so pr_comment
can merge it with the reports of other targets.

The baseline is a json file mapping metric keys to their expected values, so a
target that later also measures memory keeps every baseline in one file::

    {"cpu_instructions": 28032185999}

Run with Bazel:
    bazel run //tools/valgrind/report:callgrind_report -- --output-dir <dir>
"""

import argparse
import os
import re
import sys
from collections.abc import Iterable

from tools.valgrind.report.metrics import (
    STATUS_REGRESSION,
    STATUS_STALE_BASELINE,
    build_metric,
    build_report,
    read_baseline,
    write_report,
)

INSTRUCTIONS_FILENAME = "valgrind-callgrind.instructions"
REPORT_JSON_FILENAME = "valgrind-callgrind.report.json"

METRIC_KEY = "cpu_instructions"
METRIC_NAME = "CPU instructions"

# Only the per-process dumps, so the report files this tool writes into the
# same directory are never mistaken for callgrind output on a re-run.
_OUTPUT_FILE_RE = re.compile(r"^valgrind-callgrind\.\d+$")

# callgrind reports the run total on a "summary:" line, or "totals:" in older
# output formats. The first field is the instruction count (Ir); later fields
# are the other collected events.
_SUMMARY_RE = re.compile(r"^summary:\s*(\d+)")
_TOTALS_RE = re.compile(r"^totals:\s*(\d+)")


def find_output_files(output_dir: str) -> list[str]:
    """Return the per-process callgrind dumps in output_dir, sorted by name."""
    return sorted(os.path.join(output_dir, name) for name in os.listdir(output_dir) if _OUTPUT_FILE_RE.match(name))


def parse_instructions(path: str | os.PathLike) -> int | None:
    """Return the instruction total of a single callgrind dump, or None."""
    with open(path) as f:
        for line in f:
            match = _SUMMARY_RE.match(line) or _TOTALS_RE.match(line)
            if match:
                return int(match.group(1))
    return None


def sum_instructions(paths: Iterable[str | os.PathLike]) -> int:
    """Sum the instruction totals of every callgrind dump.

    Raises:
        ValueError: if no dump carried a usable total.
    """
    total = 0
    found = False
    for path in paths:
        count = parse_instructions(path)
        if count is None:
            continue
        total += count
        found = True
    if not found:
        raise ValueError("no callgrind output files with an instruction total")
    return total


def _refresh_hint(measured: int, baseline_file: str) -> str:
    return f'  set "{METRIC_KEY}": {measured} in {baseline_file}'


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory holding the valgrind-callgrind.<pid> dumps",
    )
    parser.add_argument(
        "--label",
        default="callgrind",
        help="Name of the profiled target, shown in the reports",
    )
    parser.add_argument(
        "--baseline",
        default=None,
        help=f"Json file whose {METRIC_KEY!r} entry is the expected instruction count",
    )
    parser.add_argument(
        "--baseline-label",
        default=None,
        help="Workspace-relative baseline path, used only in the reports",
    )
    parser.add_argument(
        "--tolerance-pct",
        type=float,
        default=5.0,
        help="Allowed percentage increase over the baseline",
    )
    args = parser.parse_args(argv)

    try:
        measured = sum_instructions(find_output_files(args.output_dir))
    except (OSError, ValueError) as err:
        print(f"Error: could not read callgrind output from {args.output_dir}: {err}", file=sys.stderr)
        return 1

    with open(os.path.join(args.output_dir, INSTRUCTIONS_FILENAME), "w") as f:
        f.write(f"{measured}\n")
    print(f"CPU instructions: {measured:,}")

    if not args.baseline:
        return 0

    baseline_file = args.baseline_label or args.baseline
    try:
        baseline = read_baseline(args.baseline, METRIC_KEY)
    except OSError:
        print(f"Error: baseline '{baseline_file}' not found", file=sys.stderr)
        return 1
    except ValueError as err:
        print(f"Error: baseline '{baseline_file}' is unusable: {err}", file=sys.stderr)
        return 1

    metric = build_metric(METRIC_KEY, METRIC_NAME, "", measured, baseline, args.tolerance_pct)
    report = build_report(args.label, baseline_file, [metric])
    write_report(report, os.path.join(args.output_dir, REPORT_JSON_FILENAME))

    print(f"Baseline:         {baseline:,.0f}  ({baseline_file})")
    print(
        f"Delta:            {metric['delta']:+,.0f} ({metric['delta_pct']:+.2f}%), tolerance ±{args.tolerance_pct:.2f}%"
    )

    if report["status"] == STATUS_REGRESSION:
        print(
            f"\nError: runtime regression. CPU instructions grew {metric['delta_pct']:+.2f}%, more than the "
            f"allowed {args.tolerance_pct:.2f}%.\nIf the increase is expected, refresh the baseline with:\n"
            f"{_refresh_hint(measured, baseline_file)}",
            file=sys.stderr,
        )
        return 1

    if report["status"] == STATUS_STALE_BASELINE:
        # An improvement this large means the baseline no longer guards this
        # target, so say so loudly without failing the test.
        print(
            f"\nWarning: measured count is {-metric['delta_pct']:.2f}% below the baseline, which no longer "
            f"guards this target.\nConsider refreshing it with:\n{_refresh_hint(measured, baseline_file)}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
