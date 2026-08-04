#!/usr/bin/env python3
"""Summarise massif and DRD output and optionally gate on memory baselines.

Reads the ``valgrind-massif.<pid>`` dumps a massif run leaves behind, picks the
single largest snapshot across all of them, and reports peak heap, heap extra,
stacks and their sum. Under --trace-children=yes there is a dump per process,
and the peak is the worst moment of the worst one. When the runner also made a
DRD pass its ``valgrind-drd.stack_usage.txt`` supplies the stack figure
instead of massif's own.

When a baseline is supplied every metric is compared against it and the tool
exits non-zero on a regression larger than the tolerance, or on exceeding an
absolute limit, which turns a plain ``bazel test`` into a memory regression
gate. The comparison is also written to ``valgrind-massif-drd.report.json`` in the
shared report format, so pr_comment can merge it with the reports of other
targets.

The baseline is a json file mapping metric keys to their expected values, with
an optional ``_max`` ceiling beside any of them::

    {"memory_heap_mb": 15.405, "memory_heap_mb_max": 50}

Run with Bazel:
    bazel run //tools/valgrind/report:massif_drd_report -- --output-dir <dir>
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

STACK_USAGE_FILENAME = "valgrind-drd.stack_usage.txt"
METRICS_FILENAME = "valgrind-massif-drd.metrics"
REPORT_JSON_FILENAME = "valgrind-massif-drd.report.json"

# Only the per-process dumps, so the files this tool writes alongside them are
# never mistaken for massif output on a re-run.
_DUMP_FILE_RE = re.compile(r"^valgrind-massif\.\d+$")

UNIT = "MB"
_BYTES_PER_MB = 1024 * 1024

DEFAULT_LABEL = "massif"
DEFAULT_TOLERANCE_PCT = 5.0

METRIC_NAMES = {
    "memory_heap_mb": "Peak heap (massif)",
    "memory_heap_extra_mb": "Peak heap extra (massif)",
    "memory_stack_mb": "Peak stacks (DRD)",
    "memory_total_mb": "Peak memory (massif + DRD)",
}

_ZERO_SNAPSHOT = {"mem_heap_B": 0, "mem_heap_extra_B": 0, "mem_stacks_B": 0}

# massif writes one "snapshot=N" block per sample, each carrying these totals.
_FIELD_RE = re.compile(r"^(mem_heap_B|mem_heap_extra_B|mem_stacks_B)=(\d+)")

# DRD --show-stack-usage prints one line per thread as it exits; the first
# number is that thread's own high-water mark.
_STACK_USAGE_RE = re.compile(
    r"thread \d+ finished and used (\d+) bytes out of \d+ on its stack"
)


def find_dump_files(dump_dir: Path) -> list[Path]:
    """Return the per-process massif dumps in dump_dir, sorted by name."""
    return sorted(p for p in dump_dir.iterdir() if _DUMP_FILE_RE.match(p.name))


def _snapshots(path: Path) -> list[dict[str, int]]:
    """Return every snapshot's byte totals from one massif dump."""
    snapshots = []
    current = dict(_ZERO_SNAPSHOT)

    with path.open() as f:
        for line in f:
            if line.startswith("snapshot="):
                snapshots.append(current)
                current = dict(_ZERO_SNAPSHOT)
                continue
            match = _FIELD_RE.match(line)
            if match:
                current[match.group(1)] = int(match.group(2))
    snapshots.append(current)
    return snapshots


def parse_massif(paths: Iterable[Path]) -> dict[str, int]:
    """Return the peak snapshot's byte totals across every massif dump.

    "Peak" is the snapshot with the largest heap + heap extra + stacks. massif
    marks a peak snapshot of its own, but only by heap. With one dump per
    process this is the worst moment of the worst process, which is the closest
    single number to what the tree cost — the concurrent total is not
    recoverable from per-process dumps.

    Raises:
        ValueError: if no snapshot carried a non-zero total, which means the
            run produced nothing worth comparing.
    """
    snapshots = [snapshot for path in paths for snapshot in _snapshots(path)]

    peak = max(
        snapshots,
        key=lambda snapshot: sum(snapshot.values()),
        default=dict(_ZERO_SNAPSHOT),
    )
    if not sum(peak.values()):
        raise ValueError("no massif snapshot with a non-zero total")
    return peak


def parse_stack_usage(path: Path) -> int:
    """Return the summed per-thread stack high-water, in bytes.

    Stack pages stay committed once touched, so the sum over threads is what
    the process really costs in stacks.

    Raises:
        ValueError: if the file holds no DRD stack usage lines.
    """
    total = 0
    found = False
    with path.open() as f:
        for line in f:
            match = _STACK_USAGE_RE.search(line)
            if match:
                total += int(match.group(1))
                found = True
    if not found:
        raise ValueError("no DRD stack usage lines")
    return total


def measure(output_dir: Path, dump_dir: Path) -> dict[str, float]:
    """Measure every memory metric from a run's massif dumps and DRD report."""
    peak = parse_massif(find_dump_files(dump_dir))

    heap_mb = peak["mem_heap_B"] / _BYTES_PER_MB
    heap_extra_mb = peak["mem_heap_extra_B"] / _BYTES_PER_MB

    # massif only accounts for stacks under --stacks=yes, which slows it down
    # considerably, so the runner can measure them with a DRD pass instead.
    # Fall back to massif's own figure when that pass was not made.
    stack_path = output_dir / STACK_USAGE_FILENAME
    stack_b = (
        parse_stack_usage(stack_path) if stack_path.exists() else peak["mem_stacks_B"]
    )
    stack_mb = stack_b / _BYTES_PER_MB

    return {
        "memory_heap_mb": heap_mb,
        "memory_heap_extra_mb": heap_extra_mb,
        "memory_stack_mb": stack_mb,
        "memory_total_mb": heap_mb + heap_extra_mb + stack_mb,
    }


def run(
    output_dir: Path,
    dump_dir: Path | None = None,
    label: str = DEFAULT_LABEL,
    baseline: Path | None = None,
    baseline_label: str | None = None,
    tolerance_pct: float = DEFAULT_TOLERANCE_PCT,
) -> int:
    """Summarise a massif run, gating on the baselines when they are given.

    dump_dir defaults to output_dir, for a run that kept its dumps beside the
    reports. Returns the exit code: non-zero once a metric is more than
    tolerance_pct above its baseline, over its limit, or unreadable.
    """
    dumps = dump_dir or output_dir
    try:
        measured = measure(output_dir, dumps)
    except (OSError, ValueError) as err:
        print(
            f"Error: could not read massif output from {dumps}: {err}",
            file=sys.stderr,
        )
        return 1

    (output_dir / METRICS_FILENAME).write_text(
        "".join(f"{key} {value:.3f}\n" for key, value in measured.items())
    )

    if not baseline:
        for key, value in measured.items():
            print(f"{METRIC_NAMES[key]}: {value:.3f} {UNIT}")
        return 0

    baseline_file = baseline_label or str(baseline)
    try:
        metrics = [
            build_metric(
                key,
                METRIC_NAMES[key],
                UNIT,
                value,
                read_baseline(baseline, key),
                tolerance_pct,
                read_limit(baseline, key),
            )
            for key, value in measured.items()
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

    report = build_report(label, baseline_file, metrics)
    write_report(report, output_dir / REPORT_JSON_FILENAME)

    return print_summary(report)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help=f"Directory the reports are written to, holding {STACK_USAGE_FILENAME} if a DRD pass was made",
    )
    parser.add_argument(
        "--dump-dir",
        default=None,
        type=Path,
        help="Directory holding the valgrind-massif.<pid> dumps. Defaults to --output-dir",
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
        help="Json file whose memory_* entries are the expected values",
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
        args.dump_dir,
        args.label,
        args.baseline,
        args.baseline_label,
        args.tolerance_pct,
    )


if __name__ == "__main__":
    sys.exit(main())
