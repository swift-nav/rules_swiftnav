"""Valgrind memory profiling macro for Bazel: massif for heap, DRD for stacks.

Both run in one target because the reported total spans them, and only a single
test can compare that sum against a baseline.

Usage:
    load("@rules_swiftnav//tools/valgrind:massif_drd.bzl",
         "swift_add_valgrind_massif")

    swift_add_valgrind_massif(
        binary = ":my_binary",
        program_args = ["--config", "config.yaml"],
        workdir_data = ["config.yaml", ":input.file"],
        stack_usage = True,
        baseline = "massif_baseline.json",
        tolerance_pct = 5,
    )
"""

load(":runner.bzl", "valgrind_gate")

_REPORT_NAME = "valgrind-massif-drd.report.json"

def swift_add_valgrind_massif(
        binary,
        name = None,
        stack_usage = False,
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
    """Creates a test target that gates a binary's peak memory.

    Two targets: "<name>.profile" runs the binary under massif (and DRD) and
    measures it, and "<name>" is the test that compares those measurements
    against the baseline. They are separate so that editing the baseline re-runs
    only the comparison rather than massif.

    Outputs:
        <name>.profile.measurement.json  in bazel-bin, the measured figures
        valgrind-massif-drd.report.json  in the test's undeclared outputs, the
                                         baseline comparison, with baseline set

    Metric keys, which the baseline file must also carry: memory_heap_mb,
    memory_heap_extra_mb, memory_stack_mb, memory_total_mb.

    The raw massif dumps are discarded. To read one with ms_print, name a
    directory to keep them in:

        bazel build --action_env=VALGRIND_DUMP_DIR=/tmp/dumps \
            //pkg:<name>.profile

    Args:
        binary: Label of the cc_binary (or swift_cc_test) to run under massif.
        name: Defaults to "<binary_target>.valgrind.massif_drd" with
            stack_usage, else "<binary_target>.valgrind.massif".
        stack_usage: Measure thread stacks in a second DRD pass, roughly
            doubling the runtime. Without it the figure is massif's own, which
            is zero unless --stacks=yes was passed in valgrind_args.
            The pass runs the binary a second time with the same arguments and
            working directory, so anything it wrote the first time is still
            there. A binary that refuses to overwrite its own output needs to be
            pointed at {TMPDIR} or given a --overwrite flag of its own.
        child_silent_after_fork: Enable --child-silent-after-fork=yes.
        trace_children: Enable --trace-children=yes. Each process writes its own
            dump, and the peak is the largest snapshot across all of them.
        valgrind_args: Extra valgrind flags, e.g. ["--detailed-freq=1"]. Applied
            to the DRD pass too, so massif-only flags break stack_usage.
        program_args: Arguments forwarded to the binary. Supports $(location)
            and the {OUTPUT_DIR}, {TMPDIR} and {RUNFILES} runtime tokens.
            {OUTPUT_DIR} is scratch here and does not survive the run.
        workdir_data: Files to symlink by basename into a working directory the
            binary is run from, for one that names its inputs by bare filename
            or writes into the working directory. A $(location) elsewhere in
            program_args then needs "{RUNFILES}/" in front of it.
        baseline: Json file of expected values, e.g. {"memory_heap_mb": 15.405},
            optionally with a "<key>_max" absolute ceiling beside any of them.
            Setting it turns the target into a regression gate; without it, it
            only profiles. Keep it out of the binary's data, or editing it
            profiles again.
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
        suffix = ".valgrind.massif_drd" if stack_usage else ".valgrind.massif"
        name = binary.split(":")[-1] + suffix

    valgrind_flags = []
    if child_silent_after_fork:
        valgrind_flags.append("--child-silent-after-fork=yes")
    if trace_children:
        valgrind_flags.append("--trace-children=yes")
    valgrind_flags += valgrind_args

    valgrind_gate(
        name = name,
        tool = "massif",
        binary = binary,
        report_name = _REPORT_NAME,
        stack_usage = stack_usage,
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
