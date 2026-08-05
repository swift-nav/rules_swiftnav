"""Runner setup shared by every valgrind macro: memcheck, callgrind and massif."""

load("@rules_python//python:py_test.bzl", "py_test")

_RUNNER = "@rules_swiftnav//tools/valgrind:runner.py"

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
        runner_flags = [],
        report = [],
        valgrind_flags = [],
        program_args = [],
        workdir_data = [],
        tags = [],
        data = [],
        kwargs = {}):
    """Declares the test target every valgrind macro generates.

    Args:
        name: Name of the target.
        tool: Valgrind tool the runner selects, and the tag stem.
        binary: Label of the binary to run under it.
        runner_flags: Flags for the runner itself, before the report tool.
        report: The reporting tool's arguments, its $(location) first. Empty for
            a tool with nothing to measure.
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
            runner_flags +
            workdir_flags +
            report +
            ["--"] +
            valgrind_flags +
            ["$(location {})".format(binary)] +
            program_args
        ),
        data = deps,
        tags = tags + ["valgrind-" + tool, "manual"],
        target_compatible_with = kwargs.pop("target_compatible_with", []) + ["@platforms//os:linux"],
        **kwargs
    )
