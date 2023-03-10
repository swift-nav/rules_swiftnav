load("@bazel_tools//tools/cpp:toolchain_utils.bzl", "find_cpp_toolchain")

def _get_linker_inputs(deps):
    lib_sets = []
    for dep in deps:
        lib_sets.append(dep[CcInfo].linking_context.linker_inputs)
    input_depset = depset(transitive = lib_sets)
    return input_depset.to_list()

def _get_libs(linker_inputs):
    libs = []
    for inp in linker_inputs:
        for lib in inp.libraries:
            if lib.pic_static_library:
                libs.append(lib.pic_static_library)
            elif lib.static_library:
                libs.append(lib.static_library)
    return libs

def _get_commands(output_lib, libs):
    commands = ["create {}".format(output_lib.path)]
    for lib in libs:
        commands.append("addlib {}".format(lib.path))
    commands.append("save")
    commands.append("end")
    return commands

def _cc_static_library_impl(ctx):
    output_lib = ctx.actions.declare_file("{}.a".format(ctx.attr.name))

    cc_toolchain = find_cpp_toolchain(ctx)

    linker_inputs = _get_linker_inputs(ctx.attr.deps)

    libs = _get_libs(linker_inputs)

    script_file = ctx.actions.declare_file("{}.mri".format(ctx.attr.name))
    ctx.actions.write(
        output = script_file,
        content = "\n".join(_get_commands(output_lib, libs)) + "\n",
    )

    ctx.actions.run_shell(
        command = "{} -M < {}".format(cc_toolchain.ar_executable, script_file.path),
        inputs = [script_file] + libs + cc_toolchain.all_files.to_list(),
        outputs = [output_lib],
        mnemonic = "ArMerge",
        progress_message = "Merging static library {}".format(output_lib.path),
    )
    return [
        DefaultInfo(files = depset([output_lib])),
    ]

cc_static_library = rule(
    implementation = _cc_static_library_impl,
    attrs = {
        "deps": attr.label_list(),
        "_cc_toolchain": attr.label(
            default = "@bazel_tools//tools/cpp:current_cc_toolchain",
        ),
    },
    toolchains = ["@bazel_tools//tools/cpp:toolchain_type"],
    incompatible_use_toolchain_transition = True,
)
