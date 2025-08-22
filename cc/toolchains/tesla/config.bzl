load("@bazel_tools//tools/cpp:cc_toolchain_config_lib.bzl", "feature", "flag_group", "flag_set", "tool_path", "with_feature_set")
load("@bazel_tools//tools/build_defs/cc:action_names.bzl", "ACTION_NAMES")

def _impl(ctx):
    SDK_PATH_PREFIX = "/opt/tesla/{cpu}/bin/{cpu}-tesla-linux-gnu-".format(cpu = ctx.attr.cpu) + "{}"

    tool_paths = [
        tool_path(
            name = "ar",
            path = SDK_PATH_PREFIX.format("ar"),
        ),
        tool_path(
            name = "as",
            path = SDK_PATH_PREFIX.format("as"),
        ),
        tool_path(
            name = "cpp",
            path = SDK_PATH_PREFIX.format("gcc"),
        ),
        tool_path(
            name = "gcc",
            path = SDK_PATH_PREFIX.format("gcc"),
        ),
        tool_path(
            name = "g++",
            path = SDK_PATH_PREFIX.format("g++"),
        ),
        tool_path(
            name = "ld",
            path = SDK_PATH_PREFIX.format("ld"),
        ),
        tool_path(
            name = "nm",
            path = SDK_PATH_PREFIX.format("nm"),
        ),
        tool_path(
            name = "objcopy",
            path = SDK_PATH_PREFIX.format("objcopy"),
        ),
        tool_path(
            name = "objdump",
            path = SDK_PATH_PREFIX.format("objdump"),
        ),
        tool_path(
            name = "ranlib",
            path = SDK_PATH_PREFIX.format("ranlib"),
        ),
        tool_path(
            name = "strip",
            path = SDK_PATH_PREFIX.format("strip"),
        ),
    ]

    common_compile_flags = [
        "-D_FORTIFY_SOURCE=1",
        "-fstack-protector-strong",
        "-Wl,-z,relro,-z,now",
        "-fPIC",
        "-fPIE",
        # Reproducibility
        "-Wno-builtin-macro-redefined",
        "-D__DATE__=\"redacted\"",
        "-D__TIMESTAMP__=\"redacted\"",
        "-D__TIME__=\"redacted\"",
    ]

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
                            flags = common_compile_flags + [
                                "-fno-rtti",
                                "-Wno-noexcept-type",
                                "-std=c++14",
                            ],
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
                                "-Wl,-O1",
                                "-Wl,--hash-style=gnu",
                                "-Wl,--as-needed",
                            ],
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
        cxx_builtin_include_directories = [
            "/opt/tesla/{cpu}/{cpu}-tesla-linux-gnu/include".format(cpu = ctx.attr.cpu),
            "/opt/tesla/{cpu}/{cpu}-tesla-linux-gnu/sysroot/usr/include".format(cpu = ctx.attr.cpu),
            "/opt/tesla/{cpu}/lib/gcc/{cpu}-tesla-linux-gnu/7.4.0/include".format(cpu = ctx.attr.cpu),
            "/opt/tesla/{cpu}/lib/gcc/{cpu}-tesla-linux-gnu/7.4.0/include-fixed".format(cpu = ctx.attr.cpu),
        ],
        toolchain_identifier = "tesla-toolchain",
        host_system_name = "local",
        target_system_name = "local",
        target_cpu = ctx.attr.cpu,
        target_libc = "unknown",
        compiler = "gcc",
        abi_version = "unknown",
        abi_libc_version = "unknown",
        tool_paths = tool_paths,
    )

config = rule(
    implementation = _impl,
    attrs = {
        "cpu": attr.string(mandatory = True),
    },
    provides = [CcToolchainConfigInfo],
)
