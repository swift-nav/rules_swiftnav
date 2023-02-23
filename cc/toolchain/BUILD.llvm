# Copyright (C) 2022 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

package(default_visibility = ["//visibility:public"])

# Some targets may need to directly depend on these files.
exports_files(glob([
    "bin/*",
    "lib/*",
    "include/*",
]))

## LLVM toolchain files

filegroup(
    name = "clang",
    srcs = [
        "bin/clang",
        "bin/clang++",
        "bin/clang-cpp",
    ],
)

filegroup(
    name = "ld",
    srcs = [
        "bin/ld.lld",
    ],
)

filegroup(
    name = "include",
    srcs = glob([
        "include/**/c++/**",
        "lib/clang/*/include/**",
    ]),
)

filegroup(
    name = "bin",
    srcs = glob(["bin/**"]),
)

filegroup(
    name = "lib",
    srcs = glob(
        [
            "lib/**/lib*.a",
            "lib/clang/*/lib/**/*.a",
            # clang_rt.*.o supply crtbegin and crtend sections.
            "lib/**/clang_rt.*.o",
        ],
        exclude = [
            "lib/libLLVM*.a",
            "lib/libclang*.a",
            "lib/liblld*.a",
        ],
    ),
    # Do not include the .dylib files in the linker sandbox because they will
    # not be available at runtime. Any library linked from the toolchain should
    # be linked statically.
)

filegroup(
    name = "ar",
    srcs = ["bin/llvm-ar"],
)

filegroup(
    name = "as",
    srcs = [
        "bin/clang",
        "bin/llvm-as",
    ],
)

filegroup(
    name = "nm",
    srcs = ["bin/llvm-nm"],
)

filegroup(
    name = "objcopy",
    srcs = ["bin/llvm-objcopy"],
)

filegroup(
    name = "objdump",
    srcs = ["bin/llvm-objdump"],
)

filegroup(
    name = "profdata",
    srcs = ["bin/llvm-profdata"],
)

filegroup(
    name = "dwp",
    srcs = ["bin/llvm-dwp"],
)

filegroup(
    name = "ranlib",
    srcs = ["bin/llvm-ranlib"],
)

filegroup(
    name = "readelf",
    srcs = ["bin/llvm-readelf"],
)

filegroup(
    name = "strip",
    srcs = ["bin/llvm-strip"],
)

filegroup(
    name = "symbolizer",
    srcs = ["bin/llvm-symbolizer"],
)

filegroup(
    name = "clang-tidy",
    srcs = ["bin/clang-tidy"],
)
