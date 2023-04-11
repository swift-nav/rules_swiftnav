load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

def gcc_arm_embedded_toolchain():
    http_archive(
        name = "gcc_arm_embedded_toolchain",
        build_file = "@rules_swiftnav//cc/toolchains/gcc_arm_embedded:toolchain.BUILD",
        sha256 = "97dbb4f019ad1650b732faffcc881689cedc14e2b7ee863d390e0a41ef16c9a3",
        strip_prefix = "gcc-arm-none-eabi-10.3-2021.10",
        url = "https://github.com/swift-nav/swift-toolchains/releases/download/gcc-arm-none-eabi-10/gcc-arm-none-eabi-10.3-2021.10-x86_64-linux.tar.bz2",
    )
