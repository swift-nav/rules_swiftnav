# Copyright (C) 2023 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

load("@rules_cc//cc:defs.bzl", "cc_import", "cc_library")

cc_import(
    name = "libmkl_core",
    static_library = "libmkl_core.a",
    visibility = ["//visibility:public"],
)

cc_import(
    name = "libmkl_intel_lp64",
    static_library = "libmkl_intel_lp64.a",
    visibility = ["//visibility:public"],
)

cc_import(
    name = "libmkl_gnu_thread",
    static_library = "libmkl_gnu_thread.a",
    visibility = ["//visibility:public"],
)

cc_library(
    name = "mkl",
    srcs = [
        "@mkl//:libmkl_core.a",
        "@mkl//:libmkl_gnu_thread.a",
        "@mkl//:libmkl_intel_lp64.a",
    ],
    copts = ["-fopenmp"],
    linkopts = [
        "-Wl,--start-group",
        "$(location @mkl//:libmkl_intel_lp64.a)",
        "$(location @mkl//:libmkl_core.a)",
        "$(location @mkl//:libmkl_gnu_thread.a)",
        "-Wl,--end-group",
        "-l:libgomp.a",
    ],
    linkstatic = 1,
    visibility = ["//visibility:public"],
    deps = [
        ":libmkl_core",
        ":libmkl_gnu_thread",
        ":libmkl_intel_lp64",
        "@mkl_headers",
    ],
    alwayslink = 1,
)
