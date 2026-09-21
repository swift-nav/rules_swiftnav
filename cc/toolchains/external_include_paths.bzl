"""Shared definition of the `external_include_paths` cc toolchain feature."""

load("@bazel_tools//tools/build_defs/cc:action_names.bzl", "ACTION_NAMES")
load("@bazel_tools//tools/cpp:cc_toolchain_config_lib.bzl", "feature", "flag_group", "flag_set")

EXTERNAL_INCLUDE_PATHS_FEATURE = feature(
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
