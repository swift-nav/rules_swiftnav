load("@bazel_tools//tools/cpp:toolchain_utils.bzl", "find_cpp_toolchain")

def _check_format(ctx, exe, config, infile, clang_format_bin):
    output = ctx.actions.declare_file(infile.basename + ".clang-format.txt")

    args = ctx.actions.args()

    args.add("check_file")
    args.add(clang_format_bin.path)
    args.add(infile.path)
    args.add(output.path)

    ctx.actions.run(
        inputs = [clang_format_bin, infile, config],
        outputs = [output],
        executable = exe,
        arguments = [args],
        mnemonic = "ClangFormat",
        progress_message = "Check clang-format on {}".format(infile.short_path),
    )
    return output

def _extract_files(ctx):
    files = []
    if hasattr(ctx.rule.attr, "srcs"):
        for src in ctx.rule.attr.srcs:
            files += [src for src in src.files.to_list() if src.is_source]

    if hasattr(ctx.rule.attr, "hdrs"):
        for hdr in ctx.rule.attr.hdrs:
            files += [hdr for hdr in hdr.files.to_list() if hdr.is_source]

    return files

def _clang_format_check_aspect_impl(target, ctx):
    # if not a C/C++ target, we are not interested
    if not CcInfo in target:
        return []

    exe = ctx.attr._clang_format.files_to_run
    config = ctx.attr._clang_format_config.files.to_list()[0]
    clang_format_bin = ctx.attr._clang_format_bin.files.to_list()[0]
    files = _extract_files(ctx)

    outputs = []
    for file in files:
        if file.basename.endswith((".c", ".h", ".cpp", ".cc", ".hpp")):
            outputs.append(_check_format(ctx, exe, config, file, clang_format_bin))

    return [
        OutputGroupInfo(report = depset(direct = outputs)),
    ]

clang_format_check_aspect = aspect(
    implementation = _clang_format_check_aspect_impl,
    fragments = ["cpp"],
    attrs = {
        "_clang_format": attr.label(default = Label("//bazel/clang_format:clang_format")),
        "_clang_format_config": attr.label(default = Label("//:clang_format_config")),
        "_clang_format_bin": attr.label(default = Label("//bazel/clang_format:clang_format_bin")),
    },
    toolchains = ["@bazel_tools//tools/cpp:toolchain_type"],
)
