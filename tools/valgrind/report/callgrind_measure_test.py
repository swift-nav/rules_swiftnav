#!/usr/bin/env python3
"""Tests for callgrind_measure.py

Run with Bazel:
    bazel test //tools/valgrind/report/...
"""

import tempfile
import unittest
from pathlib import Path

from callgrind_measure import (
    find_output_files,
    run,
    sum_instructions,
)
from metrics import read_measurement

# Multi-event summary line: the first field is Ir, the rest are other events.
_SUMMARY_DUMP = """\
version: 1
creator: callgrind-3.22.0
events: Ir Dr Dw
fn=main
0 12
summary: 1000000 100 50
"""

# Older callgrind writes "totals:" instead of "summary:".
_TOTALS_DUMP = """\
version: 1
events: Ir
fn=main
0 12
totals: 250000
"""


def _write(path: Path, content: str) -> Path:
    path.write_text(content)
    return path


class ReadCallgrindOutputTest(unittest.TestCase):
    def test_sums_both_dump_formats_across_processes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _write(Path(tmp) / "valgrind-callgrind.1", _SUMMARY_DUMP)
            _write(Path(tmp) / "valgrind-callgrind.2", _TOTALS_DUMP)
            self.assertEqual(sum_instructions(find_output_files(Path(tmp))), 1250000)

    def test_counts_multi_part_and_per_thread_dumps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "valgrind-callgrind.1.2", _SUMMARY_DUMP)
            _write(root / "valgrind-callgrind.2-01", _TOTALS_DUMP)
            _write(root / "valgrind-callgrind.3.1-02", _TOTALS_DUMP)

            self.assertEqual(sum_instructions(find_output_files(root)), 1500000)

    def test_ignores_everything_but_per_process_dumps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "valgrind-callgrind.1", _SUMMARY_DUMP)
            # Whatever else shares the directory must never be picked up as
            # callgrind output on a re-run.
            _write(root / "valgrind-callgrind.measurement.json", "{}\n")

            self.assertEqual(
                [p.name for p in find_output_files(root)], ["valgrind-callgrind.1"]
            )

    def test_raises_when_no_dump_carries_a_total(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _write(Path(tmp) / "valgrind-callgrind.1", "version: 1\nfn=main\n0 12\n")
            with self.assertRaises(ValueError):
                sum_instructions(find_output_files(Path(tmp)))


class RunTest(unittest.TestCase):
    def setUp(self) -> None:
        self.output_dir = Path(self.enterContext(tempfile.TemporaryDirectory()))
        _write(self.output_dir / "valgrind-callgrind.1", _SUMMARY_DUMP)
        self.measurement = self.output_dir / "measurement.json"

    def test_writes_one_unitless_cpu_metric(self) -> None:
        self.assertEqual(run(self.output_dir, self.measurement, "my_target"), 0)

        measurement = read_measurement(self.measurement)
        self.assertEqual(measurement["label"], "my_target")
        self.assertEqual(len(measurement["metrics"]), 1)
        entry = measurement["metrics"][0]
        self.assertEqual(entry["key"], "cpu_instructions")
        self.assertEqual(entry["name"], "CPU instructions")
        # Unitless, which is what renders it comma-grouped rather than to three
        # decimal places.
        self.assertEqual(entry["unit"], "")
        self.assertEqual(entry["value"], 1000000)

    def test_fails_when_no_callgrind_output_exists(self) -> None:
        with tempfile.TemporaryDirectory() as empty:
            self.assertEqual(run(Path(empty), self.measurement), 1)
            self.assertFalse(self.measurement.exists())


if __name__ == "__main__":
    unittest.main()
