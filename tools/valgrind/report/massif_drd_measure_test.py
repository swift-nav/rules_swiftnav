#!/usr/bin/env python3
"""Tests for massif_drd_measure.py

Run with Bazel:
    bazel test //tools/valgrind/report/...
"""

import tempfile
import unittest
from pathlib import Path

from tools.valgrind.report.massif_drd_measure import (
    STACK_USAGE_FILENAME,
    find_dump_files,
    measure,
    parse_massif,
    parse_stack_usage,
    run,
)
from tools.valgrind.report.metrics import read_measurement

_MB = 1024 * 1024


def _snapshot(index: int, heap: int, extra: int, stacks: int) -> str:
    return (
        f"snapshot={index}\n"
        "#-----------\n"
        f"time={index}\n"
        f"mem_heap_B={heap}\n"
        f"mem_heap_extra_B={extra}\n"
        f"mem_stacks_B={stacks}\n"
        "heap_tree=empty\n"
    )


# The peak is snapshot 1, and it is not the last one — the tool has to compare
# rather than take whatever it saw last.
_MASSIF_OUT = (
    "desc: (none)\ncmd: ./binary\ntime_unit: i\n"
    + _snapshot(0, 1 * _MB, 0, 0)
    + _snapshot(1, 10 * _MB, 2 * _MB, 1 * _MB)
    + _snapshot(2, 4 * _MB, 0, 0)
)

_STACK_USAGE = (
    "==42== thread 1 finished and used 2097152 bytes out of 8388608 on its stack. Margin: 6291456 bytes.\n"
    "==42== thread 2 finished and used 1048576 bytes out of 8388608 on its stack. Margin: 7340032 bytes.\n"
)


def _write(path: Path, content: str) -> Path:
    path.write_text(content)
    return path


class ParseMassifTest(unittest.TestCase):
    def test_takes_the_snapshot_with_the_largest_total(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(Path(tmp) / "valgrind-massif.1", _MASSIF_OUT)

            self.assertEqual(
                parse_massif([path]),
                {
                    "mem_heap_B": 10 * _MB,
                    "mem_heap_extra_B": 2 * _MB,
                    "mem_stacks_B": 1 * _MB,
                },
            )

    def test_peak_is_the_worst_moment_of_the_worst_process(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "valgrind-massif.1", _MASSIF_OUT)
            _write(root / "valgrind-massif.2", _snapshot(0, 30 * _MB, 0, 0))

            self.assertEqual(
                parse_massif(find_dump_files(root)),
                {"mem_heap_B": 30 * _MB, "mem_heap_extra_B": 0, "mem_stacks_B": 0},
            )

    def test_ignores_everything_but_per_process_dumps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "valgrind-massif.1", _MASSIF_OUT)
            # Whatever else shares the directory must never be picked up as
            # massif output on a re-run.
            _write(root / "valgrind-massif.measurement.json", "{}\n")
            _write(root / STACK_USAGE_FILENAME, _STACK_USAGE)

            self.assertEqual(
                [p.name for p in find_dump_files(root)], ["valgrind-massif.1"]
            )

    def test_raises_when_every_snapshot_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(Path(tmp) / "valgrind-massif.1", _snapshot(0, 0, 0, 0))
            with self.assertRaises(ValueError):
                parse_massif([path])

    def test_raises_when_there_are_no_dumps(self) -> None:
        with self.assertRaises(ValueError):
            parse_massif([])


class ParseStackUsageTest(unittest.TestCase):
    def test_sums_every_thread(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(Path(tmp) / STACK_USAGE_FILENAME, _STACK_USAGE)
            self.assertEqual(parse_stack_usage(path), 3 * _MB)

    def test_raises_on_an_empty_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(Path(tmp) / STACK_USAGE_FILENAME, "")
            with self.assertRaises(ValueError):
                parse_stack_usage(path)


class MeasureTest(unittest.TestCase):
    def test_drd_supersedes_the_massif_stack_figure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _write(Path(tmp) / "valgrind-massif.1", _MASSIF_OUT)
            _write(Path(tmp) / STACK_USAGE_FILENAME, _STACK_USAGE)

            measured = measure(Path(tmp))

            self.assertAlmostEqual(measured["memory_stack_mb"], 3.0)
            self.assertAlmostEqual(measured["memory_total_mb"], 15.0)

    def test_falls_back_to_massif_without_a_drd_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _write(Path(tmp) / "valgrind-massif.1", _MASSIF_OUT)

            measured = measure(Path(tmp))

            self.assertAlmostEqual(measured["memory_heap_mb"], 10.0)
            self.assertAlmostEqual(measured["memory_heap_extra_mb"], 2.0)
            self.assertAlmostEqual(measured["memory_stack_mb"], 1.0)
            self.assertAlmostEqual(measured["memory_total_mb"], 13.0)


class RunTest(unittest.TestCase):
    def setUp(self) -> None:
        self.output_dir = Path(self.enterContext(tempfile.TemporaryDirectory()))
        _write(self.output_dir / "valgrind-massif.1", _MASSIF_OUT)
        _write(self.output_dir / STACK_USAGE_FILENAME, _STACK_USAGE)
        self.measurement = self.output_dir / "measurement.json"

    def test_writes_every_metric_in_report_order(self) -> None:
        self.assertEqual(run(self.output_dir, self.measurement, "my_target"), 0)

        measurement = read_measurement(self.measurement)
        self.assertEqual(measurement["label"], "my_target")
        self.assertEqual(
            [entry["key"] for entry in measurement["metrics"]],
            [
                "memory_heap_mb",
                "memory_heap_extra_mb",
                "memory_stack_mb",
                "memory_total_mb",
            ],
        )
        self.assertEqual({entry["unit"] for entry in measurement["metrics"]}, {"MB"})
        self.assertAlmostEqual(measurement["metrics"][3]["value"], 15.0)

    def test_names_every_metric_for_the_reports(self) -> None:
        run(self.output_dir, self.measurement)

        names = [
            entry["name"] for entry in read_measurement(self.measurement)["metrics"]
        ]
        self.assertEqual(names[0], "Peak heap (massif)")
        self.assertTrue(all(names))

    def test_fails_when_there_is_no_massif_output(self) -> None:
        with tempfile.TemporaryDirectory() as empty:
            self.assertEqual(run(Path(empty), self.measurement), 1)
            self.assertFalse(self.measurement.exists())


if __name__ == "__main__":
    unittest.main()
