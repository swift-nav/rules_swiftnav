"""Swiftnav custom toolchain features

Our unix_cc_toolchain_config.bzl is a fork of upstream at:
    https://github.com/bazelbuild/bazel/blob/master/tools/cpp/unix_cc_toolchain_config.bzl

For the time being we would like to keep this a super set of the features defined there
or pull in fixes and new features without upgrading bazel.

In order to keep this maintainable all of our custom additions will be added
to this file under the swift_ prefix.

Bug fixes, ports of features from newer versions, etc.. should be put as they
appear in upstream in unix_cc_toolchain_config.bzl.
"""

load("@bazel_tools//tools/build_defs/cc:action_names.bzl", "ACTION_NAMES")
load(
    "@rules_swiftnav//cc/toolchains:gcc_llvm_flags.bzl",
    "get_flags_for_lang_and_level",
    "disable_conversion_warning_flags",
)
load(
    "@bazel_tools//tools/cpp:cc_toolchain_config_lib.bzl",
    "feature",
    "flag_group",
    "flag_set",
    "with_feature_set",
)
_invalid_flags = [
    "-Wmismatched-dealloc",
    "-Wsizeof-array-div",
    "-Wstring-compare",
    "-Wenum-conversion",
    "-Wenum-int-mismatch",
    "-Wvla-parameter",
    "-Wzero-length-bounds",
    "-Wself-move",
    "-Wtautological-unsigned-zero-compare",
    "-Wno-tautological-unsigned-zero-compare",
    # Really overzealous on this toolchain, especially with C code
    "-Wunused-const-variable",
    "-Wconversion",
    "-Wsign-conversion",
]

_extra_flags = []


_all_compile_actions = [
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

_all_cpp_compile_actions = [
    ACTION_NAMES.cpp_compile,
    ACTION_NAMES.linkstamp_compile,
    ACTION_NAMES.cpp_header_parsing,
    ACTION_NAMES.cpp_module_compile,
    ACTION_NAMES.cpp_module_codegen,
    ACTION_NAMES.clif_match,
]

_preprocessor_compile_actions = [
    ACTION_NAMES.c_compile,
    ACTION_NAMES.cpp_compile,
    ACTION_NAMES.linkstamp_compile,
    ACTION_NAMES.preprocess_assemble,
    ACTION_NAMES.cpp_header_parsing,
    ACTION_NAMES.cpp_module_compile,
    ACTION_NAMES.clif_match,
]

_codegen_compile_actions = [
    ACTION_NAMES.c_compile,
    ACTION_NAMES.cpp_compile,
    ACTION_NAMES.linkstamp_compile,
    ACTION_NAMES.assemble,
    ACTION_NAMES.preprocess_assemble,
    ACTION_NAMES.cpp_module_codegen,
    ACTION_NAMES.lto_backend,
]

_all_link_actions = [
    ACTION_NAMES.cpp_link_executable,
    ACTION_NAMES.cpp_link_dynamic_library,
    ACTION_NAMES.cpp_link_nodeps_dynamic_library,
]

_lto_index_actions = [
    ACTION_NAMES.lto_index_for_executable,
    ACTION_NAMES.lto_index_for_dynamic_library,
    ACTION_NAMES.lto_index_for_nodeps_dynamic_library,
]

gnu_extensions_feature = feature(name="gnu_extensions")

c89_standard_feature = feature(
    name="c89",
    provides=["c_standard"],
    flag_sets=[
        flag_set(
            actions=[ACTION_NAMES.c_compile],
            flag_groups=(
                [
                    flag_group(
                        flags=["-std=c89"],
                    ),
                ]
            ),
            with_features=[
                with_feature_set(not_features=["gnu_extensions"]),
            ],
        ),
        flag_set(
            actions=[ACTION_NAMES.c_compile],
            flag_groups=(
                [
                    flag_group(
                        flags=["-std=gnu89"],
                    ),
                ]
            ),
            with_features=[
                with_feature_set(features=["gnu_extensions"]),
            ],
        ),
    ],
)

c90_standard_feature = feature(
    name="c90",
    provides=["c_standard"],
    flag_sets=[
        flag_set(
            actions=[ACTION_NAMES.c_compile],
            flag_groups=(
                [
                    flag_group(
                        flags=["-std=c90"],
                    ),
                ]
            ),
            with_features=[
                with_feature_set(not_features=["gnu_extensions"]),
            ],
        ),
        flag_set(
            actions=[ACTION_NAMES.c_compile],
            flag_groups=(
                [
                    flag_group(
                        flags=["-std=gnu90"],
                    ),
                ]
            ),
            with_features=[
                with_feature_set(features=["gnu_extensions"]),
            ],
        ),
    ],
)

c99_standard_feature = feature(
    name="c99",
    provides=["c_standard"],
    flag_sets=[
        flag_set(
            actions=[ACTION_NAMES.c_compile],
            flag_groups=(
                [
                    flag_group(
                        flags=["-std=c99"],
                    ),
                ]
            ),
            with_features=[
                with_feature_set(not_features=["gnu_extensions"]),
            ],
        ),
        flag_set(
            actions=[ACTION_NAMES.c_compile],
            flag_groups=(
                [
                    flag_group(
                        flags=["-std=gnu99"],
                    ),
                ]
            ),
            with_features=[
                with_feature_set(features=["gnu_extensions"]),
            ],
        ),
    ],
)

c11_standard_feature = feature(
    name="c11",
    provides=["c_standard"],
    flag_sets=[
        flag_set(
            actions=[ACTION_NAMES.c_compile],
            flag_groups=(
                [
                    flag_group(
                        flags=["-std=c11"],
                    ),
                ]
            ),
            with_features=[
                with_feature_set(not_features=["gnu_extensions"]),
            ],
        ),
        flag_set(
            actions=[ACTION_NAMES.c_compile],
            flag_groups=(
                [
                    flag_group(
                        flags=["-std=gnu11"],
                    ),
                ]
            ),
            with_features=[
                with_feature_set(features=["gnu_extensions"]),
            ],
        ),
    ],
)

c17_standard_feature = feature(
    name="c17",
    provides=["c_standard"],
    flag_sets=[
        flag_set(
            actions=[ACTION_NAMES.c_compile],
            flag_groups=(
                [
                    flag_group(
                        flags=["-std=c17"],
                    ),
                ]
            ),
            with_features=[
                with_feature_set(not_features=["gnu_extensions"]),
            ],
        ),
        flag_set(
            actions=[ACTION_NAMES.c_compile],
            flag_groups=(
                [
                    flag_group(
                        flags=["-std=gnu17"],
                    ),
                ]
            ),
            with_features=[
                with_feature_set(features=["gnu_extensions"]),
            ],
        ),
    ],
)

cxx98_standard_feature = feature(
    name="c++98",
    provides=["cxx_standard"],
    flag_sets=[
        flag_set(
            actions=_all_cpp_compile_actions,
            flag_groups=(
                [
                    flag_group(
                        flags=["-std=c++98"],
                    ),
                ]
            ),
            with_features=[
                with_feature_set(not_features=["gnu_extensions"]),
            ],
        ),
        flag_set(
            actions=_all_cpp_compile_actions,
            flag_groups=(
                [
                    flag_group(
                        flags=["-std=gnu++98"],
                    ),
                ]
            ),
            with_features=[
                with_feature_set(features=["gnu_extensions"]),
            ],
        ),
    ],
)

cxx11_standard_feature = feature(
    name="c++11",
    provides=["cxx_standard"],
    flag_sets=[
        flag_set(
            actions=_all_cpp_compile_actions,
            flag_groups=(
                [
                    flag_group(
                        flags=["-std=c++0x"],
                    ),
                ]
            ),
            with_features=[
                with_feature_set(not_features=["gnu_extensions"]),
            ],
        ),
        flag_set(
            actions=_all_cpp_compile_actions,
            flag_groups=(
                [
                    flag_group(
                        flags=["-std=gnu++0x"],
                    ),
                ]
            ),
            with_features=[
                with_feature_set(features=["gnu_extensions"]),
            ],
        ),
    ],
)

cxx14_standard_feature = feature(
    name="c++14",
    provides=["cxx_standard"],
    flag_sets=[
        flag_set(
            actions=_all_cpp_compile_actions,
            flag_groups=(
                [
                    flag_group(
                        flags=["-std=c++14"],
                    ),
                ]
            ),
            with_features=[
                with_feature_set(not_features=["gnu_extensions"]),
            ],
        ),
        flag_set(
            actions=_all_cpp_compile_actions,
            flag_groups=(
                [
                    flag_group(
                        flags=["-std=gnu++14"],
                    ),
                ]
            ),
            with_features=[
                with_feature_set(features=["gnu_extensions"]),
            ],
        ),
    ],
)

cxx17_standard_feature = feature(
    name="c++17",
    provides=["cxx_standard"],
    flag_sets=[
        flag_set(
            actions=_all_cpp_compile_actions,
            flag_groups=(
                [
                    flag_group(
                        flags=["-std=c++17"],
                    ),
                ]
            ),
            with_features=[
                with_feature_set(not_features=["gnu_extensions"]),
            ],
        ),
        flag_set(
            actions=_all_cpp_compile_actions,
            flag_groups=(
                [
                    flag_group(
                        flags=["-std=gnu++17"],
                    ),
                ]
            ),
            with_features=[
                with_feature_set(features=["gnu_extensions"]),
            ],
        ),
    ],
)

cxx20_standard_feature = feature(
    name="c++20",
    provides=["cxx_standard"],
    flag_sets=[
        flag_set(
            actions=_all_cpp_compile_actions,
            flag_groups=(
                [
                    flag_group(
                        flags=["-std=c++20"],
                    ),
                ]
            ),
            with_features=[
                with_feature_set(not_features=["gnu_extensions"]),
            ],
        ),
        flag_set(
            actions=_all_cpp_compile_actions,
            flag_groups=(
                [
                    flag_group(
                        flags=["-std=gnu++20"],
                    ),
                ]
            ),
            with_features=[
                with_feature_set(features=["gnu_extensions"]),
            ],
        ),
        # clang is aggresive about removing features from the standard.
        flag_set(
            actions=_preprocessor_compile_actions,
            flag_groups=(
                [
                    flag_group(
                        flags=[
                            # This is a workaround for memory_resource being experimental only
                            # in the llvm-14 libc++ impelmentation.
                            "-DSWIFTNAV_EXPERIMENTAL_MEMORY_RESOURCE",
                            "-D_LIBCPP_ENABLE_CXX20_REMOVED_FEATURES",
                        ],
                    ),
                ]
            ),
            with_features=[
                with_feature_set(features=["libcpp"]),
            ],
        ),
    ],
)

swift_relwdbg_feature = feature(
    name="relwdbg",
    flag_sets=[
        flag_set(
            actions=_all_compile_actions,
            flag_groups=[flag_group(flags=["-O2", "-g"])],
        ),
    ],
)

swift_rtti_feature = feature(
    name="rtti_feature",
    flag_sets=[
        flag_set(
            actions=[ACTION_NAMES.cpp_compile],
            flag_groups=[flag_group(flags=["-frtti"])],
        ),
    ],
)
swift_nortti_feature = feature(
    name="nortti_feature",
    flag_sets=[
        flag_set(
            actions=[ACTION_NAMES.cpp_compile],
            flag_groups=[flag_group(flags=["-fno-rtti"])],
        ),
    ],
)

swift_exceptions_feature = feature(
    name="exceptions_feature",
    flag_sets=[
        flag_set(
            actions=[ACTION_NAMES.cpp_compile],
            flag_groups=[flag_group(flags=["-fexceptions"])],
        ),
    ],
)
swift_noexceptions_feature = feature(
    name="noexceptions_feature",
    flag_sets=[
        flag_set(
            actions=[ACTION_NAMES.cpp_compile],
            flag_groups=[flag_group(flags=["-fno-exceptions"])],
        ),
    ],
)

swift_internal_coding_standard_feature = feature(
    name="internal_coding_standard",
    flag_sets=[
        flag_set(
            actions=_all_compile_actions,
            flag_groups=[
                flag_group(
                    flags=get_flags_for_lang_and_level(
                        "cxx", "internal", _invalid_flags, _extra_flags
                    )
                )
            ],
        ),
    ],
)

swift_prod_coding_standard_feature = feature(
    name="prod_coding_standard",
    flag_sets=[
        flag_set(
            actions=_all_compile_actions,
            flag_groups=[
                flag_group(
                    flags=get_flags_for_lang_and_level(
                        "cxx", "prod", _invalid_flags, _extra_flags
                    )
                )
            ],
        ),
    ],
)

swift_safe_coding_standard_feature = feature(
    name="safe_coding_standard",
    flag_sets=[
        flag_set(
            actions=_all_compile_actions,
            flag_groups=[
                flag_group(
                    flags=get_flags_for_lang_and_level(
                        "cxx", "prod", _invalid_flags, _extra_flags
                    )
                )
            ],
        ),
    ],
)

swift_portable_coding_standard_feature = feature(
    name="portable_coding_standard",
    flag_sets=[
        flag_set(
            actions=_all_compile_actions,
            flag_groups=[flag_group(flags=["-pedantic"])],
        ),
    ],
)

swift_disable_conversion_warning_feature = feature(
    name="disable_conversion_warnings",
    flag_sets=[
        flag_set(
            actions=_all_compile_actions,
            flag_groups=[flag_group(flags=disable_conversion_warning_flags)],
        ),
    ],
)


stack_protector_feature = feature(
    name = "stack_protector",
    flag_sets = [
        flag_set(
            actions = _all_compile_actions,
            flag_groups = [flag_group(flags = ["-fstack-protector"])],
        with_features = [
          with_feature_set(
          not_features = ["strong_stack_protector"],
          ),
        ],
        ),
    ],
)

strong_stack_protector_feature = feature(
    name = "strong_stack_protector",
    flag_sets = [
        flag_set(
            actions = _all_compile_actions,
            flag_groups = [flag_group(flags = ["-fstack-protector-strong"])],
        ),
    ],
)
