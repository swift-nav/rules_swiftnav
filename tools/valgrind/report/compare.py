#!/usr/bin/env python3
"""Gate a valgrind measurement against its baseline.

Reads the measurement json a measuring tool wrote, compares every metric in it
against the matching entry in a baseline file, and exits non-zero on a
regression larger than the tolerance or on exceeding an absolute limit — which
is what turns a plain ``bazel test`` into a regression gate. The comparison is
also written out in the shared report format, so pr_comment can merge it with
the reports of other targets.

This is the second half of a profiled target, split from the measuring half so
that editing a baseline re-runs only the comparison and not valgrind. It knows
nothing about which profiler produced the measurement: every metric carries its
own key, display name and unit.

The baseline is a json file mapping metric keys to their expected values, with
an optional ``_max`` ceiling beside any of them::

    {"memory_heap_mb": 15.405, "memory_heap_mb_max": 50}

Run with Bazel:
    bazel run //tools/valgrind/report:compare -- --measurement <file>

As the generated gate test it writes its report into the test's undeclared
outputs, under the same name the measuring tool used to write it, so nothing
downstream of the reports had to change when the two halves were split.
"""

import argparse
import os
import sys
from pathlib import Path

from metrics import (
    Measurement,
    build_metric,
    build_report,
    print_measurement,
    print_summary,
    read_baseline,
    read_limit,
    read_measurement,
    write_report,
)

DEFAULT_TOLERANCE_PCT = 5.0


def run(
    measurement_path: Path,
    baseline: Path | None = None,
    baseline_label: str | None = None,
    tolerance_pct: float = DEFAULT_TOLERANCE_PCT,
    report_out: Path | None = None,
) -> int:
    """Compare a measurement against a baseline, when one is given.

    Without a baseline the measurement is only printed, so a target can profile
    before anyone has decided what it should cost. Returns the exit code:
    non-zero once a metric is more than tolerance_pct above its baseline, over
    its limit, or either file is unreadable.
    """
    try:
        measurement: Measurement = read_measurement(measurement_path)
    except (OSError, ValueError) as err:
        print(
            f"Error: could not read the measurement at '{measurement_path}': {err}",
            file=sys.stderr,
        )
        return 1

    if not baseline:
        print_measurement(measurement)
        return 0

    baseline_file = baseline_label or str(baseline)
    try:
        metrics = [
            build_metric(
                measured["key"],
                measured["name"],
                measured["unit"],
                measured["value"],
                read_baseline(baseline, measured["key"]),
                tolerance_pct,
                read_limit(baseline, measured["key"]),
            )
            for measured in measurement["metrics"]
        ]
    except OSError as err:
        print(
            f"Error: baseline '{baseline_file}' could not be read at '{baseline}': {err}",
            file=sys.stderr,
        )
        return 1
    except ValueError as err:
        print(f"Error: baseline '{baseline_file}' is unusable: {err}", file=sys.stderr)
        return 1

    report = build_report(measurement["label"], baseline_file, metrics)
    if report_out:
        write_report(report, report_out)

    return print_summary(report)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--measurement",
        required=True,
        type=Path,
        help="Json file a measuring tool wrote, holding the measured metrics",
    )
    parser.add_argument(
        "--baseline",
        default=None,
        type=Path,
        help="Json file whose entries are the expected values, one per metric key",
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
    parser.add_argument(
        "--report-name",
        default=None,
        help="Filename to write the comparison under, for pr_comment to merge",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        type=Path,
        help="Directory the comparison is written to. Defaults to TEST_UNDECLARED_OUTPUTS_DIR",
    )
    args = parser.parse_args(argv)

    # A bare `bazel run` has neither, and only prints the summary.
    output_dir = args.output_dir or os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR")
    report_out = (
        Path(output_dir) / args.report_name if output_dir and args.report_name else None
    )

    return run(
        args.measurement,
        args.baseline,
        args.baseline_label,
        args.tolerance_pct,
        report_out,
    )


if __name__ == "__main__":
    sys.exit(main())
