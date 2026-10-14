#!/usr/bin/env python3
"""Tests for generate_workspace.py

Run with Bazel:
    bazel test //tools/...
"""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from tools.vscode.generate_workspace import main

QUERY_XML = """<query version="2">
  <rule class="cc_test" name="//a:a_test"><list name="tags"/></rule>
</query>
"""


class TestMain(unittest.TestCase):
    """Writing the workspace file of a repository."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "my-repo"
        self.repo.mkdir()
        self.queried_in: list[Path] = []

    def tearDown(self):
        self.tmp.cleanup()

    def query(self, workspace_dir: Path) -> str:
        self.queried_in.append(workspace_dir)
        return QUERY_XML

    def run_main(self, argv=(), environ=None) -> int:
        if environ is None:
            environ = {"BUILD_WORKSPACE_DIRECTORY": str(self.repo)}
        return main(list(argv), environ=environ, query=self.query)

    def written(self, name="my-repo.code-workspace") -> dict:
        return json.loads((self.repo / name).read_text())

    def test_writes_workspace_of_the_bazel_run_workspace(self):
        self.assertEqual(self.run_main(), 0)
        self.assertEqual(self.queried_in, [self.repo])
        workspace = self.written()
        self.assertEqual(workspace["folders"], [{"path": ".", "name": "my-repo"}])
        self.assertIn(
            "a_test", [c["name"] for c in workspace["launch"]["configurations"]]
        )

    def test_output_can_be_chosen(self):
        environ = {
            "BUILD_WORKSPACE_DIRECTORY": str(self.repo),
            "BUILD_WORKING_DIRECTORY": str(self.repo),
        }
        self.assertEqual(
            self.run_main(["--output", "custom.code-workspace"], environ), 0
        )
        self.assertIn("folders", self.written("custom.code-workspace"))

    def test_output_is_relative_to_where_bazel_run_was_invoked(self):
        subdir = self.repo / "sub"
        subdir.mkdir()
        environ = {
            "BUILD_WORKSPACE_DIRECTORY": str(self.repo),
            "BUILD_WORKING_DIRECTORY": str(subdir),
        }
        self.assertEqual(self.run_main(["--output", "w.code-workspace"], environ), 0)
        self.assertTrue((subdir / "w.code-workspace").exists())

    def test_repository_config_is_applied(self):
        (self.repo / ".vscode-workspace.json").write_text(
            json.dumps({"settings": {"a": 1}, "test_exclude_tags": ["fuzz"]})
        )
        self.assertEqual(self.run_main(), 0)
        self.assertEqual(self.written()["settings"]["a"], 1)

    def test_personal_additions_are_left_to_vscode(self):
        """Per developer settings, tasks and launches go in the ignored .vscode/."""
        (self.repo / ".vscode-workspace.local.json").write_text(
            json.dumps({"settings": {"b": 2}})
        )
        self.assertEqual(self.run_main(), 0)
        self.assertNotIn("b", self.written()["settings"])

    def test_repository_is_named_after_its_module(self):
        """Worktrees and clones under another directory name give the same file."""
        (self.repo / "MODULE.bazel").write_text(
            'module(\n    name = "the-module",\n    version = "0.1.0",\n)\n'
        )
        self.assertEqual(self.run_main(), 0)
        workspace = self.written("the-module.code-workspace")
        self.assertEqual(workspace["folders"], [{"path": ".", "name": "the-module"}])

    def test_lldbinit_is_detected(self):
        (self.repo / ".lldbinit").write_text("")
        self.assertEqual(self.run_main(), 0)
        self.assertIn("lldb.launch.initCommands", self.written()["settings"])

    def test_invalid_config_fails_without_writing(self):
        (self.repo / ".vscode-workspace.json").write_text('{"typo": 1}')
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(self.run_main(), 1)
        self.assertIn("typo", err.getvalue())
        self.assertFalse((self.repo / "my-repo.code-workspace").exists())

    def test_outside_bazel_run_the_workspace_must_be_given(self):
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(self.run_main(environ={}), 1)
        self.assertEqual(
            self.run_main(["--workspace-dir", str(self.repo)], environ={}), 0
        )
        self.assertEqual(self.queried_in, [self.repo])


if __name__ == "__main__":
    unittest.main()
