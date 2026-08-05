"""Runner setup shared by every valgrind macro: memcheck, callgrind and massif."""

load("@rules_python//python:py_test.bzl", "py_test")
load(":profile.bzl", "measure_tool", "valgrind_profile")

_RUNNER = "@rules_swiftnav//tools/valgrind:runner.py"
_COMPARE = "@rules_swiftnav//tools/valgrind/report:compare.py"
_METRICS = "@rules_swiftnav//tools/valgrind/report:metrics"

def target_label(name):
    """Returns the target's full label, for reports read outside its package.

    Args:
        name: Name of the target.
    """
    return "//{}:{}".format(native.package_name(), name)

def valgrind_test(
        name,
        tool,
        binary,
        valgrind_flags = [],
        program_args = [],
        workdir_data = [],
        tags = [],
        data = [],
        kwargs = {}):
    """Declares one test that runs a binary under valgrind, verdict and all.

    For a tool with nothing to measure — memcheck, where valgrind's own exit code
    is the answer. A tool that measures splits in two instead; see valgrind_gate.

    Args:
        name: Name of the target.
        tool: Valgrind tool the runner selects, and the tag stem.
        binary: Label of the binary to run under it.
        valgrind_flags: Flags passed to valgrind before the binary.
        program_args: Arguments forwarded to the binary.
        workdir_data: Labels to place in the binary's working directory.
        tags: Additional Bazel tags.
        data: Additional data dependencies.
        kwargs: The macro's **kwargs, forwarded to py_test.
    """
    workdir_flags = []
    for f in workdir_data:
        workdir_flags += ["--workdir-data", "$(location {})".format(f)]

    # A label can legitimately be a data dependency, a workdir file and the
    # binary at once, and Bazel rejects a repeated label in an attribute.
    # Resolved first, so the two spellings of one target compare equal.
    deps = []
    for label in data + workdir_data + [binary]:
        resolved = native.package_relative_label(label)
        if resolved not in deps:
            deps.append(resolved)

    py_test(
        name = name,
        srcs = [_RUNNER],
        main = _RUNNER,
        args = (
            ["--tool", tool] +
            workdir_flags +
            ["--"] +
            valgrind_flags +
            ["$(location {})".format(binary)] +
            program_args
        ),
        data = deps,
        tags = tags + ["valgrind", "valgrind-" + tool, "manual"],
        target_compatible_with = kwargs.pop("target_compatible_with", []) + ["@platforms//os:linux"],
        **kwargs
    )

def valgrind_gate(
        name,
        tool,
        binary,
        report_name,
        stack_usage = False,
        valgrind_flags = [],
        program_args = [],
        workdir_data = [],
        baseline = None,
        tolerance_pct = 5,
        binary_env = {},
        tags = [],
        data = [],
        kwargs = {}):
    """Declares the two targets a measuring valgrind macro generates.

    The profiling half is a build action named "<name>.profile"; the gate that
    compares its measurement against the baseline is the test named "<name>",
    which is the target a user runs. Editing the baseline re-runs only the test.

    Args:
        name: Name of the gate test.
        tool: Valgrind tool the runner selects, and the tag stem.
        binary: Label of the binary to run under it.
        report_name: Filename to write the comparison to in the test's outputs.
        stack_usage: massif: measure thread stacks in a second DRD pass.
        valgrind_flags: Flags passed to valgrind before the binary.
        program_args: Arguments forwarded to the binary.
        workdir_data: Labels to place in the binary's working directory.
        baseline: Json file of expected values, or None to only profile.
        tolerance_pct: Percent over baseline before the test fails.
        binary_env: Environment variables for the profiled binary.
        tags: Additional Bazel tags.
        data: Additional data dependencies.
        kwargs: The macro's **kwargs, forwarded to py_test.
    """
    profile = name + ".profile"
    compatible = kwargs.pop("target_compatible_with", []) + ["@platforms//os:linux"]
    visibility = kwargs.get("visibility", None)

    valgrind_profile(
        name = profile,
        tool = tool,
        label = target_label(name),
        binary = binary,
        measure_tool = measure_tool(tool),
        stack_usage = stack_usage,
        valgrind_flags = valgrind_flags,
        program_args = program_args,
        workdir_data = workdir_data,
        data = data,
        binary_env = binary_env,
        # manual because a wildcard build must not start an unbounded valgrind
        # pass; the gate test pulls it in as a dependency when asked for.
        tags = tags + ["valgrind", "valgrind-" + tool, "manual"],
        target_compatible_with = compatible,
        testonly = True,
        visibility = visibility,
    )

    baseline_args = []
    baseline_data = []
    if baseline:
        baseline_data = [baseline]
        baseline_args = [
            "--baseline",
            "$(location {})".format(baseline),
            # Workspace-relative, for the refresh hint to quote.
            "--baseline-label",
            "$(rootpath {})".format(baseline),
            "--tolerance-pct",
            str(tolerance_pct),
        ]

    py_test(
        name = name,
        srcs = [_COMPARE],
        main = _COMPARE,
        args = [
            "--measurement",
            "$(location :{})".format(profile),
            "--report-name",
            report_name,
        ] + baseline_args,
        data = [":" + profile] + baseline_data,
        deps = [_METRICS],
        tags = tags + ["valgrind-" + tool, "manual"],
        # Comparing two json files, however long the profiling took.
        timeout = kwargs.pop("timeout", "short"),
        size = kwargs.pop("size", "small"),
        target_compatible_with = compatible,
        **kwargs
    )
