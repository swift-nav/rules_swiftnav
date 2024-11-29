load("@bazel_tools//tools/cpp:cc_toolchain_config_lib.bzl", "feature", "flag_group", "flag_set", "tool_path", "with_feature_set")
load("@bazel_tools//tools/build_defs/cc:action_names.bzl", "ACTION_NAMES")
load(
    "@yocto_generic//:toolchain.bzl",
    "AR",
    "AS",
    "CC",
    "COMPILE_FLAGS",
    "CPP",
    "CXX",
    "LD",
    "LINK_FLAGS",
    "NATIVE_INCLUDE_PATHS",
    "NM",
    "OBJCOPY",
    "OBJDUMP",
    "RANLIB",
    "STRIP",
    "SYSROOT",
)

def _impl(ctx):
    tool_paths = [
        tool_path(
            name = "ar",
            path = AR,
        ),
        tool_path(
            name = "as",
            path = AS,
        ),
        tool_path(
            name = "gcc",
            path = CC,
        ),
        tool_path(
            name = "cpp",
            path = CPP,
        ),
        tool_path(
            name = "g++",
            path = CXX,
        ),
        tool_path(
            name = "ld",
            path = LD,
        ),
        tool_path(
            name = "nm",
            path = NM,
        ),
        tool_path(
            name = "objcopy",
            path = OBJCOPY,
        ),
        tool_path(
            name = "objdump",
            path = OBJDUMP,
        ),
        tool_path(
            name = "ranlib",
            path = RANLIB,
        ),
        tool_path(
            name = "strip",
            path = STRIP,
        ),
    ]
    common_compile_flags = [
        "-no-canonical-prefixes",
        "-fno-canonical-system-headers",
        # Reproducibility
        "-Wno-builtin-macro-redefined",
        "-D__DATE__=\"redacted\"",
        "-D__TIMESTAMP__=\"redacted\"",
        "-D__TIME__=\"redacted\"",
    ] + COMPILE_FLAGS

    compile_actions = [
        ACTION_NAMES.assemble,
        ACTION_NAMES.c_compile,
        ACTION_NAMES.clif_match,
        ACTION_NAMES.linkstamp_compile,
        ACTION_NAMES.lto_backend,
        ACTION_NAMES.preprocess_assemble,
    ]

    cpp_compile_actions = [
        ACTION_NAMES.cpp_compile,
        ACTION_NAMES.cpp_header_parsing,
        ACTION_NAMES.cpp_module_codegen,
        ACTION_NAMES.cpp_module_compile,
    ]

    opt_feature = feature(name = "opt")

    features = [
        feature(
            name = "default_compile_actions",
            enabled = True,
            flag_sets = [
                flag_set(
                    actions = compile_actions,
                    flag_groups = ([
                        flag_group(
                            flags = common_compile_flags,
                        ),
                    ]),
                ),
                flag_set(
                    actions = cpp_compile_actions,
                    flag_groups = ([
                        flag_group(
                            flags = common_compile_flags + ["-std=c++14"],
                        ),
                    ]),
                ),
                flag_set(
                    actions = compile_actions + cpp_compile_actions,
                    flag_groups = ([
                        flag_group(
                            flags = ["-O2", "-g"],
                        ),
                    ]),
                    with_features = [with_feature_set(features = ["opt"])],
                ),
            ],
        ),
        feature(
            name = "default_link_flags",
            enabled = True,
            flag_sets = [
                flag_set(
                    actions = [
                        ACTION_NAMES.cpp_link_executable,
                        ACTION_NAMES.cpp_link_dynamic_library,
                        ACTION_NAMES.cpp_link_nodeps_dynamic_library,
                    ],
                    flag_groups = ([
                        flag_group(
                            flags = [
                                "-lstdc++",
                                "-lm",
                            ] + LINK_FLAGS,
                        ),
                    ]),
                ),
            ],
        ),
        opt_feature,
    ]

    return cc_common.create_cc_toolchain_config_info(
        ctx = ctx,
        features = features,
        cxx_builtin_include_directories = ["%sysroot%/usr/include"] + NATIVE_INCLUDE_PATHS,
        builtin_sysroot = SYSROOT,
        toolchain_identifier = "yocto-generic",
        host_system_name = "local",
        target_system_name = "local",
        target_cpu = "",
        target_libc = "unknown",
        compiler = "gcc",
        abi_version = "unknown",
        abi_libc_version = "unknown",
        tool_paths = tool_paths,
    )

config = rule(
    implementation = _impl,
    attrs = {},
    provides = [CcToolchainConfigInfo],
)
