# Copyright (C) 2022 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

load("@bazel_skylib//rules:common_settings.bzl", "bool_flag")

package(
    default_visibility = ["//visibility:public"],
)

bool_flag(
    name = "disable_rtti",
    build_setting_default = False,
    visibility = ["//visibility:public"],
)

config_setting(
    name = "_disable_rtti",
    flag_values = {":disable_rtti": "true"},
    visibility = ["//visibility:public"],
)

cc_library(
    name = "rapidcheck",
    srcs = glob(["src/**"]),
    hdrs = glob(["include/**"] + ["extras/**"]),
    defines = select({
        ":_disable_rtti": ["RC_DONT_USE_RTTI"],
        "//conditions:default": [],
    }),
    includes = [
        "extras/gtest/include",
        "include",
    ],
)
