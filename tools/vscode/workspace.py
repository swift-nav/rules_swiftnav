"""
Build a VS Code workspace for a Bazel C++ repository.

The workspace every repository gets is defined here: build, format, compile
commands, test and cppcheck tasks, plus a build task and an lldb launch
configuration for each cc_test and cc_binary. A repository adds to it, or
overrides parts of it, with a JSON config (see README.md for its keys).
"""

import json
import xml.etree.ElementTree as ET
from typing import Any, NamedTuple, Optional

BUILD_ALL_TESTS = "Build all tests"

CONFIG_KEYS = frozenset(
    [
        "folders",
        "test_exclude_tags",
        "tasks",
        "disable_tasks",
        "inputs",
        "launch",
        "settings",
        "extensions",
    ]
)

CPPCHECK_REPORT = "cppcheck-output/merged-report.xml"

# Matches the lines printed by @rules_swiftnav//tools/lint:cppcheck_problems.
CPPCHECK_PROBLEM_MATCHER = {
    "owner": "cppcheck",
    "source": "cppcheck-xml",
    "fileLocation": "relative",
    "severity": "warning",
    "pattern": {
        "regexp": "^(.+):(\\d+):(\\d+):\\s+\\[([^\\]]+)\\]\\s+(\\w+):\\s+(.+)$",
        "file": 1,
        "line": 2,
        "column": 3,
        "code": 4,
        "message": 6,
    },
}

EXTENSIONS = [
    "llvm-vs-code-extensions.vscode-clangd",
    "vadimcn.vscode-lldb",
    "bazelbuild.vscode-bazel",
    "github.vscode-pull-request-github",
    "fabiospampinato.vscode-open-in-github",
    "matepek.vscode-catch2-test-adapter",
    "ryanluker.vscode-coverage-gutters",
    "jebbs.plantuml",
    "bierner.markdown-mermaid",
    # Runs the bazel query behind the ccLibraryTarget input.
    "augustocdias.tasks-shell-input",
]


class ConfigError(Exception):
    """A repository config that cannot be used."""


class Target(NamedTuple):
    """A cc target of the repository."""

    label: str
    kind: str
    tags: tuple[str, ...]


def parse_targets(query_xml: str) -> list[Target]:
    """Read the targets of a `bazel query --output=xml`.

    Args:
        query_xml: The query's output.

    Returns:
        The targets, in query order.
    """
    targets = []
    for rule in ET.fromstring(query_xml).iter("rule"):
        tags = rule.find('list[@name="tags"]')
        targets.append(
            Target(
                label=rule.get("name", ""),
                kind=rule.get("class", ""),
                tags=tuple(tag.get("value", "") for tag in tags.iter("string"))
                if tags is not None
                else (),
            )
        )
    return targets


def load_config(text: str, source: str) -> dict[str, Any]:
    """Parse and validate a config.

    Args:
        text: The config's JSON content.
        source: Where the config comes from, for error messages.

    Returns:
        The config.

    Raises:
        ConfigError: The config is not a JSON object of known keys.
    """
    try:
        config = json.loads(text)
    except json.JSONDecodeError as e:
        raise ConfigError(f"{source}: invalid JSON: {e}") from e
    if not isinstance(config, dict):
        raise ConfigError(f"{source}: expected a JSON object")
    unknown = sorted(set(config) - CONFIG_KEYS)
    if unknown:
        raise ConfigError(
            f"{source}: unknown keys {unknown}, expected some of {sorted(CONFIG_KEYS)}"
        )
    return config


def merge_named(base: list[dict], overlay: list[dict], key: str) -> list[dict]:
    """Merge two lists of named entries.

    Args:
        base: The entries to start from.
        overlay: Entries replacing the base entry of the same name, in place,
            or appended if there is none.
        key: The key holding an entry's name.

    Returns:
        The merged entries.
    """
    merged = {entry[key]: entry for entry in base}
    merged.update({entry[key]: entry for entry in overlay})
    return list(merged.values())


def merge_settings(base: dict, overlay: dict) -> dict:
    """Deep merge two settings objects, the overlay winning."""
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_settings(merged[key], value)
        else:
            merged[key] = value
    return merged


def osx_build_options(folder: str) -> str:
    """Options making macOS debug info point at the sources.

    They are absolute paths otherwise, which also defeats the remote cache.
    """
    return f'--linkopt="-Wl,-oso_prefix,." --copt=-fdebug-compilation-dir=${{workspaceFolder:{folder}}}'


def build_task(label: str, command: str, folder: str, **extra: Any) -> dict[str, Any]:
    """A `bazel build -c dbg` task, with the macOS debug info options on macOS.

    Args:
        label: The task's label.
        command: The command, which must contain `bazel build -c dbg`.
        folder: The workspace folder the build runs in.
        **extra: Other task properties.

    Returns:
        The task.
    """
    osx_command = command.replace(
        "bazel build -c dbg", f"bazel build -c dbg {osx_build_options(folder)}", 1
    )
    return {
        "label": label,
        "type": "shell",
        "command": command,
        "osx": {"command": osx_command},
        **extra,
    }


def compile_commands_task(folder: str) -> dict[str, Any]:
    """The task writing compile_commands.json with bazel-compile-commands.

    It passes the options of the build tasks: bazel aquery discards the
    analysis cache when its options differ from the last build's.
    """
    command = "bazel-compile-commands --bazelopt=--compilation_mode=dbg"
    osx_options = [
        f"--bazelopt=--copt=-fdebug-compilation-dir=${{workspaceFolder:{folder}}}",
        "--bazelopt=--linkopt=-Wl,-oso_prefix,.",
    ]
    return {
        "label": "bazel-compile-commands",
        "type": "shell",
        "command": command,
        "osx": {"command": " ".join([command] + osx_options)},
        "hide": True,
    }


def cppcheck_task(label: str, targets: str) -> dict[str, Any]:
    """A task running cppcheck through the lint driver and matching its findings."""
    return {
        "label": label,
        "type": "shell",
        "command": (
            f"bazel run @rules_swiftnav//tools/lint:lint -- --linters cppcheck --targets {targets} ; "
            f"bazel run @rules_swiftnav//tools/lint:cppcheck_problems -- {CPPCHECK_REPORT}"
        ),
        "problemMatcher": CPPCHECK_PROBLEM_MATCHER,
    }


def default_tasks(folder: str, test_exclude_tags: list[str]) -> list[dict[str, Any]]:
    """The tasks every repository gets.

    Args:
        folder: The workspace folder of the repository.
        test_exclude_tags: Tags of tests not to build.

    Returns:
        The tasks.
    """
    build_tests = "bazel query 'tests(//...)' | xargs bazel build -c dbg"
    if test_exclude_tags:
        build_tests += " --build_tag_filters=" + ",".join(
            f"-{tag}" for tag in test_exclude_tags
        )
    return [
        build_task(
            "build",
            "bazel build -c dbg ${input:target}",
            folder,
            group={"kind": "build"},
        ),
        build_task("Build all", "bazel build -c dbg //...", folder, group="build"),
        build_task(
            BUILD_ALL_TESTS,
            build_tests,
            folder,
            group="build",
            presentation={"reveal": "never"},
        ),
        {
            "label": "format",
            "type": "shell",
            "command": "bazel run //tools/format:format",
        },
        compile_commands_task(folder),
        {
            "label": "Generate compile commands",
            "command": "${command:clangd.restart}",
            "dependsOn": ["bazel-compile-commands"],
            "group": {"kind": "build", "isDefault": True},
        },
        {
            "label": "Refresh compile commands",
            "dependsOn": ["Build all", "Generate compile commands"],
            "dependsOrder": "sequence",
            "group": "build",
        },
        {
            "label": "Integration Tests",
            "type": "shell",
            "command": "bazel test --config=integration //...",
        },
        cppcheck_task("Run Cppcheck", "//..."),
        cppcheck_task("Run Cppcheck for Target", "${input:ccLibraryTarget}"),
    ]


def default_task_inputs(folder: str, targets: list[Target]) -> list[dict[str, Any]]:
    """The inputs the default tasks prompt for."""
    return [
        {
            "id": "target",
            "type": "pickString",
            "description": "Which target do you want to build?",
            "default": "//...",
            "options": ["//..."] + [target.label for target in targets],
        },
        {
            "id": "ccLibraryTarget",
            "type": "command",
            "command": "shellCommand.execute",
            "args": {
                "command": "bazel query 'kind(\"cc_library\", //...)' 2>/dev/null | sort",
                "cwd": f"${{workspaceFolder:{folder}}}",
                "useFirstResult": False,
                "useSingleResult": False,
                "description": "Select cc_library target for cppcheck analysis",
            },
        },
    ]


def launch_group(target: Target) -> dict[str, Any]:
    """Where a target's launch configuration shows in the Run and Debug list."""
    if target.kind == "cc_test":
        if "integration" in target.tags:
            return {"group": "integration_test", "order": 2}
        return {"group": "unit_test", "order": 0}
    return {"group": "binaries", "order": 1}


def target_names(targets: list[Target]) -> dict[str, str]:
    """Name each target's task and launch configuration.

    Returns:
        Map of label to name: the target's name, or its full label when
        another target has the same name. A `.binary` suffix is dropped:
        wrapper macros such as orion_cc_binary name their cc_binary so, and
        the wrapper's name is the one people know.
    """
    short = {
        target.label: target.label.split(":")[-1].removesuffix(".binary")
        for target in targets
    }
    counts: dict[str, int] = {}
    for name in short.values():
        counts[name] = counts.get(name, 0) + 1
    return {
        label: name if counts[name] == 1 else label for label, name in short.items()
    }


def target_configurations(
    targets: list[Target], folder: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build tasks and launch configurations of the tests and binaries.

    Args:
        targets: The repository's cc targets.
        folder: The workspace folder of the repository.

    Returns:
        The build tasks and the launch configurations.
    """
    runnable = [target for target in targets if target.kind in ("cc_test", "cc_binary")]
    names = target_names(runnable)
    tasks = []
    launches = []
    for target in runnable:
        name = names[target.label]
        package, _, target_name = target.label.removeprefix("//").partition(":")
        program = f"${{workspaceFolder:{folder}}}/bazel-bin/" + "/".join(
            part for part in (package, target_name) if part
        )
        # --build_runfile_links makes `bazel build` create the runfiles tree,
        # which otherwise only `bazel test` does.
        tasks.append(
            build_task(
                name,
                f"bazel build -c dbg --build_runfile_links {target.label}",
                folder,
                group={"kind": "build"},
            )
        )
        launches.append(
            {
                "type": "lldb",
                "request": "launch",
                "name": name,
                "preLaunchTask": name,
                "program": program,
                "presentation": launch_group(target),
                "args": ["--gtest_filter=${input:gtest_filter}"]
                if target.kind == "cc_test"
                else [],
                "cwd": program + ".runfiles/_main/",
                "linux": {
                    "sourceMap": {"/proc/self/cwd": f"${{workspaceFolder:{folder}}}"}
                },
            }
        )
    return tasks, launches


def default_settings(folder: str, has_lldbinit: bool) -> dict[str, Any]:
    """The settings every repository gets."""
    settings: dict[str, Any] = {
        "clangd.arguments": [
            "--clang-tidy",
            "--background-index",
            "--all-scopes-completion",
            "--completion-style=detailed",
            "--suggest-missing-includes",
            "--header-insertion=never",
            "--inlay-hints=true",
            "--compile-commands-dir=${workspaceFolder}/",
            "--query-driver=**",
        ],
        "clangd.checkUpdates": True,
        "git.blame.editorDecoration.enabled": True,
        "makefile.configureOnOpen": False,
        "bazel.enableCodeLens": True,
        "editor.formatOnType": True,
        "editor.formatOnSave": True,
        "editor.formatOnPaste": True,
        "C_Cpp.clang_format_path": "",
        "files.insertFinalNewline": True,
        "files.trimTrailingWhitespace": True,
        "files.watcherExclude": {"bazel-bin/**/*runfiles*/**/*test*": True},
        "testMate.cpp.test.advancedExecutables": [
            {
                "pattern": "bazel-bin/*[!.]*/*test*",
                "runTask": {"before": [BUILD_ALL_TESTS]},
                "cwd": "${workspaceFolder}",
            }
        ],
        "coverage-gutters.coverageBaseDir": "bazel-out/_coverage/",
        "coverage-gutters.coverageFileNames": ["_coverage_report.dat"],
        # Where the repositories' scripts/generate_code_coverage.sh write the
        # genhtml report of the Bazel one above.
        "coverage-gutters.coverageReportFileName": "code_coverage_html/index.html",
        "coverage-gutters.showLineCoverage": True,
        "coverage-gutters.showRulerCoverage": True,
        "coverage-gutters.watchOnActivate": False,
        "testing.coverageToolbarEnabled": True,
    }
    if has_lldbinit:
        settings["lldb.launch.initCommands"] = [
            f"command source '${{workspaceFolder:{folder}}}/.lldbinit'"
        ]
    return settings


def default_group(task: dict[str, Any]) -> Optional[str]:
    """The group a task is the default task of, if any."""
    group = task.get("group")
    if isinstance(group, dict) and group.get("isDefault"):
        return group.get("kind")
    return None


def yield_default_groups(
    tasks: list[dict[str, Any]], repo_tasks: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Let the repository's default tasks replace the generated ones.

    VS Code prompts instead of running when a group has two default tasks.

    Args:
        tasks: The generated tasks.
        repo_tasks: The repository's tasks.

    Returns:
        The generated tasks, no longer default for the groups the repository
        has a default task for.
    """
    taken = {default_group(task) for task in repo_tasks} - {None}
    return [
        {**task, "group": task["group"]["kind"]}
        if default_group(task) in taken
        else task
        for task in tasks
    ]


def generate(
    config: dict[str, Any],
    targets: list[Target],
    repo_name: str,
    has_lldbinit: bool,
) -> dict[str, Any]:
    """Build the workspace of a repository.

    Args:
        config: The repository's config, as returned by load_config.
        targets: The repository's cc targets.
        repo_name: The repository's name, which names its workspace folder.
        has_lldbinit: Whether the repository has a .lldbinit to source.

    Returns:
        The content of the .code-workspace file.

    Raises:
        ConfigError: The config disables a task that does not exist.
    """
    folder = repo_name
    target_tasks, target_launches = target_configurations(targets, folder)

    repo_tasks = config.get("tasks", [])
    tasks = default_tasks(folder, config.get("test_exclude_tags", [])) + target_tasks
    tasks = yield_default_groups(tasks, repo_tasks)
    tasks = merge_named(tasks, repo_tasks, "label")
    labels = {task["label"] for task in tasks}
    disabled = set(config.get("disable_tasks", []))
    unknown = sorted(disabled - labels)
    if unknown:
        raise ConfigError(f"disable_tasks names tasks that do not exist: {unknown}")
    tasks = [task for task in tasks if task["label"] not in disabled]

    inputs = config.get("inputs", [])
    task_inputs = merge_named(default_task_inputs(folder, targets), inputs, "id")
    gtest_filter = {
        "id": "gtest_filter",
        "type": "promptString",
        "description": "Gtest filter",
        "default": "*",
    }
    launch_inputs = merge_named([gtest_filter], inputs, "id")

    return {
        "folders": config.get("folders", [{"path": ".", "name": folder}]),
        "settings": merge_settings(
            default_settings(folder, has_lldbinit), config.get("settings", {})
        ),
        "extensions": {
            "recommendations": list(
                dict.fromkeys(EXTENSIONS + config.get("extensions", []))
            )
        },
        "tasks": {"version": "2.0.0", "tasks": tasks, "inputs": task_inputs},
        "launch": {
            "version": "0.2.0",
            "configurations": merge_named(
                target_launches, config.get("launch", []), "name"
            ),
            "inputs": launch_inputs,
        },
    }
