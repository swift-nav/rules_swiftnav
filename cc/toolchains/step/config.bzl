load("@bazel_tools//tools/cpp:cc_toolchain_config_lib.bzl", "feature", "flag_group", "flag_set", "tool_path")
load("@bazel_tools//tools/build_defs/cc:action_names.bzl", "ACTION_NAMES")
load("swift_custom_features.bzl",
            "gnu_extensions_feature",
            "c89_standard_feature",
            "c90_standard_feature",
            "c99_standard_feature",
            "c11_standard_feature",
            "c17_standard_feature",
            "cxx98_standard_feature",
            "cxx11_standard_feature",
            "cxx14_standard_feature",
            "cxx17_standard_feature",
            "cxx20_standard_feature",
            "swift_relwdbg_feature",
            "swift_rtti_feature",
            "swift_nortti_feature",
            "swift_exceptions_feature",
            "swift_noexceptions_feature",
            "swift_internal_coding_standard_feature",
            "swift_prod_coding_standard_feature",
            "swift_safe_coding_standard_feature",
            "swift_portable_coding_standard_feature",
)

SDK_PATH_PREFIX = "/opt/poky-st/2.6/sysroots/x86_64-pokysdk-linux/usr/bin/arm-poky-linux-gnueabi/arm-poky-linux-gnueabi-{}"

def _impl(ctx):
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
                                "-march=armv7ve",
                                "-mthumb",
                                "-mfpu=neon",
                                "-mfloat-abi=hard",
                                "-mcpu=cortex-a7",
                                "-O2",
                                "-pipe",
                                "-g",
                                "-feliminate-unused-debug-types",
                                "-fno-aggressive-loop-optimizations",
                                # Reproducibility
                                "-Wno-builtin-macro-redefined",
                                "-D__DATE__=\"redacted\"",
                                "-D__TIMESTAMP__=\"redacted\"",
                                "-D__TIME__=\"redacted\"",
                            ],
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
                                "-march=armv7ve",
                                "-mthumb",
                                "-mfpu=neon",
                                "-mfloat-abi=hard",
                                "-mcpu=cortex-a7",
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
      feature(
          name = "treat_warnings_as_errors",
          flag_sets = [
              flag_set(
                  actions = [ACTION_NAMES.c_compile, ACTION_NAMES.cpp_compile],
                  flag_groups = [flag_group(flags = ["-Werror"])],
              ),
          ],
      )
    ] + [
            # append swiftnavs custom features here
            gnu_extensions_feature,
            c89_standard_feature,
            c90_standard_feature,
            c99_standard_feature,
            c11_standard_feature,
            c17_standard_feature,
            cxx98_standard_feature,
            cxx11_standard_feature,
            cxx14_standard_feature,
            cxx17_standard_feature,
            cxx20_standard_feature,
            swift_relwdbg_feature,
            swift_rtti_feature,
            swift_nortti_feature,
            swift_exceptions_feature,
            swift_noexceptions_feature,
            swift_internal_coding_standard_feature,
            swift_prod_coding_standard_feature,
            swift_safe_coding_standard_feature,
            swift_portable_coding_standard_feature,
    ]

    return cc_common.create_cc_toolchain_config_info(
        ctx = ctx,
        features = features,
        cxx_builtin_include_directories = [
            "/opt/poky-st/2.6/sysroots/cortexa7t2hf-neon-poky-linux-gnueabi/usr/include",
            "/opt/poky-st/2.6/sysroots/x86_64-pokysdk-linux/usr/lib/arm-poky-linux-gnueabi/gcc/arm-poky-linux-gnueabi/8.2.0/include",
            "/opt/poky-st/2.6/sysroots/x86_64-pokysdk-linux/usr/lib/arm-poky-linux-gnueabi/gcc/arm-poky-linux-gnueabi/8.2.0/include-fixed",
        ],
        builtin_sysroot = "/opt/poky-st/2.6/sysroots/cortexa7t2hf-neon-poky-linux-gnueabi",
        toolchain_identifier = "step-toolchain",
        host_system_name = "local",
        target_system_name = "local",
        target_cpu = "step",
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
