"""Valgrind memcheck test macros for Bazel.

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

load(":runner.bzl", "valgrind_test")

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
        valgrind_args = [],
        program_args = [],
        workdir_data = [],
        tags = [],
        data = [],
        **kwargs):
    """Creates a test target that runs a binary under valgrind memcheck.

    One target per call, so valgrind flags are configurable per test — unlike
    --run_under, which is global. The XML report is written to
    TEST_UNDECLARED_OUTPUTS_DIR as valgrind-memcheck.<pid>.xml.

    Args:
        binary: Label of the swift_cc_test or cc_binary to run under valgrind.
        name: Defaults to "<binary_target>.valgrind.memcheck".
        leak_check: Leak check mode (e.g. "full", "summary"). Omit to disable.
        errors_for_leak_kinds: Which leak kinds count as errors (e.g. "all",
            "definite,indirect").
        show_reachable: Enable --show-reachable=yes.
        undef_value_errors: Enable --undef-value-errors=yes.
        track_origins: Enable --track-origins=yes.
        child_silent_after_fork: Enable --child-silent-after-fork=yes.
        trace_children: Enable --trace-children=yes.
        skip_tests: Drop --error-exitcode, so valgrind errors do not fail the
            test and only the binary's own exit code counts. For tests with
            known pre-existing valgrind issues. CMake calls this
            GENERATE_JUNIT_REPORT with --skip_tests.
        suppressions: Suppression file labels, each passed as
            --suppressions=<path>.
        valgrind_args: Extra valgrind flags, e.g. ["--max-stackframe=16000000"].
        program_args: Arguments forwarded to the binary. Supports $(location)
            and the {OUTPUT_DIR}, {TMPDIR} and {RUNFILES} runtime tokens.
        workdir_data: Files to symlink by basename into a working directory the
            binary is run from, for one that names its inputs by bare filename
            or writes into the working directory. A $(location) elsewhere in
            program_args then needs "{RUNFILES}/" in front of it.
        tags: Additional Bazel tags.
        data: Additional data dependencies.
        **kwargs: Forwarded to py_test (e.g. timeout, size, env).
    """
    if name == None:
        name = binary.split(":")[-1] + ".valgrind.memcheck"

    valgrind_flags = []
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
        # Absolute, so a working directory cannot move it out from under valgrind.
        valgrind_flags.append("--suppressions={{RUNFILES}}/$(location {})".format(supp))
    valgrind_flags += valgrind_args

    valgrind_test(
        name = name,
        tool = "memcheck",
        binary = binary,
        valgrind_flags = valgrind_flags,
        program_args = program_args,
        workdir_data = workdir_data,
        tags = tags,
        data = data + suppressions,
        kwargs = kwargs,
    )
