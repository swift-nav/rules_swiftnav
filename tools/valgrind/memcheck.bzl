"""Valgrind memcheck test macros for Bazel.

Provides a Starlark equivalent of CMake's swift_add_valgrind_memcheck macro,
creating per-test valgrind targets with individually configurable options.

Usage:
    load("//tools/valgrind:memcheck.bzl", "swift_add_valgrind_memcheck")

    # name defaults to "my_test.valgrind.memcheck"
    swift_add_valgrind_memcheck(
        binary = ":my_test",
        trace_children = True,
        program_args = ["--gtest_filter=MyTest", "--notimeout"],
        timeout = "long",
    )

    # explicit name
    swift_add_valgrind_memcheck(
        binary = ":my_test",
        name = "my_test_valgrind",
    )
"""

load("@rules_shell//shell:sh_test.bzl", "sh_test")

def swift_add_valgrind_memcheck(
        binary,
        name = None,
        leak_check = None,
        errors_for_leak_kinds = "all",
        show_reachable = False,
        undef_value_errors = False,
        track_origins = True,
        child_silent_after_fork = False,
        trace_children = False,
        skip_tests = False,
        suppressions = [],
        program_args = [],
        tags = [],
        data = [],
        **kwargs):
    """Creates a test target that runs a binary under valgrind memcheck.

    This is the Bazel equivalent of CMake's swift_add_valgrind_memcheck macro.
    A separate sh_test target is created for each call, allowing per-test
    valgrind flag configuration — unlike --run_under which is global.

    Args:
        binary: Label of the swift_cc_test or cc_binary to run under valgrind.
        name: Name of the new valgrind test target. Defaults to
            "<binary_target>.valgrind.memcheck" if omitted.
        leak_check: Leak check mode (e.g. "full", "summary"). Omit to disable.
        errors_for_leak_kinds: Which leak kinds count as errors (e.g. "all",
            "definite,indirect"). Omit to use "all".
        show_reachable: Enable --show-reachable=yes.
        undef_value_errors: Enable --undef-value-errors=yes.
        track_origins: Enable --track-origins=yes.
        child_silent_after_fork: Enable --child-silent-after-fork=yes.
        trace_children: Enable --trace-children=yes.
        skip_tests: When True, valgrind errors do not fail the test (equivalent
            to CMake's GENERATE_JUNIT_REPORT with --skip_tests). Omitting
            --error-exitcode means the test passes as long as the binary exits 0.
            Use for tests with known pre-existing valgrind issues.
        suppressions: List of suppression file labels (e.g.
            ["//tools/valgrind:googletest.supp"]). Each is passed as
            --suppressions=<path> to valgrind.
        program_args: Extra arguments forwarded to the test binary.
        tags: Additional Bazel tags.
        data: Additional data dependencies.
        **kwargs: Forwarded to sh_test (e.g. timeout, size, env).
    """
    if name == None:
        name = binary.split(":")[-1] + ".valgrind.memcheck"

    valgrind_flags = ["--tool=memcheck"]
    if not skip_tests:
        valgrind_flags.append("--error-exitcode=1")
    if leak_check:
        valgrind_flags.append("--leak-check={}".format(leak_check))
    if errors_for_leak_kinds:
        valgrind_flags.append("--errors-for-leak-kinds={}".format(errors_for_leak_kinds))
    if show_reachable:
        valgrind_flags.append("--show-reachable=yes")
    if undef_value_errors:
        valgrind_flags.append("--undef-value-errors=yes")
    if track_origins:
        valgrind_flags.append("--track-origins=yes")
    if child_silent_after_fork:
        valgrind_flags.append("--child-silent-after-fork=yes")
    if trace_children:
        valgrind_flags.append("--trace-children=yes")
    for supp in suppressions:
        valgrind_flags.append("--suppressions=$(location {})".format(supp))

    sh_test(
        name = name,
        srcs = ["@rules_swiftnav//tools/valgrind:valgrind_memcheck_run.sh"],
        args = valgrind_flags + ["$(location {})".format(binary)] + program_args,
        data = data + [binary] + suppressions,
        tags = tags + ["valgrind-memcheck", "manual"],
        **kwargs
    )
