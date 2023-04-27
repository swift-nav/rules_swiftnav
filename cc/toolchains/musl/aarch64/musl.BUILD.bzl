package(default_visibility = ["//visibility:public"])

filegroup(
    name = "gcc",
    srcs = [
        "bin/aarch64-linux-musl-cpp",
        "bin/aarch64-linux-musl-g++",
        "bin/aarch64-linux-musl-gcc",
    ],
)

filegroup(
    name = "ld",
    srcs = [
        "bin/aarch64-linux-musl-ld",
    ],
)

filegroup(
    name = "include",
    srcs = glob([
        "lib/gcc/aarch64-linux-musl/11.2.0/include/**",
        "lib/gcc/aarch64-linux-musl/11.2.0/include-fixed/**",
        "aarch64-linux-musl/include/**",
    ]),
)

filegroup(
    name = "bin",
    srcs = glob([
        "bin/**",
        "aarch64-linux-musl/bin/**",
    ]) + [
        "libexec/gcc/aarch64-linux-musl/11.2.0/cc1",
        "libexec/gcc/aarch64-linux-musl/11.2.0/cc1plus",
        "libexec/gcc/aarch64-linux-musl/11.2.0/liblto_plugin.so",
    ],
)

filegroup(
    name = "lib",
    srcs = glob([
        "aarch64-linux-musl/lib/**",
        "aarch64-linux-musl/**/lib*.a",  # ?
        "lib/gcc/aarch64-linux-musl/11.2.0/**",
        "lib/**/lib*.a",  # ?
    ]),
)

filegroup(
    name = "ar",
    srcs = ["bin/aarch64-linux-musl-ar"],
)

filegroup(
    name = "as",
    srcs = ["bin/aarch64-linux-musl-as"],
)

filegroup(
    name = "nm",
    srcs = ["bin/aarch64-linux-musl-nm"],
)

filegroup(
    name = "objcopy",
    srcs = ["bin/aarch64-linux-musl-objcopy"],
)

filegroup(
    name = "objdump",
    srcs = ["bin/aarch64-linux-musl-objdump"],
)

filegroup(
    name = "ranlib",
    srcs = ["bin/aarch64-linux-musl-ranlib"],
)

filegroup(
    name = "strip",
    srcs = ["bin/aarch64-linux-musl-strip"],
)
