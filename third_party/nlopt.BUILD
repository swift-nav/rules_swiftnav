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

package(
    default_visibility = ["//visibility:public"],
)

filegroup(
    name = "srcs",
    srcs = glob(["**"]),
)

cmake(
    name = "nlopt",
    cache_entries = {
        "CMAKE_C_FLAGS": "-fPIC",
    },
    generate_args = [
        "-DBUILD_SHARED_LIBS=OFF",
        "-DNLOPT_PYTHON=OFF",
        "-DNLOPT_OCTAVE=OFF",
        "-DNLOPT_MATLAB=OFF",
        "-DNLOPT_GUILE=OFF",
        "-DNLOPT_SWIG=OFF",
    ],
    lib_source = ":srcs",
    out_static_libs = ["libnlopt.a"],
    visibility = ["//visibility:public"],
)
