#!/usr/bin/env python3
"""Tests for runner.py

Run with Bazel:
    bazel test //tools/valgrind/...
"""

import os
import tempfile
import unittest
from pathlib import Path
from typing import ClassVar
from unittest import mock

import runner

_STACK_LINES = (
    "==42== thread 1 finished and used 2097152 bytes out of 8388608 on its stack. Margin: 6291456 bytes.\n"
    "==42== Thread 2:\n"
    "==42== Conflicting load by thread 2 at 0x1234 size 4\n"
    "==42== thread 2 finished and used 1048576 bytes out of 8388608 on its stack. Margin: 7340032 bytes.\n"
)


class _Dirs:
    """A temporary stand-in for the three directories a run works in.

    The working directory moves to the stand-in runfiles, because that is where
    a py_test starts and what the relative paths $(location) expands to are
    resolved against.
    """

    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name).resolve()
        self.output = root / "outputs"
        self.scratch = root / "scratch"
        self.runfiles = root / "runfiles"
        for path in (self.output, self.scratch, self.runfiles):
            path.mkdir()

    def __enter__(self) -> "_Dirs":
        self._cwd = Path.cwd()
        os.chdir(self.runfiles)
        return self

    def __exit__(self, *exc: object) -> None:
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def file(self, name: str, content: str = "") -> Path:
        path = self.runfiles / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def opts(self, **extra: object) -> runner.argparse.Namespace:
        return runner.argparse.Namespace(
            output_dir=self.output,
            tmpdir=self.scratch,
            stack_usage=False,
            env=None,
            **extra,
        )


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
                ],
                dirs.output,
                dirs.scratch,
            )

            self.assertEqual(args[0], f"--supp={dirs.runfiles}/googletest.supp")
            self.assertEqual(args[3], f"{dirs.output}/report")
            self.assertEqual(args[5], f"{dirs.scratch}/scratch")

    def test_absolutises_the_binary_and_leaves_the_rest_alone(self) -> None:
        # The binary has to be absolute because it may run from a working
        # directory of its own; its arguments are the caller's business.
        with _Dirs() as dirs:
            binary = dirs.file("bin/prog")

            args = runner.expand(
                ["--tool=massif", "bin/prog", "relative/arg"], dirs.output, dirs.scratch
            )

            self.assertEqual(args, ["--tool=massif", str(binary), "relative/arg"])

    def test_takes_the_first_non_flag_as_the_binary(self) -> None:
        with _Dirs() as dirs:
            first = dirs.file("first")
            dirs.file("second")

            args = runner.expand(["-q", "first", "second"], dirs.output, dirs.scratch)

            self.assertEqual(args[1], str(first))
            self.assertEqual(args[2], "second")

    def test_raises_when_every_argument_is_a_flag(self) -> None:
        with _Dirs() as dirs, self.assertRaises(ValueError):
            runner.expand(["--only-a-flag"], dirs.output, dirs.scratch)


class WorkdirTest(unittest.TestCase):
    def test_stays_in_the_runfiles_without_workdir_data(self) -> None:
        with _Dirs() as dirs:
            self.assertIsNone(runner.workdir([], dirs.scratch))

    def test_symlinks_files_in_by_basename(self) -> None:
        # A config naming its inputs by bare filename has to resolve them from
        # the working directory, whatever their path in the runfiles was.
        with _Dirs() as dirs:
            dirs.file("deep/nested/config.yaml", "key: value\n")

            path = runner.workdir(["deep/nested/config.yaml"], dirs.scratch)

            self.assertEqual(sorted(p.name for p in path.iterdir()), ["config.yaml"])
            self.assertEqual((path / "config.yaml").read_text(), "key: value\n")

    def test_raises_rather_than_shadowing_a_shared_basename(self) -> None:
        with _Dirs() as dirs:
            dirs.file("a/config.yaml", "a\n")
            dirs.file("b/config.yaml", "b\n")

            with self.assertRaises(FileExistsError):
                runner.workdir(["a/config.yaml", "b/config.yaml"], dirs.scratch)


class DrdStackUsageTest(unittest.TestCase):
    def _run(self, *logs: str, code: int = 0) -> tuple[int, str | None]:
        """Run a DRD pass writing one log per child, returning its exit code and report."""
        with _Dirs() as dirs:

            def fake_valgrind(
                label: str,
                flags: list[str],
                args: list[str],
                cwd: Path | None,
                env: dict[str, str] | None = None,
            ) -> int:
                for pid, text in enumerate(logs):
                    (dirs.scratch / f"drd.log.{pid}").write_text(text)
                return code

            with mock.patch.object(runner, "valgrind", fake_valgrind):
                returned = runner.drd_stack_usage(["prog"], None, dirs.opts())

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
        # An empty report would stop massif_drd_measure falling back on massif's
        # own stack figure, and fail the target with a misleading error.
        self.assertIsNone(self._run("==42== no stack usage here\n")[1])

    def test_writes_no_report_when_the_pass_never_logged(self) -> None:
        self.assertIsNone(self._run()[1])

    def test_returns_the_drd_exit_code(self) -> None:
        # A DRD pass that failed must fail the target rather than leave the
        # stack figure quietly unmeasured.
        self.assertEqual(self._run(code=3)[0], 3)


class ToolFlagsTest(unittest.TestCase):
    def _flags(self, tool: str, **opts: bool) -> list[str]:
        """Run one tool with valgrind stubbed out, returning the flags it passed."""
        captured: list[list[str]] = []

        with _Dirs() as dirs:

            def fake_valgrind(
                label: str,
                flags: list[str],
                args: list[str],
                cwd: Path | None,
                env: dict[str, str] | None = None,
            ) -> int:
                captured.append(flags)
                return 0

            with mock.patch.object(runner, "valgrind", fake_valgrind):
                runner.TOOLS[tool](["prog"], None, dirs.opts(**opts))
        return captured[0]

    def test_callgrind_writes_a_dump_per_process(self) -> None:
        flags = self._flags("callgrind")

        self.assertIn("--tool=callgrind", flags)
        self.assertTrue(
            any(
                f.startswith("--callgrind-out-file=")
                and f.endswith("valgrind-callgrind.%p")
                for f in flags
            )
        )

    def test_memcheck_writes_xml_per_process(self) -> None:
        flags = self._flags("memcheck")

        self.assertIn("--tool=memcheck", flags)
        self.assertIn("--xml=yes", flags)
        self.assertTrue(any(f.endswith("valgrind-memcheck.%p.xml") for f in flags))

    def test_massif_writes_its_dumps_to_the_output_directory(self) -> None:
        flags = self._flags("massif")

        self.assertIn("--tool=massif", flags)
        self.assertTrue(
            any(
                f.startswith("--massif-out-file=") and f.endswith("valgrind-massif.%p")
                for f in flags
            )
        )


class ChildEnvTest(unittest.TestCase):
    _INHERITED: ClassVar[dict[str, str]] = {
        "RUNFILES_DIR": "/the/runners/own.runfiles",
        "RUNFILES_MANIFEST_FILE": "/the/runners/own.runfiles_manifest",
        "PYTHONPATH": "/the/runners/deps",
        "PATH": "/usr/bin",
    }

    def _env(self, layout: str, extra: list[str] | None = None) -> dict[str, str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary = root / "prog"
            binary.write_text("")
            if layout == "tree":
                (root / "prog.runfiles").mkdir()
            elif layout == "manifest":
                (root / "prog.runfiles_manifest").write_text("")

            with mock.patch.dict(os.environ, self._INHERITED, clear=True):
                return runner.child_env(binary, root / "scratch", extra or [])

    def test_points_a_tree_at_the_binarys_own_runfiles(self) -> None:
        # Whatever the runner inherited describes the runner's tree, and a binary
        # resolving its data against that would look in the wrong one.
        env = self._env("tree")

        self.assertTrue(env["RUNFILES_DIR"].endswith("prog.runfiles"))
        self.assertNotIn("RUNFILES_MANIFEST_FILE", env)

    def test_falls_back_on_a_manifest_when_there_is_no_tree(self) -> None:
        env = self._env("manifest")

        self.assertTrue(
            env["RUNFILES_MANIFEST_FILE"].endswith("prog.runfiles_manifest")
        )
        self.assertNotIn("RUNFILES_DIR", env)

    def test_leaves_a_test_environment_alone(self) -> None:
        # Under a test the binary lives inside the test's own tree, so what the
        # runner inherited already describes it.
        env = self._env("none")

        self.assertEqual(env["RUNFILES_DIR"], self._INHERITED["RUNFILES_DIR"])
        self.assertEqual(
            env["RUNFILES_MANIFEST_FILE"], self._INHERITED["RUNFILES_MANIFEST_FILE"]
        )
        self.assertEqual(env["PYTHONPATH"], self._INHERITED["PYTHONPATH"])

    def test_scrubs_the_python_parents_interpreter(self) -> None:
        self.assertNotIn("PYTHONPATH", self._env("tree"))

    def test_stands_in_for_the_test_variables_a_gtest_binary_expects(self) -> None:
        env = self._env("tree")

        self.assertTrue(env["TEST_TMPDIR"].endswith("scratch"))
        self.assertTrue(env["TEST_SRCDIR"].endswith("prog.runfiles"))

    def test_the_caller_wins(self) -> None:
        env = self._env("tree", ["TEST_TMPDIR=/mine", "MY_FLAG=1"])

        self.assertEqual(env["TEST_TMPDIR"], "/mine")
        self.assertEqual(env["MY_FLAG"], "1")

    def test_the_caller_wins_in_a_test_environment_too(self) -> None:
        self.assertEqual(self._env("none", ["MY_FLAG=1"])["MY_FLAG"], "1")


class ResolveDirsTest(unittest.TestCase):
    def _resolve(
        self, environ: dict[str, str], **flags: object
    ) -> runner.argparse.Namespace:
        opts = runner.argparse.Namespace(output_dir=None, tmpdir=None, **flags)
        with mock.patch.dict(os.environ, environ, clear=True):
            runner.resolve_dirs(opts)
        return opts

    def test_falls_back_on_the_test_environment(self) -> None:
        opts = self._resolve(
            {"TEST_UNDECLARED_OUTPUTS_DIR": "/outs", "TEST_TMPDIR": "/tmp/t"}
        )

        self.assertEqual(opts.output_dir, Path("/outs"))
        self.assertEqual(opts.tmpdir, Path("/tmp/t"))

    def test_invents_directories_when_run_by_hand(self) -> None:
        opts = runner.argparse.Namespace(output_dir=None, tmpdir=None)
        with mock.patch.dict(os.environ, {}, clear=True):
            invented = runner.resolve_dirs(opts)

        self.assertTrue(opts.output_dir.is_dir())
        self.assertTrue(opts.tmpdir.is_dir())
        # Reported back so main can remove them: a build action leaves no test
        # environment behind to clean up after it, and a callgrind dump left
        # behind every build runs to tens of megabytes.
        self.assertEqual(sorted(invented), sorted([opts.output_dir, opts.tmpdir]))

    def test_claims_nothing_it_was_given(self) -> None:
        opts = runner.argparse.Namespace(output_dir=Path("/passed"), tmpdir=None)
        with mock.patch.dict(os.environ, {"TEST_TMPDIR": "/tmp/t"}, clear=True):
            self.assertEqual(runner.resolve_dirs(opts), [])

    def test_the_dump_override_beats_the_flag(self) -> None:
        # A build action always passes its own scratch directory, so overriding
        # it is the only way to keep the raw dumps.
        with tempfile.TemporaryDirectory() as tmp:
            override = Path(tmp) / "kept"
            opts = runner.argparse.Namespace(output_dir=Path("/passed"), tmpdir=None)

            with mock.patch.dict(
                os.environ, {"VALGRIND_DUMP_DIR": str(override)}, clear=True
            ):
                runner.resolve_dirs(opts)

            self.assertEqual(opts.output_dir, override)
            self.assertTrue(override.is_dir())


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
                "--output-dir",
                "outs",
                "--env",
                "MY_FLAG=1",
                "--workdir-data",
                "config.yaml",
                "path/to/massif_drd_measure",
                "--label",
                "some.target",
                "--measurement-out",
                "m.json",
            ]
        )

        self.assertTrue(opts.stack_usage)
        self.assertEqual(opts.output_dir, Path("outs"))
        self.assertEqual(opts.env, ["MY_FLAG=1"])
        self.assertEqual(opts.workdir_data, ["config.yaml"])
        self.assertEqual(
            opts.report,
            [
                "path/to/massif_drd_measure",
                "--label",
                "some.target",
                "--measurement-out",
                "m.json",
            ],
        )


class MainTest(unittest.TestCase):
    def _main(self, argv: list[str], code: int = 0) -> tuple[int, list[list[str]]]:
        calls: list[list[str]] = []

        def fake_tool(args: list[str], cwd: Path | None, opts: object) -> int:
            calls.append(args)
            return code

        def fake_run(command: list[str], **kwargs: object) -> mock.Mock:
            calls.append(command)
            return mock.Mock(returncode=0)

        with _Dirs() as dirs:
            argv = [
                "--output-dir",
                str(dirs.output),
                "--tmpdir",
                str(dirs.scratch),
                *argv,
            ]
            with (
                mock.patch.dict(runner.TOOLS, {"massif": fake_tool}, clear=True),
                mock.patch.object(runner.subprocess, "run", fake_run),
                mock.patch.dict(os.environ, {}, clear=True),
            ):
                return runner.main(argv), calls

    def test_fails_without_a_separator(self) -> None:
        returned, calls = self._main(["--tool", "massif", "report"])

        self.assertEqual(returned, 1)
        self.assertEqual(calls, [])

    def test_raises_when_there_is_no_binary_to_run(self) -> None:
        with self.assertRaises(ValueError):
            self._main(["--tool", "massif", "--", "--only-a-flag"])

    def test_hands_the_report_tool_the_output_directory(self) -> None:
        returned, calls = self._main(
            ["--tool", "massif", "report_tool", "--label", "x", "--", "prog"]
        )

        self.assertEqual(returned, 0)
        self.assertEqual(calls[1][0], "report_tool")
        self.assertEqual(calls[1][1], "--output-dir")
        self.assertEqual(calls[1][3:], ["--label", "x"])

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

    def test_removes_the_directories_it_invented_even_on_failure(self) -> None:
        invented: list[Path] = []

        def fake_tool(args: list[str], cwd: Path | None, opts: object) -> int:
            invented.extend([opts.output_dir, opts.tmpdir])
            return 1

        with (
            _Dirs(),
            mock.patch.dict(runner.TOOLS, {"massif": fake_tool}, clear=True),
            mock.patch.dict(os.environ, {}, clear=True),
        ):
            self.assertEqual(runner.main(["--tool", "massif", "--", "prog"]), 1)

        self.assertEqual(len(invented), 2)
        for path in invented:
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
