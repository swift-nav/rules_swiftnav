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

PREFIX = "clang+llvm-14.0.6-{}"
LLVM_DISTRIBUTION_URL = "https://github.com/swift-nav/swift-toolchains/releases/download/llvm-14.0.6/{}.tar.gz".format(PREFIX)

def swift_cc_toolchain(platform):
    maybe(
        http_archive,
        name = "llvm-distribution",
        build_file = Label("//cc/toolchains:llvm.BUILD.bzl"),
        url = LLVM_DISTRIBUTION_URL.format(platform),
        strip_prefix = PREFIX.format(platform),
        # sha256 = "81e8f72231f4b3d86c70d432a86eb238e6b128deb9e76484ebbfad85ed15ac4e",
    )

def register_swift_cc_toolchains():
    native.register_toolchains("@rules_swiftnav//cc/toolchains:cc-toolchain-x86_64-linux")
