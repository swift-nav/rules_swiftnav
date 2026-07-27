#!/usr/bin/env python3
"""Merge callgrind baseline reports into one markdown comment.

Takes the ``valgrind-callgrind.report.json`` file of one or more callgrind
targets and prints a single markdown document to stdout: one table row per
target, plus a footer naming each baseline file. CI pipes that straight into a
PR comment, so no formatting logic has to live in the workflow.

Run with Bazel:
    bazel run //tools/valgrind:callgrind_comment -- --commit abc1234 \\
        /abs/path/a/valgrind-callgrind.report.json \\
        /abs/path/b/valgrind-callgrind.report.json
"""

import argparse
import json
import sys

from tools.valgrind.callgrind_report import (
    STATUS_PASS,
    STATUS_REGRESSION,
    STATUS_STALE_BASELINE,
    Report,
)

DEFAULT_MARKER = "<!-- valgrind-callgrind-regression -->"
DEFAULT_TITLE = "Valgrind callgrind: runtime regression"

# Kept to five columns with the numbers right-aligned: GitHub clips a wider
# table behind a horizontal scrollbar. Tolerance and the absolute delta live in
# the footer instead.
TABLE_HEADER = "\n".join(
    [
        "| | Target | CPU instructions | Baseline | Delta |",
        "|:-:|---|--:|--:|--:|",
    ]
)

LEGEND = "✅ within tolerance · ❌ regression · ⚠️ baseline stale"

_STATUS_TEXT = {
    STATUS_PASS: "✅",
    STATUS_REGRESSION: "❌",
    STATUS_STALE_BASELINE: "⚠️",
}


def read_report(path: str) -> Report:
    """Load a report written by callgrind_report."""
    with open(path) as f:
        return json.load(f)


def format_percent(pct: float) -> str:
    """Render a delta percentage, dropping the decimals once they are noise."""
    return f"{pct:+,.0f}%" if abs(pct) >= 1000 else f"{pct:+.2f}%"


def format_row(report: Report) -> str:
    """Render a report as one row of a TABLE_HEADER table."""
    return (
        f"| {_STATUS_TEXT.get(report['status'], report['status'])} "
        f"| `{report['label']}` "
        f"| {report['cpu_instructions']:,} "
        f"| {report['baseline']:,} "
        f"| {format_percent(report['delta_pct'])} |"
    )


def format_detail(report: Report) -> str:
    """Render the per-target footer line kept out of the table."""
    return (
        f"- `{report['label']}` — baseline `{report['baseline_file']}`, "
        f"tolerance ±{report['tolerance_pct']:.2f}%, absolute delta {report['delta']:+,}"
    )


def format_comment(reports: list[Report], marker: str, title: str, commit: str | None) -> str:
    """Render every report as a single markdown comment."""
    # Stable ordering, so an updated comment does not reshuffle its rows when
    # the tests happen to finish in a different order.
    reports = sorted(reports, key=lambda r: r["label"])

    lines = [marker, f"## {title}", "", TABLE_HEADER]
    lines += [format_row(report) for report in reports]
    lines += ["", LEGEND, ""]
    lines += [format_detail(report) for report in reports]
    lines.append("")

    if commit:
        lines.append(f"Commit: `{commit}`")
        lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="+", help="Paths to valgrind-callgrind.report.json files")
    parser.add_argument("--marker", default=DEFAULT_MARKER, help="Hidden marker used to find the comment again")
    parser.add_argument("--title", default=DEFAULT_TITLE, help="Heading of the comment")
    parser.add_argument("--commit", default=None, help="Commit SHA quoted in the footer")
    args = parser.parse_args(argv)

    try:
        reports = [read_report(path) for path in args.reports]
    except (OSError, ValueError) as err:
        print(f"Error: could not read a callgrind report: {err}", file=sys.stderr)
        return 1

    print(format_comment(reports, args.marker, args.title, args.commit))
    return 0


if __name__ == "__main__":
    sys.exit(main())
