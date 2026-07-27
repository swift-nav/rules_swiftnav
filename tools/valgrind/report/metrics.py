#!/usr/bin/env python3
"""Shared report types for the valgrind profiling tools.

A report is what one profiled Bazel target produces: a label, the baseline file
it was compared against, and one metric per measured quantity. Every valgrind
metric is a single scalar compared against a single scalar baseline — callgrind
yields an instruction count, massif peak heap sizes, DRD a stack high-water —
so one Metric type covers them all.

The measuring tools (callgrind_report and friends) write these as json;
pr_comment reads them back and renders the PR comment.
"""

import json
import os
from typing import TypedDict

STATUS_PASS = "pass"
STATUS_REGRESSION = "regression"
STATUS_STALE_BASELINE = "stale-baseline"

# Worst first: a target's verdict is the worst status among its metrics.
_STATUS_PRECEDENCE = [STATUS_REGRESSION, STATUS_STALE_BASELINE, STATUS_PASS]


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
) -> Metric:
    """Compare a measured value against a baseline within a percent tolerance."""
    delta = value - baseline
    delta_pct = (delta / baseline) * 100 if baseline else 0.0

    if delta_pct > tolerance_pct:
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
    with open(path) as f:
        baselines = json.load(f)

    if not isinstance(baselines, dict) or key not in baselines:
        raise ValueError(f"no {key!r} entry")

    value = baselines[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{key!r} must be a positive number, got {value!r}")
    return value


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


def write_report(report: Report, path: str | os.PathLike) -> None:
    """Write a report as json."""
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
        f.write("\n")


def read_report(path: str | os.PathLike) -> Report:
    """Read a report written by write_report."""
    with open(path) as f:
        return json.load(f)
