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

cc_library(
    name = "cereal",
    hdrs = glob(["include/**"]),
    defines = ["CEREAL_THREAD_SAFE=1"],
    includes = ["include"],
    linkopts = ["-lpthread"],
)
