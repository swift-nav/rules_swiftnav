# Copyright (c) 2023 Synopsys, Inc. All rights reserved worldwide.
load("//coverity/private:toolchains.bzl", "coverity_toolchain", "empty_toolchain")

exports_files(["cov-bazel-agent.jar"])

toolchain_type(name="toolchain_type")

coverity_toolchain(name="coverity_linux", helper="cov-internal-bazel-helper/linux64")
coverity_toolchain(name="coverity_linux_arm64", helper="cov-internal-bazel-helper/linux-arm64")
coverity_toolchain(name="coverity_windows", helper="cov-internal-bazel-helper/win64")
coverity_toolchain(name="coverity_osx", helper="cov-internal-bazel-helper/macosx")
coverity_toolchain(
    name="coverity_macos_arm", helper="cov-internal-bazel-helper/macos-arm"
)

toolchain(
    name="coverity_linux_toolchain",
    exec_compatible_with=[
        "@platforms//os:linux",
        "@platforms//cpu:x86_64",
    ],
    toolchain=":coverity_linux",
    toolchain_type=":toolchain_type",
)

toolchain(
    name="coverity_linux_arm64_toolchain",
    exec_compatible_with=[
        "@platforms//os:linux",
        "@platforms//cpu:arm64",
    ],
    toolchain=":coverity_linux_arm64",
    toolchain_type=":toolchain_type",
)

toolchain(
    name="coverity_windows_toolchain",
    exec_compatible_with=[
        "@platforms//os:windows",
        "@platforms//cpu:x86_64",
    ],
    toolchain=":coverity_windows",
    toolchain_type=":toolchain_type",
)

toolchain(
    name="coverity_osx_toolchain",
    exec_compatible_with=[
        "@platforms//os:osx",
        "@platforms//cpu:x86_64",
    ],
    toolchain=":coverity_osx",
    toolchain_type=":toolchain_type",
)

toolchain(
    name="coverity_macos_arm_toolchain",
    exec_compatible_with=[
        "@platforms//os:macos",
        "@platforms//cpu:arm64",
    ],
    toolchain=":coverity_macos_arm",
    toolchain_type=":toolchain_type",
)

# An empty C++ toolchain that will be present on all platforms
# and be valid on all platforms so that our rule can depend
# on there being some matching C++ toolchain registered
empty_toolchain(name="empty_toolchain")
toolchain(
    name="empty_cpp_toolchain",
    toolchain=":empty_toolchain",
    toolchain_type="@bazel_tools//tools/cpp:toolchain_type",
)
