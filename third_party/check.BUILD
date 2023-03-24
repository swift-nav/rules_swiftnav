# Copyright (C) 2022 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

load("@rules_foreign_cc//foreign_cc:defs.bzl", "cmake")

filegroup(
    name = "srcs",
    srcs = glob(["**"]),
)

cmake(
    name = "check",
    cache_entries = {
        "CMAKE_C_FLAGS": "-fPIC",
        "CMAKE_INSTALL_LIBDIR": "lib",
        "HAVE_SUBUNIT": "0",
    },
    lib_source = ":srcs",
    linkopts = select({
        "@bazel_tools//src/conditions:darwin": ["-lpthread"],
        "//conditions:default": [
            "-lpthread",
            "-lrt",
        ],
    }),
    out_static_libs = select({
        "@bazel_tools//src/conditions:windows": ["check.lib"],
        "//conditions:default": ["libcheck.a"],
    }),
    visibility = ["//visibility:public"],
)
