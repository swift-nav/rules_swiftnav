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
load("//cc/toolchains/yocto_generic:yocto_generic.bzl", "yocto_generic")

AARCH64_DARWIN_LLVM = "https://github.com/swift-nav/swift-toolchains/releases/download/llvm-14.0.0/clang%2Bllvm-14.0.0-arm64-apple-darwin.tar.gz"

X86_64_DARWIN_LLVM = "https://github.com/llvm/llvm-project/releases/download/llvmorg-14.0.0/clang%2Bllvm-14.0.0-x86_64-apple-darwin.tar.xz"

AARCH64_LINUX_LLVM = "https://github.com/llvm/llvm-project/releases/download/llvmorg-14.0.0/clang%2Bllvm-14.0.0-aarch64-linux-gnu.tar.xz"

X86_64_LINUX_LLVM = "https://github.com/llvm/llvm-project/releases/download/llvmorg-14.0.0/clang%2Bllvm-14.0.0-x86_64-linux-gnu-ubuntu-18.04.tar.xz"

X86_64_LINUX_UCRT_LLVM_MINGW = "https://github.com/mstorsjo/llvm-mingw/releases/download/20241203/llvm-mingw-20241203-ucrt-ubuntu-20.04-x86_64.tar.xz"

AARCH64_LINUX_MUSL = "https://github.com/swift-nav/swift-toolchains/releases/download/musl-cross-11.2.0/aarch64-linux-musl-cross.tar.gz"

ARM_LINUX_MUSLEABIHF = "https://github.com/swift-nav/swift-toolchains/releases/download/musl-cross-11.2.0/arm-linux-musleabihf-cross.tar.gz"

X86_64_LINUX_MUSL = "https://github.com/swift-nav/swift-toolchains/releases/download/musl-cross-11.2.0/x86_64-linux-musl-cross.tar.gz"

DARWIN_GCC_ARM_EMBEDDED = "https://github.com/swift-nav/swift-toolchains/releases/download/gcc-arm-none-eabi-10/gcc-arm-none-eabi-10.3-2021.10-mac.tar.bz2"

X86_64_LINUX_GCC_ARM_EMBEDDED = "https://github.com/swift-nav/swift-toolchains/releases/download/gcc-arm-none-eabi-10/gcc-arm-none-eabi-10.3-2021.10-x86_64-linux.tar.bz2"

# Fixes a bug in libcpp that removed the std::allocator<void> specialization
# when building with c++20. This was patched in llvm-15 so once we upgrade to
# that this will no longer be necessary.
LLVM_PATCH_FILE = [Label("//cc/toolchains/llvm:llvm.patch")]

# Use p1 for patches generated with git.
LLVM_PATCH_ARGS = ["-p1"]

def swift_cc_toolchain():
    maybe(
        http_archive,
        name = "aarch64-darwin-llvm",
        build_file = Label("//cc/toolchains/llvm:llvm.BUILD.bzl"),
        patch_args = LLVM_PATCH_ARGS,
        patches = LLVM_PATCH_FILE,
        url = AARCH64_DARWIN_LLVM,
        strip_prefix = "clang+llvm-14.0.0-arm64-apple-darwin",
        sha256 = "f826ee92c3fedb92bad2f9f834d96f6b9db3192871bfe434124bca848ba9a2a3",
    )

    maybe(
        http_archive,
        name = "x86_64-darwin-llvm",
        patch_args = LLVM_PATCH_ARGS,
        patches = LLVM_PATCH_FILE,
        build_file = Label("//cc/toolchains/llvm:llvm.BUILD.bzl"),
        url = X86_64_DARWIN_LLVM,
        strip_prefix = "clang+llvm-14.0.0-x86_64-apple-darwin",
        sha256 = "cf5af0f32d78dcf4413ef6966abbfd5b1445fe80bba57f2ff8a08f77e672b9b3",
    )

    maybe(
        http_archive,
        name = "aarch64-linux-llvm",
        patch_args = LLVM_PATCH_ARGS,
        patches = LLVM_PATCH_FILE,
        build_file = Label("//cc/toolchains/llvm:llvm.BUILD.bzl"),
        url = AARCH64_LINUX_LLVM,
        strip_prefix = "clang+llvm-14.0.0-aarch64-linux-gnu",
        sha256 = "1792badcd44066c79148ffeb1746058422cc9d838462be07e3cb19a4b724a1ee",
    )

    maybe(
        http_archive,
        name = "x86_64-linux-llvm",
        build_file = Label("//cc/toolchains/llvm:llvm.BUILD.bzl"),
        patch_args = LLVM_PATCH_ARGS,
        patches = LLVM_PATCH_FILE,
        url = X86_64_LINUX_LLVM,
        strip_prefix = "clang+llvm-14.0.0-x86_64-linux-gnu-ubuntu-18.04",
        sha256 = "61582215dafafb7b576ea30cc136be92c877ba1f1c31ddbbd372d6d65622fef5",
    )

def aarch64_sysroot():
    maybe(
        http_archive,
        name = "aarch64-sysroot",
        sha256 = "4e4cbbed33e78602a5f038305514307a5bd9baa6f6330f433fa4dffb3e9e9ad1",
        build_file_content = """
filegroup(
    name = "aarch64-sysroot",
    srcs = glob(["*/**"]),
    visibility = ["//visibility:public"],
)
    """,
        url = "https://github.com/swift-nav/swift-toolchains/releases/download/bullseye-sysroot-v3/debian_bullseye_aarch64_sysroot.tar.xz",
    )

def x86_64_sysroot():
    maybe(
        http_archive,
        name = "x86_64-sysroot",
        sha256 = "cfa444ecc4fcc858acc045e72403efd54dab734bdad4ddec30aad8826916a617",
        build_file_content = """
filegroup(
    name = "x86_64-sysroot",
    srcs = glob(["*/**"]),
    visibility = ["//visibility:public"],
)
    """,
        url = "https://github.com/swift-nav/swift-toolchains/releases/download/bullseye-sysroot-v3/debian_bullseye_x86_64_sysroot.tar.xz",
    )

def register_swift_cc_toolchains():
    native.register_toolchains("@rules_swiftnav//cc/toolchains/llvm/aarch64-darwin:cc-toolchain-aarch64-darwin")
    native.register_toolchains("@rules_swiftnav//cc/toolchains/llvm/x86_64-darwin:cc-toolchain-x86_64-darwin")
    native.register_toolchains("@rules_swiftnav//cc/toolchains/llvm/aarch64-linux:cc-toolchain-aarch64-linux")
    native.register_toolchains("@rules_swiftnav//cc/toolchains/llvm/x86_64-linux:cc-toolchain-x86_64-linux")
    native.register_toolchains("@rules_swiftnav//cc/toolchains/llvm/x86_64-linux:cc-toolchain-intel-mkl")
    native.register_toolchains("@rules_swiftnav//cc/toolchains/llvm/x86_64-aarch64-linux:cc-toolchain-aarch64-bullseye-graviton2")
    native.register_toolchains("@rules_swiftnav//cc/toolchains/llvm/x86_64-aarch64-linux:cc-toolchain-aarch64-bullseye-graviton3")

def aarch64_linux_musl_toolchain():
    http_archive(
        name = "aarch64-linux-musl",
        build_file = "@rules_swiftnav//cc/toolchains/musl/aarch64:musl.BUILD.bzl",
        sha256 = "a6650541dcc778b79add1dd7369869d5d38ddefa9362b7e32d4cc1267fa7977e",
        strip_prefix = "output",
        url = AARCH64_LINUX_MUSL,
    )

def register_aarch64_linux_musl_toolchain():
    native.register_toolchains("@rules_swiftnav//cc/toolchains/musl/aarch64:toolchain")

def arm_linux_musleabihf_toolchain():
    http_archive(
        name = "arm-linux-musleabihf",
        build_file = "@rules_swiftnav//cc/toolchains/musl/armhf:musl.BUILD.bzl",
        sha256 = "7b310a8bf70500a4072f87c3292321fc4f7b91cc67a85a31e7cf13508fa24a3c",
        strip_prefix = "output",
        url = ARM_LINUX_MUSLEABIHF,
    )

def register_arm_linux_musleabihf_toolchain():
    native.register_toolchains("@rules_swiftnav//cc/toolchains/musl/armhf:toolchain")

def x86_64_linux_musl_toolchain():
    http_archive(
        name = "x86_64-linux-musl",
        build_file = "@rules_swiftnav//cc/toolchains/musl/x86_64:musl.BUILD.bzl",
        sha256 = "594395e60bc93acd7eb049f6d8c28a9c5ad5b6060b230e94f19cd8c005cd3a91",
        strip_prefix = "output",
        url = X86_64_LINUX_MUSL,
    )

def register_x86_64_linux_musl_toolchain():
    native.register_toolchains("@rules_swiftnav//cc/toolchains/musl/x86_64:toolchain")

def llvm_mingw_toolchain():
    http_archive(
        name = "x86_64-linux-llvm-mingw",
        build_file = "@rules_swiftnav//cc/toolchains/llvm_x86_64_windows:toolchain.BUILD",
        sha256 = "21458febf5d2c918df922dd0da60137a8787e5e6b427925a1977c882fc79b550",
        strip_prefix = "llvm-mingw-20241203-ucrt-ubuntu-20.04-x86_64",
        url = X86_64_LINUX_UCRT_LLVM_MINGW,
    )

def register_llvm_mingw_toolchain():
    native.register_toolchains("@rules_swiftnav//cc/toolchains/llvm_x86_64_windows:cc-toolchain-x86_64-windows")

def gcc_arm_embedded_toolchain():
    http_archive(
        name = "x86_64_linux_gcc_arm_embedded_toolchain",
        build_file = "@rules_swiftnav//cc/toolchains/gcc_arm_embedded:toolchain.BUILD",
        sha256 = "97dbb4f019ad1650b732faffcc881689cedc14e2b7ee863d390e0a41ef16c9a3",
        strip_prefix = "gcc-arm-none-eabi-10.3-2021.10",
        url = X86_64_LINUX_GCC_ARM_EMBEDDED,
    )

    http_archive(
        name = "darwin_gcc_arm_embedded_toolchain",
        build_file = "@rules_swiftnav//cc/toolchains/gcc_arm_embedded:toolchain.BUILD",
        sha256 = "fb613dacb25149f140f73fe9ff6c380bb43328e6bf813473986e9127e2bc283b",
        strip_prefix = "gcc-arm-none-eabi-10.3-2021.10",
        url = DARWIN_GCC_ARM_EMBEDDED,
    )

def register_gcc_arm_embedded_toolchain():
    native.register_toolchains("@rules_swiftnav//cc/toolchains/gcc_arm_embedded:toolchain")

def gcc_arm_gnu_8_3_toolchain():
    http_archive(
        name = "gcc_arm_gnu_8_3_toolchain",
        build_file = "@rules_swiftnav//cc/toolchains/gcc_arm_gnu_8_3:toolchain.BUILD",
        sha256 = "8ce3e7688a47d8cd2d8e8323f147104ae1c8139520eca50ccf8a7fa933002731",
        strip_prefix = "gcc-arm-8.3-2019.03-x86_64-aarch64-linux-gnu",
        url = "https://github.com/swift-nav/swift-toolchains/releases/download/gcc-arm-gnu-8.3/gcc-arm-8.3-2019.03-x86_64-aarch64-linux-gnu.tar.xz",
    )

def yocto_generic_toolchain():
    yocto_generic(name = "yocto_generic")

def register_yocto_generic_toolchain():
    native.register_toolchains("@rules_swiftnav//cc/toolchains/yocto_generic:toolchain")
