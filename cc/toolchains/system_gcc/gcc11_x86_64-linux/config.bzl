load("@bazel_tools//tools/build_defs/cc:action_names.bzl", "ACTION_NAMES")
load(
    "@bazel_tools//tools/cpp:cc_toolchain_config_lib.bzl",
    "action_config",
    "artifact_name_pattern",
    "feature",
    "feature_set",
    "flag_group",
    "flag_set",
    "tool",
    "tool_path",
    "variable_with_value",
    "with_feature_set",
)
load(
    "swift_custom_features.bzl",
    "c11_standard_feature",
    "c17_standard_feature",
    "c89_standard_feature",
    "c90_standard_feature",
    "c99_standard_feature",
    "cxx11_standard_feature",
    "cxx14_standard_feature",
    "cxx17_standard_feature",
    "cxx20_standard_feature",
    "cxx98_standard_feature",
    "gnu_extensions_feature",
    "stack_protector_feature",
    "strong_stack_protector_feature",
    "swift_disable_conversion_warning_feature",
    "swift_disable_warnings_for_test_targets_feature",
    "swift_exceptions_feature",
    "swift_internal_coding_standard_feature",
    "swift_noexceptions_feature",
    "swift_nortti_feature",
    "swift_portable_coding_standard_feature",
    "swift_prod_coding_standard_feature",
    "swift_relwdbg_feature",
    "swift_rtti_feature",
    "swift_safe_coding_standard_feature",
)

all_compile_actions = [
    ACTION_NAMES.c_compile,
    ACTION_NAMES.cpp_compile,
    ACTION_NAMES.linkstamp_compile,
    ACTION_NAMES.assemble,
    ACTION_NAMES.preprocess_assemble,
    ACTION_NAMES.cpp_header_parsing,
    ACTION_NAMES.cpp_module_compile,
    ACTION_NAMES.cpp_module_codegen,
    ACTION_NAMES.clif_match,
    ACTION_NAMES.lto_backend,
]

all_cpp_compile_actions = [
    ACTION_NAMES.cpp_compile,
    ACTION_NAMES.linkstamp_compile,
    ACTION_NAMES.cpp_header_parsing,
    ACTION_NAMES.cpp_module_compile,
    ACTION_NAMES.cpp_module_codegen,
    ACTION_NAMES.clif_match,
]

preprocessor_compile_actions = [
    ACTION_NAMES.c_compile,
    ACTION_NAMES.cpp_compile,
    ACTION_NAMES.linkstamp_compile,
    ACTION_NAMES.preprocess_assemble,
    ACTION_NAMES.cpp_header_parsing,
    ACTION_NAMES.cpp_module_compile,
    ACTION_NAMES.clif_match,
]

codegen_compile_actions = [
    ACTION_NAMES.c_compile,
    ACTION_NAMES.cpp_compile,
    ACTION_NAMES.linkstamp_compile,
    ACTION_NAMES.assemble,
    ACTION_NAMES.preprocess_assemble,
    ACTION_NAMES.cpp_module_codegen,
    ACTION_NAMES.lto_backend,
]

all_link_actions = [
    ACTION_NAMES.cpp_link_executable,
    ACTION_NAMES.cpp_link_dynamic_library,
    ACTION_NAMES.cpp_link_nodeps_dynamic_library,
]

lto_index_actions = [
    ACTION_NAMES.lto_index_for_executable,
    ACTION_NAMES.lto_index_for_dynamic_library,
    ACTION_NAMES.lto_index_for_nodeps_dynamic_library,
]

def _impl(ctx):
    # Note that we also set --coverage for c++-link-nodeps-dynamic-library. The
    # generated code contains references to gcov symbols, and the dynamic linker
    # can't resolve them unless the library is linked against gcov.
    coverage_feature = feature(
        name = "coverage",
        provides = ["profile"],
        flag_sets = [
            flag_set(
                actions = [
                    ACTION_NAMES.preprocess_assemble,
                    ACTION_NAMES.c_compile,
                    ACTION_NAMES.cpp_compile,
                    ACTION_NAMES.cpp_header_parsing,
                    ACTION_NAMES.cpp_module_compile,
                ],
                flag_groups = ([
                    flag_group(flags = ctx.attr.coverage_compile_flags),
                ] if ctx.attr.coverage_compile_flags else []),
            ),
            flag_set(
                actions = all_link_actions + lto_index_actions,
                flag_groups = ([
                    flag_group(flags = ctx.attr.coverage_link_flags),
                ] if ctx.attr.coverage_link_flags else []),
            ),
        ],
    )

    cxx_builtin_include_directories = [
        "/usr/include",
        "/usr/include/c++/11",
        "/usr/include/x86_64-linux-gnu/c++/11",
        "/usr/include/c++/11/backward",
        "/usr/lib/gcc/x86_64-linux-gnu/11/include",
        "/usr/lib/gcc/x86_64-linux-gnu/11/include-fixed",
    ]

    default_compile_flags_feature = feature(
        name = "default_compile_flags",
        enabled = True,
        flag_sets = [
            flag_set(
                actions = all_compile_actions,
                flag_groups = [
                    flag_group(
                        # Security hardening requires optimization.
                        # We need to undef it as some distributions now have it enabled by default.
                        flags = [
                            "-U_FORTIFY_SOURCE",
                            "-no-canonical-prefixes",
                            "-fno-canonical-system-headers",
                        ],
                    ),
                ],
                with_features = [
                    with_feature_set(
                        not_features = ["thin_lto"],
                    ),
                ],
            ),
            flag_set(
                actions = all_compile_actions,
                flag_groups = ([
                    flag_group(
                        flags = ctx.attr.compile_flags,
                    ),
                ] if ctx.attr.compile_flags else []),
            ),
            flag_set(
                actions = all_compile_actions,
                flag_groups = ([
                    flag_group(
                        flags = ctx.attr.dbg_compile_flags,
                    ),
                ] if ctx.attr.dbg_compile_flags else []),
                with_features = [with_feature_set(features = ["dbg"])],
            ),
            flag_set(
                actions = all_compile_actions,
                flag_groups = ([
                    flag_group(
                        flags = ctx.attr.opt_compile_flags,
                    ),
                ] if ctx.attr.opt_compile_flags else []),
                with_features = [with_feature_set(features = ["opt"])],
            ),
            flag_set(
                actions = all_cpp_compile_actions + [ACTION_NAMES.lto_backend],
                flag_groups = ([
                    flag_group(
                        flags = ctx.attr.cxx_flags,
                    ),
                ] if ctx.attr.cxx_flags else []),
            ),
        ],
    )

    is_linux = ctx.attr.target_libc != "macosx"

    default_link_flags_feature = feature(
        name = "default_link_flags",
        enabled = True,
        flag_sets = [
            flag_set(
                actions = all_link_actions + lto_index_actions,
                flag_groups = ([
                    flag_group(
                        flags = ["-lm", "-latomic"] + ctx.attr.link_flags,
                    ),
                ] if ctx.attr.link_flags else []),
            ),
            flag_set(
                actions = all_link_actions + lto_index_actions,
                flag_groups = ([
                    flag_group(
                        flags = ctx.attr.opt_link_flags,
                    ),
                ] if ctx.attr.opt_link_flags else []),
                with_features = [with_feature_set(features = ["opt"])],
            ),
        ] + ([flag_set(
            actions = all_link_actions + lto_index_actions,
            flag_groups = ([
                flag_group(
                    flags = [
                        # implies static linking.
                        "-l:libc++.a",
                        "-l:libc++abi.a",
                        "-l:libunwind.a",
                        "-rtlib=compiler-rt",
                    ],
                ),
            ]),
            with_features = [with_feature_set(features = ["libcpp"])],
        )] if is_linux else []),
    )

    dbg_feature = feature(name = "dbg")

    opt_feature = feature(name = "opt")

    supports_pic_feature = feature(
        name = "supports_pic",
        enabled = True,
    )
    supports_start_end_lib_feature = feature(
        name = "supports_start_end_lib",
        enabled = True,
    )

    tool_paths = [
        tool_path(name = "ar", path = "/usr/bin/ar"),
        tool_path(name = "as", path = "/usr/bin/as"),
        tool_path(name = "cpp", path = "/usr/bin/cpp-11"),
        tool_path(name = "gcc", path = "/usr/bin/gcc-11"),
        tool_path(name = "g++", path = "/usr/bin/g++-11"),
        tool_path(name = "gcov", path = "/usr/bin/gcov-11"),
        tool_path(name = "ld", path = "/usr/bin/g++-11"),
        tool_path(name = "nm", path = "/usr/bin/nm"),
        tool_path(name = "objcopy", path = "/usr/bin/objcopy"),
        tool_path(name = "objdump", path = "/usr/bin/objdump"),
        tool_path(name = "ranlib", path = "/usr/bin/ranlib"),
        tool_path(name = "strip", path = "/usr/bin/strip"),
    ]

    features = [
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
        swift_disable_conversion_warning_feature,
        swift_disable_warnings_for_test_targets_feature,
    ]
    toolchain_identifier = "cc-gcc-x86_64-linux"
    unfiltered_compile_flags_feature = feature(
        name = "unfiltered_compile_flags",
        enabled = True,
        flag_sets = [
            flag_set(
                actions = all_compile_actions,
                flag_groups = ([
                    flag_group(
                        flags = ctx.attr.unfiltered_compile_flags,
                    ),
                ] if ctx.attr.unfiltered_compile_flags else []),
            ),
        ],
    )

    sysroot_feature = feature(
        name = "sysroot",
        enabled = True,
        flag_sets = [
            flag_set(
                actions = [
                    ACTION_NAMES.preprocess_assemble,
                    ACTION_NAMES.linkstamp_compile,
                    ACTION_NAMES.c_compile,
                    ACTION_NAMES.cpp_compile,
                    ACTION_NAMES.cpp_header_parsing,
                    ACTION_NAMES.cpp_module_compile,
                    ACTION_NAMES.cpp_module_codegen,
                    ACTION_NAMES.lto_backend,
                    ACTION_NAMES.clif_match,
                ] + all_link_actions + lto_index_actions,
                flag_groups = [
                    flag_group(
                        flags = ["--sysroot=%{sysroot}"],
                        expand_if_available = "sysroot",
                    ),
                ],
            ),
        ],
    )

    libtool_feature = feature(
        name = "libtool",
        enabled = ctx.attr.use_libtool,
    )

    archiver_flags_feature = feature(
        name = "archiver_flags",
        flag_sets = [
            flag_set(
                actions = [ACTION_NAMES.cpp_link_static_library],
                flag_groups = [
                    flag_group(flags = ["rcsD"]),
                    flag_group(
                        flags = ["%{output_execpath}"],
                        expand_if_available = "output_execpath",
                    ),
                ],
                with_features = [
                    with_feature_set(
                        not_features = ["libtool"],
                    ),
                ],
            ),
            flag_set(
                actions = [ACTION_NAMES.cpp_link_static_library],
                flag_groups = [
                    flag_group(flags = ["-no_warning_for_no_symbols", "-static", "-s"]),
                    flag_group(
                        flags = ["-o", "%{output_execpath}"],
                        expand_if_available = "output_execpath",
                    ),
                ],
                with_features = [
                    with_feature_set(
                        features = ["libtool"],
                    ),
                ],
            ),
            flag_set(
                actions = [ACTION_NAMES.cpp_link_static_library],
                flag_groups = [
                    flag_group(
                        iterate_over = "libraries_to_link",
                        flag_groups = [
                            flag_group(
                                flags = ["%{libraries_to_link.name}"],
                                expand_if_equal = variable_with_value(
                                    name = "libraries_to_link.type",
                                    value = "object_file",
                                ),
                            ),
                            flag_group(
                                flags = ["%{libraries_to_link.object_files}"],
                                iterate_over = "libraries_to_link.object_files",
                                expand_if_equal = variable_with_value(
                                    name = "libraries_to_link.type",
                                    value = "object_file_group",
                                ),
                            ),
                        ],
                        expand_if_available = "libraries_to_link",
                    ),
                ],
            ),
            flag_set(
                actions = [ACTION_NAMES.cpp_link_static_library],
                flag_groups = ([
                    flag_group(
                        flags = ctx.attr.archive_flags,
                    ),
                ] if ctx.attr.archive_flags else []),
            ),
        ],
    )

    user_link_flags_feature = feature(
        name = "user_link_flags",
        flag_sets = [
            flag_set(
                actions = all_link_actions + lto_index_actions,
                flag_groups = [
                    flag_group(
                        flags = ["%{user_link_flags}"],
                        iterate_over = "user_link_flags",
                        expand_if_available = "user_link_flags",
                    ),
                ],
            ),
        ],
    )

    fdo_optimize_feature = feature(
        name = "fdo_optimize",
        flag_sets = [
            flag_set(
                actions = [ACTION_NAMES.c_compile, ACTION_NAMES.cpp_compile],
                flag_groups = [
                    flag_group(
                        flags = [
                            "-fprofile-use=%{fdo_profile_path}",
                            "-fprofile-correction",
                        ],
                        expand_if_available = "fdo_profile_path",
                    ),
                ],
            ),
        ],
        provides = ["profile"],
    )

    supports_dynamic_linker_feature = feature(name = "supports_dynamic_linker", enabled = True)

    user_compile_flags_feature = feature(
        name = "user_compile_flags",
        enabled = True,
        flag_sets = [
            flag_set(
                actions = all_compile_actions,
                flag_groups = [
                    flag_group(
                        flags = ["%{user_compile_flags}"],
                        iterate_over = "user_compile_flags",
                        expand_if_available = "user_compile_flags",
                    ),
                ],
            ),
        ],
    )

    unfiltered_compile_flags_feature = feature(
        name = "unfiltered_compile_flags",
        enabled = True,
        flag_sets = [
            flag_set(
                actions = all_compile_actions,
                flag_groups = ([
                    flag_group(
                        flags = ctx.attr.unfiltered_compile_flags,
                    ),
                ] if ctx.attr.unfiltered_compile_flags else []),
            ),
        ],
    )

    archive_param_file_feature = feature(
        name = "archive_param_file",
        enabled = True,
    )

    treat_warnings_as_errors_feature = feature(
        name = "treat_warnings_as_errors",
        flag_sets = [
            flag_set(
                actions = [ACTION_NAMES.c_compile, ACTION_NAMES.cpp_compile],
                flag_groups = [flag_group(flags = ["-Werror"])],
            ),
            flag_set(
                actions = all_link_actions,
                flag_groups = [flag_group(flags = ["-Wl,-fatal-warnings"])],
            ),
        ],
    )

    external_include_paths_feature = feature(
        name = "external_include_paths",
        flag_sets = [
            flag_set(
                actions = [
                    ACTION_NAMES.preprocess_assemble,
                    ACTION_NAMES.linkstamp_compile,
                    ACTION_NAMES.c_compile,
                    ACTION_NAMES.cpp_compile,
                    ACTION_NAMES.cpp_header_parsing,
                    ACTION_NAMES.cpp_module_compile,
                    ACTION_NAMES.clif_match,
                    ACTION_NAMES.objc_compile,
                    ACTION_NAMES.objcpp_compile,
                ],
                flag_groups = [
                    flag_group(
                        flags = ["-isystem", "%{external_include_paths}"],
                        iterate_over = "external_include_paths",
                        expand_if_available = "external_include_paths",
                    ),
                ],
            ),
        ],
    )

    default_link_libs_feature = feature(
        name = "default_link_libs",
        enabled = True,
        flag_sets = [
            flag_set(
                actions = all_link_actions + lto_index_actions,
                flag_groups = [flag_group(flags = ctx.attr.link_libs)] if ctx.attr.link_libs else [],
            ),
        ],
    )

    features = [
        libtool_feature,
        archiver_flags_feature,
        supports_pic_feature,
    ] + (
        [
            supports_start_end_lib_feature,
        ] if ctx.attr.supports_start_end_lib else []
    ) + [
        default_compile_flags_feature,
        default_link_flags_feature,
        user_link_flags_feature,
        default_link_libs_feature,
        external_include_paths_feature,
        fdo_optimize_feature,
        supports_dynamic_linker_feature,
        dbg_feature,
        opt_feature,
        user_compile_flags_feature,
        unfiltered_compile_flags_feature,
        treat_warnings_as_errors_feature,
        archive_param_file_feature,
        sysroot_feature,
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
        swift_disable_conversion_warning_feature,
        swift_disable_warnings_for_test_targets_feature,
        stack_protector_feature,
        strong_stack_protector_feature,
    ]

    action_configs = []
    artifact_name_patterns = []

    return cc_common.create_cc_toolchain_config_info(
        ctx = ctx,
        features = features,
        action_configs = action_configs,
        artifact_name_patterns = artifact_name_patterns,
        cxx_builtin_include_directories = cxx_builtin_include_directories,
        toolchain_identifier = ctx.attr.toolchain_identifier,
        host_system_name = ctx.attr.host_system_name,
        target_system_name = ctx.attr.target_system_name,
        target_cpu = ctx.attr.cpu,
        target_libc = ctx.attr.target_libc,
        compiler = ctx.attr.compiler,
        abi_version = ctx.attr.abi_version,
        abi_libc_version = ctx.attr.abi_libc_version,
        tool_paths = tool_paths,
        builtin_sysroot = ctx.attr.builtin_sysroot,
    )

config = rule(
    implementation = _impl,
    attrs = {
        "cpu": attr.string(),
        "compiler": attr.string(),
        "toolchain_identifier": attr.string(),
        "host_system_name": attr.string(),
        "target_system_name": attr.string(),
        "target_libc": attr.string(),
        "abi_version": attr.string(),
        "abi_libc_version": attr.string(),
        "cxx_builtin_include_directories": attr.string_list(),
        "tool_paths": attr.string_dict(),
        "compile_flags": attr.string_list(),
        "dbg_compile_flags": attr.string_list(),
        "opt_compile_flags": attr.string_list(),
        "cxx_flags": attr.string_list(),
        "link_flags": attr.string_list(),
        "archive_flags": attr.string_list(),
        "link_libs": attr.string_list(),
        "opt_link_flags": attr.string_list(),
        "unfiltered_compile_flags": attr.string_list(),
        "coverage_compile_flags": attr.string_list(),
        "coverage_link_flags": attr.string_list(),
        "supports_start_end_lib": attr.bool(),
        "builtin_sysroot": attr.string(),
        "use_libtool": attr.bool(),
        "_xcode_config": attr.label(default = configuration_field(
            fragment = "apple",
            name = "xcode_config_label",
        )),
    },
    provides = [CcToolchainConfigInfo],
)
