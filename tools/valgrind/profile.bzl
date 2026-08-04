"""The profiling half of the valgrind macros: a build action, not a test.

Running a binary under valgrind and gating the result against a baseline are two
separate nodes of the action graph, so that editing a baseline re-runs only the
comparison. The expensive half has to be a build action because a test's result
cannot be an input to another target.

The action's only output is the measurement json. The raw dumps go to scratch and
are discarded: a callgrind dump runs to tens of megabytes and would otherwise be
written into every cache entry. To keep them for ms_print or KCacheGrind, name a
directory for the runner to write them to::

    bazel build --action_env=VALGRIND_DUMP_DIR=/tmp/dumps //pkg:target.profile
"""

_MEASURE_TOOLS = {
    "callgrind": "@rules_swiftnav//tools/valgrind/report:callgrind_measure",
    "massif": "@rules_swiftnav//tools/valgrind/report:massif_drd_measure",
}

def _valgrind_profile_impl(ctx):
    measurement = ctx.actions.declare_file(ctx.label.name + ".measurement.json")

    targets = ctx.attr.data + ctx.attr.workdir_data + [ctx.attr.binary]

    def expand(args):
        return [ctx.expand_location(arg, targets = targets) for arg in args]

    args = ctx.actions.args()
    args.add("--tool", ctx.attr.tool)
    if ctx.attr.stack_usage:
        args.add("--stack-usage")
    for f in ctx.files.workdir_data:
        args.add("--workdir-data", f)
    for name, value in ctx.attr.binary_env.items():
        args.add("--env", "{}={}".format(name, value))

    # The measuring tool's own half, which the runner invokes once valgrind is
    # done. Its path is passed rather than resolved there because the runner has
    # no way to find a sibling tool in the action's inputs.
    args.add(ctx.executable.measure_tool)
    args.add("--measurement-out", measurement)
    args.add("--label", ctx.attr.label)

    args.add("--")
    args.add_all(expand(ctx.attr.valgrind_flags))
    args.add(ctx.executable.binary)
    args.add_all(expand(ctx.attr.program_args))

    ctx.actions.run(
        outputs = [measurement],
        inputs = depset(ctx.files.data + ctx.files.workdir_data),
        tools = [
            ctx.attr.binary[DefaultInfo].files_to_run,
            ctx.attr.measure_tool[DefaultInfo].files_to_run,
        ],
        executable = ctx.executable._runner,
        arguments = [args],
        mnemonic = "ValgrindProfile",
        progress_message = "Profiling %s under valgrind %s" % (
            ctx.attr.binary.label,
            ctx.attr.tool,
        ),
        # valgrind is a system binary off PATH, and needs the machine the numbers
        # will be compared against, so the action is local and its result is not
        # shared. "local" already implies no sandbox and no remote execution.
        use_default_shell_env = True,
        execution_requirements = {
            "local": "1",
            "no-remote-cache": "1",
        },
    )

    return [DefaultInfo(files = depset([measurement]))]

valgrind_profile = rule(
    implementation = _valgrind_profile_impl,
    doc = "Runs a binary under valgrind and measures it, for a gate test to compare.",
    attrs = {
        "binary": attr.label(
            mandatory = True,
            executable = True,
            # Target, not exec: the artifact being profiled is the one that ships,
            # which under cross-compilation is a different binary from the exec
            # one. So the exec platform has to be able to run it, which is what
            # target_compatible_with on the generated targets asserts.
            cfg = "target",
            doc = "The binary to run under valgrind.",
        ),
        "tool": attr.string(
            mandatory = True,
            values = sorted(_MEASURE_TOOLS),
            doc = "Valgrind tool to run under.",
        ),
        "label": attr.string(
            mandatory = True,
            doc = "Name of the profiled target, recorded in the measurement.",
        ),
        "measure_tool": attr.label(
            mandatory = True,
            executable = True,
            cfg = "exec",
            doc = "Tool that turns the tool's dumps into the measurement json.",
        ),
        "stack_usage": attr.bool(
            default = False,
            doc = "massif: measure thread stacks in a second DRD pass.",
        ),
        "valgrind_flags": attr.string_list(
            doc = "Flags passed to valgrind before the binary. $(location) expanded.",
        ),
        "program_args": attr.string_list(
            doc = "Arguments forwarded to the binary. $(location) expanded.",
        ),
        "workdir_data": attr.label_list(
            allow_files = True,
            doc = "Files symlinked by basename into a working directory to run the binary from.",
        ),
        "data": attr.label_list(
            allow_files = True,
            doc = "Additional files the binary needs at run time.",
        ),
        "binary_env": attr.string_dict(
            doc = "Environment variables for the profiled binary.",
        ),
        "_runner": attr.label(
            default = "@rules_swiftnav//tools/valgrind:runner",
            executable = True,
            cfg = "exec",
        ),
    },
)

def measure_tool(tool):
    """Returns the label of the tool that measures the given valgrind tool's dumps.

    Args:
        tool: Valgrind tool name, "callgrind" or "massif".
    """
    return _MEASURE_TOOLS[tool]
