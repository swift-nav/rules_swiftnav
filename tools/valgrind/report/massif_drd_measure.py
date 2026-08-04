#!/usr/bin/env python3
"""Measure a massif and DRD run's memory figures into a measurement json.

Reads the ``valgrind-massif.<pid>`` dumps a massif run leaves behind, picks the
single largest snapshot across all of them, and reports peak heap, heap extra,
stacks and their sum. Under --trace-children=yes there is a dump per process,
and the peak is the worst moment of the worst one. When the runner also made a
DRD pass its ``valgrind-drd.stack_usage.txt`` supplies the stack figure
instead of massif's own.

Measuring only. Gating those figures against a baseline is compare's job, run
as a separate target so that editing a baseline does not re-run massif.

Run with Bazel:
    bazel run //tools/valgrind/report:massif_drd_measure -- --output-dir <dir>
"""

import argparse
import re
import sys
from collections.abc import Iterable
from pathlib import Path

from tools.valgrind.report.metrics import (
    Measured,
    Measurement,
    write_measurement,
)

STACK_USAGE_FILENAME = "valgrind-drd.stack_usage.txt"

# Only the per-process dumps, so the files this tool writes alongside them are
# never mistaken for massif output on a re-run.
_DUMP_FILE_RE = re.compile(r"^valgrind-massif\.\d+$")

UNIT = "MB"
_BYTES_PER_MB = 1024 * 1024

DEFAULT_LABEL = "massif"

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


def measure(output_dir: Path) -> dict[str, float]:
    """Measure every memory metric from a run's massif dumps and DRD report."""
    peak = parse_massif(find_dump_files(output_dir))

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
    measurement_out: Path,
    label: str = DEFAULT_LABEL,
) -> int:
    """Measure a massif run and write the measurement json.

    Returns the exit code: non-zero only when the massif output could not be
    read at all.
    """
    try:
        measured = measure(output_dir)
    except (OSError, ValueError) as err:
        print(
            f"Error: could not read massif output from {output_dir}: {err}",
            file=sys.stderr,
        )
        return 1

    measurement = Measurement(
        label=label,
        metrics=[
            Measured(key=key, name=METRIC_NAMES[key], unit=UNIT, value=value)
            for key, value in measured.items()
        ],
    )
    write_measurement(measurement, measurement_out)

    for entry in measurement["metrics"]:
        print(f"{entry['name']}: {entry['value']:.3f} {UNIT}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help=f"Directory holding the valgrind-massif.<pid> dumps, and {STACK_USAGE_FILENAME} if a DRD pass was made",
    )
    parser.add_argument(
        "--measurement-out",
        required=True,
        type=Path,
        help="Where to write the measurement json for compare to gate on",
    )
    parser.add_argument(
        "--label",
        default=DEFAULT_LABEL,
        help="Name of the profiled target, shown in the reports",
    )
    args = parser.parse_args(argv)

    return run(
        args.output_dir,
        args.measurement_out,
        args.label,
    )


if __name__ == "__main__":
    sys.exit(main())
