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
netcdf-cxx@4.3.1
"""

load("@rules_foreign_cc//foreign_cc:defs.bzl", "cmake")

filegroup(
    name = "srcs",
    srcs = glob(["**"]),
)

cmake(
    name = "netcdf-cxx",
    cache_entries = {
        "BUILD_SHARED_LIBS": "OFF",
        "NCXX_ENABLE_TESTS": "OFF",
        "HDF5_C_LIBRARY_hdf5": "libhdf5.a",
    },
    lib_source = ":srcs",
    out_static_libs = ["libnetcdf-cxx4.a"],
    visibility = ["//visibility:public"],
    deps = [
        "@hdf5",
        "@hdf5//:hdf5_hl",
        "@netcdf-c",
    ],
)
