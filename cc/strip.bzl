load("@bazel_tools//tools/cpp:toolchain_utils.bzl", "find_cpp_toolchain")

def _strip_impl(ctx):
    binary = ctx.file.binary
    out = ctx.actions.declare_file(ctx.attr.name)
    cc_toolchain = find_cpp_toolchain(ctx)
    strip = cc_toolchain.strip_executable

    args = ctx.actions.args()
    args.add("-S")
    args.add("-p")
    args.add("-o")
    args.add(out)
    args.add(binary)
    [args.add(opt) for opt in ctx.attr.stripopts]

    ctx.actions.run(
        outputs = [out],
        inputs = [binary] + cc_toolchain.all_files.to_list(),
        executable = strip,
        arguments = [args],
        mnemonic = "Strip",
        progress_message = "Stripping {}".format(binary.basename),
    )

    return DefaultInfo(executable = out)

strip = rule(
    implementation = _strip_impl,
    attrs = {
        "binary": attr.label(allow_single_file = True),
        "stripopts": attr.string_list(),
        "_cc_toolchain": attr.label(
            default = "@bazel_tools//tools/cpp:current_cc_toolchain",
        ),
    },
    executable = True,
    toolchains = ["@bazel_tools//tools/cpp:toolchain_type"],
)
