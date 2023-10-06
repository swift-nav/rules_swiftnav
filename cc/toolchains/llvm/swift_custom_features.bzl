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
                "-Wno-incompatible-pointer-types-discards-qualifiers",
                "-Wno-implicit-const-in-float-conversion",
                "-Wno-implicit-function-declaration",
                "-Wno-mismatched-new-delete",
            ],)]
        )
    ],
)

