# Copyright (C) 2022 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

"""
netcdf-c@4.9.0
"""

load("@rules_foreign_cc//foreign_cc:defs.bzl", "cmake")

filegroup(
    name = "allsrcs",
    srcs = glob(["**"]),
)

cmake(
    name = "netcdf-c",
    cache_entries = {
        "BUILD_SHARED_LIBS": "OFF",
        "ENABLE_DAP": "OFF",
        "ENABLE_EXAMPLES": "OFF",
        "ENABLE_PNETCDF": "OFF",
        "ENABLE_TESTS": "OFF",
        "ENABLE_NCZARR": "OFF",
        "USE_SZIP": "OFF",
    },
    copts = ["-fPIC"],
    lib_source = ":allsrcs",
    out_static_libs = ["libnetcdf.a"],
    visibility = ["//visibility:public"],
    deps = [
        "@hdf5",
    ],
)
