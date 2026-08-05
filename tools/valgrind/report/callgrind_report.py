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
import re
import sys
from collections.abc import Iterable
from pathlib import Path

from tools.valgrind.report.metrics import (
    build_metric,
    build_report,
    print_summary,
    read_baseline,
    read_limit,
    write_report,
)

INSTRUCTIONS_FILENAME = "valgrind-callgrind.instructions"
REPORT_JSON_FILENAME = "valgrind-callgrind.report.json"

METRIC_KEY = "cpu_instructions"
METRIC_NAME = "CPU instructions"

DEFAULT_LABEL = "callgrind"
DEFAULT_TOLERANCE_PCT = 5.0

# Only the per-process dumps, so the report files this tool writes into the
# same directory are never mistaken for callgrind output on a re-run. callgrind
# appends .<part> for a multi-part dump and -<tid> under --separate-threads.
_OUTPUT_FILE_RE = re.compile(r"^valgrind-callgrind\.\d+(\.\d+)?(-\d+)?$")

# callgrind reports the run total on a "summary:" line, or "totals:" in older
# output formats. The first field is the instruction count (Ir); later fields
# are the other collected events.
_SUMMARY_RE = re.compile(r"^summary:\s*(\d+)")
_TOTALS_RE = re.compile(r"^totals:\s*(\d+)")


def find_output_files(output_dir: Path) -> list[Path]:
    """Return the per-process callgrind dumps in output_dir, sorted by name."""
    return sorted(p for p in output_dir.iterdir() if _OUTPUT_FILE_RE.match(p.name))


def parse_instructions(path: Path) -> int | None:
    """Return the instruction total of a single callgrind dump, or None."""
    with path.open() as f:
        for line in f:
            match = _SUMMARY_RE.match(line) or _TOTALS_RE.match(line)
            if match:
                return int(match.group(1))
    return None


def sum_instructions(paths: Iterable[Path]) -> int:
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


def run(
    output_dir: Path,
    label: str = DEFAULT_LABEL,
    baseline: Path | None = None,
    baseline_label: str | None = None,
    tolerance_pct: float = DEFAULT_TOLERANCE_PCT,
) -> int:
    """Summarise a callgrind run, gating on the baseline when one is given.

    Returns the exit code: non-zero once the instruction count is more than
    tolerance_pct above the baseline, or the output could not be read at all.
    """
    try:
        measured = sum_instructions(find_output_files(output_dir))
    except (OSError, ValueError) as err:
        print(
            f"Error: could not read callgrind output from {output_dir}: {err}",
            file=sys.stderr,
        )
        return 1

    (output_dir / INSTRUCTIONS_FILENAME).write_text(f"{measured}\n")

    if not baseline:
        print(f"{METRIC_NAME}: {measured:,}")
        return 0

    baseline_file = baseline_label or str(baseline)
    try:
        expected = read_baseline(baseline, METRIC_KEY)
        limit = read_limit(baseline, METRIC_KEY)
    except OSError as err:
        print(
            f"Error: baseline '{baseline_file}' could not be read at '{baseline}': {err}",
            file=sys.stderr,
        )
        return 1
    except ValueError as err:
        print(f"Error: baseline '{baseline_file}' is unusable: {err}", file=sys.stderr)
        return 1

    metric = build_metric(
        METRIC_KEY, METRIC_NAME, "", measured, expected, tolerance_pct, limit
    )
    report = build_report(label, baseline_file, [metric])
    write_report(report, output_dir / REPORT_JSON_FILENAME)

    return print_summary(report)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory holding the valgrind-callgrind.<pid> dumps",
    )
    parser.add_argument(
        "--label",
        default=DEFAULT_LABEL,
        help="Name of the profiled target, shown in the reports",
    )
    parser.add_argument(
        "--baseline",
        default=None,
        type=Path,
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
        default=DEFAULT_TOLERANCE_PCT,
        help="Allowed percentage increase over the baseline",
    )
    args = parser.parse_args(argv)

    return run(
        args.output_dir,
        args.label,
        args.baseline,
        args.baseline_label,
        args.tolerance_pct,
    )


if __name__ == "__main__":
    sys.exit(main())
