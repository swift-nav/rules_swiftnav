#!/usr/bin/env python3
"""Shared report types for the valgrind profiling tools.

A report is what one profiled Bazel target produces: a label, the baseline file
it was compared against, and one metric per measured quantity. Every valgrind
metric is a single scalar compared against a single scalar baseline — callgrind
yields an instruction count, massif peak heap sizes, DRD a stack high-water —
so one Metric type covers them all.

The measuring tools (callgrind_report and friends) write these as json;
pr_comment reads them back and renders the PR comment. print_summary is the
console half of the same job: it is what makes a failing `bazel test` explain
itself, and it lives here so every profiler reports a regression identically.
"""

import json
import os
import sys
from typing import TypedDict

STATUS_PASS = "pass"
STATUS_REGRESSION = "regression"
STATUS_STALE_BASELINE = "stale-baseline"
STATUS_OVER_LIMIT = "over-limit"

# Worst first: a target's verdict is the worst status among its metrics. An
# absolute limit outranks a regression — drifting past the baseline is a review
# question, exceeding the ceiling the product has to fit in is not.
_STATUS_PRECEDENCE = [
    STATUS_OVER_LIMIT,
    STATUS_REGRESSION,
    STATUS_STALE_BASELINE,
    STATUS_PASS,
]

LIMIT_SUFFIX = "_max"


class Metric(TypedDict):
    """One measured quantity compared against its baseline."""

    key: str
    name: str
    unit: str
    value: float
    baseline: float
    delta: float
    delta_pct: float
    tolerance_pct: float
    # Absolute ceiling, or None when the metric is only gated relatively.
    max: float | None
    status: str


class Report(TypedDict):
    """Every metric of one profiled target."""

    label: str
    baseline_file: str
    status: str
    metrics: list[Metric]


def build_metric(
    key: str,
    name: str,
    unit: str,
    value: float,
    baseline: float,
    tolerance_pct: float,
    max_value: float | None = None,
) -> Metric:
    """Compare a measured value against a baseline within a percent tolerance.

    max_value is an optional absolute ceiling checked before the baseline, for
    quantities that have a budget of their own rather than only a previous
    value to stay near.
    """
    delta = value - baseline
    delta_pct = (delta / baseline) * 100 if baseline else 0.0

    if max_value is not None and value > max_value:
        status = STATUS_OVER_LIMIT
    elif delta_pct > tolerance_pct:
        status = STATUS_REGRESSION
    elif delta_pct < -tolerance_pct:
        status = STATUS_STALE_BASELINE
    else:
        status = STATUS_PASS

    return Metric(
        key=key,
        name=name,
        unit=unit,
        value=value,
        baseline=baseline,
        delta=delta,
        delta_pct=delta_pct,
        tolerance_pct=tolerance_pct,
        max=max_value,
        status=status,
    )


def worst_status(statuses: list[str]) -> str:
    """Return the most severe of the given statuses."""
    for status in _STATUS_PRECEDENCE:
        if status in statuses:
            return status
    return STATUS_PASS


def build_report(label: str, baseline_file: str, metrics: list[Metric]) -> Report:
    """Assemble a target's metrics into a report, with the verdict derived."""
    return Report(
        label=label,
        baseline_file=baseline_file,
        status=worst_status([metric["status"] for metric in metrics]),
        metrics=metrics,
    )


def _load_baselines(path: str | os.PathLike) -> dict:
    """Read a baseline file as a flat metric key to number mapping."""
    with open(path) as f:
        baselines = json.load(f)

    if not isinstance(baselines, dict):
        raise ValueError("not a json object")
    return baselines


def _positive_number(key: str, value: object) -> float:
    """Return value as a number, rejecting anything that cannot be compared."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{key!r} must be a positive number, got {value!r}")
    return value


def read_baseline(path: str | os.PathLike, key: str) -> float:
    """Read one metric's expected value from a json baseline file.

    The file maps metric keys to numbers, so a target that measures several
    quantities keeps them all in one place::

        {"cpu_instructions": 28032185999, "memory_heap_mb": 15.405}

    Raises:
        ValueError: if the file is not valid json, has no entry for the key, or
            the entry is not a positive number. Zero is rejected too: a
            placeholder nobody has filled in is not something to compare
            against.
    """
    baselines = _load_baselines(path)
    if key not in baselines:
        raise ValueError(f"no {key!r} entry")
    return _positive_number(key, baselines[key])


def read_limit(path: str | os.PathLike, key: str) -> float | None:
    """Read a metric's optional absolute ceiling, or None if it has none.

    The ceiling lives beside the baseline under the same key plus
    ``LIMIT_SUFFIX``, so the file stays a flat mapping::

        {"memory_heap_mb": 15.405, "memory_heap_mb_max": 50}

    Unlike the baseline this is optional — most metrics are only gated against
    their previous value.

    Raises:
        ValueError: if the file is not valid json, or the entry is present but
            not a positive number.
    """
    baselines = _load_baselines(path)
    limit_key = key + LIMIT_SUFFIX
    if limit_key not in baselines:
        return None
    return _positive_number(limit_key, baselines[limit_key])


def format_number(value: float, unit: str, signed: bool = False) -> str:
    """Render a metric number: counts as integers, everything else to 3 decimals."""
    sign = "+" if signed else ""
    if not unit:
        return format(value, f"{sign},.0f")
    return f"{format(value, f'{sign},.3f')} {unit}"


def format_value(metric: Metric) -> str:
    """Render a metric's measured value."""
    return format_number(metric["value"], metric["unit"])


def format_baseline(metric: Metric) -> str:
    """Render a metric's baseline."""
    return format_number(metric["baseline"], metric["unit"])


def format_delta(metric: Metric) -> str:
    """Render a metric's delta, always signed."""
    return format_number(metric["delta"], metric["unit"], signed=True)


def format_limit(metric: Metric) -> str:
    """Render a metric's absolute ceiling, or an em dash when it has none."""
    limit = metric["max"]
    return format_number(limit, metric["unit"]) if limit is not None else "—"


def _baseline_literal(metric: Metric) -> str:
    """Render a measured value as it should be typed into the baseline json."""
    return f"{metric['value']:.3f}" if metric["unit"] else f"{metric['value']:.0f}"


def _refresh_hint(lead: str, metrics: list[Metric], baseline_file: str) -> str:
    """Spell out the edit that would make the given metrics pass again."""
    return "\n".join(
        [lead]
        + [
            f'  set "{metric["key"]}": {_baseline_literal(metric)} in {baseline_file}'
            for metric in metrics
        ]
    )


def print_summary(report: Report) -> int:
    """Print a report's measurements and verdict, returning the exit code.

    Shared by every measuring tool, so a regression reads the same whichever
    profiler found it and a new profiler needs no reporting logic of its own.
    Failures go to stderr; a stale baseline is a warning on stdout because it
    must not fail the test.
    """
    width = max((len(metric["name"]) for metric in report["metrics"]), default=0)
    for metric in report["metrics"]:
        line = (
            f"{metric['name'] + ':':<{width + 1}} {format_value(metric)}"
            f"  baseline {format_baseline(metric)}"
            f"  {format_delta(metric)} ({metric['delta_pct']:+.2f}%)"
            f", tolerance ±{metric['tolerance_pct']:.2f}%"
        )
        if metric["max"] is not None:
            line += f", limit {format_limit(metric)}"
        print(line)
    print(f"Baseline file: {report['baseline_file']}")

    if report["status"] == STATUS_PASS:
        return 0

    # Only the metrics that earned the target its verdict are worth naming.
    at_fault = [
        metric for metric in report["metrics"] if metric["status"] == report["status"]
    ]

    if report["status"] == STATUS_OVER_LIMIT:
        print("\nError: over the absolute limit.", file=sys.stderr)
        for metric in at_fault:
            print(
                f"  {metric['name']} is {format_value(metric)}, the limit is {format_limit(metric)}",
                file=sys.stderr,
            )
        return 1

    if report["status"] == STATUS_REGRESSION:
        print("\nError: regression beyond tolerance.", file=sys.stderr)
        for metric in at_fault:
            print(
                f"  {metric['name']} grew {metric['delta_pct']:+.2f}%, more than the allowed "
                f"{metric['tolerance_pct']:.2f}%",
                file=sys.stderr,
            )
        print(
            _refresh_hint(
                "If the increase is expected, refresh the baseline with:",
                at_fault,
                report["baseline_file"],
            ),
            file=sys.stderr,
        )
        return 1

    # A large improvement means the baseline no longer guards this target, so
    # say so loudly without failing the test.
    print(
        "\nWarning: measured well below the baseline, which no longer guards this target."
    )
    for metric in at_fault:
        print(f"  {metric['name']} is {-metric['delta_pct']:.2f}% below the baseline")
    print(
        _refresh_hint("Consider refreshing it with:", at_fault, report["baseline_file"])
    )
    return 0


def write_report(report: Report, path: str | os.PathLike) -> None:
    """Write a report as json."""
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
        f.write("\n")


def read_report(path: str | os.PathLike) -> Report:
    """Read a report written by write_report."""
    with open(path) as f:
        return json.load(f)
