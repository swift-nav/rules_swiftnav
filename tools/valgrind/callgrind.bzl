"""Valgrind callgrind profiling macro for Bazel.

Usage:
    load("@rules_swiftnav//tools/valgrind:callgrind.bzl",
         "swift_add_valgrind_callgrind")

    swift_add_valgrind_callgrind(
        binary = "//replay:run_replay",
        program_args = [
            "--input", "$(location :input.file)",
            "--directory", "{TMPDIR}/output",
        ],
        data = [":input.file"],
        baseline = "callgrind_baseline.json",
        timeout = "eternal",
    )
"""

load(":runner.bzl", "target_label", "valgrind_test")

_REPORT_TOOL = "@rules_swiftnav//tools/valgrind/report:callgrind_report"

def swift_add_valgrind_callgrind(
        binary,
        name = None,
        child_silent_after_fork = False,
        trace_children = False,
        valgrind_args = [],
        program_args = [],
        workdir_data = [],
        baseline = None,
        tolerance_pct = 5,
        tags = [],
        data = [],
        **kwargs):
    """Creates a test target that runs a binary under valgrind callgrind.

    Outputs written to TEST_UNDECLARED_OUTPUTS_DIR:
        valgrind-callgrind.<pid>        — raw output per process, for KCacheGrind
        valgrind-callgrind.instructions — instruction count over all processes
        valgrind-callgrind.report.json  — baseline comparison, with baseline set

    Args:
        binary: Label of the cc_binary (or swift_cc_test) to run under callgrind.
        name: Defaults to "<binary_target>.valgrind.callgrind".
        child_silent_after_fork: Enable --child-silent-after-fork=yes.
        trace_children: Enable --trace-children=yes for spawned processes.
        valgrind_args: Extra valgrind flags, e.g. ["--max-stackframe=16000000"].
        program_args: Arguments forwarded to the binary. Supports $(location)
            and the {OUTPUT_DIR}, {TMPDIR} and {RUNFILES} runtime tokens.
        workdir_data: Files to symlink by basename into a working directory the
            binary is run from, for one that names its inputs by bare filename
            or writes into the working directory. A $(location) elsewhere in
            program_args then needs "{RUNFILES}/" in front of it.
        baseline: Json file of expected values, e.g. {"cpu_instructions": 2803}.
            One file per target, so the memory baselines can join it. Setting it
            turns the target into a regression gate; without it, it only profiles.
        tolerance_pct: Percent over baseline before the test fails. The same
            margin under it warns that the baseline is stale.
        tags: Additional Bazel tags.
        data: Additional data dependencies.
        **kwargs: Forwarded to py_test (e.g. timeout, size, env).
    """
    if name == None:
        name = binary.split(":")[-1] + ".valgrind.callgrind"

    valgrind_flags = []
    if child_silent_after_fork:
        valgrind_flags.append("--child-silent-after-fork=yes")
    if trace_children:
        valgrind_flags.append("--trace-children=yes")
    valgrind_flags += valgrind_args

    report = ["$(location {})".format(_REPORT_TOOL), "--label", target_label(name)]
    baseline_data = []
    if baseline:
        baseline_data = [baseline]
        report += [
            "--baseline",
            "$(location {})".format(baseline),
            # Workspace-relative, for the refresh hint to quote.
            "--baseline-label",
            "$(rootpath {})".format(baseline),
            "--tolerance-pct",
            str(tolerance_pct),
        ]

    valgrind_test(
        name = name,
        tool = "callgrind",
        binary = binary,
        report = report,
        valgrind_flags = valgrind_flags,
        program_args = program_args,
        workdir_data = workdir_data,
        tags = tags,
        data = data + baseline_data + [_REPORT_TOOL],
        kwargs = kwargs,
    )
