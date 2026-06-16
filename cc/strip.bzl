load("@bazel_tools//tools/build_defs/cc:action_names.bzl", "ACTION_NAMES")
load("@bazel_tools//tools/cpp:toolchain_utils.bzl", "find_cpp_toolchain")
load("@rules_cc//cc/common:cc_common.bzl", "cc_common")

def _strip_impl(ctx):
    binary = ctx.file.binary
    out = ctx.actions.declare_file(ctx.attr.name)
    cc_toolchain = find_cpp_toolchain(ctx)

    # Resolve the strip tool through the toolchain's action config rather than the
    # legacy `cc_toolchain.strip_executable` field. Toolchains built on the modern
    # rules_cc API (e.g. the rules_rs hermetic LLVM toolchain) only wire `strip`
    # through the action config and leave `strip_executable` pointing at a path
    # that is never materialized, which fails at execution with "No such file".
    feature_configuration = cc_common.configure_features(
        ctx = ctx,
        cc_toolchain = cc_toolchain,
        requested_features = ctx.features,
        unsupported_features = ctx.disabled_features,
    )
    strip = cc_common.get_tool_for_action(
        feature_configuration = feature_configuration,
        action_name = ACTION_NAMES.strip,
    )

    args = ctx.actions.args()
    args.add("-S")
    args.add("-p")
    args.add("-o")
    args.add(out)
    args.add(binary)
    [args.add(opt) for opt in ctx.attr.stripopts]

    ctx.actions.run(
        outputs = [out],
        inputs = depset([binary], transitive = [cc_toolchain.all_files]),
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
    fragments = ["cpp"],
)
