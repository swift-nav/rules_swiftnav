# VS Code workspace generator

Generates a `.code-workspace` for a Bazel C++ repository:

```bash
bazel run @rules_swiftnav//tools/vscode:generate_workspace
```

This writes `<repository>.code-workspace` at the repository root, where
`<repository>` is the module name in `MODULE.bazel`, so every clone or worktree
generates the same file. Pass `--output` to write it somewhere else.

## What every repository gets

Tasks:

| Task | Command |
|---|---|
| `build` | `bazel build -c dbg <picked target>` |
| `Build all` | `bazel build -c dbg //...` |
| `Build all tests` | `bazel query 'tests(//...)' \| xargs bazel build -c dbg`, also run by the test explorer |
| `format` | `bazel run //tools/format:format` |
| `Generate compile commands` | [bazel-compile-commands](https://github.com/kiron1/bazel-compile-commands), then restarts clangd |
| `Refresh compile commands` | `Build all`, so generated headers exist, then `Generate compile commands` |
| `Integration Tests` | `bazel test --config=integration //...` |
| `Run Cppcheck`, `Run Cppcheck for Target` | `@rules_swiftnav//tools/lint:lint` with cppcheck, findings shown in the Problems panel |

Each `cc_test` and `cc_binary` also gets a build task and an lldb launch
configuration named after the target. Tests take a `--gtest_filter` prompt.

On macOS, builds add `-oso_prefix` and `-fdebug-compilation-dir` so debug info
points at the sources and the remote cache is shared. `Generate compile
commands` passes the same options, since `bazel aquery` otherwise throws away
the analysis cache of the last build.

`bazel-compile-commands` must be on your `PATH`.

The workspace also recommends extensions and sets clangd, formatting, test
explorer and coverage settings. See `workspace.py` for the full list.

## Repository config

An optional `.vscode-workspace.json` at the repository root adds to the
defaults or overrides them. It is strict JSON, with no comments. Unknown keys
are an error.

```json
{
  "test_exclude_tags": ["fuzz"],
  "tasks": [
    {"label": "clang-tidy-integrity", "type": "shell", "command": "bazel build -k --config=clang-tidy-check --build_tag_filters=ASIL-B //..."}
  ],
  "disable_tasks": ["Integration Tests"],
  "inputs": [{"id": "featureFile", "type": "promptString", "description": "Path to feature file"}],
  "launch": [{"name": "Debug demo", "type": "lldb", "request": "launch", "program": "${workspaceFolder}/bazel-bin/demo"}],
  "settings": {"ruff.lineLength": 120},
  "extensions": ["charliermarsh.ruff"]
}
```

| Key | Effect |
|---|---|
| `folders` | Replaces the workspace folders, `[{"path": ".", "name": "<repository>"}]` by default. |
| `test_exclude_tags` | Tags of tests `Build all tests` skips, through `--build_tag_filters`. |
| `tasks` | Added, or replace the task with the same `label`. |
| `disable_tasks` | Labels of tasks to remove. Naming a task that does not exist is an error. |
| `inputs` | Added to the task and launch inputs, or replace the one with the same `id`. |
| `launch` | Added, or replace the launch configuration with the same `name`. |
| `settings` | Deep merged over the default settings. |
| `extensions` | Added to the recommended extensions. |

A `.vscode-workspace.local.json` with the same keys is applied on top, for
settings of your own, such as a crash file to debug. Keep it out of version
control.
