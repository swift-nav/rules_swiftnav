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

load(
    "@bazel_tools//tools/cpp:cc_toolchain_config_lib.bzl",
    "feature",
    "flag_group",
    "flag_set",
)
load("@bazel_tools//tools/build_defs/cc:action_names.bzl", "ACTION_NAMES")

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

gnu_extensions_feature = feature(name = "gnu_extensions")

c89_standard_feature = feature(
    name = "c89",
    provides = ["c_standard"],
    flag_sets = [
        flag_set(
            actions = [ACTION_NAMES.c_compile],
            flag_groups = ([
                flag_group(
                    flags = ["-std=c89"],
                ),
            ]),
            with_features = [
                with_feature_set(not_features = ["gnu_extensions"]),
            ],
        ),
        flag_set(
            actions = [ACTION_NAMES.c_compile],
            flag_groups = ([
                flag_group(
                    flags = ["-std=gnu89"],
                ),
            ]),
            with_features = [
                with_feature_set(features = ["gnu_extensions"]),
            ],
        ),
    ],
)

c90_standard_feature = feature(
    name = "c90",
    provides = ["c_standard"],
    flag_sets = [
        flag_set(
            actions = [ACTION_NAMES.c_compile],
            flag_groups = ([
                flag_group(
                    flags = ["-std=c90"],
                ),
            ]),
            with_features = [
                with_feature_set(not_features = ["gnu_extensions"]),
            ],
        ),
        flag_set(
            actions = [ACTION_NAMES.c_compile],
            flag_groups = ([
                flag_group(
                    flags = ["-std=gnu90"],
                ),
            ]),
            with_features = [
                with_feature_set(features = ["gnu_extensions"]),
            ],
        ),
    ],
)

c99_standard_feature = feature(
    name = "c99",
    provides = ["c_standard"],
    flag_sets = [
        flag_set(
            actions = [ACTION_NAMES.c_compile],
            flag_groups = ([
                flag_group(
                    flags = ["-std=c99"],
                ),
            ]),
            with_features = [
                with_feature_set(not_features = ["gnu_extensions"]),
            ],
        ),
        flag_set(
            actions = [ACTION_NAMES.c_compile],
            flag_groups = ([
                flag_group(
                    flags = ["-std=gnu99"],
                ),
            ]),
            with_features = [
                with_feature_set(features = ["gnu_extensions"]),
            ],
        ),
    ],
)

c11_standard_feature = feature(
    name = "c11",
    provides = ["c_standard"],
    flag_sets = [
        flag_set(
            actions = [ACTION_NAMES.c_compile],
            flag_groups = ([
                flag_group(
                    flags = ["-std=c11"],
                ),
            ]),
            with_features = [
                with_feature_set(not_features = ["gnu_extensions"]),
            ],
        ),
        flag_set(
            actions = [ACTION_NAMES.c_compile],
            flag_groups = ([
                flag_group(
                    flags = ["-std=gnu11"],
                ),
            ]),
            with_features = [
                with_feature_set(features = ["gnu_extensions"]),
            ],
        ),
    ],
)

c17_standard_feature = feature(
    name = "c17",
    provides = ["c_standard"],
    flag_sets = [
        flag_set(
            actions = [ACTION_NAMES.c_compile],
            flag_groups = ([
                flag_group(
                    flags = ["-std=c17"],
                ),
            ]),
            with_features = [
                with_feature_set(not_features = ["gnu_extensions"]),
            ],
        ),
        flag_set(
            actions = [ACTION_NAMES.c_compile],
            flag_groups = ([
                flag_group(
                    flags = ["-std=gnu17"],
                ),
            ]),
            with_features = [
                with_feature_set(features = ["gnu_extensions"]),
            ],
        ),
    ],
)

cxx98_standard_feature = feature(
    name = "c++98",
    provides = ["cxx_standard"],
    flag_sets = [
        flag_set(
            actions = all_cpp_compile_actions,
            flag_groups = ([
                flag_group(
                    flags = ["-std=c++98"],
                ),
            ]),
            with_features = [
                with_feature_set(not_features = ["gnu_extensions"]),
            ],
        ),
        flag_set(
            actions = all_cpp_compile_actions,
            flag_groups = ([
                flag_group(
                    flags = ["-std=gnu++98"],
                ),
            ]),
            with_features = [
                with_feature_set(features = ["gnu_extensions"]),
            ],
        ),
    ],
)

cxx11_standard_feature = feature(
    name = "c++11",
    provides = ["cxx_standard"],
    flag_sets = [
        flag_set(
            actions = all_cpp_compile_actions,
            flag_groups = ([
                flag_group(
                    flags = ["-std=c++0x"],
                ),
            ]),
            with_features = [
                with_feature_set(not_features = ["gnu_extensions"]),
            ],
        ),
        flag_set(
            actions = all_cpp_compile_actions,
            flag_groups = ([
                flag_group(
                    flags = ["-std=gnu++0x"],
                ),
            ]),
            with_features = [
                with_feature_set(features = ["gnu_extensions"]),
            ],
        ),
    ],
)

cxx14_standard_feature = feature(
    name = "c++14",
    provides = ["cxx_standard"],
    flag_sets = [
        flag_set(
            actions = all_cpp_compile_actions,
            flag_groups = ([
                flag_group(
                    flags = ["-std=c++14"],
                ),
            ]),
            with_features = [
                with_feature_set(not_features = ["gnu_extensions"]),
            ],
        ),
        flag_set(
            actions = all_cpp_compile_actions,
            flag_groups = ([
                flag_group(
                    flags = ["-std=gnu++14"],
                ),
            ]),
            with_features = [
                with_feature_set(features = ["gnu_extensions"]),
            ],
        ),
    ],
)

cxx17_standard_feature = feature(
    name = "c++17",
    provides = ["cxx_standard"],
    flag_sets = [
        flag_set(
            actions = all_cpp_compile_actions,
            flag_groups = ([
                flag_group(
                    flags = ["-std=c++17"],
                ),
            ]),
            with_features = [
                with_feature_set(not_features = ["gnu_extensions"]),
            ],
        ),
        flag_set(
            actions = all_cpp_compile_actions,
            flag_groups = ([
                flag_group(
                    flags = ["-std=gnu++17"],
                ),
            ]),
            with_features = [
                with_feature_set(features = ["gnu_extensions"]),
            ],
        ),
    ],
)

cxx20_standard_feature = feature(
    name = "c++20",
    provides = ["cxx_standard"],
    flag_sets = [
        flag_set(
            actions = all_cpp_compile_actions,
            flag_groups = ([
                flag_group(
                    flags = ["-std=c++20"],
                ),
            ]),
            with_features = [
                with_feature_set(not_features = ["gnu_extensions"]),
            ],
        ),
        flag_set(
            actions = all_cpp_compile_actions,
            flag_groups = ([
                flag_group(
                    flags = ["-std=gnu++20"],
                ),
            ]),
            with_features = [
                with_feature_set(features = ["gnu_extensions"]),
            ],
        ),
        # clang is aggresive about removing features from the standard.
        flag_set(
            actions = all_cpp_compile_actions,
            flag_groups = ([
                flag_group(
                    flags = ["-D_LIBCPP_ENABLE_CXX20_REMOVED_FEATURES"],
                ),
            ]),
            with_features = [
                with_feature_set(features = ["libcpp"]),
            ],
        ),
    ],
)

# Clang has a set of warnings that are always enabled by default
# which gets noisey for third party code. This feature allows disabling
# these warnings for code we likely never intend to patch to focus on
# warnings we care about.
swift_no_default_warnings = feature(
    name = "no_default_warnings",
    flag_sets = [
        flag_set(
            actions = _all_compile_actions,
            flag_groups = [flag_group(flags = [
                "-Wno-fortify-source",
                "-Wno-absolute-value",
                "-Wno-format",
                "-Wno-deprecated-declarations",
                "-Wno-unused-but-set-variable",
                "-Wno-pointer-bool-conversion",
                "-Wno-unused-variable",
                "-Wno-incompatible-pointer-types-discards-qualifiers",
                "-Wno-implicit-const-int-float-conversion",
                "-Wno-implicit-function-declaration",
                "-Wno-mismatched-new-delete",
            ])],
        ),
    ],
)
