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
load("@bazel_tools//tools/build_defs/repo:utils.bzl", "maybe")

LLVM_DISTRIBUTION_URL = "https://github.com/swift-nav/swift-toolchains/releases/download/llvm-14.0.6/{}.tar.gz"

def swift_cc_toolchain(name):
    maybe(
        http_archive,
        name = "llvm-distribution",
        build_file = Label("//cc/toolchains:llvm.BUILD.bzl"),
        url = LLVM_DISTRIBUTION_URL.format(name),
        strip_prefix = name,
        # sha256 = "61582215dafafb7b576ea30cc136be92c877ba1f1c31ddbbd372d6d65622fef5",
    )

def register_swift_cc_toolchains():
    native.register_toolchains("@rules_swiftnav//cc/toolchains:cc-toolchain-x86_64-linux")
