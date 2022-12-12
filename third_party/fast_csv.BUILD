# Copyright (C) 2022 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

load("@bazel_skylib//rules:common_settings.bzl", "string_flag")

package(
    default_visibility = ["//visibility:public"],
)

string_flag(
    name = "fast_csv_option_type_support",
    build_setting_default = "",
)

config_setting(
    name = "_fast_csv_option_type_support",
    flag_values = {
        ":fast_csv_option_type_support": "on",
    },
)

cc_library(
    name = "fast_csv",
    hdrs = glob(["**"]),
    defines = select({
        ":_fast_csv_option_type_support": ["FAST_CSV_OPTION_TYPE_SUPPORT"],
        "//conditions:default": [],
    }),
    includes = ["."],
)
