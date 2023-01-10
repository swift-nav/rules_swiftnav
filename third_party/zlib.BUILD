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
zlib@1.2.13
"""

package(default_visibility = ["//visibility:public"])

licenses(["notice"])  # BSD/MIT-like license (for zlib)

cc_library(
    name = "zlib",
    srcs = glob([
        "*.c",
        "*.h",
    ]) + [
        "contrib/minizip/ioapi.c",
        "contrib/minizip/ioapi.h",
        "contrib/minizip/unzip.c",
        "contrib/minizip/unzip.h",
    ],
    hdrs = [
        "zlib.h",
    ],
    copts = select({
        "@bazel_tools//src/conditions:windows": [],
        "//conditions:default": [
            "-Wno-shift-negative-value",
            "-DZ_HAVE_UNISTD_H",
        ],
    }),
    includes = [
        ".",
        "contrib/minizip",
    ],
)
