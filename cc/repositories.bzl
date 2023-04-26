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

AARCH64_DARWIN_LLVM = "https://github.com/swift-nav/swift-toolchains/releases/download/llvm-14.0.0/clang%2Bllvm-14.0.0-arm64-apple-darwin.tar.gz"

X86_64_DARWIN_LLVM = "https://github.com/llvm/llvm-project/releases/download/llvmorg-14.0.0/clang%2Bllvm-14.0.0-x86_64-apple-darwin.tar.xz"

X86_64_LINUX_LLVM = "https://github.com/llvm/llvm-project/releases/download/llvmorg-14.0.0/clang%2Bllvm-14.0.0-x86_64-linux-gnu-ubuntu-18.04.tar.xz"

GCC_ARM_EMBEDDED = "https://github.com/swift-nav/swift-toolchains/releases/download/gcc-arm-none-eabi-10/gcc-arm-none-eabi-10.3-2021.10-x86_64-linux.tar.bz2"

ARM_LINUX_MUSLEABIHF = "https://github.com/swift-nav/swift-toolchains/releases/download/musl-test-2/arm-linux-musleabihf.tar.gz"

X86_64_LINUX_MUSL = "https://github.com/swift-nav/swift-toolchains/releases/download/musl-test-2/x86_64-linux-musl.tar.gz"

AARCH64_LINUX_MUSL = "https://github.com/swift-nav/swift-toolchains/releases/download/musl-test-2/aarch64-linux-musl.tar.gz"

def swift_cc_toolchain():
    maybe(
        http_archive,
        name = "aarch64-darwin-llvm",
        build_file = Label("//cc/toolchains/llvm:llvm.BUILD.bzl"),
        url = AARCH64_DARWIN_LLVM,
        strip_prefix = "clang+llvm-14.0.0-arm64-apple-darwin",
        sha256 = "f826ee92c3fedb92bad2f9f834d96f6b9db3192871bfe434124bca848ba9a2a3",
    )

    maybe(
        http_archive,
        name = "x86_64-darwin-llvm",
        build_file = Label("//cc/toolchains/llvm:llvm.BUILD.bzl"),
        url = X86_64_DARWIN_LLVM,
        strip_prefix = "clang+llvm-14.0.0-x86_64-apple-darwin",
        sha256 = "cf5af0f32d78dcf4413ef6966abbfd5b1445fe80bba57f2ff8a08f77e672b9b3",
    )

    maybe(
        http_archive,
        name = "x86_64-linux-llvm",
        build_file = Label("//cc/toolchains/llvm:llvm.BUILD.bzl"),
        url = X86_64_LINUX_LLVM,
        strip_prefix = "clang+llvm-14.0.0-x86_64-linux-gnu-ubuntu-18.04",
        sha256 = "61582215dafafb7b576ea30cc136be92c877ba1f1c31ddbbd372d6d65622fef5",
    )

def register_swift_cc_toolchains():
    native.register_toolchains("@rules_swiftnav//cc/toolchains/llvm/aarch64-darwin:cc-toolchain-aarch64-darwin")
    native.register_toolchains("@rules_swiftnav//cc/toolchains/llvm/x86_64-darwin:cc-toolchain-x86_64-darwin")
    native.register_toolchains("@rules_swiftnav//cc/toolchains/llvm/x86_64-linux:cc-toolchain-x86_64-linux")

def gcc_arm_embedded_toolchain():
    http_archive(
        name = "gcc_arm_embedded_toolchain",
        build_file = "@rules_swiftnav//cc/toolchains/gcc_arm_embedded:toolchain.BUILD",
        sha256 = "97dbb4f019ad1650b732faffcc881689cedc14e2b7ee863d390e0a41ef16c9a3",
        strip_prefix = "gcc-arm-none-eabi-10.3-2021.10",
        url = GCC_ARM_EMBEDDED,
    )

def register_gcc_arm_embedded_toolchain():
    native.register_toolchains("@rules_swiftnav//cc/toolchains/gcc_arm_embedded:toolchain")

def arm_linux_musleabihf_toolchain():
    http_archive(
        name = "arm-linux-musleabihf",
        build_file = "@rules_swiftnav//cc/toolchains/musl/armhf:musl.BUILD.bzl",
        strip_prefix = "output",
        url = ARM_LINUX_MUSLEABIHF,
    )

def register_arm_linux_musleabihf_toolchain():
    native.register_toolchains("@rules_swiftnav//cc/toolchains/musl/armhf:toolchain")

def x86_64_linux_musl_toolchain():
    http_archive(
        name = "x86_64-linux-musl",
        build_file = "@rules_swiftnav//cc/toolchains/musl/x86_64:musl.BUILD.bzl",
        strip_prefix = "output",
        url = X86_64_LINUX_MUSL,
    )

def register_x86_64_linux_musl_toolchain():
    native.register_toolchains("@rules_swiftnav//cc/toolchains/musl/x86_64:toolchain")

def aarch64_linux_musl_toolchain():
    http_archive(
        name = "aarch64-linux-musl",
        build_file = "@rules_swiftnav//cc/toolchains/musl/aarch64:musl.BUILD.bzl",
        strip_prefix = "output",
        url = AARCH64_LINUX_MUSL,
    )

def register_aarch64_linux_musl_toolchain():
    native.register_toolchains("@rules_swiftnav//cc/toolchains/musl/aarch64:toolchain")
