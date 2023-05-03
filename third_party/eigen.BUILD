# Copyright (C) 2023 Swift Navigation Inc.
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

cc_library(
    name = "eigen",
    hdrs = glob(["Eigen/**"]),
    defines = [
        "EIGEN_NO_DEBUG",
    ] + select({
        "@rules_swiftnav//third_party:_enable_mkl": ["EIGEN_USE_MKL_ALL"],
        "//conditions:default": [],
    }),
    includes = ["."],
    deps = select({
        "@rules_swiftnav//third_party:_enable_mkl": ["@mkl"],
        "//conditions:default": [],
    }),
)
