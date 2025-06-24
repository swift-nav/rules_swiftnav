load(":repositories.bzl", "swift_cc_toolchain", "aarch64_sysroot", "llvm_mingw_toolchain")

def _swift_cc_toolchain_impl(_ctx):
    swift_cc_toolchain()
    aarch64_sysroot()
    llvm_mingw_toolchain()

swift_cc_toolchain_extension = module_extension(
    implementation = _swift_cc_toolchain_impl,
)
