load("@bazel_tools//tools/cpp:toolchain_utils.bzl", "find_cpp_toolchain")

def _get_linker_inputs(deps):
    lib_sets = []
    for dep in deps:
        lib_sets.append(dep[CcInfo].linking_context.linker_inputs)
    input_depset = depset(transitive = lib_sets)
    return input_depset.to_list()

def _get_static_libaries(ctx, lib):
    # This statement checks if path contains "+" and replaces it with "_".
    # This workaround is needed for the older version of archiver (2.31.1), which doesn't accept paths with "+".
    # Moreover, the archiver MRI script has hickups with paths containing "~".
    # This is unfortunate, because "~" is part of the folder structure when using bzl_mod.
    if lib.path.find("+") != -1 or lib.path.find("~") != -1:
        new_lib = ctx.actions.declare_file(lib.path.replace("+", "_").replace("~", "_"))
        ctx.actions.run_shell(
            command = "cp {} {}".format(lib.path, new_lib.path),
            inputs = [lib],
            outputs = [new_lib],
        )
        return new_lib
    return lib

def _get_libs(ctx, linker_inputs):
    libs = []
    for inp in linker_inputs:
        for lib in inp.libraries:
            if lib.pic_static_library:
                libs.append(_get_static_libaries(ctx, lib.pic_static_library))
            elif lib.static_library:
                libs.append(_get_static_libaries(ctx, lib.static_library))
    return libs

def _get_commands(output_lib, libs):
    commands = ["create {}".format(output_lib.path)]
    for lib in libs:
        commands.append("addlib {}".format(lib.path))
    commands.append("save")
    commands.append("end")
    return commands

def _run_ar_mri(ctx, cc_toolchain, script_file, output_lib, libs):
    ctx.actions.run_shell(
        command = "{} -M < {}".format(cc_toolchain.ar_executable, script_file.path),
        inputs = [script_file] + libs + cc_toolchain.all_files.to_list(),
        outputs = [output_lib],
        mnemonic = "ArMerge",
        progress_message = "Merging static library {}".format(output_lib.path),
    )

def _run_ar_bsd(ctx, cc_toolchain, output_lib, libs):
    # macOS uses libtool instead of ar for creating static libraries
    args = ctx.actions.args()
    if cc_toolchain.ar_executable.endswith("libtool"):
        args.add("-static")
        args.add("-o")
        args.add(output_lib.path)
        args.add_all(libs)
    else:
        # BSD ar doesn't support MRI scripts, so we create the archive manually
        args.add("rc")  # replace and create
        args.add(output_lib.path)
        args.add_all(libs)

    ctx.actions.run(
        executable = cc_toolchain.ar_executable,
        arguments = [args],
        inputs = libs + cc_toolchain.all_files.to_list(),
        outputs = [output_lib],
        mnemonic = "ArMerge",
        progress_message = "Merging static library {}".format(output_lib.path),
    )

def _cc_static_library_impl(ctx):
    output_lib = ctx.actions.declare_file("{}.a".format(ctx.attr.name))

    cc_toolchain = find_cpp_toolchain(ctx)

    linker_inputs = _get_linker_inputs(ctx.attr.deps)

    libs = _get_libs(ctx, linker_inputs)

    # Use different ar strategies based on platform
    # GNU ar supports MRI scripts, BSD ar (macOS) does not
    if ctx.target_platform_has_constraint(ctx.attr._macos_constraint[platform_common.ConstraintValueInfo]):
        _run_ar_bsd(ctx, cc_toolchain, output_lib, libs)
    else:
        script_file = ctx.actions.declare_file("{}.mri".format(ctx.attr.name))
        ctx.actions.write(
            output = script_file,
            content = "\n".join(_get_commands(output_lib, libs)) + "\n",
        )
        _run_ar_mri(ctx, cc_toolchain, script_file, output_lib, libs)

    cc_infos = [dep[CcInfo] for dep in ctx.attr.deps if CcInfo in dep]
    merged_cc_info = cc_common.merge_cc_infos(cc_infos = cc_infos)

    library_to_link = cc_common.create_library_to_link(
        actions = ctx.actions,
        static_library = output_lib,
    )
    linker_input = cc_common.create_linker_input(
        owner = ctx.label,
        libraries = depset([library_to_link]),
    )
    linking_context = cc_common.create_linking_context(
        linker_inputs = depset([linker_input]),
    )

    final_cc_info = CcInfo(
        compilation_context = merged_cc_info.compilation_context,
        linking_context = cc_common.merge_linking_contexts(
            linking_contexts = [merged_cc_info.linking_context, linking_context],
        ),
    )

    return [
        DefaultInfo(files = depset([output_lib])),
        final_cc_info,
    ]

cc_static_library = rule(
    implementation = _cc_static_library_impl,
    attrs = {
        "deps": attr.label_list(),
        "_cc_toolchain": attr.label(
            default = "@bazel_tools//tools/cpp:current_cc_toolchain",
        ),
        "_macos_constraint": attr.label(
            default = "@platforms//os:macos",
        ),
    },
    toolchains = ["@bazel_tools//tools/cpp:toolchain_type"],
    incompatible_use_toolchain_transition = True,
)
