#!/usr/bin/env python3
"""Summarise callgrind output and optionally gate on an instruction baseline.

Reads the raw ``valgrind-callgrind.<pid>`` files a callgrind run leaves in the
output directory, sums the instruction counts (Ir) across every process, and
writes the total to ``valgrind-callgrind.instructions``.

When an instructions baseline is supplied the total is compared against it and
the tool exits non-zero once the measured count exceeds the baseline by more
than the tolerance, which turns a plain ``bazel test`` into a runtime
regression gate. Two extra report files are written so CI can surface the
numbers without re-parsing anything:

    valgrind-callgrind.report.json   machine readable result
    valgrind-callgrind.report.md     markdown table for a PR comment

The json report is self-contained: it carries the label and the baseline path
alongside the numbers, so the reports of several callgrind targets can be
merged into a single comment by rendering one ``format_row`` per report.

The baseline file holds nothing but the expected count as a single positive
integer, which is the exact format of the generated ``.instructions`` file.
Refreshing a baseline is therefore a copy of the one over the other.

Run with Bazel:
    bazel run //tools/valgrind:callgrind_report -- --output-dir <dir>
"""

import argparse
import json
import os
import re
import sys
from collections.abc import Iterable
from typing import TypedDict

INSTRUCTIONS_FILENAME = "valgrind-callgrind.instructions"
REPORT_JSON_FILENAME = "valgrind-callgrind.report.json"
REPORT_MD_FILENAME = "valgrind-callgrind.report.md"

STATUS_PASS = "pass"
STATUS_REGRESSION = "regression"
STATUS_STALE_BASELINE = "stale-baseline"

_STATUS_TEXT = {
    STATUS_PASS: "✅ pass",
    STATUS_REGRESSION: "❌ regression",
    STATUS_STALE_BASELINE: "⚠️ baseline stale",
}

TABLE_HEADER = "\n".join(
    [
        "| Target | CPU instructions | Baseline | Delta | Tolerance | Status |",
        "|--------|------------------|----------|-------|-----------|--------|",
    ]
)

# Only the per-process dumps, so the report files this tool writes into the
# same directory are never mistaken for callgrind output on a re-run.
_OUTPUT_FILE_RE = re.compile(r"^valgrind-callgrind\.\d+$")

# callgrind reports the run total on a "summary:" line, or "totals:" in older
# output formats. The first field is the instruction count (Ir); later fields
# are the other collected events.
_SUMMARY_RE = re.compile(r"^summary:\s*(\d+)")
_TOTALS_RE = re.compile(r"^totals:\s*(\d+)")


class Report(TypedDict):
    """A callgrind measurement compared against its baseline."""

    label: str
    cpu_instructions: int
    baseline: int
    baseline_file: str
    delta: int
    delta_pct: float
    tolerance_pct: float
    status: str


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


def read_baseline(path: str | os.PathLike) -> int:
    """Read the expected instruction count from a baseline file.

    Raises:
        ValueError: if the file does not hold a single positive integer. Zero is
            rejected too: a placeholder nobody has filled in is not something a
            measurement can be compared against.
    """
    with open(path) as f:
        content = f.read().strip()
    if not re.fullmatch(r"\d+", content) or int(content) == 0:
        raise ValueError(f"expected a single positive integer, got {content!r}")
    return int(content)


def build_report(label: str, measured: int, baseline: int, baseline_file: str, tolerance_pct: float) -> Report:
    """Compare a measured count against a baseline within a percent tolerance."""
    delta = measured - baseline
    delta_pct = (delta / baseline) * 100

    if delta_pct > tolerance_pct:
        status = STATUS_REGRESSION
    elif delta_pct < -tolerance_pct:
        status = STATUS_STALE_BASELINE
    else:
        status = STATUS_PASS

    return Report(
        label=label,
        cpu_instructions=measured,
        baseline=baseline,
        baseline_file=baseline_file,
        delta=delta,
        delta_pct=delta_pct,
        tolerance_pct=tolerance_pct,
        status=status,
    )


def format_row(report: Report) -> str:
    """Render a report as one row of a TABLE_HEADER table."""
    return (
        f"| `{report['label']}` "
        f"| {report['cpu_instructions']:,} "
        f"| {report['baseline']:,} "
        f"| {report['delta']:+,} ({report['delta_pct']:+.2f}%) "
        f"| ±{report['tolerance_pct']:.2f}% "
        f"| {_STATUS_TEXT[report['status']]} |"
    )


def format_markdown(report: Report) -> str:
    """Render a report as a standalone markdown table."""
    return "\n".join(
        [
            TABLE_HEADER,
            format_row(report),
            "",
            f"Baseline file: `{report['baseline_file']}`",
            "",
        ]
    )


def _refresh_hint(measured: int, baseline_file: str) -> str:
    return f"  echo {measured} > {baseline_file}"


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
        "--instructions-baseline",
        default=None,
        help="File holding the expected instruction count as a single integer",
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

    if not args.instructions_baseline:
        return 0

    baseline_file = args.baseline_label or args.instructions_baseline
    try:
        baseline = read_baseline(args.instructions_baseline)
    except OSError:
        print(f"Error: instructions baseline '{baseline_file}' not found", file=sys.stderr)
        return 1
    except ValueError as err:
        print(f"Error: instructions baseline '{baseline_file}' is malformed: {err}", file=sys.stderr)
        return 1

    report = build_report(args.label, measured, baseline, baseline_file, args.tolerance_pct)

    with open(os.path.join(args.output_dir, REPORT_JSON_FILENAME), "w") as f:
        json.dump(report, f, indent=2)
        f.write("\n")
    with open(os.path.join(args.output_dir, REPORT_MD_FILENAME), "w") as f:
        f.write(format_markdown(report))

    print(f"Baseline:         {baseline:,}  ({baseline_file})")
    print(f"Delta:            {report['delta']:+,} ({report['delta_pct']:+.2f}%), tolerance ±{args.tolerance_pct:.2f}%")

    if report["status"] == STATUS_REGRESSION:
        print(
            f"\nError: runtime regression. CPU instructions grew {report['delta_pct']:+.2f}%, more than the "
            f"allowed {args.tolerance_pct:.2f}%.\nIf the increase is expected, refresh the baseline with:\n"
            f"{_refresh_hint(measured, baseline_file)}",
            file=sys.stderr,
        )
        return 1

    if report["status"] == STATUS_STALE_BASELINE:
        # An improvement this large means the baseline no longer guards this
        # target, so say so loudly without failing the test.
        print(
            f"\nWarning: measured count is {-report['delta_pct']:.2f}% below the baseline, which no longer "
            f"guards this target.\nConsider refreshing it with:\n{_refresh_hint(measured, baseline_file)}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
