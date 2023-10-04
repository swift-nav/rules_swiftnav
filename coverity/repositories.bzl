# Copyright (c) 2023 Synopsys, Inc. All rights reserved worldwide.
def rules_coverity_toolchains(register_empty_cpp_toolchain=False):
    native.register_toolchains(
        "@rules_coverity//coverity/private:coverity_linux_toolchain",
        "@rules_coverity//coverity/private:coverity_linux_arm64_toolchain",
        "@rules_coverity//coverity/private:coverity_windows_toolchain",
        "@rules_coverity//coverity/private:coverity_osx_toolchain",
        "@rules_coverity//coverity/private:coverity_macos_arm_toolchain",
    )

    if register_empty_cpp_toolchain:
        native.register_toolchains(
            "@rules_coverity//coverity/private:empty_cpp_toolchain",
        )
