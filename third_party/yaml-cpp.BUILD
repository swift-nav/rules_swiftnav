# Copyright (C) 2022 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

package(
    default_visibility = ["//visibility:public"],
)

yaml_cpp_defines = select({
    # On Windows, ensure static linking is used.
    "@platforms//os:windows": [
        "YAML_CPP_STATIC_DEFINE",
        "YAML_CPP_NO_CONTRIB",
    ],
    "//conditions:default": [],
})

cc_library(
    name = "yaml-cpp_internal",
    hdrs = glob(["src/**/*.h"]),
    strip_include_prefix = "src",
    visibility = ["//:__subpackages__"],
)

cc_library(
    name = "yaml-cpp",
    srcs = glob([
        "src/**/*.cpp",
        "src/**/*.h",
    ]),
    hdrs = glob(["include/**/*.h"]),
    defines = yaml_cpp_defines,
    includes = ["include"],
    visibility = ["//visibility:public"],
)
