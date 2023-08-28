load("@bazel_tools//tools/cpp:toolchain_utils.bzl", "find_cpp_toolchain")
load("//cc:defs.bzl", "BINARY", "LIBRARY")
load("//cc_files:get_cc_files.bzl", "get_cc_srcs")
load("@bazel_tools//tools/build_defs/cc:action_names.bzl", "ACTION_NAMES")

def _flatten(input_list):
    return [item for sublist in input_list for item in sublist]

def _run_tidy(ctx, wrapper, exe, additional_deps, config, flags, compilation_contexts, infile, discriminator):
    inputs = depset(direct = [infile, config] + additional_deps.files.to_list() + ([exe.files_to_run.executable] if exe.files_to_run.executable else []), transitive = [compilation_context.headers for compilation_context in compilation_contexts])

    args = ctx.actions.args()

    # specify the output file - twice
    outfile = ctx.actions.declare_file(
        "bazel_clang_tidy_" + infile.path + "." + discriminator + ".clang-tidy.yaml",
    )

    # this is consumed by the wrapper script
    if len(exe.files.to_list()) == 0:
        args.add("clang-tidy")
    else:
        args.add(exe.files_to_run.executable)

    args.add(config.path)

    args.add(outfile.path)  # this is consumed by the wrapper script
    args.add("--export-fixes", outfile.path)

    # add source to check
    args.add(infile.path)

    # start args passed to the compiler
    args.add("--")

    # add args specified by the toolchain, on the command line and rule copts
    args.add_all(flags)

    # add defines
    for define in _flatten([compilation_context.defines.to_list() for compilation_context in compilation_contexts]):
        args.add("-D" + define)

    for define in _flatten([compilation_context.local_defines.to_list() for compilation_context in compilation_contexts]):
        args.add("-D" + define)

    # add includes
    for i in _flatten([compilation_context.framework_includes.to_list() for compilation_context in compilation_contexts]):
        args.add("-F" + i)

    for i in _flatten([compilation_context.includes.to_list() for compilation_context in compilation_contexts]):
        if "pb" in i:
            args.add("-isystem" + i)
        elif "gflags" in i:
            args.add("-isystem" + i)
        else:
            args.add("-I" + i)

    for compilation_context in compilation_contexts:
        for path in compilation_context.quote_includes.to_list() + compilation_context.system_includes.to_list():
            if path.startswith("external/") or path.find("/bin/external/") != -1:
                args.add("-isystem")
                args.add(path)
            else:
                args.add("-I")
                args.add(path)

    ctx.actions.run(
        inputs = inputs,
        outputs = [outfile],
        executable = wrapper,
        arguments = [args],
        mnemonic = "ClangTidy",
        use_default_shell_env = True,
        progress_message = "Run clang-tidy on {}".format(infile.short_path),
    )
    return outfile

def _toolchain_action_flags(ctx, action_name):
    cc_toolchain = find_cpp_toolchain(ctx)
    feature_configuration = cc_common.configure_features(
        ctx = ctx,
        cc_toolchain = cc_toolchain,
    )
    compile_variables = cc_common.create_compile_variables(
        feature_configuration = feature_configuration,
        cc_toolchain = cc_toolchain,
        user_compile_flags = ctx.fragments.cpp.cxxopts + ctx.fragments.cpp.copts,
    )

    flags = cc_common.get_memory_inefficient_command_line(
        feature_configuration = feature_configuration,
        action_name = action_name,
        variables = compile_variables,
    )

    return flags

def _toolchain_flags_c(ctx):
    return _toolchain_action_flags(ctx, ACTION_NAMES.c_compile)

def _toolchain_flags_cpp(ctx):
    return _toolchain_action_flags(ctx, ACTION_NAMES.cpp_compile)

def _is_c_compilation(srcs):
    for src in srcs:
        if src.extension == "c":
            return True

    return False

def _toolchain_flags(ctx, srcs):
    if _is_c_compilation(srcs):
        return _toolchain_flags_c(ctx)

    return _toolchain_flags_cpp(ctx)

def _safe_flags(flags):
    # Some flags might be used by GCC, but not understood by Clang.
    # Remove them here, to allow users to run clang-tidy, without having
    # a clang toolchain configured (that would produce a good command line with --compiler clang)
    unsupported_flags = [
        "-fno-canonical-system-headers",
        "-fstack-usage",
        "-Wno-free-nonheap-object",
        "-Wunused-but-set-parameter",
        "-Wno-stringop-overflow",
    ]

    return [flag for flag in flags if flag not in unsupported_flags and not flag.startswith("--sysroot") and not "-std=" in flag]

def _replace_gendir(flags, ctx):
    return [flag.replace("$(GENDIR)", ctx.genfiles_dir.path) for flag in flags]

# since implementation_deps is currently an experimental feature we have to add compilation context from implementation_deps manually
def _get_compilation_contexts(target, ctx):
    compilation_contexts = [target[CcInfo].compilation_context]

    implementation_deps = getattr(ctx.rule.attr, "implementation_deps", [])
    for implementation_dep in implementation_deps:
        compilation_contexts.append(implementation_dep[CcInfo].compilation_context)

    return compilation_contexts

def _clang_tidy_aspect_impl(target, ctx):
    # if not a C/C++ target, we are not interested
    if not CcInfo in target:
        return []

    tags = getattr(ctx.rule.attr, "tags", [])
    if not LIBRARY in tags and not BINARY in tags:
        return []

    print(ctx)
    srcs = get_cc_srcs(ctx)
    print(srcs)

    if "internal" in tags:
      config_file = "_clang_tidy_config_internal"
    elif "prod" in tags:
      config_file = "_clang_tidy_config_prod"
    elif "portable" in tags:
      config_file = "_clang_tidy_config_portable"
    elif "safe" in tags:
      config_file = "_clang_tidy_config_safe"
    else:
      fail("Invalid level")

    wrapper = ctx.attr._clang_tidy_wrapper.files_to_run
    exe = ctx.attr._clang_tidy_executable
    additional_deps = ctx.attr._clang_tidy_additional_deps
    config = getattr(ctx.attr, config_file).files.to_list()[0]
    #config = ctx.attr._clang_tidy_config.files.to_list()[0]
    print(config)
    toolchain_flags = _toolchain_flags(ctx, srcs)

    rule_flags = ctx.rule.attr.copts if hasattr(ctx.rule.attr, "copts") else []
    safe_flags = _safe_flags(toolchain_flags + rule_flags)
    final_flags = _replace_gendir(safe_flags, ctx)
    compilation_contexts = _get_compilation_contexts(target, ctx)

    # We exclude headers because we shouldn't run clang-tidy directly with them.
    # Headers will be linted if included in a source file.
    unsupported_ext = ["inc", "h", "hpp"]
    outputs = []
    for src in srcs:
        if src.extension not in unsupported_ext:
            outputs.append(_run_tidy(ctx, wrapper, exe, additional_deps, config, final_flags, compilation_contexts, src, target.label.name))

    return [
        OutputGroupInfo(report = depset(direct = outputs)),
    ]

clang_tidy_aspect = aspect(
    implementation = _clang_tidy_aspect_impl,
    fragments = ["cpp"],
    attrs = {
        "_cc_toolchain": attr.label(default = Label("@bazel_tools//tools/cpp:current_cc_toolchain")),
        "_clang_tidy_wrapper": attr.label(default = Label("//clang_tidy:clang_tidy")),
        "_clang_tidy_executable": attr.label(default = Label("//clang_tidy:clang_tidy_executable")),
        "_clang_tidy_additional_deps": attr.label(default = Label("//clang_tidy:clang_tidy_additional_deps")),
        "_clang_tidy_config": attr.label(default = Label("//clang_tidy:clang_tidy_config")),
        "_clang_tidy_config_internal": attr.label(default = Label("//clang_tidy:clang_tidy_config_internal")),
        "_clang_tidy_config_prod": attr.label(default = Label("//clang_tidy:clang_tidy_config_prod")),
        "_clang_tidy_config_portable": attr.label(default = Label("//clang_tidy:clang_tidy_config_portable")),
        "_clang_tidy_config_safe": attr.label(default = Label("//clang_tidy:clang_tidy_config_safe")),
    },
    toolchains = ["@bazel_tools//tools/cpp:toolchain_type"],
)
