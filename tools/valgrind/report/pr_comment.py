#!/usr/bin/env python3
"""Merge valgrind profiling reports into one markdown PR comment.

Takes the report json of one or more profiled targets and prints a single
markdown document to stdout: one block per target, headed by its name and
verdict and holding its full metric table. CI pipes that straight into a PR
comment, so no formatting logic has to live in the workflow.

Requirements:
  - One comment per PR, rewritten in place. The marker is how CI finds it again.
  - Any number of targets, any number of metrics each — callgrind instruction
    counts, massif heap sizes, DRD stack high-water.
  - Every block is open on arrival; nothing worth reading hides behind a click.
  - The verdict is a symbol plus the reason in words. GitHub strips title
    attributes, so hover tooltips are not an option.
  - Blocks are sorted by label, so rewriting the comment never reshuffles them.
  - Byte quantities can be rendered in a unit of the reader's choosing, for a
    target whose figures are far from the one they were measured in: a decoder
    peaking at 215 bytes of heap extra is "0.000 MB" but "0.210 KB".

Run with Bazel:
    bazel run //tools/valgrind/report:pr_comment -- --commit abc1234 \\
        --unit KB \\
        /abs/path/a/valgrind-callgrind.report.json \\
        /abs/path/b/valgrind-callgrind.report.json
"""

import argparse
import sys
from pathlib import Path

from tools.valgrind.report.metrics import (
    STATUS_OVER_LIMIT,
    STATUS_PASS,
    STATUS_REGRESSION,
    STATUS_STALE_BASELINE,
    Metric,
    Report,
    format_baseline,
    format_delta,
    format_limit,
    format_value,
    read_report,
)

DEFAULT_MARKER = "<!-- valgrind-callgrind-regression -->"
DEFAULT_TITLE = "Valgrind analysis"

# A metric measured in one of these converts to any other by ratio. Everything
# else — an instruction count, whose unit is empty — is left as measured.
_UNIT_BYTES = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
UNITS = sorted(_UNIT_BYTES)

METRIC_HEADER = "\n".join(
    [
        "| Metric | Value | Baseline | Delta |",
        "|---|--:|--:|--:|",
    ]
)

_STATUS_EMOJI = {
    STATUS_PASS: "✅",
    STATUS_REGRESSION: "❌",
    STATUS_STALE_BASELINE: "⚠️",
    STATUS_OVER_LIMIT: "🚫",
}

_STATUS_WORDING = {
    STATUS_REGRESSION: "regression",
    STATUS_STALE_BASELINE: "baseline stale",
    STATUS_OVER_LIMIT: "over limit",
}


def convert_metric(metric: Metric, unit: str) -> Metric:
    """Rescale a byte quantity to unit, leaving anything else as measured.

    Only the absolute numbers move; delta_pct and tolerance_pct are ratios and
    mean the same in any unit.
    """
    source = metric["unit"]
    if source == unit or source not in _UNIT_BYTES:
        return metric

    factor = _UNIT_BYTES[source] / _UNIT_BYTES[unit]
    converted = dict(metric)
    for key in ("value", "baseline", "delta", "max"):
        if converted[key] is not None:
            converted[key] *= factor
    converted["unit"] = unit
    return Metric(**converted)


def convert_report(report: Report, unit: str | None) -> Report:
    """Render every byte quantity of a report in unit, or as measured if None.

    Display only: the baseline file the block points at keeps the unit it was
    written in, which is the one a refresh has to be typed back in.
    """
    if unit is None:
        return report

    converted = dict(report)
    converted["metrics"] = [
        convert_metric(metric, unit) for metric in report["metrics"]
    ]
    return Report(**converted)


def format_percent(pct: float) -> str:
    """Render a delta percentage, dropping the decimals once they are noise."""
    return f"{pct:+,.0f}%" if abs(pct) >= 1000 else f"{pct:+.2f}%"


def format_verdict(status: str) -> str:
    """Render a status as its symbol."""
    return _STATUS_EMOJI.get(status, status)


def format_reason(report: Report) -> str:
    """Say in words why a target got its verdict, naming the metrics at fault."""
    if report["status"] == STATUS_PASS:
        return "within tolerance"
    at_fault = [
        metric["name"]
        for metric in report["metrics"]
        if metric["status"] == report["status"]
    ]
    return f"{', '.join(at_fault)} {_STATUS_WORDING[report['status']]}"


def format_summary_line(report: Report) -> str:
    """Render the heading of a target's block: verdict, name, and why.

    <code> rather than backticks: GitHub does not render markdown inside a raw
    <summary> element. A passing target needs no reason spelled out.
    """
    heading = f"{format_verdict(report['status'])} <code>{report['label']}</code>"
    if report["status"] == STATUS_PASS:
        return heading
    return f"{heading} — {format_reason(report)}"


def format_metric_row(metric: Metric) -> str:
    """Render one metric as a row of a METRIC_HEADER table."""
    return (
        f"| {metric['name']} "
        f"| {format_value(metric)} "
        f"| {format_baseline(metric)} "
        f"| {format_delta(metric)} ({format_percent(metric['delta_pct'])}) |"
    )


def format_limits(report: Report) -> str:
    """Name the metrics that carry an absolute ceiling, empty if none do.

    Kept out of the table so the four columns stay narrow; only a minority of
    metrics have a ceiling at all.
    """
    limited = [
        f"`{metric['key']}` ≤ {format_limit(metric)}"
        for metric in report["metrics"]
        if metric["max"] is not None
    ]
    return f"Limits: {', '.join(limited)}" if limited else ""


def format_details(report: Report) -> str:
    """Render a target's metrics inside an expanded block."""
    tolerances = {metric["tolerance_pct"] for metric in report["metrics"]}
    tolerance = (
        f"±{next(iter(tolerances)):.2f}%" if len(tolerances) == 1 else "per metric"
    )

    lines = [
        "<details open>",
        f"<summary>{format_summary_line(report)}</summary>",
        "",
        METRIC_HEADER,
        *[format_metric_row(metric) for metric in report["metrics"]],
        "",
        f"Baseline: `{report['baseline_file']}` · tolerance {tolerance}",
    ]

    limits = format_limits(report)
    if limits:
        lines.append("")
        lines.append(limits)

    lines += ["", "</details>"]
    return "\n".join(lines)


def format_comment(
    reports: list[Report], marker: str, title: str, commit: str | None
) -> str:
    """Render every report as a single markdown comment."""
    # Stable ordering, so an updated comment does not reshuffle its rows when
    # the tests happen to finish in a different order.
    reports = sorted(reports, key=lambda r: r["label"])

    lines = [marker, f"## {title}", ""]

    for report in reports:
        lines.append(format_details(report))
        lines.append("")

    if commit:
        lines.append(f"Commit: `{commit}`")
        lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "reports", nargs="+", type=Path, help="Paths to valgrind report json files"
    )
    parser.add_argument(
        "--marker",
        default=DEFAULT_MARKER,
        help="Hidden marker used to find the comment again",
    )
    parser.add_argument("--title", default=DEFAULT_TITLE, help="Heading of the comment")
    parser.add_argument(
        "--commit", default=None, help="Commit SHA quoted in the footer"
    )
    parser.add_argument(
        "--unit",
        default=None,
        choices=UNITS,
        help="Render byte quantities in this unit instead of the one they were "
        "measured in. Leave unset to keep the measured unit",
    )
    args = parser.parse_args(argv)

    try:
        reports = [
            convert_report(read_report(path), args.unit) for path in args.reports
        ]
    except (OSError, ValueError) as err:
        print(f"Error: could not read a valgrind report: {err}", file=sys.stderr)
        return 1

    print(format_comment(reports, args.marker, args.title, args.commit))
    return 0


if __name__ == "__main__":
    sys.exit(main())
