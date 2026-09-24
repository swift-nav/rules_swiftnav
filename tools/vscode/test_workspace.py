#!/usr/bin/env python3
"""Tests for workspace.py

Run with Bazel:
    bazel test //tools/...
"""

import unittest

from tools.vscode.workspace import (
    BUILD_ALL_TESTS,
    ConfigError,
    Target,
    generate,
    load_config,
    merge_configs,
    parse_targets,
)

QUERY_XML = """<?xml version="1.1" encoding="UTF-8" standalone="no"?>
<query version="2">
  <rule class="cc_library" location="/w/a/BUILD.bazel:1:1" name="//a:lib">
    <list name="tags"/>
  </rule>
  <rule class="cc_test" location="/w/a/BUILD.bazel:5:1" name="//a:lib_test">
    <list name="tags">
      <string value="unit"/>
    </list>
  </rule>
  <rule class="cc_test" location="/w/b/BUILD.bazel:5:1" name="//b:replay_test">
    <list name="tags">
      <string value="integration"/>
    </list>
  </rule>
  <rule class="cc_binary" location="/w/c/BUILD.bazel:1:1" name="//c:tool.binary"/>
</query>
"""


def by(key: str, items: list) -> dict:
    return {item[key]: item for item in items}


def workspace(config=None, targets=(), has_lldbinit=False) -> dict:
    return generate(
        config=config or {},
        targets=list(targets),
        repo_name="repo",
        has_lldbinit=has_lldbinit,
    )


class TestParseTargets(unittest.TestCase):
    """Reading cc targets out of `bazel query --output=xml`."""

    def test_reads_label_kind_and_tags(self):
        self.assertEqual(
            parse_targets(QUERY_XML),
            [
                Target("//a:lib", "cc_library", ()),
                Target("//a:lib_test", "cc_test", ("unit",)),
                Target("//b:replay_test", "cc_test", ("integration",)),
                Target("//c:tool.binary", "cc_binary", ()),
            ],
        )


class TestLoadConfig(unittest.TestCase):
    """Validating a repository's .vscode-workspace.json."""

    def test_accepts_known_keys(self):
        config = load_config('{"test_exclude_tags": ["fuzz"]}', "cfg.json")
        self.assertEqual(config, {"test_exclude_tags": ["fuzz"]})

    def test_rejects_unknown_keys(self):
        """A typo must not silently drop a setting."""
        with self.assertRaisesRegex(ConfigError, "cfg.json.*setings"):
            load_config('{"setings": {}}', "cfg.json")

    def test_rejects_invalid_json(self):
        with self.assertRaisesRegex(ConfigError, "cfg.json"):
            load_config("{", "cfg.json")


class TestMergeConfigs(unittest.TestCase):
    """Overlaying a developer's local config on the repository's."""

    def test_named_entries_are_replaced_by_name(self):
        merged = merge_configs(
            {"tasks": [{"label": "a", "command": "1"}, {"label": "b", "command": "2"}]},
            {"tasks": [{"label": "a", "command": "3"}, {"label": "c", "command": "4"}]},
        )
        self.assertEqual(
            merged["tasks"],
            [
                {"label": "a", "command": "3"},
                {"label": "b", "command": "2"},
                {"label": "c", "command": "4"},
            ],
        )

    def test_settings_are_deep_merged(self):
        merged = merge_configs(
            {"settings": {"x": {"a": 1, "b": 2}}},
            {"settings": {"x": {"b": 3}}},
        )
        self.assertEqual(merged["settings"], {"x": {"a": 1, "b": 3}})

    def test_extensions_are_combined(self):
        merged = merge_configs({"extensions": ["a", "b"]}, {"extensions": ["b", "c"]})
        self.assertEqual(merged["extensions"], ["a", "b", "c"])

    def test_folders_are_replaced(self):
        merged = merge_configs(
            {"folders": [{"path": "."}]}, {"folders": [{"path": "x"}]}
        )
        self.assertEqual(merged["folders"], [{"path": "x"}])


class TestDefaults(unittest.TestCase):
    """What every repository gets without any configuration."""

    def test_single_folder_named_after_the_repository(self):
        self.assertEqual(workspace()["folders"], [{"path": ".", "name": "repo"}])

    def test_formatting_uses_the_repository_format_target(self):
        tasks = by("label", workspace()["tasks"]["tasks"])
        self.assertEqual(tasks["format"]["command"], "bazel run //tools/format:format")

    def test_compile_commands_use_bazel_compile_commands_with_build_options(self):
        """Options must match `build` so aquery keeps Bazel's analysis cache."""
        tasks = by("label", workspace()["tasks"]["tasks"])
        generate_task = tasks["bazel-compile-commands"]
        self.assertIn("--bazelopt=--compilation_mode=dbg", generate_task["command"])
        self.assertIn(
            "--bazelopt=--copt=-fdebug-compilation-dir=${workspaceFolder:repo}",
            generate_task["osx"]["command"],
        )
        self.assertNotIn(" -b ", generate_task["command"])

    def test_refresh_builds_before_generating_compile_commands(self):
        tasks = by("label", workspace()["tasks"]["tasks"])
        refresh = tasks["Refresh compile commands"]
        self.assertEqual(refresh["dependsOrder"], "sequence")
        self.assertEqual(
            refresh["dependsOn"], ["Build all", "Generate compile commands"]
        )
        self.assertEqual(
            tasks["Generate compile commands"]["command"], "${command:clangd.restart}"
        )

    def test_no_hedron_or_path_mappings(self):
        generated = str(workspace())
        self.assertNotIn("gen_compile_commands", generated)
        self.assertNotIn("--path-mappings", generated)

    def test_cppcheck_uses_the_shared_lint_driver(self):
        tasks = by("label", workspace()["tasks"]["tasks"])
        command = tasks["Run Cppcheck"]["command"]
        self.assertIn(
            "@rules_swiftnav//tools/lint:lint -- --linters cppcheck --targets //...",
            command,
        )
        self.assertIn(
            "@rules_swiftnav//tools/lint:cppcheck_problems -- cppcheck-output/merged-report.xml",
            command,
        )
        self.assertIn(
            "${input:ccLibraryTarget}", tasks["Run Cppcheck for Target"]["command"]
        )

    def test_cc_library_input_runs_in_the_repository(self):
        inputs = by("id", workspace()["tasks"]["inputs"])
        self.assertEqual(
            inputs["ccLibraryTarget"]["args"]["cwd"], "${workspaceFolder:repo}"
        )

    def test_build_all_tests_queries_tests(self):
        tasks = by("label", workspace()["tasks"]["tasks"])
        command = tasks[BUILD_ALL_TESTS]["command"]
        self.assertTrue(
            command.startswith("bazel query 'tests(//...)' | xargs bazel build -c dbg")
        )
        self.assertNotIn("build_tag_filters", command)

    def test_test_explorer_builds_tests_with_the_same_task(self):
        executables = workspace()["settings"]["testMate.cpp.test.advancedExecutables"]
        self.assertEqual(executables[0]["runTask"]["before"], [BUILD_ALL_TESTS])

    def test_no_sonarlint_and_no_rust(self):
        generated = str(workspace()).lower()
        self.assertNotIn("sonarlint", generated)
        self.assertNotIn("rust", generated)

    def test_lldbinit_is_sourced_when_present(self):
        settings = workspace(has_lldbinit=True)["settings"]
        self.assertEqual(
            settings["lldb.launch.initCommands"],
            ["command source '${workspaceFolder:repo}/.lldbinit'"],
        )
        self.assertNotIn("lldb.launch.initCommands", workspace()["settings"])


class TestTargets(unittest.TestCase):
    """Tasks and launch configurations generated per target."""

    TARGETS = parse_targets(QUERY_XML)

    def test_build_input_offers_every_cc_target(self):
        inputs = by("id", workspace(targets=self.TARGETS)["tasks"]["inputs"])
        self.assertEqual(
            inputs["target"]["options"],
            ["//...", "//a:lib", "//a:lib_test", "//b:replay_test", "//c:tool.binary"],
        )

    def test_each_test_and_binary_gets_a_build_task_and_launch(self):
        generated = workspace(targets=self.TARGETS)
        tasks = by("label", generated["tasks"]["tasks"])
        launches = by("name", generated["launch"]["configurations"])
        self.assertEqual(sorted(launches), ["lib_test", "replay_test", "tool"])
        self.assertIn(
            "--build_runfile_links //a:lib_test", tasks["lib_test"]["command"]
        )
        self.assertEqual(launches["lib_test"]["preLaunchTask"], "lib_test")
        self.assertEqual(
            launches["lib_test"]["program"],
            "${workspaceFolder:repo}/bazel-bin/a/lib_test",
        )
        self.assertEqual(
            launches["lib_test"]["cwd"],
            "${workspaceFolder:repo}/bazel-bin/a/lib_test.runfiles/_main/",
        )

    def test_dot_binary_targets_are_named_without_the_suffix(self):
        """Wrapper macros such as orion_cc_binary only define `<name>.binary`."""
        generated = workspace(targets=self.TARGETS)
        tasks = by("label", generated["tasks"]["tasks"])
        launches = by("name", generated["launch"]["configurations"])
        self.assertTrue(
            tasks["tool"]["command"].endswith("--build_runfile_links //c:tool.binary")
        )
        self.assertEqual(
            launches["tool"]["program"],
            "${workspaceFolder:repo}/bazel-bin/c/tool.binary",
        )

    def test_root_package_targets_are_directly_in_bazel_bin(self):
        targets = [Target("//:root_test", "cc_test", ())]
        launches = by("name", workspace(targets=targets)["launch"]["configurations"])
        self.assertEqual(
            launches["root_test"]["program"],
            "${workspaceFolder:repo}/bazel-bin/root_test",
        )

    def test_launches_are_grouped_by_kind(self):
        launches = by(
            "name", workspace(targets=self.TARGETS)["launch"]["configurations"]
        )
        self.assertEqual(launches["lib_test"]["presentation"]["group"], "unit_test")
        self.assertEqual(
            launches["replay_test"]["presentation"]["group"], "integration_test"
        )
        self.assertEqual(launches["tool"]["presentation"]["group"], "binaries")

    def test_only_tests_get_a_gtest_filter(self):
        launches = by(
            "name", workspace(targets=self.TARGETS)["launch"]["configurations"]
        )
        self.assertEqual(
            launches["lib_test"]["args"], ["--gtest_filter=${input:gtest_filter}"]
        )
        self.assertEqual(launches["tool"]["args"], [])

    def test_same_name_in_two_packages_uses_full_labels(self):
        """Short names would make two tasks share a label."""
        targets = [
            Target("//a:t_test", "cc_test", ()),
            Target("//b:t_test", "cc_test", ()),
        ]
        launches = by("name", workspace(targets=targets)["launch"]["configurations"])
        self.assertEqual(sorted(launches), ["//a:t_test", "//b:t_test"])
        self.assertEqual(launches["//b:t_test"]["preLaunchTask"], "//b:t_test")


class TestRepositoryConfig(unittest.TestCase):
    """Repository specific additions and overrides."""

    def test_test_exclude_tags_filter_the_test_build(self):
        tasks = by(
            "label",
            workspace({"test_exclude_tags": ["fuzz", "slow"]})["tasks"]["tasks"],
        )
        self.assertIn(
            "--build_tag_filters=-fuzz,-slow", tasks[BUILD_ALL_TESTS]["command"]
        )
        self.assertIn(
            "--build_tag_filters=-fuzz,-slow", tasks[BUILD_ALL_TESTS]["osx"]["command"]
        )

    def test_tasks_are_added_or_replace_defaults_by_label(self):
        config = {
            "tasks": [
                {"label": "format", "type": "shell", "command": "make format"},
                {"label": "extra", "type": "shell", "command": "true"},
            ]
        }
        tasks = by("label", workspace(config)["tasks"]["tasks"])
        self.assertEqual(tasks["format"]["command"], "make format")
        self.assertIn("extra", tasks)

    def test_tasks_can_be_disabled(self):
        tasks = by(
            "label", workspace({"disable_tasks": ["Run Cppcheck"]})["tasks"]["tasks"]
        )
        self.assertNotIn("Run Cppcheck", tasks)
        self.assertIn("Run Cppcheck for Target", tasks)

    def test_disabling_an_unknown_task_is_an_error(self):
        with self.assertRaisesRegex(ConfigError, "nope"):
            workspace({"disable_tasks": ["nope"]})

    def test_inputs_go_to_tasks_and_launch(self):
        config = {"inputs": [{"id": "token", "type": "promptString"}]}
        generated = workspace(config)
        self.assertIn("token", by("id", generated["tasks"]["inputs"]))
        self.assertIn("token", by("id", generated["launch"]["inputs"]))

    def test_launch_configurations_are_added_or_replace_generated_ones(self):
        config = {
            "launch": [
                {
                    "name": "tool",
                    "type": "lldb",
                    "request": "launch",
                    "program": "x",
                    "args": ["a"],
                },
                {"name": "demo", "type": "lldb", "request": "launch", "program": "y"},
            ]
        }
        launches = by(
            "name",
            workspace(config, targets=parse_targets(QUERY_XML))["launch"][
                "configurations"
            ],
        )
        self.assertEqual(launches["tool"]["args"], ["a"])
        self.assertIn("demo", launches)

    def test_settings_extend_defaults(self):
        settings = workspace(
            {"settings": {"ruff.lineLength": 120, "editor.formatOnType": False}}
        )["settings"]
        self.assertEqual(settings["ruff.lineLength"], 120)
        self.assertFalse(settings["editor.formatOnType"])
        self.assertTrue(settings["editor.formatOnSave"])

    def test_extensions_extend_defaults(self):
        recommendations = workspace({"extensions": ["rust-lang.rust-analyzer"]})[
            "extensions"
        ]["recommendations"]
        self.assertIn("rust-lang.rust-analyzer", recommendations)
        self.assertIn("llvm-vs-code-extensions.vscode-clangd", recommendations)

    def test_folders_replace_the_default(self):
        config = {"folders": [{"path": ".", "name": "repo"}, {"path": "docs"}]}
        self.assertEqual(workspace(config)["folders"], config["folders"])


if __name__ == "__main__":
    unittest.main()
