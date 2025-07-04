# Implementation according to
# https://bazel.build/external/migration#detect-toolchain

load(
    ":repositories.bzl",
    "aarch64_linux_musl_toolchain",
    "aarch64_sysroot",
    "arm_linux_musleabihf_toolchain",
    "gcc_arm_embedded_toolchain",
    "gcc_arm_gnu_8_3_toolchain",
    "llvm_mingw_toolchain",
    "swift_cc_toolchain",
    "x86_64_linux_musl_toolchain",
    "x86_64_sysroot",
)

def _swift_cc_toolchain_impl(_ctx):
    swift_cc_toolchain()
    aarch64_sysroot()
    llvm_mingw_toolchain()
    x86_64_sysroot()
    aarch64_linux_musl_toolchain()
    arm_linux_musleabihf_toolchain()
    x86_64_linux_musl_toolchain()
    gcc_arm_gnu_8_3_toolchain()
    gcc_arm_embedded_toolchain()

swift_cc_toolchain_extension = module_extension(
    implementation = _swift_cc_toolchain_impl,
)
