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
    )
"""

load(":runner.bzl", "valgrind_gate")

_REPORT_NAME = "valgrind-callgrind.report.json"

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
        binary_env = {},
        tags = [],
        data = [],
        **kwargs):
    """Creates a test target that gates a binary's instruction count.

    Two targets: "<name>.profile" runs the binary under callgrind and measures
    it, and "<name>" is the test that compares that measurement against the
    baseline. They are separate so that editing the baseline re-runs only the
    comparison rather than callgrind.

    Outputs:
        <name>.profile.measurement.json  in bazel-bin, the measured count
        valgrind-callgrind.report.json   in the test's undeclared outputs, the
                                         baseline comparison, with baseline set

    The raw callgrind dumps are discarded, being far too large to keep on every
    run. To open one in KCacheGrind, name a directory to keep them in:

        bazel build --action_env=VALGRIND_DUMP_DIR=/tmp/dumps \
            //pkg:<name>.profile

    Args:
        binary: Label of the cc_binary (or swift_cc_test) to run under callgrind.
        name: Defaults to "<binary_target>.valgrind.callgrind".
        child_silent_after_fork: Enable --child-silent-after-fork=yes.
        trace_children: Enable --trace-children=yes for spawned processes.
        valgrind_args: Extra valgrind flags, e.g. ["--max-stackframe=16000000"].
        program_args: Arguments forwarded to the binary. Supports $(location)
            and the {OUTPUT_DIR}, {TMPDIR} and {RUNFILES} runtime tokens.
            {OUTPUT_DIR} is scratch here and does not survive the run.
        workdir_data: Files to symlink by basename into a working directory the
            binary is run from, for one that names its inputs by bare filename
            or writes into the working directory. A $(location) elsewhere in
            program_args then needs "{RUNFILES}/" in front of it.
        baseline: Json file of expected values, e.g. {"cpu_instructions": 2803},
            optionally with a "<key>_max" absolute ceiling beside it. One file
            per target, so the memory baselines can join it. Setting it turns
            the target into a regression gate; without it, it only profiles.
            Keep it out of the binary's data, or editing it profiles again.
        tolerance_pct: Percent over baseline before the test fails. The same
            margin under it warns that the baseline is stale.
        binary_env: Environment variables for the profiled binary. Use this
            rather than env, which now configures the comparison test.
        tags: Additional Bazel tags.
        data: Additional data dependencies.
        **kwargs: Forwarded to the comparison test. timeout and size no longer
            bound the profiling, which is a build action and unbounded.
    """
    if name == None:
        name = binary.split(":")[-1] + ".valgrind.callgrind"

    valgrind_flags = []
    if child_silent_after_fork:
        valgrind_flags.append("--child-silent-after-fork=yes")
    if trace_children:
        valgrind_flags.append("--trace-children=yes")
    valgrind_flags += valgrind_args

    valgrind_gate(
        name = name,
        tool = "callgrind",
        binary = binary,
        report_name = _REPORT_NAME,
        valgrind_flags = valgrind_flags,
        program_args = program_args,
        workdir_data = workdir_data,
        baseline = baseline,
        tolerance_pct = tolerance_pct,
        binary_env = binary_env,
        tags = tags,
        data = data,
        kwargs = kwargs,
    )
