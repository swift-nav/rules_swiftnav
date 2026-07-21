"""Valgrind callgrind profiling macro for Bazel.

Runs a binary under valgrind's callgrind tool, capturing the raw callgrind
output (for KCacheGrind) and a single extracted CPU instruction count.

Unlike a binary-specific profiling macro, the invocation is not hardcoded — the
caller supplies program_args verbatim, so any binary's CLI works. Two runtime
tokens are substituted in program_args by the runner:
    {OUTPUT_DIR}  -> TEST_UNDECLARED_OUTPUTS_DIR (collected by Bazel)
    {TMPDIR}      -> TEST_TMPDIR (scratch, discarded)
Use these to point a binary's output/working directory at a writable location.

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
        timeout = "eternal",
    )
"""

load("@rules_shell//shell:sh_test.bzl", "sh_test")

def swift_add_valgrind_callgrind(
        binary,
        name = None,
        child_silent_after_fork = False,
        trace_children = False,
        program_args = [],
        tags = [],
        data = [],
        **kwargs):
    """Creates a test target that runs a binary under valgrind callgrind.

    Outputs written to TEST_UNDECLARED_OUTPUTS_DIR:
        valgrind-callgrind.<pid>        — raw callgrind output per process
                                          (inspect with KCacheGrind)
        valgrind-callgrind.instructions — single line: total instruction count
                                          summed over all processes

    Args:
        binary: Label of the cc_binary (or swift_cc_test) to run under callgrind.
        name: Name of the new target. Defaults to
            "<binary_target>.valgrind.callgrind" if omitted.
        child_silent_after_fork: Enable --child-silent-after-fork=yes.
        trace_children: Enable --trace-children=yes for spawned processes.
        program_args: Arguments forwarded to the binary. Supports $(location)
            expansion and the {OUTPUT_DIR} / {TMPDIR} runtime tokens.
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

    sh_test(
        name = name,
        srcs = ["@rules_swiftnav//tools/valgrind:valgrind_callgrind_run.sh"],
        args = valgrind_flags + ["$(location {})".format(binary)] + program_args,
        data = data + [binary],
        tags = tags + ["valgrind-callgrind", "manual"],
        **kwargs
    )
