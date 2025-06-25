load(":repositories.bzl", "swift_cc_toolchain", "aarch64_sysroot", "llvm_mingw_toolchain", "x86_64_sysroot", "aarch64_linux_musl_toolchain", "arm_linux_musleabihf_toolchain", "x86_64_linux_musl_toolchain", "gcc_arm_gnu_8_3_toolchain")

def _swift_cc_toolchain_impl(_ctx):
    swift_cc_toolchain()
    aarch64_sysroot()
    llvm_mingw_toolchain()
    x86_64_sysroot()
    aarch64_linux_musl_toolchain()
    arm_linux_musleabihf_toolchain()
    x86_64_linux_musl_toolchain()
    gcc_arm_gnu_8_3_toolchain()

swift_cc_toolchain_extension = module_extension(
    implementation = _swift_cc_toolchain_impl,
)
