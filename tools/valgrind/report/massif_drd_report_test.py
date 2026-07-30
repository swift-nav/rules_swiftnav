#!/usr/bin/env python3
"""Tests for massif_drd_report.py

Run with Bazel:
    bazel test //tools/valgrind/report/...
"""

import tempfile
import unittest
from pathlib import Path

from tools.valgrind.report.massif_drd_report import (
    METRICS_FILENAME,
    REPORT_JSON_FILENAME,
    STACK_USAGE_FILENAME,
    find_dump_files,
    main,
    measure,
    parse_massif,
    parse_stack_usage,
)
from tools.valgrind.report.metrics import (
    STATUS_OVER_LIMIT,
    STATUS_PASS,
    STATUS_REGRESSION,
    STATUS_STALE_BASELINE,
    read_report,
)

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
                parse_massif(find_dump_files(tmp)),
                {"mem_heap_B": 30 * _MB, "mem_heap_extra_B": 0, "mem_stacks_B": 0},
            )

    def test_ignores_everything_but_per_process_dumps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "valgrind-massif.1", _MASSIF_OUT)
            # The files this tool writes beside the dumps must never be picked
            # up as massif output on a re-run.
            _write(root / METRICS_FILENAME, "memory_heap_mb 10.000\n")
            _write(root / REPORT_JSON_FILENAME, "{}\n")
            _write(root / STACK_USAGE_FILENAME, _STACK_USAGE)

            self.assertEqual(
                [Path(p).name for p in find_dump_files(tmp)], ["valgrind-massif.1"]
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

            measured = measure(tmp, tmp)

            self.assertEqual(measured["memory_stack_mb"], 3.0)
            self.assertEqual(measured["memory_total_mb"], 15.0)

    def test_falls_back_to_massif_without_a_drd_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _write(Path(tmp) / "valgrind-massif.1", _MASSIF_OUT)

            measured = measure(tmp, tmp)

            self.assertEqual(measured["memory_heap_mb"], 10.0)
            self.assertEqual(measured["memory_heap_extra_mb"], 2.0)
            self.assertEqual(measured["memory_stack_mb"], 1.0)
            self.assertEqual(measured["memory_total_mb"], 13.0)

    def test_dumps_can_live_apart_from_the_reports(self) -> None:
        # dumps_to_tmpdir keeps large dumps out of the collected outputs.
        with (
            tempfile.TemporaryDirectory() as out,
            tempfile.TemporaryDirectory() as dumps,
        ):
            _write(Path(dumps) / "valgrind-massif.1", _MASSIF_OUT)
            _write(Path(out) / STACK_USAGE_FILENAME, _STACK_USAGE)

            self.assertEqual(measure(out, dumps)["memory_total_mb"], 15.0)


class MainTest(unittest.TestCase):
    @staticmethod
    def _output_dir(tmp: str) -> str:
        _write(Path(tmp) / "valgrind-massif.1", _MASSIF_OUT)
        _write(Path(tmp) / STACK_USAGE_FILENAME, _STACK_USAGE)
        return tmp

    @staticmethod
    def _run(tmp: str, baseline_json: str) -> int:
        baseline = _write(Path(tmp) / "baseline.json", baseline_json)
        return main(
            [
                "--output-dir",
                tmp,
                "--label",
                "my_target",
                "--baseline",
                str(baseline),
                "--baseline-label",
                "pkg/baseline.json",
                "--tolerance-pct",
                "5",
            ]
        )

    # Measured values are heap 10, extra 2, stacks 3, total 15 MB.
    _ON_BASELINE = """
        {"memory_heap_mb": 10, "memory_heap_extra_mb": 2,
         "memory_stack_mb": 3, "memory_total_mb": 15}
    """

    def test_writes_the_metrics_file_without_a_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._output_dir(tmp)

            self.assertEqual(main(["--output-dir", tmp]), 0)

            self.assertEqual(
                (Path(tmp) / METRICS_FILENAME).read_text(),
                "memory_heap_mb 10.000\nmemory_heap_extra_mb 2.000\nmemory_stack_mb 3.000\nmemory_total_mb 15.000\n",
            )
            self.assertFalse((Path(tmp) / REPORT_JSON_FILENAME).exists())

    def test_fails_when_there_is_no_massif_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(main(["--output-dir", tmp]), 1)

    def test_passes_on_baseline_and_writes_every_metric(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._output_dir(tmp)

            self.assertEqual(self._run(tmp, self._ON_BASELINE), 0)

            report = read_report(Path(tmp) / REPORT_JSON_FILENAME)
            self.assertEqual(report["status"], STATUS_PASS)
            self.assertEqual(report["label"], "my_target")
            self.assertEqual(report["baseline_file"], "pkg/baseline.json")
            self.assertEqual(
                [metric["key"] for metric in report["metrics"]],
                [
                    "memory_heap_mb",
                    "memory_heap_extra_mb",
                    "memory_stack_mb",
                    "memory_total_mb",
                ],
            )
            self.assertEqual({metric["unit"] for metric in report["metrics"]}, {"MB"})

    def test_fails_when_one_metric_regresses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._output_dir(tmp)

            baseline = """
                {"memory_heap_mb": 5, "memory_heap_extra_mb": 2,
                 "memory_stack_mb": 3, "memory_total_mb": 15}
            """
            self.assertEqual(self._run(tmp, baseline), 1)

            report = read_report(Path(tmp) / REPORT_JSON_FILENAME)
            self.assertEqual(report["status"], STATUS_REGRESSION)
            self.assertEqual(report["metrics"][0]["status"], STATUS_REGRESSION)
            self.assertEqual(report["metrics"][1]["status"], STATUS_PASS)

    def test_fails_when_a_metric_is_over_its_absolute_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._output_dir(tmp)

            # On baseline, so only the ceiling can fail it.
            baseline = """
                {"memory_heap_mb": 10, "memory_heap_mb_max": 8, "memory_heap_extra_mb": 2,
                 "memory_stack_mb": 3, "memory_total_mb": 15}
            """
            self.assertEqual(self._run(tmp, baseline), 1)

            report = read_report(Path(tmp) / REPORT_JSON_FILENAME)
            self.assertEqual(report["status"], STATUS_OVER_LIMIT)
            self.assertEqual(report["metrics"][0]["max"], 8)

    def test_stale_baseline_warns_but_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._output_dir(tmp)

            baseline = """
                {"memory_heap_mb": 40, "memory_heap_extra_mb": 2,
                 "memory_stack_mb": 3, "memory_total_mb": 15}
            """
            self.assertEqual(self._run(tmp, baseline), 0)

            self.assertEqual(
                read_report(Path(tmp) / REPORT_JSON_FILENAME)["status"],
                STATUS_STALE_BASELINE,
            )

    def test_fails_on_a_baseline_missing_a_metric(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._output_dir(tmp)
            self.assertEqual(self._run(tmp, '{"memory_heap_mb": 10}'), 1)


if __name__ == "__main__":
    unittest.main()
