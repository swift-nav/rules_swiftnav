## local_config_sh_extension.bzl
# https://bazel.build/external/migration#detect-toolchain

load(":yocto_generic.bzl", "yocto_generic")

yocto_generic_extension = module_extension(
    implementation = lambda ctx: yocto_generic(name = "yocto_generic"),
)
