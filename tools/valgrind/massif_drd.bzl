"""Valgrind memory profiling macro for Bazel: massif for heap, DRD for stacks.

Both run in one target because the reported total spans them, and only a single
test can compare that sum against a baseline.

Usage:
    load("@rules_swiftnav//tools/valgrind:massif_drd.bzl",
         "swift_add_valgrind_massif_drd")

    swift_add_valgrind_massif_drd(
        binary = ":my_binary",
        program_args = ["--config", "config.yaml"],
        workdir_data = ["config.yaml", ":input.file"],
        stack_usage = True,
        baseline = "massif_baseline.json",
        tolerance_pct = 5,
        timeout = "eternal",
    )
"""

load(":runner.bzl", "target_label", "valgrind_test")

_REPORT_TOOL = "@rules_swiftnav//tools/valgrind/report:massif_drd_report"

def swift_add_valgrind_massif_drd(
        binary,
        name = None,
        stack_usage = False,
        child_silent_after_fork = False,
        trace_children = False,
        dumps_to_tmpdir = False,
        valgrind_args = [],
        program_args = [],
        workdir_data = [],
        baseline = None,
        tolerance_pct = 5,
        tags = [],
        data = [],
        **kwargs):
    """Creates a test target that runs a binary under valgrind massif.

    Outputs written to TEST_UNDECLARED_OUTPUTS_DIR:
        valgrind-massif.<pid>             — raw output per process, for ms_print
        valgrind-drd.stack_usage.txt      — DRD stack lines, with stack_usage
        valgrind-massif-drd.metrics       — one "key value" line per figure, in MB
        valgrind-massif-drd.report.json   — baseline comparison, with baseline set

    Metric keys, which the baseline file must also carry: memory_heap_mb,
    memory_heap_extra_mb, memory_stack_mb, memory_total_mb.

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
        dumps_to_tmpdir: Write the raw dumps to TEST_TMPDIR instead of the
            collected outputs, for dumps too large to upload on every run. CI
            can still reach them by keeping the directory it passes to
            --test_tmpdir. The report goes to the outputs either way.
        valgrind_args: Extra valgrind flags, e.g. ["--detailed-freq=1"]. Applied
            to the DRD pass too, so massif-only flags break stack_usage.
        program_args: Arguments forwarded to the binary. Supports $(location)
            and the {OUTPUT_DIR}, {TMPDIR} and {RUNFILES} runtime tokens.
        workdir_data: Files to symlink by basename into a working directory the
            binary is run from, for one that names its inputs by bare filename
            or writes into the working directory. A $(location) elsewhere in
            program_args then needs "{RUNFILES}/" in front of it.
        baseline: Json file of expected values, e.g. {"memory_heap_mb": 15.405},
            optionally with a "<key>_max" absolute ceiling beside any of them.
            Setting it turns the target into a regression gate; without it, it
            only profiles.
        tolerance_pct: Percent over baseline before the test fails. The same
            margin under it warns that the baseline is stale.
        tags: Additional Bazel tags.
        data: Additional data dependencies.
        **kwargs: Forwarded to py_test (e.g. timeout, size, env).
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

    runner_flags = []
    if stack_usage:
        runner_flags.append("--stack-usage")
    if dumps_to_tmpdir:
        runner_flags.append("--dumps-to-tmpdir")

    valgrind_test(
        name = name,
        tool = "massif",
        binary = binary,
        runner_flags = runner_flags,
        report = report,
        valgrind_flags = valgrind_flags,
        program_args = program_args,
        workdir_data = workdir_data,
        tags = tags,
        data = data + baseline_data + [_REPORT_TOOL],
        kwargs = kwargs,
    )
