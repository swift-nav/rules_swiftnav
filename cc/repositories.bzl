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

X86_64_LINUX_LLVM = "https://github.com/llvm/llvm-project/releases/download/llvmorg-14.0.0/clang%2Bllvm-14.0.0-x86_64-linux-gnu-ubuntu-18.04.tar.xz"

X86_64_DARWIN_LLVM = "https://github.com/llvm/llvm-project/releases/download/llvmorg-14.0.0/clang%2Bllvm-14.0.0-x86_64-apple-darwin.tar.xz"

def swift_cc_toolchain():
    maybe(
        http_archive,
        name = "x86_64-linux-llvm",
        build_file = Label("//cc/toolchains/llvm:llvm.BUILD.bzl"),
        url = X86_64_LINUX_LLVM,
        strip_prefix = "clang+llvm-14.0.0-x86_64-linux-gnu-ubuntu-18.04",
        sha256 = "61582215dafafb7b576ea30cc136be92c877ba1f1c31ddbbd372d6d65622fef5",
    )

    maybe(
        http_archive,
        name = "x86_64-darwin-llvm",
        build_file = Label("//cc/toolchains/llvm:llvm.BUILD.bzl"),
        url = X86_64_DARWIN_LLVM,
        strip_prefix = "clang+llvm-14.0.0-x86_64-apple-darwin",
        sha256 = "cf5af0f32d78dcf4413ef6966abbfd5b1445fe80bba57f2ff8a08f77e672b9b3",
    )

def register_swift_cc_toolchains():
    native.register_toolchains("@rules_swiftnav//cc/toolchains/llvm/x86_64-linux:cc-toolchain-x86_64-linux")
    native.register_toolchains("@rules_swiftnav//cc/toolchains/llvm/x86_64-darwin:cc-toolchain-x86_64-darwin")
