load("@bazel_tools//tools/cpp:cc_toolchain_config_lib.bzl", "feature", "flag_group", "flag_set", "tool_path")
load("@bazel_tools//tools/build_defs/cc:action_names.bzl", "ACTION_NAMES")

def _impl(ctx):
    SDK_PATH_PREFIX = "wrappers/arm-none-eabi-{}"

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
            path = SDK_PATH_PREFIX.format("cpp"),
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
            name = "gcov",
            path = SDK_PATH_PREFIX.format("gcov"),
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

    features = [
        feature(
            name = "default_compile_actions",
            enabled = True,
            flag_sets = [
                flag_set(
                    actions = [
                        ACTION_NAMES.assemble,
                        ACTION_NAMES.c_compile,
                        ACTION_NAMES.cpp_compile,
                        ACTION_NAMES.cpp_header_parsing,
                        ACTION_NAMES.cpp_module_codegen,
                        ACTION_NAMES.cpp_module_compile,
                        ACTION_NAMES.clif_match,
                        ACTION_NAMES.linkstamp_compile,
                        ACTION_NAMES.lto_backend,
                        ACTION_NAMES.preprocess_assemble,
                    ],
                    flag_groups = ([
                        flag_group(
                            flags = [
                                "--sysroot=external/gcc_arm_embedded_toolchain",
                                "-no-canonical-prefixes",
                                "-fno-canonical-system-headers",
                                "-fno-common",
                                "-ffunction-sections",
                                "-fdata-sections",
                                # Reproducibility
                                "-Wno-builtin-macro-redefined",
                                "-D__DATE__=\"redacted\"",
                                "-D__TIMESTAMP__=\"redacted\"",
                                "-D__TIME__=\"redacted\"",
                            ] + ctx.attr.c_opts,
                        ),
                    ]),
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
                            ] + ctx.attr.link_opts,
                        ),
                    ]),
                ),
            ],
        ),
        feature(
            name = "default_strip_flags",
            enabled = True,
            flag_sets = [
                flag_set(
                    actions = [
                        ACTION_NAMES.strip,
                    ],
                    flag_groups = ([
                        flag_group(
                            flags = [
                                "--strip-unneeded",
                            ],
                        ),
                    ]),
                ),
            ],
        ),
    ]

    return cc_common.create_cc_toolchain_config_info(
        ctx = ctx,
        features = features,
        toolchain_identifier = "gcc-arm-embedded",
        host_system_name = "local",
        target_system_name = "local",
        target_cpu = "arm",
        target_libc = "unknown",
        compiler = "gcc",
        abi_version = "unknown",
        abi_libc_version = "unknown",
        tool_paths = tool_paths,
    )

config = rule(
    implementation = _impl,
    attrs = {
        "c_opts": attr.string_list(),
        "link_opts": attr.string_list(),
    },
    provides = [CcToolchainConfigInfo],
)
