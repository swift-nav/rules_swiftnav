#!/usr/bin/env python3
"""Merge valgrind profiling reports into one markdown PR comment.

Takes the report json of one or more profiled targets and prints a single
markdown document to stdout: a summary table giving each target a verdict, then
a collapsible block per target holding its full metric table. CI pipes that
straight into a PR comment, so no formatting logic has to live in the workflow.

Requirements:
  - One comment per PR, rewritten in place. The marker is how CI finds it again.
  - Any number of targets, any number of metrics each — callgrind today, massif
    and DRD stack usage later.
  - The summary stays narrow. GitHub hides a wider table behind a scrollbar.
  - Status is a symbol carrying its wording as a tooltip, so there is no legend.
  - Detail sits in a collapsed block. The summary alone answers "did it regress".
  - Rows are sorted by label, so rewriting the comment never reshuffles them.

Run with Bazel:
    bazel run //tools/valgrind/report:pr_comment -- --commit abc1234 \\
        /abs/path/a/valgrind-callgrind.report.json \\
        /abs/path/b/valgrind-callgrind.report.json
"""

import argparse
import sys

from tools.valgrind.report.metrics import (
    STATUS_PASS,
    STATUS_REGRESSION,
    STATUS_STALE_BASELINE,
    Metric,
    Report,
    find_metric,
    format_baseline,
    format_delta,
    format_value,
    read_report,
)

DEFAULT_MARKER = "<!-- valgrind-callgrind-regression -->"
DEFAULT_TITLE = "Valgrind callgrind: runtime regression"

# The metric whose delta earns a column in the summary table.
SUMMARY_METRIC_KEY = "cpu_instructions"

SUMMARY_HEADER = "\n".join(
    [
        "| Target | Verdict | CPU regression |",
        "|---|:-:|--:|",
    ]
)

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
}

_STATUS_HINT = {
    STATUS_PASS: "within tolerance",
    STATUS_REGRESSION: "regression: grew past the tolerance",
    STATUS_STALE_BASELINE: "baseline stale: improved past the tolerance",
}


def format_percent(pct: float) -> str:
    """Render a delta percentage, dropping the decimals once they are noise."""
    return f"{pct:+,.0f}%" if abs(pct) >= 1000 else f"{pct:+.2f}%"


def format_status(status: str) -> str:
    """Render a status as its symbol, with the wording as a hover tooltip."""
    emoji = _STATUS_EMOJI.get(status, status)
    hint = _STATUS_HINT.get(status)
    return f'<abbr title="{hint}">{emoji}</abbr>' if hint else emoji


def format_summary_row(report: Report) -> str:
    """Render one target as a row of a SUMMARY_HEADER table."""
    summary_metric = find_metric(report, SUMMARY_METRIC_KEY)
    regression = format_percent(summary_metric["delta_pct"]) if summary_metric else "—"
    return f"| `{report['label']}` | {format_status(report['status'])} | {regression} |"


def format_metric_row(metric: Metric) -> str:
    """Render one metric as a row of a METRIC_HEADER table."""
    return (
        f"| {metric['name']} "
        f"| {format_value(metric)} "
        f"| {format_baseline(metric)} "
        f"| {format_delta(metric)} ({format_percent(metric['delta_pct'])}) |"
    )


def format_details(report: Report) -> str:
    """Render a target's metrics inside a collapsible block."""
    tolerances = {metric["tolerance_pct"] for metric in report["metrics"]}
    tolerance = f"±{next(iter(tolerances)):.2f}%" if len(tolerances) == 1 else "per metric"

    return "\n".join(
        [
            "<details>",
            f"<summary>{_STATUS_EMOJI.get(report['status'], report['status'])} {report['label']}</summary>",
            "",
            METRIC_HEADER,
            *[format_metric_row(metric) for metric in report["metrics"]],
            "",
            f"Baseline: `{report['baseline_file']}` · tolerance {tolerance}",
            "",
            "</details>",
        ]
    )


def format_comment(reports: list[Report], marker: str, title: str, commit: str | None) -> str:
    """Render every report as a single markdown comment."""
    # Stable ordering, so an updated comment does not reshuffle its rows when
    # the tests happen to finish in a different order.
    reports = sorted(reports, key=lambda r: r["label"])

    lines = [marker, f"## {title}", "", SUMMARY_HEADER]
    lines += [format_summary_row(report) for report in reports]
    lines.append("")

    for report in reports:
        lines.append(format_details(report))
        lines.append("")

    if commit:
        lines.append(f"Commit: `{commit}`")
        lines.append("")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", nargs="+", help="Paths to valgrind report json files")
    parser.add_argument("--marker", default=DEFAULT_MARKER, help="Hidden marker used to find the comment again")
    parser.add_argument("--title", default=DEFAULT_TITLE, help="Heading of the comment")
    parser.add_argument("--commit", default=None, help="Commit SHA quoted in the footer")
    args = parser.parse_args(argv)

    try:
        reports = [read_report(path) for path in args.reports]
    except (OSError, ValueError) as err:
        print(f"Error: could not read a valgrind report: {err}", file=sys.stderr)
        return 1

    print(format_comment(reports, args.marker, args.title, args.commit))
    return 0


if __name__ == "__main__":
    sys.exit(main())
