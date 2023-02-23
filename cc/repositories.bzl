# Copyright (C) 2022 Swift Navigation Inc.
# Contact: Swift Navigation <dev@swift-nav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

LLVM_DISTRIBUTION_URL = "https://github.com/llvm/llvm-project/releases/download/llvmorg-14.0.0/clang%2Bllvm-14.0.0-x86_64-linux-gnu-ubuntu-18.04.tar.xz"

def swift_cc_toolchain():
    if "llvm-distribution" not in native.existing_rules():
        http_archive(
            name = "llvm-distribution",
            build_file = Label("//cc/toolchain:BUILD.llvm"),
            url = LLVM_DISTRIBUTION_URL,
            strip_prefix = "clang+llvm-14.0.0-x86_64-linux-gnu-ubuntu-18.04",
            sha256 = "61582215dafafb7b576ea30cc136be92c877ba1f1c31ddbbd372d6d65622fef5",
        )

def register_swift_cc_toolchains():
    native.register_toolchains("@rules_swiftnav//cc/toolchain:cc-toolchain-x86_64-linux")
