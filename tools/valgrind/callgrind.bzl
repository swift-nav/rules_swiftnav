"""Valgrind callgrind profiling macro for Bazel.

Runs a binary under valgrind's callgrind tool, capturing the raw callgrind
output (for KCacheGrind) and the extracted CPU instruction count.

The invocation is not hardcoded — the caller supplies program_args verbatim, so
any binary's CLI works. The runner substitutes two tokens in them:
    {OUTPUT_DIR}  -> TEST_UNDECLARED_OUTPUTS_DIR (collected by Bazel)
    {TMPDIR}      -> TEST_TMPDIR (scratch, discarded)

Passing instructions_baseline turns the target into a runtime regression gate:
`bazel test` fails once the count exceeds the checked-in baseline by more than
tolerance_pct, so CI needs no logic of its own.

Usage:
    load("@rules_swiftnav//tools/valgrind:callgrind.bzl",
         "swift_add_valgrind_callgrind")

    swift_add_valgrind_callgrind(
        binary = "//replay:run_replay",
        program_args = [
            "--input", "$(location :input.file)",
            "--config", "$(location config.yaml)",
            "--directory", "{TMPDIR}/output",
        ],
        data = [":input.file", "config.yaml"],
        instructions_baseline = "callgrind_baseline.txt",
        tolerance_pct = 5,
        timeout = "eternal",
    )
"""

load("@rules_shell//shell:sh_test.bzl", "sh_test")

_REPORT_TOOL = "@rules_swiftnav//tools/valgrind:callgrind_report"

def swift_add_valgrind_callgrind(
        binary,
        name = None,
        child_silent_after_fork = False,
        trace_children = False,
        valgrind_args = [],
        program_args = [],
        instructions_baseline = None,
        tolerance_pct = 5,
        tags = [],
        data = [],
        **kwargs):
    """Creates a test target that runs a binary under valgrind callgrind.

    Outputs written to TEST_UNDECLARED_OUTPUTS_DIR:
        valgrind-callgrind.<pid>        — raw callgrind output per process
                                          (inspect with KCacheGrind)
        valgrind-callgrind.instructions — single line: total instruction count
                                          summed over all processes
        valgrind-callgrind.report.json  — baseline comparison, machine readable
        valgrind-callgrind.report.md    — baseline comparison as a markdown
                                          table, ready to post as a PR comment
    The last two are only produced when instructions_baseline is set.

    Args:
        binary: Label of the cc_binary (or swift_cc_test) to run under callgrind.
        name: Name of the new target. Defaults to
            "<binary_target>.valgrind.callgrind" if omitted.
        child_silent_after_fork: Enable --child-silent-after-fork=yes.
        trace_children: Enable --trace-children=yes for spawned processes.
        valgrind_args: Extra flags passed to valgrind before the binary, e.g.
            ["--max-stackframe=16000000"] for binaries with large stack frames.
        program_args: Arguments forwarded to the binary. Supports $(location)
            expansion and the {OUTPUT_DIR} / {TMPDIR} runtime tokens.
        instructions_baseline: Label of a text file holding the expected
            instruction count as a single integer — the same format as the
            generated valgrind-callgrind.instructions file, so refreshing a
            baseline is a copy of the one over the other. When set, the test
            fails on a regression larger than tolerance_pct. When omitted the
            target only profiles and never fails on the count.
        tolerance_pct: Percentage the measured instruction count may exceed the
            baseline before the test fails. Also the threshold below which an
            improvement is reported as a stale baseline (a warning, not a
            failure). Ignored without instructions_baseline.
        tags: Additional Bazel tags.
        data: Additional data dependencies (e.g. inputs referenced by args).
        **kwargs: Forwarded to sh_test (e.g. timeout, size, env).
    """
    if name == None:
        name = binary.split(":")[-1] + ".valgrind.callgrind"

    valgrind_flags = []
    if child_silent_after_fork:
        valgrind_flags.append("--child-silent-after-fork=yes")
    if trace_children:
        valgrind_flags.append("--trace-children=yes")
    valgrind_flags += valgrind_args

    # The label identifies this target's row when the reports of several
    # callgrind targets are merged into one CI comment.
    report_args = ["--label", name]
    baseline_data = []
    if instructions_baseline:
        baseline_data = [instructions_baseline]
        report_args += [
            "--instructions-baseline",
            "$(location {})".format(instructions_baseline),
            # The workspace-relative path is what a developer needs to see when
            # told how to refresh the baseline.
            "--baseline-label",
            "$(rootpath {})".format(instructions_baseline),
            "--tolerance-pct",
            str(tolerance_pct),
        ]

    sh_test(
        name = name,
        srcs = ["@rules_swiftnav//tools/valgrind:valgrind_callgrind_run.sh"],
        args = (
            ["$(location {})".format(_REPORT_TOOL)] +
            report_args +
            ["--"] +
            valgrind_flags +
            ["$(location {})".format(binary)] +
            program_args
        ),
        data = data + baseline_data + [binary, _REPORT_TOOL],
        tags = tags + ["valgrind-callgrind", "manual"],
        **kwargs
    )
