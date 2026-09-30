# Automatic `compile_commands.json` Generation

Keeps `compile_commands.json` up to date on every developer machine of a
repository depending on `rules_swiftnav`, without manual steps. The only
per-machine prerequisite is Bazelisk.

## Setup in a Downstream Repository

Requirements: the workspace is inside a git repository and Bazel is invoked via
Bazelisk.

1. Copy [`.bazelccrc`](.bazelccrc) to the workspace root.
2. Copy [`bazel_wrapper.sh`](bazel_wrapper.sh) to `tools/bazel` in the
   workspace root and commit it with the executable bit set
   (`git update-index --chmod=+x tools/bazel`).
3. Add to `.gitignore`:

   ```gitignore
   /compile_commands.json
   /external
   /.cache/
   ```

Re-copy both files when upgrading `rules_swiftnav` if they changed. To notice
when they did, run the setup check in CI. It fails if `tools/bazel` differs from
the template, is not executable, `.bazelccrc` is missing or one of the entries
above is not ignored:

```bash
bazel run @rules_swiftnav//compile_commands:check_setup
```

Manual, forced regeneration, e.g. from a `Makefile`:

```bash
bazel run @rules_swiftnav//compile_commands:refresh -- --force
```

`examples/small_world` is a working example.

## Troubleshooting

The background refresh never prints to the terminal. If `compile_commands.json`
is missing or stale after a build, look at:

- `.cache/compile_commands.error`: exists only while the last background refresh
  failed, with the exit code and the output of the `bazel run`. The next
  successful refresh removes it.
- `.cache/compile_commands.log`: output of the last regeneration.

Then run the forced regeneration above, which prints to the terminal.

## What the Database Covers

- **One database per checkout.** clangd searches parent directories, so a git
  worktree nested in another checkout silently uses that checkout's database
  until it has its own. Build once in every new clone or worktree.
- **Built targets only.** Include paths point to directories Bazel generates
  during the build (`bazel-out/.../_virtual_includes/`). A file parses only once
  its target has been built, so build `//...` rather than a single package.
- **Host default configuration only.** Sources that are only built for another
  platform or with a `--config` have no entry, and clangd guesses their flags.
  List such directories in the repository's own documentation.
- **No header entries.** clangd borrows the flags of a similarly named source
  file, which is occasionally one from another package. Diagnostics in a header
  are less reliable than in a source file that includes it.
- **New files.** A new source file gets its entry with the first
  `build`/`test`/`run` after it was added to a `BUILD` file.

Floods of `file not found`, `unknown type name` or `use of undeclared identifier`
are the symptom of each of these, not a problem in the code.

## Editors and Coding Agents

- Use a clangd of the same major version as the toolchain (LLVM 20).
- `external/` and `bazel-*` point into the Bazel output base. Exclude them from
  search and file watching, and never edit files there: Bazel does not notice the
  change in repositories that disable the check for modified external files, and
  builds get silently wrong.
- A job that sets `CI`, e.g. an agent reviewing a pull request, gets no database
  from the wrapper. Run the forced regeneration explicitly if it needs one.

For repositories that use Claude Code, add this to `CLAUDE.md`:

```markdown
## Language server (clangd)

`compile_commands.json` is generated automatically after `bazel build|test|run`
(via `tools/bazel`, requires bazelisk).

- In a fresh clone or worktree, run `bazel build //...` once before trusting clangd
  diagnostics. The database and the generated include directories both come from it.
- Floods of `file not found`, `unknown type name` or `use of undeclared identifier`
  mean the database is missing or stale, not that the code is wrong. Do not edit code
  to silence them. Check that `compile_commands.json` exists in this worktree's root
  and read `.cache/compile_commands.error` and `.cache/compile_commands.log`, then run
  `bazel run @rules_swiftnav//compile_commands:refresh -- --force`.
- After adding a source file or editing a `BUILD.bazel`, build before reading
  diagnostics for it.
- Header diagnostics are less reliable than source diagnostics. Confirm against a
  `.cc` that includes the header.
- `external/` and `bazel-*` are generated trees. Never edit files there.
```

## How It Works

Generation uses [kiron1/bazel-compile-commands](https://github.com/kiron1/bazel-compile-commands)
(`bcc`). Bazelisk runs `tools/bazel` instead of Bazel; after a `build`, `test`
or `run` the wrapper starts `@rules_swiftnav//compile_commands:refresh` in the
background. The wrapper forwards output and exit code of Bazel unchanged.

```mermaid
flowchart TD
    Dev["Developer: bazel build/test/run"] --> Bazelisk
    Bazelisk -->|"exec, sets BAZEL_REAL"| Wrapper["tools/bazel"]
    Wrapper -->|"forward args, keep exit code"| Bazel["$BAZEL_REAL"]
    Wrapper -->|"background, unless CI or BCC_REFRESH"| Refresh["compile_commands:refresh"]
    Manual["bazel run ... -- --force"] --> Refresh
    Refresh --> Stale{"build structure changed<br/>or --force?"}
    Stale -- no --> Done(["up to date"])
    Stale -- yes --> BCC["bcc (reads .bazelccrc)"]
    BCC -->|"aquery"| Bazel
    BCC --> Rewrite["rewrite paths, symlink external/"]
    Rewrite --> DB["compile_commands.json"]
    Clangd["clangd / IDE"] -->|"reads"| DB
```

`refresh` regenerates the database only if the build structure changed since the
last run. It hashes the names and contents of `BUILD`, `BUILD.bazel`, `*.bzl`,
`*.bazelrc`, `toolchains/**`, `.bazelrc`, `.bazeliskrc`, `.bazelccrc`,
`MODULE.bazel`, `MODULE.bazel.lock` and `.bazelrc.user`, plus the names (not
contents) of C/C++ sources and headers. Concurrent runs are serialized through a
lock in `.cache/`; background output goes to `.cache/compile_commands.log`, a
failed background run is recorded in `.cache/compile_commands.error`.

`bcc` emits paths relative to the execution root. `refresh` rewrites them to the
workspace and symlinks `<workspace>/external` to `<output_base>/external`, so
external headers stay reachable for clangd.

## Notes

- The wrapper does nothing if `CI` is set. `BAZELISK_SKIP_WRAPPER=1` bypasses it
  entirely.
- `.bazelccrc` deliberately has no `config` entries: `aquery` must use the
  default build flags, otherwise it discards Bazel's analysis cache of regular
  builds. For the same reason `refresh` runs with default flags, even after a
  `--config=X` build. The cost moves to builds with non-default flags: every
  such build re-runs analysis because the refresh in between discarded it
  (about 1 s instead of 0.15 s in starling-core).
- The `bcc` and `refresh` targets are tagged `manual` so that `//...` stays
  buildable for cross-compilation platforms without a prebuilt `bcc` binary.
- `--force` waits up to `BCC_LOCK_TIMEOUT` seconds (default 600) for a running
  refresh and exits 1 on timeout.
