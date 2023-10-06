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

cc_library(
    name = "netcdf-cxx",
    srcs = [
        "cxx4/ncAtt.cpp",
        "cxx4/ncByte.cpp",
        "cxx4/ncChar.cpp",
        "cxx4/ncCheck.cpp",
        "cxx4/ncCompoundType.cpp",
        "cxx4/ncDim.cpp",
        "cxx4/ncDouble.cpp",
        "cxx4/ncEnumType.cpp",
        "cxx4/ncException.cpp",
        "cxx4/ncFile.cpp",
        "cxx4/ncFill.cpp",
        "cxx4/ncFilter.cpp",
        "cxx4/ncFloat.cpp",
        "cxx4/ncGroup.cpp",
        "cxx4/ncGroupAtt.cpp",
        "cxx4/ncInt.cpp",
        "cxx4/ncInt64.cpp",
        "cxx4/ncOpaqueType.cpp",
        "cxx4/ncShort.cpp",
        "cxx4/ncString.cpp",
        "cxx4/ncType.cpp",
        "cxx4/ncUbyte.cpp",
        "cxx4/ncUint.cpp",
        "cxx4/ncUint64.cpp",
        "cxx4/ncUshort.cpp",
        "cxx4/ncVar.cpp",
        "cxx4/ncVarAtt.cpp",
        "cxx4/ncVlenType.cpp",
    ],
    hdrs = [
        "cxx4/ncAtt.h",
        "cxx4/ncByte.h",
        "cxx4/ncChar.h",
        "cxx4/ncCheck.h",
        "cxx4/ncCompoundType.h",
        "cxx4/ncDim.h",
        "cxx4/ncDouble.h",
        "cxx4/ncEnumType.h",
        "cxx4/ncException.h",
        "cxx4/ncFile.h",
        "cxx4/ncFill.h",
        "cxx4/ncFilter.h",
        "cxx4/ncFloat.h",
        "cxx4/ncGroup.h",
        "cxx4/ncGroupAtt.h",
        "cxx4/ncInt.h",
        "cxx4/ncInt64.h",
        "cxx4/ncOpaqueType.h",
        "cxx4/ncShort.h",
        "cxx4/ncString.h",
        "cxx4/ncType.h",
        "cxx4/ncUbyte.h",
        "cxx4/ncUint.h",
        "cxx4/ncUint64.h",
        "cxx4/ncUshort.h",
        "cxx4/ncVar.h",
        "cxx4/ncVarAtt.h",
        "cxx4/ncVlenType.h",
        "cxx4/netcdf",
        "cxx4/test_utilities.h",
    ],
    copts = ["-Wno-mismatched-new-delete"],
    includes = ["cxx4"],
    visibility = ["//visibility:public"],
    deps = [
        "@netcdf-c",
    ],
)
