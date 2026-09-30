#!/usr/bin/env python3
"""Tests for the compile_commands shell scripts.

Run with Bazel:
    bazel test //compile_commands:test_compile_commands
"""

import os
import shutil
import stat
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).parent
WRAPPER = HERE / "bazel_wrapper.sh"
CHECK_SETUP = HERE / "check_setup.sh"
BAZELCCRC = HERE / ".bazelccrc"

REFRESH_LABEL = "@rules_swiftnav//compile_commands:refresh"

# Stands in for the real Bazel binary: records every invocation and lets the
# test choose the exit code of regular commands and of the refresh target.
FAKE_BAZEL = f"""#!/usr/bin/env bash
echo "$*" >>"${{FAKE_BAZEL_LOG}}"
for arg in "$@"; do
    if [[ "${{arg}}" == "{REFRESH_LABEL}" ]]; then
        echo "fake refresh output"
        echo "fake refresh error" >&2
        exit "${{FAKE_REFRESH_EXIT:-0}}"
    fi
done
exit "${{FAKE_BAZEL_EXIT:-0}}"
"""

GITIGNORE = "/compile_commands.json\n/external\n/.cache/\n"


def make_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


class WorkspaceTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        # macOS temp directories are symlinks, the scripts resolve them.
        self.workspace = Path(tmp).resolve() / "workspace"
        (self.workspace / "tools").mkdir(parents=True)
        self.wrapper = self.workspace / "tools" / "bazel"
        shutil.copy(WRAPPER, self.wrapper)
        make_executable(self.wrapper)


class TestBazelWrapper(WorkspaceTestCase):
    def setUp(self):
        super().setUp()
        self.fake_bazel = self.workspace.parent / "fake_bazel"
        self.fake_bazel.write_text(FAKE_BAZEL)
        make_executable(self.fake_bazel)
        self.log = self.workspace.parent / "invocations.log"
        self.error_file = self.workspace / ".cache" / "compile_commands.error"

    def run_wrapper(self, *args, cwd=None, **env):
        full_env = {
            "PATH": os.environ["PATH"],
            "BAZEL_REAL": str(self.fake_bazel),
            "FAKE_BAZEL_LOG": str(self.log),
        }
        full_env.update({key: str(value) for key, value in env.items()})
        return subprocess.run(
            [str(self.wrapper), *args],
            cwd=cwd or self.workspace,
            env=full_env,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def invocations(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def refresh_invocations(self):
        return [line for line in self.invocations() if REFRESH_LABEL in line]

    def wait_for(self, condition, timeout=10.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if condition():
                return True
            time.sleep(0.05)
        return condition()

    def test_forwards_arguments_and_exit_code(self):
        result = self.run_wrapper(
            "build", "//foo:bar", "--keep_going", FAKE_BAZEL_EXIT=7
        )
        self.assertEqual(result.returncode, 7)
        self.assertEqual(self.invocations()[0], "build //foo:bar --keep_going")

    def test_refreshes_in_background_after_build_test_and_run(self):
        for command in ("build", "test", "run"):
            with self.subTest(command=command):
                self.log.unlink(missing_ok=True)
                self.run_wrapper(command, "//foo:bar")
                self.assertTrue(self.wait_for(lambda: self.refresh_invocations()))
                self.assertIn("--background", self.refresh_invocations()[0])

    def test_startup_options_do_not_hide_the_command(self):
        self.run_wrapper("--host_jvm_args=-Xmx4g", "build", "//foo:bar")
        self.assertTrue(self.wait_for(lambda: self.refresh_invocations()))

    def test_no_refresh_for_other_commands(self):
        self.run_wrapper("query", "//...")
        time.sleep(0.5)
        self.assertEqual(self.refresh_invocations(), [])

    def test_no_refresh_in_ci(self):
        self.run_wrapper("build", "//foo:bar", CI="true")
        time.sleep(0.5)
        self.assertEqual(self.refresh_invocations(), [])

    def test_no_refresh_when_called_by_a_refresh(self):
        self.run_wrapper("build", "//foo:bar", BCC_REFRESH="1")
        time.sleep(0.5)
        self.assertEqual(self.refresh_invocations(), [])

    def test_failed_refresh_leaves_an_error_file(self):
        result = self.run_wrapper("build", "//foo:bar", FAKE_REFRESH_EXIT=1)
        # The refresh must never change the outcome of the user's command.
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self.wait_for(self.error_file.exists))
        content = self.error_file.read_text()
        self.assertIn("fake refresh output", content)
        self.assertIn("fake refresh error", content)
        self.assertIn("exit code 1", content)

    def test_successful_refresh_removes_the_error_file(self):
        self.error_file.parent.mkdir()
        self.error_file.write_text("stale failure\n")
        self.run_wrapper("build", "//foo:bar")
        self.assertTrue(self.wait_for(lambda: not self.error_file.exists()))

    def test_error_file_lands_in_the_workspace_root_from_a_subdirectory(self):
        subdir = self.workspace / "some" / "package"
        subdir.mkdir(parents=True)
        self.run_wrapper("build", ":bar", cwd=subdir, FAKE_REFRESH_EXIT=1)
        self.assertTrue(self.wait_for(self.error_file.exists))
        self.assertFalse((subdir / ".cache").exists())

    def test_nothing_is_printed_by_the_refresh(self):
        result = self.run_wrapper("build", "//foo:bar", FAKE_REFRESH_EXIT=1)
        self.assertTrue(self.wait_for(self.error_file.exists))
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")


class TestCheckSetup(WorkspaceTestCase):
    def setUp(self):
        super().setUp()
        shutil.copy(BAZELCCRC, self.workspace / ".bazelccrc")
        (self.workspace / ".gitignore").write_text(GITIGNORE)
        subprocess.run(["git", "init", "--quiet", str(self.workspace)], check=True)

    def run_check(self):
        return subprocess.run(
            [str(CHECK_SETUP), f"--wrapper={WRAPPER}"],
            env={
                "PATH": os.environ["PATH"],
                "BUILD_WORKSPACE_DIRECTORY": str(self.workspace),
            },
            capture_output=True,
            text=True,
            timeout=60,
        )

    def assert_fails_with(self, message):
        result = self.run_check()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(message, result.stderr)

    def test_passes_on_a_complete_setup(self):
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_fails_without_wrapper(self):
        self.wrapper.unlink()
        self.assert_fails_with("tools/bazel is missing")

    def test_fails_on_outdated_wrapper(self):
        self.wrapper.write_text(self.wrapper.read_text() + "# local change\n")
        self.assert_fails_with("tools/bazel differs from")

    def test_fails_on_non_executable_wrapper(self):
        self.wrapper.chmod(0o644)
        self.assert_fails_with("tools/bazel is not executable")

    def test_fails_without_bazelccrc(self):
        (self.workspace / ".bazelccrc").unlink()
        self.assert_fails_with(".bazelccrc is missing")

    def test_fails_when_generated_files_are_not_ignored(self):
        for entry in ("compile_commands.json", "external", ".cache/"):
            with self.subTest(entry=entry):
                kept = [line for line in GITIGNORE.splitlines() if line != f"/{entry}"]
                (self.workspace / ".gitignore").write_text("\n".join(kept) + "\n")
                self.assert_fails_with(f"{entry} is not ignored by git")

    def test_reports_every_problem_at_once(self):
        self.wrapper.unlink()
        (self.workspace / ".bazelccrc").unlink()
        result = self.run_check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("tools/bazel is missing", result.stderr)
        self.assertIn(".bazelccrc is missing", result.stderr)

    def test_requires_the_workspace_directory(self):
        result = subprocess.run(
            [str(CHECK_SETUP), f"--wrapper={WRAPPER}"],
            env={"PATH": os.environ["PATH"]},
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
