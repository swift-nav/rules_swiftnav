#!/usr/bin/env python3
"""Tests for runner.py

Run with Bazel:
    bazel test //tools/valgrind/...
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.valgrind import runner

_STACK_LINES = (
    "==42== thread 1 finished and used 2097152 bytes out of 8388608 on its stack. Margin: 6291456 bytes.\n"
    "==42== Thread 2:\n"
    "==42== Conflicting load by thread 2 at 0x1234 size 4\n"
    "==42== thread 2 finished and used 1048576 bytes out of 8388608 on its stack. Margin: 7340032 bytes.\n"
)


class _Dirs:
    """Redirect the module's three run-time directories into a temporary tree.

    The working directory moves to the stand-in runfiles too, because that is
    where a py_test starts and what the relative paths $(location) expands to
    are resolved against.
    """

    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name).resolve()
        self.output = root / "outputs"
        self.scratch = root / "scratch"
        self.runfiles = root / "runfiles"
        for path in (self.output, self.scratch, self.runfiles):
            path.mkdir()
        self._patches = [
            mock.patch.object(runner, "OUTPUT_DIR", self.output),
            mock.patch.object(runner, "SCRATCH_DIR", self.scratch),
            mock.patch.object(runner, "RUNFILES", self.runfiles),
        ]

    def __enter__(self) -> "_Dirs":
        for patch in self._patches:
            patch.start()
        self._cwd = Path.cwd()
        os.chdir(self.runfiles)
        return self

    def __exit__(self, *exc: object) -> None:
        os.chdir(self._cwd)
        for patch in reversed(self._patches):
            patch.stop()
        self._tmp.cleanup()

    def file(self, name: str, content: str = "") -> Path:
        path = self.runfiles / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path


class ExpandTest(unittest.TestCase):
    def test_substitutes_every_token(self) -> None:
        with _Dirs() as dirs:
            binary = dirs.file("bin/prog")

            args = runner.expand(
                [
                    "--supp={RUNFILES}/googletest.supp",
                    str(binary),
                    "--out",
                    "{OUTPUT_DIR}/report",
                    "--work",
                    "{TMPDIR}/scratch",
                ]
            )

            self.assertEqual(args[0], f"--supp={dirs.runfiles}/googletest.supp")
            self.assertEqual(args[3], f"{dirs.output}/report")
            self.assertEqual(args[5], f"{dirs.scratch}/scratch")

    def test_absolutises_the_binary_and_leaves_the_rest_alone(self) -> None:
        # The binary has to be absolute because it may run from a working
        # directory of its own; its arguments are the caller's business.
        with _Dirs() as dirs:
            binary = dirs.file("bin/prog")

            args = runner.expand(["--tool=massif", "bin/prog", "relative/arg"])

            self.assertEqual(args, ["--tool=massif", str(binary), "relative/arg"])

    def test_takes_the_first_non_flag_as_the_binary(self) -> None:
        with _Dirs() as dirs:
            first = dirs.file("first")
            dirs.file("second")

            args = runner.expand(["-q", "first", "second"])

            self.assertEqual(args[1], str(first))
            self.assertEqual(args[2], "second")

    def test_raises_when_every_argument_is_a_flag(self) -> None:
        with _Dirs(), self.assertRaises(ValueError):
            runner.expand(["--only-a-flag"])


class WorkdirTest(unittest.TestCase):
    def test_stays_in_the_runfiles_without_workdir_data(self) -> None:
        with _Dirs():
            self.assertIsNone(runner.workdir([]))

    def test_symlinks_files_in_by_basename(self) -> None:
        # A config naming its inputs by bare filename has to resolve them from
        # the working directory, whatever their path in the runfiles was.
        with _Dirs() as dirs:
            dirs.file("deep/nested/config.yaml", "key: value\n")

            path = runner.workdir(["deep/nested/config.yaml"])

            self.assertEqual(sorted(p.name for p in path.iterdir()), ["config.yaml"])
            self.assertEqual((path / "config.yaml").read_text(), "key: value\n")

    def test_raises_rather_than_shadowing_a_shared_basename(self) -> None:
        with _Dirs() as dirs:
            dirs.file("a/config.yaml", "a\n")
            dirs.file("b/config.yaml", "b\n")

            with self.assertRaises(FileExistsError):
                runner.workdir(["a/config.yaml", "b/config.yaml"])


class DrdStackUsageTest(unittest.TestCase):
    def _run(self, *logs: str, code: int = 0) -> tuple[int, str | None]:
        """Run a DRD pass writing one log per child, returning its exit code and report."""
        with _Dirs() as dirs:

            def fake_valgrind(
                label: str, flags: list[str], args: list[str], cwd: Path | None
            ) -> int:
                for pid, text in enumerate(logs):
                    (dirs.scratch / f"drd.log.{pid}").write_text(text)
                return code

            with mock.patch.object(runner, "valgrind", fake_valgrind):
                returned = runner.drd_stack_usage(["prog"], None)

            report = dirs.output / "valgrind-drd.stack_usage.txt"
            return returned, report.read_text() if report.exists() else None

    def test_keeps_only_the_stack_lines(self) -> None:
        returned, report = self._run(_STACK_LINES)

        self.assertEqual(returned, 0)
        self.assertEqual(len(report.splitlines()), 2)
        self.assertNotIn("Conflicting load", report)

    def test_collects_the_stack_lines_of_every_child(self) -> None:
        # Under --trace-children each process logs to its own %p file, and all
        # of their threads count towards the total.
        self.assertEqual(len(self._run(_STACK_LINES, _STACK_LINES)[1].splitlines()), 4)

    def test_writes_no_report_when_the_pass_found_nothing(self) -> None:
        # An empty report would stop massif_report falling back on massif's own
        # stack figure, and fail the target with a misleading error.
        self.assertIsNone(self._run("==42== no stack usage here\n")[1])

    def test_writes_no_report_when_the_pass_never_logged(self) -> None:
        self.assertIsNone(self._run()[1])

    def test_returns_the_drd_exit_code(self) -> None:
        # A DRD pass that failed must fail the target rather than leave the
        # stack figure quietly unmeasured.
        self.assertEqual(self._run(code=3)[0], 3)


class ToolFlagsTest(unittest.TestCase):
    def _flags(self, tool: str, **opts: bool) -> tuple[list[str], list[str]]:
        """Run one tool with valgrind stubbed out, returning its flags and report arguments."""
        namespace = runner.argparse.Namespace(
            **{"stack_usage": False, "dumps_to_tmpdir": False, **opts}
        )
        captured: list[list[str]] = []

        with _Dirs():

            def fake_valgrind(
                label: str, flags: list[str], args: list[str], cwd: Path | None
            ) -> int:
                captured.append(flags)
                return 0

            with mock.patch.object(runner, "valgrind", fake_valgrind):
                _, extra = runner.TOOLS[tool](["prog"], None, namespace)
        return captured[0], extra

    def test_callgrind_writes_a_dump_per_process(self) -> None:
        flags, extra = self._flags("callgrind")

        self.assertIn("--tool=callgrind", flags)
        self.assertTrue(
            any(
                f.startswith("--callgrind-out-file=")
                and f.endswith("valgrind-callgrind.%p")
                for f in flags
            )
        )
        self.assertEqual(extra, [])

    def test_memcheck_writes_xml_per_process(self) -> None:
        flags, extra = self._flags("memcheck")

        self.assertIn("--tool=memcheck", flags)
        self.assertIn("--xml=yes", flags)
        self.assertTrue(any(f.endswith("valgrind-memcheck.%p.xml") for f in flags))
        self.assertEqual(extra, [])

    def test_massif_points_the_report_at_the_dumps(self) -> None:
        flags, extra = self._flags("massif")

        self.assertIn("--tool=massif", flags)
        self.assertEqual(extra[0], "--dump-dir")
        self.assertTrue(extra[1].endswith("outputs"))

    def test_massif_can_keep_its_dumps_out_of_the_outputs(self) -> None:
        _, extra = self._flags("massif", dumps_to_tmpdir=True)
        self.assertTrue(extra[1].endswith("scratch"))


class ParseTest(unittest.TestCase):
    def test_report_half_is_empty_for_memcheck(self) -> None:
        opts = runner.parse(["--tool", "memcheck"])

        self.assertEqual(opts.tool, "memcheck")
        self.assertEqual(opts.report, [])

    def test_keeps_the_report_tool_arguments_verbatim(self) -> None:
        # The report tool's own flags must survive untouched, including ones the
        # runner happens to share a name with.
        opts = runner.parse(
            [
                "--tool",
                "massif",
                "--stack-usage",
                "--dumps-to-tmpdir",
                "--workdir-data",
                "config.yaml",
                "path/to/massif_drd_report",
                "--label",
                "some.target",
                "--tolerance-pct",
                "5",
            ]
        )

        self.assertTrue(opts.stack_usage)
        self.assertTrue(opts.dumps_to_tmpdir)
        self.assertEqual(opts.workdir_data, ["config.yaml"])
        self.assertEqual(
            opts.report,
            [
                "path/to/massif_drd_report",
                "--label",
                "some.target",
                "--tolerance-pct",
                "5",
            ],
        )


class MainTest(unittest.TestCase):
    def _main(
        self, argv: list[str], code: int = 0, extra: list[str] | None = None
    ) -> tuple[int, list[list[str]]]:
        calls: list[list[str]] = []

        def fake_tool(
            args: list[str], cwd: Path | None, opts: object
        ) -> tuple[int, list[str]]:
            calls.append(args)
            return code, extra or []

        def fake_run(command: list[str], **kwargs: object) -> mock.Mock:
            calls.append(command)
            return mock.Mock(returncode=0)

        with _Dirs(), mock.patch.dict(runner.TOOLS, {"massif": fake_tool}, clear=True):
            with mock.patch.object(runner.subprocess, "run", fake_run):
                return runner.main(argv), calls

    def test_fails_without_a_separator(self) -> None:
        returned, calls = self._main(["--tool", "massif", "report"])

        self.assertEqual(returned, 1)
        self.assertEqual(calls, [])

    def test_raises_when_there_is_no_binary_to_run(self) -> None:
        with self.assertRaises(ValueError):
            self._main(["--tool", "massif", "--", "--only-a-flag"])

    def test_hands_the_report_tool_the_output_and_dump_directories(self) -> None:
        returned, calls = self._main(
            ["--tool", "massif", "report_tool", "--label", "x", "--", "prog"],
            extra=["--dump-dir", "/dumps"],
        )

        self.assertEqual(returned, 0)
        self.assertEqual(calls[1][0], "report_tool")
        self.assertEqual(calls[1][1], "--output-dir")
        self.assertEqual(calls[1][3:], ["--dump-dir", "/dumps", "--label", "x"])

    def test_skips_the_report_when_the_tool_failed(self) -> None:
        # A failed run has nothing worth measuring, and its exit code is the
        # answer the test wants.
        returned, calls = self._main(
            ["--tool", "massif", "report_tool", "--", "prog"], code=2
        )

        self.assertEqual(returned, 2)
        self.assertEqual(len(calls), 1)

    def test_returns_the_tool_exit_code_when_there_is_no_report(self) -> None:
        returned, calls = self._main(["--tool", "massif", "--", "prog"], code=1)

        self.assertEqual(returned, 1)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
