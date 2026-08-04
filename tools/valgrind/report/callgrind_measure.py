#!/usr/bin/env python3
"""Measure a callgrind run's instruction count into a measurement json.

Reads the raw ``valgrind-callgrind.<pid>`` files a callgrind run leaves in the
output directory and sums the instruction counts (Ir) across every process.

Measuring only. Gating that total against a baseline is compare's job, run as a
separate target so that editing a baseline does not re-run callgrind.

Run with Bazel:
    bazel run //tools/valgrind/report:callgrind_measure -- --output-dir <dir>
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

METRIC_KEY = "cpu_instructions"
METRIC_NAME = "CPU instructions"

# An instruction count is a bare number, which is what makes format_number
# render it comma-grouped rather than to three decimal places.
UNIT = ""

DEFAULT_LABEL = "callgrind"

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
    measurement_out: Path,
    label: str = DEFAULT_LABEL,
) -> int:
    """Measure a callgrind run and write the measurement json.

    Returns the exit code: non-zero only when the callgrind output could not be
    read at all.
    """
    try:
        measured = sum_instructions(find_output_files(output_dir))
    except (OSError, ValueError) as err:
        print(
            f"Error: could not read callgrind output from {output_dir}: {err}",
            file=sys.stderr,
        )
        return 1

    measurement = Measurement(
        label=label,
        metrics=[Measured(key=METRIC_KEY, name=METRIC_NAME, unit=UNIT, value=measured)],
    )
    write_measurement(measurement, measurement_out)

    print(f"{METRIC_NAME}: {measured:,}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory holding the valgrind-callgrind.<pid> dumps",
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
