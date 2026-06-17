load("@bazel_tools//tools/build_defs/cc:action_names.bzl", "ACTION_NAMES")
load("@bazel_tools//tools/cpp:toolchain_utils.bzl", "find_cpp_toolchain")
load("@rules_cc//cc/common:cc_common.bzl", "cc_common")

# llvm-strip rejects these ELF-only options when operating on a Mach-O object
# ("option is not supported for MachO"). They have no symbol-stripping effect
# worth preserving, so drop them on macOS.
_MACHO_UNSUPPORTED_STRIPOPTS = [
    "-p",
    "--preserve-dates",
]

# Translate ELF-only symbol-stripping options to their nearest Mach-O equivalent
# so the same strip() target removes comparable symbols on both platforms. The
# stripping protects shipped symbols, so we keep parity of intent rather than
# silently stripping less on macOS.
_MACHO_STRIPOPT_EQUIVALENTS = {
    # `--strip-unneeded` removes symbols not needed for relocations on ELF; `-x`
    # strips local (internal) symbols, the closest Mach-O equivalent.
    "--strip-unneeded": "-x",
}

def _strip_impl(ctx):
    binary = ctx.file.binary
    out = ctx.actions.declare_file(ctx.attr.name)
    cc_toolchain = find_cpp_toolchain(ctx)
    is_macos = ctx.target_platform_has_constraint(
        ctx.attr._macos[platform_common.ConstraintValueInfo],
    )

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

    # `-p` (preserve dates) is an ELF-only option that llvm-strip rejects for
    # Mach-O. Keep it for ELF targets, drop it on macOS.
    if not is_macos:
        args.add("-p")

    args.add("-o")
    args.add(out)
    args.add(binary)

    for opt in ctx.attr.stripopts:
        if is_macos:
            equivalent = _MACHO_STRIPOPT_EQUIVALENTS.get(opt)
            if equivalent:
                args.add(equivalent)
                continue
            if opt in _MACHO_UNSUPPORTED_STRIPOPTS:
                continue
        args.add(opt)

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
        "_macos": attr.label(
            default = "@platforms//os:macos",
        ),
    },
    executable = True,
    toolchains = ["@bazel_tools//tools/cpp:toolchain_type"],
    fragments = ["cpp"],
)
